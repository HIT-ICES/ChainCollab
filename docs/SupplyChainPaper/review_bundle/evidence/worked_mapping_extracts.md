# Worked mapping extracts

Every block below is copied verbatim from an archived raw file, with archive-relative path and line numbers. It is evidence, not repaired pseudocode.

## Message fields to globals/state memory

`source_models/SupplyChainPaper.bpmn:24`

```xml
   24:   <bpmn2:message id="Message_0hpha6h" name="Details Provision">
   25:     <bpmn2:documentation>{"properties":{"requestId":{"type":"number","description":"Unique identifier of the request for additional details "},"supplierReputation":{"type":"number","description":"A numerical rating representing the supplier's reputation."}},"required":["requestId","supplierReputation"],"files":{},"file required":[]}</bpmn2:documentation>
   26:   </bpmn2:message>
   27:   <bpmn2:message id="Message_0rwz1km" name="Request Details">
   28:     <bpmn2:documentation>{"properties":{"requestId":{"type":"number","description":" Unique identifier of the request for additional details "},"numberOfUnits":{"type":"number","description":" Total number of units in the order requested"},"urgent":{"type":"boolean","description":"Indicates whether the order requires urgent delivery."}},"required":["requestId","numberOfUnits","urgent"],"files":{},"file required":[]}</bpmn2:documentation>
   29:   </bpmn2:message>
```

`pim/SupplyChainPaper.b2c:52`

```text
   52:             multiMin 0
   53:             multiMax 0
   54:             attributes {
   55:                 role = "Special carrier"
   56: 
   57:             }
   58:         }
   59: 
   60:     }
   61: 
   62: 
   63: 
   64:     globals {
   65:         Confirm1: bool
   66:         Confirm2: bool
   67:         Confirm3: string
   68:         DeliveryConfirmation: bool
   69:         FinalPriority: string
   70:         NumberOfUnits: int
   71:         OrderDetails: string
   72:         ProductionStart: string
```

`fabric/raw/SupplyChainPaper.go:1389`

```go
 1389: func (cc *SmartContract) Message_0hpha6h_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string, requestId int, supplierReputation int) error {
 1390: 	stub := ctx.GetStub()
 1391: 	instance, err := cc.GetInstance(ctx, instanceID)
 1392: 	msg, err := cc.ReadMsg(ctx, instanceID, "Message_0hpha6h")
 1393: 	if err != nil {
 1394: 		return err
 1395: 	}
 1396: 
 1397: 	//
 1398: 	if cc.check_participant(ctx, instanceID, msg.SendParticipantID) == false {
 1399: 		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
 1400: 		fmt.Println(errorMessage)
 1401: 		return fmt.Errorf(errorMessage)
 1402: 	}
 1403: 
 1404: 	if msg.MsgState != ENABLED {
 1405: 		errorMessage := fmt.Sprintf("Message state %s is not allowed", msg.MessageID)
 1406: 		fmt.Println(errorMessage)
 1407: 		return fmt.Errorf(errorMessage)
 1408: 	}
 1409: 
 1410: 	cc.ChangeMsgFireflyTranID(ctx, instance, fireflyTranID, msg.MessageID)
 1411: 	cc.ChangeMsgState(ctx, instance, "Message_0hpha6h", COMPLETED)
 1412: 
 1413: globalMemory,readGloabolError := cc.ReadGlobalVariable(ctx, instanceID)
 1414: 	if readGloabolError != nil {
 1415: 		fmt.Println(readGloabolError.Error())
 1416: 		return readGloabolError
 1417: 	}
 1418: 	globalMemory.RequestId = requestId
 1419: 	globalMemory.SupplierReputation = supplierReputation
 1420: 	setGloabolErrror := cc.SetGlobalVariable(ctx, instance, globalMemory)
 1421: 	if setGloabolErrror != nil {
```

`fabric/raw/SupplyChainPaper.go:1532`

