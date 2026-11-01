#!/usr/bin/env python3
"""Repeat the deployed file Message through the same upload API as the UI.

Run with src/backend/venv/bin/python. No contract deployment or instance creation.
Authentication is generated locally from the BPMN's existing active user; tokens
stay in memory. All three/100 rounds use the same already-enabled chain instance.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import copy
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
from statistics import mean, median
import subprocess
import sys
import threading
import time
from urllib.parse import urlparse
from uuid import uuid4
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
sys.path.insert(0, str(ROOT / 'metric-audit'))
from monotonic_clock import read_clock, normalize, SAMPLES
from audit_metrics import epoch_ms
import requests

PHASES = ['Private Data Bus', 'IPFS', 'API Invoker', 'BPMN SC']


def mono():
    return time.monotonic_ns() / 1e6


def sync():
    before = mono(); value = read_clock(); after = mono()
    return {**value, 'browserBefore': before, 'browserAfter': after,
            'client': 'Python automated HTTP client, monotonic clock'}


def get(url, **kwargs):
    response = requests.get(url, timeout=30, **kwargs)
    response.raise_for_status()
    return response.json()


def post(url, value):
    response = requests.post(url, json=value, timeout=60)
    response.raise_for_status()
    return response.json()


def timed_post(url, timeout=180, started=None, **kwargs):
    # Prepare multipart/JSON outside the measured interval, as the browser does.
    with requests.Session() as session:
        prepared = session.prepare_request(requests.Request('POST', url, **kwargs))
        clock = read_clock(); start = mono()
        if started is not None:
            started.set()
        response = session.send(prepared, timeout=timeout)
        content = response.content
        end = mono()
        response.raise_for_status()
        value = json.loads(content)
        origin = clock['wall_ms'] - clock['monotonic_ms']
        return {'value': value, 'start': origin + start, 'end': origin + end,
                'clock': {'rawStart': start, 'rawEnd': end, 'client': 'Python requests'},
                'httpStatus': response.status_code, 'url': url}


def until(label, fetch, accept, timeout, interval):
    deadline = mono() + timeout * 1000
    while mono() < deadline:
        value = fetch()
        if accept(value):
            return value
        time.sleep(interval)
    raise TimeoutError(f'Timed out waiting for {label}')


def save(path, value):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    temp.replace(path)


def exceeds_red_limit(sample, seconds):
    red = next(v['duration_ms'] for v in sample['stages'] if v['step'] == 'BPMN SC')
    return seconds is not None and red > seconds * 1000


def record_attempt(report, output, sample, reason=None):
    """Keep raw attempts separately; only accepted rounds enter statistics."""
    number = sample['attempt']
    folder = output / 'attempts' / f'attempt-{number:04d}'
    folder.mkdir(parents=True, exist_ok=True)
    red = next((v['duration_ms'] for v in sample.get('stages', []) if v['step'] == 'BPMN SC'), None)
    entry = {'attempt': number, 'candidateRound': sample['index'], 'status': sample['status'],
             'red_ms': red if sample['status'] != 'excluded_invalid_timing' else None,
             'reason': reason, 'messageId': sample.get('messageId'),
             'operationId': sample.get('operation', {}).get('id'),
             'rawFile': str(folder.relative_to(output) / 'result.json')}
    if reason:
        sample['exclusionReason'] = reason
    save(folder / 'result.json', sample)
    report['attempts'].append(entry)
    report['sampleSelection']['totalAttempts'] = len(report['attempts'])
    report['sampleSelection']['acceptedCount'] = len(report['samples'])
    report['sampleSelection']['excludedHighRedCount'] = sum(a['status'] == 'excluded_high_red' for a in report['attempts'])
    report['sampleSelection']['excludedInvalidTimingCount'] = sum(a['status'] == 'excluded_invalid_timing' for a in report['attempts'])
    report['activeAttempt'] = None
    (output / 'active-attempt.json').unlink(missing_ok=True)
    save(output / 'attempts.json', report['attempts'])
    save(output / 'progress.json', {**report['sampleSelection'], 'status': report['status'],
         'lastAttempt': number, 'lastRed_ms': entry['red_ms'],
         'updatedAt': datetime.now(timezone.utc).isoformat()})
    save(output / 'results.json', report)


def setup(args):
    sys.path.insert(0, str(PROJECT / 'src/backend'))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    import django
    django.setup()
    from apps.core.models import BPMN, BPMNInstance
    from apps.ethereum.models import EthereumIdentity
    from apps.core.services.ethereum_message import read_message_schema
    from rest_framework_simplejwt.tokens import AccessToken

    bpmn = BPMN.objects.get(pk=args.bpmn)
    instance = BPMNInstance.objects.get(pk=args.instance, bpmn=bpmn)
    api = bpmn.firefly_url.rstrip('/')
    core = api.split('/apis/')[0]
    chain_id = int(instance.instance_chaincode_id)
    xml = ET.fromstring(bpmn.bpmnContent)
    msg = next(n for n in xml.iter() if n.get('id') == args.message and n.tag.split('}')[-1] == 'message')
    schema = read_message_schema(msg)
    files = schema.get('files', {})
    if len(files) != 1:
        raise ValueError('This runner requires one file field in the target Message')
    field = next(iter(files))
    flow = next(n for n in xml.iter() if n.tag.split('}')[-1] == 'messageFlow' and n.get('messageRef') == args.message)
    binding = instance.execution_bindings['participants'][flow.get('targetRef')]
    identities = EthereumIdentity.objects.filter(eth_environment_id=bpmn.eth_environment_id)
    identity = identities.get(pk=binding['ethereum_identity_id'])
    recipient = get(core + '/identities/' + str(identity.firefly_identity_id))
    recipient_org = recipient
    while recipient_org.get('type') != 'org':
        if not recipient_org.get('parent'):
            raise ValueError('Cannot resolve receiving FireFly organization')
        recipient_org = get(core + '/identities/' + recipient_org['parent'])
    receiver = None
    for port in args.core_ports.split(','):
        candidate = f'http://127.0.0.1:{int(port)}/api/v1/namespaces/default'
        if get(candidate + '/status')['org']['did'] == recipient_org['did']:
            receiver = candidate
    if not receiver or receiver == core:
        raise ValueError('A different receiving FireFly organization must be reachable')
    sender_binding = instance.execution_bindings['participants'][flow.get('sourceRef')]
    signer = args.signer or sender_binding['address']
    user = bpmn.organization.members.filter(is_active=True).first()
    if user is None:
        raise ValueError('No active BPMN user for the existing upload endpoint')
    # A 100-round run can outlive the access-token lifetime. Mint a fresh local
    # token per round without storing credentials or tokens in the report.
    auth_headers = lambda: {'Authorization': 'JWT ' + str(AccessToken.for_user(user))}
    endpoint = (args.backend.rstrip('/') + f'/api/v1/bpmns/{bpmn.id}/bpmn-instances/{instance.id}/prepare-file-message')
    interface = get(api + '/interface')
    methods = {m['name']: m for m in interface['methods']}
    method = args.message + '_Send'
    if method not in methods:
        raise ValueError('Target Message method not in the deployed API')
    if [m for m in methods if m.startswith('Message_') and m.endswith('_Send')] != [method]:
        raise ValueError('This repeated-node runner expects the simple single-Message contract')
    apis = get(core + '/apis')
    registered = next(a for a in apis if a['name'] == api.split('/apis/')[1])
    event = next(e for e in interface['events'] if e['name'] == 'MessageSent')
    listener_name = 'repeat-timing-' + registered['id'][:8]
    listener = next((l for l in get(core + '/contracts/listeners?limit=1000') if l['name'] == listener_name), None)
    if listener is None:
        listener = post(core + '/contracts/listeners', {
            'name': listener_name, 'interface': {'id': registered['interface']['id']},
            'location': registered['location'], 'event': {'name': event['name'], 'params': event['params']},
            'topic': listener_name, 'options': {'firstEvent': 'newest'}})
    gateway = args.ipfs_gateway
    if not gateway:
        # Match the live stack's source-node IPFS service. No container changes.
        index = int(urlparse(core).port) - 5000
        names = subprocess.check_output(['docker', 'ps', '--format', '{{.Names}}'], text=True).splitlines()
        matches = [name for name in names if name.endswith(f'_ipfs_{index}')]
        if len(matches) != 1:
            raise ValueError('Specify --ipfs-gateway for the current source IPFS node')
        mappings = json.loads(subprocess.check_output(['docker', 'inspect', matches[0]], text=True))[0]['NetworkSettings']['Ports']['8080/tcp']
        gateway = 'http://127.0.0.1:' + mappings[0]['HostPort']
    return dict(api=api, core=core, receiver=receiver, chain_id=chain_id, field=field,
                signer=signer, auth_headers=auth_headers, endpoint=endpoint, method=method,
                listener=listener, registered=registered, gateway=gateway,
                recipient=recipient, recipient_org=recipient_org)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rounds', type=int, default=3)
    parser.add_argument('--bpmn', default='f60b4319-9859-4677-9bbb-4443ed227ee1')
    parser.add_argument('--instance', default='49d20d59-cd0a-4169-8a5a-b018355426d8')
    parser.add_argument('--message', default='Message_1wswgqu')
    parser.add_argument('--signer')
    parser.add_argument('--backend', default='http://127.0.0.1:8000')
    parser.add_argument('--core-ports', default='5000,5001,5002')
    parser.add_argument('--ipfs-gateway')
    parser.add_argument('--file', type=Path)
    parser.add_argument('--timeout', type=float, default=300)
    parser.add_argument('--poll-ms', type=int, default=250)
    parser.add_argument('--max-red-seconds', type=float, help='Exclude red durations above this threshold and replace until --rounds samples are accepted')
    parser.add_argument('--output', type=Path, help='New output directory; defaults to a timestamped run directory')
    parser.add_argument('--resume', action='store_true', help='Continue from a fully verified saved round after interruption')
    args = parser.parse_args()
    if args.output is None:
        if args.resume:
            parser.error('--resume requires --output pointing to the saved run')
        args.output = ROOT / ('results-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    if not 1 <= args.rounds <= 100 or args.poll_ms < 20:
        parser.error('Use 1–100 rounds and a polling interval of at least 20ms')
    if args.max_red_seconds is not None and args.max_red_seconds <= 0:
        parser.error('--max-red-seconds must be positive')
    if args.output.exists() and any(args.output.iterdir()) and not args.resume:
        parser.error('Output folder is not empty; choose a new folder with --output')
    cfg = setup(args)
    args.output.mkdir(parents=True, exist_ok=True)
    interval = args.poll_ms / 1000
    api, core, receiver = cfg['api'], cfg['core'], cfg['receiver']
    snapshot = lambda: post(api + '/query/getExecutionSnapshot', {'input': {'instanceId': cfg['chain_id']}})
    states = lambda value: {k: v for k, v in value.items() if k.endswith('States') or k == 'businessRuleRequestIds'}
    initial = snapshot()
    if [int(v) for v in initial['messageStates']] != [1]:
        raise ValueError('The deployed Message must already be ENABLED for repeated calls')
    report = {'metricsVersion': 9, 'platform': 'geth', 'status': 'running',
        'api': api, 'sourceApi': api, 'contractAddress': cfg['registered']['location']['address'],
        'signer': cfg['signer'], 'instanceIds': [cfg['chain_id']],
        'executionMode': 'existing-contract-same-enabled-instance', 'targetMessage': args.message,
        'client': 'Automated Python HTTP client using the same authenticated prepare-file-message endpoint as the UI',
        'startedAt': datetime.now(timezone.utc).isoformat(), 'requestedRounds': args.rounds,
        'participatingFireflyCores': [core, receiver], 'recipient': cfg['recipient']['did'],
        'listener': cfg['listener'], 'pollInterval_ms': args.poll_ms,
        'file': {'name': args.file.name if args.file else 'repeat-timing-1KiB.txt', 'bytes': args.file.stat().st_size if args.file else 1024},
        'filePolicy': 'User file bytes preserved' if args.file else 'Fresh unique 1KiB content and CID each round',
        'metrics': {'Private Data Bus': 'File upload HTTP request start → both organizations confirmed and batch pin succeeded, including IPFS publication',
                    'IPFS': 'FireFly publish request start → successful CID response; upload operation verified Succeeded',
                    'API Invoker': 'Contract HTTP request start → matching FireFly Operation.created',
                    'BPMN SC': 'Same Operation.created → matching blockchain_invoke_op_succeeded.created'},
        'metricAudit': {'method': 'monotonic HTTP client timing + FireFly Operation/event/confirmation timestamps + continuously sampled wall/monotonic bridge',
                        'notes': ['Private file delivery uses the existing backend feature; an explicit experimental FireFly IPFS publication is also performed',
                                  'Publication and business invoke start after the preparation API returns MessageID; neither waits for the other to finish',
                                  'Same instance and Message reused; all state arrays must remain unchanged; only the real Message ID is updated']},
        'originalInstanceBefore': initial, 'counterBefore': post(api + '/query/currentInstanceId', {'input': {}}),
        'samples': [], 'summary': [], 'attempts': [], 'activeAttempt': None,
        'sampleSelection': {'maxRed_ms': None if args.max_red_seconds is None else args.max_red_seconds * 1000,
                            'rule': 'Retain verified samples with red <= threshold; record exclusions and replace them until target count',
                            'targetAcceptedCount': args.rounds, 'acceptedCount': 0, 'totalAttempts': 0,
                            'excludedHighRedCount': 0, 'excludedInvalidTimingCount': 0}}
    first_round = 1
    if args.resume:
        previous = json.loads((args.output / 'results.json').read_text())
        assert previous['api'] == api and previous['signer'] == cfg['signer']
        assert previous['targetMessage'] == args.message and previous['instanceIds'] == [cfg['chain_id']]
        assert previous['requestedRounds'] == args.rounds
        assert not previous.get('activeAttempt'), 'An unfinished attempt must be reviewed before resuming'
        assert previous.get('sampleSelection', {}).get('maxRed_ms') == (None if args.max_red_seconds is None else args.max_red_seconds*1000), 'Keep the original red threshold when resuming'
        assert all(s['status'] == 'passed' and s.get('executionVerified') and s.get('clockNormalization')
                   and len(s.get('stages', [])) == 4 and s['receiverFileSha256'] == s['ipfsFileSha256'] == s['file']['sha256']
                   for s in previous['samples']), 'Only fully verified saved rounds can be resumed'
        assert [s['index'] for s in previous['samples']] == list(range(1, len(previous['samples'])+1))
        assert states(initial) == states(previous['originalInstanceBefore'])
        report = previous
        report.setdefault('attempts', [])
        report.setdefault('sampleSelection', {'maxRed_ms': None, 'totalAttempts': 0})
        report['status'] = 'running'; report.pop('error', None); report.pop('finishedAt', None)
        report['summary'] = []
        first_round = len(report['samples']) + 1
        for s in report['samples']:
            folder = args.output / f"round-{s['index']}"; folder.mkdir(exist_ok=True)
            save(folder / 'result.json', s)
        print(f'Resume: {first_round-1} fully verified rounds retained; continuing at round {first_round}', flush=True)
    save(args.output / 'results.json', report)
    try:
        while len(report['samples']) < args.rounds:
            index = len(report['samples']) + 1
            attempt = len(report['attempts']) + 1
            s = {'index': index, 'attempt': attempt, 'instanceId': cfg['chain_id'], 'status': 'running', 'method': cfg['method']}
            report['activeAttempt'] = s
            s['snapshotBefore'] = snapshot()
            assert states(s['snapshotBefore']) == states(initial), 'A node state changed before the next round'
            s['clockSyncBefore'] = sync()
            data = args.file.read_bytes() if args.file else (
                f'File Message timing\nround={index}\nnonce={uuid4()}\n'.ljust(1024, 'x').encode())
            s['file'] = {'name': report['file']['name'], 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
            print(f'Attempt {attempt}, target round {index}/{args.rounds}: upload file Message on instance {cfg["chain_id"]}', flush=True)
            save(args.output / 'results.json', report)
            upload = timed_post(cfg['endpoint'], timeout=args.timeout, headers=cfg['auth_headers'](),
                data={'messageId': args.message, 'values': '{}'},
                files={cfg['field']: (s['file']['name'], io.BytesIO(data), 'application/octet-stream')})
            s['fileUpload'] = upload
            s['preparationResponse'] = upload['value']
            file_id = upload['value']['fileIds'][cfg['field']]
            s['messageId'] = upload['value']['messageId']
            s['fileBindings'] = [cfg['field']]
            s['fileCidMapping'] = {'dataId': file_id}
            s['payload'] = {'instanceId': cfg['chain_id'], 'fireflyTranId': s['messageId'], cfg['field']: file_id}
            save(args.output / 'active-attempt.json', s)
            assert file_id and s['messageId']
            assert not get(core + '/data/' + file_id).get('blob', {}).get('public'), 'Cached publication; use different file content'
            with ThreadPoolExecutor(max_workers=1) as pool:
                started = threading.Event()
                publication = pool.submit(timed_post, core + f'/data/{file_id}/blob/publish', timeout=args.timeout, started=started, json={})
                # Ensure the publication branch has actually entered its HTTP request
                # before starting the business request; never wait for its response.
                if not started.wait(10):
                    raise RuntimeError('IPFS publication request did not start')
                s['invokeRequest'] = timed_post(api + '/invoke/' + cfg['method'], timeout=args.timeout,
                    json={'input': s['payload'], 'key': cfg['signer']})
                s['invokeResponse'] = s['invokeRequest']['value']
                save(args.output / 'active-attempt.json', s)
                def operation_status():
                    value = get(core + '/operations/' + s['invokeResponse']['id'] + '?fetchstatus=true')
                    if value['status'] == 'Failed':
                        raise RuntimeError('Business operation failed: ' + json.dumps(value))
                    return value
                s['operation'] = until('business operation', operation_status, lambda v: v['status'] == 'Succeeded', args.timeout, interval)
                s['operationObservedRaw'] = mono()
                s['ipfsPublishRequest'] = publication.result()
            cid = s['ipfsPublishRequest']['value'].get('blob', {}).get('public')
            assert cid, 'Publish did not return a CID'
            s['ipfsCid'] = cid; s['fileCidMapping']['cid'] = cid
            candidates = get(core + '/operations', params={'type': 'sharedstorage_upload_blob', 'limit': 1000})
            matches = [op for op in candidates if op.get('input', {}).get('dataId') == file_id]
            assert len(matches) == 1, 'Cannot uniquely correlate file publication operation'
            s['ipfsUploadOperation'] = until('IPFS upload success', lambda: get(core + '/operations/' + matches[0]['id']), lambda v: v['status'] == 'Succeeded', args.timeout, interval)
            assert s['ipfsUploadOperation']['output']['payloadRef'] == cid
            s['senderPublishedData'] = get(core + '/data/' + file_id)
            assert s['senderPublishedData']['blob']['public'] == cid
            op = s['operation']
            s['events'] = until('business success event', lambda: get(core + '/events', params={'tx': op['tx'], 'limit': 1000}),
                lambda rows: any(e['type'] == 'blockchain_invoke_op_succeeded' and e.get('reference') == op['id'] and e.get('tx') == op['tx'] for e in rows), args.timeout, interval)
            s['chainEvent'] = until('MessageSent with this Message ID', lambda: get(core + '/blockchainevents', params={'listener': cfg['listener']['id'], 'limit': 1000}),
                lambda rows: any(e.get('output', {}).get('fireflyTranId') == s['messageId'] and int(e['output']['instanceId']) == cfg['chain_id'] for e in rows), args.timeout, interval)
            s['chainEvent'] = next(e for e in s['chainEvent'] if e.get('output', {}).get('fireflyTranId') == s['messageId'] and int(e['output']['instanceId']) == cfg['chain_id'])
            assert int(s['chainEvent']['output']['messageKey']) == 0
            for key, node in [('messageFinal', core), ('receiverMessage', receiver)]:
                s[key] = until(key, lambda node=node: get(node + '/messages/' + s['messageId']), lambda v: v.get('state') == 'confirmed' and bool(v.get('confirmed')), args.timeout, interval)
            batch_id = s['messageFinal']['batch']
            s['batch'] = get(core + '/batches/' + batch_id)
            s['transportOperations'] = until('all delivery/pin operations', lambda: get(core + '/operations', params={'tx': s['batch']['tx']['id'], 'limit': 1000}),
                lambda rows: any(v['type'] == 'blockchain_pin_batch' for v in rows) and all(v['status'] == 'Succeeded' for v in rows), args.timeout, interval)
            s['receiverMessageData'] = get(receiver + '/messages/' + s['messageId'] + '/data')
            assert any(v.get('id') == file_id for v in s['receiverMessageData'])
            assert any(v.get('value', {}).get(cfg['field']) == file_id for v in s['receiverMessageData'])
            receiver_blob = requests.get(receiver + f'/data/{file_id}/blob', timeout=30); receiver_blob.raise_for_status()
            ipfs_blob = requests.get(cfg['gateway'] + '/ipfs/' + cid, timeout=30); ipfs_blob.raise_for_status()
            assert receiver_blob.content == ipfs_blob.content == data, 'Uploaded/IPFS/receiver bytes differ'
            s['receiverFileSha256'] = hashlib.sha256(receiver_blob.content).hexdigest()
            s['ipfsFileSha256'] = hashlib.sha256(ipfs_blob.content).hexdigest()
            s['snapshotAfter'] = snapshot()
            assert states(s['snapshotAfter']) == states(initial), 'Message or another node advanced'
            assert s['snapshotAfter']['messageFireflyTranIds'] == [s['messageId']], 'On-chain Message ID mismatch'
            assert [int(v) for v in s['snapshotAfter']['messageStates']] == [1], 'Message is not repeatable'
            s['executionVerified'] = True; s['observedFinishedRaw'] = mono(); s['clockSyncAfter'] = sync()
            # Preserve actual wall-clock inputs before normalization, including
            # possible clock inversions; never use placeholder phase intervals.
            success_event = next(e for e in s['events'] if e['type'] == 'blockchain_invoke_op_succeeded'
                and e.get('reference') == op['id'] and e.get('tx') == op['tx'])
            created = epoch_ms(op['created'])
            blue_end = max(s['ipfsPublishRequest']['end'], epoch_ms(s['messageFinal']['confirmed']),
                epoch_ms(s['receiverMessage']['confirmed']),
                *(epoch_ms(v['updated']) for v in s['transportOperations'] if v['type'] == 'blockchain_pin_batch'))
            intervals = [('Private Data Bus', upload['start'], blue_end),
                ('IPFS', s['ipfsPublishRequest']['start'], s['ipfsPublishRequest']['end']),
                ('API Invoker', s['invokeRequest']['start'], created),
                ('BPMN SC', created, epoch_ms(success_event['created']))]
            s['stages'] = [{'step': name, 'start_time': a, 'end_time': b, 'duration_ms': b-a, 'valid': b>=a}
                           for name,a,b in intervals]
            single = {'metricsVersion': 9, 'metrics': dict(report['metrics']), 'metricAudit': copy.deepcopy(report['metricAudit']), 'samples': [s]}
            try:
                normalize(single)
            except AssertionError as exc:
                message = str(exc)
                if not any(text in message for text in ['No clock match', 'Ambiguous wall timestamp', 'Browser/observer clock drift']):
                    raise
                s['status'] = 'excluded_invalid_timing'
                s['clockNormalizationError'] = message
                s['clockPairsForReview'] = [pair for pair in list(SAMPLES)
                    if s['fileUpload']['clock']['rawStart']-200 <= pair[1] <= s['observedFinishedRaw']+200]
                record_attempt(report, args.output, s, 'File and chain checks passed, but clock mapping was not uniquely valid: '+message)
                print(f'Attempt {attempt} excluded: invalid clock mapping; replacement required', flush=True)
                continue
            report['metrics'] = single['metrics']
            report['browserClock'] = 'Python client monotonic timestamps and sampled server wall→monotonic bridge; normalized to upload start'
            s['clockNormalization']['client'] = 'Python requests, not browser Resource Timing'
            s['status'] = 'passed'
            if exceeds_red_limit(s, args.max_red_seconds):
                s['status'] = 'excluded_high_red'
                red_ms = next(v['duration_ms'] for v in s['stages'] if v['step'] == 'BPMN SC')
                record_attempt(report, args.output, s, f'Red {red_ms:.6f}ms exceeds {args.max_red_seconds*1000:.0f}ms')
                print(f'Attempt {attempt} excluded: red={red_ms:.2f}ms > {args.max_red_seconds*1000:.0f}ms; accepted={len(report["samples"])}/{args.rounds}', flush=True)
                continue
            report['samples'].append(s)
            folder = args.output / f'round-{index}'; folder.mkdir()
            save(folder / 'result.json', s)
            record_attempt(report, args.output, s)
            print(f'Accepted {index}/{args.rounds} (attempt {attempt}): ' + ', '.join(f"{v['step']}={v['duration_ms']:.2f}ms" for v in s['stages']), flush=True)
        report['originalInstanceAfter'] = snapshot()
        report['counterAfter'] = post(api + '/query/currentInstanceId', {'input': {}})
        assert states(report['originalInstanceAfter']) == states(initial)
        assert report['counterBefore'] == report['counterAfter'], 'Unexpected new chain instance'
        assert len({s['ipfsCid'] for s in report['samples']}) == args.rounds, 'CID reuse in measured runs'
        report['status'] = 'passed'
    except Exception as exc:
        report['status'] = 'failed'; report['error'] = str(exc)
        if report.get('activeAttempt'):
            report['activeAttempt']['status'] = 'failed'; report['activeAttempt']['error'] = str(exc)
        raise
    finally:
        report['finishedAt'] = datetime.now(timezone.utc).isoformat()
        for name in PHASES:
            values = [next(v['duration_ms'] for v in s['stages'] if v['step'] == name) for s in report['samples'] if s['status'] == 'passed']
            if values:
                report['summary'].append({'step': name, 'count': len(values), 'mean_ms': mean(values), 'median_ms': median(values), 'min_ms': min(values), 'max_ms': max(values)})
        save(args.output / 'results.json', report)
        save(args.output / 'summary.json', report['summary'])
    from summarize import export_report
    export_report(report, args.output)
    print(f'Completed {args.rounds} successful rounds. Results: {args.output}', flush=True)


if __name__ == '__main__':
    main()
