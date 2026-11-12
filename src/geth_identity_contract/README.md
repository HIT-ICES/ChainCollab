# Geth identity registry

The [IdentityRegistry contract](contracts/IdentityRegistry.sol) associates Ethereum addresses with FireFly identities, organizations, and optional custom keys. The application can synchronize identities through its backend when users are registered. Contracts can also query the registry or call authorized registration methods.

## Build

From this directory, compile the contract with a compatible Solidity compiler:

```bash
mkdir -p build
solc --optimize --bin --abi contracts/IdentityRegistry.sol -o build/
```

Follow the [deployment guide](docs/DEPLOYMENT.md) to deploy on Geth via FireFly or Web3.py. The [integration guide](docs/INTEGRATION.md) describes backend synchronization, and the [Python client](scripts/identity_registry_client.py) exposes the registry operations.

## Registry operations

- Organization administration uses `createOrganization`, `deactivateOrganization`, and `updateOrgAdmin`.
- Contract authorization uses `authorizeCaller`, `revokeCaller`, and `isAuthorizedCaller`.
- Registration and revocation use `registerIdentity` and `revokeIdentity`.
- Queries include `isOrgMember`, `getIdentityOrg`, `getOrgMembers`, `getIdentityInfo`, and `isIdentityRegistered`.

See the [design notes](docs/DESIGN.md) for the registry data model and the [workflow template](contracts/WorkflowContractTemplate.sol) for contract-side permission checks.
