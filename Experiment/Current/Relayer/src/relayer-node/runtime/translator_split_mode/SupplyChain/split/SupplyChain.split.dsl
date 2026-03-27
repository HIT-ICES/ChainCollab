split_workflow SupplyChain {
  main_contract SupplyChainMain;
  split_point SP1 {
    from_submodel SupplyChain_sub_1;
    to_submodel SupplyChain_sub_2;
    marker_node "UNKNOWN";
    handoff_event HandoffRequested;
  }
  submodel SupplyChain_sub_1 {
    start_node "Event_06sexe6";
    end_node "Event_13pbqdz";
    node_count 14;
  }
  submodel SupplyChain_sub_2 {
    start_node "UNKNOWN";
    end_node "UNKNOWN";
    node_count 1;
  }
}