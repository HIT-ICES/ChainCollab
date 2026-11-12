#!/usr/bin/env python3
"""Offline seven-stage BusinessRule mean timeline from verified saved samples."""
import argparse
import json
from pathlib import Path
from statistics import mean


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=Path(__file__).resolve().parent/'results-100/results.json')
    args=parser.parse_args();report=json.loads(args.input.read_text())
    assert report['status']=='passed' and len(report['samples'])==report['requestedRounds']
    assert report.get('timingDefinitionVersion')==2, 'Recalculate the saved timestamps with the updated Event Bus definition first'
    for sample in report['samples']:
        stages={v['step']:v for v in sample['stages']}
        assert stages['BPMN SC']['end_time']==stages['Event Bus']['start_time']
        assert stages['Event Bus']['end_time']==stages['Executor']['start_time']
    phases=['API Invoker','BPMN SC','Event Bus','Executor','IPFS','API Invoker2','DMN SC']
    colors=['#1f77b4','#ff7f0e','#2ca02c','#d62728','#9467bd','#8c564b','#e377c2']
    data=[]
    for name,color in zip(phases,colors):
        rows=[next(v for v in s['stages'] if v['step']==name) for s in report['samples']]
        assert all(v['valid'] for v in rows)
        start=mean(v['start_time'] for v in rows);end=mean(v['end_time'] for v in rows)
        data.append({'step':name,'start_time':start,'end_time':end,'duration_ms':end-start,'color':color})
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'pdf.fonttype':42})
    fig,ax=plt.subplots(figsize=(11.5,6.5));fig.subplots_adjust(left=.17,right=.97,top=.84,bottom=.2)
    extent=max(v['end_time'] for v in data)
    for i,v in enumerate(data):
        ax.barh(i,v['duration_ms'],left=v['start_time'],height=.42,color=v['color'],alpha=.8,edgecolor='#444444',linewidth=.8)
        label=f"{v['duration_ms']:.2f}ms"
        if v['duration_ms']<extent*.08:
            ax.annotate(label,(v['end_time'],i),xytext=(7,0),textcoords='offset points',va='center',fontsize=9)
        else:ax.text((v['start_time']+v['end_time'])/2,i,label,ha='center',va='center',fontsize=9)
    ax.set_yticks(range(7),phases);ax.set_ylim(6.5,-.5);ax.set_xlim(0,extent*1.05)
    ax.grid(True,linestyle='--',linewidth=.7,alpha=.4);ax.set_axisbelow(True)
    ax.set_xlabel('Timeline (ms)',labelpad=9);ax.set_ylabel('Steps')
    ax.set_title('Timeline of Steps',fontsize=15,color='#4e79a7',pad=30)
    fig.text(.57,.865,f"Fabric BusinessRule · mean of {len(report['samples'])} runs · original generated contract",ha='center',fontsize=9,color='#555555')
    fig.text(.17,.055,'Each round uses a fresh instance; DMN publication and initialization are outside measurement.\n'
        'Event Bus starts at BPMN SC completion. Executor includes IPFS and API2; overlapping intervals must not be summed.',fontsize=8,color='#555555',linespacing=1.5)
    stem=args.input.parent/'fabric_businessrule_timeline_mean'
    for suffix in ['png','pdf','svg']:fig.savefig(stem.with_suffix('.'+suffix),dpi=300,facecolor='white')
    plt.close(fig);stem.with_suffix('.json').write_text(json.dumps(data,indent=2)+'\n');print(stem)


if __name__=='__main__':main()
