#!/usr/bin/env python3
"""Draw Fabric mean intervals from saved results only; never contact services."""
import argparse
import json
from pathlib import Path
from statistics import mean


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True, help='results.json from run_repeat.py')
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    report = json.loads(args.input.read_text())
    if report.get('platform') != 'fabric' or report.get('status') != 'passed':
        raise ValueError('A completed Fabric report is required')
    samples = report['samples']
    if not samples or len(samples) != report['sampleSelection']['targetAcceptedCount']:
        raise ValueError('Incomplete retained sample count')
    data = []
    for name, color in [('Private Data Bus', '#1f77b4'), ('IPFS', '#ff7f0e'),
                        ('API Invoker', '#2ca02c'), ('BPMN SC', '#d62728')]:
        intervals = []
        for sample in samples:
            if sample['status'] != 'passed' or not sample['executionVerified']:
                raise ValueError('Unverified sample')
            origin = sample['fileUpload']['start']
            stage = next(v for v in sample['stages'] if v['step'] == name)
            if not stage['valid'] or stage['end_time'] < stage['start_time']:
                raise ValueError('Invalid measured interval')
            intervals.append((stage['start_time']-origin, stage['end_time']-origin))
        start, end = mean(v[0] for v in intervals), mean(v[1] for v in intervals)
        data.append(dict(step=name, start_time=start, end_time=end, duration_ms=end-start, color=color))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'pdf.fonttype': 42})
    fig, ax = plt.subplots(figsize=(11.5, 5.4))
    fig.subplots_adjust(left=.18, right=.97, top=.83, bottom=.24)
    extent = max(v['end_time'] for v in data)
    for i, row in enumerate(data):
        ax.barh(i, row['duration_ms'], left=row['start_time'], height=.4,
                color=row['color'], edgecolor='#444444', linewidth=.8, alpha=.8)
        label = f"{row['duration_ms']:.2f}ms"
        if row['duration_ms'] < extent*.075:
            ax.annotate(label, (row['end_time'], i), xytext=(7, 0), textcoords='offset points', va='center', fontsize=9)
        else:
            ax.text((row['start_time']+row['end_time'])/2, i, label, ha='center', va='center', fontsize=9)
    ax.set_yticks(range(4), [row['step'] for row in data]); ax.set_ylim(3.45, -.45)
    ax.set_xlim(0, extent*1.05); ax.grid(True, linestyle='--', linewidth=.7, alpha=.4)
    ax.set_axisbelow(True); ax.set_xlabel('Timeline (ms)', labelpad=9); ax.set_ylabel('Steps', labelpad=12)
    ax.set_title('Timeline of Steps', fontsize=15, color='#4e79a7', pad=27)
    limit = report['sampleSelection'].get('maxRed_ms')
    detail = f"Fabric · mean of {len(samples)} runs"
    if limit is not None:
        detail += f" · retained red ≤ {limit/1000:g}s"
    fig.text(.575, .855, detail + f" · {report['file']['bytes']} byte file", ha='center', fontsize=9, color='#555555')
    fig.text(.18, .045,
        "Blue: upload to participating nodes' data/pin confirmation. Green: API request to Operation creation.\n"
        'Orange: FireFly publication request to successful CID response. Red: same Operation creation to business invoke-success event.',
        fontsize=8, color='#555555', linespacing=1.5)
    output = args.output_dir or args.input.parent
    output.mkdir(parents=True, exist_ok=True)
    stem = output / 'fabric_message_timeline_mean'
    for extension in ['png', 'pdf', 'svg']:
        fig.savefig(stem.with_suffix('.'+extension), dpi=300, facecolor='white')
    plt.close(fig)
    stem.with_suffix('.json').write_text(json.dumps(data, indent=2)+'\n')
    print(stem)


if __name__ == '__main__':
    main()
