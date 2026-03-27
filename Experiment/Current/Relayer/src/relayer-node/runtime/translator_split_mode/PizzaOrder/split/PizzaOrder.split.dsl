split_workflow PizzaOrder {
  main_contract PizzaOrderMain;
  split_point SP1 {
    from_submodel PizzaOrder_sub_1;
    to_submodel PizzaOrder_sub_2;
    marker_node "UNKNOWN";
    handoff_event HandoffRequested;
  }
  submodel PizzaOrder_sub_1 {
    start_node "Event_1a62z0q";
    end_node "Event_04u53jh";
    node_count 10;
  }
  submodel PizzaOrder_sub_2 {
    start_node "UNKNOWN";
    end_node "UNKNOWN";
    node_count 1;
  }
}