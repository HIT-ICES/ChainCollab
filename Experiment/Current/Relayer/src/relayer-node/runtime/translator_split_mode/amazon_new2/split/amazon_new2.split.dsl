split_workflow amazon_new2 {
  main_contract amazon_new2Main;
  split_point SP1 {
    from_submodel amazon_new2_sub_1;
    to_submodel amazon_new2_sub_2;
    marker_node "UNKNOWN";
    handoff_event HandoffRequested;
  }
  submodel amazon_new2_sub_1 {
    start_node "Event_0ojehz6";
    end_node "Gateway_0ivv4vg";
    node_count 15;
  }
  submodel amazon_new2_sub_2 {
    start_node "UNKNOWN";
    end_node "UNKNOWN";
    node_count 1;
  }
}