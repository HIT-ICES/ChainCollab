# Cross-chain Adapter (EVM + Fabric)

This folder contains two adapters that receive cross-chain calls from off-chain relayers and verify threshold signatures before executing target logic.

## EVM (Solidity)

Path: `src/crosschain_adapter/evm/CrossChainAdapter.sol`

Message hash:

```
keccak256(
  abi.encodePacked(
    "XCALL",
    address(this),
    srcChainId,
    dstChainId,
    nonce,
    target,
    value,
    keccak256(callData)
  )
)
```

Relayers sign `toEthSignedMessageHash(messageHash)`. The adapter requires `threshold` distinct relayer signatures to pass.

Outbound request event:

```
XCallRequested(srcChainId, dstChainId, nonce, target, value, callData)
```

## Fabric (Go chaincode)

Path: `src/crosschain_adapter/fabric/adapter.go`

Message hash:

```
sha256(json({
  adapter: "fabric-crosschain-adapter",
  srcChainId,
  dstChainId,
  nonce,
  targetChaincode,
  channel,
  function,
  argsHash: sha256(argsJSON)
}))
```

Relayers sign the 32-byte hash using ECDSA and submit signatures as base64 `r||s` (64 bytes). Relay public keys are PKIX (base64).

## Notes

- Both adapters prevent replay using the message hash.
- Results are stored and emitted (EVM) or persisted (Fabric).
- Threshold and relay sets are owner/admin controlled.
