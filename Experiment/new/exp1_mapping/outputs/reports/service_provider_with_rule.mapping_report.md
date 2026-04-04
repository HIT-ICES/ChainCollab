# Mapping Report: service_provider_with_rule

## Metrics

- Total elements: 27
- Preserved elements: 27
- Successful mappings: 27
- Contract total: 28
- Contract passed: 28
- Element Preservation Rate: 100.00%
- Mapping Accuracy: 100.00%
- Contract Satisfaction Rate: 100.00%
- Pass/Fail: PASS

## Source Files

- BPMN: `/root/code/ChainCollab/src/newTranslator/generator/resource/bpmn/service provider running time example-with business rule.bpmn`
- DMN: `None`
- B2C: `/root/code/ChainCollab/Experiment/new/exp1_mapping/outputs/regenerated/service_provider_with_rule.generated.b2c`

## Failed Checks

- None

## All Contract Checks

- PASS | participant_mapping | BPMN `Participant_1080bkg` -> DSL `Participant_1080bkg` | Participant matched by id/name/role alias.
- PASS | participant_mapping | BPMN `Participant_0sktaei` -> DSL `Participant_0sktaei` | Participant matched by id/name/role alias.
- PASS | participant_mapping | BPMN `Participant_1gcdqza` -> DSL `Participant_1gcdqza` | Participant matched by id/name/role alias.
- PASS | participant_count | BPMN `participants` -> DSL `participants` | BPMN participants=3, DSL participants=3.
- PASS | message_mapping | BPMN `MessageFlow_03ynrhs` -> DSL `Message_1qbk325` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_0tjt3sl` -> DSL `Message_1q05nnw` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_0u8ij05` -> DSL `Message_1i8rlqn` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_1lxxqv0` -> DSL `Message_0m9p3da` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_0fb4qv7` -> DSL `Message_1etcmvl` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_13k266b` -> DSL `Message_1joj7ca` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_0dy2v5w` -> DSL `Message_1ljlm4g` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_0z9qel3` -> DSL `Message_1xm9dxy` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_1o7kyb6` -> DSL `Message_0o8eyir` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_1o6utvb` -> DSL `Message_1nlagx2` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_1bermr1` -> DSL `Message_1em0ee4` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_19g4eua` -> DSL `Message_0r9lypd` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_0zxzleu` -> DSL `Message_045i10y` | Message definition and flow trigger preserved.
- PASS | gateway_mapping | BPMN `ExclusiveGateway_106je4z` -> DSL `ExclusiveGateway_106je4z` | Gateway type preserved.
- PASS | gateway_mapping | BPMN `ExclusiveGateway_0hs3ztq` -> DSL `ExclusiveGateway_0hs3ztq` | Gateway type preserved.
- PASS | gateway_mapping | BPMN `ExclusiveGateway_0nzwv7v` -> DSL `ExclusiveGateway_0nzwv7v` | Gateway type preserved.
- PASS | gateway_mapping | BPMN `Gateway_1bhtapl` -> DSL `Gateway_1bhtapl` | Gateway type preserved.
- PASS | gateway_mapping | BPMN `Gateway_04h9e6e` -> DSL `Gateway_04h9e6e` | Gateway type preserved.
- PASS | gateway_mapping | BPMN `EventBasedGateway_1fxpmyn` -> DSL `EventBasedGateway_1fxpmyn` | Gateway type preserved.
- PASS | event_mapping | BPMN `Event_1jtgn3j` -> DSL `Event_1jtgn3j` | Event preserved with expected progression rule.
- PASS | event_mapping | BPMN `Event_0366pfz` -> DSL `Event_0366pfz` | Event preserved with expected progression rule.
- PASS | event_mapping | BPMN `Event_08edp7f` -> DSL `Event_08edp7f` | Event preserved with expected progression rule.
- PASS | event_mapping | BPMN `Event_146eii4` -> DSL `Event_146eii4` | Event preserved with expected progression rule.
- PASS | businessrule_mapping | BPMN `Activity_1q19lty` -> DSL `Activity_1q19lty` | Business rule mapping preserved.
