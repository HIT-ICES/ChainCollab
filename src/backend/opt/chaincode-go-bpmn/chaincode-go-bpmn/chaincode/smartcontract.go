package chaincode

import (
	"encoding/json"
	"errors"
	"fmt"
	"github.com/hyperledger/fabric-contract-api-go/contractapi"
	"strings"
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
	need_external_provider		bool		`json:"need_external_provider"`
	invoice		bool		`json:"invoice"`
	is_available		bool		`json:"is_available"`
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
		Format:      format,
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

func (c *SmartContract) ReadCurrentMemory(ctx contractapi.TransactionContextInterface) (*StateMemory, error) {
	memoryJSON, err := ctx.GetStub().GetState("currentMemory")

	if err != nil {
		return nil, fmt.Errorf("failed to read current memory from state: %s", err)
	}

	if memoryJSON == nil {
		return nil, fmt.Errorf("current memory does not exists")
	}

	var memory StateMemory
	err = json.Unmarshal(memoryJSON, &memory)
	if err != nil {
		return nil, fmt.Errorf("failed to unmarshal memory state: %s", err)
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

	cc.CreateMessage(ctx, "Message_1em0ee4", "Org-1.org.comMSP", "Org-2.org.comMSP", "", DISABLE, "{\"properties\":{\"service plan\":{\"type\":\"string\",\"description\":\"service plan\"},\"price_quotation\":{\"type\":\"number\",\"description\":\"Price quotation\"},\"need_external_provider\":{\"type\":\"boolean\",\"description\":\"Whether external service providers are required\"}},\"required\":[\"service plan\",\"price_quotation\",\"need_external_provider\"],\"files\":{},\"file required\":[]}")
	cc.CreateMessage(ctx, "Message_1nlagx2", "Org-2.org.comMSP", "Org-1.org.comMSP", "", DISABLE, "{\"properties\":{\"confirmation\":{\"type\":\"boolean\",\"description\":\"Whether to accept the service plan\"}},\"required\":[\"confirmation\"],\"files\":{},\"file required\":[]}")
	cc.CreateMessage(ctx, "Message_045i10y", "Org-2.org.comMSP", "Org-1.org.comMSP", "", DISABLE, "{\"properties\":{\"serviceId\":{\"type\":\"string\",\"description\":\"The required service id\"}},\"required\":[\"serviceId\"],\"files\":{},\"file required\":[]}")
	cc.CreateMessage(ctx, "Message_0r9lypd", "Org-1.org.comMSP", "Org-2.org.comMSP", "", DISABLE, "{\"properties\":{\"is_available\":{\"type\":\"boolean\",\"description\":\"Is the service available?\"}},\"required\":[\"is_available\"],\"files\":{},\"file required\":[]}")
	cc.CreateGateway(ctx, "ExclusiveGateway_0hs3ztq", DISABLE)
	cc.CreateActionEvent(ctx, "Event_1jtgn3j", ENABLE)
	cc.CreateGateway(ctx, "EventBasedGateway_1fxpmyn", DISABLE)
	cc.CreateMessage(ctx, "Message_0o8eyir", "Org-2.org.comMSP", "Org-1.org.comMSP", "", DISABLE, "{\"properties\":{\"payment amount\":{\"type\":\"number\",\"description\":\"payment amount\"},\"orderID\":{\"type\":\"number\",\"description\":\"The order id of payment\"}},\"required\":[\"payment amount\",\"orderID\"],\"files\":{},\"file required\":[]}")
	cc.CreateMessage(ctx, "Message_1xm9dxy", "Org-2.org.comMSP", "Org-1.org.comMSP", "", DISABLE, "{\"properties\":{\"motivation\":{\"type\":\"string\",\"description\":\"Motivation for Canceling orders\"}},\"required\":[\"motivation\"],\"files\":{},\"file required\":[]}")
	cc.CreateActionEvent(ctx, "Event_0366pfz", DISABLE)
	cc.CreateGateway(ctx, "ExclusiveGateway_0nzwv7v", DISABLE)
	cc.CreateActionEvent(ctx, "Event_08edp7f", DISABLE)
	cc.CreateMessage(ctx, "Message_1joj7ca", "Org-2.org.comMSP", "Org-1.org.comMSP", "", DISABLE, "{\"properties\":{\"invoice information\":{\"type\":\"string\",\"description\":\"Invoice related information\"}},\"required\":[\"invoice information\"],\"files\":{},\"file required\":[]}")
	cc.CreateMessage(ctx, "Message_1etcmvl", "Org-1.org.comMSP", "Org-2.org.comMSP", "", DISABLE, "{\"properties\":{\"invoice_id\":{\"type\":\"string\",\"description\":\"Invoice Id\"},\"invoice_data\":{\"type\":\"number\",\"description\":\"Date of invoice issuance\"}},\"required\":[\"invoice_id\"],\"files\":{\"invoice\":{\"type\":\"file\",\"description\":\"Invoice documents\"}},\"file required\":[\"invoice\"]}")
	cc.CreateActionEvent(ctx, "Event_146eii4", DISABLE)
	cc.CreateGateway(ctx, "ExclusiveGateway_106je4z", DISABLE)
	cc.CreateGateway(ctx, "Gateway_1bhtapl", DISABLE)
	cc.CreateMessage(ctx, "Message_1i8rlqn", "Org-1.org.comMSP", "Org-con.org.comMSP", "", DISABLE, "{\"properties\":{\"external service Id\":{\"type\":\"string\",\"description\":\"The requested external service information\"}},\"required\":[\"external service Id\"],\"files\":{},\"file required\":[]}")
	cc.CreateMessage(ctx, "Message_1ljlm4g", "Org-1.org.comMSP", "Org-2.org.comMSP", "", DISABLE, "{\"properties\":{\"delivered_product_id\":{\"type\":\"string\",\"description\":\"delivered_product_id\"}},\"required\":[\"delivered_product_id\"],\"files\":{},\"file required\":[]}")
	cc.CreateMessage(ctx, "Message_0m9p3da", "Org-2.org.comMSP", "Org-1.org.comMSP", "", DISABLE, "{\"properties\":{\"invoice\":{\"type\":\"boolean\",\"description\":\"Do you need an invoice?\"}},\"required\":[\"invoice\"],\"files\":{},\"file required\":[]}")
	cc.CreateGateway(ctx, "Gateway_04h9e6e", DISABLE)
	cc.CreateMessage(ctx, "Message_1q05nnw", "Org-1.org.comMSP", "Org-con.org.comMSP", "", DISABLE, "{\"properties\":{\"payment amount\":{\"type\":\"number\",\"description\":\"payment amount\"}},\"required\":[\"payment amount\"],\"files\":{},\"file required\":[]}")
	cc.CreateMessage(ctx, "Message_1qbk325", "Org-con.org.comMSP", "Org-1.org.comMSP", "", DISABLE, "{\"properties\":{\"product Id\":{\"type\":\"string\",\"description\":\"Delivered product id\"}},\"required\":[\"product Id\"],\"files\":{},\"file required\":[]}")
	
	isInited = true

	stub.SetEvent("initContractEvent", []byte("Contract has been initialized successfully"))
	return nil
}
func (cc *SmartContract) Message_1em0ee4_Send(ctx contractapi.TransactionContextInterface, fireflyTranID string, need_external_provider bool) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1em0ee4")
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
	stub.PutState("Message_1em0ee4", msgJSON)
	stub.SetEvent("Message_1em0ee4", []byte("Message wait for confirming"))

	cc.currentMemory.need_external_provider = need_external_provider
		memoryJSON, err := json.Marshal(cc.currentMemory)
		if err != nil {
		return fmt.Errorf("failed to marshal memory state: %s", err)
	}

	err = stub.PutState("currentMemory", memoryJSON)
		if err != nil {
		return fmt.Errorf("failed to save memory state: %s", err)
	}


return nil
}

func (cc *SmartContract) Message_1em0ee4_Complete(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1em0ee4")
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

	cc.ChangeMsgState(ctx, "Message_1em0ee4", DONE)
	stub.SetEvent("Message_1em0ee4", []byte("Message has been done"))

	cc.ChangeMsgState(ctx, "Message_1nlagx2", ENABLE)
	return nil
}

func (cc *SmartContract) Message_1nlagx2_Send(ctx contractapi.TransactionContextInterface, fireflyTranID string) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1nlagx2")
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
	stub.PutState("Message_1nlagx2", msgJSON)
	stub.SetEvent("Message_1nlagx2", []byte("Message wait for confirming"))

	memoryJSON, err := json.Marshal(cc.currentMemory)
		if err != nil {
		return fmt.Errorf("failed to marshal memory state: %s", err)
	}

	err = stub.PutState("currentMemory", memoryJSON)
		if err != nil {
		return fmt.Errorf("failed to save memory state: %s", err)
	}

	
return nil
}

