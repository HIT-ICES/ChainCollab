func (cc *SmartContract) {message}_Complete(ctx contractapi.TransactionContextInterface) error {{
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "{message}")
	if err != nil {{
		return err
	}}

	clientIdentity := ctx.GetClientIdentity()
	clientMspID, _ := clientIdentity.GetMSPID()
	if clientMspID != msg.ReceiveMspID {{
		errorMessage := fmt.Sprintf("Msp denied")
		fmt.Println(errorMessage)
		return errors.New(fmt.Sprintf("Msp denied"))
	}}

	if msg.MsgState != WAITINGFORCONFIRMATION {{
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}}

	cc.ChangeMsgState(ctx, "{message}", COMPLETED)
	stub.SetEvent("{message}", []byte("Message has been done"))

	{pre_activate_next_hook}
	{change_next_state_code}

	{after_all_hook}
	return nil
}}