```go
 1532: func (cc *SmartContract) Message_0rwz1km_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string, numberOfUnits int, requestId int, urgent bool) error {
 1533: 	stub := ctx.GetStub()
 1534: 	instance, err := cc.GetInstance(ctx, instanceID)
 1535: 	msg, err := cc.ReadMsg(ctx, instanceID, "Message_0rwz1km")
 1536: 	if err != nil {
 1537: 		return err
 1538: 	}
 1539: 
 1540: 	//
 1541: 	if cc.check_participant(ctx, instanceID, msg.SendParticipantID) == false {
 1542: 		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
 1543: 		fmt.Println(errorMessage)
 1544: 		return fmt.Errorf(errorMessage)
 1545: 	}
 1546: 
 1547: 	if msg.MsgState != ENABLED {
 1548: 		errorMessage := fmt.Sprintf("Message state %s is not allowed", msg.MessageID)
 1549: 		fmt.Println(errorMessage)
 1550: 		return fmt.Errorf(errorMessage)
 1551: 	}
 1552: 
 1553: 	cc.ChangeMsgFireflyTranID(ctx, instance, fireflyTranID, msg.MessageID)
 1554: 	cc.ChangeMsgState(ctx, instance, "Message_0rwz1km", COMPLETED)
 1555: 
 1556: globalMemory,readGloabolError := cc.ReadGlobalVariable(ctx, instanceID)
 1557: 	if readGloabolError != nil {
 1558: 		fmt.Println(readGloabolError.Error())
 1559: 		return readGloabolError
 1560: 	}
 1561: 	globalMemory.NumberOfUnits = numberOfUnits
 1562: 	globalMemory.RequestId = requestId
 1563: 	globalMemory.Urgent = urgent
 1564: 	setGloabolErrror := cc.SetGlobalVariable(ctx, instance, globalMemory)
 1565: 	if setGloabolErrror != nil {
```

`geth/raw/SupplyChainPaper.sol:1033`

```solidity
 1033: function Message_0hpha6h_Send(uint256 instanceId, string calldata fireflyTranId, int256 requestId, int256 supplierReputation) external onlyInitialized {
 1034:         Instance storage inst = _getInstance(instanceId);
 1035:         Message storage m = inst.messages[MessageKey.Message_0hpha6h];
 1036:         require(m.exists, "message not set");
 1037:         _checkParticipant(inst, m.sendParticipant);
 1038:         require(m.state == ElementState.ENABLED, "message state not allowed");
 1039: 
 1040:         m.fireflyTranId = fireflyTranId;
 1041:         inst.stateMemory.RequestId = requestId;
 1042:         inst.stateMemory.SupplierReputation = supplierReputation;
 1043:         m.state = ElementState.COMPLETED;
 1044:         emit MessageSent(instanceId, MessageKey.Message_0hpha6h, fireflyTranId);
 1045:         inst.messages[MessageKey.Message_1io2g9u].state = ElementState.ENABLED;
```

`geth/raw/SupplyChainPaper.sol:1064`

```solidity
 1064: function Message_0rwz1km_Send(uint256 instanceId, string calldata fireflyTranId, int256 requestId, int256 numberOfUnits, bool urgent) external onlyInitialized {
 1065:         Instance storage inst = _getInstance(instanceId);
 1066:         Message storage m = inst.messages[MessageKey.Message_0rwz1km];
 1067:         require(m.exists, "message not set");
 1068:         _checkParticipant(inst, m.sendParticipant);
 1069:         require(m.state == ElementState.ENABLED, "message state not allowed");
 1070: 
 1071:         m.fireflyTranId = fireflyTranId;
 1072:         inst.stateMemory.RequestId = requestId;
 1073:         inst.stateMemory.NumberOfUnits = numberOfUnits;
 1074:         inst.stateMemory.Urgent = urgent;
 1075:         m.state = ElementState.COMPLETED;
 1076:         emit MessageSent(instanceId, MessageKey.Message_0rwz1km, fireflyTranId);
 1077:         inst.messages[MessageKey.Message_0hpha6h].state = ElementState.ENABLED;
```

## Business rule and DMN binding evidence

`source_models/SupplyChainPaper.bpmn:158`

