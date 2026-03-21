split_workflow ManagementSystem {
  main_contract ManagementSystemMain;
  split_point SP1 {
    from_submodel ManagementSystem_sub_1;
    to_submodel ManagementSystem_sub_2;
    marker_node "UNKNOWN";
    handoff_event HandoffRequested;
  }
  submodel ManagementSystem_sub_1 {
    start_node "Event_1y0sgtz";
    end_node "Event_03qnwuo";
    node_count 10;
  }
  submodel ManagementSystem_sub_2 {
    start_node "UNKNOWN";
    end_node "UNKNOWN";
    node_count 1;
  }
}