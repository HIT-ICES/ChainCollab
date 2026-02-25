# Crosschain Relay Lab Architecture

```mermaid
flowchart LR
  subgraph A[Chain A]
    EA[CrossChainEndpoint A]
    RA[RelayTaskReceiver A]
  end

  subgraph B[Chain B]
    EB[CrossChainEndpoint B]
    RB[RelayTaskReceiver B]
  end

  U1[User/Task Producer]
  RLY[Relayer Server\nrelay-server/index.js]
  EXP[Experiment Runner\nexperiments/run-experiment.js]

  U1 -->|sendMessage(dst,payload)| EA
  U1 -->|sendMessage(dst,payload)| EB

  EA -->|RelayRequested| RLY
  EB -->|RelayRequested| RLY

  RLY -->|executeMessage(...)| EA
  RLY -->|executeMessage(...)| EB

  EA -->|call payload| RA
  EB -->|call payload| RB

  EXP -->|deploy/contracts setup| EA
  EXP -->|deploy/contracts setup| EB
  EXP -->|collect gas+latency| RLY
```

## Message lifecycle

1. Source chain task sender calls `CrossChainEndpoint.sendMessage`.
2. Source endpoint emits `RelayRequested(msgId, dstChainId, dstReceiver, payload, nonce)`.
3. Relayer server listens event and enqueues relay job.
4. Relayer calls destination endpoint `executeMessage(...)`.
5. Destination endpoint validates `msgId`, target allow-list, and replay state.
6. Destination endpoint calls target business contract (`RelayTaskReceiver`) with payload.
7. Destination endpoint emits `RelayExecuted(msgId, ok, returnData, relayer)`.
8. Experiment runner queries logs and computes gas/latency statistics.
