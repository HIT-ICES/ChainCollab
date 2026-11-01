"""Read-only audit of Message file timing runs against FireFly/IPFS and connector records."""
import datetime
import json
from pathlib import Path
import re
from statistics import mean
import subprocess
import requests

ROOT = Path(__file__).resolve().parent.parent


def epoch_ms(value):
    # Go timestamps may have nanoseconds; datetime on Python 3.10 accepts six digits.
    text = value.removesuffix("Z")
    if "." in text:
        base, fraction = text.split(".")
        text = base + "." + fraction[:6]
    return datetime.datetime.fromisoformat(text + "+00:00").timestamp() * 1000


def fetch(url):
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


def audit(report, scope="contract"):
    assert scope == "contract", "API Invoker measures the business contract request"
    first = min(s["fileUpload"]["start"] for s in report["samples"]) / 1000 - 2
    last = max(s["ipfsPublishRequest"]["end"] for s in report["samples"]) / 1000 + 2
    iso = lambda value: datetime.datetime.fromtimestamp(value, datetime.timezone.utc).isoformat()
    command = ["docker", "logs", "--since", iso(first), "--until", iso(last), "cello_forge-qlt_firefly_core_1"]
    logs = subprocess.run(command, capture_output=True, text=True, check=True)
    lines = (logs.stdout + logs.stderr).splitlines()
    details = []
    for sample in report["samples"]:
        cid = sample["ipfsCid"]
        published = [i for i, line in enumerate(lines) if f"IPFS published {cid} " in line]
        assert len(published) == 1, (cid, published)
        at = published[0]
        # Serial publish calls: require a unique successful /add response in
        # this request's time window and immediately before this CID is logged.
        candidates = []
        for i, line in enumerate(lines[:at]):
            match = re.search(r"\[([^]]+)\].*<== POST http://ipfs_1:5001/api/v0/add \[200\] \(([\d.]+)ms\) breq=(\S+)", line)
            if match and abs(epoch_ms(match[1]) - epoch_ms(re.match(r"\[([^]]+)\]", lines[at])[1])) <= 5:
                candidates.append((i, match))
        assert len(candidates) == 1, (cid, len(candidates))
        end_index, match = candidates[0]
        breq = match[3]
        starts = [line for line in lines[:end_index] if "==> POST http://ipfs_1:5001/api/v0/add" in line and f"breq={breq} " in line]
        assert len(starts) == 1
        duration = float(match[2])
        ipfs_start = epoch_ms(re.match(r"\[([^]]+)\]", starts[0])[1])
        # Log timestamps have millisecond precision, while the HTTP logger's
        # monotonic elapsed duration has hundredth-millisecond precision.
        ipfs_end = ipfs_start + duration
        op_id = sample["ipfsUploadOperation"]["id"]
        op_lines = [line for line in lines if f"Executing sharedstorage_upload_blob operation {op_id} " in line]
        assert len(op_lines) == 1
        assert sample["ipfsUploadOperation"]["output"]["payloadRef"] == cid

        transaction = fetch("http://127.0.0.1:5202/transactions/default:" + sample["operation"]["id"])
        assert transaction["transactionHash"] == sample["operation"]["output"]["transactionHash"]
        assert transaction["status"] == "Succeeded" and transaction["receipt"]["success"] is True
        receipts = [a for h in transaction["history"] for a in h.get("actions", []) if a["action"] == "ReceiveReceipt"]
        assert len(receipts) == 1
        submit = epoch_ms(transaction["firstSubmit"])
        receipt = epoch_ms(receipts[0]["time"])
        assert receipt >= submit
        api = sample["invokeRequest"]
        created = epoch_ms(sample["operation"]["created"])
        success_events = [e for e in sample["events"]
                          if e["type"] == "blockchain_invoke_op_succeeded"
                          and e.get("reference") == sample["operation"]["id"]
                          and e.get("tx") == sample["operation"]["tx"]]
        assert len(success_events) == 1
        succeeded = epoch_ms(success_events[0]["created"])
        blue = next(s for s in sample["stages"] if s["step"] == "Private Data Bus")
        assert sample["messageFinal"]["state"] == sample["receiverMessage"]["state"] == "confirmed"
        details.append({
            "round": sample["index"], "instanceId": sample["instanceId"], "cid": cid,
            "apiScope": scope, "apiCompleteHttp_ms": api["end"] - api["start"],
            "contractApiCompleteHttp_ms": sample["invokeRequest"]["end"] - sample["invokeRequest"]["start"],
            "fileUploadApiCompleteHttp_ms": sample["fileUpload"]["end"] - sample["fileUpload"]["start"],
            "ipfsInternalHttp_ms": duration, "chainSubmitToReceipt_ms": receipt - submit,
            "ipfsEvidence": [op_lines[0], starts[0], lines[end_index], lines[at]],
            "connectorTransaction": transaction,
            "stages": [dict(blue),
                       {"step": "IPFS", "start_time": ipfs_start, "end_time": ipfs_end, "duration_ms": duration, "valid": True},
                       {"step": "API Invoker", "start_time": api["start"], "end_time": created, "duration_ms": created - api["start"], "valid": created >= api["start"]},
                       {"step": "BPMN SC", "start_time": created, "end_time": succeeded, "duration_ms": succeeded - created, "valid": succeeded >= created}],
        })
    summary = [{"step": name, "count": len(details),
                "mean_ms": mean(next(s["duration_ms"] for s in d["stages"] if s["step"] == name) for d in details)}
               for name in ["Private Data Bus", "IPFS", "API Invoker", "BPMN SC"]]
    result = {"apiScope": scope, "source": "geth_message_ipfs_test_result.json", "rounds": details, "summary": summary,
              "notes": ["Read-only reanalysis of the same transactions; no new benchmark or contract deployment",
                        "IPFS is the internal FireFly→IPFS /api/v0/add HTTP duration, matched to CID and Operation",
                        "Green and red share the same Operation.created; red ends at the correlated business invoke-success event",
                        "Blue covers only the two participating FireFly organizations, not all three organizations"]}
    return result


if __name__ == "__main__":
    report = json.loads((ROOT / "results" / "results.json").read_text())
    result = audit(report)
    print(json.dumps(result["summary"], indent=2))
