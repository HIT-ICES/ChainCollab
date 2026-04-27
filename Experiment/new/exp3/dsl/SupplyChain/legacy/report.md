# SupplyChain

DSL reference simulation for parallel join and businessrule behavior.

## Paths

- `parallel_delivery_happy_path`: expected `accepted`, actual `accepted`
- `reject_before_parallel_split`: expected `rejected`, actual `rejected`
  reason: element not triggerable: Message_0pm90nx is INACTIVE

## Notes

- This phase runs only the DSL reference simulator.
- Go/Fabric and Solidity execution hooks are intentionally deferred to the next phase.
