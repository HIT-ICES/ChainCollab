# Oracle, DMN and Relayer services

Start the core stack using the root README first. Creating a Fabric/Geth
environment also requires the corresponding Docker images and FireFly CLI;
starting the web application alone does not create blockchain networks.

## Fabric DMN event listener

After creating the Fabric environment, FireFly stack, Oracle and DMNEngine
chaincodes through the system, run:

```bash
python3 scripts/chaincollab.py run fabric-oracle
```

This uses the existing Django `oracle` management command. It expects the
FireFly API/WebSocket endpoint on port 5000, as implemented in that command.
Configure the environment and subscriptions before expecting decision execution.
This listener is not needed for offline BPMN-to-code generation.

## Geth Oracle/OCR

The active stack is `src/oracle`, with three collaborating directories:
`CHAINLINK`, `03-ocr-multinode` and `04-dmn-ocr`. Do not use the retired
`src/oracle-node` path from old development notes.

From the repository root:

```bash
export CHAINLINK_ROOT="$PWD/src/oracle/CHAINLINK"
cd src/oracle/CHAINLINK
npm install
cd ../../..
```

Create local `.api`, `.password` and `secrets.toml` beside their `.example`
files for the base node and OCR nodes. Replace example values consistently:
Chainlink API credentials, keystore passwords and PostgreSQL passwords must match
the corresponding compose services. Existing local files are preserved by the
release cleanup and are not committed. Node TOML configuration and example
files remain available in the source tree.

Create/choose a running Geth environment in the system first. The backend uses
its RPC address and stores resulting deployment metadata. Its setup operation
calls `src/oracle/04-dmn-ocr/run-setup-lite.sh` with the environment configuration.
For an explicitly configured existing system-geth-node, the equivalent shell
entry point is:

```bash
export CHAINLINK_ROOT="$PWD/src/oracle/CHAINLINK"
export SYSTEM_GETH_CONTAINER=system-geth-node
export OCR_RPC_URL=http://system-geth-node:8545
bash src/oracle/04-dmn-ocr/run-setup-lite.sh
```

This is a provisioning command: it deploys contracts and creates jobs. Run it
only for the selected environment, not as a web-service health check. Native
Solidity compilation or the compiler Docker image, OCR/Chainlink images, Docker
networks and the DMN service image must be available. There are no universal
predeployed addresses or job IDs for a new checkout.

## Relayer

The backend's default Relayer API is `http://127.0.0.1:8082`. Keep this service
for cross-chain operations; it is not an obsolete translator.

```bash
python3 scripts/chaincollab.py setup --with-relayer
python3 scripts/chaincollab.py run relayer
curl --fail http://127.0.0.1:8082/health
```

Configure `RELAYER_NODE_URL` in the backend process environment when the service
runs elsewhere. Register identities and source/destination routes through its
API before relaying. Its SQLite state database is local runtime data, not a
published identity/key store. The optional standalone UI has its own
`src/relayer-node/frontend/package.json`; start it separately with `npm install`
and `npm run dev`. Configure `RELAYER_NODE_UI` if linking to that UI.

These optional services depend on live blockchains and Oracle infrastructure.
Core HTTP/generator smoke tests do not establish an end-to-end live-chain or
performance result.
