# Active Chainlink runtime

This directory is used by the system backend. Follow [Oracle / Relayer setup](../../../docs/ORACLE_RELAYER_SETUP.md) and the root [startup guide](../../../Readme.md).

The active fork also needs sibling `../03-ocr-multinode` and `../04-dmn-ocr`. Local `.api`, `.password`, `secrets.toml`, chain data and deployment metadata are not universal release defaults. Create the ignored local files from `.example` files and configure the selected environment; old development addresses/job IDs must not be reused as new deployment results.
