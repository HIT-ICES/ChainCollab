基准：dev-MultiBlockChain-fork，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`；日期 2026-10-27（Asia/Shanghai）。生成成功不代表部署或 DMN 执行成功。

九项均在当前 SupplyChainPaper 中实际存在。源码位置、commit、生成单元见 CSV；完整函数摘录见下文及 06/07。

| Category | Item | CIM | PIM | Fabric | Geth |
|---|---|---|---|---|---|
| Structure & Data | S1 Participant and identity binding | Participant_0w6qkdf (L97) | participant Participant_0w6qkdf (L4) | Participant/InitParameters/CreateInstance | ParticipantInit/_createParticipant |
| Structure & Data | S2 Message interface | Message_0rwz1km (L59) | message Message_0rwz1km (L105) | Message_0rwz1km_Send / Message_0rwz1km_Complete | Message_0rwz1km_Send |
| Structure & Data | S3 Shared data | Message_0rwz1km (L59) | NumberOfUnits: int (L70) | StateMemory.NumberOfUnits / Send assignment | StateMemory.NumberOfUnits / Send assignment |
| Business Rules | B1 BusinessRuleTask interface and request | Activity_0rm8bkp (L212) | businessrule Activity_0rm8bkp (L177) | Activity_0rm8bkp | Activity_0rm8bkp |
| Business Rules | B2 BusinessRuleTask completion and continuation | Activity_0rm8bkp (L212) | when businessrule Activity_0rm8bkp done (L254) | Activity_0rm8bkp_Continue | Activity_0rm8bkp_Continue |
| Events & Sequencing | E1 Events and sequence relations | Event_06sexe6 (L115) | start event Event_06sexe6 enables Message_1wswgqu (L205) | Event_06sexe6 / Message_1wswgqu_Complete / Event_13pbqdz | Event_06sexe6 / Message_1wswgqu_Send / Event_13pbqdz |
| Gateways | G1 Exclusive split | Gateway_0ep8cuh (L263) | when gateway Gateway_0ep8cuh completed (L236) | Gateway_0ep8cuh | Gateway_0ep8cuh |
| Gateways | G2 Parallel split | Gateway_0onpe6x (L134) | when gateway Gateway_0onpe6x completed (L248) | Gateway_0onpe6x | Gateway_0onpe6x |
| Gateways | G3 Parallel join | Gateway_1fbifca (L156) | parallel gateway Gateway_1fbifca await (L251) | Gateway_1fbifca | Gateway_1fbifca |

S1/S3 对应结构与初始化；B1/B2 对应两个函数；E1 顺序关系包含嵌入动作；G1/G2/G3 复用 handler 加分支/并行代码。

## S1 Participant and identity binding

XML 摘录（继承根命名空间 xmlns:bpmn2="http://www.omg.org/spec/BPMN/20100524/MODEL"；xmlns:abc="https://chaincollab.io/schema/abc"）：`Experiment/BPMNwithDMNcase/new/SupplyChainPaper.bpmn:97` (`id="Participant_0w6qkdf"`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

```xml
<bpmn2:participant id="Participant_0w6qkdf" name="Bulk buyer" />
```
`src/newTranslator/generator/translator.py:551` (`def _build_participants_section`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

`src/newTranslator/CodeGenerator/b2cdsl-go/b2cdsl_go/__init__.py:650` (`def _create_instance_payload`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

`src/newTranslator/CodeGenerator/b2cdsl-solidity/b2cdsl_solidity/__init__.py:212` (`def _participant_payload`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

原始摘录：`src/newTranslator/CodeGenerator/b2cdsl-go/b2cdsl_go/__init__.py:650`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```python
    def _create_instance_payload(self) -> dict:
        start_event = self.adapter.start_event_id or "StartEvent"
        end_events = self.adapter.end_event_ids
        return {
            "start_event": start_event,
            "end_events": end_events,
            "oracle_tasks": [task.name for task in self.adapter.oracle_tasks],
            "messages": [
                {
                    "name": message.name,
                    "sender": message.sender.name,
                    "receiver": message.receiver.name,
                    "properties": json.dumps({"schema": getattr(message, "schema", "") or ""}),
                }
                for message in self.adapter.messages
            ],
            "gateways": [gateway.name for gateway in self.adapter.gateways],
            "participants": [
                {
                    "id": participant.name,
                    "field_name": public_the_name(participant.name),
                    "multi_maximum": getattr(participant, "multiMax", 0) or 0,
                    "multi_minimum": getattr(participant, "multiMin", 0) or 0,
                }
                for participant in self.adapter.participants
            ],
            "business_rules": [
                {
                    "name": rule.name,
                    "field_name": public_the_name(rule.name),
                }
                for rule in self.adapter.business_rules
            ],
        }
