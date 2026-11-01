#!/usr/bin/env python3
"""Draw the retained three-round results; --round selects the current round ID."""
import argparse
import json
from pathlib import Path
from plot_timeline import plot

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT/'results-100/results.json')
    parser.add_argument('--output-dir', type=Path, default=ROOT/'results-100')
    parser.add_argument('--round', type=int, dest='round_number')
    parser.add_argument('--prefix', default='geth_message_timeline')
    args = parser.parse_args()
    report = json.loads(args.input.read_text())
    samples = [s for s in report['samples'] if s['status']=='passed' and
               (args.round_number is None or s['index']==args.round_number)]
    if not samples:
        raise ValueError('No retained result for this round')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    suffix = 'mean' if args.round_number is None else f'round{args.round_number}'
    plot(report, samples, args.output_dir/f'{args.prefix}_{suffix}')


if __name__ == '__main__':
    main()
