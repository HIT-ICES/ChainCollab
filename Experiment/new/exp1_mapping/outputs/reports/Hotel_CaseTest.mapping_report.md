# Mapping Report: Hotel_CaseTest

## Metrics

- Total elements: 20
- Preserved elements: 20
- Successful mappings: 20
- Contract total: 21
- Contract passed: 21
- Element Preservation Rate: 100.00%
- Mapping Accuracy: 100.00%
- Contract Satisfaction Rate: 100.00%
- Pass/Fail: PASS

## Source Files

- BPMN: `/root/code/ChainCollab/Experiment/CaseTest/Hotel Booking.bpmn`
- DMN: `None`
- B2C: `/root/code/ChainCollab/Experiment/new/exp1_mapping/outputs/regenerated/Hotel_CaseTest.generated.b2c`

## Failed Checks

- None

## All Contract Checks

- PASS | participant_mapping | BPMN `Participant_1080bkg` -> DSL `Participant_1080bkg` | Participant matched by id/name/role alias.
- PASS | participant_mapping | BPMN `Participant_0sktaei` -> DSL `Participant_0sktaei` | Participant matched by id/name/role alias.
- PASS | participant_count | BPMN `participants` -> DSL `participants` | BPMN participants=2, DSL participants=2.
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
- PASS | gateway_mapping | BPMN `EventBasedGateway_1fxpmyn` -> DSL `EventBasedGateway_1fxpmyn` | Gateway type preserved.
- PASS | event_mapping | BPMN `StartEvent_1jtgn3j` -> DSL `StartEvent_1jtgn3j` | Event preserved with expected progression rule.
- PASS | event_mapping | BPMN `EndEvent_0366pfz` -> DSL `EndEvent_0366pfz` | Event preserved with expected progression rule.
- PASS | event_mapping | BPMN `EndEvent_08edp7f` -> DSL `EndEvent_08edp7f` | Event preserved with expected progression rule.
- PASS | event_mapping | BPMN `EndEvent_146eii4` -> DSL `EndEvent_146eii4` | Event preserved with expected progression rule.
