# Relayer Node

Relayer node listens for cross-chain call events on a source adapter and forwards them to a destination adapter, then optionally sends the result back.

## Backend

Run:

```
python -m relayer_node.main
```

API:

- `GET /health`
- `GET /identities` / `POST /identities` / `PUT /identities/{id}` / `DELETE /identities/{id}`
- `GET /routes` / `POST /routes` / `PUT /routes/{id}` / `DELETE /routes/{id}`
- `GET /logs?route_id=...`
- `POST /control/start` / `POST /control/stop`

### Route metadata

```
{
  "source_event_name": "XCallRequested",
  "relay_signers": ["0x...privateKey1", "0x...privateKey2"],
  "result_callback": {
    "target": "0x...resultReceiver",
    "method": "onXCallResult(bytes32,bool,bytes)"
  }
}
```

### Fabric notes

Fabric forwarding uses a gateway HTTP API:

```
POST {gateway_url}/invoke
{
  "channel": "...",
  "chaincode": "...",
  "function": "...",
  "args": ["..."]
}
```

Provide `gateway_url`, `channel_name`, `chaincode_name` in the Fabric identity metadata.

For Fabric routes, the relayer expects a `fabric_payload` object in the incoming event payload
with `target_chaincode`, `channel`, `function`, `args_json`, and `signatures_json`.

## Frontend

React + Vite app under `frontend`.
