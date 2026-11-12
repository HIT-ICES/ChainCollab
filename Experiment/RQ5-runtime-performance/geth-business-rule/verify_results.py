#!/usr/bin/env python3
"""Replay saved timing evidence without issuing any new business transaction."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from run_repeat import normalization, PHASES, ROOT, load_report, excluded_count


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=ROOT/'results-100/results.json')
    args=parser.parse_args();report=load_report(args.input)
    assert report['status']=='passed'
    assert len(report['samples'])==report['requestedRounds']
    assert len({s['requestId'] for s in report['samples']})==len(report['samples'])
    if 'sampleFiles' in report:
        hashes=json.loads((args.input.parent/'sample-sha256.json').read_text())
        assert set(hashes)==set(report['sampleFiles'])
        for name,digest in hashes.items():
            assert hashlib.sha256((args.input.parent/name).read_bytes()).hexdigest()==digest,name
    if 'attemptCount' in report:
        assert report['attemptCount']==len(report['samples'])+excluded_count(report)
    source=(ROOT/'deployment/contract.sol').read_bytes()
    deployment=json.loads((ROOT/'deployment/deployment.json').read_text())
    assert hashlib.sha256(source).hexdigest()==deployment['sourceSha256']
    original=(ROOT.parent/'fabric-business-rule/deployment/rule.dmn').read_bytes()
    assert original==(ROOT/'deployment/rule.dmn').read_bytes()
    sha=hashlib.sha256(original).hexdigest()
    checked=0
    for sample in report['samples']:
        assert sample['status']=='passed' and sample['executionVerified']
        for phase in sample['stages']:
            limit=report.get('outlierThresholds_ms',{}).get(phase['step'])
            assert limit is None or phase['duration_ms']<=limit,(sample['index'],phase,limit)
        assert not sample['approvalBefore']['approved'] and sample['approvalAfter']['approved']
        assert list(map(int,sample['snapshotBefore']['businessRuleStates']))==[1]
        assert list(map(int,sample['snapshotAfter']['businessRuleStates']))==[3]
        assert int(sample['requestStatus']['state'])==2 and sample['requestStatus']['exists']
        assert json.loads(sample['rawDmnResult'])[0]['approved'] is True
        evidence=sample['nodeHttpEvidence'][sample['primaryNode']]
        assert evidence['ipfs']['status']==200
        assert evidence['ipfs']['response_sha256']==sha
        assert evidence['ipfs']['response_bytes']==len(original)
        assert evidence['ipfs']['cid']==report['dmnPublication']['cid']
        assert evidence['cdmn']['output']['requestId']==sample['requestId']
        duplicate=copy.deepcopy(sample);normalization(duplicate,pairs=sample['clockPairs'])
        assert len(duplicate['stages'])==len(PHASES)
        for old,new in zip(sample['stages'],duplicate['stages']):
            assert old==new,(sample['index'],old,new)
            checked+=1
    print(f'Verified {len(report["samples"])} real executions and replayed {checked} stage intervals.')


if __name__=='__main__':main()
