#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


MDA = Path(__file__).resolve().parent
ROOT = MDA.parent

ECORE = MDA / "b2c.ecore"
OCL = MDA / "check.ocl"
POSITIVE_XMI = MDA / "bpmn-positive" / "xmi"
POSITIVE_REPORT = MDA / "ocl-report-bpmn-positives" / "report.json"
TARGETED_MANIFEST = MDA / "bpmn-mutations" / "manifest.json"

RUN_RANDOM = MDA / "emf-random" / "run_instantiator.sh"
RUN_BATCH_VALIDATE = MDA / "run_ocl_validate_batch.sh"
RUN_MUTATIONS = MDA / "bpmn-mutations" / "generate_mutation_failures.py"


@dataclass(frozen=True)
class SampleRecord:
    split: str
    assigned_rule: str | None
    relative_path: str
    source_path: str
    metadata: dict


def parse_rule_quota(items: Iterable[str]) -> dict[str, int]:
    quotas: dict[str, int] = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"Invalid rule quota '{item}', expected RULE=COUNT")
        rule, count_text = item.split("=", 1)
        rule = rule.strip()
        if not rule:
            raise SystemExit(f"Invalid rule quota '{item}', empty rule")
        try:
            count = int(count_text)
        except ValueError as exc:
            raise SystemExit(f"Invalid rule quota '{item}', COUNT must be integer") from exc
        if count < 0:
            raise SystemExit(f"Invalid rule quota '{item}', COUNT must be >= 0")
        quotas[rule] = count
    return quotas


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_positive_report() -> None:
    if POSITIVE_REPORT.exists():
        return
    subprocess.run(
        [
            "bash",
            str(RUN_BATCH_VALIDATE),
            str(POSITIVE_XMI),
            str(ECORE),
            str(OCL),
            str(POSITIVE_REPORT.parent),
        ],
        cwd=ROOT,
        check=True,
    )


def ensure_targeted_manifest() -> None:
    if TARGETED_MANIFEST.exists():
        return
    subprocess.run(["python3", str(RUN_MUTATIONS)], cwd=ROOT, check=True)


def safe_rule_name(rule: str) -> str:
    return rule.replace("::", "__").replace("/", "_").replace(" ", "_")


