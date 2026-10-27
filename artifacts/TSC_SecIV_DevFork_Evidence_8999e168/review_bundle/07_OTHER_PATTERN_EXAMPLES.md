基准：dev-MultiBlockChain-fork，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`；日期 2026-10-27（Asia/Shanghai）。生成成功不代表部署或 DMN 执行成功。

本例具备全部模式。以下代码块为原始摘录，保留源定位。PIM 摘录是相关行索引；完整声明/flow 见 03。

## Participant and message

XML 摘录（继承根命名空间 xmlns:bpmn2="http://www.omg.org/spec/BPMN/20100524/MODEL"；xmlns:abc="https://chaincollab.io/schema/abc"）：`Experiment/BPMNwithDMNcase/new/SupplyChainPaper.bpmn:89` (`id="Message_1wswgqu"`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

```xml
<bpmn2:message id="Message_1wswgqu" name="Goods Order Request">
    <bpmn2:extensionElements>
      <abc:MessageSchema>
        <abc:Property name="orderDetails" type="string" description="Detailed list of goods ordered" required="true" definition="{&quot;type&quot;:&quot;string&quot;,&quot;description&quot;:&quot;Detailed list of goods ordered&quot;}" />
      </abc:MessageSchema>
    </bpmn2:extensionElements>
  </bpmn2:message>