```xml
  158:     <bpmn2:businessRuleTask id="Activity_0rm8bkp" name="Priority Decision">
  159:       <bpmn2:documentation>{"inputs":[{"name":"numberOfUnits","type":"number","description":" Total number of units in the order requested"},{"name":"urgent","type":"boolean","description":"Indicates whether the order requires urgent delivery."},{"name":"supplierReputation","type":"number","description":"A numerical rating representing the supplier's reputation."}],"outputs":[{"name":"finalPriority","type":"string","description":""}]}</bpmn2:documentation>
  160:       <bpmn2:incoming>Flow_19s99wl</bpmn2:incoming>
  161:       <bpmn2:outgoing>Flow_1jxt9fr</bpmn2:outgoing>
  162:     </bpmn2:businessRuleTask>
  163:     <bpmn2:sequenceFlow id="Flow_19s99wl" sourceRef="ChoreographyTask_0q1fvry" targetRef="Activity_0rm8bkp" />
  164:     <bpmn2:sequenceFlow id="Flow_1jxt9fr" sourceRef="Activity_0rm8bkp" targetRef="Gateway_0ep8cuh" />
```

`source_models/supplyChainPaper.dmn:3` and `:70`

```xml
    3:   <decision id="decision_0tybghz" name="Initial Priority Decision">
    4:     <informationRequirement id="InformationRequirement_1yax2nr">
    5:       <requiredInput href="#InputData_0x10kua" />
    6:     </informationRequirement>
    7:     <informationRequirement id="InformationRequirement_0968tcf">
    8:       <requiredInput href="#InputData_19y9i1v" />
    9:     </informationRequirement>
   10:     <decisionTable id="decisionTable_1v3tii8">
   11:       <input id="input1" label="numberOfUnits">
   12:         <inputExpression id="inputExpression1" typeRef="number">
   13:           <text>numberOfUnits</text>
   14:         </inputExpression>
   15:       </input>
   16:       <input id="InputClause_0pvns0w" label="urgent">
   17:         <inputExpression id="LiteralExpression_08nncbj" typeRef="boolean">
   18:           <text>urgent</text>
   19:         </inputExpression>
   20:       </input>
   21:       <output id="output1" label="initialPriority" name="initialPriority" typeRef="string" />
   22:       <rule id="DecisionRule_0u3ic44">
   23:         <inputEntry id="UnaryTests_0ju5tlr">
...
   70:   <decision id="Decision_0zwjfyy" name="Final Priority Adjustment Decision">
   71:     <informationRequirement id="InformationRequirement_0hefcti">
   72:       <requiredDecision href="#decision_0tybghz" />
   73:     </informationRequirement>
   74:     <informationRequirement id="InformationRequirement_1o26uw3">
   75:       <requiredInput href="#InputData_01mbjhm" />
   76:     </informationRequirement>
   77:     <decisionTable id="DecisionTable_1c43yo6">
   78:       <input id="InputClause_14snh1s" label="initialPriority">
   79:         <inputExpression id="LiteralExpression_0zgz0u7" typeRef="string">
   80:           <text>initialPriority</text>
   81:         </inputExpression>
   82:       </input>
   83:       <input id="InputClause_0r7er56" label="supplierReputation">
   84:         <inputExpression id="LiteralExpression_14je7bl" typeRef="number">
   85:           <text>supplierReputation</text>
   86:         </inputExpression>
   87:       </input>
   88:       <output id="OutputClause_0ugy0r3" label="finalPriority" name="finalPriority" typeRef="string" />
   89:       <rule id="DecisionRule_1ji9p5q">
```

`pim/SupplyChainPaper.b2c:177`

```text
  177:         businessrule Activity_0rm8bkp {
  178:             dmn "Activity_0rm8bkp.dmn"
  179:             decision "Activity_0rm8bkp_DecisionID"
  180:             input mapping {
  181:                 numberOfUnits -> NumberOfUnits
  182:                 urgent -> Urgent
  183:                 supplierReputation -> SupplierReputation
  184: 
  185:             }
  186:             output mapping {
  187:                 finalPriority -> FinalPriority
  188: 
  189:             }
  190: 
  191:             initial state INACTIVE
  192:         }
```

## Request, wait, continue, and output write-back

`fabric/raw/SupplyChainPaper.go:967`

