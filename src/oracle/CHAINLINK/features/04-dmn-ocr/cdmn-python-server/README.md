# CDMN Python server

This Flask service evaluates DMN decision tables, caches rule outputs for the Chainlink workflow, and can acknowledge results after OCR confirmation. A request can supply a DMN model directly or retrieve it through the configured FireFly/IPFS endpoints.

## Run locally

From this directory, install the Python requirements and start the service:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
curl --fail http://127.0.0.1:5000/api/dmn/health
```

Set `FIREFLY_CORE_URL`, `IPFS_GATEWAY_URL`, and `DMN_FETCH_TIMEOUT` for remote rule retrieval. For OCR event processing, configure `OCR_LISTENER_ENABLED`, `OCR_RPC_URL`, `OCR_AGGREGATOR_ADDRESS`, and `OCR_POLL_INTERVAL`. The Flask host and port can be set with `FLASK_RUN_HOST` and `FLASK_RUN_PORT`.

## HTTP endpoints

| Method and path | Purpose |
| --- | --- |
| `GET /api/dmn/health` | Service health |
| `POST /api/dmn/evaluate` | Evaluate a decision |
| `POST /api/dmn/calc` | Evaluate and cache a result |
| `GET /api/dmn/latest` | Read the latest cached result |
| `GET /api/dmn/by-hash` | Retrieve a cached result by hash |
| `POST /api/dmn/ack` | Acknowledge a result and clear the relevant cache entry |
| `POST /api/dmn/input-info` | Inspect decision inputs |

For deployed workloads, use the parent stack's Compose configuration so worker endpoints and environment settings match the configured Chainlink jobs. The [application source](app.py) defines request and response fields.
