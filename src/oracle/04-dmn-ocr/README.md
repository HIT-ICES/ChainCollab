# Chainlink DMN and OCR workflow

This stack connects Geth rule requests to Chainlink and CDMN. A request identifies the decision and its input, and the worker retrieves the DMN model using its CID. The worker evaluates the rule and submits a result. The generated workflow continues after the result is available. The full OCR path coordinates multiple reporting nodes and uses the acknowledgement listener to clear corresponding cached results.

For the release entry points, environment variables, and prerequisites, follow the [Oracle and Relayer setup guide](../../../docs/ORACLE_RELAYER_SETUP.md).

## Provision the workflow

Start with a running Geth environment, Chainlink worker configuration, IPFS access, and the required Docker networks. Configure local API credentials and keystore passwords using the provided examples. The provisioning scripts deploy contracts and register jobs for the selected environment.

From the repository root:

```bash
bash src/oracle/04-dmn-ocr/run-setup-lite.sh
```

The release uses the lite entry point for DirectRequest. The full OCR entry point is `run-setup.sh` in the same directory. Check the generated deployment metadata for the request contract, job IDs, and worker addresses. Fund the request contract with development LINK and keep the worker jobs and CDMN services running during rule execution.

## Components

- [CDMN server](cdmn-python-server/README.md) evaluates and caches rule results.
- [CDMN Compose configuration](docker-compose-cdmn.yml) defines the worker services.
- The JavaScript job scripts register DirectRequest and OCR jobs and configure the on-chain request and writer contracts.
- `ocr-ack-listener.js` observes finalization and acknowledges cached results.
- `test-dmn-ocr.js` exercises a configured deployment. Check its options and verify the target deployment before running it.