```go
  967: func (cc *SmartContract) Activity_0rm8bkp(ctx contractapi.TransactionContextInterface, instanceID string) error {
  968: 
  969: 
  970: 	instance, err := cc.GetInstance(ctx, instanceID)
  971: 	// Read Business Info
  972: 	businessRule, err := cc.ReadBusinessRule(ctx, instanceID, "Activity_0rm8bkp")
  973: 	if err != nil {
  974: 		return err
  975: 	}
  976: 
  977: 	// Check the BusinessRule State
  978: 	if businessRule.State != ENABLED {
  979: 		return fmt.Errorf("The BusinessRule is not ENABLED")
  980: 	}
  981: 
  982: 	// Get the CID
  983: 
  984: 	res,err := cc.Invoke_Other_chaincode(ctx, "Oracle:v1", "default", oracle.EncodeGetDataItemArgs(
  985: 		instanceID, "Activity_0rm8bkp",
  986: 	))
  987: 	if err != nil {
  988: 		return  err
  989: 	}
  990: 
  991: 	var dataItem *oracle.DataItem
  992: 	dataItem, err = oracle.DecodeGetDataItemResult(res)
  993: 	if err != nil {
  994: 		return  err
  995: 	}
  996: 
  997: 	eventPayload := map[string]string{
  998: 		"ID":        "Activity_0rm8bkp",
  999: 		"InstanceID": instanceID,
 1000: 		"Func":	   "Activity_0rm8bkp_Continue",
 1001: 		"CID": dataItem.Value, 
 1002: 	}
 1003: 
 1004: 	eventPayloadAsBytes, err := json.Marshal(eventPayload)
 1005: 	if err != nil {
 1006: 		return fmt.Errorf("failed to marshal event payload: %v", err)
 1007: 	}
 1008: 
 1009: 	err = ctx.GetStub().SetEvent("DMNContentRequired", eventPayloadAsBytes)
 1010: 	if err != nil {
 1011: 		return fmt.Errorf("failed to set event: %v", err)
 1012: 	}
 1013: 
 1014: 	cc.ChangeBusinessRuleState(ctx, instance, "Activity_0rm8bkp", WAITINGFORCONFIRMATION)
 1015: 	cc.SetInstance(ctx, instance)
 1016: 
 1017: 	return nil
 1018: }
 1019: 
 1020: func (cc *SmartContract) Activity_0rm8bkp_Continue(ctx contractapi.TransactionContextInterface, instanceID string, ContentOfDmn string) error {
```

`fabric/raw/SupplyChainPaper.go:1042`

```go
 1042: 	// input in json format
 1043: 	ParamMapping := businessRule.ParamMapping
 1044: 	realParamMapping := make(map[string]interface{})
 1045: 	globalVariable, _err := cc.ReadGlobalVariable(ctx, instanceID)
 1046: 	if _err != nil {
 1047: 		return _err
 1048: 	}
 1049: 
 1050: 	for key, value := range ParamMapping {
 1051: 		field := reflect.ValueOf(globalVariable).Elem().FieldByName(strings.Title(value))
 1052: 		if !field.IsValid() {
 1053: 			return fmt.Errorf("The field %s is not valid", value)
 1054: 		}
 1055: 		realParamMapping[key] = field.Interface()		
 1056: 	}
 1057: 	var inputJsonBytes []byte
 1058: 	inputJsonBytes, err= json.Marshal(realParamMapping)
 1059: 	if err != nil {
 1060: 		return err
 1061: 	}
 1062: 	_args[1] = inputJsonBytes
 1063: 
 1064: 	// DMN Content
 1065: 	_args[2] = []byte(ContentOfDmn)
 1066: 
 1067: 	// decisionId
 1068: 	_args[3] = []byte(businessRule.DecisionID)
 1069: 
 1070: 	// Invoke DMN Engine Chaincode
 1071: 	var resJson []byte
 1072: 	resJson, err=cc.Invoke_Other_chaincode(ctx, "DMNEngine:v1","default", _args)
 1073: 
 1074: 	// Set the Result
```

`fabric/raw/SupplyChainPaper.go:1081`

