package chaincode

import (
	"encoding/json"
	"errors"
	"fmt"
	"strconv"
	"reflect"
	"crypto/sha256"
	"encoding/hex"
	"github.com/hyperledger/fabric-chaincode-go/shim"
	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

// SmartContract is the main chaincode entry point.
type SmartContract struct {
	contractapi.Contract
}

// Core domain model ---------------------------------------------------------

type ContractInstance struct {
	// Incremental ID
	InstanceID string `json:"InstanceID"`
	// global Memory
	InstanceStateMemory StateMemory `json:"stateMemory"`
	// map type from string to Message、Gateway、ActionEvent
	InstanceMessages      map[string]*Message      `json:"InstanceMessages"`
	InstanceGateways      map[string]*Gateway      `json:"InstanceGateways"`
	InstanceActionEvents  map[string]*ActionEvent  `json:"InstanceActionEvents"`
	InstanceBusinessRules map[string]*BusinessRule `json:"InstanceBusinessRule"`
	InstanceParticipants  map[string]*Participant  `json:"InstanceParticipants"`
	// state of the instance
	InstanceState InstanceState `json:"InstanceState"`
}

type ElementState int

const (
	DISABLED = iota
	ENABLED
	WAITINGFORCONFIRMATION // means wait continue in BusinessRule
	COMPLETED
)

type InstanceState int

type Participant struct {
	ParticipantID string            `json:"ParticipantID"`
	MSP           string            `json:"MSP"`
	Attributes    map[string]string `json:"Attributes"`
	IsMulti       bool              `json:"IsMulti"`
	MultiMaximum  int               `json:"MultiMaximum"`
	MultiMinimum  int               `json:"MultiMinimum"`

	X509 string `json:"X509"`
}

type Message struct {
	MessageID            string       `json:"MessageID"`
	SendParticipantID    string       `json:"SendMspID"`
	ReceiveParticipantID string       `json:"ReceiveMspID"`
	FireflyTranID        string       `json:"FireflyTranID"`
	MsgState             ElementState `json:"MsgState"`
	Format               string       `json:"Format"`
}

type Gateway struct {
	GatewayID    string       `json:"GatewayID"`
	GatewayState ElementState `json:"GatewayState"`
}

type ActionEvent struct {
	EventID    string       `json:"EventID"`
	EventState ElementState `json:"EventState"`
}

type BusinessRule struct {
	BusinessRuleID string            `json:"BusinessRuleID"`
	Hash           string            `json:"Hash"`
	DecisionID     string            `json:"DecisionID"`
	ParamMapping   map[string]string `json:"ParamMapping"`
	State          ElementState      `json:"State"`
}

type StateMemory struct {
	AcceptedB bool `json:"AcceptedB"`
}

type InitParameters struct {
	ProviderB Participant `json:"ProviderB"`
	ClientB Participant `json:"ClientB"`
}

// Static helpers copied from the legacy snippet -----------------------------

func (cc *SmartContract) CreateBusinessRule(ctx contractapi.TransactionContextInterface, instance *ContractInstance, BusinessRuleID string, DMNContent string, DecisionID string, ParamMapping map[string]string) (*BusinessRule, error) {

	Hash, err := cc.hashXML(ctx, DMNContent)
	if err != nil {
		fmt.Println(err.Error())
		return nil, err
	}

	// 创建业务规则对象
	instance.InstanceBusinessRules[BusinessRuleID] = &BusinessRule{
		BusinessRuleID: BusinessRuleID,
		Hash:           Hash,
		DecisionID:     DecisionID,
		ParamMapping:   ParamMapping,
		State:          DISABLED,
	}

	returnBusinessRule, ok := instance.InstanceBusinessRules[BusinessRuleID]
	if !ok {
		return nil, fmt.Errorf("无法将实例元素转换为BusinessRule")
	}

	return returnBusinessRule, nil
}

func (cc *SmartContract) CreateParticipant(ctx contractapi.TransactionContextInterface, instance *ContractInstance, participantID string, msp string, attributes map[string]string, x509 string, IsMulti bool, MultiMaximum int, MultiMinimum int) (*Participant, error) {

	// 创建参与者对象
	instance.InstanceParticipants[participantID] = &Participant{
		ParticipantID: participantID,
		MSP:           msp,
		Attributes:    attributes,
		IsMulti:       IsMulti,
		MultiMaximum:  MultiMaximum,
		MultiMinimum:  MultiMinimum,
		X509:          x509,
	}

	returnParticipant, ok := instance.InstanceParticipants[participantID]
	if !ok {
		return nil, fmt.Errorf("无法将实例元素转换为Participant")
	}

	return returnParticipant, nil

}

func (cc *SmartContract) CreateMessage(ctx contractapi.TransactionContextInterface, instance *ContractInstance, messageID string, sendParticipantID string, receiveParticipantID string, fireflyTranID string, msgState ElementState, format string) (*Message, error) {

	// 创建消息对象
	instance.InstanceMessages[messageID] = &Message{
		MessageID:            messageID,
		SendParticipantID:    sendParticipantID,
		ReceiveParticipantID: receiveParticipantID,
		FireflyTranID:        fireflyTranID,
		MsgState:             msgState,
		Format:               format,
	}

	returnMessage, ok := instance.InstanceMessages[messageID]
	if !ok {
		return nil, fmt.Errorf("无法将实例元素转换为Message")
	}

	return returnMessage, nil
}

func (cc *SmartContract) CreateGateway(ctx contractapi.TransactionContextInterface, instance *ContractInstance, gatewayID string, gatewayState ElementState) (*Gateway, error) {

	// 创建网关对象
	instance.InstanceGateways[gatewayID] = &Gateway{
		GatewayID:    gatewayID,
		GatewayState: gatewayState,
	}

	returnGateway, ok := instance.InstanceGateways[gatewayID]
	if !ok {
		return nil, fmt.Errorf("无法将实例元素转换为Gateway")
	}

	return returnGateway, nil
}

func (cc *SmartContract) CreateActionEvent(ctx contractapi.TransactionContextInterface, instance *ContractInstance, eventID string, eventState ElementState) (*ActionEvent, error) {
	// 创建事件对象
	instance.InstanceActionEvents[eventID] = &ActionEvent{
		EventID:    eventID,
		EventState: eventState,
	}

	returnEvent, ok := instance.InstanceActionEvents[eventID]
	if !ok {
		return nil, fmt.Errorf("无法将实例元素转换为ActionEvent")
	}

	return returnEvent, nil

}

func (cc *SmartContract) GetInstance(ctx contractapi.TransactionContextInterface, instanceID string) (*ContractInstance, error) {
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

	return &instance, nil
}

func (cc *SmartContract) SetInstance(ctx contractapi.TransactionContextInterface, instance *ContractInstance) error {
	instanceJson, err := json.Marshal(instance)
	if err != nil {
		fmt.Println(err.Error())
		return err
	}

	err = ctx.GetStub().PutState(instance.InstanceID, instanceJson)
	if err != nil {
		fmt.Println(err.Error())
		return err
	}

	return nil
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

	msg, ok := instance.InstanceMessages[messageID]
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

	gtw, ok := instance.InstanceGateways[gatewayID]
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

	actionEvent, ok := instance.InstanceActionEvents[eventID]
	if !ok {
		errorMessage := fmt.Sprintf("Event %s does not exist", eventID)
		fmt.Println(errorMessage)
		return nil, errors.New(errorMessage)
	}

	return actionEvent, nil

}

// Change State  function
func (c *SmartContract) ChangeMsgState(ctx contractapi.TransactionContextInterface, instance *ContractInstance, messageID string, msgState ElementState) error {
	msg, ok := instance.InstanceMessages[messageID]
	if !ok {
		errorMessage := fmt.Sprintf("Message %s does not exist", messageID)
		fmt.Println(errorMessage)
		return errors.New(errorMessage)
	}
	msg.MsgState = msgState
	return nil
}

func (c *SmartContract) ChangeMsgFireflyTranID(ctx contractapi.TransactionContextInterface, instance *ContractInstance, fireflyTranID string, messageID string) error {
	msg, ok := instance.InstanceMessages[messageID]
	if !ok {
		errorMessage := fmt.Sprintf("Message %s does not exist", messageID)
		fmt.Println(errorMessage)
		return errors.New(errorMessage)
	}
	msg.FireflyTranID = fireflyTranID
	return nil

}

func (c *SmartContract) ChangeGtwState(ctx contractapi.TransactionContextInterface, instance *ContractInstance, gatewayID string, gtwState ElementState) error {
	gtw, ok := instance.InstanceGateways[gatewayID]
	if !ok {
		errorMessage := fmt.Sprintf("Gateway %s does not exist", gatewayID)
		fmt.Println(errorMessage)
		return errors.New(errorMessage)
	}
	gtw.GatewayState = gtwState
	return nil
}

func (c *SmartContract) ChangeEventState(ctx contractapi.TransactionContextInterface, instance *ContractInstance, eventID string, eventState ElementState) error {
	actionEvent, ok := instance.InstanceActionEvents[eventID]
	if !ok {
		errorMessage := fmt.Sprintf("Event %s does not exist", eventID)
		fmt.Println(errorMessage)
		return errors.New(errorMessage)
	}
	actionEvent.EventState = eventState
	return nil

}

func (cc *SmartContract) ChangeBusinessRuleState(ctx contractapi.TransactionContextInterface, instance *ContractInstance, BusinessRuleID string, state ElementState) error {
	businessRule, ok := instance.InstanceBusinessRules[BusinessRuleID]
	if !ok {
		errorMessage := fmt.Sprintf("BusinessRule %s does not exist", BusinessRuleID)
		fmt.Println(errorMessage)
		return errors.New(errorMessage)
	}
	businessRule.State = state
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
	for _, msg := range instance.InstanceMessages {
		messages = append(messages, msg)
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
	for _, gtw := range instance.InstanceGateways {
		gateways = append(gateways, gtw)
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
	for _, event := range instance.InstanceActionEvents {
		actionEvents = append(actionEvents, event)
	}

	return actionEvents, nil

}

func (cc *SmartContract) GetAllParticipants(ctx contractapi.TransactionContextInterface, instanceID string) ([]*Participant, error) {

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

	var participants []*Participant
	for _, participant := range instance.InstanceParticipants {
		participants = append(participants, participant)
	}

	return participants, nil

}

func (cc *SmartContract) GetAllBusinessRules(ctx contractapi.TransactionContextInterface, instanceID string) ([]*BusinessRule, error) {

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

	var businessRules []*BusinessRule
	for _, businessRule := range instance.InstanceBusinessRules {
		businessRules = append(businessRules, businessRule)
	}

	return businessRules, nil

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

func (cc *SmartContract) SetGlobalVariable(ctx contractapi.TransactionContextInterface, instance *ContractInstance, globalVariable *StateMemory) error {
	instance.InstanceStateMemory = *globalVariable
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

	businessRule, ok := instance.InstanceBusinessRules[BusinessRuleID]
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

	participant, ok := instance.InstanceParticipants[participantID]
	if !ok {
		errorMessage := fmt.Sprintf("Participant %s does not exist", participantID)
		fmt.Println(errorMessage)
		return nil, errors.New(errorMessage)
	}

	return participant, nil

}

// Don't use, since it not conform the rule of one commit one invoke
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

	instance.InstanceParticipants[participantID] = participant

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
	if targetParticipant.MSP != "" && !cc.check_msp(ctx, instanceID, target_participant) {
		return false
	}

	// check all attributes
	for key := range targetParticipant.Attributes {
		if !cc.check_attribute(ctx, instanceID, target_participant, key) {
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

	stub.PutState("currentInstanceID", []byte("0"))

	stub.PutState("isInited", []byte("true"))

	stub.SetEvent("initContractEvent", []byte("Contract has been initialized successfully"))
	return nil
}

func (s *SmartContract) hashXML(ctx contractapi.TransactionContextInterface, xmlString string) (string, error) {
	// Calculate SHA-256 hash
	hash := sha256.New()
	hash.Write([]byte(xmlString))
	hashInBytes := hash.Sum(nil)
	hashString := hex.EncodeToString(hashInBytes)
	fmt.Print(hashString)
	return hashString, nil
}

// State memory helpers ------------------------------------------------------

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

// Instance creation ---------------------------------------------------------

func (cc *SmartContract) CreateInstance(ctx contractapi.TransactionContextInterface, initParametersBytes string) (string, error) {
	stub := ctx.GetStub()

	isInitedBytes, err := stub.GetState("isInited")
	if err != nil {
		return "", fmt.Errorf("failed to read from world state. %s", err.Error())
	}

	if isInitedBytes == nil {
		return "", fmt.Errorf("The instance has not been initialized.")
	}

	isInited, err := strconv.ParseBool(string(isInitedBytes))

	if err != nil {
		return "", fmt.Errorf("fail To Resolve isInited")
	}
	if !isInited {
		return "", fmt.Errorf("The instance has not been initialized.")
	}

	// get the instanceID
	instanceIDBytes, err := stub.GetState("currentInstanceID")
	if err != nil {
		return "", fmt.Errorf("failed to read from world state. %s", err.Error())
	}

	instanceID := string(instanceIDBytes)

	// Create the instance with the data from the InitParameters
	var initParameters InitParameters
	err = json.Unmarshal([]byte(initParametersBytes), &initParameters)
	if err != nil {
		return "", fmt.Errorf("failed to unmarshal. %s", err.Error())
	}

	instance := ContractInstance{
		InstanceID:          instanceID,
		InstanceStateMemory: StateMemory{},
		InstanceMessages:    make(map[string]*Message),
		InstanceActionEvents: make(map[string]*ActionEvent),
		InstanceGateways:   make(map[string]*Gateway),
		InstanceParticipants: make(map[string]*Participant),
		InstanceBusinessRules: make(map[string]*BusinessRule),
	}

	// Update the currentInstanceID
	cc.CreateParticipant(ctx, &instance, "ProviderB", initParameters.ProviderB.MSP, initParameters.ProviderB.Attributes, initParameters.ProviderB.X509, initParameters.ProviderB.IsMulti, 0, 0)
	cc.CreateParticipant(ctx, &instance, "ClientB", initParameters.ClientB.MSP, initParameters.ClientB.Attributes, initParameters.ClientB.X509, initParameters.ClientB.IsMulti, 0, 0)
	cc.CreateActionEvent(ctx, &instance, "StartEvent_B", ENABLED)
	cc.CreateActionEvent(ctx, &instance, "EndEvent_B", DISABLED)
	cc.CreateMessage(ctx, &instance, "QuoteB", "ProviderB", "ClientB", "", DISABLED, `{"schema": "{}"}`)
	cc.CreateMessage(ctx, &instance, "AckB", "ClientB", "ProviderB", "", DISABLED, `{"schema": "{}"}`)
	cc.CreateGateway(ctx, &instance, "ChoiceB", DISABLED)

	// Save the instance
	instanceBytes, err := json.Marshal(instance)
	if err != nil {
		return "", fmt.Errorf("failed to marshal. %s", err.Error())
	}

	err = stub.PutState(instanceID, instanceBytes)
	if err != nil {
		return "", fmt.Errorf("failed to put state. %s", err.Error())
	}

	eventPayload := map[string]string{
		"InstanceID": instanceID,
	}

	eventPayloadAsBytes, err := json.Marshal(eventPayload)
	if err != nil {
		return "", fmt.Errorf("failed to marshal event payload: %v", err)
	}

	err = ctx.GetStub().SetEvent("InstanceCreated", eventPayloadAsBytes)
	if err != nil {
		return "", fmt.Errorf("failed to set event: %v", err)
	}

	instanceIDInt, err := strconv.Atoi(instanceID)
	if err != nil {
		return "", fmt.Errorf("failed to convert instanceID to int. %s", err.Error())
	}

	instanceIDInt++
	instanceID = strconv.Itoa(instanceIDInt)

	instanceIDBytes = []byte(instanceID)
	if err != nil {
		return "", fmt.Errorf("failed to marshal instanceID. %s", err.Error())
	}

	err = stub.PutState("currentInstanceID", instanceIDBytes)
	if err != nil {
		return "", fmt.Errorf("failed to put state. %s", err.Error())
	}

	return instanceID, nil

}


// Flow behaviour ------------------------------------------------------------

func (cc *SmartContract) StartEvent_B(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)

	actionEvent, err := cc.ReadEvent(ctx, instanceID, "StartEvent_B")
	if err != nil {
		return err
	}

	if actionEvent.EventState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", actionEvent.EventID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeEventState(ctx, instance, "StartEvent_B", COMPLETED)
	stub.SetEvent("StartEvent_B", []byte("Contract has been started successfully"))
	cc.SetInstance(ctx, instance)
	cc.ChangeMsgState(ctx, instance, "QuoteB", ENABLED)

	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) QuoteB_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "QuoteB")
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
	cc.ChangeMsgState(ctx, instance, "QuoteB", COMPLETED)

	stub.SetEvent("QuoteB", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) QuoteB_Complete(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "QuoteB")
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
	stub.SetEvent("QuoteB", []byte("Message has been done"))
	cc.SetInstance(ctx, instance)
	cc.ChangeGtwState(ctx, instance, "ChoiceB", ENABLED)

	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) AckB_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "AckB")
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
	cc.ChangeMsgState(ctx, instance, "AckB", COMPLETED)

	stub.SetEvent("AckB", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) AckB_Complete(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "AckB")
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
	stub.SetEvent("AckB", []byte("Message has been done"))
	cc.SetInstance(ctx, instance)
	cc.ChangeEventState(ctx, instance, "EndEvent_B", ENABLED)

	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) ChoiceB(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	gtw, err := cc.ReadGtw(ctx, instanceID, "ChoiceB")
	if err != nil {
		return err
	}

	if gtw.GatewayState != ENABLED {
		errorMessage := fmt.Sprintf("Gateway state %s is not allowed", gtw.GatewayID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}


	cc.ChangeGtwState(ctx, instance, gtw.GatewayID, COMPLETED)
	stub.SetEvent("ChoiceB", []byte("Gateway has been completed"))
	cc.SetInstance(ctx, instance)
	if instance.InstanceStateMemory.AcceptedB == true {
		cc.ChangeMsgState(ctx, instance, "AckB", ENABLED)
	} else {
		cc.ChangeEventState(ctx, instance, "EndEvent_B", ENABLED)
	}

	cc.SetInstance(ctx, instance)

	return nil
}

func (cc *SmartContract) EndEvent_B(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	actionEvent, err := cc.ReadEvent(ctx, instanceID, "EndEvent_B")
	if err != nil {
		return err
	}

	if actionEvent.EventState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", actionEvent.EventID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeEventState(ctx, instance, "EndEvent_B", COMPLETED)
	stub.SetEvent("EndEvent_B", []byte("Event has been completed"))
	cc.SetInstance(ctx, instance)
	cc.SetInstance(ctx, instance)
	return nil
}

// External integrations -----------------------------------------------------

func (cc *SmartContract) Invoke_Other_chaincode(ctx contractapi.TransactionContextInterface, chaincodeName string, channel string, _args [][]byte) ([]byte, error) {
	stub := ctx.GetStub()
	response := stub.InvokeChaincode(chaincodeName, _args, channel)

	if response.Status != shim.OK {
		return []byte(""), fmt.Errorf("failed to invoke chaincode. Response status: %d. Response message: %s", response.Status, response.Message)
	}

	fmt.Print("response.Payload: ")
	fmt.Println(string(response.Payload))

	return response.Payload, nil
}
