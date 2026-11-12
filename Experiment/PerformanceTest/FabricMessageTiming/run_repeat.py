#!/usr/bin/env python3
"""Fabric file Message timing: existing repeatable node, whole-batch filtering.

Only explicit execution contacts FireFly. --check-config performs local checks.
No deployment, instance creation, reset, database access or business-code edits.
"""
import argparse
import copy
import csv
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
from statistics import mean, median
import sys
import threading
import time
from urllib.parse import quote, urlsplit
from uuid import uuid4

ROOT = Path(__file__).resolve().parent
# Reuse precisely the clock conversion used by the retained Geth results.
sys.path.insert(0, str(ROOT.parent / 'GethMessageTiming' / 'metric-audit'))
import requests
from monotonic_clock import normalize, read_clock, SAMPLES
from audit_metrics import epoch_ms

PHASES = ['Private Data Bus', 'IPFS', 'API Invoker', 'BPMN SC']


def require(condition, message):
    if not condition:
        raise ValueError(message)


def mono():
    return time.monotonic_ns() / 1e6


def sync():
    before = mono(); value = read_clock(); after = mono()
    return {**value, 'browserBefore': before, 'browserAfter': after}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def load_config(path):
    cfg = json.loads(path.read_text())
    for name in ['source_core', 'receiver_core', 'api', 'ipfs_gateway',
                 'instance_id', 'message_id', 'recipient', 'key', 'file_field']:
        require(isinstance(cfg.get(name), str) and cfg[name].strip()
                and 'REPLACE_WITH' not in cfg[name], f'Fill config field: {name}')
    for name in ['source_core', 'receiver_core', 'api', 'ipfs_gateway']:
        cfg[name] = cfg[name].rstrip('/')
        url = urlsplit(cfg[name])
        require(url.scheme in ['http', 'https'] and url.netloc and not url.query
                and not url.fragment and not url.username, f'Invalid URL: {name}')
    require(cfg['api'].startswith(cfg['source_core'] + '/apis/'),
            'api must be a registered API on source_core')
    require(cfg['source_core'] != cfg['receiver_core'], 'Use two different FireFly cores')
    require(cfg['recipient'].startswith('did:'), 'recipient must be an identity DID')
    cfg.setdefault('values', {}); cfg.setdefault('contract_input', {})
    cfg.setdefault('parameters', {}); cfg.setdefault('header_env', {})
    cfg.setdefault('queries', ['GetAllMessages', 'GetAllGateways', 'GetAllActionEvents', 'GetAllBusinessRules'])
    require(set(cfg['queries']) >= {'GetAllMessages', 'GetAllGateways', 'GetAllActionEvents', 'GetAllBusinessRules'},
            'All four node-state queries are required')
    for name in ['values', 'contract_input', 'parameters', 'header_env']:
        require(isinstance(cfg[name], dict), f'{name} must be an object')
    require(cfg['file_field'] not in cfg['values'], 'File field is filled from the actual upload, not values')
    cfg.setdefault('timeout_seconds', 300); cfg.setdefault('poll_ms', 250)
    require(math.isfinite(cfg['timeout_seconds']) and cfg['timeout_seconds'] > 0
            and cfg['poll_ms'] >= 20, 'Use positive timeout and poll_ms >= 20')
    return cfg