```go
 1081: 	output := res["output"]
 1082: 	fmt.Println("output: ", output)  
 1083: 	if outputArr, ok := output.([]interface{}); ok {  
 1084: 		for _, item := range outputArr {  
 1085: 			itemMap := item.(map[string]interface{})  
 1086: 			for key, value := range itemMap {  
 1087: 				fmt.Printf("Key: %s, Type: %T, Value: %v\n", key,value,value)  
 1088: 				globalName , _ := ParamMapping[key]
 1089: 				field := reflect.ValueOf(globalVariable).Elem().FieldByName(strings.Title(globalName))
 1090: 				if !field.IsValid() {
 1091: 					return fmt.Errorf("The field %s is not valid", key)
 1092: 				}
 1093: 				switch field.Kind() {
 1094: 					case reflect.Int:
 1095: 						if valueFloat, ok := value.(float64); ok {
 1096: 							field.SetInt(int64(valueFloat))
 1097: 						} else {
 1098: 							return fmt.Errorf("Unable to convert %v to int", value)
 1099: 						}
 1100: 					case reflect.String:
 1101: 						if valueStr, ok := value.(string); ok {
 1102: 							field.SetString(valueStr)
 1103: 						} else {
 1104: 							return fmt.Errorf("Unable to convert %v to string", value)
 1105: 						}
 1106: 					case reflect.Bool: // 处理布尔类型
 1107: 						if valueBool, ok := value.(bool); ok {
 1108: 							field.SetBool(valueBool)
 1109: 						} else {
 1110: 							return fmt.Errorf("Unable to convert %v to bool", value)
 1111: 						}
 1112: 					// 其他类型转换可以根据需求添加
 1113: 					default:
 1114: 						return fmt.Errorf("Unsupported field type: %s", field.Type())
 1115:                 }
 1116: 				// field.Set(reflect.ValueOf(value))
 1117: 			}  
 1118: 		}  
 1119: 	}  
 1120: 
 1121: 	// Update the GlobalVariable
 1122: 	err = cc.SetGlobalVariable(ctx, instance, globalVariable)
 1123: 
 1124: 	// Change the BusinessRule State
 1125: 	cc.ChangeBusinessRuleState(ctx, instance, "Activity_0rm8bkp", COMPLETED)
 1126: 
 1127: 	cc.ChangeGtwState(ctx, instance, "Gateway_0ep8cuh", ENABLED)
 1128: 
 1129: 
 1130: 	cc.SetInstance(ctx, instance)
```

`geth/raw/SupplyChainPaper.sol:897`

