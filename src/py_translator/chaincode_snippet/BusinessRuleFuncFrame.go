func (cc *SmartContract) #business_rule#(ctx contractapi.TransactionContextInterface, instanceID string, ContentOfDmn string) error {

	// Read Business Info
	businessRule, err := cc.ReadBusinessRule(ctx, instanceID, "#business_rule#")
	if err != nil {
		return err
	}

	// Check the BusinessRule State
	if businessRule.State != ENABLED {
		return fmt.Errorf("The BusinessRule is not ENABLED")
	}

	// Combine the Parameters
	_args := make([][]byte, 4)
	_args[0] = []byte("createRecord")
	// input in json format
	ParamMapping := businessRule.ParamMapping
	realParamMapping := make(map[string]interface{})
	globalVariable, _err := cc.ReadGlobalVariable(ctx, instanceID)
	if _err != nil {
		return _err
	}

	for key, value := range ParamMapping {
		field := reflect.ValueOf(globalVariable).FieldByName(value)
		if !field.IsValid() {
			return fmt.Errorf("The field %s is not valid", value)
		}
		realParamMapping[key] = field.Interface()		
	}
	var inputJsonBytes []byte
	inputJsonBytes, err= json.Marshal(realParamMapping)
	if err != nil {
		return err
	}
	_args[1] = inputJsonBytes

	// DMN Content
	_args[2] = []byte(ContentOfDmn)

	// decisionId
	_args[3] = []byte(businessRule.DecisionId)

	// Invoke DMN Engine Chaincode
	var resJson string
	resJson, err=cc.Invoke_Other_chaincode(ctx, "asset:v1","default", _args)

	// Set the Result
	var res map[string]interface{}
	err = json.Unmarshal([]byte(resJson), &res)
	if err != nil {
		return err
	}

	for key, value := range res {
		field := reflect.ValueOf(globalVariable).FieldByName(key)
		if !field.IsValid() {
			return fmt.Errorf("The field %s is not valid", key)
		}
		field.Set(reflect.ValueOf(value))
	}

	// Update the GlobalVariable
	err = cc.SetGlobalVariable(ctx, instanceID, globalVariable)

	// Change the BusinessRule State
	cc.ChangeBusinessRuleState(ctx, instanceID, "#business_rule#", COMPLETED)

    #pre_activate_next_hook#
    #change_next_state_code#
    #after_all_hook#

	return nil
}