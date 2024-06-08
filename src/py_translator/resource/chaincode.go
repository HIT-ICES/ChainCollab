package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"strconv"
	"reflect"
	"github.com/hyperledger/fabric-chaincode-go/shim"
	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)


type SmartContract struct {
	contractapi.Contract
}


type StateMemory struct {
    Error bool `json:"Error"`
}

type InitParameters struct {
    Participant_1pasf6v Participant `json:"Participant_1pasf6v"`
	Participant_1tddbk5 Participant `json:"Participant_1tddbk5"`
	Activity_0ysk2q6 BusinessRule `json:"Activity_0ysk2q6"`
}

type ContractInstance struct {
	// Incremental ID
	InstanceID string `json:"InstanceID"`
	// global Memory
	InstanceStateMemory StateMemory `json:"stateMemory"`
	// map type from string to Message、Gateway、ActionEvent
	InstanceElements map[string]interface{} `json:"InstanceElements"`
	// state of the instance
	InstanceState InstanceState `json:"InstanceState"`
}

type ElementState int

const (
	DISABLED = iota
	ENABLED
	WAITINGFORCONFIRMATION
	COMPLETED
)

type InstanceState int

const (
	TOBEREGISTERED = iota
	READY
)

type Participant struct {
	MSP          string            `json:"msp"`
	Attributes   map[string]string `json:"attributes"`
	IsMulti      bool              `json:"isMulti"`
	MultiMaximum int               `json:"multiMaximum"`
	MultiMinimum int               `json:"multiMinimum"`

	X509 string `json:"x509"`
}

type Message struct {
	MessageID            string       `json:"messageID"`
	SendParticipantID    string       `json:"sendMspID"`
	ReceiveParticipantID string       `json:"receiveMspID"`
	FireflyTranID        string       `json:"fireflyTranID"`
	MsgState             ElementState `json:"msgState"`
	Format               string       `json:"format"`
}

type Gateway struct {
	GatewayID    string       `json:"gatewayID"`
	GatewayState ElementState `json:"gatewayState"`
}

type ActionEvent struct {
	EventID    string       `json:"eventID"`
	EventState ElementState `json:"eventState"`
}

type BusinessRule struct {
	CID          string            `json:"cid"`
	Hash         string            `json:"hash"`
	DecisionID   string            `json:"decisionId"`
	ParamMapping map[string]string `json:"mapping"`
	State        ElementState      `json:"state"`
}

func (cc *SmartContract) CreateBusinessRule(ctx contractapi.TransactionContextInterface, InstanceID string, BusinessRuleID string, CID string, Hash string, DecisionId string, ParamMapping map[string]string) (*BusinessRule, error) {
	stub := ctx.GetStub()

	existingData, err := stub.GetState(InstanceID)
	if err != nil {
		return nil, fmt.Errorf("获取状态数据时出错: %v", err)
	}
	if existingData == nil {
		return nil, fmt.Errorf("实例 %s 不存在", InstanceID)
	}

	// 从现有实例中读取
	var instance ContractInstance
	err = json.Unmarshal(existingData, &instance)
	if err != nil {
		return nil, fmt.Errorf("反序列化实例数据时出错: %v", err)
	}

	// 创建业务规则对象
	instance.InstanceElements[BusinessRuleID] = &BusinessRule{
		CID:          CID,
		Hash:         Hash,
		DecisionID:   "",
		ParamMapping: ParamMapping,
		State:        DISABLED,
	}

	instanceJson, err := json.Marshal(instance)
	if err != nil {
		return nil, fmt.Errorf("序列化实例数据时出错: %v", err)
	}
	// 将业务规则对象序列化为JSON字符串并保存在状态数据库中
	err = stub.PutState(InstanceID, instanceJson)
	if err != nil {
		return nil, fmt.Errorf("保存实例数据时出错: %v", err)
	}

	returnBusinessRule, ok := instance.InstanceElements[BusinessRuleID].(*BusinessRule)
	if !ok {
		return nil, fmt.Errorf("无法将实例元素转换为BusinessRule")
	}

	return returnBusinessRule, nil
}