```solidity
  897:     function Activity_0rm8bkp(uint256 instanceId) external onlyInitialized {
  898:         Instance storage inst = _getInstance(instanceId);
  899:         BusinessRule storage br = inst.businessRules[BusinessRuleKey.Activity_0rm8bkp];
  900:         require(br.exists, "business rule not set");
  901:         require(br.state == ElementState.ENABLED, "business rule not enabled");
  902:         _checkBusinessRuleCaller(inst, br);
  903: 
  904:         string memory inputBody = "";
  905:         inputBody = _jsonAppendField(
  906:             inputBody,
  907:             _jsonField(
  908:                 "numberOfUnits",
  909:             _jsonInt(inst.stateMemory.NumberOfUnits)
  910:             )
  911:         );
  912:         inputBody = _jsonAppendField(
  913:             inputBody,
  914:             _jsonField(
  915:                 "urgent",
  916:             _jsonBool(inst.stateMemory.Urgent)
  917:             )
  918:         );
  919:         inputBody = _jsonAppendField(
  920:             inputBody,
  921:             _jsonField(
  922:                 "supplierReputation",
  923:             _jsonInt(inst.stateMemory.SupplierReputation)
  924:             )
  925:         );
  926:         string memory inputData = _jsonObject(inputBody);
  927:         IDmnLite dmnLite = IDmnLite(inst.dmnLiteAddress);
  928:         require(bytes(br.dmnCid).length != 0, "dmn cid not set");
  929:         bytes32 requestId = dmnLite.requestDMNDecision(
  930:             inst.dmnEvalUrl,
  931:             br.dmnCid,
  932:             br.decisionId,
  933:             inputData
  934:         );
  935:         require(requestId != bytes32(0), "dmn request failed");
  936:         br.requestId = requestId;
  937:         br.requestedAt = block.timestamp;
  938:         br.fulfilledAt = 0;
  939:         br.lastRawResult = "";
  940:         br.state = ElementState.WAITING_FOR_CONFIRMATION;
  941:         emit BusinessRuleRequested(instanceId, BusinessRuleKey.Activity_0rm8bkp, requestId);
  942:     }
  943: 
  944:     function Activity_0rm8bkp_Continue(uint256 instanceId) external onlyInitialized {
  945:         Instance storage inst = _getInstance(instanceId);
  946:         BusinessRule storage br = inst.businessRules[BusinessRuleKey.Activity_0rm8bkp];
  947:         require(br.exists, "business rule not set");
  948:         require(br.state == ElementState.WAITING_FOR_CONFIRMATION, "business rule not waiting");
  949:         require(br.requestId != bytes32(0), "business rule not requested");
  950:         _checkBusinessRuleCaller(inst, br);
  951: 
  952:         IDmnLite dmnLite = IDmnLite(inst.dmnLiteAddress);
  953:         (
  954:             uint8 requestState,
  955:             address requester,
  956:             ,
  957:             uint256 fulfilledAt,
  958:             bool exists
  959:         ) = dmnLite.getRequestStatus(br.requestId);
  960:         require(exists, "dmn request missing");
  961:         require(requester == address(this), "unexpected dmn requester");
  962:         require(requestState == DMN_REQUEST_FULFILLED, "dmn result not ready");
  963: 
  964:         string memory raw = dmnLite.getRawByRequestId(br.requestId);
  965:         br.lastRawResult = raw;
  966:         br.fulfilledAt = fulfilledAt;
  967:         inst.stateMemory.FinalPriority = _extractJsonString(raw, "finalPriority");
  968:         br.state = ElementState.COMPLETED;
  969:         inst.gateways[GatewayKey.Gateway_0ep8cuh].state = ElementState.ENABLED;
  970: 
  971: 
  972:         emit BusinessRuleCompleted(instanceId, BusinessRuleKey.Activity_0rm8bkp, br.requestId);
```

## Rule completion and four priority branches

`pim/SupplyChainPaper.b2c:236`

```text
  236:         when gateway Gateway_0ep8cuh completed
  237:         choose {
  238:             if FinalPriority == "Low"
  239:             then enable Message_1oxmq1k;
  240:             if FinalPriority == "High"
  241:             then enable Message_1dmeexg;
  242:             if FinalPriority == "Medium"
  243:             then enable Message_1dzkcn0;
  244:             if FinalPriority == "VeryLow"
  245:             then enable Message_0d2xte5;
  246: 
  247:         }
  248:         when gateway Gateway_0onpe6x completed
  249:         then enable Message_0cba4t6, enable Message_0pm90nx;
  250: 
  251:         parallel gateway Gateway_1fbifca await Message_0cba4t6, Message_0pm90nx
  252:         then enable Message_0rwz1km;
  253: 
  254:         when businessrule Activity_0rm8bkp done
  255:         then enable Gateway_0ep8cuh;
```

`fabric/raw/SupplyChainPaper.go:2111`

```go
 2111: 	if gtw.GatewayState != ENABLED {
 2112: 		errorMessage := fmt.Sprintf("Gateway state %s is not allowed", gtw.GatewayID)
 2113: 		fmt.Println(errorMessage)
 2114: 		return fmt.Errorf(errorMessage)
 2115: 	}
 2116: 
 2117: 
 2118: 	cc.ChangeGtwState(ctx, instance, gtw.GatewayID, COMPLETED)
 2119: 	stub.SetEvent("Gateway_0ep8cuh", []byte("Gateway has been completed"))
 2120: 	cc.SetInstance(ctx, instance)
 2121: 	if instance.InstanceStateMemory.FinalPriority == "Low" {
 2122: 		cc.ChangeMsgState(ctx, instance, "Message_1oxmq1k", ENABLED)
 2123: 	} else if instance.InstanceStateMemory.FinalPriority == "High" {
 2124: 		cc.ChangeMsgState(ctx, instance, "Message_1dmeexg", ENABLED)
 2125: 	} else if instance.InstanceStateMemory.FinalPriority == "Medium" {
 2126: 		cc.ChangeMsgState(ctx, instance, "Message_1dzkcn0", ENABLED)
 2127: 	} else if instance.InstanceStateMemory.FinalPriority == "VeryLow" {
 2128: 		cc.ChangeMsgState(ctx, instance, "Message_0d2xte5", ENABLED)
 2129: 	}
 2130: 
```

