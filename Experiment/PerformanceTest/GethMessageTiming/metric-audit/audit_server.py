"""Local, experiment-only read-only metric audit endpoint for the Test button.

Run: python3 audit_server.py
No deployment/configuration/business-state changes are performed by this server.
"""
import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from audit_metrics import audit
from monotonic_clock import read_clock, normalize

EXPECTED_API = "http://127.0.0.1:5001/api/v1/namespaces/default/apis/SupplyChainPaper-54b29f-d8b7ed-3c13ea"


def enrich(report, scope="contract"):
    if report.get("api") != EXPECTED_API or not 1 <= len(report.get("samples", [])) <= 100:
        raise ValueError("Expected the current deployed contract and 1–100 measured samples")
    evidence = audit(report, scope)
    result = copy.deepcopy(report)
    result["metricAudit"] = {"apiScope": scope, "notes": evidence["notes"], "method": "FireFly internal IPFS HTTP logs + connector transaction history + browser Resource Timing"}
    result["previousSummaryBeforeAudit"] = result.get("summary")
    result["metricsVersion"] = max(8, report.get("metricsVersion", 0))
    result["metrics"]["API Invoker"] = "Browser Message_Send request fetchStart → correlated FireFly Operation.created"
    result["metrics"]["IPFS"] = "Internal FireFly→IPFS /api/v0/add HTTP call, matched by Operation, request id and CID"
    result["metrics"]["BPMN SC"] = "The same Operation.created → correlated blockchain_invoke_op_succeeded event.created"
    for sample, verified in zip(result["samples"], evidence["rounds"]):
        assert sample["index"] == verified["round"]
        sample["previousStagesBeforeAudit"] = sample["stages"]
        sample["stages"] = verified["stages"]
        sample["ipfsInternalCallEvidence"] = verified["ipfsEvidence"]
        sample["connectorTransaction"] = verified["connectorTransaction"]
    result["summary"] = evidence["summary"]
    return normalize(result) if report.get("metricsVersion", 0) >= 7 else result


class Handler(BaseHTTPRequestHandler):
    def respond(self, value, status=200):
        content = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:3000")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST,GET,OPTIONS")
        self.end_headers()
        self.wfile.write(content)

    def do_OPTIONS(self):
        self.respond({})

    def do_GET(self):
        self.respond(read_clock() if self.path == "/clock" else {"status": "ok", "purpose": "read-only experiment metric audit"})

    def do_POST(self):
        if self.path != "/audit":
            self.respond({"error": "not found"}, 404)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > 16 * 1024 * 1024:
                raise ValueError("Invalid report size")
            body = json.loads(self.rfile.read(size))
            self.respond(enrich(body["report"], body.get("apiScope", "contract")))
        except Exception as error:
            self.respond({"error": str(error)}, 422)


if __name__ == "__main__":
    print("Experiment-only audit endpoint: http://127.0.0.1:8791/audit", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8791), Handler).serve_forever()
