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
    VIPpoints int `json:"VIPpoints"`
	Need_external_provider bool `json:"Need_external_provider"`
	InvoiceType string `json:"InvoiceType"`
	Invoice bool `json:"Invoice"`
	ExternalAvailable bool `json:"ExternalAvailable"`
	InvoiceAvailable bool `json:"InvoiceAvailable"`
	Is_available bool `json:"Is_available"`
}

type InitParameters struct {
    Participant_1080bkg Participant `json:"Participant_1080bkg"`
	Participant_0sktaei Participant `json:"Participant_0sktaei"`
	Participant_1gcdqza Participant `json:"Participant_1gcdqza"`
	Activity_1yl9tfp_DecisionID string `json:"Activity_1yl9tfp_DecisionID"`
	Activity_1yl9tfp_ParamMapping map[string]string `json:"Activity_1yl9tfp_ParamMapping"`
	Activity_1yl9tfp_Content string `json:"Activity_1yl9tfp_Content"`
	Activity_0ibsbry_DecisionID string `json:"Activity_0ibsbry_DecisionID"`
	Activity_0ibsbry_ParamMapping map[string]string `json:"Activity_0ibsbry_ParamMapping"`
	Activity_0ibsbry_Content string `json:"Activity_0ibsbry_Content"`
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

		cc.CreateParticipant(ctx, &instance, "Participant_1080bkg", initParameters.Participant_1080bkg.MSP, initParameters.Participant_1080bkg.Attributes, initParameters.Participant_1080bkg.X509,initParameters.Participant_1080bkg.IsMulti, 0, 0)
	cc.CreateParticipant(ctx, &instance, "Participant_0sktaei", initParameters.Participant_0sktaei.MSP, initParameters.Participant_0sktaei.Attributes, initParameters.Participant_0sktaei.X509,initParameters.Participant_0sktaei.IsMulti, 0, 0)
	cc.CreateParticipant(ctx, &instance, "Participant_1gcdqza", initParameters.Participant_1gcdqza.MSP, initParameters.Participant_1gcdqza.Attributes, initParameters.Participant_1gcdqza.X509,initParameters.Participant_1gcdqza.IsMulti, 0, 0)
	cc.CreateActionEvent(ctx, &instance, "Event_1jtgn3j", ENABLED)

	cc.CreateActionEvent(ctx, &instance, "Event_0366pfz", DISABLED)

	cc.CreateActionEvent(ctx, &instance, "Event_146eii4", DISABLED)

	cc.CreateActionEvent(ctx, &instance, "Event_143ykco", DISABLED)

	cc.CreateMessage(ctx, &instance, "Message_1qbk325", "Participant_1gcdqza", "Participant_0sktaei", "", DISABLED, `{"properties":{"product Id":{"type":"string","description":"Delivered product id"}},"required":["product Id"],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_1q05nnw", "Participant_0sktaei", "Participant_1gcdqza", "", DISABLED, `{"properties":{"payment amount":{"type":"number","description":"payment amount"}},"required":["payment amount"],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_1i8rlqn", "Participant_0sktaei", "Participant_1gcdqza", "", DISABLED, `{"properties":{"external service Id":{"type":"string","description":"The requested external service information"}},"required":["external service Id"],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_0m9p3da", "Participant_1080bkg", "Participant_0sktaei", "", DISABLED, `{"properties":{"invoice":{"type":"boolean","description":"Do you need an invoice?"},"invoiceType":{"type":"string","description":"type"}},"required":["invoice","invoiceType"],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_1etcmvl", "Participant_0sktaei", "Participant_1080bkg", "", DISABLED, `{"properties":{"invoice_id":{"type":"string","description":"Invoice Id"},"invoice_data":{"type":"number","description":"Date of invoice issuance"}},"required":["invoice_id"],"files":{"invoice":{"type":"file","description":"Invoice documents"}},"file required":["invoice"]}`)
	cc.CreateMessage(ctx, &instance, "Message_1joj7ca", "Participant_1080bkg", "Participant_0sktaei", "", DISABLED, `{"properties":{"invoice information":{"type":"string","description":"Invoice related information"}},"required":["invoice information"],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_1ljlm4g", "Participant_0sktaei", "Participant_1080bkg", "", DISABLED, `{"properties":{"delivered_product_id":{"type":"string","description":"delivered_product_id"}},"required":["delivered_product_id"],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_1xm9dxy", "Participant_1080bkg", "Participant_0sktaei", "", DISABLED, `{"properties":{"motivation":{"type":"string","description":"Motivation for Canceling orders"}},"required":["motivation"],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_0o8eyir", "Participant_1080bkg", "Participant_0sktaei", "", DISABLED, `{"properties":{"payment amount":{"type":"number","description":"payment amount"},"orderID":{"type":"number","description":"The order id of payment"}},"required":["payment amount","orderID"],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_1nlagx2", "Participant_1080bkg", "Participant_0sktaei", "", DISABLED, `{"properties":{"confirmation":{"type":"boolean","description":"Whether to accept the service plan"}},"required":["confirmation"],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_1em0ee4", "Participant_0sktaei", "Participant_1080bkg", "", DISABLED, `{"properties":{"service plan":{"type":"string","description":"service plan"},"price_quotation":{"type":"number","description":"Price quotation"},"need_external_provider":{"type":"boolean","description":"Whether external service providers are required"}},"required":["service plan","price_quotation","need_external_provider"],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_0r9lypd", "Participant_0sktaei", "Participant_1080bkg", "", DISABLED, `{"properties":{"is_available":{"type":"boolean","description":"Is the service available?"}},"required":["is_available"],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_045i10y", "Participant_1080bkg", "Participant_0sktaei", "", DISABLED, `{"properties":{"serviceId":{"type":"string","description":"The required service id"},"VIPpoints":{"type":"number","description":"points"}},"required":["serviceId","VIPpoints"],"files":{},"file required":[]}`)
	cc.CreateGateway(ctx, &instance, "ExclusiveGateway_106je4z", DISABLED)

	cc.CreateGateway(ctx, &instance, "ExclusiveGateway_0hs3ztq", DISABLED)

	cc.CreateGateway(ctx, &instance, "ExclusiveGateway_0nzwv7v", DISABLED)

	cc.CreateGateway(ctx, &instance, "Gateway_1bhtapl", DISABLED)

	cc.CreateGateway(ctx, &instance, "Gateway_04h9e6e", DISABLED)

	cc.CreateGateway(ctx, &instance, "EventBasedGateway_1fxpmyn", DISABLED)

	cc.CreateBusinessRule(ctx, &instance, "Activity_1yl9tfp", initParameters.Activity_1yl9tfp_Content, initParameters.Activity_1yl9tfp_DecisionID, initParameters.Activity_1yl9tfp_ParamMapping)
	cc.CreateBusinessRule(ctx, &instance, "Activity_0ibsbry", initParameters.Activity_0ibsbry_Content, initParameters.Activity_0ibsbry_DecisionID, initParameters.Activity_0ibsbry_ParamMapping)

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
		"Activity_1yl9tfp" : initParameters.Activity_1yl9tfp_Content,
"Activity_0ibsbry" : initParameters.Activity_0ibsbry_Content,
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

func (cc *SmartContract) Event_1jtgn3j(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)

	actionEvent, err := cc.ReadEvent(ctx, instanceID, "Event_1jtgn3j")
	if err != nil {
		return err
	}

	if actionEvent.EventState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", actionEvent.EventID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeEventState(ctx, instance, "Event_1jtgn3j", COMPLETED)
	stub.SetEvent("Event_1jtgn3j", []byte("Contract has been started successfully"))
	cc.SetInstance(ctx, instance)
	
	    cc.ChangeGtwState(ctx, instance, "ExclusiveGateway_0hs3ztq", ENABLED)
	
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_045i10y_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string , VIPpoints int) error {
	stub := ctx.GetStub()
	instance,err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_045i10y")
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
	    cc.ChangeMsgState(ctx, instance, "Message_045i10y", COMPLETED)
		globalMemory,readGloabolError := cc.ReadGlobalVariable(ctx, instanceID)
	if readGloabolError != nil {
		fmt.Println(readGloabolError.Error())
		return readGloabolError
	}
		globalMemory.VIPpoints = VIPpoints
	setGloabolErrror :=cc.SetGlobalVariable(ctx, instance, globalMemory)
	if setGloabolErrror != nil {
		fmt.Println(setGloabolErrror.Error())
		return setGloabolErrror
	}
	stub.SetEvent("Message_045i10y", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	
	
	    cc.ChangeMsgState(ctx, instance, "Message_0r9lypd", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_0r9lypd_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string , Is_available bool) error {
	stub := ctx.GetStub()
	instance,err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_0r9lypd")
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
	    cc.ChangeMsgState(ctx, instance, "Message_0r9lypd", COMPLETED)
		globalMemory,readGloabolError := cc.ReadGlobalVariable(ctx, instanceID)
	if readGloabolError != nil {
		fmt.Println(readGloabolError.Error())
		return readGloabolError
	}
		globalMemory.Is_available = Is_available
	setGloabolErrror :=cc.SetGlobalVariable(ctx, instance, globalMemory)
	if setGloabolErrror != nil {
		fmt.Println(setGloabolErrror.Error())
		return setGloabolErrror
	}
	stub.SetEvent("Message_0r9lypd", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	
	
	    cc.ChangeGtwState(ctx, instance, "ExclusiveGateway_106je4z", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) ExclusiveGateway_106je4z(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance,err:=cc.GetInstance(ctx, instanceID)
	gtw, err := cc.ReadGtw(ctx, instanceID, "ExclusiveGateway_106je4z")
	if err != nil {
		return err
	}

	if gtw.GatewayState != ENABLED {
		errorMessage := fmt.Sprintf("Gateway state %s is not allowed", gtw.GatewayID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeGtwState(ctx, instance, gtw.GatewayID, COMPLETED)
	stub.SetEvent("ExclusiveGateway_106je4z", []byte("ExclusiveGateway has been done"))
	cc.SetInstance(ctx, instance)
    
    	currentMemory, err := cc.ReadGlobalVariable(ctx, instanceID)
	if err != nil {
		return err
	}

    Is_available:=currentMemory.Is_available

if Is_available==true {
	    cc.ChangeMsgState(ctx, instance, "Message_1em0ee4", ENABLED)
}
if Is_available==false {
	    cc.ChangeGtwState(ctx, instance, "ExclusiveGateway_0hs3ztq", ENABLED)
}
    
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_1em0ee4_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string , Need_external_provider bool) error {
	stub := ctx.GetStub()
	instance,err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1em0ee4")
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
	    cc.ChangeMsgState(ctx, instance, "Message_1em0ee4", COMPLETED)
		globalMemory,readGloabolError := cc.ReadGlobalVariable(ctx, instanceID)
	if readGloabolError != nil {
		fmt.Println(readGloabolError.Error())
		return readGloabolError
	}
		globalMemory.Need_external_provider = Need_external_provider
	setGloabolErrror :=cc.SetGlobalVariable(ctx, instance, globalMemory)
	if setGloabolErrror != nil {
		fmt.Println(setGloabolErrror.Error())
		return setGloabolErrror
	}
	stub.SetEvent("Message_1em0ee4", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	
	
	    cc.ChangeMsgState(ctx, instance, "Message_1nlagx2", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_1nlagx2_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string ) error {
	stub := ctx.GetStub()
	instance,err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1nlagx2")
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
	    cc.ChangeMsgState(ctx, instance, "Message_1nlagx2", COMPLETED)
	
	stub.SetEvent("Message_1nlagx2", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	
	
	    cc.ChangeGtwState(ctx, instance, "EventBasedGateway_1fxpmyn", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) ExclusiveGateway_0hs3ztq(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance,err:=cc.GetInstance(ctx, instanceID)
	gtw, err := cc.ReadGtw(ctx, instanceID, "ExclusiveGateway_0hs3ztq")
	if err != nil {
		return err
	}

	if gtw.GatewayState != ENABLED {
		errorMessage := fmt.Sprintf("Gateway state %s is not allowed", gtw.GatewayID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeGtwState(ctx, instance, gtw.GatewayID, COMPLETED)
	stub.SetEvent("ExclusiveGateway_0hs3ztq", []byte("ExclusiveGateway has been done"))
	cc.SetInstance(ctx, instance)
    
        cc.ChangeMsgState(ctx, instance, "Message_045i10y", ENABLED)
    
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) EventBasedGateway_1fxpmyn(ctx contractapi.TransactionContextInterface, instanceID string) error { 
	stub := ctx.GetStub()
	instance,err:=cc.GetInstance(ctx, instanceID)
	gtw, err := cc.ReadGtw(ctx, instanceID, "EventBasedGateway_1fxpmyn")
	if err != nil {
		return err
	}

	if gtw.GatewayState != ENABLED {
		errorMessage := fmt.Sprintf("Gateway state %s is not allowed", gtw.GatewayID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeGtwState(ctx, instance, gtw.GatewayID, COMPLETED)
	stub.SetEvent("EventBasedGateway_1fxpmyn", []byte("EventbasedGateway has been done"))
	cc.SetInstance(ctx, instance)
 	
        cc.ChangeMsgState(ctx, instance, "Message_0o8eyir", ENABLED)
    cc.ChangeMsgState(ctx, instance, "Message_1xm9dxy", ENABLED)
    
	cc.SetInstance(ctx, instance)
    return nil
}

func (cc *SmartContract) Message_0o8eyir_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string ) error {
	stub := ctx.GetStub()
	instance,err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_0o8eyir")
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
	    cc.ChangeMsgState(ctx, instance, "Message_0o8eyir", COMPLETED)
	
	stub.SetEvent("Message_0o8eyir", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	    cc.ChangeMsgState(ctx, instance, "Message_1xm9dxy", DISABLED)
	
	cc.ChangeBusinessRuleState(ctx, instance, "Activity_1yl9tfp", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_1xm9dxy_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string ) error {
	stub := ctx.GetStub()
	instance,err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1xm9dxy")
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
	    cc.ChangeMsgState(ctx, instance, "Message_1xm9dxy", COMPLETED)
	
	stub.SetEvent("Message_1xm9dxy", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	    cc.ChangeMsgState(ctx, instance, "Message_0o8eyir", DISABLED)
	
	    cc.ChangeEventState(ctx, instance, "Event_0366pfz", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Event_0366pfz(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance,err:=cc.GetInstance(ctx, instanceID)
	event, err := cc.ReadEvent(ctx, instanceID, "Event_0366pfz")
	if err != nil {
		return err
	}

	if event.EventState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", event.EventID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeEventState(ctx, instance, event.EventID, COMPLETED) 
	stub.SetEvent("Event_0366pfz", []byte("EndEvent has been done"))
	
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_1ljlm4g_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string ) error {
	stub := ctx.GetStub()
	instance,err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1ljlm4g")
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
	    cc.ChangeMsgState(ctx, instance, "Message_1ljlm4g", COMPLETED)
	
	stub.SetEvent("Message_1ljlm4g", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	
	
	    cc.ChangeMsgState(ctx, instance, "Message_0m9p3da", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_0m9p3da_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string , InvoiceType string, Invoice bool) error {
	stub := ctx.GetStub()
	instance,err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_0m9p3da")
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
	    cc.ChangeMsgState(ctx, instance, "Message_0m9p3da", COMPLETED)
		globalMemory,readGloabolError := cc.ReadGlobalVariable(ctx, instanceID)
	if readGloabolError != nil {
		fmt.Println(readGloabolError.Error())
		return readGloabolError
	}
		globalMemory.InvoiceType = InvoiceType
	globalMemory.Invoice = Invoice
	setGloabolErrror :=cc.SetGlobalVariable(ctx, instance, globalMemory)
	if setGloabolErrror != nil {
		fmt.Println(setGloabolErrror.Error())
		return setGloabolErrror
	}
	stub.SetEvent("Message_0m9p3da", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	
	
	cc.ChangeBusinessRuleState(ctx, instance, "Activity_0ibsbry", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) ExclusiveGateway_0nzwv7v(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance,err:=cc.GetInstance(ctx, instanceID)
	gtw, err := cc.ReadGtw(ctx, instanceID, "ExclusiveGateway_0nzwv7v")
	if err != nil {
		return err
	}

	if gtw.GatewayState != ENABLED {
		errorMessage := fmt.Sprintf("Gateway state %s is not allowed", gtw.GatewayID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeGtwState(ctx, instance, gtw.GatewayID, COMPLETED)
	stub.SetEvent("ExclusiveGateway_0nzwv7v", []byte("ExclusiveGateway has been done"))
	cc.SetInstance(ctx, instance)
    
    	currentMemory, err := cc.ReadGlobalVariable(ctx, instanceID)
	if err != nil {
		return err
	}

    InvoiceAvailable:=currentMemory.InvoiceAvailable

if InvoiceAvailable==true {
	    cc.ChangeMsgState(ctx, instance, "Message_1joj7ca", ENABLED)
}
if InvoiceAvailable==false {
	    cc.ChangeEventState(ctx, instance, "Event_143ykco", ENABLED)
}
    
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_1joj7ca_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string ) error {
	stub := ctx.GetStub()
	instance,err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1joj7ca")
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
	    cc.ChangeMsgState(ctx, instance, "Message_1joj7ca", COMPLETED)
	
	stub.SetEvent("Message_1joj7ca", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	
	
	    cc.ChangeMsgState(ctx, instance, "Message_1etcmvl", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_1etcmvl_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string ) error {
	stub := ctx.GetStub()
	instance,err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1etcmvl")
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
	    cc.ChangeMsgState(ctx, instance, "Message_1etcmvl", COMPLETED)
	
	stub.SetEvent("Message_1etcmvl", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	
	
	    cc.ChangeEventState(ctx, instance, "Event_146eii4", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Event_146eii4(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance,err:=cc.GetInstance(ctx, instanceID)
	event, err := cc.ReadEvent(ctx, instanceID, "Event_146eii4")
	if err != nil {
		return err
	}

	if event.EventState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", event.EventID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeEventState(ctx, instance, event.EventID, COMPLETED) 
	stub.SetEvent("Event_146eii4", []byte("EndEvent has been done"))
	
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_1i8rlqn_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string ) error {
	stub := ctx.GetStub()
	instance,err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1i8rlqn")
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
	    cc.ChangeMsgState(ctx, instance, "Message_1i8rlqn", COMPLETED)
	
	stub.SetEvent("Message_1i8rlqn", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	
	
	    cc.ChangeMsgState(ctx, instance, "Message_1q05nnw", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Gateway_1bhtapl(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance,err:=cc.GetInstance(ctx, instanceID)
	gtw, err := cc.ReadGtw(ctx, instanceID, "Gateway_1bhtapl")
	if err != nil {
		return err
	}

	if gtw.GatewayState != ENABLED {
		errorMessage := fmt.Sprintf("Gateway state %s is not allowed", gtw.GatewayID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeGtwState(ctx, instance, gtw.GatewayID, COMPLETED)
	stub.SetEvent("Gateway_1bhtapl", []byte("ExclusiveGateway has been done"))
	cc.SetInstance(ctx, instance)
    
    	currentMemory, err := cc.ReadGlobalVariable(ctx, instanceID)
	if err != nil {
		return err
	}

    ExternalAvailable:=currentMemory.ExternalAvailable

if ExternalAvailable==true {
	    cc.ChangeMsgState(ctx, instance, "Message_1i8rlqn", ENABLED)
}
if ExternalAvailable==false {
	    cc.ChangeGtwState(ctx, instance, "Gateway_04h9e6e", ENABLED)
}
    
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Gateway_04h9e6e(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance,err:=cc.GetInstance(ctx, instanceID)
	gtw, err := cc.ReadGtw(ctx, instanceID, "Gateway_04h9e6e")
	if err != nil {
		return err
	}

	if gtw.GatewayState != ENABLED {
		errorMessage := fmt.Sprintf("Gateway state %s is not allowed", gtw.GatewayID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeGtwState(ctx, instance, gtw.GatewayID, COMPLETED)
	stub.SetEvent("Gateway_04h9e6e", []byte("ExclusiveGateway has been done"))
	cc.SetInstance(ctx, instance)
    
        cc.ChangeMsgState(ctx, instance, "Message_1ljlm4g", ENABLED)
    
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_1q05nnw_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string ) error {
	stub := ctx.GetStub()
	instance,err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1q05nnw")
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
	    cc.ChangeMsgState(ctx, instance, "Message_1q05nnw", COMPLETED)
	
	stub.SetEvent("Message_1q05nnw", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	
	
	    cc.ChangeMsgState(ctx, instance, "Message_1qbk325", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_1qbk325_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string ) error {
	stub := ctx.GetStub()
	instance,err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1qbk325")
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
	    cc.ChangeMsgState(ctx, instance, "Message_1qbk325", COMPLETED)
	
	stub.SetEvent("Message_1qbk325", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	
	
	    cc.ChangeGtwState(ctx, instance, "Gateway_04h9e6e", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Activity_1yl9tfp(ctx contractapi.TransactionContextInterface, instanceID string) error {


	instance, err := cc.GetInstance(ctx, instanceID)
	// Read Business Info
	businessRule, err := cc.ReadBusinessRule(ctx, instanceID, "Activity_1yl9tfp")
	if err != nil {
		return err
	}

	// Check the BusinessRule State
	if businessRule.State != ENABLED {
		return fmt.Errorf("The BusinessRule is not ENABLED")
	}

	// Get the CID

	res,err := cc.Invoke_Other_chaincode(ctx, "Oracle:v1", "default", oracle.EncodeGetDataItemArgs(
		instanceID, "Activity_1yl9tfp",
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
		"ID":        "Activity_1yl9tfp",
		"InstanceID": instanceID,
		"Func":	   "Activity_1yl9tfp_Continue",
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

	cc.ChangeBusinessRuleState(ctx, instance, "Activity_1yl9tfp", WAITINGFORCONFIRMATION)
	cc.SetInstance(ctx, instance)

	return nil
}

func (cc *SmartContract) Activity_1yl9tfp_Continue(ctx contractapi.TransactionContextInterface, instanceID string, ContentOfDmn string) error {
	// Read Business Info
	instance,err:=cc.GetInstance(ctx, instanceID)
	businessRule, err := cc.ReadBusinessRule(ctx, instanceID, "Activity_1yl9tfp")
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
	cc.ChangeBusinessRuleState(ctx, instance, "Activity_1yl9tfp", COMPLETED)

    
        cc.ChangeGtwState(ctx, instance, "Gateway_1bhtapl", ENABLED)
    

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

func (cc *SmartContract) Activity_0ibsbry(ctx contractapi.TransactionContextInterface, instanceID string) error {


	instance, err := cc.GetInstance(ctx, instanceID)
	// Read Business Info
	businessRule, err := cc.ReadBusinessRule(ctx, instanceID, "Activity_0ibsbry")
	if err != nil {
		return err
	}

	// Check the BusinessRule State
	if businessRule.State != ENABLED {
		return fmt.Errorf("The BusinessRule is not ENABLED")
	}

	// Get the CID

	res,err := cc.Invoke_Other_chaincode(ctx, "Oracle:v1", "default", oracle.EncodeGetDataItemArgs(
		instanceID, "Activity_0ibsbry",
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
		"ID":        "Activity_0ibsbry",
		"InstanceID": instanceID,
		"Func":	   "Activity_0ibsbry_Continue",
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

	cc.ChangeBusinessRuleState(ctx, instance, "Activity_0ibsbry", WAITINGFORCONFIRMATION)
	cc.SetInstance(ctx, instance)

	return nil
}

func (cc *SmartContract) Activity_0ibsbry_Continue(ctx contractapi.TransactionContextInterface, instanceID string, ContentOfDmn string) error {
	// Read Business Info
	instance,err:=cc.GetInstance(ctx, instanceID)
	businessRule, err := cc.ReadBusinessRule(ctx, instanceID, "Activity_0ibsbry")
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
	cc.ChangeBusinessRuleState(ctx, instance, "Activity_0ibsbry", COMPLETED)

    
        cc.ChangeGtwState(ctx, instance, "ExclusiveGateway_0nzwv7v", ENABLED)
    

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

func (cc *SmartContract) Event_143ykco(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance,err:=cc.GetInstance(ctx, instanceID)
	event, err := cc.ReadEvent(ctx, instanceID, "Event_143ykco")
	if err != nil {
		return err
	}

	if event.EventState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", event.EventID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeEventState(ctx, instance, event.EventID, COMPLETED) 
	stub.SetEvent("Event_143ykco", []byte("EndEvent has been done"))
	
	cc.SetInstance(ctx, instance)
	return nil
}