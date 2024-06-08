func (cc *SmartContract) Invoke_Other_chaincode(ctx contractapi.TransactionContextInterface, channel string, chaincodeName string, _args [][]byte) (string, error) {
	stub := ctx.GetStub()
	response := stub.InvokeChaincode(chaincodeName, _args, channel)

	if response.Status != shim.OK {
		return "", fmt.Errorf("failed to invoke chaincode. Response status: %d. Response message: %s", response.Status, response.Message)
	}

	fmt.Print("response.Payload: ")
	fmt.Println(string(response.Payload))

	return string(response.Payload), nil
}