func (cc *SmartContract) Message_1nlagx2_Complete(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1nlagx2")
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

	cc.ChangeMsgState(ctx, "Message_1nlagx2", DONE)
	stub.SetEvent("Message_1nlagx2", []byte("Message has been done"))

	cc.ChangeGtwState(ctx, "EventBasedGateway_1fxpmyn" ,ENABLE)


return nil
}	//编排任务的最后一个消息

func (cc *SmartContract) Message_045i10y_Send(ctx contractapi.TransactionContextInterface, fireflyTranID string) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_045i10y")
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
	stub.PutState("Message_045i10y", msgJSON)
	stub.SetEvent("Message_045i10y", []byte("Message wait for confirming"))

	memoryJSON, err := json.Marshal(cc.currentMemory)
		if err != nil {
		return fmt.Errorf("failed to marshal memory state: %s", err)
	}

	err = stub.PutState("currentMemory", memoryJSON)
		if err != nil {
		return fmt.Errorf("failed to save memory state: %s", err)
	}


return nil
}

func (cc *SmartContract) Message_045i10y_Complete(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_045i10y")
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

	cc.ChangeMsgState(ctx, "Message_045i10y", DONE)
	stub.SetEvent("Message_045i10y", []byte("Message has been done"))

	cc.ChangeMsgState(ctx, "Message_0r9lypd", ENABLE)
	return nil
}

