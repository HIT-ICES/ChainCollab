split_workflow Manufactory {
  main_contract ManufactoryMain;
  split_point SP1 {
    from_submodel Manufactory_sub_1;
    to_submodel Manufactory_sub_2;
    marker_node "Gateway_0fkskz5";
    handoff_event HandoffRequested;
  }
  submodel Manufactory_sub_1 {
    start_node "ChoreographyTask_1uikhp7";
    end_node "Gateway_0fkskz5";
    node_count 3;
  }
  submodel Manufactory_sub_2 {
    start_node "ChoreographyTask_1qfx43c";
    end_node "ChoreographyTask_0vs79p0";
    node_count 2;
  }
}