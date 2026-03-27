split_workflow IncidentManagement {
  main_contract IncidentManagementMain;
  split_point SP1 {
    from_submodel IncidentManagement_sub_1;
    to_submodel IncidentManagement_sub_2;
    marker_node "Gateway_1lr7zva";
    handoff_event HandoffRequested;
  }
  submodel IncidentManagement_sub_1 {
    start_node "Event_026jxk6";
    end_node "Event_18807k4";
    node_count 10;
  }
  submodel IncidentManagement_sub_2 {
    start_node "Gateway_1lr7zva";
    end_node "ChoreographyTask_02opmn4";
    node_count 4;
  }
}