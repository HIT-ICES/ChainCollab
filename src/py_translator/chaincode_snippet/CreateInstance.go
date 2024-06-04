func (cc *SmartContract) CreateInstance(ctx contractapi.TransactionContextInterface, InitParameters string) (string, error) {
	stub := ctx.GetStub()

	isInitedBytes, err := stub.GetState("isInited")
	if err != nil {
		return "", fmt.Errorf("Failed to read from world state. %s", err.Error())
	}

	if isInitedBytes != nil {
		return "", fmt.Errorf("The instance has been initialized.")
	}

	var isInited bool
	err = json.Unmarshal(isInitedBytes, &isInited)
	if err != nil {
		return "", fmt.Errorf("Failed to unmarshal. %s", err.Error())
	}

	if !isInited {
		return "", fmt.Errorf("The instance has not been initialized.")
	}

	// get the instanceID

	var instanceID string
	instanceIDString, err := stub.GetState("currentInstanceID")
	if err != nil {
		return "", fmt.Errorf("Failed to read from world state. %s", err.Error())
	}

	err = json.Unmarshal(instanceIDString, &instanceID)
	if err != nil {
		return "", fmt.Errorf("Failed to unmarshal. %s", err.Error())
	}

	// Create the instance with the data from the InitParameters
	var initParameters InitParameters
	err = json.Unmarshal([]byte(InitParameters), &initParameters)
	if err != nil {
		return "", fmt.Errorf("Failed to unmarshal. %s", err.Error())
	}

	instance := Instance{
		InstanceID:          instanceID,
		InstanceStateMemory: &InstanceStateMemory{},
		InstanceElements:    make(map[string]*InstanceElement),
	}

	// this part is hard coded in generate time
	// Create Message
	// Create Participant
	// Create Event
	// Create Gateway
	// And so on
	{
		create_elements_code
	}

	// Save the instance
	instanceBytes, err := json.Marshal(instance)
	if err != nil {
		return "", fmt.Errorf("Failed to marshal. %s", err.Error())
	}

	err = stub.PutState(instanceID, instanceBytes)
	if err != nil {
		return "", fmt.Errorf("Failed to write to world state. %s", err.Error())
	}

	// Update the currentInstanceID
	currentInstanceID, err := strconv.Atoi(instanceID)
	if err != nil {
		return "", fmt.Errorf("Failed to convert. %s", err.Error())
	}

	currentInstanceID++

	currentInstanceIDBytes, err := json.Marshal(currentInstanceID)
	if err != nil {
		return "", fmt.Errorf("Failed to marshal. %s", err.Error())
	}

	err = stub.PutState("currentInstanceID", currentInstanceIDBytes)
	if err != nil {
		return "", fmt.Errorf("Failed to write to world state. %s", err.Error())
	}

	return instanceID, nil

}