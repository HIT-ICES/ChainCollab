#!/usr/bin/env python3
"""Generate/deploy a separate unmodified BRT fixture using current Fabric env."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from datetime import datetime
from timing_utils import ROOT, PROJECT, request, operation, wait, save

BPMN_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<bpmn2:definitions xmlns:bpmn2="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:abc="https://chaincollab.io/schema/abc" id="Definitions_brtTiming" targetNamespace="http://chaincollab.io/experiment">
 <bpmn2:choreography id="Choreography_brtTiming">
  <bpmn2:participant id="Participant_A" name="Requester"/>
  <bpmn2:participant id="Participant_B" name="Reviewer"/>
  <bpmn2:startEvent id="Event_brtStart"><bpmn2:outgoing>Flow_startBrt</bpmn2:outgoing></bpmn2:startEvent>
  <bpmn2:businessRuleTask id="Activity_timingbrt" name="Score Decision">
   <bpmn2:extensionElements><abc:BusinessRule>
    <abc:Input name="score" type="string" description="Score input" definition='{"name":"score","type":"string"}'/>
    <abc:Output name="approved" type="boolean" description="Decision output" definition='{"name":"approved","type":"boolean"}'/>
   </abc:BusinessRule></bpmn2:extensionElements>
   <bpmn2:incoming>Flow_startBrt</bpmn2:incoming><bpmn2:outgoing>Flow_brtEnd</bpmn2:outgoing>
  </bpmn2:businessRuleTask>
  <bpmn2:sequenceFlow id="Flow_startBrt" sourceRef="Event_brtStart" targetRef="Activity_timingbrt"/>
  <bpmn2:sequenceFlow id="Flow_brtEnd" sourceRef="Activity_timingbrt" targetRef="Event_brtEnd"/>
  <bpmn2:endEvent id="Event_brtEnd"><bpmn2:incoming>Flow_brtEnd</bpmn2:incoming></bpmn2:endEvent>
 </bpmn2:choreography>
</bpmn2:definitions>'''

DMN = '''<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="https://www.omg.org/spec/DMN/20191111/MODEL/" id="Definitions_timing" name="Score decision" namespace="http://chaincollab.io/experiment">
 <decision id="Decision_timing" name="Approve nonnegative score">
  <decisionTable id="Table_timing" hitPolicy="UNIQUE">
   <input id="Input_score" label="score"><inputExpression id="Expression_score" typeRef="string"><text>score</text></inputExpression></input>
   <output id="Output_approved" name="approved" typeRef="boolean"/>
   <rule id="Rule_nonnegative"><inputEntry id="Test_nonnegative"><text>""</text></inputEntry><outputEntry id="Result_true"><text>true</text></outputEntry></rule>
   <rule id="Rule_negative"><inputEntry id="Test_negative"><text>not("")</text></inputEntry><outputEntry id="Result_false"><text>false</text></outputEntry></rule>
  </decisionTable>
 </decision>
</definitions>'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',choices=['generate','package','install','approve','commit','register','all'],default='all')
    parser.add_argument('--core',default='http://127.0.0.1:5000/api/v1/namespaces/default')
    parser.add_argument('--ipfs-gateway',default='http://127.0.0.1:10207')
    args=parser.parse_args()
    sys.path.insert(0,str(PROJECT/'src/backend'));os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
    import django;django.setup()
    from apps.environment.models import Environment
    from apps.core.models import BPMN
    from apps.core.services.new_translator import NewTranslatorClient
    from apps.environment.routes.environment.utils import packageChaincodeForEnv,installChaincodeForEnv,approveChaincodeForEnv,commmitChaincodeForEnv
    from rest_framework_simplejwt.tokens import AccessToken
    folder=ROOT/'deployment';folder.mkdir(exist_ok=True);path=folder/'deployment.json'
    if path.exists():
        state=json.loads(path.read_text());env=Environment.objects.get(pk=state['environmentId'])
    else:
        env=Environment.objects.get(status='ACTIVATED')
        state={'environmentId':str(env.id),'name':'FabricBrtTiming'+datetime.now().strftime('%m%d%H%M%S'),'completed':[]}
        save(path,state)
    org=env.resource_sets.filter(sub_resource_set__org_type=0).first().membership.loleido_organization
    user=org.members.filter(is_active=True).first();assert user
    def auth():
        token=AccessToken.for_user(user)
        # Accommodate small backward wall-clock adjustments while provisioning.
        token['iat']-=30
        return 'JWT '+str(token)
    stages=['generate','package','install','approve','commit','register']
    for stage in stages if args.stage=='all' else [args.stage]:
        if stage in state['completed']:
            print('Already complete:',stage,flush=True);continue
        assert stages.index(stage)==len(state['completed'])
        print('Starting:',stage,flush=True)
        if stage=='generate':
            (folder/'BusinessRuleTiming.bpmn').write_text(BPMN_XML);(folder/'rule.dmn').write_text(DMN)
            generated=NewTranslatorClient().generate_artifacts(BPMN_XML,'go',artifact_name='BusinessRuleTiming',persist_to_runtime=False)
            code=generated['chaincodeContent'];(folder/'generated.go').write_text(code)
            (folder/'model.b2c').write_text(generated['dslContent']);(folder/'ffi.json').write_text(generated['ffiContent'])
            module=folder/'source'/'brt-chaincode';(module/'chaincode').mkdir(parents=True,exist_ok=True)
            (module/'chaincode/smartcontract.go').write_text(code)
            original=PROJECT/'src/backend/opt/chaincode-go-bpmn/chaincode-go-bpmn'
            shutil.copy2(original/'bpmnChoreography.go',module/'main.go');shutil.copy2(original/'go.sum',module/'go.sum')
            (module/'go.mod').write_text((original/'go.mod').read_text().replace('../../../oracle-go','./oracle-go'))
            shutil.copytree(PROJECT/'src/backend/opt/oracle-go',module/'oracle-go',dirs_exist_ok=True)
            (module/'metadata_test.go').write_text('package main\nimport("testing";"chaincode-go-bpmn/chaincode";"github.com/hyperledger/fabric-contract-api-go/contractapi")\nfunc TestMetadata(t *testing.T){if _,e:=contractapi.NewChaincode(&chaincode.SmartContract{});e!=nil{t.Fatal(e)}}\n')
            for cmd in [['go','mod','tidy'],['go','test','./...']]:subprocess.run(cmd,cwd=module,check=True,env={**os.environ,'GOWORK':'off'})
            with zipfile.ZipFile(folder/'fixture.zip','w',zipfile.ZIP_DEFLATED) as archive:
                for p in module.rglob('*'):
                    if p.is_file():archive.write(p,p.relative_to(folder/'source'))
            state['sourceSha256']=hashlib.sha256(code.encode()).hexdigest()
        elif stage=='package':state['chaincodeId']=packageChaincodeForEnv(str(env.id),str(folder/'fixture.zip'),state['name'],'1.0',str(org.id),auth())
        elif stage=='install':installChaincodeForEnv(str(env.id),state['chaincodeId'],auth())
        elif stage=='approve':approveChaincodeForEnv(str(env.id),'default',state['name'],auth())
        elif stage=='commit':commmitChaincodeForEnv(str(env.id),'default',state['name'],auth())
        elif stage=='register':
            core=args.core.rstrip('/');name=state['name']+'-'+state['chaincodeId'][:6]
            ffi=json.loads((folder/'ffi.json').read_text());ffi['name']=name
            interface=next((i for i in request('GET',core+'/contracts/interfaces?limit=1000') if i['name']==name),None)
            if interface is None:interface=request('POST',core+'/contracts/interfaces',json=ffi)
            def ready(url):
                import requests
                r=requests.get(url,timeout=30)
                if r.status_code==404:return None
                r.raise_for_status();return r.json()
            wait('interface',lambda:ready(core+'/contracts/interfaces/'+interface['id']),bool)
            api=next((i for i in request('GET',core+'/apis') if i['name']==name),None)
            if api is None:api=request('POST',core+'/apis',json={'name':name,'interface':{'id':interface['id']},'location':{'channel':'default','chaincode':state['name']}})
            state['api']=core+'/apis/'+name;state['interfaceId']=interface['id'];save(path,state)
            wait('API',lambda:ready(state['api']+'/interface'),bool)
            if 'initOperationId' not in state:
                op=request('POST',state['api']+'/invoke/InitLedger',json={'input':{}});state['initOperationId']=op['id'];save(path,state)
            operation(core,state['initOperationId'])
            event=next(v for v in ffi['events'] if v['name']=='DMNContentRequired')
            listener_name='brt-timing-'+state['chaincodeId'][:8]
            listener=next((i for i in request('GET',core+'/contracts/listeners?limit=1000') if i.get('name')==listener_name),None)
            if listener is None:listener=request('POST',core+'/contracts/listeners',json={'name':listener_name,'interface':{'id':interface['id']},'location':{'channel':'default','chaincode':state['name']},'event':event,'topic':listener_name,'options':{'firstEvent':'newest'}})
            state['listenerId']=listener['id']
            bpmn,_=BPMN.objects.get_or_create(chaincode_id=state['chaincodeId'],defaults={'name':state['name']+'.bpmn','organization':org,'consortium':env.consortium,'environment':env,'status':'Registered','bpmnContent':BPMN_XML,'svgContent':'<svg xmlns="http://www.w3.org/2000/svg" width="600" height="100"><text x="20" y="50">Start → Score Decision (BRT) → End</text></svg>','chaincode_content':(folder/'generated.go').read_text(),'ffiContent':json.dumps(ffi),'firefly_url':state['api']+'/api','participants':'[]','events':''})
            state['bpmnId']=str(bpmn.id)
            save(ROOT/'config.live.json',{'core':core,'api':state['api'],'ipfs_gateway':args.ipfs_gateway,'rule_id':'Activity_timingbrt','decision_id':'Decision_timing','start_method':'Event_brtStart','listener_id':listener['id'],'bpmn_id':str(bpmn.id),'dmn_file':str((folder/'rule.dmn').resolve())})
        state['completed'].append(stage);save(path,state);print('Completed:',stage,flush=True)


if __name__=='__main__':main()
