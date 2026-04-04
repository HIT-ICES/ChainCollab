# Mapping Report: ExamProcedure

## Metrics

- Total elements: 16
- Preserved elements: 16
- Successful mappings: 16
- Contract total: 17
- Contract passed: 17
- Element Preservation Rate: 100.00%
- Mapping Accuracy: 100.00%
- Contract Satisfaction Rate: 100.00%
- Pass/Fail: PASS

## Source Files

- BPMN: `/root/code/ChainCollab/Experiment/CaseTest/ExamProcedure.bpmn`
- DMN: `None`
- B2C: `/root/code/ChainCollab/Experiment/new/exp1_mapping/outputs/regenerated/ExamProcedure.generated.b2c`

## Failed Checks

- None

## All Contract Checks

- PASS | participant_mapping | BPMN `Participant_1nsr1pk` -> DSL `Participant_1nsr1pk` | Participant matched by id/name/role alias.
- PASS | participant_mapping | BPMN `Participant_17p14zp` -> DSL `Participant_17p14zp` | Participant matched by id/name/role alias.
- PASS | participant_mapping | BPMN `Participant_0hq3u2g` -> DSL `Participant_0hq3u2g` | Participant matched by id/name/role alias.
- PASS | participant_count | BPMN `participants` -> DSL `participants` | BPMN participants=3, DSL participants=3.
- PASS | message_mapping | BPMN `MessageFlow_0gs3xdn` -> DSL `Message_056fnvb` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_00u4438` -> DSL `Message_02c4y9x` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_0hsmt49` -> DSL `Message_17fxrx9` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_03cmks3` -> DSL `Message_0q57ry5` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_0kuz7xy` -> DSL `Message_088v968` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_1qj4ovk` -> DSL `Message_0ljgx63` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_0qram9q` -> DSL `Message_0hmbvna` | Message definition and flow trigger preserved.
- PASS | gateway_mapping | BPMN `ExclusiveGateway_03vvj42` -> DSL `ExclusiveGateway_03vvj42` | Gateway type preserved.
- PASS | gateway_mapping | BPMN `ExclusiveGateway_1rce5wz` -> DSL `ExclusiveGateway_1rce5wz` | Gateway type preserved.
- PASS | gateway_mapping | BPMN `ExclusiveGateway_0w1a2wn` -> DSL `ExclusiveGateway_0w1a2wn` | Gateway type preserved.
- PASS | gateway_mapping | BPMN `ExclusiveGateway_08unpzh` -> DSL `ExclusiveGateway_08unpzh` | Gateway type preserved.
- PASS | event_mapping | BPMN `StartEvent_1c8pohk` -> DSL `StartEvent_1c8pohk` | Event preserved with expected progression rule.
- PASS | event_mapping | BPMN `EndEvent_12bli43` -> DSL `EndEvent_12bli43` | Event preserved with expected progression rule.