```
原始摘录：`src/newTranslator/CodeGenerator/b2cdsl-solidity/b2cdsl_solidity/__init__.py:212`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```python
    def _participant_payload(self) -> List[dict]:
        payload: List[dict] = []
        for participant in self.adapter.participants:
            enum_name = sanitize_identifier(participant.name)
            payload.append(
                {
                    "name": participant.name,
                    "enum_name": enum_name,
                    "param_name": f"{enum_name}_account",
                    "org_param": f"{enum_name}_org",
                    "is_multi": "true" if getattr(participant, "isMulti", False) else "false",
                    "multi_maximum": getattr(participant, "multiMax", 0) or 0,
                    "multi_minimum": getattr(participant, "multiMin", 0) or 0,
                }
            )
        return payload
```

## S2 Message interface

XML 摘录（继承根命名空间 xmlns:bpmn2="http://www.omg.org/spec/BPMN/20100524/MODEL"；xmlns:abc="https://chaincollab.io/schema/abc"）：`Experiment/BPMNwithDMNcase/new/SupplyChainPaper.bpmn:59` (`id="Message_0rwz1km"`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

```xml
<bpmn2:message id="Message_0rwz1km" name="Request Details">
    <bpmn2:extensionElements>
      <abc:MessageSchema>
        <abc:Property name="requestId" type="number" description=" Unique identifier of the request for additional details " required="true" definition="{&quot;type&quot;:&quot;number&quot;,&quot;description&quot;:&quot; Unique identifier of the request for additional details &quot;}" />
        <abc:Property name="numberOfUnits" type="number" description=" Total number of units in the order requested" required="true" definition="{&quot;type&quot;:&quot;number&quot;,&quot;description&quot;:&quot; Total number of units in the order requested&quot;}" />
        <abc:Property name="urgent" type="boolean" description="Indicates whether the order requires urgent delivery." required="true" definition="{&quot;type&quot;:&quot;boolean&quot;,&quot;description&quot;:&quot;Indicates whether the order requires urgent delivery.&quot;}" />
      </abc:MessageSchema>
    </bpmn2:extensionElements>
  </bpmn2:message>
