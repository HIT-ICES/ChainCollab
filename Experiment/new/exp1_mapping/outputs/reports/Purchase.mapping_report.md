# Mapping Report: Purchase

## Metrics

- Total elements: 18
- Preserved elements: 18
- Successful mappings: 17
- Contract total: 19
- Contract passed: 18
- Element Preservation Rate: 100.00%
- Mapping Accuracy: 94.44%
- Contract Satisfaction Rate: 94.74%
- Pass/Fail: FAIL

## Source Files

- BPMN: `/root/code/ChainCollab/Experiment/BPMNwithDMNcase/Purchase.bpmn`
- DMN: `/root/code/ChainCollab/Experiment/BPMNwithDMNcase/purchase.dmn`
- B2C: `/root/code/ChainCollab/Experiment/new/exp1_mapping/outputs/regenerated/Purchase.generated.b2c`

## Failed Checks

- [message_mapping] BPMN messageFlow "sale" (MessageFlow_1qi88x8) -> DSL `Message_08ms1jj`: DSL flows missing message sent/completed trigger

## All Contract Checks

- PASS | participant_mapping | BPMN `Participant_0oa2za9` -> DSL `Participant_0oa2za9` | Participant matched by id/name/role alias.
- PASS | participant_mapping | BPMN `Participant_0jwk4tk` -> DSL `Participant_0jwk4tk` | Participant matched by id/name/role alias.
- PASS | participant_mapping | BPMN `Participant_0cb2p7d` -> DSL `Participant_0cb2p7d` | Participant matched by id/name/role alias.
- PASS | participant_count | BPMN `participants` -> DSL `participants` | BPMN participants=3, DSL participants=3.
- FAIL | message_mapping | BPMN `MessageFlow_1qi88x8` -> DSL `Message_08ms1jj` | DSL flows missing message sent/completed trigger
- PASS | message_mapping | BPMN `MessageFlow_0nq8x22` -> DSL `Message_0mcktm6` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_18hgpre` -> DSL `Message_0q9hvem` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_0s1vo46` -> DSL `Message_05gz8u0` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_0tb3its` -> DSL `Message_0g7m9tf` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_0m4bfnr` -> DSL `Message_14wu8ts` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_0xexblk` -> DSL `Message_1f0gefc` | Message definition and flow trigger preserved.
- PASS | gateway_mapping | BPMN `Gateway_1ltys0e` -> DSL `Gateway_1ltys0e` | Gateway type preserved.
- PASS | gateway_mapping | BPMN `Gateway_025uwvp` -> DSL `Gateway_025uwvp` | Gateway type preserved.
- PASS | gateway_mapping | BPMN `Gateway_13i0b7w` -> DSL `Gateway_13i0b7w` | Gateway type preserved.
- PASS | event_mapping | BPMN `Event_0ehnwwz` -> DSL `Event_0ehnwwz` | Event preserved with expected progression rule.
- PASS | event_mapping | BPMN `Event_0e3j88g` -> DSL `Event_0e3j88g` | Event preserved with expected progression rule.
- PASS | event_mapping | BPMN `Event_1o9guxu` -> DSL `Event_1o9guxu` | Event preserved with expected progression rule.
- PASS | event_mapping | BPMN `Event_194zr5n` -> DSL `Event_194zr5n` | Event preserved with expected progression rule.
- PASS | businessrule_mapping | BPMN `Activity_12arovy` -> DSL `Activity_12arovy` | Business rule mapping preserved.
