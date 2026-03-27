split_workflow Blood_analysis {
  main_contract Blood_analysisMain;
  split_point SP1 {
    from_submodel Blood_analysis_sub_1;
    to_submodel Blood_analysis_sub_2;
    marker_node "UNKNOWN";
    handoff_event HandoffRequested;
  }
  submodel Blood_analysis_sub_1 {
    start_node "StartEvent_0m7hz56";
    end_node "EndEvent_110myff";
    node_count 8;
  }
  submodel Blood_analysis_sub_2 {
    start_node "UNKNOWN";
    end_node "UNKNOWN";
    node_count 1;
  }
}