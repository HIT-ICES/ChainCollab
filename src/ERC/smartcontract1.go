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
	UriTest   string `json:"UriTest"`
	OwnerTest string `json:"OwnerTest"`
}

type InitParameters struct {
	Participant_12jdsig Participant `json:"Participant_12jdsig"`
	Participant_18g06ah Participant `json:"Participant_18g06ah"`
	Participant_121jlha Participant `json:"Participant_121jlha"`
	Participant_0wg64sj Participant `json:"Participant_0wg64sj"`
	Participant_1incub6 Participant `json:"Participant_1incub6"`

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
	TokenID          string            `json:"tokenID"`
	TokenURL         string            `json:"tokenURL"`
	TokenName        string            `json:"tokenName"`
	TokenBalance     string            `json:  "tokenBalance"` // For FT
	FtBalance        map[string]string `json:"FtBalance"`
	Flagdistributive bool              `json:"flagdistributive"` //标注是否所有权创建
}

func (cc *SmartContract) CreateToken(ctx contractapi.TransactionContextInterface, instance *ContractInstance, tokenType string, tokenID string, tokenURL string, tokenName string, ftbalance map[string]string) (*Token, error) {
	var token Token
	// 创建Token对象
	token = Token{
		TokenType:        tokenType,
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
		token, err = cc.CreateToken(ctx, instance, fla.TokenType, fla.TokenID, fla.TokenURL, fla.TokenName, ftbalance)
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

	cc.CreateParticipant(ctx, &instance, "Participant_12jdsig", initParameters.Participant_12jdsig.MSP, initParameters.Participant_12jdsig.Attributes, initParameters.Participant_12jdsig.X509, initParameters.Participant_12jdsig.IsMulti, 0, 0)
	cc.CreateParticipant(ctx, &instance, "Participant_18g06ah", initParameters.Participant_18g06ah.MSP, initParameters.Participant_18g06ah.Attributes, initParameters.Participant_18g06ah.X509, initParameters.Participant_18g06ah.IsMulti, 0, 0)
	cc.CreateParticipant(ctx, &instance, "Participant_121jlha", initParameters.Participant_121jlha.MSP, initParameters.Participant_121jlha.Attributes, initParameters.Participant_121jlha.X509, initParameters.Participant_121jlha.IsMulti, 0, 0)
	cc.CreateParticipant(ctx, &instance, "Participant_0wg64sj", initParameters.Participant_0wg64sj.MSP, initParameters.Participant_0wg64sj.Attributes, initParameters.Participant_0wg64sj.X509, initParameters.Participant_0wg64sj.IsMulti, 0, 0)
	cc.CreateParticipant(ctx, &instance, "Participant_1incub6", initParameters.Participant_1incub6.MSP, initParameters.Participant_1incub6.Attributes, initParameters.Participant_1incub6.X509, initParameters.Participant_1incub6.IsMulti, 0, 0)
	cc.CreateActionEvent(ctx, &instance, "Event_1so6gi5", ENABLED)

	cc.CreateActionEvent(ctx, &instance, "Event_1r44vsj", DISABLED)

	cc.CreateMessage(ctx, &instance, "Message_1wyvezt", "Participant_18g06ah", "Participant_12jdsig", "", DISABLED, `{"properties":{"deliverd_product":{"type":"string","description":""}},"required":[],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_10m6wae", "Participant_18g06ah", "Participant_12jdsig", "", DISABLED, `{"properties":{"report":{"type":"string","description":""}},"required":[],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_0olnqt0", "Participant_1incub6", "Participant_18g06ah", "", DISABLED, `{"properties":{"deliverd_order":{"type":"string","description":""}},"required":[],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_1kqcpl3", "Participant_0wg64sj", "Participant_1incub6", "", DISABLED, `{"properties":{"waybill":{"type":"string","description":""}},"required":[],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_1v05oen", "Participant_0wg64sj", "Participant_1incub6", "", DISABLED, `{"properties":{"provided_details":{"type":"string","description":""}},"required":[],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_09uka8c", "Participant_1incub6", "Participant_0wg64sj", "", DISABLED, `{"properties":{"requested_details":{"type":"string","description":""}},"required":[],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_0dy0w96", "Participant_12jdsig", "Participant_1incub6", "", DISABLED, `{"properties":{"transport_order":{"type":"string","description":""}},"required":[],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_0wvtw7k", "Participant_12jdsig", "Participant_0wg64sj", "", DISABLED, `{"properties":{"fwd_order":{"type":"string","description":""}},"required":[],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_15pq051", "Participant_18g06ah", "Participant_121jlha", "", DISABLED, `{"properties":{"placed_order":{"type":"string","description":""}},"required":[],"files":{},"file required":[]}`)
	cc.CreateMessage(ctx, &instance, "Message_1f0g7ng", "Participant_12jdsig", "Participant_18g06ah", "", DISABLED, `{"properties":{"order":{"type":"string","description":""}},"required":[],"files":{},"file required":[]}`)
	cc.CreateGateway(ctx, &instance, "Gateway_1yei1dm", DISABLED)

	cc.CreateGateway(ctx, &instance, "Gateway_0n7lupx", DISABLED)

	cc.CreateTokenElement(ctx, &instance, "Activity_0i3c0p3", DISABLED, `{"assetType":"transferable","tokenType":"NFT","tokenName":"rawMaterial","tokenId":"1","operation":"mint","caller":"Participant_0wg64sj"}`, initParameters.ERCChaincodeNames["Activity_0i3c0p3"], initParameters.BpmnId)
	cc.CreateTokenElement(ctx, &instance, "Activity_11qv4ci", DISABLED, `{"assetType":"transferable","tokenType":"NFT","tokenName":"rawMaterial","tokenId":"1","operation":"Transfer","caller":"Participant_0wg64sj","callee":["Participant_18g06ah"]}`, initParameters.ERCChaincodeNames["Activity_11qv4ci"], initParameters.BpmnId)
	cc.CreateTokenElement(ctx, &instance, "Activity_12g7edm", DISABLED, `{"assetType":"transferable","tokenType":"NFT","tokenName":"rawMaterial","tokenId":"1","operation":"query","caller":"Participant_18g06ah","outputs":{"uriTest":{"type":"URI","dataType":"string"},"ownerTest":{"type":"owner","dataType":"string"}}}`, initParameters.ERCChaincodeNames["Activity_12g7edm"], initParameters.BpmnId)

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

func (cc *SmartContract) Event_1so6gi5(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)

	actionEvent, err := cc.ReadEvent(ctx, instanceID, "Event_1so6gi5")
	if err != nil {
		return err
	}

	if actionEvent.EventState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", actionEvent.EventID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeEventState(ctx, instance, "Event_1so6gi5", COMPLETED)
	stub.SetEvent("Event_1so6gi5", []byte("Contract has been started successfully"))
	cc.SetInstance(ctx, instance)

	cc.ChangeMsgState(ctx, instance, "Message_1f0g7ng", ENABLED)

	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_1f0g7ng_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1f0g7ng")
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
	cc.ChangeMsgState(ctx, instance, "Message_1f0g7ng", COMPLETED)

	stub.SetEvent("Message_1f0g7ng", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	cc.ChangeMsgState(ctx, instance, "Message_15pq051", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_15pq051_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_15pq051")
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
	cc.ChangeMsgState(ctx, instance, "Message_15pq051", COMPLETED)

	stub.SetEvent("Message_15pq051", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	cc.ChangeGtwState(ctx, instance, "Gateway_1yei1dm", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_0wvtw7k_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_0wvtw7k")
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
	cc.ChangeMsgState(ctx, instance, "Message_0wvtw7k", COMPLETED)

	stub.SetEvent("Message_0wvtw7k", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	cc.changeTokenElementState(ctx, instance, "Activity_0i3c0p3", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Gateway_1yei1dm(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	gtw, err := cc.ReadGtw(ctx, instanceID, "Gateway_1yei1dm")
	if err != nil {
		return err
	}

	if gtw.GatewayState != ENABLED {
		errorMessage := fmt.Sprintf("Gateway state %s is not allowed", gtw.GatewayID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeGtwState(ctx, instance, gtw.GatewayID, COMPLETED)
	stub.SetEvent("Gateway_1yei1dm", []byte("Gateway has been done"))
	cc.SetInstance(ctx, instance)

	cc.ChangeMsgState(ctx, instance, "Message_0wvtw7k", ENABLED)
	cc.ChangeMsgState(ctx, instance, "Message_0dy0w96", ENABLED)
	cc.SetInstance(ctx, instance)

	return nil
}

func (cc *SmartContract) Message_0dy0w96_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_0dy0w96")
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
	cc.ChangeMsgState(ctx, instance, "Message_0dy0w96", COMPLETED)

	stub.SetEvent("Message_0dy0w96", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	if !(func() bool {
		msg, err := cc.ReadTokenElement(ctx, instanceID, "Activity_0i3c0p3")
		return err == nil && msg.State == COMPLETED
	}()) {
		return nil
	}
	cc.ChangeGtwState(ctx, instance, "Gateway_0n7lupx", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Activity_0i3c0p3(ctx contractapi.TransactionContextInterface, instanceID string) error {
	fmt.Println("----- Activity_0i3c0p3 (Start) -----")

	instance, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	if instance == nil {
		return errors.New("instanceID does not exist")
	}

	// 1. 读 TokenElement + Token（只是校验，不在这里 mint）
	tokenElement, err := cc.ReadTokenElement(ctx, instanceID, "Activity_0i3c0p3")
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

	// 3. 校验调用者身份
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
		"ActivityID": "Activity_0i3c0p3",
		"Func":       "Activity_0i3c0p3_Continue",
	}
	eventPayloadAsBytes, err := json.Marshal(eventPayload)
	if err != nil {
		return fmt.Errorf("failed to marshal event payload: %v", err)
	}

	if err := ctx.GetStub().SetEvent("AssetUploadRequired", eventPayloadAsBytes); err != nil {
		return fmt.Errorf("failed to set AssetUploadRequired event: %v", err)
	}

	// 5. 标记 TokenElement 状态为 WAITINGFORCONFIRMATION
	if err := cc.changeTokenElementState(ctx, instance, "Activity_0i3c0p3", WAITINGFORCONFIRMATION); err != nil {
		return err
	}
	if err := cc.SetInstance(ctx, instance); err != nil {
		return err
	}

	return nil
}

func (cc *SmartContract) Activity_0i3c0p3_Continue(ctx contractapi.TransactionContextInterface, instanceID string) error {
	fmt.Println("----- Activity_0i3c0p3_Continue -----")

	instance, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	if instance == nil {
		return errors.New("instanceID does not exist")
	}

	// 1. 读 TokenElement
	tokenElement, err := cc.ReadTokenElement(ctx, instanceID, "Activity_0i3c0p3")
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
	cid, err := cc.GetURLData(ctx, instanceID, "Activity_0i3c0p3")
	// 4. 在当前 instance 里真正更新 TokenURL
	tokenURI := "ipfs://" + cid
	if err := cc.changeTokenURL(ctx, instance, tokenElement.TokenKey, tokenURI); err != nil {
		return err
	}
	// 从 instance 里拿出最新的 token，用来调用 ERC 链码
	token, ok := instance.InstanceTokens[tokenElement.TokenKey]
	if !ok {
		return fmt.Errorf("Token %s does not exist", tokenElement.TokenKey)
	}
	// 5. 调 ERC 的 MintWithTokenURI
	chaincodeName := tokenElement.ChaincodeName
	_args := make([][]byte, 4)
	_args[0] = []byte("MintWithTokenURI")
	_args[1] = []byte(token.TokenID)
	_args[2] = []byte(token.TokenURL) // 已经是 ipfs://CID
	_args[3] = []byte(instanceID)

	getpayload, err := cc.Invoke_Other_chaincode(ctx, chaincodeName, "default", _args)
	if err != nil {
		return err
	}
	if len(getpayload) == 0 || string(getpayload) == "null" {
		return errors.New("did not create successfully")
	}
	// 6. 改 TokenElement 状态 + 写回实例
	if err := cc.changeTokenElementState(ctx, instance, "Activity_0i3c0p3", COMPLETED); err != nil {
		return err
	}
	if err := cc.SetInstance(ctx, instance); err != nil {
		return err
	}

	if !(func() bool {
		msg, err := cc.ReadMsg(ctx, instanceID, "Message_0dy0w96")
		return err == nil && msg.MsgState == COMPLETED
	}()) {
		return nil
	}
	cc.ChangeGtwState(ctx, instance, "Gateway_0n7lupx", ENABLED)
	if err := cc.SetInstance(ctx, instance); err != nil {
		return err
	}

	return nil
}

func (cc *SmartContract) Gateway_0n7lupx(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	gtw, err := cc.ReadGtw(ctx, instanceID, "Gateway_0n7lupx")
	if err != nil {
		return err
	}

	if gtw.GatewayState != ENABLED {
		errorMessage := fmt.Sprintf("Gateway state %s is not allowed", gtw.GatewayID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeGtwState(ctx, instance, gtw.GatewayID, COMPLETED)
	stub.SetEvent("Gateway_0n7lupx", []byte("Gateway has been done"))

	cc.ChangeMsgState(ctx, instance, "Message_09uka8c", ENABLED)

	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_09uka8c_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_09uka8c")
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
	cc.ChangeMsgState(ctx, instance, "Message_09uka8c", COMPLETED)

	stub.SetEvent("Message_09uka8c", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	cc.ChangeMsgState(ctx, instance, "Message_1v05oen", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_1v05oen_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1v05oen")
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
	cc.ChangeMsgState(ctx, instance, "Message_1v05oen", COMPLETED)

	stub.SetEvent("Message_1v05oen", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	cc.ChangeMsgState(ctx, instance, "Message_1kqcpl3", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_1kqcpl3_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1kqcpl3")
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
	cc.ChangeMsgState(ctx, instance, "Message_1kqcpl3", COMPLETED)

	stub.SetEvent("Message_1kqcpl3", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	cc.ChangeMsgState(ctx, instance, "Message_0olnqt0", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_0olnqt0_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_0olnqt0")
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
	cc.ChangeMsgState(ctx, instance, "Message_0olnqt0", COMPLETED)

	stub.SetEvent("Message_0olnqt0", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	cc.changeTokenElementState(ctx, instance, "Activity_11qv4ci", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Activity_11qv4ci(ctx contractapi.TransactionContextInterface, instanceID string) error {
	fmt.Println("---------------------------------")
	instance, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	if instance == nil {
		return errors.New("instanceID does not exist")
	}

	tokenElement, err := cc.ReadTokenElement(ctx, instanceID, "Activity_11qv4ci")
	if err != nil {
		return err
	}
	token, err := cc.ReadToken(ctx, instanceID, tokenElement.TokenKey)
	if err != nil {
		return err
	}
	if tokenElement.State != ENABLED {
		errorMessage := fmt.Sprintf("TokenElement state %s is not allowed", tokenElement.TokenElementID)
		fmt.Sprintln(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	nowid64, _ := ctx.GetClientIdentity().GetID()
	nowidBytes, _ := base64.StdEncoding.DecodeString(nowid64)
	nowrid := string(nowidBytes)
	fmt.Println("nowid:", nowrid)

	callid, _ := cc.ParticipantToidentity(ctx, instanceID, tokenElement.CallerID)
	if nowrid != callid {
		errorMessage := fmt.Sprintf("Caller %s is not allowed to call this function", nowrid)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}
	var calleeID []string
	for _, callee := range tokenElement.CalleeID {
		callee11, _ := cc.ParticipantToidentity(ctx, instanceID, callee)
		calleeID = append(calleeID, callee11)
	}

	chaincodeName := tokenElement.ChaincodeName
	_args := make([][]byte, 4)
	_args[0] = []byte("TransferFrom") // 操作类型
	_args[1] = []byte(callid)
	_args[2] = []byte(calleeID[0]) // 这里假设只有一个接收者
	_args[3] = []byte(token.TokenID)
	getpayload, err := cc.Invoke_Other_chaincode(ctx, chaincodeName, "default", _args)
	if err != nil {
		return fmt.Errorf("failed to invoke chaincode %s: %v", chaincodeName, err)
	}
	if string(getpayload) != "true" {
		return fmt.Errorf("failed to invoke chaincode %s: %v", chaincodeName, err)
	}

	cc.changeTokenElementState(ctx, instance, "Activity_11qv4ci", COMPLETED)
	cc.SetInstance(ctx, instance)

	cc.changeTokenElementState(ctx, instance, "Activity_12g7edm", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_10m6wae_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_10m6wae")
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
	cc.ChangeMsgState(ctx, instance, "Message_10m6wae", COMPLETED)

	stub.SetEvent("Message_10m6wae", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	cc.ChangeMsgState(ctx, instance, "Message_1wyvezt", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Event_1r44vsj(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	event, err := cc.ReadEvent(ctx, instanceID, "Event_1r44vsj")
	if err != nil {
		return err
	}

	if event.EventState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", event.EventID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeEventState(ctx, instance, event.EventID, COMPLETED)
	stub.SetEvent("Event_1r44vsj", []byte("EndEvent has been done"))

	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_1wyvezt_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_1wyvezt")
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
	cc.ChangeMsgState(ctx, instance, "Message_1wyvezt", COMPLETED)

	stub.SetEvent("Message_1wyvezt", []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)

	cc.ChangeEventState(ctx, instance, "Event_1r44vsj", ENABLED)
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Activity_12g7edm(ctx contractapi.TransactionContextInterface, instanceID string) error {
	fmt.Println("----- Activity_12g7edm -----")
	instance, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	if instance == nil {
		return errors.New("instanceID does not exist")
	}

	tokenElement, err := cc.ReadTokenElement(ctx, instanceID, "Activity_12g7edm")
	if err != nil {
		return err
	}

	if tokenElement.State != ENABLED {
		return fmt.Errorf(
			"TokenElement state %s is not allowed",
			tokenElement.TokenElementID,
		)
	}

	nowid64, _ := ctx.GetClientIdentity().GetID()
	nowidBytes, _ := base64.StdEncoding.DecodeString(nowid64)
	nowid := string(nowidBytes)

	callid, _ := cc.ParticipantToidentity(ctx, instanceID, tokenElement.CallerID)
	if nowid != callid {
		return fmt.Errorf("Caller %s is not allowed", nowid)
	}

	token, err := cc.ReadToken(ctx, instanceID, tokenElement.TokenKey)
	if err != nil {
		return err
	}
	tokenId := token.TokenID

	chaincodeName := tokenElement.ChaincodeName

	// 6. 遍历 outputs
	for name, spec := range tokenElement.Outputs {

		switch spec.Type {

		case "URI":
			args := make([][]byte, 2)
			args[0] = []byte("TokenURI")
			args[1] = []byte(tokenId)

			payload, err := cc.Invoke_Other_chaincode(
				ctx,
				chaincodeName,
				"default",
				args,
			)
			if err != nil {
				return fmt.Errorf("failed to invoke TokenURI: %v", err)
			}

			value := string(payload)
			switch name {
			case "uriTest":
				fmt.Println("query value:", value)
				instance.InstanceStateMemory.UriTest = value
			case "ownerTest":
				fmt.Println("query value:", value)
				instance.InstanceStateMemory.OwnerTest = value
			default:
				return fmt.Errorf("unsupported output name: %s", name)
			}

		case "owner":
			args := make([][]byte, 2)
			args[0] = []byte("OwnerOf")
			args[1] = []byte(tokenId)

			payload, err := cc.Invoke_Other_chaincode(
				ctx,
				chaincodeName,
				"default",
				args,
			)
			if err != nil {
				return fmt.Errorf("failed to invoke OwnerOf: %v", err)
			}

			value := string(payload)

			switch name {
			case "uriTest":
				fmt.Println("query value:", value)
				instance.InstanceStateMemory.UriTest = value
			case "ownerTest":
				fmt.Println("query value:", value)
				instance.InstanceStateMemory.OwnerTest = value
			default:
				return fmt.Errorf("unsupported output name: %s", name)
			}

		default:
			return fmt.Errorf("unsupported NFT query type: %s", spec.Type)
		}
	}

	cc.changeTokenElementState(ctx, instance, "Activity_12g7edm", COMPLETED)
	cc.SetInstance(ctx, instance)

	cc.ChangeMsgState(ctx, instance, "Message_10m6wae", ENABLED)
	cc.SetInstance(ctx, instance)

	return nil
}
