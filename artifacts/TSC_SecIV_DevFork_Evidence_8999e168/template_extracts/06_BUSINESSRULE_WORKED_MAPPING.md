基准：dev-MultiBlockChain-fork，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`；日期 2026-10-27（Asia/Shanghai）。生成成功不代表部署或 DMN 执行成功。

## Stage 1 CIM

贯穿对象为 Priority Decision Activity_0rm8bkp。接口已迁移，但没有显式 DMN 引用。DMN 中 Decision_0zwjfyy 依赖 decision_0tybghz；PIM 合成 decisionID 与它们不同。

XML 摘录（继承根命名空间 xmlns:bpmn2="http://www.omg.org/spec/BPMN/20100524/MODEL"；xmlns:abc="https://chaincollab.io/schema/abc"）：`Experiment/BPMNwithDMNcase/new/SupplyChainPaper.bpmn:212` (`id="Activity_0rm8bkp"`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

```xml
<bpmn2:businessRuleTask id="Activity_0rm8bkp" name="Priority Decision">
      <bpmn2:extensionElements>
        <abc:BusinessRule>
          <abc:Input name="numberOfUnits" type="number" description=" Total number of units in the order requested" definition="{&quot;name&quot;:&quot;numberOfUnits&quot;,&quot;type&quot;:&quot;number&quot;,&quot;description&quot;:&quot; Total number of units in the order requested&quot;}" />
          <abc:Input name="urgent" type="boolean" description="Indicates whether the order requires urgent delivery." definition="{&quot;name&quot;:&quot;urgent&quot;,&quot;type&quot;:&quot;boolean&quot;,&quot;description&quot;:&quot;Indicates whether the order requires urgent delivery.&quot;}" />
          <abc:Input name="supplierReputation" type="number" description="A numerical rating representing the supplier's reputation." definition="{&quot;name&quot;:&quot;supplierReputation&quot;,&quot;type&quot;:&quot;number&quot;,&quot;description&quot;:&quot;A numerical rating representing the supplier's reputation.&quot;}" />
          <abc:Output name="finalPriority" type="string" description="" definition="{&quot;name&quot;:&quot;finalPriority&quot;,&quot;type&quot;:&quot;string&quot;,&quot;description&quot;:&quot;&quot;}" />
        </abc:BusinessRule>
      </bpmn2:extensionElements>
      <bpmn2:incoming>Flow_19s99wl</bpmn2:incoming>
      <bpmn2:outgoing>Flow_1jxt9fr</bpmn2:outgoing>
    </bpmn2:businessRuleTask>
