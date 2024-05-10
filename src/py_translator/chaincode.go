package chaincode


import (
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"reflect"
"github.com/hyperledger/fabric-contract-api-go/contractapi"
)


type SmartContract struct {
	contractapi.Contract
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
	currentMemory, err := cc.ReadState(ctx)
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

type StateMemory struct {
    Is_true bool `json:"Is_true"`
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

	cc.CreateActionEvent(ctx, "Event_0silmfa", ENABLED)

	cc.CreateActionEvent(ctx, "Event_01zd82j", DISABLED)
	cc.CreateMessage(ctx, "condition", "Participant_0nrc0gf", "Participant_0vpw1po", "", DISABLED, `{"properties":{"is_true":{"type":"boolean","description":""}},"required":[],"files":{},"file required":[]}`)
cc.CreateGateway(ctx, "Gateway_1kh9a59", DISABLED)

cc.CreateGateway(ctx, "Gateway_01t8bsf", DISABLED)

	stub.PutState("isInited", []byte("true"))

	stub.SetEvent("initContractEvent", []byte("Contract has been initialized successfully"))
	return nil
}


func (cc *SmartContract) Event_0silmfa(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	actionEvent, err := cc.ReadEvent(ctx, "Event_0silmfa")
	if err != nil {
		return err
	}

	if actionEvent.EventState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", actionEvent.EventID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

		cc.ChangeMsgState(ctx, "Event_0silmfa", COMPLETED)
	stub.SetEvent("Event_0silmfa", []byte("Contract has been started successfully"))
	
	    cc.ChangeGtwState(ctx, "Gateway_01t8bsf", ENABLED)
	
	return nil
}

func (cc *SmartContract) Message_0zut31s_Send(ctx contractapi.TransactionContextInterface, fireflyTranID string , Is_true bool) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_0zut31s")
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
	if msg.MsgState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	msg.MsgState = WAITINGFORCONFIRMATION
	msg.FireflyTranID = fireflyTranID
	msgJSON, _ := json.Marshal(msg)
	stub.PutState("Message_0zut31s", msgJSON)
	    cc.PutState(ctx, "Is_true", Is_true)
	stub.SetEvent("Message_0zut31s", []byte("Message is waiting for confirmation"))

	
	return nil
}

func (cc *SmartContract) Message_0zut31s_Complete(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, "Message_0zut31s")
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

	if msg.MsgState != WAITINGFORCONFIRMATION {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgState(ctx, "Message_0zut31s", COMPLETED)
	stub.SetEvent("Message_0zut31s", []byte("Message has been done"))

	
	    cc.ChangeGtwState(ctx, "Gateway_1kh9a59", ENABLED)

	
	return nil
}

func (cc *SmartContract) Gateway_1kh9a59(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	gtw, err := cc.ReadGtw(ctx, "Gateway_1kh9a59")
	if err != nil {
		return err
	}

	if gtw.GatewayState != ENABLED {
		errorMessage := fmt.Sprintf("Gateway state %s is not allowed", gtw.GatewayID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeGtwState(ctx, "Gateway_1kh9a59", COMPLETED)
	stub.SetEvent("Gateway_1kh9a59", []byte("ExclusiveGateway has been done"))

    
        currentMemory,err := cc.ReadState(ctx)
    if err != nil {
        return err
    }

if     Is_true:=currentMemory.Is_true

Is_true==false {
	    cc.ChangeGtwState(ctx, "Gateway_01t8bsf", ENABLED)
}
if     Is_true:=currentMemory.Is_true

Is_true==true {
	    cc.ChangeEventState(ctx, "Event_01zd82j", ENABLED)
}
    

	return nil
}

func (cc *SmartContract) Gateway_01t8bsf(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	gtw, err := cc.ReadGtw(ctx, "Gateway_01t8bsf")
	if err != nil {
		return err
	}

	if gtw.GatewayState != ENABLED {
		errorMessage := fmt.Sprintf("Gateway state %s is not allowed", gtw.GatewayID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeGtwState(ctx, "Gateway_01t8bsf", COMPLETED)
	stub.SetEvent("Gateway_01t8bsf", []byte("ExclusiveGateway has been done"))

    
        cc.ChangeMsgState(ctx, "Message_0zut31s", ENABLED)
    

	return nil
}

func (cc *SmartContract) Event_01zd82j(ctx contractapi.TransactionContextInterface) error {
	stub := ctx.GetStub()
	event, err := cc.ReadEvent(ctx, "Event_01zd82j")
	if err != nil {
		return err
	}

	if event.EventState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", event.EventID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeEventState(ctx, "Event_01zd82j", COMPLETED)
	stub.SetEvent("Event_01zd82j", []byte("EndEvent has been done"))
	
	return nil
}