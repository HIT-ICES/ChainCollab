package chaincode


import (
	"encoding/json"
	"errors"
	"fmt"
	"strconv"
	"reflect"
	"crypto/sha256"
	"strings"
	"encoding/hex"
	"github.com/hyperledger/fabric-chaincode-go/shim"
	"github.com/hyperledger/fabric-contract-api-go/contractapi"
	"IBC/Oracle/oracle"
)


type SmartContract struct {
	contractapi.Contract
}


type StateMemory struct {
    NumberOfUnits int `json:"NumberOfUnits"`
	Urgent bool `json:"Urgent"`
	SupplierReputation int `json:"SupplierReputation"`
	FinalPriority string `json:"FinalPriority"`
}

type InitParameters struct {
    Participant_0w6qkdf Participant `json:"Participant_0w6qkdf"`
	Participant_19mgbdn Participant `json:"Participant_19mgbdn"`
	Participant_09cjol2 Participant `json:"Participant_09cjol2"`
	Participant_0sa2v7d Participant `json:"Participant_0sa2v7d"`
	Participant_19j1e3o Participant `json:"Participant_19j1e3o"`
	Activity_0rm8bkp_DecisionID string `json:"Activity_0rm8bkp_DecisionID"`
	Activity_0rm8bkp_ParamMapping map[string]string `json:"Activity_0rm8bkp_ParamMapping"`
	Activity_0rm8bkp_Content string `json:"Activity_0rm8bkp_Content"`
}

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
	for key, _ := range targetParticipant.Attributes {
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

// func (s *SmartContract) UpdateCID(ctx contractapi.TransactionContextInterface, instanceID string, BusinessRuleID string, cid string) error {
// 	instanceBytes, err := ctx.GetStub().GetState(instanceID)
// 	if err != nil {
// 		return fmt.Errorf("failed to read from world state: %v", err)
// 	}
// 	if instanceBytes == nil {
// 		return fmt.Errorf("the record %s does not exist", instanceID)
// 	}

// 	// Unmarshal the JSON to a Instance
// 	var instance ContractInstance
// 	err = json.Unmarshal(instanceBytes, &instance)

// 	if err != nil {
// 		return fmt.Errorf("failed to unmarshal JSON: %v", err)
// 	}
// 	// Update the Cid field
// 	instance.InstanceBusinessRules[BusinessRuleID].CID = cid

// 	// Marshal the updated struct to JSON
// 	instanceBytes, err = json.Marshal(instance)
// 	if err != nil {
// 		return fmt.Errorf("failed to marshal JSON: %v", err)
// 	}

// 	// Put the updated record back into the ledger
// 	err = ctx.GetStub().PutState(instanceID, instanceBytes)
// 	if err != nil {
// 		return fmt.Errorf("failed to update record in world state: %v", err)
// 	}

// 	return nil
// }


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
		InstanceGateways: make(map[string]*Gateway),
		InstanceParticipants : make(map[string]*Participant),
		InstanceBusinessRules: make(map[string]*BusinessRule),
	}

	// Update the currentInstanceID

		cc.CreateParticipant(ctx, &instance, "Participant_0w6qkdf", initParameters.Participant_0w6qkdf.MSP, initParameters.Participant_0w6qkdf.Attributes, initParameters.Participant_0w6qkdf.X509,initParameters.Participant_0w6qkdf.IsMulti, 0, 0)
	cc.CreateParticipant(ctx, &instance, "Participant_19mgbdn", initParameters.Participant_19mgbdn.MSP, initParameters.Participant_19mgbdn.Attributes, initParameters.Participant_19mgbdn.X509,initParameters.Participant_19mgbdn.IsMulti, 0, 0)
	cc.CreateParticipant(ctx, &instance, "Participant_09cjol2", initParameters.Participant_09cjol2.MSP, initParameters.Participant_09cjol2.Attributes, initParameters.Participant_09cjol2.X509,initParameters.Participant_09cjol2.IsMulti, 0, 0)
	cc.CreateParticipant(ctx, &instance, "Participant_0sa2v7d", initParameters.Participant_0sa2v7d.MSP, initParameters.Participant_0sa2v7d.Attributes, initParameters.Participant_0sa2v7d.X509,initParameters.Participant_0sa2v7d.IsMulti, 0, 0)
	cc.CreateParticipant(ctx, &instance, "Participant_19j1e3o", initParameters.Participant_19j1e3o.MSP, initParameters.Participant_19j1e3o.Attributes, initParameters.Participant_19j1e3o.X509,initParameters.Participant_19j1e3o.IsMulti, 0, 0)
	cc.CreateActionEvent(ctx, &instance, "Event_06sexe6", ENABLED)

	cc.CreateActionEvent(ctx, &instance, "Event_13pbqdz", DISABLED)

	cc.CreateMessage(ctx, &instance, "Message_1dmeexg", "Participant_19j1e3o", "Participant_19mgbdn", "", DISABLED, `{}`)
	cc.CreateMessage(ctx, &instance, "Message_1dzkcn0", "Participant_19j1e3o", "Participant_19mgbdn", "", DISABLED, `{}`)
	cc.CreateMessage(ctx, &instance, "Message_1oxmq1k", "Participant_19j1e3o", "Participant_19mgbdn", "", DISABLED, `{}`)
	cc.CreateMessage(ctx, &instance, "Message_1amf6l2", "Participant_0sa2v7d", "Participant_19j1e3o", "", DISABLED, `{}`)
	cc.CreateMessage(ctx, &instance, "Message_196q1fj", "Participant_19mgbdn", "Participant_0w6qkdf", "", DISABLED, `{"properties":{},"required":[],"files":{"deliveryNote":{"type":"file","description":"A document confirming the delivery of goods"}},"file required":["deliveryNote"]}`)
	cc.CreateMessage(ctx, &instance, "Message_04wmlqe", "Participant_19mgbdn", "Participant_0w6qkdf", "", DISABLED, `{"properties":{"productionStart":{"type":"string","description":"Notification of the commencement of production, including the date and time"}},"required":["productionStart"],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_1slt8tv", "Participant_0w6qkdf", "Participant_19mgbdn", "", DISABLED, `{}`)
	cc.CreateMessage(ctx, &instance, "Message_1yv2h4e", "Participant_0w6qkdf", "Participant_19mgbdn", "", DISABLED, `{}`)
	cc.CreateMessage(ctx, &instance, "Message_0d2xte5", "Participant_19j1e3o", "Participant_19mgbdn", "", DISABLED, `{"properties":{"deliveryConfirmation":{"type":"boolean","description":"Confirmation of whether the supplies have been successfully delivered"}},"required":["deliveryConfirmation"],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_1io2g9u", "Participant_0sa2v7d", "Participant_19j1e3o", "", DISABLED, `{"properties":{},"required":[],"files":{"waybill":{"type":"file","description":"Digital or physical waybill document，detailing the shipment contents and destination."}},"file required":["waybill"]}`)
	cc.CreateMessage(ctx, &instance, "Message_0hpha6h", "Participant_0sa2v7d", "Participant_19j1e3o", "", DISABLED, `{"properties":{"requestId":{"type":"number","description":"Unique identifier of the request for additional details "},"supplierReputation":{"type":"number","description":"A numerical rating representing the supplier's reputation."}},"required":["requestId","supplierReputation"],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_0rwz1km", "Participant_19j1e3o", "Participant_0sa2v7d", "", DISABLED, `{"properties":{"requestId":{"type":"number","description":" Unique identifier of the request for additional details "},"numberOfUnits":{"type":"number","description":" Total number of units in the order requested"},"urgent":{"type":"boolean","description":"Indicates whether the order requires urgent delivery."}},"required":["requestId","numberOfUnits","urgent"],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_0pm90nx", "Participant_09cjol2", "Participant_19j1e3o", "", DISABLED, `{"properties":{"transportOrderId":{"type":"string","description":"Identifier of the transport order being forwarded"}},"required":["transportOrderId"],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_0cba4t6", "Participant_09cjol2", "Participant_0sa2v7d", "", DISABLED, `{"properties":{"supplyOrderId":{"type":"string","description":" Identifier of the supply order being forwarded"}},"required":["supplyOrderId"],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_1ajdm9l", "Participant_19mgbdn", "Participant_09cjol2", "", DISABLED, `{"properties":{"supplyOrderDetails":{"type":"string","description":" Details of the supplies needed"}},"required":["supplyOrderDetails"],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_1wswgqu", "Participant_0w6qkdf", "Participant_19mgbdn", "", DISABLED, `{"properties":{"orderDetails":{"type":"string","description":"Detailed list of goods ordered"}},"required":["orderDetails"],"files":{},"file required":[]}`)
	cc.CreateGateway(ctx, &instance, "Gateway_1cr0nma", DISABLED)

	cc.CreateGateway(ctx, &instance, "Gateway_0ep8cuh", DISABLED)

	cc.CreateGateway(ctx, &instance, "Gateway_0onpe6x", DISABLED)

	cc.CreateGateway(ctx, &instance, "Gateway_1fbifca", DISABLED)

	cc.CreateBusinessRule(ctx, &instance, "Activity_0rm8bkp", initParameters.Activity_0rm8bkp_Content, initParameters.Activity_0rm8bkp_DecisionID, initParameters.Activity_0rm8bkp_ParamMapping)

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
		"Activity_0rm8bkp" : initParameters.Activity_0rm8bkp_Content,
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

func (cc *SmartContract) Message_1wswgqu_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string ) error {
	stub := ctx.GetStub()
	instance,err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1wswgqu")
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

	cc.ChangeMsgFireflyTranID(ctx, instance, fireflyTranID, msg.MessageID)
	    cc.ChangeMsgState(ctx, instance, "Message_1wswgqu", COMPLETED)
	
	stub.SetEvent("Message_1wswgqu", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	
	
	    cc.ChangeMsgState(ctx, instance, "Message_1ajdm9l", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_1ajdm9l_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string ) error {
	stub := ctx.GetStub()
	instance,err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1ajdm9l")
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

	cc.ChangeMsgFireflyTranID(ctx, instance, fireflyTranID, msg.MessageID)
	    cc.ChangeMsgState(ctx, instance, "Message_1ajdm9l", COMPLETED)
	
	stub.SetEvent("Message_1ajdm9l", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	
	
	    cc.ChangeGtwState(ctx, instance, "Gateway_0onpe6x", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

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
	stub.SetEvent("Gateway_0onpe6x", []byte("Gateway has been done"))
	cc.SetInstance(ctx, instance)
	

	    cc.ChangeMsgState(ctx, instance, "Message_0cba4t6", ENABLED)
    cc.ChangeMsgState(ctx, instance, "Message_0pm90nx", ENABLED)
	cc.SetInstance(ctx, instance)

	return nil
}

func (cc *SmartContract) Message_0cba4t6_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string ) error {
	stub := ctx.GetStub()
	instance,err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_0cba4t6")
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

	cc.ChangeMsgFireflyTranID(ctx, instance, fireflyTranID, msg.MessageID)
	    cc.ChangeMsgState(ctx, instance, "Message_0cba4t6", COMPLETED)
	
	stub.SetEvent("Message_0cba4t6", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	
	if !(func() bool { msg, err := cc.ReadMsg(ctx, instanceID, "Message_0pm90nx"); return err == nil && msg.MsgState == COMPLETED }()) {
	return nil
}
	    cc.ChangeGtwState(ctx, instance, "Gateway_1fbifca", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_0pm90nx_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string ) error {
	stub := ctx.GetStub()
	instance,err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_0pm90nx")
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

	cc.ChangeMsgFireflyTranID(ctx, instance, fireflyTranID, msg.MessageID)
	    cc.ChangeMsgState(ctx, instance, "Message_0pm90nx", COMPLETED)
	
	stub.SetEvent("Message_0pm90nx", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	
	if !(func() bool { msg, err := cc.ReadMsg(ctx, instanceID, "Message_0cba4t6"); return err == nil && msg.MsgState == COMPLETED }()) {
	return nil
}
	    cc.ChangeGtwState(ctx, instance, "Gateway_1fbifca", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Gateway_1fbifca(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance,err := cc.GetInstance(ctx, instanceID)
	gtw, err := cc.ReadGtw(ctx, instanceID, "Gateway_1fbifca")
	if err != nil {
		return err
	}

	if gtw.GatewayState != ENABLED {
		errorMessage := fmt.Sprintf("Gateway state %s is not allowed", gtw.GatewayID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeGtwState(ctx, instance, gtw.GatewayID, COMPLETED)
	stub.SetEvent("Gateway_1fbifca", []byte("Gateway has been done"))

	
	    cc.ChangeMsgState(ctx, instance, "Message_0rwz1km", ENABLED)
	
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_0rwz1km_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string , NumberOfUnits int, Urgent bool) error {
	stub := ctx.GetStub()
	instance,err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_0rwz1km")
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

	cc.ChangeMsgFireflyTranID(ctx, instance, fireflyTranID, msg.MessageID)
	    cc.ChangeMsgState(ctx, instance, "Message_0rwz1km", COMPLETED)
		globalMemory,readGloabolError := cc.ReadGlobalVariable(ctx, instanceID)
	if readGloabolError != nil {
		fmt.Println(readGloabolError.Error())
		return readGloabolError
	}
		globalMemory.NumberOfUnits = NumberOfUnits
	globalMemory.Urgent = Urgent
	setGloabolErrror :=cc.SetGlobalVariable(ctx, instance, globalMemory)
	if setGloabolErrror != nil {
		fmt.Println(setGloabolErrror.Error())
		return setGloabolErrror
	}
	stub.SetEvent("Message_0rwz1km", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	
	
	    cc.ChangeMsgState(ctx, instance, "Message_1amf6l2", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_1amf6l2_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string ) error {
	stub := ctx.GetStub()
	instance,err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1amf6l2")
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

	cc.ChangeMsgFireflyTranID(ctx, instance, fireflyTranID, msg.MessageID)
	    cc.ChangeMsgState(ctx, instance, "Message_1amf6l2", COMPLETED)
	
	stub.SetEvent("Message_1amf6l2", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	
	
	    cc.ChangeMsgState(ctx, instance, "Message_0hpha6h", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_0hpha6h_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string , SupplierReputation int) error {
	stub := ctx.GetStub()
	instance,err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_0hpha6h")
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

	cc.ChangeMsgFireflyTranID(ctx, instance, fireflyTranID, msg.MessageID)
	    cc.ChangeMsgState(ctx, instance, "Message_0hpha6h", COMPLETED)
		globalMemory,readGloabolError := cc.ReadGlobalVariable(ctx, instanceID)
	if readGloabolError != nil {
		fmt.Println(readGloabolError.Error())
		return readGloabolError
	}
		globalMemory.SupplierReputation = SupplierReputation
	setGloabolErrror :=cc.SetGlobalVariable(ctx, instance, globalMemory)
	if setGloabolErrror != nil {
		fmt.Println(setGloabolErrror.Error())
		return setGloabolErrror
	}
	stub.SetEvent("Message_0hpha6h", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	
	
	    cc.ChangeMsgState(ctx, instance, "Message_1io2g9u", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_1io2g9u_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string ) error {
	stub := ctx.GetStub()
	instance,err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1io2g9u")
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

	cc.ChangeMsgFireflyTranID(ctx, instance, fireflyTranID, msg.MessageID)
	    cc.ChangeMsgState(ctx, instance, "Message_1io2g9u", COMPLETED)
	
	stub.SetEvent("Message_1io2g9u", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	
	
	cc.ChangeBusinessRuleState(ctx, instance, "Activity_0rm8bkp", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_0d2xte5_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string ) error {
	stub := ctx.GetStub()
	instance,err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_0d2xte5")
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

	cc.ChangeMsgFireflyTranID(ctx, instance, fireflyTranID, msg.MessageID)
	    cc.ChangeMsgState(ctx, instance, "Message_0d2xte5", COMPLETED)
	
	stub.SetEvent("Message_0d2xte5", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	
	
	    cc.ChangeGtwState(ctx, instance, "Gateway_1cr0nma", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_04wmlqe_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string ) error {
	stub := ctx.GetStub()
	instance,err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_04wmlqe")
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

	cc.ChangeMsgFireflyTranID(ctx, instance, fireflyTranID, msg.MessageID)
	    cc.ChangeMsgState(ctx, instance, "Message_04wmlqe", COMPLETED)
	
	stub.SetEvent("Message_04wmlqe", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	
	
	    cc.ChangeMsgState(ctx, instance, "Message_1yv2h4e", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_1yv2h4e_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string ) error {
	stub := ctx.GetStub()
	instance,err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1yv2h4e")
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

	cc.ChangeMsgFireflyTranID(ctx, instance, fireflyTranID, msg.MessageID)
	    cc.ChangeMsgState(ctx, instance, "Message_1yv2h4e", COMPLETED)
	
	stub.SetEvent("Message_1yv2h4e", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	
	
	    cc.ChangeMsgState(ctx, instance, "Message_196q1fj", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_196q1fj_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string ) error {
	stub := ctx.GetStub()
	instance,err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_196q1fj")
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

	cc.ChangeMsgFireflyTranID(ctx, instance, fireflyTranID, msg.MessageID)
	    cc.ChangeMsgState(ctx, instance, "Message_196q1fj", COMPLETED)
	
	stub.SetEvent("Message_196q1fj", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	
	
	    cc.ChangeMsgState(ctx, instance, "Message_1slt8tv", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_1slt8tv_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string ) error {
	stub := ctx.GetStub()
	instance,err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1slt8tv")
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

	cc.ChangeMsgFireflyTranID(ctx, instance, fireflyTranID, msg.MessageID)
	    cc.ChangeMsgState(ctx, instance, "Message_1slt8tv", COMPLETED)
	
	stub.SetEvent("Message_1slt8tv", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	
	
	    cc.ChangeEventState(ctx, instance, "Event_13pbqdz", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Event_13pbqdz(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance,err:=cc.GetInstance(ctx, instanceID)
	event, err := cc.ReadEvent(ctx, instanceID, "Event_13pbqdz")
	if err != nil {
		return err
	}

	if event.EventState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", event.EventID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeEventState(ctx, instance, event.EventID, COMPLETED) 
	stub.SetEvent("Event_13pbqdz", []byte("EndEvent has been done"))
	
	cc.SetInstance(ctx, instance)
	return nil
}

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
		"ID":         "Activity_0ibsbry_Continue",
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

func (cc *SmartContract) Message_1oxmq1k_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string ) error {
	stub := ctx.GetStub()
	instance,err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1oxmq1k")
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

	cc.ChangeMsgFireflyTranID(ctx, instance, fireflyTranID, msg.MessageID)
	    cc.ChangeMsgState(ctx, instance, "Message_1oxmq1k", COMPLETED)
	
	stub.SetEvent("Message_1oxmq1k", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	
	
	    cc.ChangeGtwState(ctx, instance, "Gateway_1cr0nma", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_1dzkcn0_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string ) error {
	stub := ctx.GetStub()
	instance,err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1dzkcn0")
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

	cc.ChangeMsgFireflyTranID(ctx, instance, fireflyTranID, msg.MessageID)
	    cc.ChangeMsgState(ctx, instance, "Message_1dzkcn0", COMPLETED)
	
	stub.SetEvent("Message_1dzkcn0", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	
	
	    cc.ChangeGtwState(ctx, instance, "Gateway_1cr0nma", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_1dmeexg_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string ) error {
	stub := ctx.GetStub()
	instance,err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1dmeexg")
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

	cc.ChangeMsgFireflyTranID(ctx, instance, fireflyTranID, msg.MessageID)
	    cc.ChangeMsgState(ctx, instance, "Message_1dmeexg", COMPLETED)
	
	stub.SetEvent("Message_1dmeexg", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	
	
	    cc.ChangeGtwState(ctx, instance, "Gateway_1cr0nma", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Gateway_1cr0nma(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance,err:=cc.GetInstance(ctx, instanceID)
	gtw, err := cc.ReadGtw(ctx, instanceID, "Gateway_1cr0nma")
	if err != nil {
		return err
	}

	if gtw.GatewayState != ENABLED {
		errorMessage := fmt.Sprintf("Gateway state %s is not allowed", gtw.GatewayID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeGtwState(ctx, instance, gtw.GatewayID, COMPLETED)
	stub.SetEvent("Gateway_1cr0nma", []byte("ExclusiveGateway has been done"))
	cc.SetInstance(ctx, instance)
    
        cc.ChangeMsgState(ctx, instance, "Message_04wmlqe", ENABLED)
    
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Gateway_0ep8cuh(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance,err:=cc.GetInstance(ctx, instanceID)
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
	stub.SetEvent("Gateway_0ep8cuh", []byte("ExclusiveGateway has been done"))
	cc.SetInstance(ctx, instance)
    
    	currentMemory, err := cc.ReadGlobalVariable(ctx, instanceID)
	if err != nil {
		return err
	}

    FinalPriority:=currentMemory.FinalPriority

if true {
	    cc.ChangeMsgState(ctx, instance, "Message_0d2xte5", ENABLED)
}
if FinalPriority=="Low" {
	    cc.ChangeMsgState(ctx, instance, "Message_1oxmq1k", ENABLED)
}
if FinalPriority=="High" {
	    cc.ChangeMsgState(ctx, instance, "Message_1dmeexg", ENABLED)
}
if FinalPriority=="Medium" {
	    cc.ChangeMsgState(ctx, instance, "Message_1dzkcn0", ENABLED)
}
    
	cc.SetInstance(ctx, instance)
	return nil
}