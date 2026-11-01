#!/usr/bin/env python3
"""Measure real Fabric BRT → WebSocket executor → IPFS → DMNEngine calls.

New standard instances are prepared outside each measured interval. No business
state reset, generator edit, dummy execution, Redis shared keys or fixed sleeps
used to determine transaction completion.
"""
import argparse
import copy
import csv
import hashlib
import json
import os
from pathlib import Path
from statistics import mean,median
import sys
import threading
import time
import requests
from urllib.parse import urlsplit
from uuid import uuid4
import websocket
from timing_utils import ROOT,PROJECT,SAMPLES,read_clock,mono,save,request,timed,timed_post,wait,operation,success,map_wall

PHASES=['API Invoker','BPMN SC','Event Bus','Executor','IPFS','API Invoker2','DMN SC']


def unpack(value):
    for _ in range(5):
        if value=='':return []
        if isinstance(value,str):value=json.loads(value)
        elif isinstance(value,dict) and 'output' in value:value=value['output']
        elif isinstance(value,dict) and set(value)=={'ret0'}:value=value['ret0']
        else:break
    return value


def query(cfg,method,instance):
    if method in ['ReadGlobalVariable','GetInstance']:
        return unpack(request('POST',cfg['core']+'/contracts/query',json={
            'location':cfg['location'],'method':{'name':method,'params':[{'name':'InstanceID','schema':{'type':'string'}}]},
            'input':{'InstanceID':str(instance)}}))
    return unpack(request('POST',cfg['api']+'/query/'+method,json={'input':{'InstanceID':str(instance)}}))


def invoke(cfg,method,value):
    result=request('POST',cfg['api']+'/invoke/'+method,json={'input':value})
    return operation(cfg['core'],result['id'])


class Executor:
    """Real independent WebSocket consumer, limited to this model and instance."""
    def __init__(self,cfg,subscription,instance,cid,expected):
        self.cfg,self.subscription,self.instance,self.cid,self.expected=cfg,subscription,str(instance),cid,expected
        self.ready=threading.Event();self.done=threading.Event();self.stop=threading.Event()
        self.evidence={};self.error=None
        self.thread=threading.Thread(target=self.run,daemon=True)

    def run(self):
        cfg=self.cfg
        parts=urlsplit(cfg['core']);uri=('wss' if parts.scheme=='https' else 'ws')+'://'+parts.netloc+'/ws'
        ws=None
        try:
            ws=websocket.create_connection(uri,timeout=1)
            ws.send(json.dumps({'type':'start','namespace':'default','name':self.subscription,'autoack':True}))
            self.ready.set()
            while not self.stop.is_set():
                try:raw=ws.recv();received=mono()
                except websocket.WebSocketTimeoutException:continue
                if not raw:raise RuntimeError('WebSocket closed before BRT event')
                frame=json.loads(raw);chain=frame.get('blockchainEvent',{});output=chain.get('output',{})
                if not isinstance(output,dict):continue
                if str(output.get('InstanceID'))!=self.instance or output.get('ID')!=cfg['rule_id']:continue
                assert output['CID']==self.cid and output['Func']==cfg['rule_id']+'_Continue'
                self.evidence={'received_ms':received,'websocket':frame}
                download,content=timed('GET',cfg['ipfs_gateway']+'/ipfs/'+self.cid)
                self.evidence['ipfsRequest']=download
                assert content==self.expected, 'Downloaded DMN bytes do not match prepared rule'
                self.evidence['dmnSha256']=hashlib.sha256(content).hexdigest()
                self.evidence['invokeRequest']=timed_post(cfg['api']+'/invoke/'+output['Func'],
                    {'input':{'InstanceID':self.instance,'ContentOfDmn':content.decode()}})
                self.evidence['finished_ms']=self.evidence['invokeRequest']['end_ms']
                self.done.set();return
        except Exception as exc:
            self.error=exc;self.done.set();self.ready.set()
        finally:
            if ws is not None:ws.close()

    def close(self):
        self.stop.set();self.thread.join(3)


