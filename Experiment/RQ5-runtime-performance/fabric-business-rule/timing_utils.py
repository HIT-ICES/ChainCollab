"""Experiment-only HTTP and local wall/monotonic clock helpers."""
import json
import sys
import time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
sys.path.insert(0, str(ROOT.parent/'geth-file-message/metric-audit'))
from monotonic_clock import read_clock, SAMPLES
from audit_metrics import epoch_ms


def mono():
    return time.monotonic_ns()/1e6


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')
    tmp.replace(path)


def request(method, url, **kwargs):
    r = requests.request(method, url, timeout=180, **kwargs)
    if not r.ok:
        raise RuntimeError(f'{method} {url}: {r.status_code}: {r.text}')
    return r.json() if r.content else None


def timed(method, url, **kwargs):
    with requests.Session() as session:
        prepared = session.prepare_request(requests.Request(method, url, **kwargs))
        start = mono(); response = session.send(prepared, timeout=180)
        content = response.content; end = mono()
        response.raise_for_status()
        return {'start_ms': start, 'end_ms': end, 'url': url,
                'httpStatus': response.status_code}, content


def timed_post(url, value):
    clock, content = timed('POST', url, json=value)
    return {**clock, 'value': json.loads(content)}


def wait(label, fetch, accept, seconds=180):
    deadline = mono()+seconds*1000
    while mono()<deadline:
        v = fetch()
        if isinstance(v, dict) and v.get('status')=='Failed':
            raise RuntimeError(f'{label}: {json.dumps(v)}')
        if accept(v):
            return v
        time.sleep(.1)
    raise TimeoutError(label)


def operation(core, oid):
    # status persisted by FireFly, plus a separately correlated success event.
    return wait('Operation '+oid, lambda: request('GET',core+'/operations/'+oid),
                lambda v:v['status']=='Succeeded')


def success(core, op):
    def matches(e):
        return (e['type']=='blockchain_invoke_op_succeeded' and
                e.get('reference')==op['id'] and e.get('tx')==op['tx'])
    events = wait('invoke success event',lambda:request('GET',core+'/events',params={'tx':op['tx'],'limit':1000}),
                  lambda rows:any(matches(e) for e in rows))
    found = [e for e in events if matches(e)]
    assert len(found)==1
    return found[0]


def map_wall(value, lower, upper, pairs, label):
    wall = epoch_ms(value); candidates=[]
    for (w1,m1),(w2,m2) in zip(pairs,pairs[1:]):
        if abs((w2-w1)-(m2-m1))>2:
            continue
        if w1-.6<=wall<=w2+.6:
            point=m1+wall-w1
            if lower-2<=point<=upper+2:
                candidates.append(point)
    if not candidates or max(candidates)-min(candidates)>=3:
        raise ValueError('Invalid clock mapping: '+label)
    return sum(candidates)/len(candidates)
