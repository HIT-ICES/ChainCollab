# Development Geth node

This directory contains the Geth image definition and genesis configuration for the standalone Chainlink development stack. Run Compose from the parent [Chainlink directory](../README.md).

```bash
cd ..
docker compose up -d mybootnode
docker compose logs -f mybootnode
```

The Compose service configures RPC, WebSocket, peer discovery, and data volumes. Inspect its configuration for the active port mappings. To open the local node console:

```bash
docker compose exec mybootnode geth attach http://localhost:8545
```

Use `eth.blockNumber`, `eth.accounts`, and `net.peerCount` to inspect the running node. The stack uses development accounts, a private genesis, and development RPC settings. Configure local keys and unlock credentials before starting the corresponding signing services. Keep the data volume to reuse the current chain state. Stop the node with `docker compose stop mybootnode`.
