# Hotel_Booking

DSL reference simulation for exclusive gateway and businessrule behavior.

## Paths

- `vip_discount_happy_path`: expected `accepted`, actual `accepted`
- `reject_unenabled_message`: expected `rejected`, actual `rejected`
  reason: element not triggerable: Message_0r9lypd is INACTIVE

## Notes

- This phase runs only the DSL reference simulator.
- Go/Fabric and Solidity execution hooks are intentionally deferred to the next phase.