func (cc *SmartContract) CreateParticipant(ctx contractapi.TransactionContextInterface, instanceID string, participantID string, msp string, attributes map[string]string, IsMulti bool, MultiMaximum int, MultiMinimum int) (*Participant, error) {
	stub := ctx.GetStub()

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

	// 创建参与者对象
	instance.InstanceElements[participantID] = &Participant{
		MSP:          msp,
		Attributes:   attributes,
		IsMulti:      IsMulti,
		MultiMaximum: MultiMaximum,
		MultiMinimum: MultiMinimum,
	}

	instanceJson, err := json.Marshal(instance)
	if err != nil {
		return nil, fmt.Errorf("序列化实例数据时出错: %v", err)
	}
	// 将参与者对象序列化为JSON字符串并保存在状态数据库中
	err = stub.PutState(instanceID, instanceJson)
	if err != nil {
		return nil, fmt.Errorf("保存实例数据时出错: %v", err)
	}

	returnParticipant, ok := instance.InstanceElements[participantID].(*Participant)
	if !ok {
		return nil, fmt.Errorf("无法将实例元素转换为Participant")
	}

	return returnParticipant, nil

}

func (cc *SmartContract) CreateMessage(ctx contractapi.TransactionContextInterface, instanceID string, messageID string, sendParticipantID string, receiveParticipantID string, fireflyTranID string, msgState ElementState, format string) (*Message, error) {
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
		MessageID:            messageID,
		SendParticipantID:    sendParticipantID,
		ReceiveParticipantID: receiveParticipantID,
		FireflyTranID:        fireflyTranID,
		MsgState:             msgState,
		Format:               format,
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

func (c *SmartContract) ChangeMsgFireflyTranID(ctx contractapi.TransactionContextInterface, instanceID string, messageID string, fireflyTranID string) error {

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

	msg.FireflyTranID = fireflyTranID

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

func (cc *SmartContract) ChangeBusinessRuleState(ctx contractapi.TransactionContextInterface, instanceID string, BusinessRuleID string, state ElementState) error {

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

	businessRule, ok := instance.InstanceElements[BusinessRuleID].(*BusinessRule)
	if !ok {
		errorMessage := fmt.Sprintf("BusinessRule %s does not exist", BusinessRuleID)
		fmt.Println(errorMessage)
		return errors.New(errorMessage)
	}

	businessRule.State = state

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

func (cc *SmartContract) ReadBusinessRule(ctx contractapi.TransactionContextInterface, instanceID string, BusinessRuleID string) (*BusinessRule, error) {
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

	businessRule, ok := instance.InstanceElements[BusinessRuleID].(*BusinessRule)
	if !ok {
		errorMessage := fmt.Sprintf("BusinessRule %s does not exist", BusinessRuleID)
		fmt.Println(errorMessage)
		return nil, errors.New(errorMessage)
	}

	return businessRule, nil
}

func (cc *SmartContract) ReadParticipant(ctx contractapi.TransactionContextInterface, instanceID string, participantID string) (*Participant, error) {

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

	participant, ok := instance.InstanceElements[participantID].(*Participant)
	if !ok {
		errorMessage := fmt.Sprintf("Participant %s does not exist", participantID)
		fmt.Println(errorMessage)
		return nil, errors.New(errorMessage)
	}

	return participant, nil

}

func (cc *SmartContract) WriteParticipant(ctx contractapi.TransactionContextInterface, instanceID string, participantID string, participant *Participant) error {
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

	instance.InstanceElements[participantID] = participant

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

func (cc *SmartContract) check_msp(ctx contractapi.TransactionContextInterface, instanceID string, target_participant string) bool {
	// Read the target participant's msp
	targetParticipant, err := cc.ReadParticipant(ctx, instanceID, target_participant)
	if err != nil {
		return false
	}
	mspID, err := ctx.GetClientIdentity().GetMSPID()
	if err != nil {
		return false
	}
	return mspID == targetParticipant.MSP
}

func (cc *SmartContract) check_attribute(ctx contractapi.TransactionContextInterface, instanceID string, target_participant string, attributeName string) bool {
	targetParticipant, err := cc.ReadParticipant(ctx, instanceID, target_participant)
	if err != nil {
		return false
	}
	if ctx.GetClientIdentity().AssertAttributeValue(attributeName, targetParticipant.Attributes[attributeName]) != nil {
		return false
	}

	return true
}

func (cc *SmartContract) check_participant(ctx contractapi.TransactionContextInterface, instanceID string, target_participant string) bool {
	// Read the target participant's msp
	targetParticipant, err := cc.ReadParticipant(ctx, instanceID, target_participant)
	if err != nil {
		return false
	}

	if !targetParticipant.IsMulti {
		// check X509 = MSPID + @ + ID
		mspID, _ := ctx.GetClientIdentity().GetMSPID()
		pid, _ := ctx.GetClientIdentity().GetID()
		if targetParticipant.X509 == pid+"@"+mspID {
			return true
		} else {
			return false
		}
	}

	// check MSP if msp!=''
	if targetParticipant.MSP != "" && cc.check_msp(ctx, instanceID, target_participant) == false {
		return false
	}

	// check all attributes
	for key, _ := range targetParticipant.Attributes {
		if cc.check_attribute(ctx, instanceID, target_participant, key) == false {
			return false
		}
	}

	return true
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


func (cc *SmartContract) CheckRegister(ctx contractapi.TransactionContextInterface, instanceID string) (bool, error) {
	stub := ctx.GetStub()

	// Check if the instance has been registered
	instanceBytes, err := stub.GetState(instanceID)
	if err != nil {
		return false, fmt.Errorf("Failed to read from world state. %s", err.Error())
	}
	var instance ContractInstance
	err = json.Unmarshal(instanceBytes, &instance)
	if err != nil {
		return false, fmt.Errorf("Failed to unmarshal. %s", err.Error())
	}

	if instance.InstanceState == READY {
		return true, nil
	}

	// set State depend on Participant with IsMulti=true

	for element, value := range instance.InstanceElements {
		participant, ok := value.(*Participant)
		if ok {
			if !participant.IsMulti && participant.X509 == "" {
				return false, fmt.Errorf("The participant %s is not registered.", element)
			}
		}
	}

	// set State depend on Participant with IsMulti=false
	instance.InstanceState = READY
	instanceBytes, err = json.Marshal(instance)
	if err != nil {
		return false, fmt.Errorf("Failed to marshal. %s", err.Error())
	}

	err = stub.PutState(instanceID, instanceBytes)
	if err != nil {
		return false, fmt.Errorf("Failed to put state. %s", err.Error())
	}

	return true, nil
}

func (cc *SmartContract) RegisterParticipant(ctx contractapi.TransactionContextInterface, instanceID string, targetParticipantID string) error {
	{
		// check if the participant is single
		var targetParticipant Participant
		participant, _ := cc.ReadParticipant(ctx, instanceID, targetParticipantID)
		if participant.IsMulti {
			{
				return fmt.Errorf("The participant is not multi")
			}
		}

		// check ACL

		if !cc.check_participant(ctx, instanceID, targetParticipantID) {
			return fmt.Errorf("The participant is not allowed to be registered")
		}

		// Read the identity of invoker ,and binding it's identity to the participant

		// Get the identity of the invoker
		invokerIdentity, err := ctx.GetClientIdentity().GetID()
		mspIndentity, err := ctx.GetClientIdentity().GetMSPID()

		X509 := invokerIdentity + "@" + mspIndentity

		// save the identity to the participant
		targetParticipant.X509 = X509

		// save the participant
		err = cc.WriteParticipant(ctx, instanceID, targetParticipantID, &targetParticipant)
		if err != nil {
			{
				return err
			}
		}

		return nil
	}
}

func (cc *SmartContract) Invoke_Other_chaincode(ctx contractapi.TransactionContextInterface, chaincodeName string, channel string, _args [][]byte) (string, error) {
	stub := ctx.GetStub()
	response := stub.InvokeChaincode(chaincodeName, _args, channel)

	if response.Status != shim.OK {
		return "", fmt.Errorf("failed to invoke chaincode. Response status: %d. Response message: %s", response.Status, response.Message)
	}

	fmt.Print("response.Payload: ")
	fmt.Println(string(response.Payload))

	return string(response.Payload), nil
}

func (cc *SmartContract) CreateInstance(ctx contractapi.TransactionContextInterface, initParametersBytes string) (string, error) {
	stub := ctx.GetStub()

	isInitedBytes, err := stub.GetState("isInited")
	if err != nil {
		return "", fmt.Errorf("Failed to read from world state. %s", err.Error())
	}

	if isInitedBytes != nil {
		return "", fmt.Errorf("The instance has been initialized.")
	}

	var isInited bool
	err = json.Unmarshal(isInitedBytes, &isInited)
	if err != nil {
		return "", fmt.Errorf("Failed to unmarshal. %s", err.Error())
	}

	if !isInited {
		return "", fmt.Errorf("The instance has not been initialized.")
	}

	// get the instanceID

	var instanceID string
	instanceIDString, err := stub.GetState("currentInstanceID")
	if err != nil {
		return "", fmt.Errorf("Failed to read from world state. %s", err.Error())
	}

	err = json.Unmarshal(instanceIDString, &instanceID)
	if err != nil {
		return "", fmt.Errorf("Failed to unmarshal. %s", err.Error())
	}

	// Create the instance with the data from the InitParameters
	var initParameters InitParameters
	err = json.Unmarshal([]byte(initParametersBytes), &initParameters)
	if err != nil {
		return "", fmt.Errorf("Failed to unmarshal. %s", err.Error())
	}

	instance := ContractInstance{
		InstanceID:          instanceID,
		InstanceStateMemory: StateMemory{},
		InstanceElements:    make(map[string]interface{}),
	}

	// Save the instance
	instanceBytes, err := json.Marshal(instance)
	if err != nil {
		return "", fmt.Errorf("Failed to marshal. %s", err.Error())
	}

	err = stub.PutState(instanceID, instanceBytes)
	if err != nil {
		return "", fmt.Errorf("Failed to put state. %s", err.Error())
	}

	// Update the currentInstanceID

		cc.CreateParticipant(ctx, instanceID, "Participant_1pasf6v", initParameters.Participant_1pasf6v.MSP, initParameters.Participant_1pasf6v.Attributes, false, 0, 0)
	cc.CreateParticipant(ctx, instanceID, "Participant_1tddbk5", initParameters.Participant_1tddbk5.MSP, initParameters.Participant_1tddbk5.Attributes, false, 0, 0)
	cc.CreateActionEvent(ctx, instanceID, "StartEvent_1v2ab61", ENABLED)

	cc.CreateActionEvent(ctx, instanceID, "EndEvent_17h95ah", DISABLED)

	cc.CreateMessage(ctx, instanceID, "Message_1j4s0qh", "Participant_1tddbk5", "Participant_1pasf6v", "", DISABLED, `{}`)
	cc.CreateMessage(ctx, instanceID, "Message_0gg08bf", "Participant_1tddbk5", "Participant_1pasf6v", "", DISABLED, `{}`)
	cc.CreateMessage(ctx, instanceID, "Message_0i0xp6a", "Participant_1pasf6v", "Participant_1tddbk5", "", DISABLED, `{}`)
	cc.CreateMessage(ctx, instanceID, "Message_1uiozoi", "Participant_1tddbk5", "Participant_1pasf6v", "", DISABLED, `{}`)
	cc.CreateMessage(ctx, instanceID, "Message_1e90tfn", "Participant_1pasf6v", "Participant_1tddbk5", "", DISABLED, `{"properties":{"error":{"type":"boolean","description":""}},"required":[],"files":{},"file required":[]}`)
	cc.CreateGateway(ctx, instanceID, "ExclusiveGateway_0c8hy9b", DISABLED)

	cc.CreateGateway(ctx, instanceID, "ExclusiveGateway_1sp1v7s", DISABLED)

cc.CreateBusinessRule(ctx, instanceID, "Activity_0ysk2q6", initParameters.Activity_0ysk2q6.CID, initParameters.Activity_0ysk2q6.Hash, initParameters.Activity_0ysk2q6.DecisionID, initParameters.Activity_0ysk2q6.ParamMapping)

	instanceIDInt, err := strconv.Atoi(instanceID)
	if err != nil {
		return "", fmt.Errorf("Failed to convert instanceID to int. %s", err.Error())
	}

	instanceIDInt++
	instanceID = strconv.Itoa(instanceIDInt)

	instanceIDBytes, err := json.Marshal(instanceID)
	if err != nil {
		return "", fmt.Errorf("Failed to marshal instanceID. %s", err.Error())
	}

	err = stub.PutState("currentInstanceID", instanceIDBytes)
	if err != nil {
		return "", fmt.Errorf("Failed to put state. %s", err.Error())
	}

	return instanceID, nil

}

func (cc *SmartContract) StartEvent_1v2ab61(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	isRegistered, err := cc.CheckRegister(ctx, instanceID)
	if !isRegistered {
		errorMessage := fmt.Sprintf("Instance %s is not registered fully", instanceID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}


	actionEvent, err := cc.ReadEvent(ctx, instanceID, "StartEvent_1v2ab61")
	if err != nil {
		return err
	}

	if actionEvent.EventState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", actionEvent.EventID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeEventState(ctx, instanceID, "StartEvent_1v2ab61", COMPLETED)
	stub.SetEvent("StartEvent_1v2ab61", []byte("Contract has been started successfully"))
	
	    cc.ChangeGtwState(ctx, instanceID, "ExclusiveGateway_1sp1v7s", ENABLED)
	
	return nil
}

func (cc *SmartContract) Message_1e90tfn_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string , Error bool) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1e90tfn")
	if err != nil {
		return err
	}

	//
	if cc.check_participant(ctx, instanceID, msg.SendParticipantID) == false{
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != ENABLED {
		errorMessage := fmt.Sprintf("Message state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgFireflyTranID(ctx, instanceID, fireflyTranID, msg.MessageID)
	cc.ChangeMsgState(ctx, instanceID, msg.MessageID, WAITINGFORCONFIRMATION)
		globalMemory,readGloabolError := cc.ReadGlobalVariable(ctx, instanceID)
	if readGloabolError != nil {
		fmt.Println(readGloabolError.Error())
		return readGloabolError
	}
	globalMemory.Error = Error
	setGloabolErrror :=cc.SetGlobalVariable(ctx, instanceID, globalMemory)
	if setGloabolErrror != nil {
		fmt.Println(setGloabolErrror.Error())
		return setGloabolErrror
	}
	stub.SetEvent("Message_1e90tfn", []byte("Message is waiting for confirmation"))

	
	return nil
}

func (cc *SmartContract) Message_1e90tfn_Complete(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1e90tfn")
	if err != nil {
		return err
	}

	if cc.check_participant(ctx, instanceID, msg.ReceiveParticipantID) == false{
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != WAITINGFORCONFIRMATION {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgState(ctx, instanceID, msg.MessageID, COMPLETED)
	stub.SetEvent("Message_1e90tfn", []byte("Message has been done"))

	
	    cc.ChangeMsgState(ctx, instanceID, "Message_1uiozoi", ENABLED)

	
	return nil
}

func (cc *SmartContract) Message_1uiozoi_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string ) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1uiozoi")
	if err != nil {
		return err
	}

	//
	if cc.check_participant(ctx, instanceID, msg.SendParticipantID) == false{
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != ENABLED {
		errorMessage := fmt.Sprintf("Message state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgFireflyTranID(ctx, instanceID, fireflyTranID, msg.MessageID)
	cc.ChangeMsgState(ctx, instanceID, msg.MessageID, WAITINGFORCONFIRMATION)
	
	stub.SetEvent("Message_1uiozoi", []byte("Message is waiting for confirmation"))

	
	return nil
}

func (cc *SmartContract) Message_1uiozoi_Complete(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1uiozoi")
	if err != nil {
		return err
	}

	if cc.check_participant(ctx, instanceID, msg.ReceiveParticipantID) == false{
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != WAITINGFORCONFIRMATION {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgState(ctx, instanceID, msg.MessageID, COMPLETED)
	stub.SetEvent("Message_1uiozoi", []byte("Message has been done"))

	
	    cc.ChangeMsgState(ctx, instanceID, "Message_0i0xp6a", ENABLED)

	
	return nil
}

func (cc *SmartContract) Message_0i0xp6a_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string ) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_0i0xp6a")
	if err != nil {
		return err
	}

	//
	if cc.check_participant(ctx, instanceID, msg.SendParticipantID) == false{
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != ENABLED {
		errorMessage := fmt.Sprintf("Message state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgFireflyTranID(ctx, instanceID, fireflyTranID, msg.MessageID)
	cc.ChangeMsgState(ctx, instanceID, msg.MessageID, WAITINGFORCONFIRMATION)
	
	stub.SetEvent("Message_0i0xp6a", []byte("Message is waiting for confirmation"))

	
	return nil
}

func (cc *SmartContract) Message_0i0xp6a_Complete(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_0i0xp6a")
	if err != nil {
		return err
	}

	if cc.check_participant(ctx, instanceID, msg.ReceiveParticipantID) == false{
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != WAITINGFORCONFIRMATION {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgState(ctx, instanceID, msg.MessageID, COMPLETED)
	stub.SetEvent("Message_0i0xp6a", []byte("Message has been done"))

	
	    cc.ChangeMsgState(ctx, instanceID, "Message_0gg08bf", ENABLED)

	
	return nil
}

func (cc *SmartContract) Message_0gg08bf_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string ) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_0gg08bf")
	if err != nil {
		return err
	}

	//
	if cc.check_participant(ctx, instanceID, msg.SendParticipantID) == false{
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != ENABLED {
		errorMessage := fmt.Sprintf("Message state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgFireflyTranID(ctx, instanceID, fireflyTranID, msg.MessageID)
	cc.ChangeMsgState(ctx, instanceID, msg.MessageID, WAITINGFORCONFIRMATION)
	
	stub.SetEvent("Message_0gg08bf", []byte("Message is waiting for confirmation"))

	
	return nil
}

func (cc *SmartContract) Message_0gg08bf_Complete(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_0gg08bf")
	if err != nil {
		return err
	}

	if cc.check_participant(ctx, instanceID, msg.ReceiveParticipantID) == false{
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != WAITINGFORCONFIRMATION {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgState(ctx, instanceID, msg.MessageID, COMPLETED)
	stub.SetEvent("Message_0gg08bf", []byte("Message has been done"))

	
	    cc.ChangeMsgState(ctx, instanceID, "Message_1j4s0qh", ENABLED)

	
	return nil
}

func (cc *SmartContract) Message_1j4s0qh_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string ) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1j4s0qh")
	if err != nil {
		return err
	}

	//
	if cc.check_participant(ctx, instanceID, msg.SendParticipantID) == false{
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != ENABLED {
		errorMessage := fmt.Sprintf("Message state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgFireflyTranID(ctx, instanceID, fireflyTranID, msg.MessageID)
	cc.ChangeMsgState(ctx, instanceID, msg.MessageID, WAITINGFORCONFIRMATION)
	
	stub.SetEvent("Message_1j4s0qh", []byte("Message is waiting for confirmation"))

	
	return nil
}

func (cc *SmartContract) Message_1j4s0qh_Complete(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1j4s0qh")
	if err != nil {
		return err
	}

	if cc.check_participant(ctx, instanceID, msg.ReceiveParticipantID) == false{
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if msg.MsgState != WAITINGFORCONFIRMATION {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeMsgState(ctx, instanceID, msg.MessageID, COMPLETED)
	stub.SetEvent("Message_1j4s0qh", []byte("Message has been done"))

	
	    cc.ChangeGtwState(ctx, instanceID, "ExclusiveGateway_0c8hy9b", ENABLED)

	
	return nil
}

func (cc *SmartContract) ExclusiveGateway_0c8hy9b(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	gtw, err := cc.ReadGtw(ctx, instanceID, "ExclusiveGateway_0c8hy9b")
	if err != nil {
		return err
	}

	if gtw.GatewayState != ENABLED {
		errorMessage := fmt.Sprintf("Gateway state %s is not allowed", gtw.GatewayID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeGtwState(ctx, instanceID, gtw.GatewayID, COMPLETED)
	stub.SetEvent("ExclusiveGateway_0c8hy9b", []byte("ExclusiveGateway has been done"))

    
    	currentMemory, err := cc.ReadGlobalVariable(ctx, instanceID)
	if err != nil {
		return err
	}

    Error:=currentMemory.Error

if Error==true {
	    cc.ChangeGtwState(ctx, instanceID, "ExclusiveGateway_1sp1v7s", ENABLED)
}
if Error==false {
	    cc.ChangeEventState(ctx, instanceID, "EndEvent_17h95ah", ENABLED)
}
    

	return nil
}

func (cc *SmartContract) ExclusiveGateway_1sp1v7s(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	gtw, err := cc.ReadGtw(ctx, instanceID, "ExclusiveGateway_1sp1v7s")
	if err != nil {
		return err
	}

	if gtw.GatewayState != ENABLED {
		errorMessage := fmt.Sprintf("Gateway state %s is not allowed", gtw.GatewayID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeGtwState(ctx, instanceID, gtw.GatewayID, COMPLETED)
	stub.SetEvent("ExclusiveGateway_1sp1v7s", []byte("ExclusiveGateway has been done"))

    
        cc.ChangeMsgState(ctx, instanceID, "Activity_0ysk2q6", ENABLED)
    

	return nil
}

func (cc *SmartContract) EndEvent_17h95ah(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	event, err := cc.ReadEvent(ctx, instanceID, "EndEvent_17h95ah")
	if err != nil {
		return err
	}

	if event.EventState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", event.EventID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeEventState(ctx, instanceID, event.EventID, COMPLETED) 
	stub.SetEvent("EndEvent_17h95ah", []byte("EndEvent has been done"))
	
	return nil
}

func (cc *SmartContract) Activity_0ysk2q6(ctx contractapi.TransactionContextInterface, instanceID string, ContentOfDmn string) error {

	// Read Business Info
	businessRule, err := cc.ReadBusinessRule(ctx, instanceID, "Activity_0ysk2q6")
	if err != nil {
		return err
	}

	// Check the BusinessRule State
	if businessRule.State != ENABLED {
		return fmt.Errorf("The BusinessRule is not ENABLED")
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
		field := reflect.ValueOf(globalVariable).FieldByName(value)
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
	var resJson string
	resJson, err=cc.Invoke_Other_chaincode(ctx, "asset:v1","default", _args)

	// Set the Result
	var res map[string]interface{}
	err = json.Unmarshal([]byte(resJson), &res)
	if err != nil {
		return err
	}

	for key, value := range res {
		field := reflect.ValueOf(globalVariable).FieldByName(key)
		if !field.IsValid() {
			return fmt.Errorf("The field %s is not valid", key)
		}
		field.Set(reflect.ValueOf(value))
	}

	// Update the GlobalVariable
	err = cc.SetGlobalVariable(ctx, instanceID, globalVariable)

	// Change the BusinessRule State
	cc.ChangeBusinessRuleState(ctx, instanceID, "Activity_0ysk2q6", COMPLETED)

    
        cc.ChangeMsgState(ctx, instanceID, "Message_1e90tfn", ENABLED)
    

	return nil
}