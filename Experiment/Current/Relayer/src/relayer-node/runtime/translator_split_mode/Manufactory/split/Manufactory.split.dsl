split_workflow Manufactory {
  main_contract ManufactoryMain;
  split_point SP1 {
    from_submodel Manufactory_sub_1;
    to_submodel Manufactory_sub_2;
    marker_node "UNKNOWN";
    handoff_event HandoffRequested;
  }
  submodel Manufactory_sub_1 {
    start_node "Event_1kw6wq7";
    end_node "Event_1tsex1f";
    node_count 9;
  }
  submodel Manufactory_sub_2 {
    start_node "UNKNOWN";
    end_node "UNKNOWN";
    node_count 1;
  }
}