class Experiment:
    def __init__(self, cfg):
        self.cfg = cfg
        self.core, self.receiver, self.api = (cfg[k] for k in ['source_core', 'receiver_core', 'api'])
        self.headers = {header: os.environ[env] for header, env in cfg['header_env'].items()}
        self.timeout = cfg['timeout_seconds']
        self.interval = cfg['poll_ms'] / 1000

    def request(self, method, url, **kwargs):
        headers = self.headers if url.startswith((self.core + '/', self.receiver + '/')) else {}
        response = requests.request(method, url, headers=headers, timeout=self.timeout, **kwargs)
        response.raise_for_status()
        return response.json()

    def get(self, url, **kwargs):
        return self.request('GET', url, **kwargs)

    def post(self, url, value):
        return self.request('POST', url, json=value)

    def message(self, core, message_id):
        try:
            value = self.get(core + '/messages/' + message_id)
        except requests.HTTPError as exc:
            # A private Message can be absent on the receiver until delivery.
            if exc.response is not None and exc.response.status_code == 404:
                return {}
            raise
        require(value.get('state') not in ['rejected', 'failed'], 'File Message was rejected')
        return value

    def timed_post(self, url, started=None, **kwargs):
        with requests.Session() as session:
            prepared = session.prepare_request(requests.Request('POST', url, headers=self.headers, **kwargs))
            clock = read_clock(); start = mono()
            if started is not None:
                started.set()
            response = session.send(prepared, timeout=self.timeout)
            content = response.content; end = mono()
            response.raise_for_status()
            origin = clock['wall_ms'] - clock['monotonic_ms']
            return {'value': json.loads(content), 'start': origin + start, 'end': origin + end,
                    'clock': {'rawStart': start, 'rawEnd': end, 'client': 'Python requests'},
                    'httpStatus': response.status_code, 'url': url}

    def until(self, label, fetch, accept):
        deadline = mono() + self.timeout * 1000
        while mono() < deadline:
            value = fetch()
            rows = value if isinstance(value, list) else [value]
            require(not any(isinstance(v, dict) and v.get('status') == 'Failed' for v in rows),
                    f'Failed FireFly operation while waiting for {label}')
            if accept(value):
                return value
            time.sleep(self.interval)
        raise TimeoutError(f'Timed out waiting for {label}')

    def parameter(self, method, role, required=True):
        names = [p['name'] for p in self.methods[method].get('params', [])]
        explicit = self.cfg['parameters'].get(role)
        if explicit:
            require(explicit in names, f'{method} has no configured {role} parameter {explicit}')
            return explicit
        aliases = {'instance': ['instanceid'], 'message': ['messageid'],
                   'firefly': ['fireflytranid', 'fireflytran'],
                   'file': [self.cfg['file_field'].lower()]}[role]
        matches = [n for n in names if n.lower() in aliases]
        require(len(matches) <= 1 and (matches or not required),
                f'Configure parameters.{role} for {method}; actual names: {names}')
        return matches[0] if matches else None

    def query(self, method):
        value = self.post(self.api + '/query/' + quote(method, safe=''),
                          {'input': {self.parameter(method, 'instance'): self.cfg['instance_id']}})
        # FireFly/Fabric returns may be an array, output wrapper, or JSON ret0.
        for _ in range(5):
            # fabconnect represents a nil Go slice as the empty JSON string.
            if value == '':
                return []
            if isinstance(value, str):
                value = json.loads(value)
            elif isinstance(value, dict) and 'output' in value:
                value = value['output']
            elif isinstance(value, dict) and set(value) == {'ret0'}:
                value = value['ret0']
            else:
                break
        require(value is None or isinstance(value, list), f'{method} did not return an array')
        return value or []

    def snapshot(self):
        return {method: self.query(method) for method in self.cfg['queries']}

    def target(self, snapshot):
        matches = [v for v in snapshot['GetAllMessages'] if v.get('MessageID') == self.cfg['message_id']]
        require(len(matches) == 1, 'Cannot uniquely identify target Message')
        return matches[0]

    def states(self, snapshot):
        value = copy.deepcopy(snapshot)
        # Only the target node's latest real FireFly Message ID may change.
        self.target(value).pop('FireflyTranID', None)
        return {k: sorted(rows, key=lambda v: json.dumps(v, sort_keys=True)) for k, rows in value.items()}

    def preflight(self):
        self.methods = {m['name']: m for m in self.get(self.api + '/interface')['methods']}
        self.method = self.cfg['message_id'] + '_Send'
        require(self.method in self.methods, 'Target Send method missing from registered interface')
        require(all(m in self.methods for m in self.cfg['queries']), 'Required node queries missing from interface')
        self.instance_param = self.parameter(self.method, 'instance')
        self.firefly_param = self.parameter(self.method, 'firefly')
        self.file_param = self.parameter(self.method, 'file', required=False)
        expected = {p['name'] for p in self.methods[self.method].get('params', [])}
        supplied = set(self.cfg['contract_input']) | {self.instance_param, self.firefly_param}
        if self.file_param:
            supplied.add(self.file_param)
        require(not set(self.cfg['contract_input']) & {self.instance_param, self.firefly_param, self.file_param},
                'contract_input must not override generated instance, Message ID or file fields')
        require(supplied == expected, f'Send input mismatch: required {sorted(expected)}, supplied {sorted(supplied)}')
        self.initial = self.snapshot()
        target = self.target(self.initial)
        require(target.get('MsgState') == 1, 'Target must already be ENABLED (MsgState=1)')
        schema = target.get('Format')
        schema = json.loads(schema) if isinstance(schema, str) else schema
        if isinstance(schema, dict) and 'schema' in schema:
            schema = schema['schema']
            schema = json.loads(schema) if isinstance(schema, str) else schema
        require(isinstance(schema, dict) and set(schema.get('files', {})) == {self.cfg['file_field']},
                'This runner requires exactly one file field in the target Message Format')
        source_org = self.get(self.core + '/status')['org']['did']
        receiver_org = self.get(self.receiver + '/status')['org']['did']
        require(source_org != receiver_org, 'Source and receiver must be different organizations')
        identity = self.get(self.core + '/identities/' + quote(self.cfg['recipient'], safe=''))
        seen = set()
        while identity.get('type') != 'org':
            parent = identity.get('parent')
            require(parent and parent not in seen, 'Cannot resolve recipient organization')
            seen.add(parent)
            identity = self.get(self.core + '/identities/' + quote(parent, safe=''))
        require(identity['did'] == receiver_org, 'recipient does not belong to receiver_core organization')

    def run_one(self, sample, checkpoint, file_path=None):
        s, cfg = sample, self.cfg
        s['snapshotBefore'] = self.snapshot()
        require(self.states(s['snapshotBefore']) == self.states(self.initial), 'Node state changed before round')
        s['clockSyncBefore'] = sync()
        content = file_path.read_bytes() if file_path else (
            f'Fabric Message timing\nnonce={uuid4()}\n'.ljust(1024, 'x').encode())
        name = file_path.name if file_path else 'repeat-timing-1KiB.txt'
        s['file'] = {'name': name, 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()}
        s['fileUpload'] = self.timed_post(self.core + '/data', data={'autometa': 'true'},
                                        files={'file': (name, content, 'application/octet-stream')})
        data_id = s['fileUpload']['value']['id']
        s['fileCidMapping'] = {'dataId': data_id}; checkpoint(s)
        require(not self.get(self.core + '/data/' + data_id).get('blob', {}).get('public'),
                'Cached publication; use a new file')
        values = {**cfg['values'], cfg['file_field']: data_id}
        s['messageRequest'] = self.timed_post(self.core + '/messages/private', json={
            'header': {'tag': 'private', 'topics': ['fabric-timing-' + cfg['message_id']]},
            'group': {'members': [{'identity': cfg['recipient']}]},
            'data': [{'value': values}, {'id': data_id}]})
        s['messageId'] = s['messageRequest']['value']['header']['id']; checkpoint(s)
        payload = {**cfg['contract_input'], self.instance_param: cfg['instance_id'],
                   self.firefly_param: s['messageId']}
        if self.file_param:
            payload[self.file_param] = data_id
        s['payload'] = payload
        with ThreadPoolExecutor(max_workers=1) as pool:
            started = threading.Event()
            future = pool.submit(self.timed_post, self.core + f'/data/{data_id}/blob/publish',
                                 started=started, json={})
            require(started.wait(10), 'Publication HTTP request did not start')
            s['invokeRequest'] = self.timed_post(self.api + '/invoke/' + self.method,
                                                json={'key': cfg['key'], 'input': payload})
            s['invokeResponse'] = s['invokeRequest']['value']; checkpoint(s)
            operation_id = s['invokeResponse']['id']
            s['operation'] = self.until('business operation',
                lambda: self.get(self.core + '/operations/' + operation_id + '?fetchstatus=true'),
                lambda v: v['status'] == 'Succeeded')
            s['ipfsPublishRequest'] = future.result()
        cid = s['ipfsPublishRequest']['value'].get('blob', {}).get('public')
        require(cid, 'Successful publish response must contain CID')
        s['ipfsCid'] = cid; s['fileCidMapping']['cid'] = cid; checkpoint(s)
        matches = self.until('upload operation',
            lambda: self.get(self.core + '/operations', params={'type': 'sharedstorage_upload_blob', 'limit': 1000}),
            lambda rows: any(v.get('input', {}).get('dataId') == data_id for v in rows))
        matches = [v for v in matches if v.get('input', {}).get('dataId') == data_id]
        require(len(matches) == 1, 'Cannot uniquely correlate IPFS upload Operation')
        s['ipfsUploadOperation'] = self.until('IPFS upload success',
            lambda: self.get(self.core + '/operations/' + matches[0]['id']), lambda v: v['status'] == 'Succeeded')
        require(s['ipfsUploadOperation']['output']['payloadRef'] == cid, 'Operation CID mismatch')
        s['senderPublishedData'] = self.get(self.core + '/data/' + data_id)
        require(s['senderPublishedData']['blob']['public'] == cid, 'Data CID mismatch')
        op = s['operation']
        def success(e):
            return (e['type'] == 'blockchain_invoke_op_succeeded'
                    and e.get('reference') == op['id'] and e.get('tx') == op['tx'])
        s['events'] = self.until('correlated business success event',
            lambda: self.get(self.core + '/events', params={'tx': op['tx'], 'limit': 1000}),
            lambda rows: any(success(e) for e in rows))
        for key, core in [('messageFinal', self.core), ('receiverMessage', self.receiver)]:
            s[key] = self.until(key, lambda core=core: self.message(core, s['messageId']),
                               lambda v: v.get('state') == 'confirmed' and bool(v.get('confirmed')))
        s['batch'] = self.get(self.core + '/batches/' + s['messageFinal']['batch'])
        s['transportOperations'] = self.until('delivery and pin success',
            lambda: self.get(self.core + '/operations', params={'tx': s['batch']['tx']['id'], 'limit': 1000}),
            lambda rows: any(v['type'] == 'blockchain_pin_batch' for v in rows)
                         and all(v['status'] == 'Succeeded' for v in rows))
        s['receiverMessageData'] = self.get(self.receiver + '/messages/' + s['messageId'] + '/data')
        require(any(v.get('id') == data_id for v in s['receiverMessageData'])
                and any(isinstance(v.get('value'), dict) and v['value'].get(cfg['file_field']) == data_id
                        for v in s['receiverMessageData']), 'Receiver file attachment/binding mismatch')
        for key, url, headers in [
            ('receiverFileSha256', self.receiver + f'/data/{data_id}/blob', self.headers),
            ('ipfsFileSha256', cfg['ipfs_gateway'] + '/ipfs/' + cid, {})]:
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            require(response.content == content, f'{key}: file bytes mismatch')
            s[key] = hashlib.sha256(response.content).hexdigest()
        s['snapshotAfter'] = self.snapshot()
        require(self.states(s['snapshotAfter']) == self.states(self.initial),
                'Message or another node advanced; deploy a repeatable test Message before running')
        target = self.target(s['snapshotAfter'])
        require(target['MsgState'] == 1 and target['FireflyTranID'] == s['messageId'],
                'On-chain target state/FireFly Message ID mismatch')
        s['executionVerified'] = True; s['observedFinishedRaw'] = mono(); s['clockSyncAfter'] = sync()
        event = next(e for e in s['events'] if success(e))
        created = epoch_ms(op['created'])
        blue_end = max(s['ipfsPublishRequest']['end'], epoch_ms(s['messageFinal']['confirmed']),
                       epoch_ms(s['receiverMessage']['confirmed']),
                       *(epoch_ms(v['updated']) for v in s['transportOperations'] if v['type'] == 'blockchain_pin_batch'))
        s['stages'] = [dict(step=name, start_time=a, end_time=b, duration_ms=b-a, valid=b>=a)
                      for name, a, b in [
                          ('Private Data Bus', s['fileUpload']['start'], blue_end),
                          ('IPFS', s['ipfsPublishRequest']['start'], s['ipfsPublishRequest']['end']),
                          ('API Invoker', s['invokeRequest']['start'], created),
                          ('BPMN SC', created, epoch_ms(event['created']))]]
        try:
            normalize({'metricsVersion': 9, 'samples': [s], 'metrics': {}, 'metricAudit': {}})
        except AssertionError as exc:
            if not any(text in str(exc) for text in ['No clock match', 'Ambiguous wall timestamp', 'Browser/observer clock drift']):
                raise
            s['status'] = 'excluded_invalid_timing'; s['clockNormalizationError'] = str(exc)
            s['clockPairsForReview'] = [p for p in list(SAMPLES)
                if s['fileUpload']['clock']['rawStart']-200 <= p[1] <= s['observedFinishedRaw']+200]
            return
        s['status'] = 'passed'


