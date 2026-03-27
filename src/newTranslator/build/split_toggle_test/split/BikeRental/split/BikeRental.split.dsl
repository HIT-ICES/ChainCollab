split_workflow BikeRental {
  main_contract BikeRentalMain;
  split_point SP1 {
    from_submodel BikeRental_sub_1;
    to_submodel BikeRental_sub_2;
    marker_node "ParallelGateway_0himv1h";
    handoff_event HandoffRequested;
  }
  submodel BikeRental_sub_1 {
    start_node "ChoreographyTask_0v7d1xd";
    end_node "ParallelGateway_0himv1h";
    node_count 24;
  }
  submodel BikeRental_sub_2 {
    start_node "ChoreographyTask_0v7d1xd";
    end_node "ParallelGateway_0yw95j2";
    node_count 21;
  }
}