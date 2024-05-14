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
	currentMemory StateMemory
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
	SendMspID     string       `json:"sendMspID"`     //实例信息 in
	ReceiveMspID  string       `json:"receiveMspID"`  //实例信息 in
	FireflyTranID string       `json:"fireflyTranID"` //实例信息 out
	MsgState      ElementState `json:"msgState"`      //实例信息 inout
	Format        string       `json:"format"`        //实例信息 in
}

type Gateway struct {
	GatewayID    string       `json:"gatewayID"`
	GatewayState ElementState `json:"gatewayState"`
}

type ActionEvent struct {
	EventID    string       `json:"eventID"`
	EventState ElementState `json:"eventState"`
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

	cc.CreateActionEvent(ctx, "Event_0yvuoj9", ENABLE)
	cc.CreateMessage(ctx, "Message_0wk0hjx", "Member2.org.comMSP", "Member1.org.comMSP", "", DISABLE, "{\"properties\":{\"Message\":{\"type\":\"string\",\"description\":\"\"}},\"required\":[],\"files\":{},\"file required\":[]}")
	cc.CreateActionEvent(ctx, "Event_0zbimwf", DISABLE)

	isInited = true

	stub.SetEvent("initContractEvent", []byte("Contract has been initialized successfully"))
	return nil
}
func (cc *SmartContract) Event_0yvuoj9(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	actionEvent, err := cc.ReadEvent(ctx, "Event_0yvuoj9")
	if err != nil {
		return err
	}

	if actionEvent.EventState != ENABLE {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", actionEvent.EventID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeEventState(ctx, "Event_0yvuoj9", DONE)
	stub.SetEvent("Event_0yvuoj9", []byte("Contract has been started successfully"))

	cc.ChangeMsgState(ctx, "Message_0wk0hjx", ENABLE)
	return nil
}

func (cc *SmartContract) Message_0wk0hjx_Send(ctx contractapi.TransactionContextInterface, fireflyTranID string) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_0wk0hjx")
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
	stub.PutState("Message_0wk0hjx", msgJSON)
	stub.SetEvent("ChoreographyTask_1t3oouf", []byte("Message wait for confirming"))

	return nil
}

func (cc *SmartContract) Message_0wk0hjx_Complete(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_0wk0hjx")
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

	cc.ChangeMsgState(ctx, "Message_0wk0hjx", DONE)
	stub.SetEvent("Message_0wk0hjx", []byte("Message has been done"))

	cc.ChangeEventState(ctx, "Event_0zbimwf", ENABLE)

	return nil
} //编排任务的最后一个消息

func (cc *SmartContract) Event_0zbimwf(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	event, err := cc.ReadEvent(ctx, "Event_0zbimwf")
	if err != nil {
		return err
	}

	if event.EventState != ENABLE {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", event.EventID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeEventState(ctx, "Event_0zbimwf", ENABLE)
	stub.SetEvent("Event_0zbimwf", []byte("EndEvent has been done"))
	return nil
}
