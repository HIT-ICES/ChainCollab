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
	ID string `json:"id,omitempty"` // 防报错

}

type InitParameters struct {
	Participant_1nczm69 Participant `json:"Participant_1nczm69"`
	Participant_0flfbxu Participant `json:"Participant_0flfbxu"`
	Participant_1ohclkv Participant `json:"Participant_1ohclkv"`
	Participant_05cm9yd Participant `json:"Participant_05cm9yd"`
	Participant_13ps2jw Participant `json:"Participant_13ps2jw"`

	ERCChaincodeNames map[string]string `json:"ERCChaincodeNames"`
	BpmnId            string            `json:"BpmnId"`
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

type OutputSpec struct {
	Type     string `json:"type"`
	DataType string `json:"dataType"`
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
	TokenElementID string                `json:"tokenElementID"`
	AssetType      string                `json:"assetType"`
	Operation      string                `json:"operation"`
	TokenName      string                `json:"tokenName"`
	TokenID        string                `json:"tokenId"`
	CallerID       string                `json:"caller"`
	CalleeID       []string              `json:"callee"`
	TokenType      string                `json:"tokenType"`
	TokenNumber    string                `json:"tokenNumber"`
	TokenURL       string                `json:"tokenURL"`
	State          ElementState          `json:"State"`
	RefTokenIds    []string              `json:"refTokenIds"`
	Outputs        map[string]OutputSpec `json:"outputs"`
}

type TokenElement struct {
	TokenElementID  string                `json:"tokenElementID"`
	AssetType       string                `json:"assetType"`
	Operation       string                `json:"operation"`
	CallerID        string                `json:"caller"`
	CalleeID        []string              `json:"callee"`
	State           ElementState          `json:"State"`
	OperationNumber string                `json:"operationNumber"`
	TokenKey        string                `json:"TokenKey"`
	ChaincodeName   string                `json:"chaincodeName"`
	RefTokenIds     []string              `json:"refTokenIds"`
	Outputs         map[string]OutputSpec `json:"outputs"`
}

type Token struct {
	TokenType        string            `json:"tokenType"`
	OwnerID          string            `json:"tokenOwner"`
	TokenID          string            `json:"tokenID"`
	TokenURL         string            `json:"tokenURL"`
	TokenName        string            `json:"tokenName"`
	TokenBalance     string            `json:  "tokenBalance"` // For FT
	FtBalance        map[string]string `json:"FtBalance"`
	Flagdistributive bool              `json:"flagdistributive"` //标注是否所有权创建
}

func (cc *SmartContract) CreateToken(ctx contractapi.TransactionContextInterface, instance *ContractInstance, tokenType string, ownerID string, tokenID string, tokenURL string, tokenName string, ftbalance map[string]string) (*Token, error) {
	var token Token
	// 创建Token对象
	token = Token{
		TokenType:        tokenType,
		OwnerID:          ownerID,
		TokenID:          tokenID,
		TokenURL:         tokenURL,
		TokenName:        tokenName,
		FtBalance:        ftbalance,
		Flagdistributive: false,
	}
	var tokenKey string
	if tokenType == "NFT" {
		tokenKey = "NFT_" + tokenID
	} else if tokenType == "FT" {
		tokenKey = "FT_" + tokenName
	} else if tokenType == "distributive" {
		tokenKey = "distributive_" + tokenID
	} else if tokenType == "value-added" {
		tokenKey = "value-added_" + tokenID
	}
	instance.InstanceTokens[tokenKey] = &token
	returnToken, ok := instance.InstanceTokens[tokenKey]
	if !ok {
		return nil, fmt.Errorf("无法将实例元素转换为Token")
	}
	return returnToken, nil
}

func (cc *SmartContract) CreateTokenElement(ctx contractapi.TransactionContextInterface, instance *ContractInstance, tokenElementID string, state ElementState, Jsonstr string, chaincodeName string, bpmnID string) (*TokenElement, error) {
	var fla FlatokenElement
	err := json.Unmarshal([]byte(Jsonstr), &fla)
	if err != nil {
		return nil, fmt.Errorf("failed to unmarshal FlatokenElement: %s", err.Error())
	}
	fla.TokenElementID = tokenElementID
	fla.State = state
	fla.TokenID = bpmnID + "-" + instance.InstanceID + "-" + fla.TokenID
	outputs := fla.Outputs
	if outputs == nil {
		outputs = make(map[string]OutputSpec)
	}
	//检查是否有这个元素
	var tokenKey string
	var token *Token
	if fla.AssetType == "transferable" {
		if fla.TokenType == "NFT" {
			tokenKey = "NFT_" + fla.TokenID
		} else if fla.TokenType == "FT" {
			tokenKey = "FT_" + fla.TokenName
		}
	} else if fla.AssetType == "distributive" {
		tokenKey = "distributive_" + fla.TokenID //关于分发型的实施，在ERC创建时同时创建两个代币，一个nft一个ft，但对于外部，就只有一个tokenid表示所有权符合建模
		fla.TokenType = "distributive"           //为了方便解析，对于分发型资产的tokentype和assettype均使用distributive
	} else if fla.AssetType == "value-added" {
		tokenKey = "value-added_" + fla.TokenID
		fla.TokenType = "value-added"
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
		ChaincodeName:   chaincodeName,
		RefTokenIds:     fla.RefTokenIds,
		Outputs:         outputs,
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
		if TokenElement.CalleeID == nil {
			TokenElement.CalleeID = []string{}
		}
		if TokenElement.RefTokenIds == nil {
			TokenElement.RefTokenIds = []string{}
		}
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

//		return nil
//	}
func (cc *SmartContract) GetTokenKey(ctx contractapi.TransactionContextInterface, token *Token) (string, error) {
	var resultKey string
	if token.TokenType == "NFT" {
		resultKey = "NFT_" + token.TokenID
	} else if token.TokenType == "FT" {
		resultKey = "FT_" + token.TokenName
	} else if token.TokenType == "distributive" {
		resultKey = "distributive_" + token.TokenID
	} else if token.TokenType == "value-added" {
		resultKey = "value-added_" + token.TokenID
	}
	return resultKey, nil
}

func (cc *SmartContract) changeTokenOwner(ctx contractapi.TransactionContextInterface, instance *ContractInstance, tokenkey string, ownerid string) error {
	if ownerid == "delete" {
		// 检查 token 是否存在，如果不存在，则直接返回 nil，不报错
		if _, ok := instance.InstanceTokens[tokenkey]; !ok {
			fmt.Printf("Token %s does not exist, no action needed.\n", tokenkey)
			return nil
		}

		// 使用 delete 函数删除 map 中的键值对
		delete(instance.InstanceTokens, tokenkey)
		fmt.Printf("Token %s has been deleted.\n", tokenkey)
		return nil
	}

	token, ok := instance.InstanceTokens[tokenkey]
	if !ok {
		errorMessage := fmt.Sprintf("Token %s does not exist", tokenkey)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}
	token.OwnerID = ownerid
	//打印检查一下
	fmt.Println("this token"+token.TokenID+" owner is", token.OwnerID)
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

	//print
	ownerbytes, _ := base64.StdEncoding.DecodeString(owner)
	ownerstr := string(ownerbytes)
	fmt.Println(ownerstr + ":" + balance)

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

func (cc *SmartContract) AddMintAuthority(ctx contractapi.TransactionContextInterface, initParametersBytes string) error {
	// 1. 定义一个结构体对应前端发送的 payload
	type AddAuthorityPayload struct {
		InstanceID    string   `json:"InstanceID"`
		AllowedMSPs   []string `json:"allowedMSPs"`
		ChaincodeName string   `json:"chaincodeName"`
	}

	// 2. 解析 JSON 字符串
	var payload AddAuthorityPayload
	if err := json.Unmarshal([]byte(initParametersBytes), &payload); err != nil {
		return fmt.Errorf("failed to unmarshal initParametersBytes: %v", err)
	}

	// 3. 将 allowedMSPs 转为 JSON
	allowedMSPsJson, err := json.Marshal(payload.AllowedMSPs)
	if err != nil {
		return fmt.Errorf("failed to marshal allowedMSPs: %v", err)
	}

	// 4. 构造调用参数
	_args := make([][]byte, 3)
	_args[0] = []byte("AddMintAuthority") // 调用函数
	_args[1] = []byte(payload.InstanceID) // InstanceID
	_args[2] = allowedMSPsJson            // allowedMSPs

	// 5. 调用目标链码
	cc.Invoke_Other_chaincode(
		ctx,
		payload.ChaincodeName,
		"default",
		_args,
	)

	return nil
}

func (cc *SmartContract) TokenElementInitialize(ctx contractapi.TransactionContextInterface, inputBytes string) error {
	// 解析 JSON
	var input map[string]string
	if err := json.Unmarshal([]byte(inputBytes), &input); err != nil {
		return err
	}

	name := input["name"]
	chaincodeName := input["chaincodeName"]
	erc1155flag := input["erc5521flag"]
	symbol := name
	if erc1155flag == "true" {
		_args := make([][]byte, 4)
		_args[0] = []byte("Initialize")
		_args[1] = []byte(name)
		_args[2] = []byte(symbol)
		_args[3] = []byte(chaincodeName)
		response, err := cc.Invoke_Other_chaincode(ctx, chaincodeName, "default", _args)
		if err != nil {
			return err
		}
		fmt.Print("response:")
		fmt.Println(string(response))
	} else {
		_args := make([][]byte, 3)
		_args[0] = []byte("Initialize")
		_args[1] = []byte(name)
		_args[2] = []byte(symbol)

		response, err := cc.Invoke_Other_chaincode(ctx, chaincodeName, "default", _args)
		if err != nil {
			return err
		}
		fmt.Print("response:")
		fmt.Println(string(response))
	}

	return nil
}

func (cc *SmartContract) TokenElementInitializeFT(ctx contractapi.TransactionContextInterface, inputBytes string) error {
	// 解析 JSON
	var input map[string]string
	if err := json.Unmarshal([]byte(inputBytes), &input); err != nil {
		return err
	}

	name := input["name"]
	chaincodeName := input["chaincodeName"]
	symbol := name
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

func (cc *SmartContract) changeTokenFlag(ctx contractapi.TransactionContextInterface, instance *ContractInstance, tokenkey string, flag bool) error {
	token, ok := instance.InstanceTokens[tokenkey]
	if !ok {
		errorMessage := fmt.Sprintf("Token %s does not exist", tokenkey)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}
	token.Flagdistributive = flag

	return nil
}

func (cc *SmartContract) changeTokenURL(ctx contractapi.TransactionContextInterface, instance *ContractInstance, tokenKey string, tokenURL string) error {
	token, ok := instance.InstanceTokens[tokenKey]
	if !ok {
		errorMessage := fmt.Sprintf("Token %s does not exist", tokenKey)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	token.TokenURL = tokenURL
	fmt.Println("set token", token.TokenID, "TokenURL to", tokenURL)
	return nil
}

func (cc *SmartContract) SetURLData(ctx contractapi.TransactionContextInterface, instanceID string, key string, value string) error {

	storeKey := "URLdatastorm_" + instanceID
	storeBytes, err := ctx.GetStub().GetState(storeKey)
	if err != nil {
		return err
	}

	store := make(map[string]string)

	if len(storeBytes) != 0 {
		json.Unmarshal(storeBytes, &store)
	}

	store[key] = value

	newBytes, _ := json.Marshal(store)
	return ctx.GetStub().PutState(storeKey, newBytes)
}

func (cc *SmartContract) GetURLData(ctx contractapi.TransactionContextInterface, instanceID string, key string) (string, error) {

	storeKey := "URLdatastorm_" + instanceID
	storeBytes, err := ctx.GetStub().GetState(storeKey)
	if err != nil {
		return "", err
	}

	if len(storeBytes) == 0 {
		return "", nil
	}

	store := make(map[string]string)
	json.Unmarshal(storeBytes, &store)

	return store[key], nil
}

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

	cc.CreateParticipant(ctx, &instance, "Participant_1nczm69", initParameters.Participant_1nczm69.MSP, initParameters.Participant_1nczm69.Attributes, initParameters.Participant_1nczm69.X509, initParameters.Participant_1nczm69.IsMulti, 0, 0)
	cc.CreateParticipant(ctx, &instance, "Participant_0flfbxu", initParameters.Participant_0flfbxu.MSP, initParameters.Participant_0flfbxu.Attributes, initParameters.Participant_0flfbxu.X509, initParameters.Participant_0flfbxu.IsMulti, 0, 0)
	cc.CreateParticipant(ctx, &instance, "Participant_1ohclkv", initParameters.Participant_1ohclkv.MSP, initParameters.Participant_1ohclkv.Attributes, initParameters.Participant_1ohclkv.X509, initParameters.Participant_1ohclkv.IsMulti, 0, 0)
	cc.CreateParticipant(ctx, &instance, "Participant_05cm9yd", initParameters.Participant_05cm9yd.MSP, initParameters.Participant_05cm9yd.Attributes, initParameters.Participant_05cm9yd.X509, initParameters.Participant_05cm9yd.IsMulti, 0, 0)
	cc.CreateParticipant(ctx, &instance, "Participant_13ps2jw", initParameters.Participant_13ps2jw.MSP, initParameters.Participant_13ps2jw.Attributes, initParameters.Participant_13ps2jw.X509, initParameters.Participant_13ps2jw.IsMulti, 0, 0)
	cc.CreateActionEvent(ctx, &instance, "Event_0bofw6q", ENABLED)

	cc.CreateActionEvent(ctx, &instance, "Event_0avtwbl", DISABLED)

	cc.CreateMessage(ctx, &instance, "Message_1hus4uj", "Participant_13ps2jw", "Participant_0flfbxu", "", DISABLED, `{"properties":{"Trained Model":{"type":"string","description":""}},"required":[],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_0mjfhno", "Participant_0flfbxu", "Participant_13ps2jw", "", DISABLED, `{"properties":{"Merged Data":{"type":"string","description":""}},"required":[],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_0b9ois4", "Participant_05cm9yd", "Participant_0flfbxu", "", DISABLED, `{"properties":{"Cleaned Data":{"type":"string","description":""}},"required":[],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_1ezn1zg", "Participant_1ohclkv", "Participant_0flfbxu", "", DISABLED, `{"properties":{"Cleaned Data":{"type":"string","description":""}},"required":[],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_0u8zgjt", "Participant_0flfbxu", "Participant_05cm9yd", "", DISABLED, `{"properties":{},"required":[],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_1ejama4", "Participant_0flfbxu", "Participant_1ohclkv", "", DISABLED, `{"properties":{"Original Data":{"type":"string","description":""}},"required":[],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_0bwmjy1", "Participant_1nczm69", "Participant_0flfbxu", "", DISABLED, `{"properties":{"AI Data":{"type":"string","description":""}},"required":[],"files":{},"file required":[]}`)
	cc.CreateGateway(ctx, &instance, "Gateway_13uxpvw", DISABLED)

	cc.CreateGateway(ctx, &instance, "Gateway_13efgz8", DISABLED)

	cc.CreateTokenElement(ctx, &instance, "Activity_0vjedml", DISABLED, `{"assetType":"value-added","operation":"branch","tokenName":"ai data","caller":"Participant_1nczm69","tokenId":"1"}`, initParameters.ERCChaincodeNames["Activity_0vjedml"], initParameters.BpmnId)
	cc.CreateTokenElement(ctx, &instance, "Activity_0z4hvvs", DISABLED, `{"assetType":"value-added","operation":"branch","tokenName":"ai data","caller":"Participant_1ohclkv","tokenId":"2","refTokenIds":["1"]}`, initParameters.ERCChaincodeNames["Activity_0z4hvvs"], initParameters.BpmnId)
	cc.CreateTokenElement(ctx, &instance, "Activity_1pvlgsk", DISABLED, `{"assetType":"value-added","operation":"branch","tokenName":"ai data","caller":"Participant_05cm9yd","tokenId":"3","refTokenIds":["1"]}`, initParameters.ERCChaincodeNames["Activity_1pvlgsk"], initParameters.BpmnId)
	cc.CreateTokenElement(ctx, &instance, "Activity_1a1v36t", DISABLED, `{"assetType":"value-added","operation":"branch","tokenName":"ai data","caller":"Participant_0flfbxu","tokenId":"4","refTokenIds":["2","3"]}`, initParameters.ERCChaincodeNames["Activity_1a1v36t"], initParameters.BpmnId)

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

func (cc *SmartContract) Event_0bofw6q(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)

	actionEvent, err := cc.ReadEvent(ctx, instanceID, "Event_0bofw6q")
	if err != nil {
		return err
	}

	if actionEvent.EventState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", actionEvent.EventID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeEventState(ctx, instance, "Event_0bofw6q", COMPLETED)
	stub.SetEvent("Event_0bofw6q", []byte("Contract has been started successfully"))
	cc.SetInstance(ctx, instance)

	cc.changeTokenElementState(ctx, instance, "Activity_0vjedml", ENABLED)

	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_0bwmjy1_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_0bwmjy1")
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
	cc.ChangeMsgState(ctx, instance, "Message_0bwmjy1", COMPLETED)

	stub.SetEvent("Message_0bwmjy1", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	cc.ChangeGtwState(ctx, instance, "Gateway_13uxpvw", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Gateway_13uxpvw(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	gtw, err := cc.ReadGtw(ctx, instanceID, "Gateway_13uxpvw")
	if err != nil {
		return err
	}

	if gtw.GatewayState != ENABLED {
		errorMessage := fmt.Sprintf("Gateway state %s is not allowed", gtw.GatewayID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeGtwState(ctx, instance, gtw.GatewayID, COMPLETED)
	stub.SetEvent("Gateway_13uxpvw", []byte("Gateway has been done"))
	cc.SetInstance(ctx, instance)

	cc.ChangeMsgState(ctx, instance, "Message_1ejama4", ENABLED)
	cc.ChangeMsgState(ctx, instance, "Message_0u8zgjt", ENABLED)
	cc.SetInstance(ctx, instance)

	return nil
}

func (cc *SmartContract) Message_1ejama4_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1ejama4")
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
	cc.ChangeMsgState(ctx, instance, "Message_1ejama4", COMPLETED)

	stub.SetEvent("Message_1ejama4", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	cc.ChangeMsgState(ctx, instance, "Message_1ezn1zg", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_0u8zgjt_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_0u8zgjt")
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
	cc.ChangeMsgState(ctx, instance, "Message_0u8zgjt", COMPLETED)

	stub.SetEvent("Message_0u8zgjt", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	cc.ChangeMsgState(ctx, instance, "Message_0b9ois4", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_1ezn1zg_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1ezn1zg")
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
	cc.ChangeMsgState(ctx, instance, "Message_1ezn1zg", COMPLETED)

	stub.SetEvent("Message_1ezn1zg", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	cc.changeTokenElementState(ctx, instance, "Activity_0z4hvvs", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_0b9ois4_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_0b9ois4")
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
	cc.ChangeMsgState(ctx, instance, "Message_0b9ois4", COMPLETED)

	stub.SetEvent("Message_0b9ois4", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	cc.changeTokenElementState(ctx, instance, "Activity_1pvlgsk", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Gateway_13efgz8(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	gtw, err := cc.ReadGtw(ctx, instanceID, "Gateway_13efgz8")
	if err != nil {
		return err
	}

	if gtw.GatewayState != ENABLED {
		errorMessage := fmt.Sprintf("Gateway state %s is not allowed", gtw.GatewayID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeGtwState(ctx, instance, gtw.GatewayID, COMPLETED)
	stub.SetEvent("Gateway_13efgz8", []byte("Gateway has been done"))

	cc.changeTokenElementState(ctx, instance, "Activity_1a1v36t", ENABLED)

	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_0mjfhno_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_0mjfhno")
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
	cc.ChangeMsgState(ctx, instance, "Message_0mjfhno", COMPLETED)

	stub.SetEvent("Message_0mjfhno", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	cc.ChangeMsgState(ctx, instance, "Message_1hus4uj", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_1hus4uj_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1hus4uj")
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
	cc.ChangeMsgState(ctx, instance, "Message_1hus4uj", COMPLETED)

	stub.SetEvent("Message_1hus4uj", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	cc.ChangeEventState(ctx, instance, "Event_0avtwbl", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Event_0avtwbl(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	event, err := cc.ReadEvent(ctx, instanceID, "Event_0avtwbl")
	if err != nil {
		return err
	}

	if event.EventState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", event.EventID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeEventState(ctx, instance, event.EventID, COMPLETED)
	stub.SetEvent("Event_0avtwbl", []byte("EndEvent has been done"))

	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Activity_0vjedml(ctx contractapi.TransactionContextInterface, instanceID string) error {
	fmt.Println("----- Activity_0vjedml (Start) -----")

	instance, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	if instance == nil {
		return errors.New("instanceID does not exist")
	}

	// 1. 读 TokenElement + Token（只是校验，不在这里 mint）
	tokenElement, err := cc.ReadTokenElement(ctx, instanceID, "Activity_0vjedml")
	if err != nil {
		return err
	}
	_, err = cc.ReadToken(ctx, instanceID, tokenElement.TokenKey)
	if err != nil {
		return err
	}

	// 2. 必须是 ENABLED 才能进入资产上传流程
	if tokenElement.State != ENABLED {
		errorMessage := fmt.Sprintf("TokenElement state %s is not allowed", tokenElement.TokenElementID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	// 3. 校验调用者身份（沿用你原来的逻辑）
	nowid64, _ := ctx.GetClientIdentity().GetID()
	nowidBytes, _ := base64.StdEncoding.DecodeString(nowid64)
	nowid := string(nowidBytes)
	fmt.Println("nowid:", nowid)

	callid, _ := cc.ParticipantToidentity(ctx, instanceID, tokenElement.CallerID)
	if nowid != callid {
		errorMessage := fmt.Sprintf("Caller %s is not allowed to call this function", nowid)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	eventPayload := map[string]string{
		"InstanceID": instanceID,
		"ActivityID": "Activity_0vjedml",
		"Func":       "Activity_0vjedml_Continue",
	}
	eventPayloadAsBytes, err := json.Marshal(eventPayload)
	if err != nil {
		return fmt.Errorf("failed to marshal event payload: %v", err)
	}

	if err := ctx.GetStub().SetEvent("AssetUploadRequired", eventPayloadAsBytes); err != nil {
		return fmt.Errorf("failed to set AssetUploadRequired event: %v", err)
	}

	// 5. 标记 TokenElement 状态为 WAITINGFORCONFIRMATION
	if err := cc.changeTokenElementState(ctx, instance, "Activity_0vjedml", WAITINGFORCONFIRMATION); err != nil {
		return err
	}
	if err := cc.SetInstance(ctx, instance); err != nil {
		return err
	}

	return nil
}

func (cc *SmartContract) Activity_0vjedml_Continue(ctx contractapi.TransactionContextInterface, testtokenid string, testreftokenid []string, instanceID string) error {
	fmt.Println("----- Activity_0vjedml_Continue -----")

	instance, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	if instance == nil {
		return errors.New("instanceID does not exist")
	}

	// 1. 读 TokenElement
	tokenElement, err := cc.ReadTokenElement(ctx, instanceID, "Activity_0vjedml")
	if err != nil {
		return err
	}

	// 2. 必须是 WAITINGFORCONFIRMATION
	// if tokenElement.State != WAITINGFORCONFIRMATION {
	// 	errorMessage := fmt.Sprintf(
	// 		"TokenElement state %s is not allowed (expect WAITINGFORCONFIRMATION)",
	// 		tokenElement.TokenElementID,
	// 	)
	// 	fmt.Println(errorMessage)
	// 	return fmt.Errorf(errorMessage)
	// }

	// 3.读 CID
	// cid, err := cc.GetURLData(ctx, instanceID, "Activity_0vjedml")
	// fmt.Println(cid)
	// 4. 在当前 instance 里真正更新 TokenURL
	tokenURI := "ipfs://test"
	// if err := cc.changeTokenURL(ctx, instance, tokenElement.TokenKey, tokenURI); err != nil {
	// 	return err
	// }
	fmt.Println(tokenURI)
	// 从 instance 里拿出最新的 token，用来调用 ERC 链码
	// token, ok := instance.InstanceTokens[tokenElement.TokenKey]
	// if !ok {
	// 	return fmt.Errorf("Token %s does not exist", tokenElement.TokenKey)
	// }
	// fmt.Println(token.TokenURL)
	// 5. 调 ERC 的 MintWithTokenURI
	nowid64, _ := ctx.GetClientIdentity().GetID()
	nowidBytes, _ := base64.StdEncoding.DecodeString(nowid64)
	nowid := string(nowidBytes)
	fmt.Println("nowid:", nowid)

	//parts := strings.SplitN(token.TokenID, "-", 3)
	//bpmnID := parts[0]
	// parts := strings.Split(token.TokenID, "-")
	// if len(parts) < 3 {
	// 	return fmt.Errorf("invalid tokenID: %s", token.TokenID)
	// }
	// bpmnID := strings.Join(parts[:len(parts)-2], "-")

	callid, _ := cc.ParticipantToidentity(ctx, instanceID, tokenElement.CallerID)
	if nowid != callid {
		errorMessage := fmt.Sprintf("Caller %s is not allowed to call this function", nowid)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}
	// if tokenElement.Operation == "merge" {
	// 	if tokenElement.RefTokenIds == nil {
	// 		return fmt.Errorf("merge operation can not be empty")
	// 	}
	// }
	tempRefTokenIds := testreftokenid
	// if tempRefTokenIds == nil {
	// 	tempRefTokenIds = []string{}
	// } else {
	// 	for i := 0; i < len(tempRefTokenIds); i++ {
	// 		tempRefTokenIds[i] = bpmnID + "-" + instanceID + "-" + tempRefTokenIds[i]
	// 	}
	// }
	// if err != nil {
	// 	return fmt.Errorf("failed to marshal RefTokenIds: %v", err)
	// }
	// 轮到他运行，调用
	chaincodeName := tokenElement.ChaincodeName

	var tempChaincodes []string
	var tempTokenIds [][]string

	if len(tempRefTokenIds) > 0 {
		// 有父节点才写入引用
		tempChaincodes = []string{chaincodeName}
		tempTokenIds = [][]string{tempRefTokenIds}
	} else {
		// 完全空引用，表示普通 mint
		tempChaincodes = []string{}
		tempTokenIds = [][]string{}
	}

	chaincodesJson, err := json.Marshal(tempChaincodes)
	if err != nil {
		return fmt.Errorf("failed to marshal chaincodeName list: %v", err)
	}

	tokenIdsJson, err := json.Marshal(tempTokenIds)
	if err != nil {
		return fmt.Errorf("failed to marshal tokenIds list: %v", err)
	}

	// 组装 SafeMint 参数
	_args := make([][]byte, 6)
	_args[0] = []byte("SafeMint")
	_args[1] = []byte(testtokenid)
	_args[2] = []byte(tokenURI)
	_args[3] = []byte(instanceID)
	_args[4] = chaincodesJson
	_args[5] = tokenIdsJson

	// 跨链码调用 SafeMint
	getpayload, err := cc.Invoke_Other_chaincode(ctx, chaincodeName, "default", _args)
	if err != nil {
		fmt.Println(err)
		return errors.New("fail to invoke ERC5521")
	}
	if len(getpayload) == 0 || string(getpayload) == "null" {
		return errors.New("did not create successfully")
	}
	// //打印
	// var data map[string]interface{}
	// err = json.Unmarshal(getpayload, &data)
	// if err != nil {
	// 	return fmt.Errorf("failed to parse JSON: %v", err)
	// }

	// owner := data["owner"].(string) //
	// fmt.Println("payload解析出来的Owner:", owner)
	// //修改token对象的拥有者
	// cc.changeTokenOwner(ctx, instance, tokenElement.TokenKey, owner)

	// //测试一下
	// fmt.Println("TokenElement中的拥有者:", token.OwnerID)
	// //检查
	// fmt.Println("调用chaincode结束")
	// //改状态
	// cc.changeTokenElementState(ctx, instance, "Activity_0vjedml", COMPLETED)
	// cc.SetInstance(ctx, instance)
	// //检查
	// fmt.Println("Activity_0vjedml run end")
	// //gtw判断

	// cc.ChangeMsgState(ctx, instance, "Message_0bwmjy1", ENABLED)
	// cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Activity_0z4hvvs(ctx contractapi.TransactionContextInterface, instanceID string) error {
	fmt.Println("----- Activity_0z4hvvs (Start) -----")

	instance, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	if instance == nil {
		return errors.New("instanceID does not exist")
	}

	// 1. 读 TokenElement + Token（只是校验，不在这里 mint）
	tokenElement, err := cc.ReadTokenElement(ctx, instanceID, "Activity_0z4hvvs")
	if err != nil {
		return err
	}
	_, err = cc.ReadToken(ctx, instanceID, tokenElement.TokenKey)
	if err != nil {
		return err
	}

	// 2. 必须是 ENABLED 才能进入资产上传流程
	if tokenElement.State != ENABLED {
		errorMessage := fmt.Sprintf("TokenElement state %s is not allowed", tokenElement.TokenElementID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	// 3. 校验调用者身份（沿用你原来的逻辑）
	nowid64, _ := ctx.GetClientIdentity().GetID()
	nowidBytes, _ := base64.StdEncoding.DecodeString(nowid64)
	nowid := string(nowidBytes)
	fmt.Println("nowid:", nowid)

	callid, _ := cc.ParticipantToidentity(ctx, instanceID, tokenElement.CallerID)
	if nowid != callid {
		errorMessage := fmt.Sprintf("Caller %s is not allowed to call this function", nowid)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	eventPayload := map[string]string{
		"InstanceID": instanceID,
		"ActivityID": "Activity_0z4hvvs",
		"Func":       "Activity_0z4hvvs_Continue",
	}
	eventPayloadAsBytes, err := json.Marshal(eventPayload)
	if err != nil {
		return fmt.Errorf("failed to marshal event payload: %v", err)
	}

	if err := ctx.GetStub().SetEvent("AssetUploadRequired", eventPayloadAsBytes); err != nil {
		return fmt.Errorf("failed to set AssetUploadRequired event: %v", err)
	}

	// 5. 标记 TokenElement 状态为 WAITINGFORCONFIRMATION
	if err := cc.changeTokenElementState(ctx, instance, "Activity_0z4hvvs", WAITINGFORCONFIRMATION); err != nil {
		return err
	}
	if err := cc.SetInstance(ctx, instance); err != nil {
		return err
	}

	return nil
}

func (cc *SmartContract) Activity_0z4hvvs_Continue(ctx contractapi.TransactionContextInterface, instanceID string) error {
	fmt.Println("----- Activity_0z4hvvs_Continue -----")

	instance, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	if instance == nil {
		return errors.New("instanceID does not exist")
	}

	// 1. 读 TokenElement
	tokenElement, err := cc.ReadTokenElement(ctx, instanceID, "Activity_0z4hvvs")
	if err != nil {
		return err
	}

	// 2. 必须是 WAITINGFORCONFIRMATION
	if tokenElement.State != WAITINGFORCONFIRMATION {
		errorMessage := fmt.Sprintf(
			"TokenElement state %s is not allowed (expect WAITINGFORCONFIRMATION)",
			tokenElement.TokenElementID,
		)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	// 3.读 CID
	cid, err := cc.GetURLData(ctx, instanceID, "Activity_0z4hvvs")
	fmt.Println(cid)
	// 4. 在当前 instance 里真正更新 TokenURL
	tokenURI := "ipfs://" + cid
	if err := cc.changeTokenURL(ctx, instance, tokenElement.TokenKey, tokenURI); err != nil {
		return err
	}
	fmt.Println(tokenURI)
	// 从 instance 里拿出最新的 token，用来调用 ERC 链码
	token, ok := instance.InstanceTokens[tokenElement.TokenKey]
	if !ok {
		return fmt.Errorf("Token %s does not exist", tokenElement.TokenKey)
	}
	fmt.Println(token.TokenURL)
	// 5. 调 ERC 的 MintWithTokenURI
	nowid64, _ := ctx.GetClientIdentity().GetID()
	nowidBytes, _ := base64.StdEncoding.DecodeString(nowid64)
	nowid := string(nowidBytes)
	fmt.Println("nowid:", nowid)

	//parts := strings.SplitN(token.TokenID, "-", 3)
	//bpmnID := parts[0]
	parts := strings.Split(token.TokenID, "-")
	if len(parts) < 3 {
		return fmt.Errorf("invalid tokenID: %s", token.TokenID)
	}
	bpmnID := strings.Join(parts[:len(parts)-2], "-")

	callid, _ := cc.ParticipantToidentity(ctx, instanceID, tokenElement.CallerID)
	if nowid != callid {
		errorMessage := fmt.Sprintf("Caller %s is not allowed to call this function", nowid)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}
	if tokenElement.Operation == "merge" {
		if tokenElement.RefTokenIds == nil {
			return fmt.Errorf("merge operation can not be empty")
		}
	}
	tempRefTokenIds := tokenElement.RefTokenIds
	if tempRefTokenIds == nil {
		tempRefTokenIds = []string{}
	} else {
		for i := 0; i < len(tempRefTokenIds); i++ {
			tempRefTokenIds[i] = bpmnID + "-" + instanceID + "-" + tempRefTokenIds[i]
		}
	}
	if err != nil {
		return fmt.Errorf("failed to marshal RefTokenIds: %v", err)
	}
	// 轮到他运行，调用
	chaincodeName := tokenElement.ChaincodeName

	var tempChaincodes []string
	var tempTokenIds [][]string

	if len(tempRefTokenIds) > 0 {
		// 有父节点才写入引用
		tempChaincodes = []string{chaincodeName}
		tempTokenIds = [][]string{tempRefTokenIds}
	} else {
		// 完全空引用，表示普通 mint
		tempChaincodes = []string{}
		tempTokenIds = [][]string{}
	}

	chaincodesJson, err := json.Marshal(tempChaincodes)
	if err != nil {
		return fmt.Errorf("failed to marshal chaincodeName list: %v", err)
	}

	tokenIdsJson, err := json.Marshal(tempTokenIds)
	if err != nil {
		return fmt.Errorf("failed to marshal tokenIds list: %v", err)
	}

	// 组装 SafeMint 参数
	_args := make([][]byte, 6)
	_args[0] = []byte("SafeMint")
	_args[1] = []byte(token.TokenID)
	_args[2] = []byte(token.TokenURL)
	_args[3] = []byte(instanceID)
	_args[4] = chaincodesJson
	_args[5] = tokenIdsJson

	// 跨链码调用 SafeMint
	getpayload, err := cc.Invoke_Other_chaincode(ctx, chaincodeName, "default", _args)
	if err != nil {
		fmt.Println(err)
		return errors.New("fail to invoke ERC5521")
	}
	if len(getpayload) == 0 || string(getpayload) == "null" {
		return errors.New("did not create successfully")
	}
	//打印
	var data map[string]interface{}
	err = json.Unmarshal(getpayload, &data)
	if err != nil {
		return fmt.Errorf("failed to parse JSON: %v", err)
	}

	owner := data["owner"].(string) //
	fmt.Println("payload解析出来的Owner:", owner)
	//修改token对象的拥有者
	cc.changeTokenOwner(ctx, instance, tokenElement.TokenKey, owner)

	//测试一下
	fmt.Println("TokenElement中的拥有者:", token.OwnerID)
	//检查
	fmt.Println("调用chaincode结束")
	//改状态
	cc.changeTokenElementState(ctx, instance, "Activity_0z4hvvs", COMPLETED)
	cc.SetInstance(ctx, instance)
	//检查
	fmt.Println("Activity_0z4hvvs run end")
	//gtw判断

	if !(func() bool {
		msg, err := cc.ReadTokenElement(ctx, instanceID, "Activity_1pvlgsk")
		return err == nil && msg.State == COMPLETED
	}()) {
		return nil
	}
	cc.ChangeGtwState(ctx, instance, "Gateway_13efgz8", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Activity_1pvlgsk(ctx contractapi.TransactionContextInterface, instanceID string) error {
	fmt.Println("----- Activity_1pvlgsk (Start) -----")

	instance, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	if instance == nil {
		return errors.New("instanceID does not exist")
	}

	// 1. 读 TokenElement + Token（只是校验，不在这里 mint）
	tokenElement, err := cc.ReadTokenElement(ctx, instanceID, "Activity_1pvlgsk")
	if err != nil {
		return err
	}
	_, err = cc.ReadToken(ctx, instanceID, tokenElement.TokenKey)
	if err != nil {
		return err
	}

	// 2. 必须是 ENABLED 才能进入资产上传流程
	if tokenElement.State != ENABLED {
		errorMessage := fmt.Sprintf("TokenElement state %s is not allowed", tokenElement.TokenElementID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	// 3. 校验调用者身份（沿用你原来的逻辑）
	nowid64, _ := ctx.GetClientIdentity().GetID()
	nowidBytes, _ := base64.StdEncoding.DecodeString(nowid64)
	nowid := string(nowidBytes)
	fmt.Println("nowid:", nowid)

	callid, _ := cc.ParticipantToidentity(ctx, instanceID, tokenElement.CallerID)
	if nowid != callid {
		errorMessage := fmt.Sprintf("Caller %s is not allowed to call this function", nowid)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	eventPayload := map[string]string{
		"InstanceID": instanceID,
		"ActivityID": "Activity_1pvlgsk",
		"Func":       "Activity_1pvlgsk_Continue",
	}
	eventPayloadAsBytes, err := json.Marshal(eventPayload)
	if err != nil {
		return fmt.Errorf("failed to marshal event payload: %v", err)
	}

	if err := ctx.GetStub().SetEvent("AssetUploadRequired", eventPayloadAsBytes); err != nil {
		return fmt.Errorf("failed to set AssetUploadRequired event: %v", err)
	}

	// 5. 标记 TokenElement 状态为 WAITINGFORCONFIRMATION
	if err := cc.changeTokenElementState(ctx, instance, "Activity_1pvlgsk", WAITINGFORCONFIRMATION); err != nil {
		return err
	}
	if err := cc.SetInstance(ctx, instance); err != nil {
		return err
	}

	return nil
}

func (cc *SmartContract) Activity_1pvlgsk_Continue(ctx contractapi.TransactionContextInterface, instanceID string) error {
	fmt.Println("----- Activity_1pvlgsk_Continue -----")

	instance, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	if instance == nil {
		return errors.New("instanceID does not exist")
	}

	// 1. 读 TokenElement
	tokenElement, err := cc.ReadTokenElement(ctx, instanceID, "Activity_1pvlgsk")
	if err != nil {
		return err
	}

	// 2. 必须是 WAITINGFORCONFIRMATION
	if tokenElement.State != WAITINGFORCONFIRMATION {
		errorMessage := fmt.Sprintf(
			"TokenElement state %s is not allowed (expect WAITINGFORCONFIRMATION)",
			tokenElement.TokenElementID,
		)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	// 3.读 CID
	cid, err := cc.GetURLData(ctx, instanceID, "Activity_1pvlgsk")
	fmt.Println(cid)
	// 4. 在当前 instance 里真正更新 TokenURL
	tokenURI := "ipfs://" + cid
	if err := cc.changeTokenURL(ctx, instance, tokenElement.TokenKey, tokenURI); err != nil {
		return err
	}
	fmt.Println(tokenURI)
	// 从 instance 里拿出最新的 token，用来调用 ERC 链码
	token, ok := instance.InstanceTokens[tokenElement.TokenKey]
	if !ok {
		return fmt.Errorf("Token %s does not exist", tokenElement.TokenKey)
	}
	fmt.Println(token.TokenURL)
	// 5. 调 ERC 的 MintWithTokenURI
	nowid64, _ := ctx.GetClientIdentity().GetID()
	nowidBytes, _ := base64.StdEncoding.DecodeString(nowid64)
	nowid := string(nowidBytes)
	fmt.Println("nowid:", nowid)

	//parts := strings.SplitN(token.TokenID, "-", 3)
	//bpmnID := parts[0]
	parts := strings.Split(token.TokenID, "-")
	if len(parts) < 3 {
		return fmt.Errorf("invalid tokenID: %s", token.TokenID)
	}
	bpmnID := strings.Join(parts[:len(parts)-2], "-")

	callid, _ := cc.ParticipantToidentity(ctx, instanceID, tokenElement.CallerID)
	if nowid != callid {
		errorMessage := fmt.Sprintf("Caller %s is not allowed to call this function", nowid)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}
	if tokenElement.Operation == "merge" {
		if tokenElement.RefTokenIds == nil {
			return fmt.Errorf("merge operation can not be empty")
		}
	}
	tempRefTokenIds := tokenElement.RefTokenIds
	if tempRefTokenIds == nil {
		tempRefTokenIds = []string{}
	} else {
		for i := 0; i < len(tempRefTokenIds); i++ {
			tempRefTokenIds[i] = bpmnID + "-" + instanceID + "-" + tempRefTokenIds[i]
		}
	}
	if err != nil {
		return fmt.Errorf("failed to marshal RefTokenIds: %v", err)
	}
	// 轮到他运行，调用
	chaincodeName := tokenElement.ChaincodeName

	var tempChaincodes []string
	var tempTokenIds [][]string

	if len(tempRefTokenIds) > 0 {
		// 有父节点才写入引用
		tempChaincodes = []string{chaincodeName}
		tempTokenIds = [][]string{tempRefTokenIds}
	} else {
		// 完全空引用，表示普通 mint
		tempChaincodes = []string{}
		tempTokenIds = [][]string{}
	}

	chaincodesJson, err := json.Marshal(tempChaincodes)
	if err != nil {
		return fmt.Errorf("failed to marshal chaincodeName list: %v", err)
	}

	tokenIdsJson, err := json.Marshal(tempTokenIds)
	if err != nil {
		return fmt.Errorf("failed to marshal tokenIds list: %v", err)
	}

	// 组装 SafeMint 参数
	_args := make([][]byte, 6)
	_args[0] = []byte("SafeMint")
	_args[1] = []byte(token.TokenID)
	_args[2] = []byte(token.TokenURL)
	_args[3] = []byte(instanceID)
	_args[4] = chaincodesJson
	_args[5] = tokenIdsJson

	// 跨链码调用 SafeMint
	getpayload, err := cc.Invoke_Other_chaincode(ctx, chaincodeName, "default", _args)
	if err != nil {
		fmt.Println(err)
		return errors.New("fail to invoke ERC5521")
	}
	if len(getpayload) == 0 || string(getpayload) == "null" {
		return errors.New("did not create successfully")
	}
	//打印
	var data map[string]interface{}
	err = json.Unmarshal(getpayload, &data)
	if err != nil {
		return fmt.Errorf("failed to parse JSON: %v", err)
	}

	owner := data["owner"].(string) //
	fmt.Println("payload解析出来的Owner:", owner)
	//修改token对象的拥有者
	cc.changeTokenOwner(ctx, instance, tokenElement.TokenKey, owner)

	//测试一下
	fmt.Println("TokenElement中的拥有者:", token.OwnerID)
	//检查
	fmt.Println("调用chaincode结束")
	//改状态
	cc.changeTokenElementState(ctx, instance, "Activity_1pvlgsk", COMPLETED)
	cc.SetInstance(ctx, instance)
	//检查
	fmt.Println("Activity_1pvlgsk run end")
	//gtw判断

	if !(func() bool {
		msg, err := cc.ReadTokenElement(ctx, instanceID, "Activity_0z4hvvs")
		return err == nil && msg.State == COMPLETED
	}()) {
		return nil
	}
	cc.ChangeGtwState(ctx, instance, "Gateway_13efgz8", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Activity_1a1v36t(ctx contractapi.TransactionContextInterface, instanceID string) error {
	fmt.Println("----- Activity_1a1v36t (Start) -----")

	instance, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	if instance == nil {
		return errors.New("instanceID does not exist")
	}

	// 1. 读 TokenElement + Token（只是校验，不在这里 mint）
	tokenElement, err := cc.ReadTokenElement(ctx, instanceID, "Activity_1a1v36t")
	if err != nil {
		return err
	}
	_, err = cc.ReadToken(ctx, instanceID, tokenElement.TokenKey)
	if err != nil {
		return err
	}

	// 2. 必须是 ENABLED 才能进入资产上传流程
	if tokenElement.State != ENABLED {
		errorMessage := fmt.Sprintf("TokenElement state %s is not allowed", tokenElement.TokenElementID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	// 3. 校验调用者身份（沿用你原来的逻辑）
	nowid64, _ := ctx.GetClientIdentity().GetID()
	nowidBytes, _ := base64.StdEncoding.DecodeString(nowid64)
	nowid := string(nowidBytes)
	fmt.Println("nowid:", nowid)

	callid, _ := cc.ParticipantToidentity(ctx, instanceID, tokenElement.CallerID)
	if nowid != callid {
		errorMessage := fmt.Sprintf("Caller %s is not allowed to call this function", nowid)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	eventPayload := map[string]string{
		"InstanceID": instanceID,
		"ActivityID": "Activity_1a1v36t",
		"Func":       "Activity_1a1v36t_Continue",
	}
	eventPayloadAsBytes, err := json.Marshal(eventPayload)
	if err != nil {
		return fmt.Errorf("failed to marshal event payload: %v", err)
	}

	if err := ctx.GetStub().SetEvent("AssetUploadRequired", eventPayloadAsBytes); err != nil {
		return fmt.Errorf("failed to set AssetUploadRequired event: %v", err)
	}

	// 5. 标记 TokenElement 状态为 WAITINGFORCONFIRMATION
	if err := cc.changeTokenElementState(ctx, instance, "Activity_1a1v36t", WAITINGFORCONFIRMATION); err != nil {
		return err
	}
	if err := cc.SetInstance(ctx, instance); err != nil {
		return err
	}

	return nil
}

func (cc *SmartContract) Activity_1a1v36t_Continue(ctx contractapi.TransactionContextInterface, instanceID string) error {
	fmt.Println("----- Activity_1a1v36t_Continue -----")

	instance, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	if instance == nil {
		return errors.New("instanceID does not exist")
	}

	// 1. 读 TokenElement
	tokenElement, err := cc.ReadTokenElement(ctx, instanceID, "Activity_1a1v36t")
	if err != nil {
		return err
	}

	// 2. 必须是 WAITINGFORCONFIRMATION
	if tokenElement.State != WAITINGFORCONFIRMATION {
		errorMessage := fmt.Sprintf(
			"TokenElement state %s is not allowed (expect WAITINGFORCONFIRMATION)",
			tokenElement.TokenElementID,
		)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	// 3.读 CID
	cid, err := cc.GetURLData(ctx, instanceID, "Activity_1a1v36t")
	fmt.Println(cid)
	// 4. 在当前 instance 里真正更新 TokenURL
	tokenURI := "ipfs://" + cid
	if err := cc.changeTokenURL(ctx, instance, tokenElement.TokenKey, tokenURI); err != nil {
		return err
	}
	fmt.Println(tokenURI)
	// 从 instance 里拿出最新的 token，用来调用 ERC 链码
	token, ok := instance.InstanceTokens[tokenElement.TokenKey]
	if !ok {
		return fmt.Errorf("Token %s does not exist", tokenElement.TokenKey)
	}
	fmt.Println(token.TokenURL)
	// 5. 调 ERC 的 MintWithTokenURI
	nowid64, _ := ctx.GetClientIdentity().GetID()
	nowidBytes, _ := base64.StdEncoding.DecodeString(nowid64)
	nowid := string(nowidBytes)
	fmt.Println("nowid:", nowid)

	//parts := strings.SplitN(token.TokenID, "-", 3)
	//bpmnID := parts[0]
	parts := strings.Split(token.TokenID, "-")
	if len(parts) < 3 {
		return fmt.Errorf("invalid tokenID: %s", token.TokenID)
	}
	bpmnID := strings.Join(parts[:len(parts)-2], "-")

	callid, _ := cc.ParticipantToidentity(ctx, instanceID, tokenElement.CallerID)
	if nowid != callid {
		errorMessage := fmt.Sprintf("Caller %s is not allowed to call this function", nowid)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}
	if tokenElement.Operation == "merge" {
		if tokenElement.RefTokenIds == nil {
			return fmt.Errorf("merge operation can not be empty")
		}
	}
	tempRefTokenIds := tokenElement.RefTokenIds
	if tempRefTokenIds == nil {
		tempRefTokenIds = []string{}
	} else {
		for i := 0; i < len(tempRefTokenIds); i++ {
			tempRefTokenIds[i] = bpmnID + "-" + instanceID + "-" + tempRefTokenIds[i]
		}
	}
	if err != nil {
		return fmt.Errorf("failed to marshal RefTokenIds: %v", err)
	}
	// 轮到他运行，调用
	chaincodeName := tokenElement.ChaincodeName

	var tempChaincodes []string
	var tempTokenIds [][]string

	if len(tempRefTokenIds) > 0 {
		// 有父节点才写入引用
		tempChaincodes = []string{chaincodeName}
		tempTokenIds = [][]string{tempRefTokenIds}
	} else {
		// 完全空引用，表示普通 mint
		tempChaincodes = []string{}
		tempTokenIds = [][]string{}
	}

	chaincodesJson, err := json.Marshal(tempChaincodes)
	if err != nil {
		return fmt.Errorf("failed to marshal chaincodeName list: %v", err)
	}

	tokenIdsJson, err := json.Marshal(tempTokenIds)
	if err != nil {
		return fmt.Errorf("failed to marshal tokenIds list: %v", err)
	}

	// 组装 SafeMint 参数
	_args := make([][]byte, 6)
	_args[0] = []byte("SafeMint")
	_args[1] = []byte(token.TokenID)
	_args[2] = []byte(token.TokenURL)
	_args[3] = []byte(instanceID)
	_args[4] = chaincodesJson
	_args[5] = tokenIdsJson

	// 跨链码调用 SafeMint
	getpayload, err := cc.Invoke_Other_chaincode(ctx, chaincodeName, "default", _args)
	if err != nil {
		fmt.Println(err)
		return errors.New("fail to invoke ERC5521")
	}
	if len(getpayload) == 0 || string(getpayload) == "null" {
		return errors.New("did not create successfully")
	}
	//打印
	var data map[string]interface{}
	err = json.Unmarshal(getpayload, &data)
	if err != nil {
		return fmt.Errorf("failed to parse JSON: %v", err)
	}

	owner := data["owner"].(string) //
	fmt.Println("payload解析出来的Owner:", owner)
	//修改token对象的拥有者
	cc.changeTokenOwner(ctx, instance, tokenElement.TokenKey, owner)

	//测试一下
	fmt.Println("TokenElement中的拥有者:", token.OwnerID)
	//检查
	fmt.Println("调用chaincode结束")
	//改状态
	cc.changeTokenElementState(ctx, instance, "Activity_1a1v36t", COMPLETED)
	cc.SetInstance(ctx, instance)
	//检查
	fmt.Println("Activity_1a1v36t run end")
	//gtw判断

	cc.ChangeMsgState(ctx, instance, "Message_0mjfhno", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}
