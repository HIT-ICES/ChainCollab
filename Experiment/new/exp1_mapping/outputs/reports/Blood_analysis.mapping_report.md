# Mapping Report: Blood_analysis

## Metrics

- Total elements: 15
- Preserved elements: 15
- Successful mappings: 15
- Contract total: 16
- Contract passed: 16
- Element Preservation Rate: 100.00%
- Mapping Accuracy: 100.00%
- Contract Satisfaction Rate: 100.00%
- Pass/Fail: PASS

## Source Files

- BPMN: `/root/code/ChainCollab/Experiment/BPMNwithDMNcase/Blood_analysis.bpmn`
- DMN: `/root/code/ChainCollab/Experiment/BPMNwithDMNcase/Blood_analysis.dmn`
- B2C: `/root/code/ChainCollab/Experiment/new/exp1_mapping/outputs/regenerated/Blood_analysis.generated.b2c`

## Failed Checks

- None

## All Contract Checks

- PASS | participant_mapping | BPMN `Participant_0ggs0ck` -> DSL `Participant_0ggs0ck` | Participant matched by id/name/role alias.
- PASS | participant_mapping | BPMN `Participant_1v6wnpq` -> DSL `Participant_1v6wnpq` | Participant matched by id/name/role alias.
- PASS | participant_mapping | BPMN `Participant_0tkhpj2` -> DSL `Participant_0tkhpj2` | Participant matched by id/name/role alias.
- PASS | participant_count | BPMN `participants` -> DSL `participants` | BPMN participants=3, DSL participants=3.
- PASS | message_mapping | BPMN `MessageFlow_0axr6ym` -> DSL `Message_13mh6mk` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_1ueexfr` -> DSL `Message_0gd0z61` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_09o9s93` -> DSL `Message_1rqbibd` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_0r5mbr1` -> DSL `Message_1vzqd37` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_0vz56a0` -> DSL `Message_0wq8mc6` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_16uaf5s` -> DSL `Message_0gswvmq` | Message definition and flow trigger preserved.
- PASS | gateway_mapping | BPMN `Gateway_0o8snyv` -> DSL `Gateway_0o8snyv` | Gateway type preserved.
- PASS | gateway_mapping | BPMN `ParallelGateway_1pgjqtw` -> DSL `ParallelGateway_1pgjqtw` | Gateway type preserved.
- PASS | gateway_mapping | BPMN `Gateway_1m6dgym` -> DSL `Gateway_1m6dgym` | Gateway type preserved.
- PASS | event_mapping | BPMN `StartEvent_0m7hz56` -> DSL `StartEvent_0m7hz56` | Event preserved with expected progression rule.
- PASS | event_mapping | BPMN `EndEvent_110myff` -> DSL `EndEvent_110myff` | Event preserved with expected progression rule.
- PASS | businessrule_mapping | BPMN `Activity_1mj4mr7` -> DSL `Activity_1mj4mr7` | Business rule mapping preserved.
