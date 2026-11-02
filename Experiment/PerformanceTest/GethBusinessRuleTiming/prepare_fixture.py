#!/usr/bin/env python3
"""Generate and deploy an isolated Geth BRT contract without editing business code."""
import json
import os
from pathlib import Path
import sys
import hashlib
import time
import subprocess
from datetime import datetime
import requests

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[2]


def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix('.tmp')
    tmp.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');tmp.replace(p)


def req(method,url,**kwargs):
    r=requests.request(method,url,timeout=300,**kwargs)
    if not r.ok:raise RuntimeError(f'{method} {url}: {r.status_code} {r.text}')
    return r.json()


def wait_get(url):
    deadline=time.monotonic()+180
    while time.monotonic()<deadline:
        r=requests.get(url,timeout=20)
        if r.ok:return r.json()
        if r.status_code!=404:r.raise_for_status()
        time.sleep(.2)
    raise TimeoutError(url)


def main():
    sys.path.insert(0,str(PROJECT/'src/backend'));os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
    import django;django.setup()
    from apps.environment.models import EthEnvironment
    from apps.core.models import BPMN
    from apps.ethereum.models import EthereumContract
    from apps.core.services.new_translator import NewTranslatorClient
    from common.lib.ethereum.solc_compiler import SolidityCompiler
    env=EthEnvironment.objects.get(status='ACTIVATED')
    org=env.resource_sets.first().membership.loleido_organization
    folder=ROOT/'deployment';folder.mkdir(exist_ok=True);path=folder/'deployment.json'
    state=json.loads(path.read_text()) if path.exists() else {'environmentId':str(env.id),'name':'GethBrtTiming'+datetime.now().strftime('%m%d%H%M%S')}
    assert state['environmentId']==str(env.id),'Environment changed'
    core='http://127.0.0.1:5002/api/v1/namespaces/default'
    reference=ROOT.parent/'FabricBusinessRuleTiming/deployment'
    if not (folder/'contract.sol').exists():
        bpmn=(reference/'BusinessRuleTiming.bpmn').read_text()
        generated=NewTranslatorClient().generate_artifacts(bpmn,'solidity',artifact_name=state['name'],persist_to_runtime=False)
        (folder/'model.bpmn').write_text(bpmn);(folder/'contract.sol').write_text(generated['chaincodeContent'])
        (folder/'rule.dmn').write_bytes((reference/'rule.dmn').read_bytes())
        save(folder/'execution-layout.json',generated['executionLayout'])
    if not (folder/'compiled.json').exists():
        compiler=SolidityCompiler();code,data,error=compiler.compile_contract(str(folder/'contract.sol'))
        if code:raise RuntimeError(error)
        save(folder/'compiled.json',data)
    if not (folder/'storage-layout.json').exists():
        spec={'language':'Solidity','sources':{'contract.sol':{'content':(folder/'contract.sol').read_text()}},
            'settings':{'outputSelection':{'*':{'*':['storageLayout']}}}}
        result=subprocess.run(['solc','--standard-json'],input=json.dumps(spec),text=True,capture_output=True,check=True)
        save(folder/'storage-layout.json',json.loads(result.stdout))
    compiled=json.loads((folder/'compiled.json').read_text())
    candidates=[(k,v) for k,v in compiled['contracts'].items() if v.get('bin')]
    assert len(candidates)==1
    contract_name,artifact=candidates[0];abi=artifact['abi'];abi=json.loads(abi) if isinstance(abi,str) else abi
    save(folder/'abi.json',abi)
    if 'deployResponse' not in state:
        print('Deploy generated BRT contract',flush=True)
        state['deployResponse']=req('POST',core+'/contracts/deploy?confirm=true',json={
            'contract':'0x'+artifact['bin'],'definition':abi,'input':['0x0000000000000000000000000000000000000000']})
        save(path,state)
    response=state['deployResponse'];print('Deployment response fields',list(response),flush=True)
    address=response.get('contractLocation',{}).get('address') or response.get('location',{}).get('address') or response.get('address')
    if not address:
        oid=response.get('id')
        op=req('GET',core+'/operations/'+oid);save(folder/'deploy-operation.json',op)
        address=op.get('output',{}).get('contractLocation',{}).get('address') or op.get('output',{}).get('contractAddress')
    assert address, response
    state['contractAddress']=address
    name=state['name']+'-'+address[-6:]
    interfaces=req('GET',core+'/contracts/interfaces?limit=1000')
    interface=next((v for v in interfaces if v['name']==name),None)
    if interface is None:
        ffi=req('POST',core+'/contracts/interfaces/generate',json={'name':name,'version':'1.0','input':{'abi':abi}})
        save(folder/'ffi.json',ffi)
        interface=req('POST',core+'/contracts/interfaces',json=ffi)
    wait_get(core+'/contracts/interfaces/'+interface['id'])
    api=next((v for v in req('GET',core+'/apis') if v['name']==name),None)
    if api is None:api=req('POST',core+'/apis',json={'name':name,'interface':{'id':interface['id']},'location':{'address':address}})
    state['api']=core+'/apis/'+name;state['interfaceId']=interface['id'];save(path,state)
    wait_get(state['api']+'/interface')
    def unwrap(v):return next(iter(v.values())) if isinstance(v,dict) and len(v)==1 else v
    if not unwrap(req('POST',state['api']+'/query/isInited',json={'input':{}})):
        if 'initOperationId' not in state:
            op=req('POST',state['api']+'/invoke/initLedger',json={'input':{}});state['initOperationId']=op['id'];save(path,state)
        deadline=time.monotonic()+180
        while time.monotonic()<deadline:
            op=req('GET',core+'/operations/'+state['initOperationId'])
            if op['status']=='Succeeded':break
            if op['status']=='Failed':raise RuntimeError(json.dumps(op))
            time.sleep(.2)
        else:raise TimeoutError('initLedger')
    c,_=EthereumContract.objects.get_or_create(contract_address=address,defaults={'name':state['name'],'creator':org,
        'eth_environment':env,'language':'solidity','version':'1.0','contract_content':(folder/'contract.sol').read_text(),
        'abi':abi,'bytecode':artifact['bin'],'status':'Deployed','filename':state['name']+'.sol'})
    b,_=BPMN.objects.get_or_create(ethereum_contract=c,defaults={'name':state['name']+'.bpmn','organization':org,
        'consortium':env.consortium,'eth_environment':env,'status':'Registered','bpmnContent':(folder/'model.bpmn').read_text(),
        'svgContent':'<svg xmlns="http://www.w3.org/2000/svg" width="600" height="100"><text x="20" y="50">Start → Geth BusinessRule → End</text></svg>',
        'chaincode_content':(folder/'contract.sol').read_text(),'ffiContent':json.dumps(wait_get(state['api']+'/interface')),
        'firefly_url':state['api'],'execution_layout':json.loads((folder/'execution-layout.json').read_text())})
    state['bpmnId']=str(b.id);state['sourceSha256']=hashlib.sha256((folder/'contract.sol').read_bytes()).hexdigest();save(path,state)
    # The current environment uses DMN Lite with real Chainlink directrequest jobs.
    d=env.dmn_detail
    save(ROOT/'config.live.json',{'core':core,'api':state['api'],'contract_address':address,'bpmn_id':str(b.id),
        'identity_address':env.identity_deployment.contract_address,'dmn_address':d['contractAddress'],
        'dmn_api':d['firefly_api_base'],'ipfs_gateway':'http://127.0.0.1:10207',
        'dmn_file':str((folder/'rule.dmn').resolve()),'rule_method':'Activity_timingbrt','start_method':'Event_brtStart',
        'decision_id':'Decision_timing','dmn_eval_url':'http://cdmn-node1:5000/api/dmn/calc',
        'chainlink_ports':[6688,6689,6691,6692],'cdmn_containers':['cdmn-node1','cdmn-node2','cdmn-node3','cdmn-node4'],
        'rpc_url':'http://127.0.0.1:20313'})
    print('Generated contract deployed and registered:',address,flush=True)


if __name__=='__main__':main()
