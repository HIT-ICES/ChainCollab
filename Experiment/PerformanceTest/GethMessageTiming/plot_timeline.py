"""Draw the original four-stage layout using the saved measured intervals."""
import json
from pathlib import Path
from statistics import mean
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PHASES = [
    ("Private Data Bus", "#1f77b4"),
    ("IPFS", "#ff7f0e"),
    ("API Invoker", "#2ca02c"),
    ("BPMN SC", "#d62728"),
]


def plot(report, samples, stem):
    data = []
    for name, color in PHASES:
        intervals = []
        for sample in samples:
            origin = sample["fileUpload"]["start"]
            stage = next(item for item in sample["stages"] if item["step"] == name)
            assert stage["valid"] and stage["end_time"] >= stage["start_time"]
            intervals.append((stage["start_time"] - origin, stage["end_time"] - origin))
        start, end = mean(v[0] for v in intervals), mean(v[1] for v in intervals)
        data.append({"step": name, "start_time": start, "end_time": end,
                     "duration_ms": end - start, "color": color})
    stem = Path(stem)
    stem.with_suffix(".json").write_text(json.dumps(data, indent=2) + "\n")

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "pdf.fonttype": 42, "ps.fonttype": 42})
    fig, ax = plt.subplots(figsize=(11.5, 5.4))
    fig.subplots_adjust(left=0.18, right=0.97, top=0.83, bottom=0.24)
    extent = max(row["end_time"] for row in data)
    for i, row in enumerate(data):
        ax.barh(i, row["duration_ms"], left=row["start_time"], height=0.4,
                color=row["color"], edgecolor="#444444", linewidth=0.8, alpha=0.8)
        label = f"{row['duration_ms']:.2f}ms"
        if row["duration_ms"] < extent * 0.075:
            ax.annotate(label, (row["end_time"], i), xytext=(7, 0),
                        textcoords="offset points", ha="left", va="center", fontsize=9)
        else:
            ax.text((row["start_time"] + row["end_time"]) / 2, i, label,
                    ha="center", va="center", fontsize=9)
    ax.set_yticks(range(4), [name for name, _ in PHASES])
    ax.set_ylim(3.45, -0.45)
    ax.set_xlim(0, extent * 1.05)
    ax.grid(True, linestyle="--", linewidth=0.7, alpha=0.4)
    ax.set_axisbelow(True)
    ax.set_xlabel("Timeline (ms)", labelpad=9)
    ax.set_ylabel("Steps", labelpad=12)
    ax.set_title("Timeline of Steps", fontsize=15, color="#4e79a7", pad=27)
    detail = ('round ' + str(samples[0]['index']) if len(samples) == 1 else 'mean of ' + str(len(samples)) + ' runs')
    threshold = report.get('sampleSelection', {}).get('maxRed_ms')
    if threshold is not None:
        detail += f" · retained red ≤ {threshold/1000:g}s"
    fig.text(0.575, 0.855, f"Geth · {detail} · {report['file']['bytes']} byte file",
             ha="center", fontsize=9, color="#555555")
    audited = report.get("metricAudit")
    ipfs_label = ("Orange: FireFly publication request to successful CID response."
                  if report.get("metricsVersion", 0) >= 9 else "Orange: FireFly-to-IPFS /add call.")
    footer = ("Blue: upload to participating nodes' data/pin confirmation. Green: API request to Operation creation.\n"
              + ipfs_label + " Red: same Operation creation to business invoke-success event."
              if audited else
              "File-upload API is included in blue. Orange: IPFS publish API; green: contract API admission.\n"
              "Red: Operation creation to invoke-success event. All bars preserve the measured linear time scale.")
    fig.text(0.18, 0.045,
             footer,
             fontsize=8, color="#555555", linespacing=1.5)
    for extension in ("png", "pdf", "svg"):
        fig.savefig(stem.with_suffix("." + extension), dpi=300, facecolor="white")
    plt.close(fig)
    print(stem)