```
XML 摘录（继承根命名空间 xmlns:bpmn2="http://www.omg.org/spec/BPMN/20100524/MODEL"；xmlns:abc="https://chaincollab.io/schema/abc"）：`Experiment/BPMNwithDMNcase/new/SupplyChainPaper.bpmn:97` (`id="Participant_0w6qkdf"`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

```xml
<bpmn2:participant id="Participant_0w6qkdf" name="Bulk buyer" />
```
PIM 原始行摘录（含行号）：

```text
133:         message Message_1wswgqu from Participant_0w6qkdf to Participant_19mgbdn {
205:         start event Event_06sexe6 enables Message_1wswgqu;
207:         when message Message_1wswgqu completed
```
原始摘录：`artifacts/TSC_SecIV_DevFork_Evidence_8999e168/generated_fabric/SupplyChainPaper.go:2007`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```go
func (cc *SmartContract) Message_1wswgqu_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string, orderDetails string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1wswgqu")
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
	cc.ChangeMsgState(ctx, instance, "Message_1wswgqu", WAITINGFORCONFIRMATION)

globalMemory,readGloabolError := cc.ReadGlobalVariable(ctx, instanceID)
	if readGloabolError != nil {
		fmt.Println(readGloabolError.Error())
		return readGloabolError
	}
	globalMemory.OrderDetails = orderDetails
	setGloabolErrror := cc.SetGlobalVariable(ctx, instance, globalMemory)
	if setGloabolErrror != nil {
		fmt.Println(setGloabolErrror.Error())
		return setGloabolErrror
	}

	stub.SetEvent("Message_1wswgqu", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	cc.SetInstance(ctx, instance)
	return nil
}
```
没有生成 Message_1wswgqu_Send 函数。
原始摘录：`artifacts/TSC_SecIV_DevFork_Evidence_8999e168/generated_fabric/SupplyChainPaper.go:2049`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```go
func (cc *SmartContract) Message_1wswgqu_Complete(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1wswgqu")
	if err != nil {
		return err
	}

	if cc.check_participant(ctx, instanceID, msg.ReceiveParticipantID) == false {
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != WAITINGFORCONFIRMATION {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgState(ctx, instance, msg.MessageID, COMPLETED)
	stub.SetEvent("Message_1wswgqu", []byte("Message has been done"))
	cc.SetInstance(ctx, instance)
	cc.ChangeMsgState(ctx, instance, "Message_1ajdm9l", ENABLED)

	cc.SetInstance(ctx, instance)
	return nil
}
```
`src/newTranslator/CodeGenerator/b2cdsl-go/b2cdsl_go/__init__.py:211` (`def _render_messages`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

`src/newTranslator/CodeGenerator/b2cdsl-solidity/b2cdsl_solidity/__init__.py:454` (`def _render_messages`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

## Schema and globals

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
PIM 原始行摘录（含行号）：

```text
70:         NumberOfUnits: int
105:         message Message_0rwz1km from Participant_19j1e3o to Participant_0sa2v7d {
181:                 numberOfUnits -> NumberOfUnits
215:         when message Message_0rwz1km completed
252:         then enable Message_0rwz1km;
```
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
原始摘录：`artifacts/TSC_SecIV_DevFork_Evidence_8999e168/generated_fabric/SupplyChainPaper.go:1576`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```go
func (cc *SmartContract) Message_0rwz1km_Complete(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_0rwz1km")
	if err != nil {
		return err
	}

	if cc.check_participant(ctx, instanceID, msg.ReceiveParticipantID) == false {
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != WAITINGFORCONFIRMATION {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgState(ctx, instance, msg.MessageID, COMPLETED)
	stub.SetEvent("Message_0rwz1km", []byte("Message has been done"))
	cc.SetInstance(ctx, instance)
	cc.ChangeMsgState(ctx, instance, "Message_0hpha6h", ENABLED)

	cc.SetInstance(ctx, instance)
	return nil
}
```
`src/newTranslator/CodeGenerator/b2cdsl-go/b2cdsl_go/__init__.py:211` (`def _render_messages`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

`src/newTranslator/CodeGenerator/b2cdsl-solidity/b2cdsl_solidity/__init__.py:454` (`def _render_messages`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

## Start and sequence

XML 摘录（继承根命名空间 xmlns:bpmn2="http://www.omg.org/spec/BPMN/20100524/MODEL"；xmlns:abc="https://chaincollab.io/schema/abc"）：`Experiment/BPMNwithDMNcase/new/SupplyChainPaper.bpmn:115` (`id="Event_06sexe6"`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

```xml
<bpmn2:startEvent id="Event_06sexe6">
      <bpmn2:outgoing>Flow_1btgvf6</bpmn2:outgoing>
    </bpmn2:startEvent>
```
PIM 原始行摘录（含行号）：

```text
165:         event Event_06sexe6 {
205:         start event Event_06sexe6 enables Message_1wswgqu;
```
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
`src/newTranslator/CodeGenerator/b2cdsl-go/b2cdsl_go/__init__.py:197` (`def _render_start_events`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

`src/newTranslator/CodeGenerator/b2cdsl-solidity/b2cdsl_solidity/__init__.py:437` (`def _render_start_events`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

## Exclusive

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
PIM 原始行摘录（含行号）：

```text
147:         gateway Gateway_0ep8cuh {
236:         when gateway Gateway_0ep8cuh completed
255:         then enable Gateway_0ep8cuh;
```
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
`src/newTranslator/CodeGenerator/b2cdsl-go/b2cdsl_go/__init__.py:279` (`def _render_gateways`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

`src/newTranslator/CodeGenerator/b2cdsl-solidity/b2cdsl_solidity/__init__.py:550` (`def _render_gateways`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

## Parallel split

XML 摘录（继承根命名空间 xmlns:bpmn2="http://www.omg.org/spec/BPMN/20100524/MODEL"；xmlns:abc="https://chaincollab.io/schema/abc"）：`Experiment/BPMNwithDMNcase/new/SupplyChainPaper.bpmn:134` (`id="Gateway_0onpe6x"`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

```xml
<bpmn2:parallelGateway id="Gateway_0onpe6x">
      <bpmn2:incoming>Flow_0by1ery</bpmn2:incoming>
      <bpmn2:outgoing>Flow_0fs2i4x</bpmn2:outgoing>
      <bpmn2:outgoing>Flow_1wyrozo</bpmn2:outgoing>
    </bpmn2:parallelGateway>
```
PIM 原始行摘录（含行号）：

```text
151:         gateway Gateway_0onpe6x {
210:         then enable Gateway_0onpe6x;
248:         when gateway Gateway_0onpe6x completed
```
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
`src/newTranslator/CodeGenerator/b2cdsl-go/b2cdsl_go/__init__.py:279` (`def _render_gateways`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

`src/newTranslator/CodeGenerator/b2cdsl-solidity/b2cdsl_solidity/__init__.py:550` (`def _render_gateways`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

## Parallel join

XML 摘录（继承根命名空间 xmlns:bpmn2="http://www.omg.org/spec/BPMN/20100524/MODEL"；xmlns:abc="https://chaincollab.io/schema/abc"）：`Experiment/BPMNwithDMNcase/new/SupplyChainPaper.bpmn:156` (`id="Gateway_1fbifca"`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

```xml
<bpmn2:parallelGateway id="Gateway_1fbifca">
      <bpmn2:incoming>Flow_1azhglw</bpmn2:incoming>
      <bpmn2:incoming>Flow_1tvz6lc</bpmn2:incoming>
      <bpmn2:outgoing>Flow_0gtd6v3</bpmn2:outgoing>
    </bpmn2:parallelGateway>
```
PIM 原始行摘录（含行号）：

```text
155:         gateway Gateway_1fbifca {
212:         then enable Gateway_1fbifca;
214:         then enable Gateway_1fbifca;
251:         parallel gateway Gateway_1fbifca await Message_0cba4t6, Message_0pm90nx
```
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
`src/newTranslator/CodeGenerator/b2cdsl-go/b2cdsl_go/__init__.py:279` (`def _render_gateways`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

`src/newTranslator/CodeGenerator/b2cdsl-solidity/b2cdsl_solidity/__init__.py:550` (`def _render_gateways`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)