func (cc *SmartContract) Message_0r9lypd_Send(ctx contractapi.TransactionContextInterface, fireflyTranID string, is_available bool) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_0r9lypd")
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
	stub.PutState("Message_0r9lypd", msgJSON)
	stub.SetEvent("Message_0r9lypd", []byte("Message wait for confirming"))

	cc.currentMemory.is_available = is_available
		memoryJSON, err := json.Marshal(cc.currentMemory)
		if err != nil {
		return fmt.Errorf("failed to marshal memory state: %s", err)
	}

	err = stub.PutState("currentMemory", memoryJSON)
		if err != nil {
		return fmt.Errorf("failed to save memory state: %s", err)
	}

	
return nil
}

func (cc *SmartContract) Message_0r9lypd_Complete(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_0r9lypd")
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

	cc.ChangeMsgState(ctx, "Message_0r9lypd", DONE)
	stub.SetEvent("Message_0r9lypd", []byte("Message has been done"))

	cc.ChangeGtwState(ctx, "ExclusiveGateway_106je4z" ,ENABLE)


return nil
}	//编排任务的最后一个消息

func (cc *SmartContract) ExclusiveGateway_0hs3ztq(ctx contractapi.TransactionContextInterface) error { 
	stub := ctx.GetStub()
	gtw, err := cc.ReadGtw(ctx, "ExclusiveGateway_0hs3ztq")
	if err != nil {
		return err
	}

	if gtw.GatewayState != ENABLE {
		errorMessage := fmt.Sprintf("Gateway state %s is not allowed", gtw.GatewayID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeGtwState(ctx, "ExclusiveGateway_0hs3ztq", DONE)
	stub.SetEvent("ExclusiveGateway_0hs3ztq", []byte("ExclusiveGateway has been done"))

        cc.ChangeMsgState(ctx, "Message_045i10y" ,ENABLE)


	return nil
}

func (cc *SmartContract) Event_1jtgn3j(ctx contractapi.TransactionContextInterface) error { 
	stub := ctx.GetStub()
	actionEvent, err := cc.ReadEvent(ctx, "Event_1jtgn3j")
	if err != nil {
		return err
	}

	if actionEvent.EventState != ENABLE {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", actionEvent.EventID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeEventState(ctx, "Event_1jtgn3j", DONE)
	stub.SetEvent("Event_1jtgn3j", []byte("Contract has been started successfully"))

	cc.ChangeGtwState(ctx, "ExclusiveGateway_0hs3ztq", ENABLE)
	return nil
}

func (cc *SmartContract) EventBasedGateway_1fxpmyn(ctx contractapi.TransactionContextInterface) error { 
	stub := ctx.GetStub()
	gtw, err := cc.ReadGtw(ctx, "EventBasedGateway_1fxpmyn")
	if err != nil {
		return err
	}

	if gtw.GatewayState != ENABLE {
		errorMessage := fmt.Sprintf("Gateway state %s is not allowed", gtw.GatewayID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeGtwState(ctx, "EventBasedGateway_1fxpmyn", DONE)
	stub.SetEvent("EventBasedGateway_1fxpmyn", []byte("EventbasedGateway has been done"))

        cc.ChangeMsgState(ctx, "Message_0o8eyir" ,ENABLE)

        cc.ChangeMsgState(ctx, "Message_1xm9dxy" ,ENABLE)


return nil
}

func (cc *SmartContract) Message_0o8eyir_Send(ctx contractapi.TransactionContextInterface, fireflyTranID string) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_0o8eyir")
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
	stub.PutState("Message_0o8eyir", msgJSON)
		stub.SetEvent("ChoreographyTask_177ikw5", []byte("Message wait for confirming"))

	memoryJSON, err := json.Marshal(cc.currentMemory)
		if err != nil {
		return fmt.Errorf("failed to marshal memory state: %s", err)
	}

	err = stub.PutState("currentMemory", memoryJSON)
		if err != nil {
		return fmt.Errorf("failed to save memory state: %s", err)
	}

        cc.ChangeMsgState(ctx, "Message_1xm9dxy" ,DISABLE)

	
return nil
}

func (cc *SmartContract) Message_0o8eyir_Complete(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_0o8eyir")
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

	cc.ChangeMsgState(ctx, "Message_0o8eyir", DONE)
	stub.SetEvent("Message_0o8eyir", []byte("Message has been done"))

	cc.ChangeGtwState(ctx, "Gateway_1bhtapl" ,ENABLE)


return nil
}	//编排任务的最后一个消息

func (cc *SmartContract) Message_1xm9dxy_Send(ctx contractapi.TransactionContextInterface, fireflyTranID string) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1xm9dxy")
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
	stub.PutState("Message_1xm9dxy", msgJSON)
		stub.SetEvent("ChoreographyTask_09lf521", []byte("Message wait for confirming"))

	memoryJSON, err := json.Marshal(cc.currentMemory)
		if err != nil {
		return fmt.Errorf("failed to marshal memory state: %s", err)
	}

	err = stub.PutState("currentMemory", memoryJSON)
		if err != nil {
		return fmt.Errorf("failed to save memory state: %s", err)
	}

        cc.ChangeMsgState(ctx, "Message_0o8eyir" ,DISABLE)

	
return nil
}

func (cc *SmartContract) Message_1xm9dxy_Complete(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_1xm9dxy")
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

	cc.ChangeMsgState(ctx, "Message_1xm9dxy", DONE)
	stub.SetEvent("Message_1xm9dxy", []byte("Message has been done"))

	cc.ChangeEventState(ctx, "Event_0366pfz" ,ENABLE)


return nil
}	//编排任务的最后一个消息

func (cc *SmartContract) Event_0366pfz(ctx contractapi.TransactionContextInterface) error { 
	stub := ctx.GetStub()
	event, err := cc.ReadEvent(ctx, "Event_0366pfz")
	if err != nil {
		return err
	}

	if event.EventState != ENABLE {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", event.EventID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeEventState(ctx, "Event_0366pfz", DONE)
	stub.SetEvent("Event_0366pfz", []byte("EndEvent has been done"))
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

if cc.currentMemory.invoice==false {
        cc.ChangeEventState(ctx, "Event_08edp7f" ,ENABLE)

} else if cc.currentMemory.invoice==true {
        cc.ChangeMsgState(ctx, "Message_1joj7ca" ,ENABLE)

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

	memoryJSON, err := json.Marshal(cc.currentMemory)
		if err != nil {
		return fmt.Errorf("failed to marshal memory state: %s", err)
	}

	err = stub.PutState("currentMemory", memoryJSON)
		if err != nil {
		return fmt.Errorf("failed to save memory state: %s", err)
	}


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

	memoryJSON, err := json.Marshal(cc.currentMemory)
		if err != nil {
		return fmt.Errorf("failed to marshal memory state: %s", err)
	}

	err = stub.PutState("currentMemory", memoryJSON)
		if err != nil {
		return fmt.Errorf("failed to save memory state: %s", err)
	}

	
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

	cc.ChangeEventState(ctx, "Event_146eii4" ,ENABLE)


return nil
}	//编排任务的最后一个消息

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

if cc.currentMemory.is_available==true {
        cc.ChangeMsgState(ctx, "Message_1em0ee4" ,ENABLE)

} else if cc.currentMemory.is_available==false {
        cc.ChangeGtwState(ctx, "ExclusiveGateway_0hs3ztq" ,ENABLE)

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

if cc.currentMemory.need_external_provider==true {
        cc.ChangeMsgState(ctx, "Message_1i8rlqn" ,ENABLE)

} else if cc.currentMemory.need_external_provider==false {
        cc.ChangeGtwState(ctx, "Gateway_04h9e6e" ,ENABLE)

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

	memoryJSON, err := json.Marshal(cc.currentMemory)
		if err != nil {
		return fmt.Errorf("failed to marshal memory state: %s", err)
	}

	err = stub.PutState("currentMemory", memoryJSON)
		if err != nil {
		return fmt.Errorf("failed to save memory state: %s", err)
	}

	
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

	cc.ChangeMsgState(ctx, "Message_1q05nnw" ,ENABLE)


return nil
}	//编排任务的最后一个消息

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

	memoryJSON, err := json.Marshal(cc.currentMemory)
		if err != nil {
		return fmt.Errorf("failed to marshal memory state: %s", err)
	}

	err = stub.PutState("currentMemory", memoryJSON)
		if err != nil {
		return fmt.Errorf("failed to save memory state: %s", err)
	}


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

	cc.currentMemory.invoice = invoice
		memoryJSON, err := json.Marshal(cc.currentMemory)
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

	cc.ChangeGtwState(ctx, "ExclusiveGateway_0nzwv7v" ,ENABLE)


return nil
}	//编排任务的最后一个消息

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

        cc.ChangeMsgState(ctx, "Message_1ljlm4g" ,ENABLE)


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

	memoryJSON, err := json.Marshal(cc.currentMemory)
		if err != nil {
		return fmt.Errorf("failed to marshal memory state: %s", err)
	}

	err = stub.PutState("currentMemory", memoryJSON)
		if err != nil {
		return fmt.Errorf("failed to save memory state: %s", err)
	}


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

	memoryJSON, err := json.Marshal(cc.currentMemory)
		if err != nil {
		return fmt.Errorf("failed to marshal memory state: %s", err)
	}

	err = stub.PutState("currentMemory", memoryJSON)
		if err != nil {
		return fmt.Errorf("failed to save memory state: %s", err)
	}

	
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

	cc.ChangeGtwState(ctx, "Gateway_04h9e6e" ,ENABLE)


return nil
}	//编排任务的最后一个消息

