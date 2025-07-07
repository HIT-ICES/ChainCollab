package chaincode

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"strconv"

	"github.com/hyperledger/fabric-chaincode-go/shim"
	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

type SmartContract struct {
	contractapi.Contract
}

type StateMemory struct {
}

type InitParameters struct {
	Participant_0w6qkdf Participant `json:"Participant_0w6qkdf"`
	Participant_19mgbdn Participant `json:"Participant_19mgbdn"`
	Participant_09cjol2 Participant `json:"Participant_09cjol2"`
	Participant_0sa2v7d Participant `json:"Participant_0sa2v7d"`
	Participant_19j1e3o Participant `json:"Participant_19j1e3o"`
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
	InstanceTokenELements map[string]*TokenElement `json:"InstanceTokenElements"`
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

type TokenElement struct {
	TokenElementID string       `json:"tokenElementID"`
	AssetType      string       `json:"assetType"`
	Operation      string       `json:"operation"`
	TokenName      string       `json:"tokenName"`
	TokenID        string       `json:"tokenId"`
	CallerID       string       `json:"caller"`
	CalleeID       []string     `json:"callee"`
	TokenType      string       `json:"tokenType"`
	TokenNumber    string       `json:"tokenNumber"`
	TokenURL       string       `json:"tokenURL"`
	State          ElementState `json:"State"`
}

func (cc *SmartContract) CreateTokenElement(ctx contractapi.TransactionContextInterface, instance *ContractInstance, tokenElementID string, state ElementState, Jsonstr string) (*TokenElement, error) {
	var TokenElement TokenElement
	err := json.Unmarshal([]byte(Jsonstr), &TokenElement)
	if err != nil {
		return nil, errors.New("  ") //错误信息
	}
	TokenElement.TokenElementID = tokenElementID
	TokenElement.State = state
	instance.InstanceTokenELements[tokenElementID] = &TokenElement

	returnToken, ok := instance.InstanceTokenELements[tokenElementID]
	if !ok {
		return nil, fmt.Errorf("无法将实例元素转换为Token")
	}
	return returnToken, nil
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

func (cc *SmartContract) changeTokenElementState(ctx contractapi.TransactionContextInterface, instance *ContractInstance, tokenElementID string, state ElementState) error {
	token, ok := instance.InstanceTokenELements[tokenElementID]
	if !ok {
		errorMessage := fmt.Sprintf("Token %s does not exist", tokenElementID)
		fmt.Println(errorMessage)
		return errors.New(errorMessage)
	}
	token.State = state
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
func (cc *SmartContract) GetAllTokenElement(ctx contractapi.TransactionContextInterface, instanceID string) ([]*TokenElement, error) {
	instanceJson, err := ctx.GetStub().GetState(instanceID)
	if err != nil {
		return nil, err
	}
	if instanceJson == nil {
		errorMessage := fmt.Sprintf("instance %s does not exist", instanceID)
		fmt.Println(errorMessage)
		return nil, errors.New(errorMessage)
	}
	var instance ContractInstance
	err = json.Unmarshal(instanceJson, &instance)
	if err != nil {
		fmt.Println(err.Error())
		return nil, err
	}
	var TokenElements []*TokenElement
	for _, TokenElement := range instance.InstanceTokenELements {
		TokenElements = append(TokenElements, TokenElement)
	}
	return TokenElements, nil

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

func (cc *SmartContract) ReadTokenElement(ctx contractapi.TransactionContextInterface, instanceID string, TokenElementID string) (*TokenElement, error) {
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
	TokenElement, ok := instance.InstanceTokenELements[TokenElementID]
	if !ok {
		errorMessage := fmt.Sprintf("TokenElement %s does not exist", TokenElementID)
		fmt.Sprintf(errorMessage)
		return nil, errors.New(errorMessage)
	}
	return TokenElement, nil
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

func (cc *SmartContract) TokenElementRun(ctx contractapi.TransactionContextInterface, TokenElement *TokenElement) error {
	if TokenElement.AssetType == "transferable" {
		var chaincodeName string
		switch TokenElement.Operation {
		//所有链码名字都为协议_tokenname eg: ERC20_toeknNAme
		//这里调用者身份会随着ctx传递下来
		case "mint":
			if TokenElement.TokenType == "FT" {
				chaincodeName = "ERC20_" + TokenElement.TokenName
				_args := make([][]byte, 2)
				_args[0] = []byte("Mint")                   // 操作类型
				_args[1] = []byte(TokenElement.TokenNumber) //铸造的数量
				cc.Invoke_Other_chaincode(ctx, chaincodeName, "default", _args)
			} else if TokenElement.TokenType == "NFT" {
				chaincodeName = "ERC721_" + TokenElement.TokenName
				_args := make([][]byte, 3)
				_args[0] = []byte("MintWithTokenURI") // 操作类型
				_args[1] = []byte(TokenElement.TokenID)
				_args[1] = []byte(TokenElement.TokenURL) //tokenURL待补充
				cc.Invoke_Other_chaincode(ctx, chaincodeName, "default", _args)
			}
		case "burn":
			if TokenElement.TokenType == "FT" {
				chaincodeName = "ERC20_" + TokenElement.TokenName
				_args := make([][]byte, 2)
				_args[0] = []byte("Burn")                   // 操作类型
				_args[1] = []byte(TokenElement.TokenNumber) //销毁的数量
				cc.Invoke_Other_chaincode(ctx, chaincodeName, "default", _args)
			} else if TokenElement.TokenType == "NFT" {
				chaincodeName = "ERC721_" + TokenElement.TokenName
				_args := make([][]byte, 2)
				_args[0] = []byte("Burn") // 操作类型
				_args[1] = []byte(TokenElement.TokenID)
				cc.Invoke_Other_chaincode(ctx, chaincodeName, "default", _args)
			}
		case "transfer":
			if TokenElement.TokenType == "FT" {
				chaincodeName = "ERC20_" + TokenElement.TokenName
				_args := make([][]byte, 3)
				_args[0] = []byte("Transfer")               // 操作类型
				_args[1] = []byte(TokenElement.CalleeID[0]) //转移对象
				cc.Invoke_Other_chaincode(ctx, chaincodeName, "default", _args)
			} else if TokenElement.TokenType == "NFT" {
				chaincodeName = "ERC721_" + TokenElement.TokenName
				_args := make([][]byte, 4)
				_args[0] = []byte("TransferFrom") // 操作类型
				_args[1] = []byte(TokenElement.CallerID)
				_args[2] = []byte(TokenElement.CalleeID[0])
				_args[3] = []byte(TokenElement.TokenID)
				cc.Invoke_Other_chaincode(ctx, chaincodeName, "default", _args)
			}
		case "query":
			//查询自己的余额
			if TokenElement.TokenType == "FT" {
				chaincodeName = "ERC20_" + TokenElement.TokenName
				_args := make([][]byte, 2)
				_args[0] = []byte("BalanceOf")           // 操作类型
				_args[1] = []byte(TokenElement.CallerID) //转移对象
				cc.Invoke_Other_chaincode(ctx, chaincodeName, "default", _args)
			} else if TokenElement.TokenType == "NFT" {
				//查看nft对应的url
				chaincodeName = "ERC721_" + TokenElement.TokenName
				_args := make([][]byte, 2)
				_args[0] = []byte("TokenURL") // 操作类型
				_args[1] = []byte(TokenElement.TokenID)
				cc.Invoke_Other_chaincode(ctx, chaincodeName, "default", _args)
			}
		default:
			return errors.New("operation is wrong")
		}

	} else if TokenElement.AssetType == "distributive" {
		//TODO

	} else if TokenElement.AssetType == "value-added" {
		//TODO
	}
	return nil
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
		InstanceID:            instanceID,
		InstanceStateMemory:   StateMemory{},
		InstanceMessages:      make(map[string]*Message),
		InstanceActionEvents:  make(map[string]*ActionEvent),
		InstanceGateways:      make(map[string]*Gateway),
		InstanceParticipants:  make(map[string]*Participant),
		InstanceBusinessRules: make(map[string]*BusinessRule),
		InstanceTokenELements: make(map[string]*TokenElement),
	}

	// Update the currentInstanceID
	/*
		cc.Crete

	*/
	cc.CreateParticipant(ctx, &instance, "Participant_0w6qkdf", initParameters.Participant_0w6qkdf.MSP, initParameters.Participant_0w6qkdf.Attributes, initParameters.Participant_0w6qkdf.X509, initParameters.Participant_0w6qkdf.IsMulti, 0, 0)
	cc.CreateParticipant(ctx, &instance, "Participant_19mgbdn", initParameters.Participant_19mgbdn.MSP, initParameters.Participant_19mgbdn.Attributes, initParameters.Participant_19mgbdn.X509, initParameters.Participant_19mgbdn.IsMulti, 0, 0)
	cc.CreateParticipant(ctx, &instance, "Participant_09cjol2", initParameters.Participant_09cjol2.MSP, initParameters.Participant_09cjol2.Attributes, initParameters.Participant_09cjol2.X509, initParameters.Participant_09cjol2.IsMulti, 0, 0)
	cc.CreateParticipant(ctx, &instance, "Participant_0sa2v7d", initParameters.Participant_0sa2v7d.MSP, initParameters.Participant_0sa2v7d.Attributes, initParameters.Participant_0sa2v7d.X509, initParameters.Participant_0sa2v7d.IsMulti, 0, 0)
	cc.CreateParticipant(ctx, &instance, "Participant_19j1e3o", initParameters.Participant_19j1e3o.MSP, initParameters.Participant_19j1e3o.Attributes, initParameters.Participant_19j1e3o.X509, initParameters.Participant_19j1e3o.IsMulti, 0, 0)
	cc.CreateActionEvent(ctx, &instance, "Event_06sexe6", ENABLED)

	cc.CreateActionEvent(ctx, &instance, "Event_13pbqdz", DISABLED)

	cc.CreateMessage(ctx, &instance, "Message_1amf6l2", "Participant_0sa2v7d", "Participant_19j1e3o", "", DISABLED, `{}`)
	cc.CreateMessage(ctx, &instance, "Message_196q1fj", "Participant_19mgbdn", "Participant_0w6qkdf", "", DISABLED, `{"properties":{"deliver":{"type":"string","description":""}},"required":[],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_04wmlqe", "Participant_19mgbdn", "Participant_0w6qkdf", "", DISABLED, `{"properties":{"report":{"type":"string","description":""}},"required":[],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_1slt8tv", "Participant_0w6qkdf", "Participant_19mgbdn", "", DISABLED, `{}`)
	cc.CreateMessage(ctx, &instance, "Message_1yv2h4e", "Participant_0w6qkdf", "Participant_19mgbdn", "", DISABLED, `{}`)
	cc.CreateMessage(ctx, &instance, "Message_0d2xte5", "Participant_19j1e3o", "Participant_19mgbdn", "", DISABLED, `{"properties":{"del_order":{"type":"string","description":""}},"required":[],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_1io2g9u", "Participant_0sa2v7d", "Participant_19j1e3o", "", DISABLED, `{"properties":{"waybill":{"type":"string","description":""}},"required":[],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_0hpha6h", "Participant_0sa2v7d", "Participant_19j1e3o", "", DISABLED, `{"properties":{"pre_details":{"type":"string","description":""}},"required":[],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_0rwz1km", "Participant_19j1e3o", "Participant_0sa2v7d", "", DISABLED, `{"properties":{"req_details":{"type":"string","description":""}},"required":[],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_0pm90nx", "Participant_0w6qkdf", "Participant_19j1e3o", "", DISABLED, `{"properties":{"transport_order":{"type":"string","description":""}},"required":[],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_0cba4t6", "Participant_0w6qkdf", "Participant_0sa2v7d", "", DISABLED, `{"properties":{"fwd_order":{"type":"string","description":""}},"required":[],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_1ajdm9l", "Participant_19mgbdn", "Participant_09cjol2", "", DISABLED, `{"properties":{"placed_order":{"type":"string","description":""}},"required":[],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_1wswgqu", "Participant_0w6qkdf", "Participant_19mgbdn", "", DISABLED, `{"properties":{"order":{"type":"string","description":""}},"required":[],"files":{},"file required":[]}`)
	cc.CreateGateway(ctx, &instance, "Gateway_0onpe6x", DISABLED)

	cc.CreateGateway(ctx, &instance, "Gateway_1fbifca", DISABLED)
	//原料创建阶段
	cc.CreateTokenElement(ctx, &instance, "Activity_0voe68z", DISABLED, `{"assetType": "transferable","operation": "mint","tokenName": "原料","caller": "Supplier","tokenType": "NFT","tokenId": "1"}`)
	cc.CreateTokenElement(ctx, &instance, "Activity_0l6jyqh", DISABLED, `{"assetType": "transferable","operation": "Transfer","tokenName": "原料", "caller": "Supplier","callee": ["Manufacturer"],"tokenType": "NFT","tokenId": "1"}`)
	cc.CreateTokenElement(ctx, &instance, "Activity_0xhcefo", DISABLED, `{"assetType": "transferable","operation": "mint","tokenName": "产品","caller": "Manufacturer","tokenType": "NFT","tokenId": "111"}`)
	cc.CreateTokenElement(ctx, &instance, "Activity_1u61szh", DISABLED, `{"assetType": "transferable","operation": "Transfer","tokenName": "产品","caller": "Manufacturer","callee": ["Bulk buyer"],"tokenType": "NFT","tokenId": "111"}`)
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

func (cc *SmartContract) Message_1wswgqu_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
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
	cc.ChangeMsgState(ctx, instance, "Message_1wswgqu", COMPLETED)

	stub.SetEvent("Message_1wswgqu", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	cc.ChangeMsgState(ctx, instance, "Message_1ajdm9l", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_1ajdm9l_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1ajdm9l")
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

func (cc *SmartContract) Message_0cba4t6_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_0cba4t6")
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
	cc.ChangeMsgState(ctx, instance, "Message_0cba4t6", COMPLETED)

	stub.SetEvent("Message_0cba4t6", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	cc.ChangeGtwState(ctx, instance, "Activity_0voe68z", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_0pm90nx_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_0pm90nx")
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
	cc.ChangeMsgState(ctx, instance, "Message_0pm90nx", COMPLETED)

	stub.SetEvent("Message_0pm90nx", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	if !(func() bool {
		msg, err := cc.ReadTokenElement(ctx, instanceID, "Activity_0voe68z")
		return err == nil && msg.State == COMPLETED
	}()) {
		return nil
	}
	cc.ChangeGtwState(ctx, instance, "Gateway_1fbifca", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

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

	cc.ChangeGtwState(ctx, instance, gtw.GatewayID, COMPLETED)
	stub.SetEvent("Gateway_1fbifca", []byte("Gateway has been done"))

	cc.ChangeMsgState(ctx, instance, "Message_0rwz1km", ENABLED)

	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_0rwz1km_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
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
	cc.ChangeMsgState(ctx, instance, "Message_0rwz1km", COMPLETED)

	stub.SetEvent("Message_0rwz1km", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	cc.ChangeMsgState(ctx, instance, "Message_1amf6l2", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_1amf6l2_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1amf6l2")
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
	cc.ChangeMsgState(ctx, instance, "Message_1amf6l2", COMPLETED)

	stub.SetEvent("Message_1amf6l2", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	cc.ChangeMsgState(ctx, instance, "Message_0hpha6h", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_0hpha6h_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_0hpha6h")
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
	cc.ChangeMsgState(ctx, instance, "Message_0hpha6h", COMPLETED)

	stub.SetEvent("Message_0hpha6h", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	cc.ChangeMsgState(ctx, instance, "Message_1io2g9u", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_1io2g9u_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1io2g9u")
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
	cc.ChangeMsgState(ctx, instance, "Message_1io2g9u", COMPLETED)

	stub.SetEvent("Message_1io2g9u", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	cc.ChangeMsgState(ctx, instance, "Message_0d2xte5", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_0d2xte5_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_0d2xte5")
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
	cc.ChangeMsgState(ctx, instance, "Message_0d2xte5", COMPLETED)

	stub.SetEvent("Message_0d2xte5", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	//Activity_0l6jyqh
	cc.ChangeMsgState(ctx, instance, "Activity_0l6jyqh", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_04wmlqe_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_04wmlqe")
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
	cc.ChangeMsgState(ctx, instance, "Message_04wmlqe", COMPLETED)

	stub.SetEvent("Message_04wmlqe", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	cc.ChangeMsgState(ctx, instance, "Activity_0xhcefo", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_1yv2h4e_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1yv2h4e")
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
	cc.ChangeMsgState(ctx, instance, "Message_1yv2h4e", COMPLETED)

	stub.SetEvent("Message_1yv2h4e", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	cc.ChangeMsgState(ctx, instance, "Message_196q1fj", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_196q1fj_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_196q1fj")
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
	cc.ChangeMsgState(ctx, instance, "Message_196q1fj", COMPLETED)

	stub.SetEvent("Message_196q1fj", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	//Activity_1u61szh
	cc.ChangeMsgState(ctx, instance, "Activity_1u61szh", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_1slt8tv_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1slt8tv")
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
	cc.ChangeMsgState(ctx, instance, "Message_1slt8tv", COMPLETED)

	stub.SetEvent("Message_1slt8tv", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	cc.ChangeEventState(ctx, instance, "Event_13pbqdz", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Event_13pbqdz(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
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
func (cc *SmartContract) Activity_0voe68z(ctx contractapi.TransactionContextInterface, instanceID string) error {
	instance, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	if instance == nil {
		return errors.New("instanceID does not exist")
	}
	//得到tokenElement元素
	tokenElement, err := cc.ReadTokenElement(ctx, instanceID, "Activity_0voe68z")
	if err != nil {
		return err
	}
	//检查
	if tokenElement.State != ENABLED {
		errorMessage := fmt.Sprintf("TokenElement state %s is not allowed", tokenElement.TokenElementID)
		fmt.Sprintln(errorMessage)
		return fmt.Errorf(errorMessage)
	}
	//轮到他运行，调用
	cc.TokenElementRun(ctx, tokenElement)
	//改状态
	cc.changeTokenElementState(ctx, instance, "Activity_0voe68z", COMPLETED)
	cc.SetInstance(ctx, instance)
	//gtw判断
	if !(func() bool {
		msg, err := cc.ReadMsg(ctx, instanceID, "Message_0pm90nx")
		return err == nil && msg.MsgState == COMPLETED
	}()) {
		return nil
	}
	cc.ChangeGtwState(ctx, instance, "Gateway_1fbifaca", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Activity_0l6jyqh(ctx contractapi.TransactionContextInterface, instanceID string) error {
	instance, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	if instance == nil {
		return errors.New("instanceID does not exist")
	}
	//得到tokenElement元素
	tokenElement, err := cc.ReadTokenElement(ctx, instanceID, "Activity_0l6jyqh")
	if err != nil {
		return err
	}
	//检查
	if tokenElement.State != ENABLED {
		errorMessage := fmt.Sprintf("TokenElement state %s is not allowed", tokenElement.TokenElementID)
		fmt.Sprintln(errorMessage)
		return fmt.Errorf(errorMessage)
	}
	//轮到他运行，调用
	cc.TokenElementRun(ctx, tokenElement)
	//改状态
	cc.changeTokenElementState(ctx, instance, "Activity_0l6jyqh", COMPLETED)
	cc.SetInstance(ctx, instance)
	cc.ChangeGtwState(ctx, instance, "Message_04wmlqe", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Activity_0xhcefo(ctx contractapi.TransactionContextInterface, instanceID string) error {
	instance, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	if instance == nil {
		return errors.New("instanceID does not exist")
	}
	//得到tokenElement元素
	tokenElement, err := cc.ReadTokenElement(ctx, instanceID, "Activity_0xhcefo")
	if err != nil {
		return err
	}
	//检查
	if tokenElement.State != ENABLED {
		errorMessage := fmt.Sprintf("TokenElement state %s is not allowed", tokenElement.TokenElementID)
		fmt.Sprintln(errorMessage)
		return fmt.Errorf(errorMessage)
	}
	//轮到他运行，调用
	cc.TokenElementRun(ctx, tokenElement)
	//改状态
	cc.changeTokenElementState(ctx, instance, "Activity_0xhcefo", COMPLETED)
	cc.SetInstance(ctx, instance)
	cc.ChangeGtwState(ctx, instance, "Message_1yv2h4e", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Activity_1u61szh(ctx contractapi.TransactionContextInterface, instanceID string) error {
	instance, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	if instance == nil {
		return errors.New("instanceID does not exist")
	}
	//得到tokenElement元素
	tokenElement, err := cc.ReadTokenElement(ctx, instanceID, "Activity_1u61szh")
	if err != nil {
		return err
	}
	//检查
	if tokenElement.State != ENABLED {
		errorMessage := fmt.Sprintf("TokenElement state %s is not allowed", tokenElement.TokenElementID)
		fmt.Sprintln(errorMessage)
		return fmt.Errorf(errorMessage)
	}
	//轮到他运行，调用
	cc.TokenElementRun(ctx, tokenElement)
	//改状态
	cc.changeTokenElementState(ctx, instance, "Activity_1u61szh", COMPLETED)
	cc.SetInstance(ctx, instance)
	cc.ChangeGtwState(ctx, instance, "Message_1slt8tv", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}
