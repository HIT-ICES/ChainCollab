#!/usr/bin/env python3
import json
import random
from pathlib import Path


def _require_ucimlrepo():
    try:
        from ucimlrepo import fetch_ucirepo  # type: ignore
        return fetch_ucirepo
    except Exception as exc:
        raise SystemExit(
            "Missing dependency `ucimlrepo`. Install with: python3 -m pip install ucimlrepo\n"
            f"detail: {exc}"
        )


def _clamp_uint(v: float) -> int:
    if v < 0:
        return 0
    return int(round(v))


def _sample_values(values, rounds: int):
    if len(values) <= rounds:
        return values
    step = max(1, len(values) // rounds)
    sampled = values[::step][:rounds]
    return sampled


def _build_profiles(truth: int, prev_truth: int, idx: int, rng: random.Random, node_count: int):
    # 1) 轻微噪声场景：各节点围绕同一真值轻微波动
    normal = [_clamp_uint(truth * (1.0 + rng.gauss(0.0, 0.0025))) for _ in range(node_count)]

    # 2) 单节点异常值场景：某一节点出现显著偏离
    single_outlier = [_clamp_uint(truth * (1.0 + rng.gauss(0.0, 0.007))) for _ in range(node_count)]
    outlier_idx = idx % node_count
    if idx % 2 == 0:
        single_outlier[outlier_idx] = _clamp_uint(single_outlier[outlier_idx] * 1.45)
    else:
        single_outlier[outlier_idx] = _clamp_uint(single_outlier[outlier_idx] * 0.60)

    # 3) 存在缺失值场景：部分缺失 + 少量陈旧回报
    missing_stale = []
    for i in range(node_count):
        if (idx + i) % 16 == 0:
            missing_stale.append(None)
            continue
        if i == 2 and idx % 7 == 0:
            missing_stale.append(_clamp_uint(prev_truth))
            continue
        missing_stale.append(_clamp_uint(truth * (1.0 + rng.gauss(0.0, 0.009))))

    return {
        "轻微噪声场景": normal,
        "单节点异常值场景": single_outlier,
        "存在缺失值场景": missing_stale,
    }


def main():
    fetch_ucirepo = _require_ucimlrepo()
    root = Path(__file__).resolve().parent.parent
    out_path = root / "dataset" / "industrial_data_aggregation_scenarios.json"

    dataset_cfg = [
        {
            "uci_id": 864,
            "dataset_name": "Room Occupancy Estimation",
            "dataset_ref": "https://archive.ics.uci.edu/dataset/864/room+occupancy+estimation",
            "metric_family": "Temp",
            "sensor_cols": ["S1_Temp", "S2_Temp", "S3_Temp", "S4_Temp"],
            "scale": 100,
            "rounds": 90,
        },
        {
            "uci_id": 864,
            "dataset_name": "Room Occupancy Estimation",
            "dataset_ref": "https://archive.ics.uci.edu/dataset/864/room+occupancy+estimation",
            "metric_family": "Light",
            "sensor_cols": ["S1_Light", "S2_Light", "S3_Light", "S4_Light"],
            "scale": 10,
            "rounds": 90,
        },
    ]

    scenarios = []
    rng = random.Random(20260227)

    for cfg in dataset_cfg:
        ds = fetch_ucirepo(id=cfg["uci_id"])
        features = ds.data.features
        if features is None:
            raise SystemExit(f"dataset id={cfg['uci_id']} has no features")
        for col in cfg["sensor_cols"]:
            if col not in features.columns:
                raise SystemExit(f"dataset id={cfg['uci_id']} missing sensor column `{col}`")

        sensor_df = features[cfg["sensor_cols"]].dropna().astype(float)
        sampled_rows = _sample_values(sensor_df.values.tolist(), cfg["rounds"])

        rounds = []
        prev_truth = None
        for idx, row_vals in enumerate(sampled_rows):
            sensor_vals = [v * cfg["scale"] for v in row_vals]
            truth = _clamp_uint(sum(sensor_vals) / len(sensor_vals))
            profiles = _build_profiles(
                truth,
                prev_truth if prev_truth is not None else truth,
                idx,
                rng,
                len(cfg["sensor_cols"]),
            )
            rounds.append(
                {
                    "idx": idx,
                    "truth": truth,
                    "profiles": profiles,
                }
            )
            prev_truth = truth

        scenarios.append(
            {
                "uci_id": cfg["uci_id"],
                "dataset_name": cfg["dataset_name"],
                "dataset_ref": cfg["dataset_ref"],
                "metric_col": cfg["metric_family"],
                "sensor_cols": cfg["sensor_cols"],
                "scale": cfg["scale"],
                "round_count": len(rounds),
                "rounds": rounds,
            }
        )

    payload = {
        "generated_by": "prepare-industrial-data-aggregation.py",
        "generated_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "oracle_node_count": len(dataset_cfg[0]["sensor_cols"]),
        "profiles": [
            {
                "name": "轻微噪声场景",
                "desc": "同一指标多传感器常规观测（轻微高斯噪声）"
            },
            {
                "name": "单节点异常值场景",
                "desc": "单个节点出现显著偏离值（上冲或下冲）"
            },
            {
                "name": "存在缺失值场景",
                "desc": "部分节点缺失上报，部分节点上报陈旧值"
            },
        ],
        "profile_weights": {
            "轻微噪声场景": [1, 1, 1, 1],
            "单节点异常值场景": [1, 1, 1, 1],
            "存在缺失值场景": [1, 1, 1, 1]
        },
        "hetero_gas_eval": {
            "enabled": True,
            "weights": [45, 30, 15, 10],
            "note": "仅用于加权聚合的gas测算，不纳入精度对比"
        },
        "scenarios": scenarios,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"industrial aggregation dataset -> {out_path}")


if __name__ == "__main__":
    main()