```
XML 摘录（继承根命名空间 xmlns:bpmn2="http://www.omg.org/spec/BPMN/20100524/MODEL"；xmlns:abc="https://chaincollab.io/schema/abc"）：`Experiment/BPMNwithDMNcase/new/SupplyChainPaper.bpmn:225` (`id="Flow_1jxt9fr"`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

```xml
<bpmn2:sequenceFlow id="Flow_1jxt9fr" sourceRef="Activity_0rm8bkp" targetRef="Gateway_0ep8cuh" />
```

## Stage 2 PIM

原始摘录：`artifacts/TSC_SecIV_DevFork_Evidence_8999e168/generated_pim/SupplyChainPaper.b2c:177`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```text
        businessrule Activity_0rm8bkp {
            dmn "Activity_0rm8bkp.dmn"
            decision "Activity_0rm8bkp_DecisionID"
            input mapping {
                numberOfUnits -> NumberOfUnits
                urgent -> Urgent
                supplierReputation -> SupplierReputation

            }
            output mapping {
                finalPriority -> FinalPriority

            }

            initial state INACTIVE
        }

    }



    oracletasks {
```
原始摘录：`artifacts/TSC_SecIV_DevFork_Evidence_8999e168/generated_pim/SupplyChainPaper.b2c:254`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```text
        when businessrule Activity_0rm8bkp done
        then enable Gateway_0ep8cuh;

```
输入 globals：NumberOfUnits:int、Urgent:bool、SupplierReputation:int；输出 FinalPriority:string。RuleFlow 只启用 Gateway_0ep8cuh，不赋值；该 gateway 读取 FinalPriority 并判断 Low/High/Medium/VeryLow。

## Stage 3 Fabric specialization

请求函数查询 Oracle:v1/default 的 CID，发 DMNContentRequired，进入 WAITINGFORCONFIRMATION。Continue 显式接收 ContentOfDmn、校验 hash、根据 runtime ParamMapping 反射读取共享状态，调用 DMNEngine:v1/default 的 createRecord，反射写回 output 数组、置 COMPLETED，并执行 done_actions 启用后继。此平台没有 Geth requestId 协议。

Go context 未将 PIM I/O 映射逐字段展开；ParamMapping、DecisionID、DMN content 依赖 InitParameters。运行时同一 map 同时用于输入和输出，配置正确性仍待验证。不能声称 Go 自动落实了全部 PIM 参数映射。

真实诊断 context 精选：

```json
{
  "business_rules": [
    {
      "name": "Activity_0rm8bkp",
      "done_actions": "\tcc.ChangeGtwState(ctx, instance, \"Gateway_0ep8cuh\", ENABLED)\n"
    }
  ],
  "init_params": [
    {
      "name": "Activity_0rm8bkp_DecisionID",
      "type": "string"
    },
    {
      "name": "Activity_0rm8bkp_ParamMapping",
      "type": "map[string]string"
    },
    {
      "name": "Activity_0rm8bkp_Content",
      "type": "string"
    }
  ]
}
```
原始摘录：`artifacts/TSC_SecIV_DevFork_Evidence_8999e168/generated_fabric/SupplyChainPaper.go:967`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```go
func (cc *SmartContract) Activity_0rm8bkp(ctx contractapi.TransactionContextInterface, instanceID string) error {


	instance, err := cc.GetInstance(ctx, instanceID)
	// Read Business Info
	businessRule, err := cc.ReadBusinessRule(ctx, instanceID, "Activity_0rm8bkp")
	if err != nil {
		return err
	}

	// Check the BusinessRule State
	if businessRule.State != ENABLED {
		return fmt.Errorf("The BusinessRule is not ENABLED")
	}

	// Get the CID

	res,err := cc.Invoke_Other_chaincode(ctx, "Oracle:v1", "default", oracle.EncodeGetDataItemArgs(
		instanceID, "Activity_0rm8bkp",
	))
	if err != nil {
		return  err
	}

	var dataItem *oracle.DataItem
	dataItem, err = oracle.DecodeGetDataItemResult(res)
	if err != nil {
		return  err
	}

	eventPayload := map[string]string{
		"ID":        "Activity_0rm8bkp",
		"InstanceID": instanceID,
		"Func":	   "Activity_0rm8bkp_Continue",
		"CID": dataItem.Value, 
	}

	eventPayloadAsBytes, err := json.Marshal(eventPayload)
	if err != nil {
		return fmt.Errorf("failed to marshal event payload: %v", err)
	}

	err = ctx.GetStub().SetEvent("DMNContentRequired", eventPayloadAsBytes)
	if err != nil {
		return fmt.Errorf("failed to set event: %v", err)
	}

	cc.ChangeBusinessRuleState(ctx, instance, "Activity_0rm8bkp", WAITINGFORCONFIRMATION)
	cc.SetInstance(ctx, instance)

	return nil
}
```
原始摘录：`artifacts/TSC_SecIV_DevFork_Evidence_8999e168/generated_fabric/SupplyChainPaper.go:1020`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```go
func (cc *SmartContract) Activity_0rm8bkp_Continue(ctx contractapi.TransactionContextInterface, instanceID string, ContentOfDmn string) error {
	// Read Business Info
	instance,err:=cc.GetInstance(ctx, instanceID)
	businessRule, err := cc.ReadBusinessRule(ctx, instanceID, "Activity_0rm8bkp")
	if err != nil {
		return err
	}

	// Check the BusinessRule State
	if businessRule.State != WAITINGFORCONFIRMATION {
		return fmt.Errorf("The BusinessRule is not Actived")
	}

	// check the hash
	hashString, _ := cc.hashXML(ctx, ContentOfDmn)
	if hashString != businessRule.Hash {
		return fmt.Errorf("The hash is not matched")
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
		field := reflect.ValueOf(globalVariable).Elem().FieldByName(strings.Title(value))
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
	_args[3] = []byte(businessRule.DecisionID)

	// Invoke DMN Engine Chaincode
	var resJson []byte
	resJson, err=cc.Invoke_Other_chaincode(ctx, "DMNEngine:v1","default", _args)

	// Set the Result
	var res map[string]interface{}
	err = json.Unmarshal(resJson, &res)
	if err != nil {
		return err
	}

	output := res["output"]
	fmt.Println("output: ", output)  
	if outputArr, ok := output.([]interface{}); ok {  
		for _, item := range outputArr {  
			itemMap := item.(map[string]interface{})  
			for key, value := range itemMap {  
				fmt.Printf("Key: %s, Type: %T, Value: %v\n", key,value,value)  
				globalName , _ := ParamMapping[key]
				field := reflect.ValueOf(globalVariable).Elem().FieldByName(strings.Title(globalName))
				if !field.IsValid() {
					return fmt.Errorf("The field %s is not valid", key)
				}
				switch field.Kind() {
					case reflect.Int:
						if valueFloat, ok := value.(float64); ok {
							field.SetInt(int64(valueFloat))
						} else {
							return fmt.Errorf("Unable to convert %v to int", value)
						}
					case reflect.String:
						if valueStr, ok := value.(string); ok {
							field.SetString(valueStr)
						} else {
							return fmt.Errorf("Unable to convert %v to string", value)
						}
					case reflect.Bool: // 处理布尔类型
						if valueBool, ok := value.(bool); ok {
							field.SetBool(valueBool)
						} else {
							return fmt.Errorf("Unable to convert %v to bool", value)
						}
					// 其他类型转换可以根据需求添加
					default:
						return fmt.Errorf("Unsupported field type: %s", field.Type())
                }
				// field.Set(reflect.ValueOf(value))
			}  
		}  
	}  

	// Update the GlobalVariable
	err = cc.SetGlobalVariable(ctx, instance, globalVariable)

	// Change the BusinessRule State
	cc.ChangeBusinessRuleState(ctx, instance, "Activity_0rm8bkp", COMPLETED)

	cc.ChangeGtwState(ctx, instance, "Gateway_0ep8cuh", ENABLED)


	cc.SetInstance(ctx, instance)
	eventPayload := map[string]string{
		"ID":         "Activity_0rm8bkp_Continue",
		"InstanceID": instanceID,
	}

	eventPayloadAsBytes, err := json.Marshal(eventPayload)
	if err != nil {
		return fmt.Errorf("failed to marshal event payload: %v", err)
	}

	err = ctx.GetStub().SetEvent("Avtivity_continueDone", eventPayloadAsBytes)
	if err != nil {
		return fmt.Errorf("failed to set event: %v", err)
	}
	return nil

}
```

## Stage 4 Geth specialization

requestDMNDecision(evalUrl,CID,decisionId,inputData) 返回 requestId，持久化后 WAITING_FOR_CONFIRMATION；Continue 检查 getRequestStatus 的 requester/state，再 getRawByRequestId；按 output_mappings 读 finalPriority 写 FinalPriority，置 COMPLETED 并启用后继。Continue 只接收 instanceId，不接收 ContentOfDmn。

真实诊断 context 精选：

```json
[
  {
    "name": "Activity_0rm8bkp",
    "enum_name": "Activity_0rm8bkp",
    "config_param": "Activity_0rm8bkp",
    "content_param": "dmnCid",
    "hash_param": "dmnHash",
    "decision_param": "decisionId",
    "caller_restricted_param": "callerRestricted",
    "allowed_caller_param": "allowedCaller",
    "input_mappings": [
      {
        "param_name": "numberOfUnits",
        "param_literal": "\"numberOfUnits\"",
        "slot_name": "NumberOfUnits",
        "sol_type": "int256"
      },
      {
        "param_name": "urgent",
        "param_literal": "\"urgent\"",
        "slot_name": "Urgent",
        "sol_type": "bool"
      },
      {
        "param_name": "supplierReputation",
        "param_literal": "\"supplierReputation\"",
        "slot_name": "SupplierReputation",
        "sol_type": "int256"
      }
    ],
    "output_mappings": [
      {
        "param_name": "finalPriority",
        "param_literal": "\"finalPriority\"",
        "slot_name": "FinalPriority",
        "sol_type": "string"
      }
    ],
    "done_actions": "        inst.gateways[GatewayKey.Gateway_0ep8cuh].state = ElementState.ENABLED;\n"
  }
]
```
原始摘录：`artifacts/TSC_SecIV_DevFork_Evidence_8999e168/generated_geth/SupplyChainPaper.sol:897`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```sol
    function Activity_0rm8bkp(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        BusinessRule storage br = inst.businessRules[BusinessRuleKey.Activity_0rm8bkp];
        require(br.exists, "business rule not set");
        require(br.state == ElementState.ENABLED, "business rule not enabled");
        _checkBusinessRuleCaller(inst, br);

        string memory inputBody = "";
        inputBody = _jsonAppendField(
            inputBody,
            _jsonField(
                "numberOfUnits",
            _jsonInt(inst.stateMemory.NumberOfUnits)
            )
        );
        inputBody = _jsonAppendField(
            inputBody,
            _jsonField(
                "urgent",
            _jsonBool(inst.stateMemory.Urgent)
            )
        );
        inputBody = _jsonAppendField(
            inputBody,
            _jsonField(
                "supplierReputation",
            _jsonInt(inst.stateMemory.SupplierReputation)
            )
        );
        string memory inputData = _jsonObject(inputBody);
        IDmnLite dmnLite = IDmnLite(inst.dmnLiteAddress);
        require(bytes(br.dmnCid).length != 0, "dmn cid not set");
        bytes32 requestId = dmnLite.requestDMNDecision(
            inst.dmnEvalUrl,
            br.dmnCid,
            br.decisionId,
            inputData
        );
        require(requestId != bytes32(0), "dmn request failed");
        br.requestId = requestId;
        br.requestedAt = block.timestamp;
        br.fulfilledAt = 0;
        br.lastRawResult = "";
        br.state = ElementState.WAITING_FOR_CONFIRMATION;
        emit BusinessRuleRequested(instanceId, BusinessRuleKey.Activity_0rm8bkp, requestId);
    }
```
原始摘录：`artifacts/TSC_SecIV_DevFork_Evidence_8999e168/generated_geth/SupplyChainPaper.sol:944`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```sol
    function Activity_0rm8bkp_Continue(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        BusinessRule storage br = inst.businessRules[BusinessRuleKey.Activity_0rm8bkp];
        require(br.exists, "business rule not set");
        require(br.state == ElementState.WAITING_FOR_CONFIRMATION, "business rule not waiting");
        require(br.requestId != bytes32(0), "business rule not requested");
        _checkBusinessRuleCaller(inst, br);

        IDmnLite dmnLite = IDmnLite(inst.dmnLiteAddress);
        (
            uint8 requestState,
            address requester,
            ,
            uint256 fulfilledAt,
            bool exists
        ) = dmnLite.getRequestStatus(br.requestId);
        require(exists, "dmn request missing");
        require(requester == address(this), "unexpected dmn requester");
        require(requestState == DMN_REQUEST_FULFILLED, "dmn result not ready");

        string memory raw = dmnLite.getRawByRequestId(br.requestId);
        br.lastRawResult = raw;
        br.fulfilledAt = fulfilledAt;
        inst.stateMemory.FinalPriority = _extractJsonString(raw, "finalPriority");
        br.state = ElementState.COMPLETED;
        inst.gateways[GatewayKey.Gateway_0ep8cuh].state = ElementState.ENABLED;


        emit BusinessRuleCompleted(instanceId, BusinessRuleKey.Activity_0rm8bkp, br.requestId);
    }
```

## Stage 5 原始模板展开

Geth：PIM numberOfUnits→NumberOfUnits → input_mappings[param_literal,slot_name,sol_type=int256] → mapping.param_literal / mapping.slot_name / mapping.sol_type → _jsonInt(inst.stateMemory.NumberOfUnits)。finalPriority→FinalPriority → output_mappings → _extractJsonString(raw,"finalPriority")。RuleFlow → rule_done_actions → business_rules[].done_actions → {{ rule.done_actions }} → Gateway_0ep8cuh ENABLED。

Fabric：RuleFlow → rule_done_actions → business_rules[].done_actions → {{ rule.done_actions }} → cc.ChangeGtwState(...,ENABLED)。输入输出是 runtime ParamMapping 的反射循环，没有 Geth 的逐字段映射占位符。

原始摘录：`src/newTranslator/CodeGenerator/b2cdsl-go/templates/contract.go.jinja:947`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```jinja
{% if business_rules %}
// Business rule handlers ----------------------------------------------------

{% for rule in business_rules %}
func (cc *SmartContract) {{ rule.name }}(ctx contractapi.TransactionContextInterface, instanceID string) error {


	instance, err := cc.GetInstance(ctx, instanceID)
	// Read Business Info
	businessRule, err := cc.ReadBusinessRule(ctx, instanceID, "{{ rule.name }}")
	if err != nil {
		return err
	}

	// Check the BusinessRule State
	if businessRule.State != ENABLED {
		return fmt.Errorf("The BusinessRule is not ENABLED")
	}

	// Get the CID

	res,err := cc.Invoke_Other_chaincode(ctx, "Oracle:v1", "default", oracle.EncodeGetDataItemArgs(
		instanceID, "{{ rule.name }}",
	))
	if err != nil {
		return  err
	}

	var dataItem *oracle.DataItem
	dataItem, err = oracle.DecodeGetDataItemResult(res)
	if err != nil {
		return  err
	}

	eventPayload := map[string]string{
		"ID":        "{{ rule.name }}",
		"InstanceID": instanceID,
		"Func":	   "{{ rule.name }}_Continue",
		"CID": dataItem.Value, 
	}

	eventPayloadAsBytes, err := json.Marshal(eventPayload)
	if err != nil {
		return fmt.Errorf("failed to marshal event payload: %v", err)
	}

	err = ctx.GetStub().SetEvent("DMNContentRequired", eventPayloadAsBytes)
	if err != nil {
		return fmt.Errorf("failed to set event: %v", err)
	}

	cc.ChangeBusinessRuleState(ctx, instance, "{{ rule.name }}", WAITINGFORCONFIRMATION)
	cc.SetInstance(ctx, instance)

	return nil
}

func (cc *SmartContract) {{ rule.name }}_Continue(ctx contractapi.TransactionContextInterface, instanceID string, ContentOfDmn string) error {
	// Read Business Info
	instance,err:=cc.GetInstance(ctx, instanceID)
	businessRule, err := cc.ReadBusinessRule(ctx, instanceID, "{{ rule.name }}")
	if err != nil {
		return err
	}

	// Check the BusinessRule State
	if businessRule.State != WAITINGFORCONFIRMATION {
		return fmt.Errorf("The BusinessRule is not Actived")
	}

	// check the hash
	hashString, _ := cc.hashXML(ctx, ContentOfDmn)
	if hashString != businessRule.Hash {
		return fmt.Errorf("The hash is not matched")
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
		field := reflect.ValueOf(globalVariable).Elem().FieldByName(strings.Title(value))
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
	_args[3] = []byte(businessRule.DecisionID)

	// Invoke DMN Engine Chaincode
	var resJson []byte
	resJson, err=cc.Invoke_Other_chaincode(ctx, "DMNEngine:v1","default", _args)

	// Set the Result
	var res map[string]interface{}
	err = json.Unmarshal(resJson, &res)
	if err != nil {
		return err
	}

	output := res["output"]
	fmt.Println("output: ", output)  
	if outputArr, ok := output.([]interface{}); ok {  
		for _, item := range outputArr {  
			itemMap := item.(map[string]interface{})  
			for key, value := range itemMap {  
				fmt.Printf("Key: %s, Type: %T, Value: %v\n", key,value,value)  
				globalName , _ := ParamMapping[key]
				field := reflect.ValueOf(globalVariable).Elem().FieldByName(strings.Title(globalName))
				if !field.IsValid() {
					return fmt.Errorf("The field %s is not valid", key)
				}
				switch field.Kind() {
					case reflect.Int:
						if valueFloat, ok := value.(float64); ok {
							field.SetInt(int64(valueFloat))
						} else {
							return fmt.Errorf("Unable to convert %v to int", value)
						}
					case reflect.String:
						if valueStr, ok := value.(string); ok {
							field.SetString(valueStr)
						} else {
							return fmt.Errorf("Unable to convert %v to string", value)
						}
					case reflect.Bool: // 处理布尔类型
						if valueBool, ok := value.(bool); ok {
							field.SetBool(valueBool)
						} else {
							return fmt.Errorf("Unable to convert %v to bool", value)
						}
					// 其他类型转换可以根据需求添加
					default:
						return fmt.Errorf("Unsupported field type: %s", field.Type())
                }
				// field.Set(reflect.ValueOf(value))
			}  
		}  
	}  

	// Update the GlobalVariable
	err = cc.SetGlobalVariable(ctx, instance, globalVariable)

	// Change the BusinessRule State
	cc.ChangeBusinessRuleState(ctx, instance, "{{ rule.name }}", COMPLETED)

{% if rule.done_actions %}
{{ rule.done_actions }}
{% endif %}

	cc.SetInstance(ctx, instance)
	eventPayload := map[string]string{
		"ID":         "{{ rule.name }}_Continue",
		"InstanceID": instanceID,
	}

	eventPayloadAsBytes, err := json.Marshal(eventPayload)
	if err != nil {
		return fmt.Errorf("failed to marshal event payload: %v", err)
	}

	err = ctx.GetStub().SetEvent("Avtivity_continueDone", eventPayloadAsBytes)
	if err != nil {
		return fmt.Errorf("failed to set event: %v", err)
	}
	return nil

}

{% endfor %}
```
原始摘录：`src/newTranslator/CodeGenerator/b2cdsl-solidity/templates/contract.sol.jinja:715`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```jinja
{% if business_rules %}
{% for rule in business_rules %}
    function {{ rule.enum_name }}(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        BusinessRule storage br = inst.businessRules[BusinessRuleKey.{{ rule.enum_name }}];
        require(br.exists, "business rule not set");
        require(br.state == ElementState.ENABLED, "business rule not enabled");
        _checkBusinessRuleCaller(inst, br);

        string memory inputBody = "";
        {% for mapping in rule.input_mappings %}
        inputBody = _jsonAppendField(
            inputBody,
            _jsonField(
                {{ mapping.param_literal }},
            {% if mapping.sol_type == 'int256' %}
            _jsonInt(inst.stateMemory.{{ mapping.slot_name }})
            {% elif mapping.sol_type == 'bool' %}
            _jsonBool(inst.stateMemory.{{ mapping.slot_name }})
            {% else %}
            _jsonString(inst.stateMemory.{{ mapping.slot_name }})
            {% endif %}
            )
        );
        {% endfor %}
        string memory inputData = _jsonObject(inputBody);
        IDmnLite dmnLite = IDmnLite(inst.dmnLiteAddress);
        require(bytes(br.dmnCid).length != 0, "dmn cid not set");
        bytes32 requestId = dmnLite.requestDMNDecision(
            inst.dmnEvalUrl,
            br.dmnCid,
            br.decisionId,
            inputData
        );
        require(requestId != bytes32(0), "dmn request failed");
        br.requestId = requestId;
        br.requestedAt = block.timestamp;
        br.fulfilledAt = 0;
        br.lastRawResult = "";
        br.state = ElementState.WAITING_FOR_CONFIRMATION;
        emit BusinessRuleRequested(instanceId, BusinessRuleKey.{{ rule.enum_name }}, requestId);
    }

    function {{ rule.enum_name }}_Continue(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        BusinessRule storage br = inst.businessRules[BusinessRuleKey.{{ rule.enum_name }}];
        require(br.exists, "business rule not set");
        require(br.state == ElementState.WAITING_FOR_CONFIRMATION, "business rule not waiting");
        require(br.requestId != bytes32(0), "business rule not requested");
        _checkBusinessRuleCaller(inst, br);

        IDmnLite dmnLite = IDmnLite(inst.dmnLiteAddress);
        (
            uint8 requestState,
            address requester,
            ,
            uint256 fulfilledAt,
            bool exists
        ) = dmnLite.getRequestStatus(br.requestId);
        require(exists, "dmn request missing");
        require(requester == address(this), "unexpected dmn requester");
        require(requestState == DMN_REQUEST_FULFILLED, "dmn result not ready");

        string memory raw = dmnLite.getRawByRequestId(br.requestId);
        br.lastRawResult = raw;
        br.fulfilledAt = fulfilledAt;
        {% for mapping in rule.output_mappings %}
        {% if mapping.sol_type == 'int256' %}
        inst.stateMemory.{{ mapping.slot_name }} = _extractJsonInt(raw, {{ mapping.param_literal }});
        {% elif mapping.sol_type == 'bool' %}
        inst.stateMemory.{{ mapping.slot_name }} = _extractJsonBool(raw, {{ mapping.param_literal }});
        {% else %}
        inst.stateMemory.{{ mapping.slot_name }} = _extractJsonString(raw, {{ mapping.param_literal }});
        {% endif %}
        {% endfor %}
        br.state = ElementState.COMPLETED;
{% if rule.done_actions %}
{{ rule.done_actions }}
{% endif %}

        emit BusinessRuleCompleted(instanceId, BusinessRuleKey.{{ rule.enum_name }}, br.requestId);
    }

{% endfor %}
{% endif %}

```
