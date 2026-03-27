split_workflow SupplyChain {
  main_contract SupplyChainMain;
  split_point SP1 {
    from_submodel SupplyChain_sub_1;
    to_submodel SupplyChain_sub_2;
    handoff_event HandoffRequested;
  }
  submodel SupplyChain_sub_1 {
    start_node "ChoreographyTask_0tyax7p";
    end_node "ChoreographyTask_1q3p8t2";
    node_count 12;
  }
  submodel SupplyChain_sub_2 {
    start_node "ChoreographyTask_0m4d50p";
    end_node "ChoreographyTask_1q3p8t2";
    node_count 11;
  }
}