# Exp2 Summary

- 总案例数: 23
- 正例数: 15
- 负例数: 8

## 正例

- basic_linear_case: go=PASS (1.0), solidity=PASS (1.0), assertions=A01_model_has_contract,A02_unique_names_per_kind,A08_exactly_one_start_flow,A09_start_event_ready,A10_start_flow_target_in_contract,A15_gateway_choose_only_for_exclusive,A16_gateway_flow_mode_unique
- business_rule_case: go=PASS (1.0), solidity=PASS (1.0), assertions=A01_model_has_contract,A02_unique_names_per_kind,A05_rule_mappings_reference_own_globals,A08_exactly_one_start_flow,A09_start_event_ready,A10_start_flow_target_in_contract
- business_rule_contract_b: go=PASS (1.0), solidity=PASS (1.0), assertions=A05_rule_mappings_reference_own_globals,A08_exactly_one_start_flow,A15_gateway_choose_only_for_exclusive
- business_rule_contract_c: go=PASS (1.0), solidity=PASS (1.0), assertions=A05_rule_mappings_reference_own_globals,A08_exactly_one_start_flow,A15_gateway_choose_only_for_exclusive
- business_rule_contract_d: go=PASS (1.0), solidity=PASS (1.0), assertions=A05_rule_mappings_reference_own_globals,A08_exactly_one_start_flow,A15_gateway_choose_only_for_exclusive
- business_rule_contract_e: go=PASS (1.0), solidity=PASS (1.0), assertions=A05_rule_mappings_reference_own_globals,A08_exactly_one_start_flow,A15_gateway_choose_only_for_exclusive
- linear_contract_a: go=PASS (1.0), solidity=PASS (1.0), assertions=A03_message_sender_receiver_in_contract,A04_message_sender_not_receiver,A08_exactly_one_start_flow,A15_gateway_choose_only_for_exclusive
- linear_contract_b: go=PASS (1.0), solidity=PASS (1.0), assertions=A03_message_sender_receiver_in_contract,A04_message_sender_not_receiver,A08_exactly_one_start_flow,A15_gateway_choose_only_for_exclusive
- linear_contract_c: go=PASS (1.0), solidity=PASS (1.0), assertions=A03_message_sender_receiver_in_contract,A04_message_sender_not_receiver,A08_exactly_one_start_flow,A15_gateway_choose_only_for_exclusive
- linear_contract_d: go=PASS (1.0), solidity=PASS (1.0), assertions=A03_message_sender_receiver_in_contract,A04_message_sender_not_receiver,A08_exactly_one_start_flow,A15_gateway_choose_only_for_exclusive
- linear_contract_e: go=PASS (1.0), solidity=PASS (1.0), assertions=A03_message_sender_receiver_in_contract,A04_message_sender_not_receiver,A08_exactly_one_start_flow,A15_gateway_choose_only_for_exclusive
- multi_message_case: go=PASS (1.0), solidity=PASS (1.0), assertions=A03_message_sender_receiver_in_contract,A04_message_sender_not_receiver,A08_exactly_one_start_flow,A10_start_flow_target_in_contract
- multi_message_contract_b: go=PASS (1.0), solidity=PASS (1.0), assertions=A03_message_sender_receiver_in_contract,A04_message_sender_not_receiver,A08_exactly_one_start_flow,A10_start_flow_target_in_contract
- multi_message_contract_c: go=PASS (1.0), solidity=PASS (1.0), assertions=A03_message_sender_receiver_in_contract,A04_message_sender_not_receiver,A08_exactly_one_start_flow,A10_start_flow_target_in_contract
- multi_message_contract_d: go=PASS (1.0), solidity=PASS (1.0), assertions=A03_message_sender_receiver_in_contract,A04_message_sender_not_receiver,A08_exactly_one_start_flow,A10_start_flow_target_in_contract

## 负例

- invalid_gateway_type: result=EXPECTED_REJECT, assertions=A17_gateway_type_enum_legal
- invalid_missing_flow_target: result=EXPECTED_REJECT, assertions=A10_start_flow_target_in_contract,A11_flow_refs_stay_in_same_contract
- invalid_missing_message_sender: result=EXPECTED_REJECT, assertions=A03_message_sender_receiver_in_contract
- invalid_missing_message_trigger: result=EXPECTED_REJECT, assertions=A11_flow_refs_stay_in_same_contract
- invalid_missing_parallel_source: result=EXPECTED_REJECT, assertions=A11_flow_refs_stay_in_same_contract,A14_parallel_sources_valid
- invalid_missing_rule_mapping_global: result=EXPECTED_REJECT, assertions=A05_rule_mappings_reference_own_globals
- invalid_missing_set_variable: result=EXPECTED_REJECT, assertions=A12_actions_reference_own_elements_and_globals
- invalid_missing_start_event: result=EXPECTED_REJECT, assertions=A08_exactly_one_start_flow,A11_flow_refs_stay_in_same_contract
