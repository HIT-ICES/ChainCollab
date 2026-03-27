split_workflow customer_new {
  main_contract customer_newMain;
  split_point SP1 {
    from_submodel customer_new_sub_1;
    to_submodel customer_new_sub_2;
    marker_node "UNKNOWN";
    handoff_event HandoffRequested;
  }
  submodel customer_new_sub_1 {
    start_node "Event_1jtgn3j";
    end_node "Event_143ykco";
    node_count 20;
  }
  submodel customer_new_sub_2 {
    start_node "UNKNOWN";
    end_node "UNKNOWN";
    node_count 1;
  }
}