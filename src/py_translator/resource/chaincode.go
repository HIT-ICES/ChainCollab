package main

import (
	"encoding/json"
	"errors"
	"fmt"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

type SmartContract struct {
	contractapi.Contract
}

type StateMemory struct {
	Is_available           bool `json:"Is_available"`
	Invoice                bool `json:"Invoice"`
	Need_external_provider bool `json:"Need_external_provider"`
}

type ContractInstance struct {
	// Incremental ID
	InstanceId string `json:"InstanceId"`
	// global Memory
	InstanceStateMemory StateMemory `json:"stateMemory"`
	// map type from string to Message、Gateway、ActionEvent
	InstanceElements map[string]interface{} `json:"InstanceElements"`
}

type ElementState int

const (
	DISABLED = iota
	ENABLED
	WAITINGFORCONFIRMATION
	COMPLETED
)

type Message struct {
	MessageID     string       `json:"messageID"`
	SendMspID     string       `json:"sendMspID"`
	ReceiveMspID  string       `json:"receiveMspID"`
	FireflyTranID string       `json:"fireflyTranID"`
	MsgState      ElementState `json:"msgState"`
	Format        string       `json:"format"`
}

type Gateway struct {
	GatewayID    string       `json:"gatewayID"`
	GatewayState ElementState `json:"gatewayState"`
}

type ActionEvent struct {
	EventID    string       `json:"eventID"`
	EventState ElementState `json:"eventState"`
}

func (cc *SmartContract) CreateMessage(ctx contractapi.TransactionContextInterface, instanceID string, messageID string, sendMspID string, receiveMspID string, fireflyTranID string, msgState ElementState, format string) (*Message, error) {
	stub := ctx.GetStub()

	existingData, err := stub.GetState(instanceID)
	if err != nil {
		return nil, fmt.Errorf("获取状态数据时出错: %v", err)
	}
	if existingData == nil {
		return nil, fmt.Errorf("实例 %s 不存在", instanceID)
	}

	// read from the existing instance
	var instance ContractInstance
	err = json.Unmarshal(existingData, &instance)
	if err != nil {
		return nil, fmt.Errorf("反序列化实例数据时出错: %v", err)
	}

	// 创建消息对象
	instance.InstanceElements[messageID] = &Message{
		MessageID:     messageID,
		SendMspID:     sendMspID,
		ReceiveMspID:  receiveMspID,
		FireflyTranID: fireflyTranID,
		MsgState:      msgState,
		Format:        format,
	}
	instanceJson, err := json.Marshal(instance)
	if err != nil {
		return nil, fmt.Errorf("序列化实例数据时出错: %v", err)
	}
	// 将消息对象序列化为JSON字符串并保存在状态数据库中
	err = stub.PutState(instanceID, instanceJson)
	if err != nil {
		return nil, fmt.Errorf("保存实例数据时出错: %v", err)
	}

	returnMessage, ok := instance.InstanceElements[messageID].(*Message)
	if !ok {
		return nil, fmt.Errorf("无法将实例元素转换为Message")
	}

	return returnMessage, nil
}

func (cc *SmartContract) CreateGateway(ctx contractapi.TransactionContextInterface, instanceID string, gatewayID string, gatewayState ElementState) (*Gateway, error) {
	stub := ctx.GetStub()

	// 检查是否存在具有相同ID的记录
	existingData, err := stub.GetState(instanceID)
	if err != nil {
		return nil, fmt.Errorf("获取状态数据时出错: %v", err)
	}
	if existingData == nil {
		return nil, fmt.Errorf("实例 %s 不存在", instanceID)
	}

	// 从现有实例中读取
	var instance ContractInstance
	err = json.Unmarshal(existingData, &instance)
	if err != nil {
		return nil, fmt.Errorf("反序列化实例数据时出错: %v", err)
	}

	// 创建网关对象
	instance.InstanceElements[gatewayID] = &Gateway{
		GatewayID:    gatewayID,
		GatewayState: gatewayState,
	}

	instanceJson, err := json.Marshal(instance)
	if err != nil {
		return nil, fmt.Errorf("序列化实例数据时出错: %v", err)
	}
	// 将网关对象序列化为JSON字符串并保存在状态数据库中
	err = stub.PutState(instanceID, instanceJson)
	if err != nil {
		return nil, fmt.Errorf("保存实例数据时出错: %v", err)
	}

	returnGateway, ok := instance.InstanceElements[gatewayID].(*Gateway)
	if !ok {
		return nil, fmt.Errorf("无法将实例元素转换为Gateway")
	}

	return returnGateway, nil
}

func (cc *SmartContract) CreateActionEvent(ctx contractapi.TransactionContextInterface, instanceID string, eventID string, eventState ElementState) (*ActionEvent, error) {
	stub := ctx.GetStub()

	// 检查是否存在具有相同ID的记录
	existingData, err := stub.GetState(instanceID)
	if err != nil {
		return nil, fmt.Errorf("获取状态数据时出错: %v", err)
	}
	if existingData == nil {
		return nil, fmt.Errorf("实例 %s 不存在", instanceID)
	}

	// 从现有实例中读取
	var instance ContractInstance
	err = json.Unmarshal(existingData, &instance)
	if err != nil {
		return nil, fmt.Errorf("反序列化实例数据时出错: %v", err)
	}

	// 创建事件对象
	instance.InstanceElements[eventID] = &ActionEvent{
		EventID:    eventID,
		EventState: eventState,
	}

	returnEvent, ok := instance.InstanceElements[eventID].(*ActionEvent)
	if !ok {
		return nil, fmt.Errorf("无法将实例元素转换为ActionEvent")
	}

	return returnEvent, nil

}

// Read function
func (c *SmartContract) ReadMsg(ctx contractapi.TransactionContextInterface, instanceID string, messageID string) (*Message, error) {
	instanceJson, err := ctx.GetStub().GetState(instanceID)
	if err != nil {
		return nil, err
	}
	if instanceJson == nil {
		errorMessage := fmt.Sprintf("Instance %s does not exist", instanceID)
		fmt.Println(errorMessage)
		return nil, errors.New(errorMessage)
	}

	var instance ContractInstance
	err = json.Unmarshal(instanceJson, &instance)
	if err != nil {
		fmt.Println(err.Error())
		return nil, err
	}

	msg, ok := instance.InstanceElements[messageID].(*Message)
	if !ok {
		errorMessage := fmt.Sprintf("Message %s does not exist", messageID)
		fmt.Println(errorMessage)
		return nil, errors.New(errorMessage)
	}

	return msg, nil
}

func (c *SmartContract) ReadGtw(ctx contractapi.TransactionContextInterface, instanceID string, gatewayID string) (*Gateway, error) {

	instanceJson, err := ctx.GetStub().GetState(instanceID)
	if err != nil {
		return nil, err
	}
	if instanceJson == nil {
		errorMessage := fmt.Sprintf("Instance %s does not exist", instanceID)
		fmt.Println(errorMessage)
		return nil, errors.New(errorMessage)
	}

	var instance ContractInstance
	err = json.Unmarshal(instanceJson, &instance)
	if err != nil {
		fmt.Println(err.Error())
		return nil, err
	}

	gtw, ok := instance.InstanceElements[gatewayID].(*Gateway)
	if !ok {
		errorMessage := fmt.Sprintf("Gateway %s does not exist", gatewayID)
		fmt.Println(errorMessage)
		return nil, errors.New(errorMessage)
	}

	return gtw, nil

}

func (c *SmartContract) ReadEvent(ctx contractapi.TransactionContextInterface, instanceID string, eventID string) (*ActionEvent, error) {

	instanceJson, err := ctx.GetStub().GetState(instanceID)
	if err != nil {
		return nil, err
	}
	if instanceJson == nil {
		errorMessage := fmt.Sprintf("Instance %s does not exist", instanceID)
		fmt.Println(errorMessage)
		return nil, errors.New(errorMessage)
	}

	var instance ContractInstance
	err = json.Unmarshal(instanceJson, &instance)
	if err != nil {
		fmt.Println(err.Error())
		return nil, err
	}

	actionEvent, ok := instance.InstanceElements[eventID].(*ActionEvent)
	if !ok {
		errorMessage := fmt.Sprintf("Event %s does not exist", eventID)
		fmt.Println(errorMessage)
		return nil, errors.New(errorMessage)
	}

	return actionEvent, nil

}

// Change State  function
func (c *SmartContract) ChangeMsgState(ctx contractapi.TransactionContextInterface, instanceID string, messageID string, msgState ElementState) error {

	stub := ctx.GetStub()

	instanceJson, err := stub.GetState(instanceID)
	if err != nil {
		return err
	}
	if instanceJson == nil {
		errorMessage := fmt.Sprintf("Instance %s does not exist", instanceID)
		fmt.Println(errorMessage)
		return errors.New(errorMessage)
	}

	var instance ContractInstance
	err = json.Unmarshal(instanceJson, &instance)
	if err != nil {
		fmt.Println(err.Error())
		return err
	}

	msg, ok := instance.InstanceElements[messageID].(*Message)
	if !ok {
		errorMessage := fmt.Sprintf("Message %s does not exist", messageID)
		fmt.Println(errorMessage)
		return errors.New(errorMessage)
	}

	msg.MsgState = msgState

	instanceJson, err = json.Marshal(instance)
	if err != nil {
		fmt.Println(err.Error())
		return err
	}

	err = stub.PutState(instanceID, instanceJson)
	if err != nil {
		fmt.Println(err.Error())
		return err
	}

	return nil

}

func (c *SmartContract) ChangeGtwState(ctx contractapi.TransactionContextInterface, instanceID string, gatewayID string, gtwState ElementState) error {

	stub := ctx.GetStub()

	instanceJson, err := stub.GetState(instanceID)
	if err != nil {
		return err
	}
	if instanceJson == nil {
		errorMessage := fmt.Sprintf("Instance %s does not exist", instanceID)
		fmt.Println(errorMessage)
		return errors.New(errorMessage)
	}

	var instance ContractInstance
	err = json.Unmarshal(instanceJson, &instance)
	if err != nil {
		fmt.Println(err.Error())
		return err
	}

	gtw, ok := instance.InstanceElements[gatewayID].(*Gateway)
	if !ok {
		errorMessage := fmt.Sprintf("Gateway %s does not exist", gatewayID)
		fmt.Println(errorMessage)
		return errors.New(errorMessage)
	}

	gtw.GatewayState = gtwState

	instanceJson, err = json.Marshal(instance)
	if err != nil {
		fmt.Println(err.Error())
		return err
	}

	err = stub.PutState(instanceID, instanceJson)
	if err != nil {
		fmt.Println(err.Error())
		return err
	}

	return nil

}

func (c *SmartContract) ChangeEventState(ctx contractapi.TransactionContextInterface, instanceID string, eventID string, eventState ElementState) error {

	stub := ctx.GetStub()

	instanceJson, err := stub.GetState(instanceID)
	if err != nil {
		return err
	}
	if instanceJson == nil {
		errorMessage := fmt.Sprintf("Instance %s does not exist", instanceID)
		fmt.Println(errorMessage)
		return errors.New(errorMessage)
	}

	var instance ContractInstance
	err = json.Unmarshal(instanceJson, &instance)
	if err != nil {
		fmt.Println(err.Error())
		return err
	}

	actionEvent, ok := instance.InstanceElements[eventID].(*ActionEvent)
	if !ok {
		errorMessage := fmt.Sprintf("Event %s does not exist", eventID)
		fmt.Println(errorMessage)
		return errors.New(errorMessage)
	}

	actionEvent.EventState = eventState

	instanceJson, err = json.Marshal(instance)
	if err != nil {
		fmt.Println(err.Error())
		return err
	}

	err = stub.PutState(instanceID, instanceJson)
	if err != nil {
		fmt.Println(err.Error())
		return err
	}

	return nil

}

//get all message

func (cc *SmartContract) GetAllMessages(ctx contractapi.TransactionContextInterface, instanceID string) ([]*Message, error) {
	instanceJson, err := ctx.GetStub().GetState(instanceID)
	if err != nil {
		return nil, err
	}
	if instanceJson == nil {
		errorMessage := fmt.Sprintf("Instance %s does not exist", instanceID)
		fmt.Println(errorMessage)
		return nil, errors.New(errorMessage)
	}

	var instance ContractInstance
	err = json.Unmarshal(instanceJson, &instance)
	if err != nil {
		fmt.Println(err.Error())
		return nil, err
	}

	var messages []*Message
	for _, element := range instance.InstanceElements {
		msg, ok := element.(*Message)
		if ok {
			messages = append(messages, msg)
		}
	}

	return messages, nil
}

func (cc *SmartContract) GetAllGateways(ctx contractapi.TransactionContextInterface, instanceID string) ([]*Gateway, error) {

	instanceJson, err := ctx.GetStub().GetState(instanceID)
	if err != nil {
		return nil, err
	}
	if instanceJson == nil {
		errorMessage := fmt.Sprintf("Instance %s does not exist", instanceID)
		fmt.Println(errorMessage)
		return nil, errors.New(errorMessage)
	}

	var instance ContractInstance
	err = json.Unmarshal(instanceJson, &instance)
	if err != nil {
		fmt.Println(err.Error())
		return nil, err
	}

	var gateways []*Gateway
	for _, element := range instance.InstanceElements {
		gtw, ok := element.(*Gateway)
		if ok {
			gateways = append(gateways, gtw)
		}
	}

	return gateways, nil
}

func (cc *SmartContract) GetAllActionEvents(ctx contractapi.TransactionContextInterface, instanceID string) ([]*ActionEvent, error) {

	instanceJson, err := ctx.GetStub().GetState(instanceID)
	if err != nil {
		return nil, err
	}
	if instanceJson == nil {
		errorMessage := fmt.Sprintf("Instance %s does not exist", instanceID)
		fmt.Println(errorMessage)
		return nil, errors.New(errorMessage)
	}

	var instance ContractInstance
	err = json.Unmarshal(instanceJson, &instance)
	if err != nil {
		fmt.Println(err.Error())
		return nil, err
	}

	var actionEvents []*ActionEvent
	for _, element := range instance.InstanceElements {
		event, ok := element.(*ActionEvent)
		if ok {
			actionEvents = append(actionEvents, event)
		}
	}

	return actionEvents, nil

}

func (cc *SmartContract) ReadGlobalVariable(ctx contractapi.TransactionContextInterface, instanceID string) (*StateMemory, error) {

	instanceJson, err := ctx.GetStub().GetState(instanceID)
	if err != nil {
		return nil, err
	}
	if instanceJson == nil {
		errorMessage := fmt.Sprintf("Instance %s does not exist", instanceID)
		fmt.Println(errorMessage)
		return nil, errors.New(errorMessage)
	}

	var instance ContractInstance
	err = json.Unmarshal(instanceJson, &instance)
	if err != nil {
		fmt.Println(err.Error())
		return nil, err
	}

	return &instance.InstanceStateMemory, nil

}

func (cc *SmartContract) SetGlobalVariable(ctx contractapi.TransactionContextInterface, instanceID string, globalVariable *StateMemory) error {

	stub := ctx.GetStub()

	instanceJson, err := stub.GetState(instanceID)
	if err != nil {
		return err
	}
	if instanceJson == nil {
		errorMessage := fmt.Sprintf("Instance %s does not exist", instanceID)
		fmt.Println(errorMessage)
		return errors.New(errorMessage)
	}

	var instance ContractInstance
	err = json.Unmarshal(instanceJson, &instance)
	if err != nil {
		fmt.Println(err.Error())
		return err
	}

	instance.InstanceStateMemory = *globalVariable

	instanceJson, err = json.Marshal(instance)
	if err != nil {
		fmt.Println(err.Error())
		return err
	}

	err = stub.PutState(instanceID, instanceJson)
	if err != nil {
		fmt.Println(err.Error())
		return err
	}

	return nil

}

func (cc *SmartContract) InitLedger(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()

	// isInited in state
	isInitedBytes, err := stub.GetState("isInited")
	if err != nil {
		return fmt.Errorf("Failed to get isInited: %v", err)
	}
	if isInitedBytes != nil {
		errorMessage := "Chaincode has already been initialized"
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	stub.PutState("currentInstanceId", []byte("0"))

	stub.PutState("isInited", []byte("true"))

	stub.SetEvent("initContractEvent", []byte("Contract has been initialized successfully"))
	return nil
}

func (cc *SmartContract) Event_1jtgn3j(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	actionEvent, err := cc.ReadEvent(ctx, "Event_1jtgn3j")
	if err != nil {
		return err
	}

	if actionEvent.EventState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", actionEvent.EventID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgState(ctx, instanceID, "Event_1jtgn3j", COMPLETED)
	stub.SetEvent("Event_1jtgn3j", []byte("Contract has been started successfully"))

	cc.ChangeGtwState(ctx, instanceID, "ExclusiveGateway_0hs3ztq", ENABLED)

	return nil
}

func (cc *SmartContract) Message_045i10y_Send(ctx contractapi.TransactionContextInterface, fireflyTranID string) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_045i10y")
	if err != nil {
		return err
	}

	if cc.check_participant(ctx, msg.SendParticipantID) == false {
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	msg.MsgState = WAITINGFORCONFIRMATION
	msg.FireflyTranID = fireflyTranID
	msgJSON, _ := json.Marshal(msg)
	stub.PutState("Message_045i10y", msgJSON)

	stub.SetEvent("Message_045i10y", []byte("Message is waiting for confirmation"))

	return nil
}

func (cc *SmartContract) Message_045i10y_Complete(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_045i10y")
	if err != nil {
		return err
	}

	if cc.check_participant(ctx, msg.ReceiveParticipantID) == false {
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != WAITINGFORCONFIRMATION {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgState(ctx, "Message_045i10y", COMPLETED)
	stub.SetEvent("Message_045i10y", []byte("Message has been done"))

	cc.ChangeMsgState(ctx, instanceID, "Message_0r9lypd", ENABLED)

	return nil
}

func (cc *SmartContract) Message_0r9lypd_Send(ctx contractapi.TransactionContextInterface, fireflyTranID string, Is_available bool) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_0r9lypd")
	if err != nil {
		return err
	}

	if cc.check_participant(ctx, msg.SendParticipantID) == false {
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	msg.MsgState = WAITINGFORCONFIRMATION
	msg.FireflyTranID = fireflyTranID
	msgJSON, _ := json.Marshal(msg)
	stub.PutState("Message_0r9lypd", msgJSON)
	globalMemory, readGloabolError := cc.ReadGlobalVariable(ctx)
	if readGloabolError != nil {
		fmt.Println(readGloabolError.Error())
		return readGloabolError
	}
	globalMemory.Is_available = Is_available
	setGloabolErrror := cc.SetGlobalVariable(ctx, globalMemory)
	if setGloabolErrror != nil {
		fmt.Println(setGloabolErrror.Error())
		return setGloabolErrror
	}
	stub.SetEvent("Message_0r9lypd", []byte("Message is waiting for confirmation"))

	return nil
}

func (cc *SmartContract) Message_0r9lypd_Complete(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_0r9lypd")
	if err != nil {
		return err
	}

	if cc.check_participant(ctx, msg.ReceiveParticipantID) == false {
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != WAITINGFORCONFIRMATION {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgState(ctx, "Message_0r9lypd", COMPLETED)
	stub.SetEvent("Message_0r9lypd", []byte("Message has been done"))

	cc.ChangeGtwState(ctx, instanceID, "ExclusiveGateway_106je4z", ENABLED)

	return nil
}

func (cc *SmartContract) ExclusiveGateway_106je4z(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	gtw, err := cc.ReadGtw(ctx, "ExclusiveGateway_106je4z")
	if err != nil {
		return err
	}

	if gtw.GatewayState != ENABLED {
		errorMessage := fmt.Sprintf("Gateway state %s is not allowed", gtw.GatewayID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeGtwState(ctx, "ExclusiveGateway_106je4z", COMPLETED)
	stub.SetEvent("ExclusiveGateway_106je4z", []byte("ExclusiveGateway has been done"))

	currentMemory, err := cc.ReadGlobalVariable(ctx)
	if err != nil {
		return err
	}

	Is_available := currentMemory.Is_available

	if Is_available == true {
		cc.ChangeMsgState(ctx, instanceID, "Message_1em0ee4", ENABLED)
	}
	if Is_available == false {
		cc.ChangeGtwState(ctx, instanceID, "ExclusiveGateway_0hs3ztq", ENABLED)
	}

	return nil
}

func (cc *SmartContract) Message_1em0ee4_Send(ctx contractapi.TransactionContextInterface, fireflyTranID string, Need_external_provider bool) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1em0ee4")
	if err != nil {
		return err
	}

	if cc.check_participant(ctx, msg.SendParticipantID) == false {
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	msg.MsgState = WAITINGFORCONFIRMATION
	msg.FireflyTranID = fireflyTranID
	msgJSON, _ := json.Marshal(msg)
	stub.PutState("Message_1em0ee4", msgJSON)
	globalMemory, readGloabolError := cc.ReadGlobalVariable(ctx)
	if readGloabolError != nil {
		fmt.Println(readGloabolError.Error())
		return readGloabolError
	}
	globalMemory.Need_external_provider = Need_external_provider
	setGloabolErrror := cc.SetGlobalVariable(ctx, globalMemory)
	if setGloabolErrror != nil {
		fmt.Println(setGloabolErrror.Error())
		return setGloabolErrror
	}
	stub.SetEvent("Message_1em0ee4", []byte("Message is waiting for confirmation"))

	return nil
}

func (cc *SmartContract) Message_1em0ee4_Complete(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1em0ee4")
	if err != nil {
		return err
	}

	if cc.check_participant(ctx, msg.ReceiveParticipantID) == false {
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != WAITINGFORCONFIRMATION {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgState(ctx, "Message_1em0ee4", COMPLETED)
	stub.SetEvent("Message_1em0ee4", []byte("Message has been done"))

	cc.ChangeMsgState(ctx, instanceID, "Message_1nlagx2", ENABLED)

	return nil
}

func (cc *SmartContract) Message_1nlagx2_Send(ctx contractapi.TransactionContextInterface, fireflyTranID string) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1nlagx2")
	if err != nil {
		return err
	}

	if cc.check_participant(ctx, msg.SendParticipantID) == false {
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	msg.MsgState = WAITINGFORCONFIRMATION
	msg.FireflyTranID = fireflyTranID
	msgJSON, _ := json.Marshal(msg)
	stub.PutState("Message_1nlagx2", msgJSON)

	stub.SetEvent("Message_1nlagx2", []byte("Message is waiting for confirmation"))

	return nil
}

func (cc *SmartContract) Message_1nlagx2_Complete(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1nlagx2")
	if err != nil {
		return err
	}

	if cc.check_participant(ctx, msg.ReceiveParticipantID) == false {
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != WAITINGFORCONFIRMATION {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgState(ctx, "Message_1nlagx2", COMPLETED)
	stub.SetEvent("Message_1nlagx2", []byte("Message has been done"))

	cc.ChangeGtwState(ctx, instanceID, "EventBasedGateway_1fxpmyn", ENABLED)

	return nil
}

func (cc *SmartContract) ExclusiveGateway_0hs3ztq(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	gtw, err := cc.ReadGtw(ctx, "ExclusiveGateway_0hs3ztq")
	if err != nil {
		return err
	}

	if gtw.GatewayState != ENABLED {
		errorMessage := fmt.Sprintf("Gateway state %s is not allowed", gtw.GatewayID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeGtwState(ctx, "ExclusiveGateway_0hs3ztq", COMPLETED)
	stub.SetEvent("ExclusiveGateway_0hs3ztq", []byte("ExclusiveGateway has been done"))

	cc.ChangeMsgState(ctx, instanceID, "Message_045i10y", ENABLED)

	return nil
}

func (cc *SmartContract) EventBasedGateway_1fxpmyn(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	gtw, err := cc.ReadGtw(ctx, "EventBasedGateway_1fxpmyn")
	if err != nil {
		return err
	}

	if gtw.GatewayState != ENABLED {
		errorMessage := fmt.Sprintf("Gateway state %s is not allowed", gtw.GatewayID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeGtwState(ctx, "EventBasedGateway_1fxpmyn", COMPLETED)
	stub.SetEvent("EventBasedGateway_1fxpmyn", []byte("EventbasedGateway has been done"))

	cc.ChangeMsgState(ctx, instanceID, "Message_0o8eyir", ENABLED)
	cc.ChangeMsgState(ctx, instanceID, "Message_1xm9dxy", ENABLED)

	return nil
}

func (cc *SmartContract) Message_0o8eyir_Send(ctx contractapi.TransactionContextInterface, fireflyTranID string) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_0o8eyir")
	if err != nil {
		return err
	}

	if cc.check_participant(ctx, msg.SendParticipantID) == false {
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	msg.MsgState = WAITINGFORCONFIRMATION
	msg.FireflyTranID = fireflyTranID
	msgJSON, _ := json.Marshal(msg)
	stub.PutState("Message_0o8eyir", msgJSON)

	stub.SetEvent("Message_0o8eyir", []byte("Message is waiting for confirmation"))

	cc.ChangeMsgState(ctx, instanceID, "Message_1xm9dxy", DISABLED)
	return nil
}

func (cc *SmartContract) Message_0o8eyir_Complete(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_0o8eyir")
	if err != nil {
		return err
	}

	if cc.check_participant(ctx, msg.ReceiveParticipantID) == false {
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != WAITINGFORCONFIRMATION {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgState(ctx, "Message_0o8eyir", COMPLETED)
	stub.SetEvent("Message_0o8eyir", []byte("Message has been done"))

	cc.ChangeGtwState(ctx, instanceID, "Gateway_1bhtapl", ENABLED)

	return nil
}

func (cc *SmartContract) Message_1xm9dxy_Send(ctx contractapi.TransactionContextInterface, fireflyTranID string) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1xm9dxy")
	if err != nil {
		return err
	}

	if cc.check_participant(ctx, msg.SendParticipantID) == false {
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	msg.MsgState = WAITINGFORCONFIRMATION
	msg.FireflyTranID = fireflyTranID
	msgJSON, _ := json.Marshal(msg)
	stub.PutState("Message_1xm9dxy", msgJSON)

	stub.SetEvent("Message_1xm9dxy", []byte("Message is waiting for confirmation"))

	cc.ChangeMsgState(ctx, instanceID, "Message_0o8eyir", DISABLED)
	return nil
}

func (cc *SmartContract) Message_1xm9dxy_Complete(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1xm9dxy")
	if err != nil {
		return err
	}

	if cc.check_participant(ctx, msg.ReceiveParticipantID) == false {
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != WAITINGFORCONFIRMATION {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgState(ctx, "Message_1xm9dxy", COMPLETED)
	stub.SetEvent("Message_1xm9dxy", []byte("Message has been done"))

	cc.ChangeEventState(ctx, instanceID, "Event_0366pfz", ENABLED)

	return nil
}

func (cc *SmartContract) Event_0366pfz(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	event, err := cc.ReadEvent(ctx, "Event_0366pfz")
	if err != nil {
		return err
	}

	if event.EventState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", event.EventID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeEventState(ctx, "Event_0366pfz", COMPLETED)
	stub.SetEvent("Event_0366pfz", []byte("EndEvent has been done"))

	return nil
}

func (cc *SmartContract) Message_1ljlm4g_Send(ctx contractapi.TransactionContextInterface, fireflyTranID string) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1ljlm4g")
	if err != nil {
		return err
	}

	if cc.check_participant(ctx, msg.SendParticipantID) == false {
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	msg.MsgState = WAITINGFORCONFIRMATION
	msg.FireflyTranID = fireflyTranID
	msgJSON, _ := json.Marshal(msg)
	stub.PutState("Message_1ljlm4g", msgJSON)

	stub.SetEvent("Message_1ljlm4g", []byte("Message is waiting for confirmation"))

	return nil
}

func (cc *SmartContract) Message_1ljlm4g_Complete(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1ljlm4g")
	if err != nil {
		return err
	}

	if cc.check_participant(ctx, msg.ReceiveParticipantID) == false {
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != WAITINGFORCONFIRMATION {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgState(ctx, "Message_1ljlm4g", COMPLETED)
	stub.SetEvent("Message_1ljlm4g", []byte("Message has been done"))

	cc.ChangeMsgState(ctx, instanceID, "Message_0m9p3da", ENABLED)

	return nil
}

func (cc *SmartContract) Message_0m9p3da_Send(ctx contractapi.TransactionContextInterface, fireflyTranID string, Invoice bool) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_0m9p3da")
	if err != nil {
		return err
	}

	if cc.check_participant(ctx, msg.SendParticipantID) == false {
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	msg.MsgState = WAITINGFORCONFIRMATION
	msg.FireflyTranID = fireflyTranID
	msgJSON, _ := json.Marshal(msg)
	stub.PutState("Message_0m9p3da", msgJSON)
	globalMemory, readGloabolError := cc.ReadGlobalVariable(ctx)
	if readGloabolError != nil {
		fmt.Println(readGloabolError.Error())
		return readGloabolError
	}
	globalMemory.Invoice = Invoice
	setGloabolErrror := cc.SetGlobalVariable(ctx, globalMemory)
	if setGloabolErrror != nil {
		fmt.Println(setGloabolErrror.Error())
		return setGloabolErrror
	}
	stub.SetEvent("Message_0m9p3da", []byte("Message is waiting for confirmation"))

	return nil
}

func (cc *SmartContract) Message_0m9p3da_Complete(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_0m9p3da")
	if err != nil {
		return err
	}

	if cc.check_participant(ctx, msg.ReceiveParticipantID) == false {
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != WAITINGFORCONFIRMATION {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgState(ctx, "Message_0m9p3da", COMPLETED)
	stub.SetEvent("Message_0m9p3da", []byte("Message has been done"))

	cc.ChangeGtwState(ctx, instanceID, "ExclusiveGateway_0nzwv7v", ENABLED)

	return nil
}

func (cc *SmartContract) ExclusiveGateway_0nzwv7v(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	gtw, err := cc.ReadGtw(ctx, "ExclusiveGateway_0nzwv7v")
	if err != nil {
		return err
	}

	if gtw.GatewayState != ENABLED {
		errorMessage := fmt.Sprintf("Gateway state %s is not allowed", gtw.GatewayID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeGtwState(ctx, "ExclusiveGateway_0nzwv7v", COMPLETED)
	stub.SetEvent("ExclusiveGateway_0nzwv7v", []byte("ExclusiveGateway has been done"))

	currentMemory, err := cc.ReadGlobalVariable(ctx)
	if err != nil {
		return err
	}

	Invoice := currentMemory.Invoice

	if Invoice == false {
		cc.ChangeEventState(ctx, instanceID, "Event_08edp7f", ENABLED)
	}
	if Invoice == true {
		cc.ChangeMsgState(ctx, instanceID, "Message_1joj7ca", ENABLED)
	}

	return nil
}

func (cc *SmartContract) Event_08edp7f(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	event, err := cc.ReadEvent(ctx, "Event_08edp7f")
	if err != nil {
		return err
	}

	if event.EventState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", event.EventID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeEventState(ctx, "Event_08edp7f", COMPLETED)
	stub.SetEvent("Event_08edp7f", []byte("EndEvent has been done"))

	return nil
}

func (cc *SmartContract) Message_1joj7ca_Send(ctx contractapi.TransactionContextInterface, fireflyTranID string) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1joj7ca")
	if err != nil {
		return err
	}

	if cc.check_participant(ctx, msg.SendParticipantID) == false {
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	msg.MsgState = WAITINGFORCONFIRMATION
	msg.FireflyTranID = fireflyTranID
	msgJSON, _ := json.Marshal(msg)
	stub.PutState("Message_1joj7ca", msgJSON)

	stub.SetEvent("Message_1joj7ca", []byte("Message is waiting for confirmation"))

	return nil
}

func (cc *SmartContract) Message_1joj7ca_Complete(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1joj7ca")
	if err != nil {
		return err
	}

	if cc.check_participant(ctx, msg.ReceiveParticipantID) == false {
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != WAITINGFORCONFIRMATION {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgState(ctx, "Message_1joj7ca", COMPLETED)
	stub.SetEvent("Message_1joj7ca", []byte("Message has been done"))

	cc.ChangeMsgState(ctx, instanceID, "Message_1etcmvl", ENABLED)

	return nil
}

func (cc *SmartContract) Message_1etcmvl_Send(ctx contractapi.TransactionContextInterface, fireflyTranID string) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1etcmvl")
	if err != nil {
		return err
	}

	if cc.check_participant(ctx, msg.SendParticipantID) == false {
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	msg.MsgState = WAITINGFORCONFIRMATION
	msg.FireflyTranID = fireflyTranID
	msgJSON, _ := json.Marshal(msg)
	stub.PutState("Message_1etcmvl", msgJSON)

	stub.SetEvent("Message_1etcmvl", []byte("Message is waiting for confirmation"))

	return nil
}

func (cc *SmartContract) Message_1etcmvl_Complete(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1etcmvl")
	if err != nil {
		return err
	}

	if cc.check_participant(ctx, msg.ReceiveParticipantID) == false {
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != WAITINGFORCONFIRMATION {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgState(ctx, "Message_1etcmvl", COMPLETED)
	stub.SetEvent("Message_1etcmvl", []byte("Message has been done"))

	cc.ChangeEventState(ctx, instanceID, "Event_146eii4", ENABLED)

	return nil
}

func (cc *SmartContract) Event_146eii4(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	event, err := cc.ReadEvent(ctx, "Event_146eii4")
	if err != nil {
		return err
	}

	if event.EventState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", event.EventID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeEventState(ctx, "Event_146eii4", COMPLETED)
	stub.SetEvent("Event_146eii4", []byte("EndEvent has been done"))

	return nil
}

func (cc *SmartContract) Message_1i8rlqn_Send(ctx contractapi.TransactionContextInterface, fireflyTranID string) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1i8rlqn")
	if err != nil {
		return err
	}

	if cc.check_participant(ctx, msg.SendParticipantID) == false {
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	msg.MsgState = WAITINGFORCONFIRMATION
	msg.FireflyTranID = fireflyTranID
	msgJSON, _ := json.Marshal(msg)
	stub.PutState("Message_1i8rlqn", msgJSON)

	stub.SetEvent("Message_1i8rlqn", []byte("Message is waiting for confirmation"))

	return nil
}

func (cc *SmartContract) Message_1i8rlqn_Complete(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1i8rlqn")
	if err != nil {
		return err
	}

	if cc.check_participant(ctx, msg.ReceiveParticipantID) == false {
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != WAITINGFORCONFIRMATION {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgState(ctx, "Message_1i8rlqn", COMPLETED)
	stub.SetEvent("Message_1i8rlqn", []byte("Message has been done"))

	cc.ChangeMsgState(ctx, instanceID, "Message_1q05nnw", ENABLED)

	return nil
}

func (cc *SmartContract) Gateway_1bhtapl(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	gtw, err := cc.ReadGtw(ctx, "Gateway_1bhtapl")
	if err != nil {
		return err
	}

	if gtw.GatewayState != ENABLED {
		errorMessage := fmt.Sprintf("Gateway state %s is not allowed", gtw.GatewayID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeGtwState(ctx, "Gateway_1bhtapl", COMPLETED)
	stub.SetEvent("Gateway_1bhtapl", []byte("ExclusiveGateway has been done"))

	currentMemory, err := cc.ReadGlobalVariable(ctx)
	if err != nil {
		return err
	}

	Need_external_provider := currentMemory.Need_external_provider

	if Need_external_provider == true {
		cc.ChangeMsgState(ctx, instanceID, "Message_1i8rlqn", ENABLED)
	}
	if Need_external_provider == false {
		cc.ChangeGtwState(ctx, instanceID, "Gateway_04h9e6e", ENABLED)
	}

	return nil
}

func (cc *SmartContract) Gateway_04h9e6e(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	gtw, err := cc.ReadGtw(ctx, "Gateway_04h9e6e")
	if err != nil {
		return err
	}

	if gtw.GatewayState != ENABLED {
		errorMessage := fmt.Sprintf("Gateway state %s is not allowed", gtw.GatewayID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeGtwState(ctx, "Gateway_04h9e6e", COMPLETED)
	stub.SetEvent("Gateway_04h9e6e", []byte("ExclusiveGateway has been done"))

	cc.ChangeMsgState(ctx, instanceID, "Message_1ljlm4g", ENABLED)

	return nil
}

func (cc *SmartContract) Message_1q05nnw_Send(ctx contractapi.TransactionContextInterface, fireflyTranID string) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1q05nnw")
	if err != nil {
		return err
	}

	if cc.check_participant(ctx, msg.SendParticipantID) == false {
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	msg.MsgState = WAITINGFORCONFIRMATION
	msg.FireflyTranID = fireflyTranID
	msgJSON, _ := json.Marshal(msg)
	stub.PutState("Message_1q05nnw", msgJSON)

	stub.SetEvent("Message_1q05nnw", []byte("Message is waiting for confirmation"))

	return nil
}

func (cc *SmartContract) Message_1q05nnw_Complete(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1q05nnw")
	if err != nil {
		return err
	}

	if cc.check_participant(ctx, msg.ReceiveParticipantID) == false {
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != WAITINGFORCONFIRMATION {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgState(ctx, "Message_1q05nnw", COMPLETED)
	stub.SetEvent("Message_1q05nnw", []byte("Message has been done"))

	cc.ChangeMsgState(ctx, instanceID, "Message_1qbk325", ENABLED)

	return nil
}

func (cc *SmartContract) Message_1qbk325_Send(ctx contractapi.TransactionContextInterface, fireflyTranID string) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1qbk325")
	if err != nil {
		return err
	}

	if cc.check_participant(ctx, msg.SendParticipantID) == false {
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	msg.MsgState = WAITINGFORCONFIRMATION
	msg.FireflyTranID = fireflyTranID
	msgJSON, _ := json.Marshal(msg)
	stub.PutState("Message_1qbk325", msgJSON)

	stub.SetEvent("Message_1qbk325", []byte("Message is waiting for confirmation"))

	return nil
}

func (cc *SmartContract) Message_1qbk325_Complete(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1qbk325")
	if err != nil {
		return err
	}

	if cc.check_participant(ctx, msg.ReceiveParticipantID) == false {
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != WAITINGFORCONFIRMATION {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgState(ctx, "Message_1qbk325", COMPLETED)
	stub.SetEvent("Message_1qbk325", []byte("Message has been done"))

	cc.ChangeGtwState(ctx, instanceID, "Gateway_04h9e6e", ENABLED)

	return nil
}