def export(report, output):
    samples = report['samples']
    verification = []
    for sample in samples:
        require(sample['status'] == 'passed' and sample['executionVerified'], 'Unverified retained sample')
        phases = {v['step']: v for v in sample['stages']}
        require(phases['API Invoker']['end_time'] == phases['BPMN SC']['start_time'], 'Red/green boundary differs')
        require(sample['file']['sha256'] == sample['receiverFileSha256'] == sample['ipfsFileSha256'], 'File hash differs')
        verification.append({'round': sample['index'], 'messageId': sample['messageId'],
            'dataId': sample['fileCidMapping']['dataId'], 'cid': sample['ipfsCid'],
            'operationId': sample['operation']['id'], 'sha256': sample['file']['sha256'],
            'executionVerified': True, 'greenRedBoundaryIdentical': True,
            'uploadReceiverIpfsContentsIdentical': True})
    report['summary'] = []
    for name in PHASES:
        values = [next(v['duration_ms'] for v in s['stages'] if v['step'] == name) for s in samples]
        if values:
            report['summary'].append(dict(step=name, count=len(values), mean_ms=mean(values),
                median_ms=median(values), min_ms=min(values), max_ms=max(values)))
    save(output / 'results.json', report); save(output / 'summary.json', report['summary'])
    save(output / 'verification.json', verification)
    with (output / 'timings.csv').open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['round', 'instanceId', 'stage', 'start_offset_ms', 'end_offset_ms', 'duration_ms'])
        for s in samples:
            save(output / f"round-{s['index']}" / 'result.json', s)
            for v in s['stages']:
                writer.writerow([s['index'], s['instanceId'], v['step'],
                    v['start_time']-s['fileUpload']['start'], v['end_time']-s['fileUpload']['start'], v['duration_ms']])
    selection = report['sampleSelection']
    lines = ['# Fabric 文件 Message 分阶段耗时', '',
             f"状态：{report['status']}；保留 {len(samples)} 轮。", '',
             '同一已部署链码、同一实例、可重复文件 Message；红绿共用 Operation.created 边界。', '',
             f"筛选配置：{json.dumps(selection, ensure_ascii=False)}", '',
             '均值是按所设阈值筛选后的条件统计；attempts/保留尝试原始数据。', '',
             '| 阶段 | 样本数 | 平均(ms) | 中位数(ms) | 最小(ms) | 最大(ms) |',
             '|---|---:|---:|---:|---:|---:|']
    for row in report['summary']:
        lines.append(f"| {row['step']} | {row['count']} | {row['mean_ms']:.2f} | {row['median_ms']:.2f} | {row['min_ms']:.2f} | {row['max_ms']:.2f} |")
    (output / 'RESULTS.md').write_text('\n'.join(lines) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--check-config', action='store_true', help='Validate config locally; no network requests')
    parser.add_argument('--rounds', type=int, default=3)
    parser.add_argument('--max-red-seconds', type=float, default=25, help='Batch filter; 0 disables red threshold')
    parser.add_argument('--max-attempts', type=int, default=1000)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--file', type=Path)
    args = parser.parse_args()
    require(1 <= args.rounds <= 100 and args.max_attempts >= args.rounds, 'Use 1–100 rounds and enough max-attempts')
    require(math.isfinite(args.max_red_seconds) and args.max_red_seconds >= 0, 'Invalid red threshold')
    cfg = load_config(args.config)
    if args.file:
        require(args.file.is_file(), '--file does not exist')
    if args.check_config:
        print('Configuration valid locally. No requests sent; deployment not verified.')
        return
    output = args.output or ROOT / ('results-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    require(not output.exists() or not any(output.iterdir()), 'Choose a new empty output directory')
    experiment = Experiment(cfg)
    experiment.preflight()
    output.mkdir(parents=True, exist_ok=True)
    report = {'platform': 'fabric', 'metricsVersion': 9, 'status': 'running',
        'api': cfg['api'], 'instanceIds': [cfg['instance_id']], 'targetMessage': cfg['message_id'],
        'participatingFireflyCores': [cfg['source_core'], cfg['receiver_core']],
        'file': {'bytes': args.file.stat().st_size if args.file else 1024},
        'startedAt': datetime.now(timezone.utc).isoformat(), 'samples': [], 'attempts': [], 'batches': [],
        'metricAudit': {'clock': 'Same 5ms local wall/monotonic conversion as Geth',
            'notes': ['Direct Fabric FireFly file preparation; no Geth/Django preparation endpoint',
                      'Private delivery plus explicit parallel IPFS publication; file checks excluded from blue end']},
        'originalInstanceBefore': experiment.initial,
        'sampleSelection': {'maxRed_ms': args.max_red_seconds*1000 if args.max_red_seconds else None,
            'targetAcceptedCount': args.rounds, 'strategy': 'batch_then_filter_then_refill'}}
    active = None
    try:
        while len(report['samples']) < args.rounds:
            batch = []; number = len(report['batches']) + 1
            deficit = args.rounds - len(report['samples'])
            print(f'Batch {number}: execute {deficit} rounds, then filter', flush=True)
            for _ in range(deficit):
                require(len(report['attempts']) < args.max_attempts, 'Attempt budget exhausted')
                active = {'attempt': len(report['attempts'])+1, 'batchNumber': number,
                          'instanceId': cfg['instance_id'], 'status': 'running'}
                active['index'] = active['attempt']
                save(output / 'active-attempt.json', active)
                experiment.run_one(active, lambda s: save(output / 'active-attempt.json', s), args.file)
                batch.append(active); report['attempts'].append(active)
                save(output / 'attempts' / f"attempt-{active['attempt']:04d}" / 'result.json', active)
                save(output / 'results.json', report)
                (output / 'active-attempt.json').unlink(); active = None
            retained_before = len(report['samples'])
            for sample in batch:
                if sample['status'] == 'passed':
                    red = next(v['duration_ms'] for v in sample['stages'] if v['step'] == 'BPMN SC')
                    if args.max_red_seconds and red > args.max_red_seconds*1000:
                        sample['status'] = 'excluded_high_red'
                    else:
                        sample['index'] = len(report['samples']) + 1
                        report['samples'].append(sample)
                save(output / 'attempts' / f"attempt-{sample['attempt']:04d}" / 'result.json', sample)
            report['batches'].append({'batch': number, 'requested': deficit,
                'retained': len(report['samples'])-retained_before})
            export(report, output)
            print(f'Batch complete: retained {len(report["samples"])}/{args.rounds}', flush=True)
        for key in ['messageId', 'ipfsCid']:
            require(len({s[key] for s in report['samples']}) == args.rounds, f'{key} reused')
        report['originalInstanceAfter'] = experiment.snapshot()
        require(experiment.states(report['originalInstanceAfter']) == experiment.states(experiment.initial),
                'Node states changed after final round')
        report['status'] = 'passed'
    except Exception as exc:
        report['status'] = 'failed'; report['error'] = str(exc)
        if active:
            active['status'] = 'failed'; active['error'] = str(exc)
            save(output / 'active-attempt.json', active)
        raise
    finally:
        selection = report['sampleSelection']
        selection.update(acceptedCount=len(report['samples']), totalAttempts=len(report['attempts']) + bool(active),
            excludedHighRedCount=sum(s['status'] == 'excluded_high_red' for s in report['attempts']),
            excludedInvalidTimingCount=sum(s['status'] == 'excluded_invalid_timing' for s in report['attempts']))
        report['finishedAt'] = datetime.now(timezone.utc).isoformat()
        export(report, output)
    print(f'Completed {args.rounds} verified rounds. Saved to {output}', flush=True)


if __name__ == '__main__':
    main()
