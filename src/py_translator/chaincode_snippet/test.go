func (cc *SmartContract) {message}_Send(ctx contractapi.TransactionContextInterface, fireflyTranID string {more_parameters}) error {{
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "{message}")
	if err != nil {{
		return err
	}}

	clientIdentity := ctx.GetClientIdentity()
	clientMspID, _ := clientIdentity.GetMSPID()
	if clientMspID != msg.SendMspID {{
		errorMessage := fmt.Sprintf("Msp denied")
		fmt.Println(errorMessage)
		return errors.New(fmt.Sprintf("Msp denied"))
	}}
	if msg.MsgState != ENABLED {{
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}}

	msg.MsgState = WAITINGFORCONFIRMATION
	msg.FireflyTranID = fireflyTranID
	msgJSON, _ := json.Marshal(msg)
	stub.PutState("{message}", msgJSON)
	{put_more_parameters}
	stub.SetEvent("{message}", []byte("Message is waiting for confirmation"))

	{after_all_hook}
	return nil
}}