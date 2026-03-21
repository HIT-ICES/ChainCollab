split_workflow Rental_Claim {
  main_contract Rental_ClaimMain;
  split_point SP1 {
    from_submodel Rental_Claim_sub_1;
    to_submodel Rental_Claim_sub_2;
    marker_node "UNKNOWN";
    handoff_event HandoffRequested;
  }
  submodel Rental_Claim_sub_1 {
    start_node "Event_19zgkxm";
    end_node "Event_0fzlrii";
    node_count 14;
  }
  submodel Rental_Claim_sub_2 {
    start_node "UNKNOWN";
    end_node "UNKNOWN";
    node_count 1;
  }
}