def normalize(sample,pairs=None):
    if pairs is None:
        wait('clock sample',lambda:list(SAMPLES),lambda v:bool(v) and v[-1][1]>sample['finished_ms']+2,seconds=2)
        pairs=[p for p in list(SAMPLES) if sample['invoke1']['start_ms']-200<=p[1]<=sample['finished_ms']+200]
    assert pairs[0][1]<=sample['invoke1']['start_ms'] and pairs[-1][1]>=sample['finished_ms']
    first,second=sample['invoke1'],sample['executor']['invokeRequest'];stop=sample['finished_ms']
    created1=map_wall(sample['operation1']['created'],first['start_ms'],first['end_ms'],pairs,'Operation1.created')
    created2=map_wall(sample['operation2']['created'],second['start_ms'],second['end_ms'],pairs,'Operation2.created')
    succeeded1=map_wall(sample['success1']['created'],created1,stop,pairs,'invoke1 success')
    succeeded2=map_wall(sample['success2']['created'],created2,stop,pairs,'invoke2 success')
    executor=sample['executor'];event=sample['sourceEvent']
    emitted=map_wall(event['created'],first['start_ms'],executor['received_ms'],pairs,'DMNContentRequired received by FireFly')
    # The seven-stage figure includes event observation/ingestion after the
    # business success notification, as well as WebSocket dispatch to executor.
    # Reuse this exact converted boundary rather than converting it twice.
    sample['eventBusBreakdown']={
        'businessSuccessEventId':sample['success1']['id'],
        'sourceEventId':event['id'],
        'chainCompletionToEventRecorded_ms':emitted-succeeded1,
        'eventRecordedToExecutor_ms':executor['received_ms']-emitted,
        'sourceEventOffset_ms':emitted-first['start_ms'],
    }
    sample['timingDefinitionVersion']=2
    ipfs=executor['ipfsRequest']
    intervals=[('API Invoker',first['start_ms'],created1),('BPMN SC',created1,succeeded1),
        ('Event Bus',succeeded1,executor['received_ms']),('Executor',executor['received_ms'],executor['finished_ms']),
        ('IPFS',ipfs['start_ms'],ipfs['end_ms']),('API Invoker2',second['start_ms'],created2),
        ('DMN SC',created2,succeeded2)]
    sample['stages']=[]
    for name,a,b in intervals:
        if b<a:raise ValueError('Invalid clock mapping: inverted '+name)
        sample['stages'].append({'step':name,'start_time':a-first['start_ms'],'end_time':b-first['start_ms'],'duration_ms':b-a,'valid':True})
    sample['clockPairs']=pairs
    sample['clockMethod']='5ms wall/monotonic bridge; reject clock steps and ambiguous mappings; local clients use monotonic_ns'


