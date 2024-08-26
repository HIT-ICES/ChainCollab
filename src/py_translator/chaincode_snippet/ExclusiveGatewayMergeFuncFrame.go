func (cc *SmartContract) #exclusive_gateway#(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance,err:=cc.GetInstance(ctx, instanceID)
	gtw, err := cc.ReadGtw(ctx, instanceID, "#exclusive_gateway#")
	if err != nil {
		return err
	}

	if gtw.GatewayState != ENABLED {
		errorMessage := fmt.Sprintf("Gateway state %s is not allowed", gtw.GatewayID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeGtwState(ctx, instance, gtw.GatewayID, COMPLETED)
	stub.SetEvent("#exclusive_gateway#", []byte("ExclusiveGateway has been done"))
	cc.SetInstance(ctx, instance)
    #pre_activate_next_hook#
    #change_next_state_code#
    #after_all_hook#
	cc.SetInstance(ctx, instance)
	return nil
}