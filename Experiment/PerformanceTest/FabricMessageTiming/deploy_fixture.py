#!/usr/bin/env python3
"""Deploy the saved generator-produced Fabric file fixture as a separate chaincode.

Uses existing backend lifecycle endpoints and a persistent step manifest. Never
overwrites the project's chaincode template, existing BPMNs or chaincodes.
Run from project root using src/backend/venv/bin/python.
"""
import argparse
import base64
from datetime import datetime
import json
import os
from pathlib import Path
import sys
import time
from urllib.parse import quote
import requests

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]


def save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=['package', 'install', 'approve', 'commit', 'register', 'initialize', 'all'], default='all')
    parser.add_argument('--source-port', type=int, default=5002)
    parser.add_argument('--receiver-port', type=int, default=5001)
    parser.add_argument('--gateway', default='http://127.0.0.1:10607')
    parser.add_argument('--key', default='user1')
    args = parser.parse_args()
    sys.path.insert(0, str(PROJECT/'src/backend'))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    import django
    django.setup()
    from apps.core.models import BPMN, BPMNInstance
    from apps.fabric.models import ChainCode, FabricIdentity
    from apps.environment.models import Environment
    from apps.environment.routes.environment.utils import (
        packageChaincodeForEnv, installChaincodeForEnv, approveChaincodeForEnv, commmitChaincodeForEnv)
    from rest_framework_simplejwt.tokens import AccessToken

    folder = ROOT/'deployment'; manifest = folder/'deployment.json'
    if manifest.exists():
        state = json.loads(manifest.read_text())
        env = Environment.objects.get(pk=state['environmentId'])
        owner = BPMN.objects.get(pk=state['ownerBpmnId'])
    else:
        env = Environment.objects.get(status='ACTIVATED')
        owner = BPMN.objects.filter(environment=env, status='Registered').first()
        assert owner, 'An existing environment BPMN is required to resolve owner/consortium'
        state = {'environmentId': str(env.id), 'ownerBpmnId': str(owner.id),
                 'name': 'FabricFileTiming'+datetime.now().strftime('%m%d%H%M%S'), 'completed': []}
        save(manifest, state)
    user = owner.organization.members.filter(is_active=True).first()
    assert user, 'No active owner user'
    auth = lambda: 'JWT '+str(AccessToken.for_user(user))
    core = f'http://127.0.0.1:{args.source_port}/api/v1/namespaces/default'
    receiver = f'http://127.0.0.1:{args.receiver_port}/api/v1/namespaces/default'

    def request(method, url, **kwargs):
        r = requests.request(method, url, timeout=300, **kwargs)
        if not r.ok:
            raise RuntimeError(f'{method} {url}: {r.status_code} {r.text}')
        return r.json()

    def wait_get(url):
        deadline = time.monotonic()+120
        while time.monotonic() < deadline:
            r = requests.get(url, timeout=30)
            if r.ok:
                return r.json()
            if r.status_code != 404:
                r.raise_for_status()
            time.sleep(.25)
        raise TimeoutError(url)

    def invoke(method, inputs, field):
        api = state['api']
        if field not in state:
            op = request('POST', api+'/invoke/'+method, json={'key': args.key, 'input': inputs})
            state[field] = op['id']; save(manifest, state)
        deadline = time.monotonic()+300
        while time.monotonic() < deadline:
            op = request('GET', core+'/operations/'+state[field]+'?fetchstatus=true')
            if op['status'] == 'Failed':
                raise RuntimeError(json.dumps(op))
            if op['status'] == 'Succeeded':
                return op
            time.sleep(.25)
        raise TimeoutError(method)

    stages = ['package', 'install', 'approve', 'commit', 'register', 'initialize']
    selected = stages if args.stage == 'all' else [args.stage]
    for stage in selected:
        if stage in state['completed']:
            print('Already completed:', stage, flush=True)
            continue
        assert stages.index(stage) == len(state['completed']), 'Run lifecycle stages in order'
        print('Starting:', stage, flush=True)
        if stage == 'package':
            state['chaincodeId'] = packageChaincodeForEnv(str(env.id), str(folder/'FabricFileTiming.zip'),
                state['name'], '1.0', str(owner.organization_id), auth())
        elif stage == 'install':
            installChaincodeForEnv(str(env.id), state['chaincodeId'], auth())
        elif stage == 'approve':
            approveChaincodeForEnv(str(env.id), 'default', state['name'], auth())
        elif stage == 'commit':
            commmitChaincodeForEnv(str(env.id), 'default', state['name'], auth())
        elif stage == 'register':
            ffi = json.loads((folder/'ffi.json').read_text())
            api_name = state['name']+'-'+state['chaincodeId'][:6]
            ffi['name'] = api_name
            interfaces = request('GET', core+'/contracts/interfaces?limit=1000')
            interface = next((v for v in interfaces if v['name'] == api_name), None)
            if interface is None:
                interface = request('POST', core+'/contracts/interfaces', json=ffi)
            wait_get(core+'/contracts/interfaces/'+interface['id'])
            apis = request('GET', core+'/apis')
            api = next((v for v in apis if v['name'] == api_name), None)
            if api is None:
                api = request('POST', core+'/apis', json={'name': api_name,
                    'interface': {'id': interface['id']}, 'location': {'channel': 'default', 'chaincode': state['name']}})
            state['api'] = core+'/apis/'+api_name
            state['interfaceId'] = interface['id']; state['apiId'] = api['id']
            save(manifest, state)
            wait_get(state['api']+'/interface')
        elif stage == 'initialize':
            invoke('InitLedger', {}, 'initOperationId')
            statuses = {name: request('GET', url+'/status') for name, url in [('source', core), ('receiver', receiver)]}
            recipient = statuses['receiver']['org']['did']
            # Bind the sender to its exact enrolled certificate verifier.
            identity = request('GET', core+'/identities/'+quote('did:firefly:'+args.key, safe=''))
            verifiers = request('GET', core+'/identities/'+identity['id']+'/verifiers')
            verifier = next(v['value'] for v in verifiers if v['type'] == 'fabric_msp_id')
            msp, x509 = verifier.split('::', 1)
            sender = {'MSP': msp, 'Attributes': {}, 'X509': base64.b64encode(x509.encode()).decode()+'@'+msp,
                      'IsMulti': False}
            receiver_msp = statuses['receiver']['org']['verifiers'][0]['value'].split('::', 1)[0]
            parameters = {'Participant_0w6qkdf': sender,
                          'Participant_19mgbdn': {'MSP': receiver_msp, 'Attributes': {}, 'IsMulti': True}}
            invoke('CreateInstance', {'initParametersBytes': json.dumps(parameters)}, 'createOperationId')
            # Fresh standalone chaincode has its first instance at 0; verify it.
            response = request('POST', state['api']+'/query/GetAllMessages', json={'input': {'InstanceID': '0'}})
            save(folder/'initialized-message.json', response)
            invoke('Event_06sexe6', {'InstanceID': '0'}, 'startOperationId')
            code = (folder/'smartcontract.go').read_text()
            bpmn, _ = BPMN.objects.get_or_create(chaincode_id=state['chaincodeId'], defaults={
                'organization': owner.organization, 'consortium': owner.consortium, 'environment': env,
                'name': state['name']+'.bpmn', 'status': 'Registered',
                'bpmnContent': (folder/'FabricFileTiming.bpmn').read_text(),
                'svgContent': '<svg xmlns="http://www.w3.org/2000/svg" width="700" height="160"><circle cx="40" cy="80" r="18" fill="white" stroke="black"/><path d="M58 80H170 M410 80H540" stroke="black"/><rect x="170" y="40" width="240" height="80" rx="8" fill="white" stroke="black"/><text x="185" y="75">Repeatable file Message</text><text x="185" y="100">orderDetails (file)</text><circle cx="560" cy="80" r="18" fill="white" stroke="black"/></svg>',
                'chaincode_content': code, 'ffiContent': json.dumps(ffi) if 'ffi' in locals() else (folder/'ffi.json').read_text(),
                'firefly_url': state['api']+'/api',
                'participants': json.dumps([{'id':'Participant_0w6qkdf','name':'Bulk buyer'},
                                            {'id':'Participant_19mgbdn','name':'Manufacturer'}]),
                'events': 'Message_1wswgqu,InstanceCreated'})
            instance, _ = BPMNInstance.objects.get_or_create(bpmn=bpmn, instance_chaincode_id=0,
                defaults={'name':'Repeatable file Message timing'})
            state['bpmnId'] = str(bpmn.id); state['instanceId'] = str(instance.id)
            state['instanceChaincodeId'] = '0'
            cfg = {'source_core': core, 'receiver_core': receiver, 'api': state['api'],
                'ipfs_gateway': args.gateway, 'instance_id': '0', 'message_id': 'Message_1wswgqu',
                'recipient': recipient, 'key': args.key, 'file_field': 'orderDetails', 'poll_ms': 250}
            ffi_methods = json.loads((folder/'ffi.json').read_text())['methods']
            send = next(m for m in ffi_methods if m['name'] == 'Message_1wswgqu_Send')
            request_parameter = next(p['name'] for p in send['params'] if p['name'].lower() == 'requestid')
            cfg['values'] = {'requestId': 1}; cfg['contract_input'] = {request_parameter: 1}
            save(ROOT/'config.live.json', cfg)
        state['completed'].append(stage); save(manifest, state)
        print('Completed:', stage, flush=True)


if __name__ == '__main__':
    main()
