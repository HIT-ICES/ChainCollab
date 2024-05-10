func (cc *SmartContract) ReadState(ctx contractapi.TransactionContextInterface) (*StateMemory, error) {
	stateJSON, err := ctx.GetStub().GetState("currentMemory")
	if err != nil {
		return nil, err
	}

	if stateJSON == nil {
		// return a empty stateMemory
		return &StateMemory{}, nil
	}

	var stateMemory StateMemory
	err = json.Unmarshal(stateJSON, &stateMemory)
	if err != nil {
		fmt.Println(err.Error())
		return nil, err
	}

	return &stateMemory, nil
}

func (cc *SmartContract) PutState(ctx contractapi.TransactionContextInterface, stateName string, stateValue interface{}) error {
	stub := ctx.GetStub()
	currentMemory, err := cc.ReadState("currentMemory")
	if err != nil {
		return err
	}
	val := reflect.ValueOf(currentMemory)
	if val.Kind() != reflect.Ptr || val.Elem().Kind() != reflect.Struct {
		return errors.New("currentMemory is not a struct pointer")
	}
	field := val.Elem().FieldByName(stateName)
	if !field.IsValid() {
		return errors.New("field does not exist")
	}
	if !field.CanSet() {
		return errors.New("field cannot be set")
	}
	// 根据字段类型将stateValue转换为合适的类型
	switch field.Interface().(type) {
	case string:
		stringValue, ok := stateValue.(string)
		if !ok {
			return errors.New("stateValue is not a string")
		}
		field.SetString(stringValue)
	case int:
		intValue, ok := stateValue.(int)
		if !ok {
			return errors.New("stateValue is not an int")
		}
		field.SetInt(int64(intValue))
	case float64:
		floatValue, ok := stateValue.(float64)
		if !ok {
			return errors.New("stateValue is not a float64")
		}
		field.SetFloat(floatValue)
	case bool:
		boolValue, ok := stateValue.(bool)
		if !ok {
			return errors.New("stateValue is not a bool")
		}
		field.SetBool(boolValue)
	// 添加其他类型的处理...
	default:
		return errors.New("unsupported field type")
	}

	currentMemoryJSON, err := json.Marshal(currentMemory)
	if err != nil {
		fmt.Println(err.Error())
		return err
	}

	err = stub.PutState("currentMemory", currentMemoryJSON)
	if err != nil {
		fmt.Println(err.Error())
		return err
	}

	return nil
}