def export(report,output):
    report['timingDefinitionVersion']=2
    report['eventBusDefinition']='Same first business invoke-success event as BPMN SC end → executor receives correlated DMNContentRequired over WebSocket'
    rows=report['samples'];report['summary']=[]
    for name in PHASES:
        values=[next(v['duration_ms'] for v in s['stages'] if v['step']==name) for s in rows]
        if values:report['summary'].append({'step':name,'count':len(values),'mean_ms':mean(values),'median_ms':median(values),'min_ms':min(values),'max_ms':max(values)})
    save(output/'results.json',report);save(output/'summary.json',report['summary'])
    with (output/'timings.csv').open('w',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['round','instanceId','stage','start_offset_ms','end_offset_ms','duration_ms'])
        for s in rows:
            save(output/f"round-{s['index']}"/'result.json',s)
            for v in s['stages']:writer.writerow([s['index'],s['instanceId'],v['step'],v['start_time'],v['end_time'],v['duration_ms']])
    total_attempts=len(report['attempts']) if 'attempts' in report else report['sampleCounts']['totalAttempts']
    lines=['# Fabric BusinessRule 分阶段时延','',f"状态：{report['status']}；有效样本：{len(rows)}；总尝试：{total_attempts}。",'',
        '| 阶段 | 均值(ms) | 中位数(ms) | 最小(ms) | 最大(ms) |','|---|---:|---:|---:|---:|']
    for v in report['summary']:lines.append(f"| {v['step']} | {v['mean_ms']:.2f} | {v['median_ms']:.2f} | {v['min_ms']:.2f} | {v['max_ms']:.2f} |")
    lines+=['','| 轮次 | 实例 | '+ ' | '.join(PHASES)+' |','|---|---|'+ '|'.join(['---:']*7)+'|']
    for s in rows:lines.append(f"| {s['index']} | {s['instanceId']} | "+' | '.join(f"{v['duration_ms']:.2f}" for v in s['stages'])+' |')
    lines+=['','Executor覆盖IPFS下载和第二次API调用，阶段不可相加。Event Bus起点与BPMN SC终点共用同一业务成功事件时间，结束于执行器收到对应DMNContentRequired。包含成功通知之后的事件监听、接收记录及WebSocket分发等待；eventBusBreakdown保留两部分明细。',
        'DMN SC覆盖BPMN Continue、DMNEngine链内调用、交易提交和成功事件处理，并非单独DMN引擎CPU耗时。',
        '每轮使用生成器原始链码的新实例；初始化、DMN发布、Oracle CID绑定和Start调用均在计时外。未改动BusinessRule状态转换。',
        '全部有效轮次原样保留，未按链上耗时筛除慢样本。DMN从同一IPFS网关按预先发布的CID下载，包含本地已存内容的读取条件，不代表冷缓存远端发现时延。',
        '', '![均值时间线](fabric_businessrule_timeline_mean.png)']
    (output/'RESULTS.md').write_text('\n'.join(lines)+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=ROOT/'config.live.json')
    parser.add_argument('--rounds',type=int,default=3)
    parser.add_argument('--output',type=Path,default=ROOT/'results-3')
    parser.add_argument('--max-attempts',type=int,default=10)
    args=parser.parse_args();assert 1<=args.rounds<=100 and args.max_attempts>=args.rounds
    cfg=json.loads(args.config.read_text());output=args.output
    assert not output.exists() or not any(output.iterdir()), 'Choose an empty output directory'
    output.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(PROJECT/'src/backend'));os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
    import django;django.setup()
    from apps.core.models import BPMNInstance
    cfg['core']=cfg['core'].rstrip('/');cfg['api']=cfg['api'].rstrip('/')
    registered=next(a for a in request('GET',cfg['core']+'/apis') if a['name']==cfg['api'].split('/apis/')[1])
    cfg['location']=registered['location']
    dmn=Path(cfg['dmn_file']).read_bytes();core=cfg['core'];rule=cfg['rule_id']
    report={'platform':'fabric','status':'running','config':cfg,'samples':[],'attempts':[],
            'executionMode':'generator-original-new-instance-per-attempt','requestedRounds':args.rounds}
    active=None
    try:
        upload=request('POST',core+'/data',data={'autometa':'true'},files={'file':('timing-rule.dmn',dmn,'application/xml')})
        published=request('POST',core+'/data/'+upload['id']+'/blob/publish',json={})
        cid=published['blob']['public'];assert cid
        report['dmnPublication']={'dataId':upload['id'],'cid':cid,'sha256':hashlib.sha256(dmn).hexdigest(),'bytes':len(dmn)}
        for attempt in range(1,args.max_attempts+1):
            if len(report['samples'])==args.rounds:break
            print(f'Attempt {attempt}: prepare a new instance outside timing',flush=True)
            parameters={rule+'_Content':dmn.decode(),rule+'_DecisionID':cfg['decision_id'],rule+'_ParamMapping':{'score':'score','approved':'approved'}}
            # Participants are not used by this BRT; its normal generated checks remain intact.
            # Find the first unused ID in this experiment's standalone chaincode.
            # Do not scan unrelated Operations or infer another model's counter.
            candidate=0
            while True:
                probe=requests.post(cfg['api']+'/query/GetAllBusinessRules',json={'input':{'InstanceID':str(candidate)}},timeout=30)
                if probe.ok:candidate+=1;continue
                if probe.status_code==500 and 'does not exist' in probe.text:break
                probe.raise_for_status()
            instance=str(candidate)
            create_op=invoke(cfg,'CreateInstance',{'initParametersBytes':json.dumps(parameters)})
            invoke(cfg,cfg['start_method'],{'InstanceID':instance})
            rule_before=query(cfg,'GetAllBusinessRules',instance)
            assert len(rule_before)==1 and rule_before[0]['State']==1
            before=query(cfg,'ReadGlobalVariable',instance);assert before['Approved'] is False
            oracle=request('POST',core+'/apis/Oracle/invoke/SetDataItem',json={'input':{'accessKey':instance,'key':rule,'value':cid,'dataType':'STRING'}})
            operation(core,oracle['id'])
            dbinstance=BPMNInstance.objects.create(bpmn_id=cfg['bpmn_id'],instance_chaincode_id=int(instance),name='BRT timing '+instance)
            subscription='brt-measure-'+uuid4().hex[:12]
            sub=request('POST',core+'/subscriptions',json={'name':subscription,'transport':'websockets','filter':{'events':'blockchain_event_received','blockchainevent':{'listener':cfg['listener_id']}},'options':{'firstEvent':'newest'}})
            worker=Executor(cfg,subscription,instance,cid,dmn)
            active={'attempt':attempt,'index':len(report['samples'])+1,'instanceId':instance,'databaseInstanceId':str(dbinstance.id),'createOperation':create_op,'status':'running','ruleBefore':rule_before,'globalBefore':before}
            save(output/'active-attempt.json',active)
            try:
                worker.thread.start();assert worker.ready.wait(10)
                if worker.error:raise worker.error
                # Establish the subscription before the measured invocation.
                time.sleep(.1)
                active['invoke1']=timed_post(cfg['api']+'/invoke/'+rule,{'input':{'InstanceID':instance}})
                save(output/'active-attempt.json',active)
                active['operation1']=operation(core,active['invoke1']['value']['id'])
                active['success1']=success(core,active['operation1'])
                assert worker.done.wait(180), 'Executor did not complete'
                if worker.error:raise worker.error
                active['executor']=worker.evidence
                active['operation2']=operation(core,worker.evidence['invokeRequest']['value']['id'])
                active['success2']=success(core,active['operation2'])
                frame=worker.evidence['websocket'];event=frame.get('event',frame)
                active['sourceEvent']=request('GET',core+'/events/'+event['id'])
                assert active['sourceEvent']['type']=='blockchain_event_received'
                assert active['sourceEvent']['reference']==frame['blockchainEvent']['id']
                assert active['sourceEvent']['created']==event['created']
                assert frame['blockchainEvent']['tx']['blockchainId']==active['operation1']['output']['transactionHash']
                active['globalAfter']=query(cfg,'ReadGlobalVariable',instance)
                active['ruleAfter']=query(cfg,'GetAllBusinessRules',instance)
                assert active['globalAfter']['Approved'] is True, 'DMN output was not persisted on chain'
                assert active['ruleAfter'][0]['State']==3, 'BRT did not complete'
                active['executionVerified']=True;active['finished_ms']=mono()
                try:normalize(active)
                except ValueError as exc:
                    active['status']='excluded_invalid_timing';active['error']=str(exc)
                else:
                    active['status']='passed';report['samples'].append(active)
                report['attempts'].append(active)
                save(output/'attempts'/f'attempt-{attempt}'/'result.json',active)
                export(report,output);active=None;(output/'active-attempt.json').unlink()
            finally:
                worker.close()
                request('DELETE',core+'/subscriptions/'+sub['id'])
        assert len(report['samples'])==args.rounds,'Could not collect requested valid samples within attempt budget'
        report['status']='passed'
    except Exception as exc:
        report['status']='failed';report['error']=str(exc)
        if active:
            active['status']='failed';active['error']=str(exc);save(output/'active-attempt.json',active)
        raise
    finally:export(report,output)
    print(f'Completed {args.rounds} verified BRT samples',flush=True)


if __name__=='__main__':main()