def copy_sample(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def safe_exists(path: Path) -> bool:
    try:
        return path.exists()
    except PermissionError:
        return False


def resolve_positive_source(model: dict) -> Path:
    by_report = Path(model["absolutePath"])
    if safe_exists(by_report):
        return by_report
    by_relative = POSITIVE_XMI / model["relativePath"]
    if safe_exists(by_relative):
        return by_relative
    by_name = POSITIVE_XMI / Path(model["relativePath"]).name
    if safe_exists(by_name):
        return by_name
    raise SystemExit(f"Positive source model not found for {model['relativePath']}")


def resolve_targeted_source(item: dict) -> Path:
    by_manifest = Path(item["mutantXmi"])
    if safe_exists(by_manifest):
        return by_manifest
    by_name = MDA / "bpmn-mutations" / "xmi" / Path(item["mutantXmi"]).name
    if safe_exists(by_name):
        return by_name
    raise SystemExit(f"Targeted mutant model not found for {item['mutantXmi']}")


def choose_without_reuse(candidates: list[dict], quota: int, label: str) -> list[dict]:
    if quota > len(candidates):
        raise SystemExit(f"Not enough {label} samples: need {quota}, available {len(candidates)}")
    return candidates[:quota]


def build_positive_samples(output_dir: Path, quota: int) -> list[SampleRecord]:
    if quota <= 0:
        return []

    ensure_positive_report()
    report = load_json(POSITIVE_REPORT)
    candidates = [
        model for model in report["models"]
        if model.get("ok") is True
    ]
    candidates.sort(key=lambda item: item["relativePath"])
    selected = choose_without_reuse(candidates, quota, "positive")

    samples: list[SampleRecord] = []
    for index, model in enumerate(selected):
        src = resolve_positive_source(model)
        dst = output_dir / "positive" / f"{index:03d}_{src.name}"
        copy_sample(src, dst)
        samples.append(
            SampleRecord(
                split="positive",
                assigned_rule=None,
                relative_path=str(dst.relative_to(output_dir)),
                source_path=str(src),
                metadata={
                    "ok": True,
                    "relativePath": model["relativePath"],
                    "violationCount": model["violationCount"],
                },
            )
        )
    return samples


def build_targeted_negative_samples(output_dir: Path, quotas: dict[str, int]) -> list[SampleRecord]:
    if not quotas:
        return []

    ensure_targeted_manifest()
    manifest = load_json(TARGETED_MANIFEST)
    samples: list[SampleRecord] = []

    for rule, quota in sorted(quotas.items()):
        exact_candidates = [
            item for item in manifest
            if item.get("ok") is False
            and item.get("intendedRule") == rule
            and item.get("actualRules") == [rule]
        ]
        exact_candidates.sort(key=lambda item: item["mutantXmi"])
        selected = choose_without_reuse(exact_candidates, quota, f"targeted negatives for {rule}")

        for index, item in enumerate(selected):
            src = resolve_targeted_source(item)
            dst = output_dir / "targeted_negative" / safe_rule_name(rule) / f"{index:03d}_{src.name}"
            copy_sample(src, dst)
            samples.append(
                SampleRecord(
                    split="targeted_negative",
                    assigned_rule=rule,
                    relative_path=str(dst.relative_to(output_dir)),
                    source_path=str(src),
                    metadata={
                        "mutantName": item["mutantName"],
                        "mutation": item["mutation"],
                        "intendedRule": item["intendedRule"],
                        "actualRules": item["actualRules"],
                        "violationCount": item["violationCount"],
                    },
                )
            )
    return samples


def run_random_batch(work_dir: Path, batch_size: int, structure_size: int, seed: int) -> tuple[Path, dict]:
    subprocess.run(
        [
            "bash",
            str(RUN_RANDOM),
            "-m",
            str(ECORE),
            "-n",
            str(batch_size),
            "-s",
            str(structure_size),
            "-e",
            str(seed),
        ],
        cwd=work_dir,
        check=True,
    )
    xmi_dir = work_dir / "b2c"
    report_dir = work_dir / "report"
    subprocess.run(
        [
            "bash",
            str(RUN_BATCH_VALIDATE),
            str(xmi_dir),
            str(ECORE),
            str(OCL),
            str(report_dir),
        ],
        cwd=ROOT,
        check=True,
    )
    return xmi_dir, load_json(report_dir / "report.json")


def build_random_negative_samples(
    output_dir: Path,
    quotas: dict[str, int],
    batch_size: int,
    structure_size: int,
    start_seed: int,
    max_batches: int,
    match_mode: str,
) -> list[SampleRecord]:
    if not quotas:
        return []

    remaining = dict(quotas)
    samples: list[SampleRecord] = []
    used_source_paths: set[str] = set()

    with tempfile.TemporaryDirectory(prefix="mda-random-", dir=str(output_dir)) as tmp_root:
        tmp_root_path = Path(tmp_root)
        for batch_index in range(max_batches):
            if all(count <= 0 for count in remaining.values()):
                break

            batch_dir = tmp_root_path / f"batch_{batch_index:03d}"
            batch_dir.mkdir(parents=True, exist_ok=True)
            _, report = run_random_batch(
                batch_dir,
                batch_size=batch_size,
                structure_size=structure_size,
                seed=start_seed + batch_index,
            )

            for model in report["models"]:
                if model.get("ok") is True:
                    continue

                src = str(Path(model["absolutePath"]))
                if src in used_source_paths:
                    continue

                codes = [v.get("code") for v in model.get("violations", []) if v.get("code")]
                code_set = set(codes)
                if not code_set:
                    continue

                for rule in sorted(remaining):
                    if remaining[rule] <= 0:
                        continue
                    if rule not in code_set:
                        continue
                    if match_mode == "exact" and code_set != {rule}:
                        continue

                    used_source_paths.add(src)
                    dst = (
                        output_dir
                        / "random_negative"
                        / safe_rule_name(rule)
                        / f"{quotas[rule] - remaining[rule]:03d}_{Path(src).name}"
                    )
                    copy_sample(Path(src), dst)
                    samples.append(
                        SampleRecord(
                            split="random_negative",
                            assigned_rule=rule,
                            relative_path=str(dst.relative_to(output_dir)),
                            source_path=src,
                            metadata={
                                "relativePath": model["relativePath"],
                                "actualRules": sorted(code_set),
                                "violationCount": model["violationCount"],
                                "matchMode": match_mode,
                                "singleRule": code_set == {rule},
                            },
                        )
                    )
                    remaining[rule] -= 1
                    break

        missing = {rule: count for rule, count in remaining.items() if count > 0}
        if missing:
            formatted = ", ".join(f"{rule}={count}" for rule, count in sorted(missing.items()))
            raise SystemExit(f"Random negative quotas not satisfied after {max_batches} batches: {formatted}")

    return samples


def write_summary(output_dir: Path, samples: list[SampleRecord], args: argparse.Namespace) -> None:
    manifest = []
    by_split: dict[str, int] = defaultdict(int)
    by_rule: dict[str, int] = defaultdict(int)

    for sample in samples:
        by_split[sample.split] += 1
        if sample.assigned_rule:
            by_rule[f"{sample.split}:{sample.assigned_rule}"] += 1
        manifest.append(
            {
                "split": sample.split,
                "assignedRule": sample.assigned_rule,
                "relativePath": sample.relative_path,
                "sourcePath": sample.source_path,
                "metadata": sample.metadata,
            }
        )

    summary = {
        "generatedAt": dt.datetime.now().astimezone().isoformat(),
        "config": {
            "positiveQuota": args.positive_quota,
            "targetedRules": parse_rule_quota(args.targeted),
            "randomRules": parse_rule_quota(args.random),
            "randomBatchSize": args.random_batch_size,
            "randomStructureSize": args.random_structure_size,
            "randomStartSeed": args.random_start_seed,
            "randomMaxBatches": args.random_max_batches,
            "randomMatchMode": args.random_match_mode,
        },
        "summary": {
            "totalSamples": len(samples),
            "bySplit": dict(sorted(by_split.items())),
            "byAssignedRule": dict(sorted(by_rule.items())),
        },
        "samples": manifest,
    }

    (output_dir / "dataset_manifest.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# Balanced Dataset Report",
        "",
        f"- Total samples: {len(samples)}",
    ]
    for split, count in sorted(by_split.items()):
        lines.append(f"- {split}: {count}")
    if by_rule:
        lines.extend(["", "## Assigned Rule Counts", ""])
        for rule, count in sorted(by_rule.items()):
            lines.append(f"- {rule}: {count}")
    lines.append("")
    lines.append("See `dataset_manifest.json` for per-sample metadata.")
    (output_dir / "dataset_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build a balanced experiment dataset from positive models, targeted mutations, "
            "and random EMF samples filtered by OCL violation rules."
        )
    )
    parser.add_argument("--output-dir", required=True, help="Directory to write dataset files into")
    parser.add_argument("--positive-quota", type=int, default=0, help="Number of OCL-valid positive samples")
    parser.add_argument(
        "--targeted",
        action="append",
        default=[],
        metavar="RULE=COUNT",
        help="Targeted negative quota, backed by bpmn-mutations/manifest.json",
    )
    parser.add_argument(
        "--random",
        action="append",
        default=[],
        metavar="RULE=COUNT",
        help="Random negative quota, collected via emf-random + OCL filtering",
    )
    parser.add_argument("--random-batch-size", type=int, default=50, help="Random models generated per batch")
    parser.add_argument("--random-structure-size", type=int, default=200, help="Random generator -s parameter")
    parser.add_argument("--random-start-seed", type=int, default=12345, help="Seed for the first random batch")
    parser.add_argument("--random-max-batches", type=int, default=20, help="Maximum random generation batches")
    parser.add_argument(
        "--random-match-mode",
        choices=("contains", "exact"),
        default="contains",
        help="Rule filtering mode for random negatives",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.positive_quota < 0:
        raise SystemExit("--positive-quota must be >= 0")

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    targeted_quotas = parse_rule_quota(args.targeted)
    random_quotas = parse_rule_quota(args.random)

    samples: list[SampleRecord] = []
    samples.extend(build_positive_samples(output_dir, args.positive_quota))
    samples.extend(build_targeted_negative_samples(output_dir, targeted_quotas))
    samples.extend(
        build_random_negative_samples(
            output_dir,
            random_quotas,
            batch_size=args.random_batch_size,
            structure_size=args.random_structure_size,
            start_seed=args.random_start_seed,
            max_batches=args.random_max_batches,
            match_mode=args.random_match_mode,
        )
    )

    write_summary(output_dir, samples, args)
    print(f"Dataset written to: {output_dir}")
    print(f"Manifest: {output_dir / 'dataset_manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