`geth/raw/SupplyChainPaper.sol:1196`

```solidity
 1196: function Gateway_0ep8cuh(uint256 instanceId) external onlyInitialized {
 1197:         Instance storage inst = _getInstance(instanceId);
 1198:         Gateway storage g = inst.gateways[GatewayKey.Gateway_0ep8cuh];
 1199:         require(g.exists, "gateway not set");
 1200:         require(g.state == ElementState.ENABLED, "gateway state not allowed");
 1201: 
 1202:         g.state = ElementState.COMPLETED;
 1203:         emit GatewayDone(instanceId, GatewayKey.Gateway_0ep8cuh);
 1204:         if (keccak256(bytes(inst.stateMemory.FinalPriority)) == keccak256(bytes("Low"))) {
 1205:             inst.messages[MessageKey.Message_1oxmq1k].state = ElementState.ENABLED;
 1206:         }
 1207:         else if (keccak256(bytes(inst.stateMemory.FinalPriority)) == keccak256(bytes("High"))) {
 1208:             inst.messages[MessageKey.Message_1dmeexg].state = ElementState.ENABLED;
 1209:         }
 1210:         else if (keccak256(bytes(inst.stateMemory.FinalPriority)) == keccak256(bytes("Medium"))) {
 1211:             inst.messages[MessageKey.Message_1dzkcn0].state = ElementState.ENABLED;
 1212:         }
 1213:         else if (keccak256(bytes(inst.stateMemory.FinalPriority)) == keccak256(bytes("VeryLow"))) {
 1214:             inst.messages[MessageKey.Message_0d2xte5].state = ElementState.ENABLED;
 1215:         }
 1216: 
```

## Parallel split and join

`source_models/SupplyChainPaper.bpmn:80`

```xml
   80:     <bpmn2:parallelGateway id="Gateway_0onpe6x">
   81:       <bpmn2:incoming>Flow_0by1ery</bpmn2:incoming>
   82:       <bpmn2:outgoing>Flow_0fs2i4x</bpmn2:outgoing>
   83:       <bpmn2:outgoing>Flow_1wyrozo</bpmn2:outgoing>
   84:     </bpmn2:parallelGateway>
   85:     <bpmn2:sequenceFlow id="Flow_0by1ery" sourceRef="ChoreographyTask_0m4d50p" targetRef="Gateway_0onpe6x" />
   86:     <bpmn2:choreographyTask id="ChoreographyTask_0i0ht39" name="Forward order for supplies" initiatingParticipantRef="Participant_09cjol2">
   87:       <bpmn2:incoming>Flow_0fs2i4x</bpmn2:incoming>
   88:       <bpmn2:outgoing>Flow_1azhglw</bpmn2:outgoing>
   89:       <bpmn2:participantRef>Participant_09cjol2</bpmn2:participantRef>
   90:       <bpmn2:participantRef>Participant_0sa2v7d</bpmn2:participantRef>
   91:       <bpmn2:messageFlowRef>MessageFlow_1m81z4l</bpmn2:messageFlowRef>
   92:     </bpmn2:choreographyTask>
   93:     <bpmn2:sequenceFlow id="Flow_0fs2i4x" sourceRef="Gateway_0onpe6x" targetRef="ChoreographyTask_0i0ht39" />
   94:     <bpmn2:choreographyTask id="ChoreographyTask_145bktk" name="Forward order for transport" initiatingParticipantRef="Participant_09cjol2">
   95:       <bpmn2:incoming>Flow_1wyrozo</bpmn2:incoming>
   96:       <bpmn2:outgoing>Flow_1tvz6lc</bpmn2:outgoing>
   97:       <bpmn2:participantRef>Participant_09cjol2</bpmn2:participantRef>
   98:       <bpmn2:participantRef>Participant_19j1e3o</bpmn2:participantRef>
   99:       <bpmn2:messageFlowRef>MessageFlow_1541zid</bpmn2:messageFlowRef>
  100:     </bpmn2:choreographyTask>
  101:     <bpmn2:sequenceFlow id="Flow_1wyrozo" sourceRef="Gateway_0onpe6x" targetRef="ChoreographyTask_145bktk" />
  102:     <bpmn2:parallelGateway id="Gateway_1fbifca">
  103:       <bpmn2:incoming>Flow_1azhglw</bpmn2:incoming>
  104:       <bpmn2:incoming>Flow_1tvz6lc</bpmn2:incoming>
  105:       <bpmn2:outgoing>Flow_0gtd6v3</bpmn2:outgoing>
  106:     </bpmn2:parallelGateway>
  107:     <bpmn2:sequenceFlow id="Flow_1azhglw" sourceRef="ChoreographyTask_0i0ht39" targetRef="Gateway_1fbifca" />
  108:     <bpmn2:sequenceFlow id="Flow_1tvz6lc" sourceRef="ChoreographyTask_145bktk" targetRef="Gateway_1fbifca" />
  109:     <bpmn2:choreographyTask id="ChoreographyTask_1cceq4q" name="Request details" initiatingParticipantRef="Participant_19j1e3o">
  110:       <bpmn2:incoming>Flow_0gtd6v3</bpmn2:incoming>
  111:       <bpmn2:outgoing>Flow_0imjwmb</bpmn2:outgoing>
  112:       <bpmn2:participantRef>Participant_19j1e3o</bpmn2:participantRef>
  113:       <bpmn2:participantRef>Participant_0sa2v7d</bpmn2:participantRef>
  114:       <bpmn2:messageFlowRef>MessageFlow_087ue4t</bpmn2:messageFlowRef>
  115:     </bpmn2:choreographyTask>
  116:     <bpmn2:sequenceFlow id="Flow_0gtd6v3" sourceRef="Gateway_1fbifca" targetRef="ChoreographyTask_1cceq4q" />
```

