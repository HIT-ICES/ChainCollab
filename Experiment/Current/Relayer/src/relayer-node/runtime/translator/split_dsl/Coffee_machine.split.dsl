split_workflow Coffee_machine {
  main_contract Coffee_machineMain;
  split_point SP1 {
    from_submodel Coffee_machine_sub_1;
    to_submodel Coffee_machine_sub_2;
    handoff_event HandoffRequested;
  }
  submodel Coffee_machine_sub_1 {
    start_node "UNKNOWN";
    end_node "UNKNOWN";
    node_count 1;
  }
  submodel Coffee_machine_sub_2 {
    start_node "UNKNOWN";
    end_node "UNKNOWN";
    node_count 1;
  }
}