split_workflow amazon {
  main_contract amazonMain;
  split_point SP1 {
    from_submodel amazon_sub_1;
    to_submodel amazon_sub_2;
    marker_node "Activity_0tya4bp";
    handoff_event HandoffRequested;
  }
  submodel amazon_sub_1 {
    start_node "ChoreographyTask_15hdy0f";
    end_node "Activity_0tya4bp";
    node_count 9;
  }
  submodel amazon_sub_2 {
    start_node "Gateway_0jgq0a6";
    end_node "Activity_0tya4bp";
    node_count 8;
  }
}