package chaincode

import (
	"encoding/json"
	"errors"
	"fmt"
	"strings"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

// SmartContract provides functions for managing an Asset
type SmartContract struct {
	contractapi.Contract
}

type ElementState int

const (
	DISABLE = iota
	ENABLE
	WAITFORCONFIRM
	DONE
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

type StateMemory struct {
}

func (cc *SmartContract) CreateMessage(ctx contractapi.TransactionContextInterface, messageID string, sendMspID string, receiveMspID string, fireflyTranID string, msgState ElementState, format string) (*Message, error) {
	stub := ctx.GetStub()

	// 检查是否存在具有相同ID的记录
	existingData, err := stub.GetState(messageID)
	if err != nil {
		return nil, fmt.Errorf("获取状态数据时出错: %v", err)
	}
	if existingData != nil {
		return nil, fmt.Errorf("消息 %s 已存在", messageID)
	}

	// 创建消息对象
	msg := &Message{
		MessageID:     messageID,
		SendMspID:     sendMspID,
		ReceiveMspID:  receiveMspID,
		FireflyTranID: fireflyTranID,
		MsgState:      msgState,
		Format:        format,
	}

	// 将消息对象序列化为JSON字符串并保存在状态数据库中
	msgJSON, err := json.Marshal(msg)
	if err != nil {
		return nil, fmt.Errorf("序列化消息数据时出错: %v", err)
	}
	err = stub.PutState(messageID, msgJSON)
	if err != nil {
		return nil, fmt.Errorf("保存消息数据时出错: %v", err)
	}

	return msg, nil
}

func (cc *SmartContract) CreateGateway(ctx contractapi.TransactionContextInterface, gatewayID string, gatewayState ElementState) (*Gateway, error) {
	stub := ctx.GetStub()

	// 检查是否存在具有相同ID的记录
	existingData, err := stub.GetState(gatewayID)
	if err != nil {
		return nil, fmt.Errorf("获取状态数据时出错: %v", err)
	}
	if existingData != nil {
		return nil, fmt.Errorf("网关 %s 已存在", gatewayID)
	}

	// 创建网关对象
	gtw := &Gateway{
		GatewayID:    gatewayID,
		GatewayState: gatewayState,
	}

	// 将网关对象序列化为JSON字符串并保存在状态数据库中
	gtwJSON, err := json.Marshal(gtw)
	if err != nil {
		return nil, fmt.Errorf("序列化网关数据时出错: %v", err)
	}
	err = stub.PutState(gatewayID, gtwJSON)
	if err != nil {
		return nil, fmt.Errorf("保存网关数据时出错: %v", err)
	}

	return gtw, nil
}

func (cc *SmartContract) CreateActionEvent(ctx contractapi.TransactionContextInterface, eventID string, eventState ElementState) (*ActionEvent, error) {
	stub := ctx.GetStub()

	// 创建ActionEvent对象
	actionEvent := &ActionEvent{
		EventID:    eventID,
		EventState: eventState,
	}

	// 将ActionEvent对象序列化为JSON字符串并保存在状态数据库中
	actionEventJSON, err := json.Marshal(actionEvent)
	if err != nil {
		return nil, fmt.Errorf("序列化事件数据时出错: %v", err)
	}
	err = stub.PutState(eventID, actionEventJSON)
	if err != nil {
		return nil, fmt.Errorf("保存事件数据时出错: %v", err)
	}

	return actionEvent, nil
}

func (s *SmartContract) InitStateMemory(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	currentMemory := StateMemory{
		NeedExternalProvider: false,
		Invoice:              false,
		IsAvailable:          false,
	}
	memoryJSON, err := json.Marshal(currentMemory)
	if err != nil {
		return fmt.Errorf("failed to marshal memory state: %s", err)
	}
	err = stub.PutState("currentMemory", memoryJSON)
	if err != nil {
		return fmt.Errorf("failed to save memory state: %s", err)
	}
	// 这里你可以添加将stateMemory保存到区块链状态数据库的代码
	return nil
}

// Read function
func (c *SmartContract) ReadMsg(ctx contractapi.TransactionContextInterface, messageID string) (*Message, error) {
	msgJSON, err := ctx.GetStub().GetState(messageID)
	if err != nil {
		fmt.Println(err.Error())
		return nil, err
	}

	if msgJSON == nil {
		errorMessage := fmt.Sprintf("Message %s does not exist", messageID)
		fmt.Println(errorMessage)
		return nil, errors.New(errorMessage)
	}

	var msg Message
	err = json.Unmarshal(msgJSON, &msg)
	if err != nil {
		fmt.Println(err.Error())
		return nil, err
	}

	return &msg, nil
}

func (c *SmartContract) ReadGtw(ctx contractapi.TransactionContextInterface, gatewayID string) (*Gateway, error) {
	gtwJSON, err := ctx.GetStub().GetState(gatewayID)
	if err != nil {
		fmt.Println(err.Error())
		return nil, err
	}

	if gtwJSON == nil {
		errorMessage := fmt.Sprintf("Gateway %s does not exist", gatewayID)
		fmt.Println(errorMessage)
		return nil, errors.New(errorMessage)
	}

	var gtw Gateway
	err = json.Unmarshal(gtwJSON, &gtw)
	if err != nil {
		fmt.Println(err.Error())
		return nil, err
	}

	return &gtw, nil
}

func (c *SmartContract) ReadEvent(ctx contractapi.TransactionContextInterface, eventID string) (*ActionEvent, error) {
	eventJSON, err := ctx.GetStub().GetState(eventID)
	if err != nil {
		fmt.Println(err.Error())
		return nil, err
	}

	if eventJSON == nil {
		errorMessage := fmt.Sprintf("Event state %s does not exist", eventID)
		fmt.Println(errorMessage)
		return nil, errors.New(errorMessage)
	}

	var event ActionEvent
	err = json.Unmarshal(eventJSON, &event)
	if err != nil {
		fmt.Println(err.Error())
		return nil, err
	}

	return &event, nil
}

func (c *SmartContract) ReadMemory(ctx contractapi.TransactionContextInterface) (*StateMemory, error) {
	memoryJSON, err := ctx.GetStub().GetState("currentMemory")
	if err != nil {
		return nil, fmt.Errorf("failed to read memory from world state: %v", err)
	}

	if memoryJSON == nil {
		return nil, fmt.Errorf("memory state not found")
	}

	var memory StateMemory
	err = json.Unmarshal(memoryJSON, &memory)
	if err != nil {
		return nil, err
	}

	return &memory, nil
}

// Change State  function
func (c *SmartContract) ChangeMsgState(ctx contractapi.TransactionContextInterface, messageID string, msgState ElementState) error {
	stub := ctx.GetStub()

	msg, err := c.ReadMsg(ctx, messageID)
	if err != nil {
		return err
	}

	msg.MsgState = msgState

	msgJSON, err := json.Marshal(msg)
	if err != nil {
		fmt.Println(err.Error())
		return err
	}

	err = stub.PutState(messageID, msgJSON)
	if err != nil {
		fmt.Println(err.Error())
		return err
	}

	return nil
}

func (c *SmartContract) ChangeGtwState(ctx contractapi.TransactionContextInterface, gatewayID string, gtwState ElementState) error {
	stub := ctx.GetStub()

	gtw, err := c.ReadGtw(ctx, gatewayID)
	if err != nil {
		return err
	}

	gtw.GatewayState = gtwState

	gtwJSON, err := json.Marshal(gtw)
	if err != nil {
		fmt.Println(err.Error())
		return err
	}

	err = stub.PutState(gatewayID, gtwJSON)
	if err != nil {
		fmt.Println(err.Error())
		return err
	}

	return nil
}

func (c *SmartContract) ChangeEventState(ctx contractapi.TransactionContextInterface, eventID string, eventState ElementState) error {
	stub := ctx.GetStub()

	actionEvent, err := c.ReadEvent(ctx, eventID)
	if err != nil {
		return err
	}

	actionEvent.EventState = eventState

	actionEventJSON, err := json.Marshal(actionEvent)
	if err != nil {
		fmt.Println(err.Error())
		return err
	}

	err = stub.PutState(eventID, actionEventJSON)
	if err != nil {
		fmt.Println(err.Error())
		return err
	}

	return nil
}

//get all message

func (cc *SmartContract) GetAllMessages(ctx contractapi.TransactionContextInterface) ([]*Message, error) {
	resultsIterator, err := ctx.GetStub().GetStateByRange("", "")
	if err != nil {
		return nil, fmt.Errorf("获取状态数据时出错: %v", err) //直接err也行
	}
	defer resultsIterator.Close()

	var messages []*Message
	for resultsIterator.HasNext() {
		queryResponse, err := resultsIterator.Next()
		if err != nil {
			return nil, fmt.Errorf("迭代状态数据时出错: %v", err)
		}

		var message Message
		err = json.Unmarshal(queryResponse.Value, &message)
		if strings.HasPrefix(message.MessageID, "Message") {
			if err != nil {
				return nil, fmt.Errorf("反序列化消息数据时出错: %v", err)
			}

			messages = append(messages, &message)
		}
	}

	return messages, nil
}

func (cc *SmartContract) GetAllGateways(ctx contractapi.TransactionContextInterface) ([]*Gateway, error) {
	resultsIterator, err := ctx.GetStub().GetStateByRange("", "")
	if err != nil {
		return nil, fmt.Errorf("获取状态数据时出错: %v", err)
	}
	defer resultsIterator.Close()

	var gateways []*Gateway
	for resultsIterator.HasNext() {
		queryResponse, err := resultsIterator.Next()
		if err != nil {
			return nil, fmt.Errorf("迭代状态数据时出错: %v", err)
		}

		var gateway Gateway
		err = json.Unmarshal(queryResponse.Value, &gateway)
		if strings.HasPrefix(gateway.GatewayID, "ExclusiveGateway") ||
			strings.HasPrefix(gateway.GatewayID, "EventBasedGateway") ||
			strings.HasPrefix(gateway.GatewayID, "Gateway") ||
			strings.HasPrefix(gateway.GatewayID, "ParallelGateway") {
			if err != nil {
				return nil, fmt.Errorf("反序列化网关数据时出错: %v", err)
			}

			gateways = append(gateways, &gateway)
		}
	}

	return gateways, nil
}

func (cc *SmartContract) GetAllActionEvents(ctx contractapi.TransactionContextInterface) ([]*ActionEvent, error) {
	resultsIterator, err := ctx.GetStub().GetStateByRange("", "")
	if err != nil {
		return nil, fmt.Errorf("获取状态数据时出错: %v", err)
	}
	defer resultsIterator.Close()

	var events []*ActionEvent
	for resultsIterator.HasNext() {
		queryResponse, err := resultsIterator.Next()
		if err != nil {
			return nil, fmt.Errorf("迭代状态数据时出错: %v", err)
		}

		var event ActionEvent
		err = json.Unmarshal(queryResponse.Value, &event)
		if strings.HasPrefix(event.EventID, "StartEvent") ||
			strings.HasPrefix(event.EventID, "Event") ||
			strings.HasPrefix(event.EventID, "EndEvent") {
			if err != nil {
				return nil, fmt.Errorf("反序列化事件数据时出错: %v", err)
			}

			events = append(events, &event)
		}
	}

	return events, nil
}

// InitLedger adds a base set of elements to the ledger

var isInited bool = false

func (cc *SmartContract) InitLedger(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	if isInited {
		errorMessage := "Chaincode has already been initialized"
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.CreateActionEvent(ctx, "Event_07p8use", ENABLE)
	cc.CreateMessage(ctx, "Message_1xm2zol", "Org1-consor1.org.comMSP", "Member1.org.comMSP", "", DISABLE, "{\"properties\":{\"123\":{\"type\":\"string\",\"description\":\"\"}},\"required\":[],\"files\":{},\"file required\":[]}")
	cc.CreateActionEvent(ctx, "Event_09mx8cj", DISABLE)

	isInited = true

	stub.SetEvent("initContractEvent", []byte("Contract has been initialized successfully"))
	return nil
}
func (cc *SmartContract) Event_07p8use(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	actionEvent, err := cc.ReadEvent(ctx, "Event_07p8use")
	if err != nil {
		return err
	}

	if actionEvent.EventState != ENABLE {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", actionEvent.EventID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeEventState(ctx, "Event_07p8use", DONE)
	stub.SetEvent("Event_07p8use", []byte("Contract has been started successfully"))

	cc.ChangeMsgState(ctx, "Message_1xm2zol", ENABLE)
	return nil
}

func (cc *SmartContract) Message_1xm2zol_Send(ctx contractapi.TransactionContextInterface, fireflyTranID string) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1xm2zol")
	if err != nil {
		return err
	}

	clientIdentity := ctx.GetClientIdentity()
	clientMspID, _ := clientIdentity.GetMSPID()
	if clientMspID != msg.SendMspID {
		errorMessage := fmt.Sprintf("Msp denied")
		fmt.Println(errorMessage)
		return errors.New(fmt.Sprintf("Msp denied"))
	}
	if msg.MsgState != ENABLE {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	msg.MsgState = WAITFORCONFIRM
	msg.FireflyTranID = fireflyTranID
	msgJSON, _ := json.Marshal(msg)
	stub.PutState("Message_1xm2zol", msgJSON)
	stub.SetEvent("ChoreographyTask_04v0g4z", []byte("Message wait for confirming"))

	return nil
}

func (cc *SmartContract) Message_1xm2zol_Complete(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1xm2zol")
	if err != nil {
		return err
	}

	clientIdentity := ctx.GetClientIdentity()
	clientMspID, _ := clientIdentity.GetMSPID()
	if clientMspID != msg.ReceiveMspID {
		errorMessage := fmt.Sprintf("Msp denied")
		fmt.Println(errorMessage)
		return errors.New(fmt.Sprintf("Msp denied"))
	}

	if msg.MsgState != WAITFORCONFIRM {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgState(ctx, "Message_1xm2zol", DONE)
	stub.SetEvent("Message_1xm2zol", []byte("Message has been done"))

	cc.ChangeEventState(ctx, "Event_09mx8cj", ENABLE)

	return nil
} //编排任务的最后一个消息

func (cc *SmartContract) Event_09mx8cj(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	event, err := cc.ReadEvent(ctx, "Event_09mx8cj")
	if err != nil {
		return err
	}

	if event.EventState != ENABLE {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", event.EventID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeEventState(ctx, "Event_09mx8cj", DONE)
	stub.SetEvent("Event_09mx8cj", []byte("EndEvent has been done"))
	return nil
}

func (cc *SmartContract) ExclusiveGateway_0nzwv7v(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	gtw, err := cc.ReadGtw(ctx, "ExclusiveGateway_0nzwv7v")
	if err != nil {
		return err
	}

	if gtw.GatewayState != ENABLE {
		errorMessage := fmt.Sprintf("Gateway state %s is not allowed", gtw.GatewayID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeGtwState(ctx, "ExclusiveGateway_0nzwv7v", DONE)
	stub.SetEvent("ExclusiveGateway_0nzwv7v", []byte("ExclusiveGateway has been done"))
	currentMemory, err := cc.ReadMemory(ctx)
	if err != nil {
		fmt.Println(err)
		return err
	}
	if currentMemory.Invoice == false {
		cc.ChangeEventState(ctx, "Event_08edp7f", ENABLE)

	} else if currentMemory.Invoice == true {
		cc.ChangeMsgState(ctx, "Message_1joj7ca", ENABLE)

	}
	return nil
}

func (cc *SmartContract) Event_08edp7f(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	event, err := cc.ReadEvent(ctx, "Event_08edp7f")
	if err != nil {
		return err
	}

	if event.EventState != ENABLE {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", event.EventID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeEventState(ctx, "Event_08edp7f", DONE)
	stub.SetEvent("Event_08edp7f", []byte("EndEvent has been done"))
	return nil
}

func (cc *SmartContract) Message_1joj7ca_Send(ctx contractapi.TransactionContextInterface, fireflyTranID string) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1joj7ca")
	if err != nil {
		return err
	}

	clientIdentity := ctx.GetClientIdentity()
	clientMspID, _ := clientIdentity.GetMSPID()
	if clientMspID != msg.SendMspID {
		errorMessage := fmt.Sprintf("Msp denied")
		fmt.Println(errorMessage)
		return errors.New(fmt.Sprintf("Msp denied"))
	}

	if msg.MsgState != ENABLE {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	msg.MsgState = WAITFORCONFIRM
	msg.FireflyTranID = fireflyTranID
	msgJSON, _ := json.Marshal(msg)
	stub.PutState("Message_1joj7ca", msgJSON)
	stub.SetEvent("Message_1joj7ca", []byte("Message wait for confirming"))

	return nil
}

func (cc *SmartContract) Message_1joj7ca_Complete(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1joj7ca")
	if err != nil {
		return err
	}

	clientIdentity := ctx.GetClientIdentity()
	clientMspID, _ := clientIdentity.GetMSPID()
	if clientMspID != msg.ReceiveMspID {
		errorMessage := fmt.Sprintf("Msp denied")
		fmt.Println(errorMessage)
		return errors.New(fmt.Sprintf("Msp denied"))
	}

	if msg.MsgState != WAITFORCONFIRM {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgState(ctx, "Message_1joj7ca", DONE)
	stub.SetEvent("Message_1joj7ca", []byte("Message has been done"))

	cc.ChangeMsgState(ctx, "Message_1etcmvl", ENABLE)
	return nil
}

func (cc *SmartContract) Message_1etcmvl_Send(ctx contractapi.TransactionContextInterface, fireflyTranID string) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1etcmvl")
	if err != nil {
		return err
	}

	clientIdentity := ctx.GetClientIdentity()
	clientMspID, _ := clientIdentity.GetMSPID()
	if clientMspID != msg.SendMspID {
		errorMessage := fmt.Sprintf("Msp denied")
		fmt.Println(errorMessage)
		return errors.New(fmt.Sprintf("Msp denied"))
	}
	if msg.MsgState != ENABLE {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	msg.MsgState = WAITFORCONFIRM
	msg.FireflyTranID = fireflyTranID
	msgJSON, _ := json.Marshal(msg)
	stub.PutState("Message_1etcmvl", msgJSON)
	stub.SetEvent("Message_1etcmvl", []byte("Message wait for confirming"))

	return nil
}

func (cc *SmartContract) Message_1etcmvl_Complete(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1etcmvl")
	if err != nil {
		return err
	}

	clientIdentity := ctx.GetClientIdentity()
	clientMspID, _ := clientIdentity.GetMSPID()
	if clientMspID != msg.ReceiveMspID {
		errorMessage := fmt.Sprintf("Msp denied")
		fmt.Println(errorMessage)
		return errors.New(fmt.Sprintf("Msp denied"))
	}

	if msg.MsgState != WAITFORCONFIRM {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgState(ctx, "Message_1etcmvl", DONE)
	stub.SetEvent("Message_1etcmvl", []byte("Message has been done"))

	cc.ChangeEventState(ctx, "Event_146eii4", ENABLE)

	return nil
} //编排任务的最后一个消息

func (cc *SmartContract) Event_146eii4(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	event, err := cc.ReadEvent(ctx, "Event_146eii4")
	if err != nil {
		return err
	}

	if event.EventState != ENABLE {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", event.EventID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeEventState(ctx, "Event_146eii4", DONE)
	stub.SetEvent("Event_146eii4", []byte("EndEvent has been done"))
	return nil
}

func (cc *SmartContract) ExclusiveGateway_106je4z(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	gtw, err := cc.ReadGtw(ctx, "ExclusiveGateway_106je4z")
	if err != nil {
		return err
	}

	if gtw.GatewayState != ENABLE {
		errorMessage := fmt.Sprintf("Gateway state %s is not allowed", gtw.GatewayID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeGtwState(ctx, "ExclusiveGateway_106je4z", DONE)
	stub.SetEvent("ExclusiveGateway_106je4z", []byte("ExclusiveGateway has been done"))
	currentMemory, err := cc.ReadMemory(ctx)
	if err != nil {
		fmt.Println(err)
		return err
	}
	if currentMemory.IsAvailable == true {
		cc.ChangeMsgState(ctx, "Message_1em0ee4", ENABLE)

	} else if currentMemory.IsAvailable == false {
		cc.ChangeGtwState(ctx, "ExclusiveGateway_0hs3ztq", ENABLE)

	}
	return nil
}

func (cc *SmartContract) Gateway_1bhtapl(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	gtw, err := cc.ReadGtw(ctx, "Gateway_1bhtapl")
	if err != nil {
		return err
	}

	if gtw.GatewayState != ENABLE {
		errorMessage := fmt.Sprintf("Gateway state %s is not allowed", gtw.GatewayID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeGtwState(ctx, "Gateway_1bhtapl", DONE)
	stub.SetEvent("Gateway_1bhtapl", []byte("ExclusiveGateway has been done"))
	currentMemory, err := cc.ReadMemory(ctx)
	if err != nil {
		fmt.Println(err)
		return err
	}
	if currentMemory.NeedExternalProvider == true {
		cc.ChangeMsgState(ctx, "Message_1i8rlqn", ENABLE)

	} else if currentMemory.NeedExternalProvider == false {
		cc.ChangeGtwState(ctx, "Gateway_04h9e6e", ENABLE)

	}
	return nil
}

func (cc *SmartContract) Message_1i8rlqn_Send(ctx contractapi.TransactionContextInterface, fireflyTranID string) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1i8rlqn")
	if err != nil {
		return err
	}

	clientIdentity := ctx.GetClientIdentity()
	clientMspID, _ := clientIdentity.GetMSPID()
	if clientMspID != msg.SendMspID {
		errorMessage := fmt.Sprintf("Msp denied")
		fmt.Println(errorMessage)
		return errors.New(fmt.Sprintf("Msp denied"))
	}
	if msg.MsgState != ENABLE {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	msg.MsgState = WAITFORCONFIRM
	msg.FireflyTranID = fireflyTranID
	msgJSON, _ := json.Marshal(msg)
	stub.PutState("Message_1i8rlqn", msgJSON)
	stub.SetEvent("ChoreographyTask_1khafgk", []byte("Message wait for confirming"))

	return nil
}

func (cc *SmartContract) Message_1i8rlqn_Complete(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1i8rlqn")
	if err != nil {
		return err
	}

	clientIdentity := ctx.GetClientIdentity()
	clientMspID, _ := clientIdentity.GetMSPID()
	if clientMspID != msg.ReceiveMspID {
		errorMessage := fmt.Sprintf("Msp denied")
		fmt.Println(errorMessage)
		return errors.New(fmt.Sprintf("Msp denied"))
	}

	if msg.MsgState != WAITFORCONFIRM {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgState(ctx, "Message_1i8rlqn", DONE)
	stub.SetEvent("Message_1i8rlqn", []byte("Message has been done"))

	cc.ChangeMsgState(ctx, "Message_1q05nnw", ENABLE)

	return nil
} //编排任务的最后一个消息

func (cc *SmartContract) Message_1ljlm4g_Send(ctx contractapi.TransactionContextInterface, fireflyTranID string) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1ljlm4g")
	if err != nil {
		return err
	}

	clientIdentity := ctx.GetClientIdentity()
	clientMspID, _ := clientIdentity.GetMSPID()
	if clientMspID != msg.SendMspID {
		errorMessage := fmt.Sprintf("Msp denied")
		fmt.Println(errorMessage)
		return errors.New(fmt.Sprintf("Msp denied"))
	}

	if msg.MsgState != ENABLE {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	msg.MsgState = WAITFORCONFIRM
	msg.FireflyTranID = fireflyTranID
	msgJSON, _ := json.Marshal(msg)
	stub.PutState("Message_1ljlm4g", msgJSON)
	stub.SetEvent("Message_1ljlm4g", []byte("Message wait for confirming"))

	return nil
}

func (cc *SmartContract) Message_1ljlm4g_Complete(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1ljlm4g")
	if err != nil {
		return err
	}

	clientIdentity := ctx.GetClientIdentity()
	clientMspID, _ := clientIdentity.GetMSPID()
	if clientMspID != msg.ReceiveMspID {
		errorMessage := fmt.Sprintf("Msp denied")
		fmt.Println(errorMessage)
		return errors.New(fmt.Sprintf("Msp denied"))
	}

	if msg.MsgState != WAITFORCONFIRM {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgState(ctx, "Message_1ljlm4g", DONE)
	stub.SetEvent("Message_1ljlm4g", []byte("Message has been done"))

	cc.ChangeMsgState(ctx, "Message_0m9p3da", ENABLE)
	return nil
}

func (cc *SmartContract) Message_0m9p3da_Send(ctx contractapi.TransactionContextInterface, fireflyTranID string, invoice bool) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_0m9p3da")
	if err != nil {
		return err
	}

	clientIdentity := ctx.GetClientIdentity()
	clientMspID, _ := clientIdentity.GetMSPID()
	if clientMspID != msg.SendMspID {
		errorMessage := fmt.Sprintf("Msp denied")
		fmt.Println(errorMessage)
		return errors.New(fmt.Sprintf("Msp denied"))
	}
	if msg.MsgState != ENABLE {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	msg.MsgState = WAITFORCONFIRM
	msg.FireflyTranID = fireflyTranID
	msgJSON, _ := json.Marshal(msg)
	stub.PutState("Message_0m9p3da", msgJSON)
	stub.SetEvent("Message_0m9p3da", []byte("Message wait for confirming"))

	currentMemory, err := cc.ReadMemory(ctx)
	if err != nil {
		fmt.Println(err)
		return err
	}
	currentMemory.Invoice = invoice
	memoryJSON, err := json.Marshal(currentMemory)
	if err != nil {
		return fmt.Errorf("failed to marshal memory state: %s", err)
	}

	err = stub.PutState("currentMemory", memoryJSON)
	if err != nil {
		return fmt.Errorf("failed to save memory state: %s", err)
	}

	return nil
}

func (cc *SmartContract) Message_0m9p3da_Complete(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_0m9p3da")
	if err != nil {
		return err
	}

	clientIdentity := ctx.GetClientIdentity()
	clientMspID, _ := clientIdentity.GetMSPID()
	if clientMspID != msg.ReceiveMspID {
		errorMessage := fmt.Sprintf("Msp denied")
		fmt.Println(errorMessage)
		return errors.New(fmt.Sprintf("Msp denied"))
	}

	if msg.MsgState != WAITFORCONFIRM {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgState(ctx, "Message_0m9p3da", DONE)
	stub.SetEvent("Message_0m9p3da", []byte("Message has been done"))

	cc.ChangeGtwState(ctx, "ExclusiveGateway_0nzwv7v", ENABLE)

	return nil
} //编排任务的最后一个消息

func (cc *SmartContract) Gateway_04h9e6e(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	gtw, err := cc.ReadGtw(ctx, "Gateway_04h9e6e")
	if err != nil {
		return err
	}

	if gtw.GatewayState != ENABLE {
		errorMessage := fmt.Sprintf("Gateway state %s is not allowed", gtw.GatewayID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeGtwState(ctx, "Gateway_04h9e6e", DONE)
	stub.SetEvent("Gateway_04h9e6e", []byte("ExclusiveGateway has been done"))

	cc.ChangeMsgState(ctx, "Message_1ljlm4g", ENABLE)

	return nil
}

func (cc *SmartContract) Message_1q05nnw_Send(ctx contractapi.TransactionContextInterface, fireflyTranID string) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1q05nnw")
	if err != nil {
		return err
	}

	clientIdentity := ctx.GetClientIdentity()
	clientMspID, _ := clientIdentity.GetMSPID()
	if clientMspID != msg.SendMspID {
		errorMessage := fmt.Sprintf("Msp denied")
		fmt.Println(errorMessage)
		return errors.New(fmt.Sprintf("Msp denied"))
	}

	if msg.MsgState != ENABLE {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	msg.MsgState = WAITFORCONFIRM
	msg.FireflyTranID = fireflyTranID
	msgJSON, _ := json.Marshal(msg)
	stub.PutState("Message_1q05nnw", msgJSON)
	stub.SetEvent("Message_1q05nnw", []byte("Message wait for confirming"))

	return nil
}

func (cc *SmartContract) Message_1q05nnw_Complete(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1q05nnw")
	if err != nil {
		return err
	}

	clientIdentity := ctx.GetClientIdentity()
	clientMspID, _ := clientIdentity.GetMSPID()
	if clientMspID != msg.ReceiveMspID {
		errorMessage := fmt.Sprintf("Msp denied")
		fmt.Println(errorMessage)
		return errors.New(fmt.Sprintf("Msp denied"))
	}

	if msg.MsgState != WAITFORCONFIRM {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgState(ctx, "Message_1q05nnw", DONE)
	stub.SetEvent("Message_1q05nnw", []byte("Message has been done"))

	cc.ChangeMsgState(ctx, "Message_1qbk325", ENABLE)
	return nil
}

func (cc *SmartContract) Message_1qbk325_Send(ctx contractapi.TransactionContextInterface, fireflyTranID string) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1qbk325")
	if err != nil {
		return err
	}

	clientIdentity := ctx.GetClientIdentity()
	clientMspID, _ := clientIdentity.GetMSPID()
	if clientMspID != msg.SendMspID {
		errorMessage := fmt.Sprintf("Msp denied")
		fmt.Println(errorMessage)
		return errors.New(fmt.Sprintf("Msp denied"))
	}
	if msg.MsgState != ENABLE {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	msg.MsgState = WAITFORCONFIRM
	msg.FireflyTranID = fireflyTranID
	msgJSON, _ := json.Marshal(msg)
	stub.PutState("Message_1qbk325", msgJSON)
	stub.SetEvent("Message_1qbk325", []byte("Message wait for confirming"))

	return nil
}

func (cc *SmartContract) Message_1qbk325_Complete(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1qbk325")
	if err != nil {
		return err
	}

	clientIdentity := ctx.GetClientIdentity()
	clientMspID, _ := clientIdentity.GetMSPID()
	if clientMspID != msg.ReceiveMspID {
		errorMessage := fmt.Sprintf("Msp denied")
		fmt.Println(errorMessage)
		return errors.New(fmt.Sprintf("Msp denied"))
	}

	if msg.MsgState != WAITFORCONFIRM {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgState(ctx, "Message_1qbk325", DONE)
	stub.SetEvent("Message_1qbk325", []byte("Message has been done"))

	cc.ChangeGtwState(ctx, "Gateway_04h9e6e", ENABLE)

	return nil
} //编排任务的最后一个消息
