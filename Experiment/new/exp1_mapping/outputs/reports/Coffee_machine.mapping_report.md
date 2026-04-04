# Mapping Report: Coffee_machine

## Metrics

- Total elements: 12
- Preserved elements: 12
- Successful mappings: 11
- Contract total: 13
- Contract passed: 12
- Element Preservation Rate: 100.00%
- Mapping Accuracy: 91.67%
- Contract Satisfaction Rate: 92.31%
- Pass/Fail: FAIL

## Source Files

- BPMN: `/root/code/ChainCollab/src/newTranslator/generator/resource/bpmn/Coffee_machine.bpmn`
- DMN: `None`
- B2C: `/root/code/ChainCollab/Experiment/new/exp1_mapping/outputs/regenerated/Coffee_machine.generated.b2c`

## Failed Checks

- [businessrule_mapping] BPMN businessRuleTask "Activity_0ysk2q6" (Activity_0ysk2q6) -> DSL `Activity_0ysk2q6`: DSL businessrule missing input mapping; DSL businessrule missing output mapping

## All Contract Checks

- PASS | participant_mapping | BPMN `Participant_1pasf6v` -> DSL `Participant_1pasf6v` | Participant matched by id/name/role alias.
- PASS | participant_mapping | BPMN `Participant_1tddbk5` -> DSL `Participant_1tddbk5` | Participant matched by id/name/role alias.
- PASS | participant_count | BPMN `participants` -> DSL `participants` | BPMN participants=2, DSL participants=2.
- PASS | message_mapping | BPMN `MessageFlow_1fgi2sb` -> DSL `Message_1j4s0qh` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_0mteofp` -> DSL `Message_0gg08bf` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_1yzgau8` -> DSL `Message_0i0xp6a` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_1izdk9y` -> DSL `Message_1uiozoi` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_0w1g28b` -> DSL `Message_1e90tfn` | Message definition and flow trigger preserved.
- PASS | gateway_mapping | BPMN `ExclusiveGateway_0c8hy9b` -> DSL `ExclusiveGateway_0c8hy9b` | Gateway type preserved.
- PASS | gateway_mapping | BPMN `ExclusiveGateway_1sp1v7s` -> DSL `ExclusiveGateway_1sp1v7s` | Gateway type preserved.
- PASS | event_mapping | BPMN `StartEvent_1v2ab61` -> DSL `StartEvent_1v2ab61` | Event preserved with expected progression rule.
- PASS | event_mapping | BPMN `EndEvent_17h95ah` -> DSL `EndEvent_17h95ah` | Event preserved with expected progression rule.
- FAIL | businessrule_mapping | BPMN `Activity_0ysk2q6` -> DSL `Activity_0ysk2q6` | DSL businessrule missing input mapping; DSL businessrule missing output mapping
