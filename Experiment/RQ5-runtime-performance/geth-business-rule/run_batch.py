#!/usr/bin/env python3
"""Run one fixed-policy batch, then verify and draw it. Safe to detach."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback
from datetime import datetime,timezone
from run_repeat import ROOT,save,OUTLIER_THRESHOLDS_MS


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rounds',type=int,default=100)
    parser.add_argument('--output',type=Path,default=ROOT/'results-100')
    parser.add_argument('--resume',action='store_true')
    args=parser.parse_args();batch=ROOT/'batch-100';batch.mkdir(exist_ok=True)
    record={'pid':os.getpid(),'status':'running','startedAt':datetime.now(timezone.utc).isoformat(),
        'requestedValidRounds':args.rounds,'output':str(args.output),'thresholds_ms':OUTLIER_THRESHOLDS_MS,
        'maxAttempts':300,'scriptSha256':{}}
    for name in ['run_repeat.py','http_observer.py','verify_results.py','draw.py','config.live.json']:
        content=(ROOT/name).read_bytes();record['scriptSha256'][name]=hashlib.sha256(content).hexdigest()
        (batch/'run-code').mkdir(exist_ok=True);(batch/'run-code'/name).write_bytes(content)
    save(batch/'status.json',record)
    try:
        command=[sys.executable,'-B',str(ROOT/'run_repeat.py'),'--rounds',str(args.rounds),
            '--output',str(args.output),'--filter-outliers','--max-attempts','300']
        if args.resume:command.append('--resume')
        subprocess.run(command,check=True)
        record['status']='verifying';save(batch/'status.json',record)
        subprocess.run([sys.executable,'-B',str(ROOT/'verify_results.py'),'--input',str(args.output/'results.json')],check=True)
        env=os.environ.copy();env['PYTHONPATH']='/tmp/geth-timing-plot-libs'+(':'+env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
        subprocess.run([sys.executable,'-B',str(ROOT/'draw.py'),'--input',str(args.output/'results.json')],check=True,env=env)
        record['status']='passed';record['finishedAt']=datetime.now(timezone.utc).isoformat()
    except Exception as exc:
        record['status']='failed';record['error']=str(exc);traceback.print_exc()
        raise
    finally:save(batch/'status.json',record)


if __name__=='__main__':main()
