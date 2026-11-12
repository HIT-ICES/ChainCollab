"""Experiment-only wall/monotonic clock bridge; never changes the system clock."""
import bisect
from collections import deque
import threading
import time
from audit_metrics import epoch_ms

SAMPLES = deque(maxlen=900000)


def read_clock():
    a = time.monotonic_ns() / 1e6
    wall = time.time_ns() / 1e6
    b = time.monotonic_ns() / 1e6
    return {"wall_ms": wall, "monotonic_ms": (a + b) / 2, "readError_ms": (b - a) / 2}


def sample_forever():
    while True:
        point = read_clock()
        SAMPLES.append((point["wall_ms"], point["monotonic_ms"]))
        time.sleep(.005)


threading.Thread(target=sample_forever, daemon=True).start()


def normalize(report, pairs=None):
    """Map wall events through recorded clock segments, rejecting ambiguous matches.

    Backward clock steps can produce more than one solution. Such a sample is
    rejected rather than choosing the prettier placement. Bounds are independent
    browser observations of the same operation.
    """
    if pairs is None:
        # A standalone runner can normalize immediately after the final read,
        # before the next 5ms sampler tick. Wait for a sample bracketing the end.
        target = max(s["observedFinishedRaw"] +
                     s["clockSyncAfter"]["monotonic_ms"] -
                     (s["clockSyncAfter"]["browserBefore"] + s["clockSyncAfter"]["browserAfter"]) / 2
                     for s in report["samples"])
        deadline = time.monotonic() + 1
        while (not SAMPLES or SAMPLES[-1][1] < target + 2) and time.monotonic() < deadline:
            time.sleep(.005)
        pairs = list(SAMPLES)
    for s in report["samples"]:
        syncs = [s["clockSyncBefore"], s["clockSyncAfter"]]
        offsets = [p["monotonic_ms"] - (p["browserBefore"] + p["browserAfter"]) / 2 for p in syncs]
        error = max((p["browserAfter"] - p["browserBefore"]) / 2 + p["readError_ms"] for p in syncs)
        assert abs(offsets[1] - offsets[0]) < 10, ("Browser/observer clock drift", offsets)
        offset = sum(offsets) / 2
        raw = lambda x: x + offset
        start_mono = raw(s["fileUpload"]["clock"]["rawStart"])
        stop_mono = raw(s["observedFinishedRaw"])
        local = [(w, m) for w, m in pairs if start_mono - 200 <= m <= stop_mono + 200]
        assert local and local[0][1] <= start_mono and local[-1][1] >= stop_mono
        origin = s["fileUpload"]["start"]
        mapping_evidence = []

        def event(wall, lower, upper, label):
            candidates = []
            for (w1, m1), (w2, m2) in zip(local, local[1:]):
                # Interpolate only continuous segments; never bridge a clock step.
                if abs((w2 - w1) - (m2 - m1)) > 2:
                    continue
                if w1 - .6 <= wall <= w2 + .6:
                    mono = m1 + wall - w1
                    if lower - error - 2 <= mono <= upper + error + 2:
                        candidates.append(mono)
            assert candidates, ("No clock match", s["index"], label, wall)
            assert max(candidates) - min(candidates) < 3, ("Ambiguous wall timestamp", s["index"], label, candidates)
            mono = sum(candidates) / len(candidates)
            mapping_evidence.append({"event": label, "wall_ms": wall, "monotonic_ms": mono,
                                     "spread_ms": max(candidates) - min(candidates)})
            return mono

        stages = {v["step"]: v for v in s["stages"]}
        converted = []
        invoke_start = raw(s["invokeRequest"]["clock"]["rawStart"])
        invoke_end = raw(s["invokeRequest"]["clock"]["rawEnd"])
        pub_start = raw(s["ipfsPublishRequest"]["clock"]["rawStart"])
        pub_end = raw(s["ipfsPublishRequest"]["clock"]["rawEnd"])
        ipfs = stages["IPFS"]
        if report.get("metricsVersion", 0) >= 9:
            # Full FireFly publish request through successful CID response.
            assert s["ipfsUploadOperation"]["status"] == "Succeeded"
            assert s["ipfsUploadOperation"]["output"]["payloadRef"] == s["ipfsCid"]
            assert s["senderPublishedData"]["blob"]["public"] == s["ipfsCid"]
            ipfs_start, ipfs_end = pub_start, pub_end
        else:
            ipfs_start = event(ipfs["start_time"], pub_start, pub_end, "IPFS add start")
            ipfs_end = ipfs_start + ipfs["duration_ms"]
        operation = s["operation"]
        assert s["invokeResponse"]["id"] == operation["id"]
        assert s["invokeResponse"]["created"] == operation["created"]
        success_events = [e for e in s["events"]
                          if e["type"] == "blockchain_invoke_op_succeeded"
                          and e.get("reference") == operation["id"]
                          and e.get("tx") == operation["tx"]]
        assert len(success_events) == 1, ("Expected one correlated business success event", s["index"])
        success_event = success_events[0]
        operation_created = event(epoch_ms(operation["created"]), invoke_start, invoke_end, "business Operation.created")
        success = event(epoch_ms(success_event["created"]), operation_created, stop_mono, "business invoke succeeded")
        s["businessTimingBoundary"] = {"operationId": operation["id"], "transactionId": operation["tx"],
            "operationCreated": operation["created"], "successEventId": success_event["id"],
            "successEventCreated": success_event["created"],
            "sharedBoundaryMonotonic_ms": operation_created}
        blue_ends = [pub_end]
        for label, wall in [("sender confirmed", s["messageFinal"]["confirmed"]), ("receiver confirmed", s["receiverMessage"]["confirmed"])]:
            blue_ends.append(event(epoch_ms(wall), start_mono, stop_mono, label))
        for op in s["transportOperations"]:
            # Delivery completion is already represented by both confirmed
            # messages. Only final blockchain pin completion adds an endpoint;
            # intermediate send timestamps do not define the blue interval.
            if op["type"] == "blockchain_pin_batch":
                blue_ends.append(event(epoch_ms(op["updated"]), start_mono, stop_mono, op["type"] + " updated"))
        for name, a, b in [("Private Data Bus", start_mono, max(blue_ends)),
                           ("IPFS", ipfs_start, ipfs_end),
                           ("API Invoker", invoke_start, operation_created),
                           ("BPMN SC", operation_created, success)]:
            assert b >= a
            converted.append({"step": name, "start_time": origin + a - start_mono,
                              "end_time": origin + b - start_mono, "duration_ms": b - a, "valid": True})
        s["stagesBeforeClockNormalization"] = s["stages"]
        s["stages"] = converted
        s["warningsBeforeClockNormalization"] = s.get("warnings", [])
        s["warnings"] = []
        s["status"] = "passed"
        s["clockNormalization"] = {"origin": "file upload request start", "browserToObserverOffset_ms": offset,
            "syncUncertainty_ms": error, "offsetChange_ms": offsets[1] - offsets[0],
            "events": mapping_evidence, "clockPairs": local,
            "steps": [{"beforeWall_ms": w1, "afterWall_ms": w2, "change_ms": (w2-w1)-(m2-m1)}
                      for (w1,m1),(w2,m2) in zip(local,local[1:]) if abs((w2-w1)-(m2-m1)) > 2]}
        if report.get("metricsVersion", 0) >= 9:
            s["clockNormalization"]["client"] = "Python automated HTTP client, monotonic clock"
        # The new UI preparation endpoint already uploads AND returns MessageID;
        # older experiments had a separate direct private-message HTTP request.
        message_request = s.get("messageRequest", s["fileUpload"])
        s["messageIdToInvokeStart_ms"] = s["invokeRequest"]["clock"]["rawStart"] - message_request["clock"]["rawEnd"]
        s["httpPublishInvokeOverlap_ms"] = max(0, min(pub_end,invoke_end)-max(pub_start,invoke_start))
    from statistics import mean
    report["summary"] = [{"step": name, "count": len(report["samples"]),
        "mean_ms": mean(next(v["duration_ms"] for v in s["stages"] if v["step"] == name) for s in report["samples"])}
        for name in ["Private Data Bus", "IPFS", "API Invoker", "BPMN SC"]]
    report["browserClock"] = ("Python HTTP client monotonic timing and sampled wall→monotonic bridge"
                              if report.get("metricsVersion", 0) >= 9 else
                              "Resource Timing and sampled wall→monotonic bridge; all bars normalized to upload start; raw wall values preserved")
    report["metricsVersion"] = max(8, report.get("metricsVersion", 0))
    if report["metricsVersion"] >= 9:
        report["metrics"]["IPFS"] = "FireFly blob/publish request start → successful response containing CID, with upload Operation Succeeded"
    report["metrics"]["API Invoker"] = "Browser Message_Send request fetchStart → correlated FireFly Operation.created"
    report["metrics"]["BPMN SC"] = "The same Operation.created → correlated blockchain_invoke_op_succeeded event.created"
    report["status"] = "passed"
    report.pop("error", None)
    report["metricAudit"]["clock"] = "5ms wall/monotonic sampling, per-round browser synchronization; discontinuities excluded from interpolation; ambiguous mappings rejected"
    return report
