# Mapping Report: ManagementSystem

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

- BPMN: `/root/code/ChainCollab/Experiment/BPMNwithDMNcase/ManagementSystem_new3.bpmn`
- DMN: `/root/code/ChainCollab/Experiment/BPMNwithDMNcase/management.dmn`
- B2C: `/root/code/ChainCollab/Experiment/new/exp1_mapping/outputs/regenerated/ManagementSystem.generated.b2c`

## Failed Checks

- None

## All Contract Checks

- PASS | participant_mapping | BPMN `Participant_0ykkst0` -> DSL `Participant_0ykkst0` | Participant matched by id/name/role alias.
- PASS | participant_mapping | BPMN `Participant_1be5jmm` -> DSL `Participant_1be5jmm` | Participant matched by id/name/role alias.
- PASS | participant_mapping | BPMN `Participant_0a0qr98` -> DSL `Participant_0a0qr98` | Participant matched by id/name/role alias.
- PASS | participant_count | BPMN `participants` -> DSL `participants` | BPMN participants=3, DSL participants=3.
- PASS | message_mapping | BPMN `MessageFlow_10317zu` -> DSL `Message_1h1vc49` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_1rzx3lk` -> DSL `Message_094ld7m` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_180bmu4` -> DSL `Message_02ng01e` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_06wulzi` -> DSL `Message_1tiyc35` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_0w90cf1` -> DSL `Message_02echpq` | Message definition and flow trigger preserved.
- PASS | message_mapping | BPMN `MessageFlow_0xi8bfc` -> DSL `Message_1ejkslm` | Message definition and flow trigger preserved.
- PASS | gateway_mapping | BPMN `Gateway_067p6u8` -> DSL `Gateway_067p6u8` | Gateway type preserved.
- PASS | gateway_mapping | BPMN `Gateway_1fl1t0k` -> DSL `Gateway_1fl1t0k` | Gateway type preserved.
- PASS | gateway_mapping | BPMN `Gateway_0e7k79c` -> DSL `Gateway_0e7k79c` | Gateway type preserved.
- PASS | event_mapping | BPMN `Event_1y0sgtz` -> DSL `Event_1y0sgtz` | Event preserved with expected progression rule.
- PASS | event_mapping | BPMN `Event_1u0cugu` -> DSL `Event_1u0cugu` | Event preserved with expected progression rule.
- PASS | event_mapping | BPMN `Event_1pm2yw6` -> DSL `Event_1pm2yw6` | Event preserved with expected progression rule.
- PASS | businessrule_mapping | BPMN `Activity_18dcm0h` -> DSL `Activity_18dcm0h` | Business rule mapping preserved.
