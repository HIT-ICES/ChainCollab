split_workflow BikeRental {
  main_contract BikeRentalMain;
  split_point SP1 {
    from_submodel BikeRental_sub_1;
    to_submodel BikeRental_sub_2;
    marker_node "ChoreographyTask_141gqps";
    handoff_event HandoffRequested;
  }
  submodel BikeRental_sub_1 {
    start_node "StartEvent_0gb8jks";
    end_node "ChoreographyTask_137ic1s";
    node_count 25;
  }
  submodel BikeRental_sub_2 {
    start_node "ChoreographyTask_141gqps";
    end_node "ChoreographyTask_141gqps";
    node_count 1;
  }
}