```
`src/newTranslator/generator/translator.py:586` (`def _build_messages_section`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

`src/newTranslator/CodeGenerator/b2cdsl-go/b2cdsl_go/__init__.py:211` (`def _render_messages`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

`src/newTranslator/CodeGenerator/b2cdsl-solidity/b2cdsl_solidity/__init__.py:454` (`def _render_messages`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

原始摘录：`artifacts/TSC_SecIV_DevFork_Evidence_8999e168/generated_fabric/SupplyChainPaper.go:1532`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```go
func (cc *SmartContract) Message_0rwz1km_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string, numberOfUnits int, requestId int, urgent bool) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_0rwz1km")
	if err != nil {
		return err
	}

	//
	if cc.check_participant(ctx, instanceID, msg.SendParticipantID) == false {
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != ENABLED {
		errorMessage := fmt.Sprintf("Message state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgFireflyTranID(ctx, instance, fireflyTranID, msg.MessageID)
	cc.ChangeMsgState(ctx, instance, "Message_0rwz1km", WAITINGFORCONFIRMATION)

globalMemory,readGloabolError := cc.ReadGlobalVariable(ctx, instanceID)
	if readGloabolError != nil {
		fmt.Println(readGloabolError.Error())
		return readGloabolError
	}
	globalMemory.NumberOfUnits = numberOfUnits
	globalMemory.RequestId = requestId
	globalMemory.Urgent = urgent
	setGloabolErrror := cc.SetGlobalVariable(ctx, instance, globalMemory)
	if setGloabolErrror != nil {
		fmt.Println(setGloabolErrror.Error())
		return setGloabolErrror
	}

	stub.SetEvent("Message_0rwz1km", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	cc.SetInstance(ctx, instance)
	return nil
}
```
没有生成 Message_0rwz1km_Send 函数。

## S3 Shared data

XML 摘录（继承根命名空间 xmlns:bpmn2="http://www.omg.org/spec/BPMN/20100524/MODEL"；xmlns:abc="https://chaincollab.io/schema/abc"）：`Experiment/BPMNwithDMNcase/new/SupplyChainPaper.bpmn:59` (`id="Message_0rwz1km"`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

```xml
<bpmn2:message id="Message_0rwz1km" name="Request Details">
    <bpmn2:extensionElements>
      <abc:MessageSchema>
        <abc:Property name="requestId" type="number" description=" Unique identifier of the request for additional details " required="true" definition="{&quot;type&quot;:&quot;number&quot;,&quot;description&quot;:&quot; Unique identifier of the request for additional details &quot;}" />
        <abc:Property name="numberOfUnits" type="number" description=" Total number of units in the order requested" required="true" definition="{&quot;type&quot;:&quot;number&quot;,&quot;description&quot;:&quot; Total number of units in the order requested&quot;}" />
        <abc:Property name="urgent" type="boolean" description="Indicates whether the order requires urgent delivery." required="true" definition="{&quot;type&quot;:&quot;boolean&quot;,&quot;description&quot;:&quot;Indicates whether the order requires urgent delivery.&quot;}" />
      </abc:MessageSchema>
    </bpmn2:extensionElements>
  </bpmn2:message>
```
`src/newTranslator/generator/translator.py:573` (`def _build_globals_section`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

`src/newTranslator/CodeGenerator/b2cdsl-go/b2cdsl_go/__init__.py:626` (`def _state_memory_fields`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

`src/newTranslator/CodeGenerator/b2cdsl-solidity/b2cdsl_solidity/__init__.py:255` (`def _global_variables`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

原始摘录：`src/newTranslator/CodeGenerator/b2cdsl-go/b2cdsl_go/__init__.py:626`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```python
    def _state_memory_fields(self) -> List[dict]:
        return [
            {
                "name": public_the_name(global_var.name),
                "type": B2C_TO_GO_TYPE.get(global_var.type, "string"),
            }
            for global_var in self.adapter.globals
        ]
```
原始摘录：`src/newTranslator/CodeGenerator/b2cdsl-solidity/b2cdsl_solidity/__init__.py:255`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```python
    def _global_variables(self) -> List[dict]:
        return [
            {
                "name": sanitize_identifier(public_the_name(global_var.name)),
                "type": SOLIDITY_TYPE.get(global_var.type, "string"),
            }
            for global_var in self.adapter.globals
        ]
```

## B1 BusinessRuleTask interface and request

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
`src/newTranslator/generator/translator.py:645` (`def _build_business_rules_section`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

`src/newTranslator/CodeGenerator/b2cdsl-go/b2cdsl_go/__init__.py:685` (`def _business_rule_payload`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

`src/newTranslator/CodeGenerator/b2cdsl-solidity/b2cdsl_solidity/__init__.py:304` (`def _business_rule_payload`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

模板与生成函数原始摘录见 06。

## B2 BusinessRuleTask completion and continuation

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
`src/newTranslator/generator/translator.py:323` (`def _business_rule_flows`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

`src/newTranslator/CodeGenerator/b2cdsl-go/b2cdsl_go/__init__.py:150` (`def rule_done_actions`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

`src/newTranslator/CodeGenerator/b2cdsl-solidity/b2cdsl_solidity/__init__.py:390` (`def rule_done_actions`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

模板与生成函数原始摘录见 06。

## E1 Events and sequence relations

XML 摘录（继承根命名空间 xmlns:bpmn2="http://www.omg.org/spec/BPMN/20100524/MODEL"；xmlns:abc="https://chaincollab.io/schema/abc"）：`Experiment/BPMNwithDMNcase/new/SupplyChainPaper.bpmn:115` (`id="Event_06sexe6"`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

```xml
<bpmn2:startEvent id="Event_06sexe6">
      <bpmn2:outgoing>Flow_1btgvf6</bpmn2:outgoing>
    </bpmn2:startEvent>
```
`src/newTranslator/generator/translator.py:258` (`def _start_event_flows`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

`src/newTranslator/CodeGenerator/b2cdsl-go/b2cdsl_go/__init__.py:197` (`def _render_start_events`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

`src/newTranslator/CodeGenerator/b2cdsl-solidity/b2cdsl_solidity/__init__.py:437` (`def _render_start_events`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

原始摘录：`artifacts/TSC_SecIV_DevFork_Evidence_8999e168/generated_fabric/SupplyChainPaper.go:1152`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```go
func (cc *SmartContract) Event_06sexe6(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)

	actionEvent, err := cc.ReadEvent(ctx, instanceID, "Event_06sexe6")
	if err != nil {
		return err
	}

	if actionEvent.EventState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", actionEvent.EventID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeEventState(ctx, instance, "Event_06sexe6", COMPLETED)
	stub.SetEvent("Event_06sexe6", []byte("Contract has been started successfully"))
	cc.SetInstance(ctx, instance)
	cc.ChangeMsgState(ctx, instance, "Message_1wswgqu", ENABLED)

	cc.SetInstance(ctx, instance)
	return nil
}
```
没有生成 Event_06sexe6 函数。

## G1 Exclusive split

XML 摘录（继承根命名空间 xmlns:bpmn2="http://www.omg.org/spec/BPMN/20100524/MODEL"；xmlns:abc="https://chaincollab.io/schema/abc"）：`Experiment/BPMNwithDMNcase/new/SupplyChainPaper.bpmn:263` (`id="Gateway_0ep8cuh"`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

```xml
<bpmn2:exclusiveGateway id="Gateway_0ep8cuh">
      <bpmn2:incoming>Flow_1jxt9fr</bpmn2:incoming>
      <bpmn2:outgoing>Flow_0bna2ku</bpmn2:outgoing>
      <bpmn2:outgoing>Flow_0r6rayf</bpmn2:outgoing>
      <bpmn2:outgoing>Flow_1ihncup</bpmn2:outgoing>
      <bpmn2:outgoing>Flow_0005j8y</bpmn2:outgoing>
    </bpmn2:exclusiveGateway>
```
`src/newTranslator/generator/translator.py:292` (`def _gateway_flows`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

`src/newTranslator/CodeGenerator/b2cdsl-go/b2cdsl_go/__init__.py:279` (`def _render_gateways`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

`src/newTranslator/CodeGenerator/b2cdsl-solidity/b2cdsl_solidity/__init__.py:550` (`def _render_gateways`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

原始摘录：`artifacts/TSC_SecIV_DevFork_Evidence_8999e168/generated_fabric/SupplyChainPaper.go:2103`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```go
func (cc *SmartContract) Gateway_0ep8cuh(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	gtw, err := cc.ReadGtw(ctx, instanceID, "Gateway_0ep8cuh")
	if err != nil {
		return err
	}

	if gtw.GatewayState != ENABLED {
		errorMessage := fmt.Sprintf("Gateway state %s is not allowed", gtw.GatewayID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}


	cc.ChangeGtwState(ctx, instance, gtw.GatewayID, COMPLETED)
	stub.SetEvent("Gateway_0ep8cuh", []byte("Gateway has been completed"))
	cc.SetInstance(ctx, instance)
	if instance.InstanceStateMemory.FinalPriority == "Low" {
		cc.ChangeMsgState(ctx, instance, "Message_1oxmq1k", ENABLED)
	} else if instance.InstanceStateMemory.FinalPriority == "High" {
		cc.ChangeMsgState(ctx, instance, "Message_1dmeexg", ENABLED)
	} else if instance.InstanceStateMemory.FinalPriority == "Medium" {
		cc.ChangeMsgState(ctx, instance, "Message_1dzkcn0", ENABLED)
	} else if instance.InstanceStateMemory.FinalPriority == "VeryLow" {
		cc.ChangeMsgState(ctx, instance, "Message_0d2xte5", ENABLED)
	}

	cc.SetInstance(ctx, instance)

	return nil
}
```
没有生成 Gateway_0ep8cuh 函数。

## G2 Parallel split

XML 摘录（继承根命名空间 xmlns:bpmn2="http://www.omg.org/spec/BPMN/20100524/MODEL"；xmlns:abc="https://chaincollab.io/schema/abc"）：`Experiment/BPMNwithDMNcase/new/SupplyChainPaper.bpmn:134` (`id="Gateway_0onpe6x"`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

```xml
<bpmn2:parallelGateway id="Gateway_0onpe6x">
      <bpmn2:incoming>Flow_0by1ery</bpmn2:incoming>
      <bpmn2:outgoing>Flow_0fs2i4x</bpmn2:outgoing>
      <bpmn2:outgoing>Flow_1wyrozo</bpmn2:outgoing>
    </bpmn2:parallelGateway>
```
`src/newTranslator/generator/translator.py:292` (`def _gateway_flows`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

`src/newTranslator/CodeGenerator/b2cdsl-go/b2cdsl_go/__init__.py:279` (`def _render_gateways`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

`src/newTranslator/CodeGenerator/b2cdsl-solidity/b2cdsl_solidity/__init__.py:550` (`def _render_gateways`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

原始摘录：`artifacts/TSC_SecIV_DevFork_Evidence_8999e168/generated_fabric/SupplyChainPaper.go:2136`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```go
func (cc *SmartContract) Gateway_0onpe6x(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	gtw, err := cc.ReadGtw(ctx, instanceID, "Gateway_0onpe6x")
	if err != nil {
		return err
	}

	if gtw.GatewayState != ENABLED {
		errorMessage := fmt.Sprintf("Gateway state %s is not allowed", gtw.GatewayID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}


	cc.ChangeGtwState(ctx, instance, gtw.GatewayID, COMPLETED)
	stub.SetEvent("Gateway_0onpe6x", []byte("Gateway has been completed"))
	cc.SetInstance(ctx, instance)
	cc.ChangeMsgState(ctx, instance, "Message_0cba4t6", ENABLED)
	cc.ChangeMsgState(ctx, instance, "Message_0pm90nx", ENABLED)

	cc.SetInstance(ctx, instance)

	return nil
}
```
没有生成 Gateway_0onpe6x 函数。

## G3 Parallel join

XML 摘录（继承根命名空间 xmlns:bpmn2="http://www.omg.org/spec/BPMN/20100524/MODEL"；xmlns:abc="https://chaincollab.io/schema/abc"）：`Experiment/BPMNwithDMNcase/new/SupplyChainPaper.bpmn:156` (`id="Gateway_1fbifca"`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

```xml
<bpmn2:parallelGateway id="Gateway_1fbifca">
      <bpmn2:incoming>Flow_1azhglw</bpmn2:incoming>
      <bpmn2:incoming>Flow_1tvz6lc</bpmn2:incoming>
      <bpmn2:outgoing>Flow_0gtd6v3</bpmn2:outgoing>
    </bpmn2:parallelGateway>
```
`src/newTranslator/generator/translator.py:356` (`def _parallel_join_flows`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

`src/newTranslator/CodeGenerator/b2cdsl-go/b2cdsl_go/__init__.py:458` (`def _parallel_guard_block`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

`src/newTranslator/CodeGenerator/b2cdsl-solidity/b2cdsl_solidity/__init__.py:822` (`def _parallel_guard_block`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

原始摘录：`artifacts/TSC_SecIV_DevFork_Evidence_8999e168/generated_fabric/SupplyChainPaper.go:2162`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```go
func (cc *SmartContract) Gateway_1fbifca(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	gtw, err := cc.ReadGtw(ctx, instanceID, "Gateway_1fbifca")
	if err != nil {
		return err
	}

	if gtw.GatewayState != ENABLED {
		errorMessage := fmt.Sprintf("Gateway state %s is not allowed", gtw.GatewayID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if !(instance.InstanceMessages["Message_0cba4t6"].MsgState == COMPLETED && instance.InstanceMessages["Message_0pm90nx"].MsgState == COMPLETED) {
		return fmt.Errorf("Parallel gateway prerequisite not met")
	}


	cc.ChangeGtwState(ctx, instance, gtw.GatewayID, COMPLETED)
	stub.SetEvent("Gateway_1fbifca", []byte("Gateway has been completed"))
	cc.SetInstance(ctx, instance)
	cc.ChangeMsgState(ctx, instance, "Message_0rwz1km", ENABLED)

	cc.SetInstance(ctx, instance)

	return nil
}
```
没有生成 Gateway_1fbifca 函数。
