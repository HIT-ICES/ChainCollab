split_workflow Purchase {
  main_contract PurchaseMain;
  split_point SP1 {
    from_submodel Purchase_sub_1;
    to_submodel Purchase_sub_2;
    marker_node "UNKNOWN";
    handoff_event HandoffRequested;
  }
  submodel Purchase_sub_1 {
    start_node "Event_0ehnwwz";
    end_node "Event_194zr5n";
    node_count 12;
  }
  submodel Purchase_sub_2 {
    start_node "UNKNOWN";
    end_node "UNKNOWN";
    node_count 1;
  }
}