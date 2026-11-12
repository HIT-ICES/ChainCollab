package chaincode

type StateMemory struct {
	Approved bool
	Counter  int
}

type SmartContract struct{}

func (cc *SmartContract) StartEvent_1() {
	cc.ChangeEventState("StartEvent_1", "COMPLETED")
	cc.ChangeGatewayState("Decision", "ENABLED")
}

func (cc *SmartContract) Message_A_Complete() {
	cc.ChangeMsgState("Message_A", "COMPLETED")
	cc.ChangeGatewayState("Decision", "ENABLED")
}

func (cc *SmartContract) Decision() {
	if Approved == true {
		cc.ChangeMsgState("Message_B", "ENABLED")
	} else {
		cc.ChangeEventState("EndEvent_1", "ENABLED")
	}
}

