package chaincode

import (
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"strconv"
	"strings"

	"github.com/hyperledger/fabric-chaincode-go/shim"
	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

type SmartContract struct {
	contractapi.Contract
}

type StateMemory struct {
	ID string `json:"id,omitempty"` // 不加 validate 标签，也不加 required
}

type InitParameters struct {
	Participant_0jf9pos Participant `json:"Participant_0jf9pos"`
	Participant_03i30x8 Participant `json:"Participant_03i30x8"`
	Participant_0i6krxb Participant `json:"Participant_0i6krxb"`
	Participant_07bbtwj Participant `json:"Participant_07bbtwj"`
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
	InstanceTokenElements map[string]*TokenElement `json:"InstanceTokenElements"`
	InstanceTokens        map[string]*Token        `json:"InstanceTokens"`
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

// 方便解析的中间结构体
type FlatokenElement struct {
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

type TokenElement struct {
	TokenElementID  string       `json:"tokenElementID"`
	AssetType       string       `json:"assetType"`
	Operation       string       `json:"operation"`
	CallerID        string       `json:"caller"`
	CalleeID        []string     `json:"callee"`
	State           ElementState `json:"State"`
	OperationNumber string       `json:"operationNumber"`
	TokenKey        string       `json:"TokenKey"`
}

type Token struct {
	TokenType    string            `json:"tokenType"`
	OwnerID      string            `json:"tokenOwner"`
	TokenID      string            `json:"tokenID"`
	TokenURL     string            `json:"tokenURL"`
	TokenName    string            `json:"tokenName"`
	TokenBalance string            `json:"tokenBalance"` // For FT
	FtBalance    map[string]string `json:"FtBalance"`
}

func (cc *SmartContract) CreateToken(ctx contractapi.TransactionContextInterface, instance *ContractInstance, tokenType string, ownerID string, tokenID string, tokenURL string, tokenName string, ftbalance map[string]string) (*Token, error) {
	var token Token
	// 创建Token对象
	token = Token{
		TokenType: tokenType,
		OwnerID:   ownerID,
		TokenID:   tokenID,
		TokenURL:  tokenURL,
		TokenName: tokenName,
		FtBalance: ftbalance,
	}
	var tokenKey string
	if tokenType == "NFT" {
		tokenKey = "NFT_" + tokenID
	} else if tokenType == "FT" {
		tokenKey = "FT_" + tokenName
	}
	instance.InstanceTokens[tokenKey] = &token
	returnToken, ok := instance.InstanceTokens[tokenKey]
	if !ok {
		return nil, fmt.Errorf("无法将实例元素转换为Token")
	}
	return returnToken, nil
}
func (cc *SmartContract) CreateTokenElement(ctx contractapi.TransactionContextInterface, instance *ContractInstance, tokenElementID string, state ElementState, Jsonstr string) (*TokenElement, error) {
	var fla FlatokenElement
	err := json.Unmarshal([]byte(Jsonstr), &fla)
	if err != nil {
		return nil, fmt.Errorf("failed to unmarshal FlatokenElement: %s", err.Error())
	}
	fla.TokenElementID = tokenElementID
	fla.State = state
	fla.TokenID = instance.InstanceID + "-" + fla.TokenID
	//检查是否有这个元素
	var tokenKey string
	var token *Token
	if fla.TokenType == "NFT" {
		tokenKey = "NFT_" + fla.TokenID
	} else if fla.TokenType == "FT" {
		tokenKey = "FT_" + fla.TokenName
	}
	if _, ok := instance.InstanceTokens[tokenKey]; !ok {
		var ftbalance map[string]string
		// 如果是FT类型，创建一个可用的map，而不是nil
		if fla.TokenType == "FT" {
			ftbalance = make(map[string]string)
		}
		token, err = cc.CreateToken(ctx, instance, fla.TokenType, "", fla.TokenID, fla.TokenURL, fla.TokenName, ftbalance)
		if err != nil {
			return nil, fmt.Errorf("failed to create token: %s", err.Error())
		}
	} else {
		token = instance.InstanceTokens[tokenKey]
	}
	// 创建TokenElement对象
	tokenKey, _ = cc.GetTokenKey(ctx, token)
	var tokenElement TokenElement
	tokenElement = TokenElement{
		TokenElementID:  fla.TokenElementID,
		AssetType:       fla.AssetType,
		Operation:       fla.Operation,
		CallerID:        fla.CallerID,
		CalleeID:        fla.CalleeID,
		State:           fla.State,
		OperationNumber: fla.TokenNumber,
		TokenKey:        tokenKey,
	}
	instance.InstanceTokenElements[tokenElementID] = &tokenElement

	returnToken, okk := instance.InstanceTokenElements[tokenElementID]
	if !okk {
		return nil, fmt.Errorf("无法将实例元素转换为TokenElement")
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
	TokenElement, ok := instance.InstanceTokenElements[TokenElementID]
	if !ok {
		errorMessage := fmt.Sprintf("TokenElement %s does not exist", TokenElementID)
		fmt.Sprintf(errorMessage)
		return nil, errors.New(errorMessage)
	}
	return TokenElement, nil
}

func (cc *SmartContract) ReadToken(ctx contractapi.TransactionContextInterface, instanceID string, tokenKey string) (*Token, error) {
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

	token, ok := instance.InstanceTokens[tokenKey]
	if !ok {
		errorMessage := fmt.Sprintf("Token %s does not exist", tokenKey)
		fmt.Println(errorMessage)
		return nil, errors.New(errorMessage)
	}

	return token, nil
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

func (cc *SmartContract) changeTokenElementState(ctx contractapi.TransactionContextInterface, instance *ContractInstance, tokenElementID string, state ElementState) error {
	token, ok := instance.InstanceTokenElements[tokenElementID]
	if !ok {
		errorMessage := fmt.Sprintf("Token %s does not exist", tokenElementID)
		fmt.Println(errorMessage)
		return errors.New(errorMessage)
	}
	token.State = state
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
	for _, TokenElement := range instance.InstanceTokenElements {
		TokenElements = append(TokenElements, TokenElement)
	}
	return TokenElements, nil

}

func (cc *SmartContract) GetAllTokens(ctx contractapi.TransactionContextInterface, instanceID string) ([]*Token, error) {
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
	var tokens []*Token
	for _, token := range instance.InstanceTokens {
		tokens = append(tokens, token)
	}
	return tokens, nil
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
		InstanceID:            instanceID,
		InstanceStateMemory:   StateMemory{},
		InstanceMessages:      make(map[string]*Message),
		InstanceActionEvents:  make(map[string]*ActionEvent),
		InstanceGateways:      make(map[string]*Gateway),
		InstanceParticipants:  make(map[string]*Participant),
		InstanceBusinessRules: make(map[string]*BusinessRule),
		InstanceTokenElements: make(map[string]*TokenElement),
		InstanceTokens:        make(map[string]*Token),
	}

	// Update the currentInstanceID

	cc.CreateParticipant(ctx, &instance, "Participant_0jf9pos", initParameters.Participant_0jf9pos.MSP, initParameters.Participant_0jf9pos.Attributes, initParameters.Participant_0jf9pos.X509, initParameters.Participant_0jf9pos.IsMulti, 0, 0)
	cc.CreateParticipant(ctx, &instance, "Participant_03i30x8", initParameters.Participant_03i30x8.MSP, initParameters.Participant_03i30x8.Attributes, initParameters.Participant_03i30x8.X509, initParameters.Participant_03i30x8.IsMulti, 0, 0)
	cc.CreateParticipant(ctx, &instance, "Participant_0i6krxb", initParameters.Participant_0i6krxb.MSP, initParameters.Participant_0i6krxb.Attributes, initParameters.Participant_0i6krxb.X509, initParameters.Participant_0i6krxb.IsMulti, 0, 0)
	cc.CreateParticipant(ctx, &instance, "Participant_07bbtwj", initParameters.Participant_07bbtwj.MSP, initParameters.Participant_07bbtwj.Attributes, initParameters.Participant_07bbtwj.X509, initParameters.Participant_07bbtwj.IsMulti, 0, 0)
	cc.CreateActionEvent(ctx, &instance, "Event_0v4xr2j", ENABLED)

	cc.CreateActionEvent(ctx, &instance, "Event_156srbw", DISABLED)

	cc.CreateMessage(ctx, &instance, "Message_050avia", "Participant_03i30x8", "Participant_0jf9pos", "", DISABLED, `{"properties":{"order2":{"type":"string","description":""}},"required":[],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_0yhqsl3", "Participant_0jf9pos", "Participant_03i30x8", "", DISABLED, `{}`)
	cc.CreateMessage(ctx, &instance, "Message_0chyejz", "Participant_0jf9pos", "Participant_03i30x8", "", DISABLED, `{"properties":{"points":{"type":"string","description":""}},"required":[],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_04s3sem", "Participant_03i30x8", "Participant_0jf9pos", "", DISABLED, `{"properties":{"order":{"type":"string","description":""}},"required":[],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_0a79682", "Participant_0jf9pos", "Participant_07bbtwj", "", DISABLED, `{"properties":{"Quota":{"type":"string","description":""}},"required":[],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_0efklb0", "Participant_0jf9pos", "Participant_03i30x8", "", DISABLED, `{}`)
	cc.CreateMessage(ctx, &instance, "Message_1pu7mww", "Participant_0jf9pos", "Participant_07bbtwj", "", DISABLED, `{}`)
	cc.CreateMessage(ctx, &instance, "Message_0rsr8ae", "Participant_07bbtwj", "Participant_0jf9pos", "", DISABLED, `{"properties":{"rules":{"type":"string","description":""}},"required":[],"files":{},"file required":[]}`)

	//tokenelement
	cc.CreateTokenElement(ctx, &instance, "Activity_1t8rpfu", DISABLED, `{"assetType": "transferable","operation": "mint","tokenName": "points","caller": "Participant_07bbtwj","tokenType": "FT","tokenNumber": "5000"}`)
	cc.CreateTokenElement(ctx, &instance, "Activity_18a0wk8", DISABLED, `{"assetType": "transferable","operation": "Transfer","tokenName": "points","caller": "Participant_07bbtwj","callee": ["Participant_0jf9pos"],"tokenType": "FT","tokenNumber": "100"}`)
	cc.CreateTokenElement(ctx, &instance, "Activity_0y6w5kq", DISABLED, `{"assetType": "transferable","operation": "Transfer","tokenName": "points","caller": "Participant_0jf9pos","callee": ["Participant_03i30x8"],"tokenType": "FT","tokenNumber": "1"}`)

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

func (cc *SmartContract) Message_0rsr8ae_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_0rsr8ae")
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
	cc.ChangeMsgState(ctx, instance, "Message_0rsr8ae", COMPLETED)

	stub.SetEvent("Message_0rsr8ae", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	cc.ChangeMsgState(ctx, instance, "Message_1pu7mww", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_1pu7mww_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1pu7mww")
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
	cc.ChangeMsgState(ctx, instance, "Message_1pu7mww", COMPLETED)

	stub.SetEvent("Message_1pu7mww", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	cc.ChangeMsgState(ctx, instance, "Message_0a79682", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Event_0v4xr2j(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)

	actionEvent, err := cc.ReadEvent(ctx, instanceID, "Event_0v4xr2j")
	if err != nil {
		return err
	}

	if actionEvent.EventState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", actionEvent.EventID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeEventState(ctx, instance, "Event_0v4xr2j", COMPLETED)
	stub.SetEvent("Event_0v4xr2j", []byte("Contract has been started successfully"))
	cc.SetInstance(ctx, instance)

	cc.changeTokenElementState(ctx, instance, "Activity_1t8rpfu", ENABLED)

	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_04s3sem_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_04s3sem")
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
	cc.ChangeMsgState(ctx, instance, "Message_04s3sem", COMPLETED)

	stub.SetEvent("Message_04s3sem", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	cc.ChangeMsgState(ctx, instance, "Message_0efklb0", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_0efklb0_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_0efklb0")
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
	cc.ChangeMsgState(ctx, instance, "Message_0efklb0", COMPLETED)

	stub.SetEvent("Message_0efklb0", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	cc.ChangeMsgState(ctx, instance, "Message_0chyejz", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_0a79682_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_0a79682")
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
	cc.ChangeMsgState(ctx, instance, "Message_0a79682", COMPLETED)

	stub.SetEvent("Message_0a79682", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	cc.changeTokenElementState(ctx, instance, "Activity_18a0wk8", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_0chyejz_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_0chyejz")
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
	cc.ChangeMsgState(ctx, instance, "Message_0chyejz", COMPLETED)

	stub.SetEvent("Message_0chyejz", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	cc.changeTokenElementState(ctx, instance, "Activity_0y6w5kq", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_050avia_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_050avia")
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
	cc.ChangeMsgState(ctx, instance, "Message_050avia", COMPLETED)

	stub.SetEvent("Message_050avia", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	cc.ChangeMsgState(ctx, instance, "Message_0yhqsl3", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_0yhqsl3_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_0yhqsl3")
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
	cc.ChangeMsgState(ctx, instance, "Message_0yhqsl3", COMPLETED)

	stub.SetEvent("Message_0yhqsl3", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	cc.ChangeEventState(ctx, instance, "Event_156srbw", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Event_156srbw(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	event, err := cc.ReadEvent(ctx, instanceID, "Event_156srbw")
	if err != nil {
		return err
	}

	if event.EventState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", event.EventID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeEventState(ctx, instance, event.EventID, COMPLETED)
	stub.SetEvent("Event_156srbw", []byte("EndEvent has been done"))

	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Activity_1t8rpfu(ctx contractapi.TransactionContextInterface, instanceID string) error {
	instance, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	if instance == nil {
		return errors.New("instanceID does not exist")
	}
	//得到tokenElement元素
	tokenElement, err := cc.ReadTokenElement(ctx, instanceID, "Activity_1t8rpfu")
	if err != nil {
		return err
	}
	//得到token元素
	token, err := cc.ReadToken(ctx, instanceID, tokenElement.TokenKey)
	if err != nil {
		return err
	}
	//测试
	for key, tokenvalue := range token.FtBalance {
		fmt.Printf("Key: %s, Value: %s\n", key, tokenvalue)
	}
	// //检查
	// if tokenElement.State != ENABLED {
	// 	errorMessage := fmt.Sprintf("TokenElement state %s is not allowed", tokenElement.TokenElementID)
	// 	fmt.Sprintln(errorMessage)
	// 	return fmt.Errorf(errorMessage)
	// }
	//轮到他运行，调用
	//先检查调用者是不是拥有者

	chaincodeName := "ERC20-" + token.TokenName
	_args := make([][]byte, 3)
	_args[0] = []byte("Mint") // 操作类型
	_args[1] = []byte(tokenElement.OperationNumber)
	_args[2] = []byte(instanceID)
	_, err = cc.Invoke_Other_chaincode(ctx, chaincodeName, "default", _args)
	if err != nil {
		return fmt.Errorf("failed to invoke chaincode %s: %v", chaincodeName, err)
	}
	//解析返回值

	//修改一下token中的账户和其余额
	nowid64, _ := ctx.GetClientIdentity().GetID()
	nowbalance := token.FtBalance[nowid64]
	str := tokenElement.OperationNumber
	// 字符串转 int
	operation, err := strconv.Atoi(str)
	value, err := strconv.Atoi(nowbalance)
	value = value + operation
	result := strconv.Itoa(value)
	cc.changeTokenBalance(ctx, instance, tokenElement.TokenKey, nowid64, result)

	//测试

	//改状态
	cc.changeTokenElementState(ctx, instance, "Activity_1t8rpfu", COMPLETED)
	cc.SetInstance(ctx, instance)
	cc.ChangeMsgState(ctx, instance, "Message_0rsr8ae", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Activity_18a0wk8(ctx contractapi.TransactionContextInterface, instanceID string) error {
	instance, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	if instance == nil {
		return errors.New("instanceID does not exist")
	}
	//得到tokenElement元素
	fmt.Println("Activity_0l6jyqh run start")
	tokenElement, err := cc.ReadTokenElement(ctx, instanceID, "Activity_18a0wk8")
	if err != nil {
		return err
	}
	//得到token元素
	token, err := cc.ReadToken(ctx, instanceID, tokenElement.TokenKey)
	if err != nil {
		return err
	}
	//测试
	for key, tokenvalue := range token.FtBalance {
		fmt.Printf("Key: %s, Value: %s\n", key, tokenvalue)
	}
	// //检查
	// if tokenElement.State != ENABLED {
	// 	errorMessage := fmt.Sprintf("TokenElement state %s is not allowed", tokenElement.TokenElementID)
	// 	fmt.Sprintln(errorMessage)
	// 	return fmt.Errorf(errorMessage)
	// }
	//轮到他运行，调用
	//先检查调用者是不是拥有者

	participantID := tokenElement.CalleeID[0]
	if participantID == "" {
		return fmt.Errorf("participantID cannot be empty")
	}
	participant, err := cc.ReadParticipant(ctx, instanceID, participantID)
	if err != nil {
		return fmt.Errorf("failed to read participant: %v", err)
	}
	//参与者为类，x509可能为空
	if participant.X509 == "" {
		return fmt.Errorf("participant.X509 is empty")
	}
	getid := participant.X509
	atindex := strings.Index(getid, "@")
	if atindex == -1 {
		return fmt.Errorf("invalid participant identity format: %s", getid)
	}
	//得到了被调用的地址
	id64 := getid[:atindex]

	chaincodeName := "ERC20-" + token.TokenName
	_args := make([][]byte, 4)
	_args[0] = []byte("Transfer") // 操作类型
	_args[1] = []byte(id64)
	_args[2] = []byte(tokenElement.OperationNumber)
	_args[3] = []byte(instanceID)
	_, err = cc.Invoke_Other_chaincode(ctx, chaincodeName, "default", _args)
	if err != nil {
		return fmt.Errorf("failed to invoke chaincode %s: %v", chaincodeName, err)
	}
	//解析返回值

	//修改一下token中的账户和其余额
	nowid64, _ := ctx.GetClientIdentity().GetID()
	nowbalance := token.FtBalance[nowid64]
	str := tokenElement.OperationNumber
	// 字符串转 int
	operation, err := strconv.Atoi(str)
	value, err := strconv.Atoi(nowbalance)
	value = value - operation //
	result := strconv.Itoa(value)
	cc.changeTokenBalance(ctx, instance, tokenElement.TokenKey, nowid64, result)
	recipientValue := token.FtBalance[id64]
	recipientNumber, err := strconv.Atoi(recipientValue)
	recipientNumber = recipientNumber + operation
	result = strconv.Itoa(recipientNumber)
	cc.changeTokenBalance(ctx, instance, tokenElement.TokenKey, id64, result)
	//测试

	//改状态
	cc.changeTokenElementState(ctx, instance, "Activity_18a0wk8", COMPLETED)
	cc.SetInstance(ctx, instance)
	cc.ChangeMsgState(ctx, instance, "Message_04s3sem", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Activity_0y6w5kq(ctx contractapi.TransactionContextInterface, instanceID string) error {
	instance, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	if instance == nil {
		return errors.New("instanceID does not exist")
	}
	//得到tokenElement元素
	fmt.Println("Activity_0l6jyqh run start")
	tokenElement, err := cc.ReadTokenElement(ctx, instanceID, "Activity_0y6w5kq")
	if err != nil {
		return err
	}
	//得到token元素
	token, err := cc.ReadToken(ctx, instanceID, tokenElement.TokenKey)
	if err != nil {
		return err
	}
	//测试
	for key, tokenvalue := range token.FtBalance {
		fmt.Printf("Key: %s, Value: %s\n", key, tokenvalue)
	}
	// //检查
	// if tokenElement.State != ENABLED {
	// 	errorMessage := fmt.Sprintf("TokenElement state %s is not allowed", tokenElement.TokenElementID)
	// 	fmt.Sprintln(errorMessage)
	// 	return fmt.Errorf(errorMessage)
	// }
	//轮到他运行，调用
	//先检查调用者是不是拥有者

	participantID := tokenElement.CalleeID[0]
	if participantID == "" {
		return fmt.Errorf("participantID cannot be empty")
	}
	participant, err := cc.ReadParticipant(ctx, instanceID, participantID)
	if err != nil {
		return fmt.Errorf("failed to read participant: %v", err)
	}
	//参与者为类，x509可能为空
	if participant.X509 == "" {
		return fmt.Errorf("participant.X509 is empty")
	}
	getid := participant.X509
	atindex := strings.Index(getid, "@")
	if atindex == -1 {
		return fmt.Errorf("invalid participant identity format: %s", getid)
	}
	//得到了被调用的地址
	id64 := getid[:atindex]

	chaincodeName := "ERC20-" + token.TokenName
	_args := make([][]byte, 4)
	_args[0] = []byte("Transfer") // 操作类型
	_args[1] = []byte(id64)
	_args[2] = []byte(tokenElement.OperationNumber)
	_args[3] = []byte(instanceID)
	_, err = cc.Invoke_Other_chaincode(ctx, chaincodeName, "default", _args)
	if err != nil {
		return fmt.Errorf("failed to invoke chaincode %s: %v", chaincodeName, err)
	}
	//解析返回值

	//修改一下token中的账户和其余额
	nowid64, _ := ctx.GetClientIdentity().GetID()
	nowbalance := token.FtBalance[nowid64]
	str := tokenElement.OperationNumber
	// 字符串转 int
	operation, err := strconv.Atoi(str)
	value, err := strconv.Atoi(nowbalance)
	value = value - operation //
	result := strconv.Itoa(value)
	cc.changeTokenBalance(ctx, instance, tokenElement.TokenKey, nowid64, result)
	recipientValue := token.FtBalance[id64]
	recipientNumber, err := strconv.Atoi(recipientValue)
	recipientNumber = recipientNumber + operation
	result = strconv.Itoa(recipientNumber)
	cc.changeTokenBalance(ctx, instance, tokenElement.TokenKey, id64, result)
	//测试

	//改状态
	cc.changeTokenElementState(ctx, instance, "Activity_0y6w5kq", COMPLETED)
	cc.SetInstance(ctx, instance)
	cc.ChangeMsgState(ctx, instance, "Message_050avia", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) GetTokenKey(ctx contractapi.TransactionContextInterface, token *Token) (string, error) {
	var resultKey string
	if token.TokenType == "NFT" {
		resultKey = "NFT_" + token.TokenID
	} else if token.TokenType == "FT" {
		resultKey = "FT_" + token.TokenName
	}
	return resultKey, nil
}

func (cc *SmartContract) changeTokenOwner(ctx contractapi.TransactionContextInterface, instance *ContractInstance, tokenkey string, ownerid string) error {
	token, ok := instance.InstanceTokens[tokenkey]
	if !ok {
		errorMessage := fmt.Sprintf("Token %s does not exist", tokenkey)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}
	token.OwnerID = ownerid
	//打印检查一下
	fmt.Println("Token的拥有者变更为", token.OwnerID)
	return nil
}

func (cc *SmartContract) changeTokenBalance(ctx contractapi.TransactionContextInterface, instance *ContractInstance, tokenkey string, owner string, balance string) error {
	token, ok := instance.InstanceTokens[tokenkey]
	if !ok {
		errorMessage := fmt.Sprintf("Token %s does not exist", tokenkey)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}
	token.FtBalance[owner] = balance
	return nil
}

// 参与者id变为身份id
func (cc *SmartContract) ParticipantToidentity(ctx contractapi.TransactionContextInterface, instanceID string, participantID string) (string, error) {
	//获取参与者的id
	if participantID == "" {
		return "", fmt.Errorf("participantID cannot be empty")
	}
	participant, err := cc.ReadParticipant(ctx, instanceID, participantID)
	if err != nil {
		return "", fmt.Errorf("failed to read participant: %v", err)
	}
	//参与者为类，x509可能为空
	if participant.X509 == "" {
		return "", fmt.Errorf("participant.X509 is empty")
	}
	getid := participant.X509
	atindex := strings.Index(getid, "@")
	if atindex == -1 {
		return "", fmt.Errorf("invalid participant identity format: %s", getid)
	}
	id64 := getid[:atindex]
	idBytes, err := base64.StdEncoding.DecodeString(id64)
	id := string(idBytes)

	return id, nil
}

func (cc *SmartContract) AddMintAuthority_nft(ctx contractapi.TransactionContextInterface, instanceID string, allowedMSPs []string, tokenelementname string) error {
	allowedMSPsJson, err := json.Marshal(allowedMSPs)
	if err != nil {
		return fmt.Errorf("failed to marshal allowedMSPs: %v", err)
	}
	chaincodeName := "ERC721-" + tokenelementname
	_args := make([][]byte, 3)
	_args[0] = []byte("AddMintAuthority") // 调用函数
	_args[1] = []byte(instanceID)         //name
	_args[2] = allowedMSPsJson            //name
	cc.Invoke_Other_chaincode(
		ctx,
		chaincodeName,
		"default",
		_args,
	)

	return nil
}

func (cc *SmartContract) AddMintAuthority_ft(ctx contractapi.TransactionContextInterface, instanceID string, allowedMSPs []string, tokenelementname string) error {
	allowedMSPsJson, err := json.Marshal(allowedMSPs)
	if err != nil {
		return fmt.Errorf("failed to marshal allowedMSPs: %v", err)
	}
	chaincodeName := "ERC20-" + tokenelementname
	_args := make([][]byte, 3)
	_args[0] = []byte("AddMintAuthority") // 调用函数
	_args[1] = []byte(instanceID)         //name
	_args[2] = allowedMSPsJson            //name
	cc.Invoke_Other_chaincode(
		ctx,
		chaincodeName,
		"default",
		_args,
	)

	return nil
}

func (cc *SmartContract) TokenElementInitialize(ctx contractapi.TransactionContextInterface, name string) error {
	symbol := name
	chaincodeName := "ERC721-" + name
	// minterMSPs := []string{"Mem.org.comMSP", "Organization-consortium.org.comMSP"}
	// minterMSPsJson, err := json.Marshal(minterMSPs)
	// if err != nil {
	// 	return err // 或 ctx.GetStub().SetEvent(...) 返回错误
	// }
	_args := make([][]byte, 4)
	_args[0] = []byte("Initialize") // 操作类型
	_args[1] = []byte(name)         //name
	_args[2] = []byte(symbol)
	response, _ := cc.Invoke_Other_chaincode(
		ctx,
		chaincodeName,
		"default",
		_args,
	)
	fmt.Print("response:")
	fmt.Println(string(response))
	return nil
}

func (cc *SmartContract) TokenElementInitializeFT(ctx contractapi.TransactionContextInterface, name string) error {
	symbol := name
	chaincodeName := "ERC20-" + name
	// minterMSPs := []string{"Mem.org.comMSP", "Organization-consortium.org.comMSP"}
	// minterMSPsJson, err := json.Marshal(minterMSPs)
	// if err != nil {
	// 	return err // 或 ctx.GetStub().SetEvent(...) 返回错误
	// }
	_args := make([][]byte, 4)
	_args[0] = []byte("Initialize") // 操作类型
	_args[1] = []byte(name)         //name
	_args[2] = []byte(symbol)
	_args[3] = []byte("0")
	response, _ := cc.Invoke_Other_chaincode(
		ctx,
		chaincodeName,
		"default",
		_args,
	)
	fmt.Print("response:")
	fmt.Println(string(response))
	return nil
}

func (cc *SmartContract) TokenftQuery(ctx contractapi.TransactionContextInterface, instanceID string) (string, error) {
	//查询功能应该是查询拥有者，tokenid，tokenurl之类的信息，但id和url的信息在填入时就有，所以只查拥有者？
	clientID, err := ctx.GetClientIdentity().GetID()
	if err != nil {
		return "", fmt.Errorf("failed to get client id: %v", err)
	}
	chaincodeName := "ERC20-points"
	_args := make([][]byte, 3)
	_args[0] = []byte("BalanceOf") // 操作类型
	_args[1] = []byte(clientID)    // 操作类型
	_args[2] = []byte(instanceID)  //name
	response, _ := cc.Invoke_Other_chaincode(
		ctx,
		chaincodeName,
		"default",
		_args,
	)
	fmt.Print("response:")
	fmt.Println(string(response))
	return (string(response)), nil
}

func (cc *SmartContract) TokenNftQuery1(ctx contractapi.TransactionContextInterface, tokenId string) (string, error) {
	//查询功能应该是查询拥有者，tokenid，tokenurl之类的信息，但id和url的信息在填入时就有，所以只查拥有者？
	chaincodeName := "ERC721-rawMaterial"
	_args := make([][]byte, 2)
	_args[0] = []byte("OwnerOf") // 操作类型
	_args[1] = []byte(tokenId)   //name
	response, _ := cc.Invoke_Other_chaincode(
		ctx,
		chaincodeName,
		"default",
		_args,
	)
	fmt.Print("response:")
	fmt.Println(string(response))
	return (string(response)), nil
}
func (cc *SmartContract) TokenNftQuery2(ctx contractapi.TransactionContextInterface, tokenId string) (string, error) {
	//查询功能应该是查询拥有者，tokenid，tokenurl之类的信息，但id和url的信息在填入时就有，所以只查拥有者？
	chaincodeName := "ERC721-product"
	_args := make([][]byte, 2)
	_args[0] = []byte("OwnerOf") // 操作类型
	_args[1] = []byte(tokenId)   //name
	response, _ := cc.Invoke_Other_chaincode(
		ctx,
		chaincodeName,
		"default",
		_args,
	)
	fmt.Print("response:")
	fmt.Println(string(response))
	return (string(response)), nil
}

// 打印token对象内容，帮助检验的
func (cc *SmartContract) printToken(ctx contractapi.TransactionContextInterface, token *Token) error {
	fmt.Println("打印的token:")
	fmt.Println("tokenid:", token.TokenID)
	fmt.Println("tokenid:", token.OwnerID)
	fmt.Println("tokenid:", token.TokenName)
	fmt.Println("tokenid:", token.TokenURL)
	return nil
}
