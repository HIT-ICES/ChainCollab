split_workflow Coffee_machine {
  main_contract Coffee_machineMain;
  split_point SP1 {
    from_submodel Coffee_machine_sub_1;
    to_submodel Coffee_machine_sub_2;
    marker_node "AUTO_EXIT_A";
    handoff_event HandoffRequested;
  }
  submodel Coffee_machine_sub_1 {
    start_node "AUTO_ENTRY_A";
    end_node "AUTO_EXIT_A";
    node_count 4;
  }
  submodel Coffee_machine_sub_2 {
    start_node "AUTO_ENTRY_B";
    end_node "AUTO_EXIT_B";
    node_count 4;
  }
}