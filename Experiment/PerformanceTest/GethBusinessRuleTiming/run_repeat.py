#!/usr/bin/env python3
"""Real generated Geth BRT → existing Chainlink/CDMN → IPFS → Continue timing.

All deployment, upload, instance initialization and packet observer startup are
outside timing. Existing jobs/services are not changed or replaced by a mock.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
from statistics import mean,median
import subprocess
import sys
import threading
import time
from datetime import datetime
import re
import requests

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[2]
sys.path.insert(0,str(ROOT.parent/'FabricBusinessRuleTiming'))
from timing_utils import mono,save,timed_post,request,wait,operation,success,SAMPLES,map_wall

PHASES=['API Invoker','BPMN SC','Request to Chainlink job','Chainlink Executor','IPFS download',
        'Result commit on chain','API Invoker2','BPMN Continue SC']


# Display names describe DMN responsibilities; raw phase keys stay stable.
PHASE_LABELS={
    'API Invoker':'API Invoker (BRT request)',
    'BPMN SC':'BPMN SC / DMN request',
    'Request to Chainlink job':'DMN request to Chainlink job',
    'Chainlink Executor':'Executor / off-chain DMN evaluation',
    'IPFS download':'IPFS / DMN download',
    'Result commit on chain':'DMN result commit / event receipt',
    'API Invoker2':'API Invoker2 (BPMN Continue)',
    'BPMN Continue SC':'BPMN SC / apply DMN result',
}


# User-confirmed limits only; equality is accepted. No latency filtering on
# other stages until a separate policy is explicitly agreed.
OUTLIER_THRESHOLDS_MS={
    'Result commit on chain':25000,
    'Request to Chainlink job':60000,
}


def load_report(path):
    """Load either an inline run report or the cleaned per-round archive."""
    path=Path(path);report=json.loads(path.read_text())
    if 'sampleFiles' in report:
        assert 'samples' not in report,'Ambiguous duplicate sample storage'
        report['samples']=[json.loads((path.parent/name).read_text()) for name in report['sampleFiles']]
    return report


def excluded_count(report):
    return sum(report.get('excludedCounts',{}).values())+len(report.get('excluded',[]))


def unwrap(value):return next(iter(value.values())) if isinstance(value,dict) and len(value)==1 else value


def query(api,method,value=None):
    return request('POST',api+'/query/'+method,json={'input':value or {}})


def invoke(cfg,method,value):
    op=request('POST',cfg['api']+'/invoke/'+method,json={'input':value})
    return operation(cfg['core'],op['id'])


def rpc(cfg,method,params):
    r=request('POST',cfg['rpc_url'],json={'jsonrpc':'2.0','id':1,'method':method,'params':params})
    if 'error' in r:raise RuntimeError(json.dumps(r['error']))
    return r['result']


def keccak(cfg,data):return rpc(cfg,'web3_sha3',['0x'+data.hex()])


def approval_storage(cfg,instance):
    compiled=json.loads((ROOT/'deployment/storage-layout.json').read_text())
    layouts=[v['storageLayout'] for v in compiled['contracts']['contract.sol'].values() if v['storageLayout']['storage']]
    assert len(layouts)==1
    layout=layouts[0];mapping=next(v for v in layout['storage'] if v['label']=='instances')
    instance_type=layout['types'][mapping['type']]['value']
    memory=next(v for v in layout['types'][instance_type]['members'] if v['label']=='stateMemory')
    approved=next(v for v in layout['types'][memory['type']]['members'] if v['label']=='Approved')
    key=instance.to_bytes(32,'big')+int(mapping['slot']).to_bytes(32,'big')
    slot=int(keccak(cfg,key),16)+int(memory['slot'])+int(approved['slot'])
    raw=rpc(cfg,'eth_getStorageAt',[cfg['contract_address'],hex(slot),'latest'])
    value=(int(raw,16)>>(8*approved['offset']))&255
    assert value in [0,1]
    return {'approved':bool(value),'slot':hex(slot),'raw':raw,'layoutType':instance_type}


def observe_success(core, initial, start):
    op=initial if 'tx' in initial else request('GET',core+'/operations/'+initial['id'])
    lower=start
    def read():
        nonlocal lower
        before=mono()
        rows=request('GET',core+'/events',params={'tx':op['tx'],'limit':1000})
        matches=[v for v in rows if v['type']=='blockchain_invoke_op_succeeded' and v.get('reference')==op['id'] and v.get('tx')==op['tx']]
        if matches:return {'event':matches[0],'bounds':{'lower':lower,'upper':mono()}}
        lower=before
    return wait('Directly observed invoke success',read,bool)


class Observer:
    def __init__(self,name,output):
        self.name=name;self.rows=[];self.ready=threading.Event();self.error=None
        self.log=(output/(name+'-http.jsonl')).open('a')
        self.before=mono()
        self.process=subprocess.Popen(['docker','exec','-i','--user','0',name,'python','-u','-'],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
        self.process.stdin.write((ROOT/'http_observer.py').read_text());self.process.stdin.close()
        self.reader=threading.Thread(target=self.read,daemon=True);self.reader.start()
        if not self.ready.wait(15):raise RuntimeError('Observer did not start on '+name)
        assert self.before<=self.startup['monotonic_ms']<=mono(),'Container clock does not share the host monotonic axis'

    def read(self):
        try:
            for line in self.process.stdout:
                row=json.loads(line);self.log.write(line);self.log.flush()
                if row.get('type')=='ready':self.startup=row;self.ready.set()
                else:self.rows.append(row)
        except Exception as exc:self.error=str(exc)

    def stop(self):
        if hasattr(self,'startup'):
            subprocess.run(['docker','exec',self.name,'kill','-TERM',str(self.startup['pid'])],capture_output=True)
        try:self.process.wait(5)
        except subprocess.TimeoutExpired:self.process.terminate()
        self.reader.join(2);self.log.close()


class Node:
    def __init__(self,port):
        self.port=port;self.base=f'http://127.0.0.1:{port}';self.session=requests.Session()
        # Existing local development credentials; never persisted or printed.
        self.login()
        keys=self.get('/v2/keys/evm')['data'];self.addresses={v['attributes']['address'].lower() for v in keys}
        self.jobs=[v for v in self.get('/v2/jobs')['data'] if v['attributes']['type']=='directrequest']

    def login(self):
        r=self.session.post(self.base+'/sessions',json={
            'email':os.environ.get('CHAINLINK_EMAIL','admin@chain.link'),
            'password':os.environ.get('CHAINLINK_PASSWORD','change-me-strong')},timeout=15)
        r.raise_for_status()
    def get(self,path):
        r=self.session.get(self.base+path,timeout=30)
        if r.status_code==401:
            self.login();r=self.session.get(self.base+path,timeout=30)
        r.raise_for_status();return r.json()

    def find_run(self,request_id):
        for job in self.jobs:
            for row in self.get('/v2/jobs/'+job['id']+'/runs?size=100')['data']:
                tasks=row['attributes'].get('taskRuns',[])
                for task in tasks:
                    if task.get('dotId')=='decode_log' and task.get('output'):
                        value=json.loads(task['output'])
                        if str(value.get('requestId','')).lower()==request_id.lower():return row
        return None


def chainlink_time(value):
    # Go API timestamps carry optional nanoseconds and timezone offsets.
    text=re.sub(r'(\.\d{6})\d+',r'\1',value).replace('Z','+00:00')
    return datetime.fromisoformat(text).timestamp()*1000


def normalization(sample,pairs=None):
    if pairs is None:
        wait('clock bridge',lambda:list(SAMPLES),lambda v:v and v[-1][1]>sample['finished_ms']+2,seconds=2)
        pairs=[v for v in list(SAMPLES) if sample['invoke1']['clock']['rawStart']-200<=v[1]<=sample['finished_ms']+200]
    sample['clockPairs']=pairs
    first=sample['invoke1'];second=sample['invoke2'];start=first['clock']['rawStart'];stop=sample['finished_ms']
    # map_wall uses ISO timestamps. The Chainlink API's nanosecond ISO fields use
    # the same container host wall clock; no block.timestamp precision is used.
    created1=map_wall(sample['operation1']['created'],start,first['clock']['rawEnd'],pairs,'Operation1.created')
    created2=map_wall(sample['operation2']['created'],second['clock']['rawStart'],second['clock']['rawEnd'],pairs,'Operation2.created')
    succeeded1=map_wall(sample['success1']['created'],max(created1,sample.get('success1Bounds',{}).get('lower',created1)),sample.get('success1Bounds',{}).get('upper',sample.get('success1Observed_ms',stop)),pairs,'Operation1 success')
    succeeded2=map_wall(sample['success2']['created'],max(created2,sample.get('success2Bounds',{}).get('lower',created2)),sample.get('success2Bounds',{}).get('upper',sample.get('success2Observed_ms',stop)),pairs,'Operation2 success')
    run=sample['primaryRun']['attributes'];wall=run['createdAt']
    # Normalize standard UTC notation for the shared parser.
    if wall.endswith('+00:00'):wall=wall[:-6]+'Z'
    wall=re.sub(r'\.(\d{1,6})Z$',lambda m:'.'+m.group(1).ljust(6,'0')+'Z',wall)
    job_start=map_wall(wall,start,sample['nodeHttpEvidence'][sample['primaryNode']]['cdmn']['start_ms'],pairs,'Chainlink job createdAt')
    cache=next(v for v in run['taskRuns'] if v['dotId']=='call_cache')
    wall=cache['finishedAt']
    if wall.endswith('+00:00'):wall=wall[:-6]+'Z'
    wall=re.sub(r'\.(\d{1,6})Z$',lambda m:'.'+m.group(1).ljust(6,'0')+'Z',wall)
    cache_end=map_wall(wall,sample['nodeHttpEvidence'][sample['primaryNode']]['cdmn']['end_ms'],sample['resultReadyObserved_ms'],pairs,'Chainlink CDMN response received')
    fulfillment=map_wall(sample['fulfillmentEvent']['created'],max(cache_end,sample.get('fulfillmentBounds',{}).get('lower',cache_end)),sample.get('fulfillmentBounds',{}).get('upper',stop),pairs,'DMN result fulfillment observed by FireFly')
    download=sample['primaryIpfs']
    intervals=[('API Invoker',start,created1),('BPMN SC',created1,succeeded1),
        ('Request to Chainlink job',start,job_start),('Chainlink Executor',job_start,cache_end),
        ('IPFS download',download['start_ms'],download['end_ms']),
        ('Result commit on chain',cache_end,fulfillment),
        ('API Invoker2',second['clock']['rawStart'],created2),('BPMN Continue SC',created2,succeeded2)]
    sample['stages']=[]
    for name,a,b in intervals:
        if b<a:raise ValueError('Invalid/ambiguous time interval: '+name)
        sample['stages'].append({'step':name,'start_time':a-start,'end_time':b-start,'duration_ms':b-a,'valid':True})
    sample['clockPairs']=pairs
    sample['timingMethod']='Local client/container monotonic clocks; host wall/monotonic bridge; read-only CDMN packet observation; Chainlink API task timestamps'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rounds',type=int,default=3)
    parser.add_argument('--max-attempts',type=int,default=300)
    parser.add_argument('--filter-outliers',action='store_true',help='Apply the user-confirmed 25s / 60s limits')
    parser.add_argument('--resume',action='store_true',help='Keep already verified rounds and continue to requested total')
    parser.add_argument('--config',type=Path,default=ROOT/'config.live.json')
    parser.add_argument('--output',type=Path,default=ROOT/'results-3')
    args=parser.parse_args();assert 1<=args.rounds<=100
    cfg=json.loads(args.config.read_text());out=args.output
    assert args.resume or not out.exists() or not any(out.iterdir()),'Choose a new empty results directory or --resume'
    out.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(PROJECT/'src/backend'));os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
    import django;django.setup()
    from apps.core.models import BPMNInstance
    core,api=cfg['core'],cfg['api'];observers=[]
    report={'platform':'geth','status':'running','requestedRounds':args.rounds,'config':cfg,'samples':[],
        'attemptCount':0,'excluded':[],
        'outlierThresholds_ms':OUTLIER_THRESHOLDS_MS if args.filter_outliers else {},
        'pipeline':'Unmodified generated BPMN → existing DMN Lite → Chainlink directrequest → CDMN/IPFS → commitBaselineFromRaw → BPMN Continue',
        'notes':['Includes real existing Chainlink jobs; not a Fabric-style substitute executor',
                 'Request to Chainlink job overlaps initial API/chain transaction; other nested intervals must not be summed',
                 'IPFS is observed on the actual CDMN worker that first committed a valid result',
                 'BPMN Continue SC is final workflow application; DMN calculation occurs off-chain in CDMN']}
    if args.resume:
        previous=load_report(out/'results.json')
        assert previous['config']==cfg and previous['requestedRounds']==args.rounds
        assert previous.get('outlierThresholds_ms',{})==report['outlierThresholds_ms'],'Filtering policy changed'
        report['samples']=previous['samples']
        report['attemptCount']=previous.get('attemptCount',len(report['samples']))
        report['excluded']=previous.get('excluded',[])
        for key in ['sampleFiles','excludedCounts','cleanup','policyHistory']:
            if key in previous:report[key]=previous[key]
        if (out/'active-round.json').exists():
            old=json.loads((out/'active-round.json').read_text())
            save(out/'diagnostics'/('instance-'+str(old['instanceId'])+'.json'),old)
            (out/'active-round.json').unlink()
    active=None
    try:
        nodes=[Node(port) for port in cfg['chainlink_ports']]
        for name in cfg['cdmn_containers']:observers.append(Observer(name,out))
        # Dedicated, fully typed observation listener. Existing environment
        # listeners may have params=null; never alter them or infer their times.
        interface=request('GET',cfg['dmn_api']+'/interface')
        event=next(v for v in interface['events'] if v['name']=='RequestFulfilled')
        listener_name='GethBrtTiming-RequestFulfilled-'+cfg['contract_address'][-6:]
        listeners=request('GET',core+'/contracts/listeners?limit=1000')
        listener=next((v for v in listeners if v['name']==listener_name),None)
        if listener is None:
            listener=request('POST',core+'/contracts/listeners',json={
                'name':listener_name,'topic':listener_name,'location':{'address':cfg['dmn_address']},
                'event':{'name':event['name'],'params':event['params']},
                'options':{'firstEvent':'newest'}})
        assert listener['signature']=='RequestFulfilled(bytes32,uint256)',listener
        report['fulfillmentListener']=listener
        dmn=Path(cfg['dmn_file']).read_bytes();sha=hashlib.sha256(dmn).hexdigest()
        upload=request('POST',core+'/data',data={'autometa':'true'},files={'file':('timing-rule.dmn',dmn,'application/xml')})
        publication=request('POST',core+'/data/'+upload['id']+'/blob/publish',json={});cid=publication['blob']['public'];assert cid
        report['dmnPublication']={'dataId':upload['id'],'cid':cid,'bytes':len(dmn),'sha256':sha}
        report['observerStartup']={v.name:v.startup for v in observers}
        owner=unwrap(query(api,'owner'));org=request('GET',core+'/status')['org']['name']
        params={'identityContractAddress':cfg['identity_address'],'dmnLiteAddress':cfg['dmn_address'],
            'dmnEvalUrl':cfg['dmn_eval_url'],'enforceBusinessRuleCaller':False,
            'Participant_A_account':owner,'Participant_A_org':org,'Participant_B_account':owner,'Participant_B_org':org,
            'Activity_timingbrt':{'dmnCid':cid,'dmnHash':keccak(cfg,dmn),'decisionId':cfg['decision_id'],
                'callerRestricted':False,'allowedCaller':owner}}
        # Verify enough existing LINK before invoking any measured request.
        env_dmn=json.loads((ROOT/'deployment/deployment.json').read_text())
        from apps.environment.models import EthEnvironment
        token=EthEnvironment.objects.get(pk=env_dmn['environmentId']).dmn_detail['linkToken']
        selector=keccak(cfg,b'balanceOf(address)')[:10]
        balance=int(rpc(cfg,'eth_call',[{'to':token,'data':selector+cfg['dmn_address'][2:].rjust(64,'0')},'latest']),16)
        assert balance>=(args.rounds-len(report['samples']))*10**17,'Existing DMN Lite requires more LINK before measurement'
        report['linkBalanceBefore']=str(balance)
        def exclude(sample,category,reason):
            sample.update(status='excluded',exclusionCategory=category,exclusionReason=reason)
            path=out/'excluded'/('attempt-'+str(sample['attempt']))/'result.json'
            save(path,sample)
            report['excluded'].append({'attempt':sample['attempt'],'instanceId':sample['instanceId'],
                'category':category,'reason':reason,'record':str(path.relative_to(out))})
            (out/'active-round.json').unlink(missing_ok=True)
            export(report,out)
            print(f"Attempt {sample['attempt']} excluded ({category}): {reason}; valid {len(report['samples'])}/{args.rounds}",flush=True)
        while len(report['samples'])<args.rounds:
            if report['attemptCount']>=args.max_attempts:raise RuntimeError('Maximum attempt count reached; inspect exclusions before resuming')
            report['attemptCount']+=1
            index=len(report['samples'])+1
            instance=int(unwrap(query(api,'currentInstanceId')))
            print(f'Round {index}: initialize instance {instance} outside timing',flush=True)
            invoke(cfg,'createInstance',{'params':params});invoke(cfg,cfg['start_method'],{'instanceId':instance})
            before=query(api,'getExecutionSnapshot',{'instanceId':instance});assert [int(v) for v in before['businessRuleStates']]==[1]
            before_storage=approval_storage(cfg,instance);assert before_storage['approved'] is False
            db=BPMNInstance.objects.create(bpmn_id=cfg['bpmn_id'],instance_chaincode_id=instance,name='Geth BRT timing '+str(instance))
            active={'index':index,'attempt':report['attemptCount'],'instanceId':instance,'databaseInstanceId':str(db.id),'status':'running',
                'snapshotBefore':before,'approvalBefore':before_storage}
            save(out/'active-round.json',active)
            # Timed HTTP request interval matches the existing Message client.
            def call_timed(method):
                value=timed_post(api+'/invoke/'+method,{'input':{'instanceId':instance}})
                value['clock']={'rawStart':value['start_ms'],'rawEnd':value['end_ms']}
                return value
            active['invoke1']=call_timed(cfg['rule_method']);save(out/'active-round.json',active)
            seen=observe_success(core,active['invoke1']['value'],active['invoke1']['start_ms'])
            active['success1']=seen['event'];active['success1Bounds']=seen['bounds'];active['success1Observed_ms']=seen['bounds']['upper']
            active['operation1']=operation(core,active['invoke1']['value']['id'])
            snap=query(api,'getExecutionSnapshot',{'instanceId':instance});request_id=snap['businessRuleRequestIds'][0]
            assert request_id!='0x'+'0'*64;active['requestId']=request_id;save(out/'active-round.json',active)
            print(f'Round {index}: real Chainlink request {request_id}; wait for committed result',flush=True)
            def dmn_status():return query(cfg['dmn_api'],'getRequestStatus',{'requestId':request_id})
            observed={};last_absence=mono();topic=keccak(cfg,b'RequestFulfilled(bytes32,uint256)')
            def observe_result():
                nonlocal last_absence
                before=mono()
                chains=request('GET',core+'/blockchainevents',params={'listener':listener['id'],'limit':1000})
                for chain in chains:
                    if str(chain.get('output',{}).get('requestId','')).lower()!=request_id.lower():continue
                    txhash=chain.get('tx',{}).get('blockchainId','').lower()
                    if txhash in observed:continue
                    rows=request('GET',core+'/events',params={'reference':chain['id'],'limit':1000})
                    matches=[v for v in rows if v['type']=='blockchain_event_received' and v.get('reference')==chain['id']]
                    if matches:observed[txhash]={'chain':chain,'event':matches[0],'bounds':{'lower':last_absence,'upper':mono()}}
                last_absence=before
                status=dmn_status()
                if int(status['state'])!=2 or not status['exists']:return None
                assert status['requester'].lower()==cfg['contract_address'].lower()
                logs=rpc(cfg,'eth_getLogs',[{'address':cfg['dmn_address'],'fromBlock':'0x0','toBlock':'latest','topics':[topic,request_id]}])
                logs.sort(key=lambda v:(int(v['blockNumber'],16),int(v['logIndex'],16)))
                if logs and logs[0]['transactionHash'].lower() in observed:
                    active['fulfillmentObservation']=observed[logs[0]['transactionHash'].lower()]
                    return status
            active['requestStatus']=wait('Chainlink DMN fulfillment and directly observed event',observe_result,bool,seconds=600)
            active['resultReadyObserved_ms']=mono()
            active['rawDmnResult']=unwrap(query(cfg['dmn_api'],'getRawByRequestId',{'requestId':request_id}))
            raw=json.loads(active['rawDmnResult']);assert raw and raw[0].get('approved') is True,raw
            active['invoke2']=call_timed(cfg['rule_method']+'_Continue');save(out/'active-round.json',active)
            seen=observe_success(core,active['invoke2']['value'],active['invoke2']['start_ms'])
            active['success2']=seen['event'];active['success2Bounds']=seen['bounds'];active['success2Observed_ms']=seen['bounds']['upper']
            active['operation2']=operation(core,active['invoke2']['value']['id'])
            active['snapshotAfter']=query(api,'getExecutionSnapshot',{'instanceId':instance})
            active['approvalAfter']=approval_storage(cfg,instance)
            assert active['approvalAfter']['approved'] is True
            assert [int(v) for v in active['snapshotAfter']['businessRuleStates']]==[3]
            # Select the actual first on-chain writer, not whichever node is faster
            # to answer our diagnostic API request.
            topic=keccak(cfg,b'RequestFulfilled(bytes32,uint256)')
            logs=rpc(cfg,'eth_getLogs',[{'address':cfg['dmn_address'],'fromBlock':'0x0','toBlock':'latest','topics':[topic,request_id]}])
            assert logs,'No real RequestFulfilled log'
            logs.sort(key=lambda v:(int(v['blockNumber'],16),int(v['logIndex'],16)))
            active['fulfillmentLogs']=logs
            tx=rpc(cfg,'eth_getTransactionByHash',[logs[0]['transactionHash']]);active['firstFulfillmentTransaction']=tx
            primary=next(i for i,n in enumerate(nodes) if tx['from'].lower() in n.addresses)
            active['primaryNode']=cfg['cdmn_containers'][primary]
            active['chainlinkRuns']={}
            for i,node in enumerate(nodes):
                run=node.find_run(request_id)
                if run:active['chainlinkRuns'][cfg['cdmn_containers'][i]]=run
            if cfg['cdmn_containers'][primary] not in active['chainlinkRuns']:
                active['chainlinkRuns'][cfg['cdmn_containers'][primary]]=wait('matching Chainlink run',lambda:nodes[primary].find_run(request_id),bool)
            active['primaryRun']=active['chainlinkRuns'][cfg['cdmn_containers'][primary]]
            active['nodeHttpEvidence']={}
            for i,observer in enumerate(observers):
                records=[v for v in observer.rows if v.get('kind')=='cdmn' and
                    str(v.get('output',{}).get('requestId','')).lower()==request_id.lower()]
                if not records:continue
                calc=records[0]
                downloads=[v for v in observer.rows if v.get('kind')=='ipfs' and v.get('cid')==cid
                    and calc['start_ms']<=v['start_ms']<=v['end_ms']<=calc['end_ms']]
                assert len(downloads)==1,(observer.name,downloads)
                assert downloads[0]['status']==200 and downloads[0]['response_sha256']==sha
                assert calc['status']==200 and calc['output']['ok'] is True
                active['nodeHttpEvidence'][observer.name]={'cdmn':calc,'ipfs':downloads[0]}
            assert active['primaryNode'] in active['nodeHttpEvidence'],'Missing real primary IPFS network trace'
            active['primaryIpfs']=active['nodeHttpEvidence'][active['primaryNode']]['ipfs']
            observation=active['fulfillmentObservation']
            assert observation['chain']['tx']['blockchainId'].lower()==logs[0]['transactionHash'].lower()
            active['fulfillmentEvent']=observation['event'];active['fulfillmentBlockchainEvent']=observation['chain']
            active['fulfillmentBounds']=observation['bounds']
            active['executionVerified']=True;active['finished_ms']=mono()
            try:normalization(active)
            except ValueError as exc:
                if not str(exc).startswith(('Invalid clock mapping:','Invalid/ambiguous time interval:')):raise
                exclude(active,'clock',str(exc));active=None
                continue
            violations=[{'step':v['step'],'duration_ms':v['duration_ms'],'limit_ms':report['outlierThresholds_ms'][v['step']]}
                for v in active['stages'] if v['step'] in report['outlierThresholds_ms'] and v['duration_ms']>report['outlierThresholds_ms'][v['step']]]
            if violations:
                active['thresholdViolations']=violations
                exclude(active,'latency_threshold',json.dumps(violations));active=None
                continue
            active['status']='passed';report['samples'].append(active)
            save(out/f'round-{index}'/'result.json',active);export(report,out);active=None
            (out/'active-round.json').unlink()
            print(f'Round {index} verified: actual Chainlink/CDMN result persisted in generated BPMN storage',flush=True)
        report['status']='passed'
    except Exception as exc:
        report['status']='failed';report['error']=str(exc)
        if active:active.update(status='failed',error=str(exc));save(out/'active-round.json',active)
        raise
    finally:
        for observer in observers:observer.stop()
        export(report,out)


def export(report,out):
    import csv
    report['summary']=[]
    for name in PHASES:
        values=[next(v['duration_ms'] for v in s['stages'] if v['step']==name) for s in report['samples']]
        if values:report['summary'].append({'step':name,'count':len(values),'mean_ms':mean(values),'median_ms':median(values),'min_ms':min(values),'max_ms':max(values)})
    totals=[next(v['end_time'] for v in s['stages'] if v['step']=='BPMN Continue SC') for s in report['samples']]
    if totals:report['endToEnd']={'definition':'First BRT request start to final Continue success event',
        'count':len(totals),'mean_ms':mean(totals),'min_ms':min(totals),'max_ms':max(totals)}
    persisted=dict(report)
    if 'sampleFiles' in persisted:
        assert len(persisted['sampleFiles'])==len(report['samples'])
        persisted.pop('samples')
    save(out/'results.json',persisted);save(out/'summary.json',report['summary'])
    with (out/'timings.csv').open('w',newline='') as f:
        writer=csv.writer(f,lineterminator='\n');writer.writerow(['round','instanceId','stage','start_ms','end_ms','duration_ms'])
        for s in report['samples']:
            for v in s['stages']:writer.writerow([s['index'],s['instanceId'],v['step'],v['start_time'],v['end_time'],v['duration_ms']])
    text=['# Geth BusinessRule 真实 Chainlink 链路测量','',f"状态：{report['status']}；有效轮次：{len(report['samples'])}。",'',
        '| 阶段 | 均值(ms) | 中位数(ms) | 最小(ms) | 最大(ms) |','|---|---:|---:|---:|---:|']
    for v in report['summary']:text.append(f"| {PHASE_LABELS[v['step']]} | {v['mean_ms']:.2f} | {v['median_ms']:.2f} | {v['min_ms']:.2f} | {v['max_ms']:.2f} |")
    if report.get('outlierThresholds_ms'):text+=['',f"阈值（ms，严格大于才排除）：{json.dumps(report['outlierThresholds_ms'],ensure_ascii=False)}。",f"累计尝试：{report.get('attemptCount',0)}；排除：{excluded_count(report)}。排除样本不计入下表；归档清理后仅保留分类计数。"]
    if len(report['samples'])<=10:
        text+=['','## 逐轮数据（ms）','','| 阶段 | '+' | '.join('第 '+str(v['index'])+' 轮' for v in report['samples'])+' |',
               '|---|'+''.join('---:|' for _ in report['samples'])]
        for name in PHASES:
            text.append('| '+PHASE_LABELS[name]+' | '+' | '.join(f"{next(v['duration_ms'] for v in sample['stages'] if v['step']==name):.2f}" for sample in report['samples'])+' |')
        if totals:text.append('| 端到端 | '+' | '.join(f'{v:.2f}' for v in totals)+' |')
    else:
        text+=['','逐轮阶段明细见 [timings.csv](timings.csv)，各轮完整原始证据见 `round-*/result.json`。']
    if report.get('validationObservationNotes'):text+=['',report['validationObservationNotes']]
    if totals:text+=['',f"端到端（首次请求至 Continue 成功事件）均值：{mean(totals):.2f} ms。"]
    text+=['','阶段名称明确区分 DMN 请求、链下规则执行、规则文件下载、结果回写和 BPMN 应用结果。Executor 包含 DMN 下载与计算，尚未单独计量纯规则计算耗时。', '', 'Request to Chainlink job从首次业务请求开始，包含前面的API/链上等待，与其重叠；不是Fabric的Event Bus指标。',
        'Chainlink Executor从实际获胜节点的Job创建至其CDMN HTTP调用返回。Result commit on chain包含其后提交结果、交易确认与FireFly事件记录。',
        'IPFS为该实际CDMN节点内部GET请求的只读网络观测，完整响应字节与原DMN哈希一致；不是脚本额外发起的替代下载。',
        '最终BPMN Continue SC只读取已回链结果并更新流程；DMN实际计算在链下CDMN，不能与Fabric链内DMN SC直接等同。']
    (out/'RESULTS.md').write_text('\n'.join(text)+'\n')


if __name__=='__main__':main()
