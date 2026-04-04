# Mapping Report: amazon_new2

## Metrics

- Total elements: 17
- Preserved elements: 17
- Successful mappings: 17
- Contract total: 18
- Contract passed: 18
- Element Preservation Rate: 100.00%
- Mapping Accuracy: 100.00%
- Contract Satisfaction Rate: 100.00%
- Pass/Fail: PASS

## Source Files

- BPMN: `/root/code/ChainCollab/Experiment/BPMNwithDMNcase/amazon_new2.bpmn`
- DMN: `/root/code/ChainCollab/Experiment/BPMNwithDMNcase/amazon.dmn`
- B2C: `/root/code/ChainCollab/Experiment/new/exp1_mapping/outputs/regenerated/amazon_new2.generated.b2c`

## Failed Checks

- None

## All Contract Checks

- PASS | participant_mapping | BPMN `Participant_1p9owwo` -> DSL `Participant_1p9owwo` | Participant matched by id/name/role alias.
- PASS | participant_mapping | BPMN `Participant_12df78t` -> DSL `Participant_12df78t` | Participant matched by id/name/role alias.
- PASS | participant_count | BPMN `participants` -> DSL `participants` | BPMN participants=2, DSL participants=2.
- PASS | message_mapping | BPMN `MessageFlow_13hle13` -> DSL `Message_1b1qlzd` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_191vfqw` -> DSL `Message_01jq2zl` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_05bvd7t` -> DSL `Message_12n6jjk` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_1haf3pl` -> DSL `Message_076ulzs` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_1nqrrp6` -> DSL `Message_068kmzv` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_1lf21qb` -> DSL `Message_09krt7c` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_0khz8el` -> DSL `Message_1bhhp1n` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_1urma6e` -> DSL `Message_0ywghlt` | Message definition and flow trigger preserved.
- PASS | gateway_mapping | BPMN `Gateway_0auc3he` -> DSL `Gateway_0auc3he` | Gateway type preserved.
- PASS | gateway_mapping | BPMN `Gateway_0ivv4vg` -> DSL `Gateway_0ivv4vg` | Gateway type preserved.
- PASS | gateway_mapping | BPMN `Gateway_0jgq0a6` -> DSL `Gateway_0jgq0a6` | Gateway type preserved.
- PASS | event_mapping | BPMN `Event_0ojehz6` -> DSL `Event_0ojehz6` | Event preserved with expected progression rule.
- PASS | event_mapping | BPMN `Event_0ci2gl8` -> DSL `Event_0ci2gl8` | Event preserved with expected progression rule.
- PASS | event_mapping | BPMN `Event_0dyp0ut` -> DSL `Event_0dyp0ut` | Event preserved with expected progression rule.
- PASS | businessrule_mapping | BPMN `Activity_0tya4bp` -> DSL `Activity_0tya4bp` | Business rule mapping preserved.
