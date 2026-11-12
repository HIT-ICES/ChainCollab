#!/usr/bin/env python3
"""Recalculate saved BRT timing boundaries offline; never submit transactions."""
import argparse
import copy
import json
from pathlib import Path
from run_repeat import ROOT, normalize, export
from timing_utils import save


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=ROOT/'results-100/results.json')
    args=parser.parse_args();path=args.input;report=json.loads(path.read_text())
    assert report['status']=='passed' and report['samples']
    canonical={}
    for sample in report['samples']:
        assert sample['executionVerified'] and sample['clockPairs']
        before={v['step']:v for v in copy.deepcopy(sample['stages'])}
        normalize(sample,sample['clockPairs'])
        phases={v['step']:v for v in sample['stages']}
        assert phases['BPMN SC']['end_time']==phases['Event Bus']['start_time']
        assert phases['Event Bus']['end_time']==phases['Executor']['start_time']
        assert phases['API Invoker']['end_time']==phases['BPMN SC']['start_time']
        assert phases['API Invoker2']['end_time']==phases['DMN SC']['start_time']
        assert abs(phases['Event Bus']['duration_ms']-sum(sample['eventBusBreakdown'][k]
            for k in ['chainCompletionToEventRecorded_ms','eventRecordedToExecutor_ms']))<.001
        for name,phase in phases.items():
            if name!='Event Bus':
                assert abs(phase['start_time']-before[name]['start_time'])<.001
                assert abs(phase['end_time']-before[name]['end_time'])<.001
        canonical[sample['attempt']]=sample
    for i,attempt in enumerate(report.get('attempts',[])):
        if attempt['attempt'] in canonical:
            report['attempts'][i]=copy.deepcopy(canonical[attempt['attempt']])
            raw=path.parent/'attempts'/f"attempt-{attempt['attempt']}"/'result.json'
            if raw.exists():save(raw,report['attempts'][i])
    export(report,path.parent)
    verification=path.parent/'verification.json'
    if verification.exists():
        checks=json.loads(verification.read_text())
        for check in checks:
            check.update(timingDefinitionVersion=2,bpmnScEventBusBoundaryIdentical=True,
                         eventBusExecutorBoundaryIdentical=True,eventBusIncludesEventIngestion=True)
        save(verification,checks)
    print(f'Recalculated {len(report["samples"])} saved rounds with full Event Bus; no requests sent.')


if __name__=='__main__':main()
