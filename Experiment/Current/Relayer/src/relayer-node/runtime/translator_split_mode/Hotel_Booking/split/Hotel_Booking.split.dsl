split_workflow Hotel_Booking {
  main_contract Hotel_BookingMain;
  split_point SP1 {
    from_submodel Hotel_Booking_sub_1;
    to_submodel Hotel_Booking_sub_2;
    marker_node "UNKNOWN";
    handoff_event HandoffRequested;
  }
  submodel Hotel_Booking_sub_1 {
    start_node "StartEvent_1jtgn3j";
    end_node "EndEvent_146eii4";
    node_count 14;
  }
  submodel Hotel_Booking_sub_2 {
    start_node "UNKNOWN";
    end_node "UNKNOWN";
    node_count 1;
  }
}