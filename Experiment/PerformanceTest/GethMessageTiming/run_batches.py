#!/usr/bin/env python3
"""Run whole batches, then filter red > threshold and refill the deficit."""
import argparse
import copy
from datetime import datetime,timezone
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent


def save(path,value):
    temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n');temp.replace(path)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rounds',type=int,default=100,help='Final retained sample count')
    parser.add_argument('--max-red-seconds',type=float,default=25)
    parser.add_argument('--output',type=Path,default=ROOT/'results-100')
    args=parser.parse_args()
    if not 1<=args.rounds<=100 or args.max_red_seconds<=0:parser.error('Use 1–100 rounds and a positive threshold')
    if args.output.exists() and any(args.output.iterdir()):parser.error('Choose a new empty output directory')
    args.output.mkdir(parents=True,exist_ok=True)
    report=None;batch_number=0;retained=0
    while retained<args.rounds:
        batch_number+=1;requested=args.rounds-retained
        folder=args.output/'batches'/f'batch-{batch_number:03d}';folder.parent.mkdir(parents=True,exist_ok=True)
        log_path=folder.parent/(folder.name+'.log')
        command=[sys.executable,str(ROOT/'run_repeat.py'),'--rounds',str(requested),'--output',str(folder)]
        progress={'status':'running','phase':'executing_batch','currentBatch':batch_number,
                  'batchRequestedRounds':requested,'acceptedCount':retained,'targetAcceptedCount':args.rounds,
                  'maxRed_ms':args.max_red_seconds*1000,'lastUpdate':datetime.now(timezone.utc).isoformat()}
        save(args.output/'progress.json',progress)
        print(f'Batch {batch_number}: execute {requested} complete rounds; no red-threshold filtering inside this batch.',flush=True)
        with log_path.open('w') as log:
            completed=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
        if completed.returncode:
            progress.update(status='failed',phase='batch_worker_failed',log=str(log_path))
            save(args.output/'progress.json',progress)
            raise RuntimeError(f'Batch worker failed; see {log_path}')
        batch=json.loads((folder/'results.json').read_text());assert batch['status']=='passed'
        assert len(batch['samples'])==requested
        if report is None:
            report=copy.deepcopy(batch)
            report['samples']=[];report['attempts']=[];report['summary']=[];report['requestedRounds']=args.rounds
            report['sampleSelection']={'maxRed_ms':args.max_red_seconds*1000,
                'rule':'Execute a full batch first; exclude red > threshold after batch completion; refill exactly the deficit',
                'strategy':'batch_then_filter_then_refill','targetAcceptedCount':args.rounds,'acceptedCount':0,
                'totalAttempts':0,'excludedHighRedCount':0,'excludedInvalidTimingCount':0}
            report['batches']=[];report['status']='running'
        assert report['api']==batch['api'] and report['instanceIds']==batch['instanceIds']
        previous=retained
        for entry in batch['attempts']:
            sample=json.loads((folder/entry['rawFile']).read_text())
            sample['batchNumber']=batch_number;sample['batchRound']=sample['index'];sample['batchAttempt']=sample['attempt']
            sample['attempt']=len(report['attempts'])+1;sample['index']=len(report['samples'])+1
            reason=entry.get('reason');red=None
            if sample['status']=='passed':
                red=next(s['duration_ms'] for s in sample['stages'] if s['step']=='BPMN SC')
                if red>args.max_red_seconds*1000:
                    sample['status']='excluded_high_red';reason=f'Red {red:.6f}ms > {args.max_red_seconds*1000:.0f}ms; excluded after full batch completion'
                    sample['exclusionReason']=reason
                else:
                    report['samples'].append(sample)
            attempt_folder=args.output/'attempts'/f"attempt-{sample['attempt']:04d}";attempt_folder.mkdir(parents=True)
            save(attempt_folder/'result.json',sample)
            report['attempts'].append({'attempt':sample['attempt'],'candidateRound':sample['index'],
                'batchNumber':batch_number,'status':sample['status'],'red_ms':red,'reason':reason,
                'messageId':sample.get('messageId'),'operationId':sample.get('operation',{}).get('id'),
                'rawFile':str((attempt_folder/'result.json').relative_to(args.output))})
        retained=len(report['samples']);selection=report['sampleSelection']
        selection['acceptedCount']=retained;selection['totalAttempts']=len(report['attempts'])
        selection['excludedHighRedCount']=sum(e['status']=='excluded_high_red' for e in report['attempts'])
        selection['excludedInvalidTimingCount']=sum(e['status']=='excluded_invalid_timing' for e in report['attempts'])
        info={'batch':batch_number,'requestedRounds':requested,'verifiedRounds':len(batch['samples']),
              'totalAttempts':len(batch['attempts']),'acceptedAdded':retained-previous,
              'excludedHighRed':requested-(retained-previous),'remaining':args.rounds-retained,
              'source':str(folder.relative_to(args.output)/'results.json')}
        report['batches'].append(info)
        report['originalInstanceAfter']=batch['originalInstanceAfter'];report['counterAfter']=batch['counterAfter']
        save(args.output/'results.json',report);save(args.output/'attempts.json',report['attempts'])
        progress.update(phase='batch_filtered',acceptedCount=retained,**{'completedBatches':report['batches'],'selection':selection})
        save(args.output/'progress.json',progress)
        print(f'Batch {batch_number} complete: {requested} verified rounds; retained {retained-previous}, red-excluded {info["excludedHighRed"]}; total retained {retained}/{args.rounds}, next deficit {args.rounds-retained}.',flush=True)
    report['status']='passed';report['activeAttempt']=None;report['finishedAt']=datetime.now(timezone.utc).isoformat()
    assert len(report['samples'])==args.rounds
    assert len({s['messageId'] for s in report['samples']})==args.rounds
    assert len({s['ipfsCid'] for s in report['samples']})==args.rounds
    assert len({s['operation']['id'] for s in report['samples']})==args.rounds
    assert all(next(v['duration_ms'] for v in s['stages'] if v['step']=='BPMN SC')<=args.max_red_seconds*1000 for s in report['samples'])
    from summarize import export_report
    export_report(report,args.output)
    progress.update(status='passed',phase='complete',acceptedCount=retained)
    save(args.output/'progress.json',progress)
    print(f'Complete: {retained} retained samples from {len(report["attempts"])} attempts in {batch_number} batches. Results: {args.output}',flush=True)


if __name__=='__main__':main()
