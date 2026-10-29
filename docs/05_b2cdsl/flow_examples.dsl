contract FlowExamples {

    globals {
        Deliver: bool
    }

    messages {
        message Message_A from Buyer to Seller {
            initial state INACTIVE
            schema "{}"
        }
        message Message_B from Seller to Buyer {
            initial state INACTIVE
            schema "{}"
        }
        message Message_C from Buyer to Carrier {
            initial state INACTIVE
            schema "{}"
        }
        message Message_D from Seller to Buyer {
            initial state INACTIVE
            schema "{}"
        }
    }

    participants {
        participant Buyer {
            msp "BuyerMSP"
        }
        participant Seller {
            msp "SellerMSP"
        }
        participant Carrier {
            msp "CarrierMSP"
        }
    }

    gateways {
        gateway Gateway_X {
            type exclusive
            initial state INACTIVE
        }
        gateway Gateway_Y {
            type parallel
            initial state INACTIVE
        }
        gateway Gateway_Z {
            type parallel
            initial state INACTIVE
        }
    }

    events {
        event Start_1 {
            initial state READY
        }
        event End_1 {
            initial state INACTIVE
        }
        event End_2 {
            initial state INACTIVE
        }
    }

    businessrules {
        businessrule Rule_1 {
            dmn "Rule_1.dmn"
            decision "Rule_1_DecisionID"
            input mapping {
                deliver -> Deliver
            }
            output mapping {
                deliver -> Deliver
            }
            initial state INACTIVE
        }
    }

    oracletasks {
    }

    flows {
        start event Start_1 enables Message_A;

        when message Message_A completed
        then enable Rule_1;

        when businessrule Rule_1 done
        then enable Gateway_X;

        when gateway Gateway_X completed
        choose {
            if Deliver == true
            then enable Message_B;
            if Deliver == false
            then enable End_2;
        }

        when message Message_B completed
        then enable Gateway_Y;

        when gateway Gateway_Y completed
        then enable Message_C, enable Message_D;

        parallel gateway Gateway_Z await Message_C, Message_D
        then enable End_1;
    }
}
