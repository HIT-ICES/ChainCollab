# Mapping Report: Blood_CaseTest

## Metrics

- Total elements: 11
- Preserved elements: 11
- Successful mappings: 11
- Contract total: 12
- Contract passed: 12
- Element Preservation Rate: 100.00%
- Mapping Accuracy: 100.00%
- Contract Satisfaction Rate: 100.00%
- Pass/Fail: PASS

## Source Files

- BPMN: `/root/code/ChainCollab/Experiment/CaseTest/Blood_analysis.bpmn`
- DMN: `None`
- B2C: `/root/code/ChainCollab/Experiment/new/exp1_mapping/outputs/regenerated/Blood_CaseTest.generated.b2c`

## Failed Checks

- None

## All Contract Checks

- PASS | participant_mapping | BPMN `Participant_0ggs0ck` -> DSL `Participant_0ggs0ck` | Participant matched by id/name/role alias.
- PASS | participant_mapping | BPMN `Participant_1v6wnpq` -> DSL `Participant_1v6wnpq` | Participant matched by id/name/role alias.
- PASS | participant_mapping | BPMN `Participant_0tkhpj2` -> DSL `Participant_0tkhpj2` | Participant matched by id/name/role alias.
- PASS | participant_count | BPMN `participants` -> DSL `participants` | BPMN participants=3, DSL participants=3.
- PASS | message_mapping | BPMN `MessageFlow_09o9s93` -> DSL `Message_1rqbibd` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_0r5mbr1` -> DSL `Message_1vzqd37` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_0vz56a0` -> DSL `Message_0wq8mc6` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_16uaf5s` -> DSL `Message_0gswvmq` | Message definition and flow trigger preserved.
- PASS | gateway_mapping | BPMN `ParallelGateway_1pgjqtw` -> DSL `ParallelGateway_1pgjqtw` | Gateway type preserved.
- PASS | gateway_mapping | BPMN `ParallelGateway_16ab76f` -> DSL `ParallelGateway_16ab76f` | Gateway type preserved.
- PASS | event_mapping | BPMN `StartEvent_0m7hz56` -> DSL `StartEvent_0m7hz56` | Event preserved with expected progression rule.
- PASS | event_mapping | BPMN `EndEvent_110myff` -> DSL `EndEvent_110myff` | Event preserved with expected progression rule.