`pim/SupplyChainPaper.b2c:248`

```text
  248:         when gateway Gateway_0onpe6x completed
  249:         then enable Message_0cba4t6, enable Message_0pm90nx;
  250: 
  251:         parallel gateway Gateway_1fbifca await Message_0cba4t6, Message_0pm90nx
  252:         then enable Message_0rwz1km;
```

`geth/raw/SupplyChainPaper.sol:1219`

```solidity
 1219: function Gateway_0onpe6x(uint256 instanceId) external onlyInitialized {
 1220:         Instance storage inst = _getInstance(instanceId);
 1221:         Gateway storage g = inst.gateways[GatewayKey.Gateway_0onpe6x];
 1222:         require(g.exists, "gateway not set");
 1223:         require(g.state == ElementState.ENABLED, "gateway state not allowed");
 1224: 
 1225:         g.state = ElementState.COMPLETED;
 1226:         emit GatewayDone(instanceId, GatewayKey.Gateway_0onpe6x);
 1227:         inst.messages[MessageKey.Message_0cba4t6].state = ElementState.ENABLED;
 1228:         inst.messages[MessageKey.Message_0pm90nx].state = ElementState.ENABLED;
 1229: 
 1230:     }
 1231: 
 1232: function Gateway_1fbifca(uint256 instanceId) external onlyInitialized {
 1233:         Instance storage inst = _getInstance(instanceId);
 1234:         Gateway storage g = inst.gateways[GatewayKey.Gateway_1fbifca];
 1235:         require(g.exists, "gateway not set");
 1236:         require(g.state == ElementState.ENABLED, "gateway state not allowed");
 1237: 
 1238:         g.state = ElementState.COMPLETED;
 1239:         emit GatewayDone(instanceId, GatewayKey.Gateway_1fbifca);
 1240:         if (!(inst.messages[MessageKey.Message_0cba4t6].state == ElementState.COMPLETED && inst.messages[MessageKey.Message_0pm90nx].state == ElementState.COMPLETED)) {
 1241:                     revert("Parallel gateway prerequisites not met");
 1242:                 }
 1243:         inst.messages[MessageKey.Message_0rwz1km].state = ElementState.ENABLED;
 1244: 
```
