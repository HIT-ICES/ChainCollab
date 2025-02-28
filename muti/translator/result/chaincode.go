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

	"IBC/StateCharts/stateCharts"
)

type SmartContract struct {
	contractapi.Contract
}

type StateMemory struct {
}

type InitParameters struct {
	Participant_0ggs0ck     ParticipantForInit `json:"Participant_0ggs0ck"`
	Participant_1v6wnpq     ParticipantForInit `json:"Participant_1v6wnpq"`
	Participant_0tkhpj2     ParticipantForInit `json:"Participant_0tkhpj2"`
	StateMachineDescription string             `json:"stateMachineDescription"`
}

type ContractInstance struct {
	// Incremental ID
	InstanceID string `json:"InstanceID"`
	// global Memory
	InstanceStateMemory StateMemory `json:"stateMemory"`
	// map type from string to Message、Gateway、ActionEvent
	InstanceMessages          map[string]*CollectiveMessage     `json:"InstanceMessages"`
	InstanceBusinessRules     map[string]*BusinessRule          `json:"InstanceBusinessRule"`
	InstanceParticipants      map[string]*CollectiveParticipant `json:"InstanceParticipants"`
	InstanceChoreographyTasks map[string]*ChoreographyTask      `json:"InstanceChoreographyTasks"`
	// state of the instance
	CurrentState            string `json:"CurrentState"`
	StateMachineDescription string `json:"StateMachineDescription"`
}

type CollectiveParticipant struct {
	ParticipantID string                 `json:"PartcipantID"`
	Participants  map[string]Participant `json:"Participants"`
	IsMulti       bool                   `json:"IsMulti"`
	IsLocked      bool                   `json:"IsLocked"`
	MultiMaximum  int                    `json:"MultiMaximum"`
	MultiMinimum  int                    `json:"MultiMinimum"`
	Attributes    map[string]string      `json:"Attributes"`
}

type Participant struct {
	// ID To Sync With OuterEngine
	ParticipantID string `json:"ParticipantID"`
	MSP           string `json:"MSP"`
	IsMulti       bool   `json:"IsMulti"`
	X509          string `json:"X509"`
}

type ParticipantForInit struct {
	PartcipantID string            `json:"PartcipantID"`
	IsMulti      bool              `json:"IsMulti"`
	MultiMaximum int               `json:"MultiMaximum"`
	MultiMinimum int               `json:"MultiMinimum"`
	Attributes   map[string]string `json:"Attributes"`
	MSP          string            `json:"MSP"`
	X509         string            `json:"X509"`
}

type ChoreographyTask struct {
	ChoreographyTaskID   string `json:"ChoreographyTaskID"`
	IsMulti              bool   `json:"IsMulti"`
	MultiType            string `json:"MultiType"`
	InitMessageCount     int    `json:"InitMessageCount"`
	ResponseMessageCount int    `json:"ResponseMessageCount"`
	InitMessage          string `json:"InitMessage"`
	ResponseMessage      string `json:"ResponseMessage"`
}

type CollectiveMessage struct {
	ChoreographyTaskID    string                        `json:"ChoreographyTaskID"`
	MessageID             string                        `json:"MessageID"`
	Messages              map[string]map[string]Message `json:"Messages"`
	IsMulti               bool                          `json:"IsMulti"`
	MessageConfirmedCount int                           `json:"MessageConfirmedCount"`
	SendParticipantID     string                        `json:"SendMspID"`
	ReceiveParticipantID  string                        `json:"ReceiveMspID"`
	Format                string                        `json:"Format"`
}

type Message struct {
	MessageID             string `json:"MessageID"`
	SendParticipantKey    string `json:"SendParticipantKey"`
	ReceiveParticipantKey string `json:"ReceiveParticipantKey"`
	FireflyTranID         string `json:"FireflyTranID"`
}

type BusinessRule struct {
	BusinessRuleID string            `json:"BusinessRuleID"`
	Hash           string            `json:"Hash"`
	DecisionID     string            `json:"DecisionID"`
	ParamMapping   map[string]string `json:"ParamMapping"`
}

func (cc *SmartContract) CreateBusinessRule(ctx contractapi.TransactionContextInterface, instance *ContractInstance, BusinessRuleID string, DMNContent string, DecisionID string, ParamMapping map[string]string) (*BusinessRule, error) {

	Hash, err := cc.hashXML(ctx, DMNContent)
	if err != nil {
		fmt.Println(err.Error())
		return nil, err
	}

	instance.InstanceBusinessRules[BusinessRuleID] = &BusinessRule{
		BusinessRuleID: BusinessRuleID,
		Hash:           Hash,
		DecisionID:     DecisionID,
		ParamMapping:   ParamMapping,
	}

	returnBusinessRule, ok := instance.InstanceBusinessRules[BusinessRuleID]
	if !ok {
		return nil, fmt.Errorf("无法将实例元素转换为BusinessRule")
	}

	return returnBusinessRule, nil
}

func (cc *SmartContract) CreateParticipant(ctx contractapi.TransactionContextInterface, instance *ContractInstance, participantID string, msp string, attributes map[string]string, x509 string, IsMulti bool, MultiMaximum int, MultiMinimum int) (*CollectiveParticipant, error) {
	collectiveParticipant := &CollectiveParticipant{
		ParticipantID: participantID,
		Participants:  make(map[string]Participant), // 初始化 Participants 映射
		IsMulti:       IsMulti,
		IsLocked:      false,
		MultiMaximum:  MultiMaximum,
		MultiMinimum:  MultiMinimum,
		Attributes:    attributes,
	}

	if !IsMulti {
		participant := Participant{
			ParticipantID: participantID,
			MSP:           msp,
			IsMulti:       IsMulti,
			X509:          x509,
		}
		collectiveParticipant.Participants[participantID] = participant
	}

	instance.InstanceParticipants[participantID] = collectiveParticipant

	return collectiveParticipant, nil
}

func (cc *SmartContract) CreateChoreographyTask(
	ctx contractapi.TransactionContextInterface,
	instance *ContractInstance,
	choreographyTaskID string,
	isMulti bool,
	multiType string,
	initMessage string,
	responseMessage string,
) (*ChoreographyTask, error) {
	choreographyTask := &ChoreographyTask{
		ChoreographyTaskID:   choreographyTaskID,
		IsMulti:              isMulti,
		MultiType:            multiType,
		InitMessageCount:     0,
		ResponseMessageCount: 0,
		InitMessage:          initMessage,
		ResponseMessage:      responseMessage,
	}

	instance.InstanceChoreographyTasks[choreographyTaskID] = choreographyTask

	return choreographyTask, nil
}

// TODO： Method To Register Participant in CollectiveParticipant

func (cc *SmartContract) CreateMessage(
	ctx contractapi.TransactionContextInterface,
	instance *ContractInstance,
	messageID string,
	sendParticipantID string,
	receiveParticipantID string,
	fireflyTranID string,
	format string,
	IsMulti bool,
	choreographyTaskID string,
) (*CollectiveMessage, error) {
	collectiveMessage := &CollectiveMessage{
		ChoreographyTaskID:    choreographyTaskID,
		MessageID:             messageID,
		Messages:              make(map[string]map[string]Message), // 初始化 Messages 映射
		IsMulti:               IsMulti,
		MessageConfirmedCount: 0,
		SendParticipantID:     sendParticipantID,
		ReceiveParticipantID:  receiveParticipantID,
		Format:                format,
	}

	if !IsMulti {
		message := Message{
			MessageID:             fmt.Sprintf("%s_0", messageID),
			SendParticipantKey:    fmt.Sprintf("%s_0", sendParticipantID),
			ReceiveParticipantKey: fmt.Sprintf("%s_0", receiveParticipantID),
			FireflyTranID:         fireflyTranID,
		}
		collectiveMessage.Messages["nonMulti"]["nonMulti"] = message
	}

	instance.InstanceMessages[messageID] = collectiveMessage

	return collectiveMessage, nil
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

func (c *SmartContract) ChangeMsgFireflyTranID(ctx contractapi.TransactionContextInterface, instance *ContractInstance, fireflyTranID string, messageID string, key1 string, key2 string) error {
	collectiveMessage, ok := instance.InstanceMessages[messageID]
	if !ok {
		errorMessage := fmt.Sprintf("CollectiveMessage %s does not exist", messageID)
		fmt.Println(errorMessage)
		return errors.New(errorMessage)
	}

	message, ok := collectiveMessage.Messages[key1][key2]
	if !ok {
		errorMessage := fmt.Sprintf("Message with key1 %s key2 %s does not exist in CollectiveMessage %s", key1, key2, messageID)
		fmt.Println(errorMessage)
		return errors.New(errorMessage)
	}

	message.FireflyTranID = fireflyTranID
	collectiveMessage.Messages[key1][key2] = message

	instance.InstanceMessages[messageID] = collectiveMessage

	return nil
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

func (cc *SmartContract) ReadCollectiveParticipant(ctx contractapi.TransactionContextInterface, instanceID string, participantID string) (*CollectiveParticipant, error) {
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

	collectiveParticipant, ok := instance.InstanceParticipants[participantID]
	if !ok {
		errorMessage := fmt.Sprintf("CollectiveParticipant %s does not exist", participantID)
		fmt.Println(errorMessage)
		return nil, errors.New(errorMessage)
	}

	return collectiveParticipant, nil
}

func (cc *SmartContract) ReadAtomicParticipant(ctx contractapi.TransactionContextInterface, instanceID string, participantID string, key string) (*Participant, error) {
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

	collectiveParticipant, ok := instance.InstanceParticipants[participantID]
	if !ok {
		errorMessage := fmt.Sprintf("CollectiveParticipant %s does not exist", participantID)
		fmt.Println(errorMessage)
		return nil, errors.New(errorMessage)
	}
	atomicParticipant, ok := collectiveParticipant.Participants[key]
	if !ok {
		errorMessage := fmt.Sprintf("Participant with key %s does not exist in CollectiveParticipant %s", key, participantID)
		fmt.Println(errorMessage)
		return nil, errors.New(errorMessage)
	}

	return &atomicParticipant, nil
}

func (cc *SmartContract) get_X509_identity(ctx contractapi.TransactionContextInterface) string {
	mspID, _ := ctx.GetClientIdentity().GetMSPID()
	certificateID, _ := ctx.GetClientIdentity().GetID()
	return certificateID + "@" + mspID
}

func (cc *SmartContract) check_msp(ctx contractapi.TransactionContextInterface, instanceID string, target_participant string, key string) bool {
	targetParticipant, err := cc.ReadAtomicParticipant(ctx, instanceID, target_participant, key)
	if err != nil {
		fmt.Printf("Failed to read participant: %v\n", err)
		return false
	}

	mspID, err := ctx.GetClientIdentity().GetMSPID()
	if err != nil {
		fmt.Printf("Failed to get client MSP ID: %v\n", err)
		return false
	}

	return mspID == targetParticipant.MSP
}

func (cc *SmartContract) check_attribute(ctx contractapi.TransactionContextInterface, instanceID string, target_participant string, attributeName string) bool {
	collectiveParticipant, err := cc.ReadCollectiveParticipant(ctx, instanceID, target_participant)
	if err != nil {
		fmt.Printf("Failed to read collective participant: %v\n", err)
		return false
	}

	attributeValue, ok := collectiveParticipant.Attributes[attributeName]
	if !ok {
		fmt.Printf("Attribute %s does not exist for collective participant %s\n", attributeName, target_participant)
		return false
	}

	if ctx.GetClientIdentity().AssertAttributeValue(attributeName, attributeValue) != nil {
		fmt.Printf("Client attribute value does not match for attribute %s\n", attributeName)
		return false
	}

	return true
}

func (cc *SmartContract) check_participant(ctx contractapi.TransactionContextInterface, instanceID string, target_participant string, key string) bool {
	collectiveParticipant, err := cc.ReadCollectiveParticipant(ctx, instanceID, target_participant)
	if err != nil {
		fmt.Printf("Failed to read collective participant: %v\n", err)
		return false
	}

	if key == "" {
		// only check Participant based on Attributes in CollectiveParticipant
	}

	if !collectiveParticipant.IsMulti {
		defaultKey := fmt.Sprintf("%s_0", target_participant)
		defaultParticipant, ok := collectiveParticipant.Participants[defaultKey]
		if !ok {
			fmt.Printf("Default participant with key %s does not exist\n", defaultKey)
			return false
		}

		if defaultParticipant.X509 != "" {
			expectedX509 := cc.get_X509_identity(ctx)
			if defaultParticipant.X509 != expectedX509 {
				fmt.Printf("X509 does not match. Expected: %s, Actual: %s\n", expectedX509, defaultParticipant.X509)
				return false
			}
			return true
		}

		for attrName := range collectiveParticipant.Attributes {
			if !cc.check_attribute(ctx, instanceID, target_participant, attrName) {
				fmt.Printf("Attribute check failed for attribute %s\n", attrName)
				return false
			}
		}
		return true
	}

	participant, ok := collectiveParticipant.Participants[key]
	if !ok {
		fmt.Printf("Participant with key %s does not exist\n", key)
		return false
	}

	if participant.X509 != "" {
		mspID, err := ctx.GetClientIdentity().GetMSPID()
		if err != nil {
			fmt.Printf("Failed to get client MSP ID: %v\n", err)
			return false
		}
		pid, err := ctx.GetClientIdentity().GetID()
		if err != nil {
			fmt.Printf("Failed to get client ID: %v\n", err)
			return false
		}
		expectedX509 := pid + "@" + mspID
		if participant.X509 != expectedX509 {
			fmt.Printf("X509 does not match. Expected: %s, Actual: %s\n", expectedX509, participant.X509)
			return false
		}
		return true
	}

	for attrName := range collectiveParticipant.Attributes {
		if !cc.check_attribute(ctx, instanceID, target_participant, attrName) {
			fmt.Printf("Attribute check failed for attribute %s\n", attrName)
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

func (c *SmartContract) ReadCollectiveMsg(ctx contractapi.TransactionContextInterface, instanceID string, messageID string) (*CollectiveMessage, error) {
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

	collectiveMsg, ok := instance.InstanceMessages[messageID]
	if !ok {
		errorMessage := fmt.Sprintf("CollectiveMessage %s does not exist", messageID)
		fmt.Println(errorMessage)
		return nil, errors.New(errorMessage)
	}

	return collectiveMsg, nil
}

func (c *SmartContract) ReadAtomicMsg(ctx contractapi.TransactionContextInterface, instanceID string, messageID string, key1 string, key2 string) (*Message, error) {
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

	collectiveMsg, ok := instance.InstanceMessages[messageID]
	if !ok {
		errorMessage := fmt.Sprintf("CollectiveMessage %s does not exist", messageID)
		fmt.Println(errorMessage)
		return nil, errors.New(errorMessage)
	}

	atomicMsg, ok := collectiveMsg.Messages[key1][key2]
	if !ok {
		errorMessage := fmt.Sprintf("Message with key1 %s, key2 %s does not exist in CollectiveMessage %s", key1, key2, messageID)
		fmt.Println(errorMessage)
		return nil, errors.New(errorMessage)
	}

	return &atomicMsg, nil
}

func (c *SmartContract) ReadChoreographyTask(ctx contractapi.TransactionContextInterface, instanceID string, choreographyTaskID string) (*ChoreographyTask, error) {
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

	choreographyTask, ok := instance.InstanceChoreographyTasks[choreographyTaskID]
	if !ok {
		errorMessage := fmt.Sprintf("ChoreographyTask %s does not exist", choreographyTaskID)
		fmt.Println(errorMessage)
		return nil, errors.New(errorMessage)
	}

	return choreographyTask, nil
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
		InstanceID:              instanceID,
		InstanceStateMemory:     StateMemory{},
		InstanceMessages:        make(map[string]*CollectiveMessage),
		InstanceParticipants:    make(map[string]*CollectiveParticipant),
		InstanceBusinessRules:   make(map[string]*BusinessRule),
		CurrentState:            "",
		StateMachineDescription: initParameters.StateMachineDescription,
	}

	// Update the currentInstanceID

	cc.CreateParticipant(ctx, &instance, "Participant_0ggs0ck", initParameters.Participant_0ggs0ck.MSP, initParameters.Participant_0ggs0ck.Attributes, initParameters.Participant_0ggs0ck.X509, initParameters.Participant_0ggs0ck.IsMulti, 2, 1)
	cc.CreateParticipant(ctx, &instance, "Participant_1v6wnpq", initParameters.Participant_1v6wnpq.MSP, initParameters.Participant_1v6wnpq.Attributes, initParameters.Participant_1v6wnpq.X509, initParameters.Participant_1v6wnpq.IsMulti, 0, 0)
	cc.CreateParticipant(ctx, &instance, "Participant_0tkhpj2", initParameters.Participant_0tkhpj2.MSP, initParameters.Participant_0tkhpj2.Attributes, initParameters.Participant_0tkhpj2.X509, initParameters.Participant_0tkhpj2.IsMulti, 0, 0)
	cc.CreateMessage(ctx, &instance, "Message_0gswvmq", "Participant_0ggs0ck", "Participant_1v6wnpq", "", `{"properties":{"sample":{"type":"string","description":""}},"required":["sample"],"files":{},"file required":[]}`, true, "ChoreographyTask_10lckh7")
	cc.CreateMessage(ctx, &instance, "Message_0wq8mc6", "Participant_0ggs0ck", "Participant_0tkhpj2", "", `{"properties":{"patientData":{"type":"string","description":""}},"required":["patientData"],"files":{},"file required":[]}`, true, "ChoreographyTask_131v44n")
	cc.CreateMessage(ctx, &instance, "Message_1vzqd37", "Participant_1v6wnpq", "Participant_0ggs0ck", "", `{"properties":{"result":{"type":"string","description":""}},"required":["result"],"files":{},"file required":[]}`, true, "ChoreographyTask_1732eky")
	cc.CreateMessage(ctx, &instance, "Message_1vzqd37_1", "Participant_1v6wnpq", "Participant_0ggs0ck", "", `{"properties":{"result":{"type":"string","description":""}},"required":["result"],"files":{},"file required":[]}`, true, "ChoreographyTask_1732eky")
	cc.CreateMessage(ctx, &instance, "Message_1vzqd37_2", "Participant_1v6wnpq", "Participant_0ggs0ck", "", `{"properties":{"result":{"type":"string","description":""}},"required":["result"],"files":{},"file required":[]}`, true, "ChoreographyTask_1732eky")
	cc.CreateMessage(ctx, &instance, "Message_1rqbibd", "Participant_0ggs0ck", "Participant_0tkhpj2", "", `{"properties":{"result":{"type":"string","description":""}},"required":["result"],"files":{},"file required":[]}`, true, "ChoreographyTask_1bkb191")
	cc.CreateMessage(ctx, &instance, "Message_1rqbibd_1", "Participant_0ggs0ck", "Participant_0tkhpj2", "", `{"properties":{"result":{"type":"string","description":""}},"required":["result"],"files":{},"file required":[]}`, true, "ChoreographyTask_1bkb191")
	cc.CreateMessage(ctx, &instance, "Message_0gd0z61", "Participant_0tkhpj2", "Participant_0ggs0ck", "", `{"properties":{"furtherCheckPlace":{"type":"string","description":""},"furtherCheckDate":{"type":"string","description":""}},"required":["furtherCheckPlace","furtherCheckDate"],"files":{},"file required":[]}`, true, "ChoreographyTask_1qmxi43")
	cc.CreateMessage(ctx, &instance, "Message_13mh6mk", "Participant_0tkhpj2", "Participant_0ggs0ck", "", `{"properties":{"reportContent":{"type":"string","description":""}},"required":["reportContent"],"files":{},"file required":[]}`, true, "ChoreographyTask_0rxioe7")
	cc.CreateChoreographyTask(ctx, &instance, "ChoreographyTask_10lckh7", false, "TaskLoopType.NONE", "Message_0gswvmq", "")
	cc.CreateChoreographyTask(ctx, &instance, "ChoreographyTask_131v44n", false, "TaskLoopType.NONE", "Message_0wq8mc6", "")
	cc.CreateChoreographyTask(ctx, &instance, "ChoreographyTask_1732eky", true, "TaskLoopType.MULTI_INSTANCE_PARALLEL", "Message_1vzqd37", "")
	cc.CreateChoreographyTask(ctx, &instance, "ChoreographyTask_1bkb191", true, "TaskLoopType.MULTI_INSTANCE_SEQUENTIAL", "Message_1rqbibd", "")
	cc.CreateChoreographyTask(ctx, &instance, "ChoreographyTask_1qmxi43", true, "TaskLoopType.STANDARD", "Message_0gd0z61", "")
	cc.CreateChoreographyTask(ctx, &instance, "ChoreographyTask_0rxioe7", false, "TaskLoopType.NONE", "Message_13mh6mk", "")

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

func (cc *SmartContract) StartEvent_0m7hz56(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)

	res, err := cc.Invoke_Other_chaincode(ctx, "stateCharts", "default",
		stateCharts.EncodeTriggerActionArgs(instance.StateMachineDescription, instance.CurrentState, "StartEvent_0m7hz56"))

	if err != nil {
		return err
	}

	state, changed := stateCharts.DecodeTriggerActionResult(res)
	if !changed {
		return errors.New("Invalid transition")
	}

	instance.CurrentState = state

	cc.SetInstance(ctx, instance)

	stub.SetEvent("StartEvent_0m7hz56", []byte("Contract has been started successfully"))

	return nil
}

func (cc *SmartContract) ParallelGateway_1pgjqtw(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)

	if err != nil {
		return err
	}

	res, err := cc.Invoke_Other_chaincode(ctx, "stateCharts:v1", "default",
		stateCharts.EncodeTriggerActionArgs(instance.StateMachineDescription, instance.CurrentState, "ParallelGateway_1pgjqtw"))

	if err != nil {
		return err
	}
	new_status, changed := stateCharts.DecodeTriggerActionResult(res)

	if !changed {
		return errors.New("Invalid transition")
	}

	instance.CurrentState = new_status
	cc.SetInstance(ctx, instance)

	stub.SetEvent("ParallelGateway_1pgjqtw", []byte("Gateway has been done"))

	return nil
}

func (cc *SmartContract) Message_0gswvmq_Send(ctx contractapi.TransactionContextInterface, instanceID string, targetTaskID int, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, _ := cc.GetInstance(ctx, instanceID)

	collectiveMsgName := "Message_0gswvmq"
	collectiveMsg, _ := cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)
	participant_id := collectiveMsg.SendParticipantID

	// MultiTask Address Located
	choreographyTaskID := collectiveMsg.ChoreographyTaskID

	choreographyTask, _ := cc.ReadChoreographyTask(ctx, instanceID, choreographyTaskID)
	if choreographyTask.IsMulti == true {
		collectiveMsgName = fmt.Sprintf("Message_0gswvmq_%d", targetTaskID)
	}

	// MultiParticipant Address Located

	collectiveMsg, _ = cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)
	sendParticipantID := collectiveMsg.SendParticipantID
	receiveParticipantID := collectiveMsg.ReceiveParticipantID
	sendParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, sendParticipantID)
	receiveParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, receiveParticipantID)

	var errorMessage string
	var key1, key2 string
	var msgsToHandle []Message = make([]Message, 0)
	var eventsToTrigger []string = make([]string, 0)
	if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == false {
		// 一对一
		key1 = "nonMulti"
		key2 = "nonMulti"

		msgsToHandle = append(msgsToHandle, collectiveMsg.Messages[key1][key2])
		eventsToTrigger = append(eventsToTrigger, "Send_Message_0gswvmq")

		participant_key := key1
		if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
			errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
			fmt.Println(errorMessage)
			return fmt.Errorf(errorMessage)
		}

	} else if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == false {
		// 多对一
		key1 = cc.get_X509_identity(ctx)
		key2 = "nonMulti"

		// // Auth

		// Check if Locked
		if sendParticipant.IsLocked == true {
			// check if registered
			if _, ok := sendParticipant.Participants[key1]; ok {
				// check X509
				participant_key := key1
				if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
					errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
					fmt.Println(errorMessage)
					return fmt.Errorf(errorMessage)
				}
			} else {
				return fmt.Errorf("The participant is locked and the participant is not registered")
			}
		} else {
			// else check if Participant has reach Maximum
			if sendParticipant.MultiMaximum <= len(sendParticipant.Participants) {
				return fmt.Errorf("The number of messages sent by the participant exceeds the maximum")
			}

			// Attributes Based Access Control
			if cc.check_participant(ctx, instanceID, participant_id, "") == false {
				errorMessage = fmt.Sprintf("Participant can't not register itself due to no conformance attributes")
				return fmt.Errorf(errorMessage)
			}

			// Register self, using a increasing key
			participant_increasing_key := fmt.Sprintf("%d", len(sendParticipant.Participants))
			// create new Participant if not exist
			msp, _ := ctx.GetClientIdentity().GetMSPID()
			newParticipant := Participant{
				ParticipantID: participant_increasing_key,
				MSP:           msp,
				IsMulti:       true,
				X509:          key1,
			}
			sendParticipant.Participants[key1] = newParticipant
		}

		// Created Message

		if _, ok := collectiveMsg.Messages[key1]; ok {

		} else {
			collectiveMsg.Messages[key1] = make(map[string]Message)
			newAtomicMsg := Message{
				MessageID:             collectiveMsgName,
				SendParticipantKey:    key1,
				ReceiveParticipantKey: key2,
				FireflyTranID:         "",
			}
			collectiveMsg.Messages[key1][key2] = newAtomicMsg
		}

		message_increasing_key := len(sendParticipant.Participants)
		msgsToHandle = append(msgsToHandle, collectiveMsg.Messages[key1][key2])
		eventsToTrigger = append(eventsToTrigger, fmt.Sprintf("Send_Message_0gswvmq_%d", message_increasing_key))

	} else if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == true {
		// 一对多
		key1 = "nonMulti"

		participant_key := key1
		if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
			errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
			fmt.Println(errorMessage)
			return fmt.Errorf(errorMessage)
		}

		// create Maximum Number of Message
		if _, ok := collectiveMsg.Messages[key1]; ok {
			// Have Been Created, Repeated Operation
		} else {
			collectiveMsg.Messages[key1] = make(map[string]Message)
		}

		if len(collectiveMsg.Messages[key1]) >= sendParticipant.MultiMaximum {
			fmt.Println("The number of messages sent by the participant exceeds the maximum")
			return fmt.Errorf("The number of messages sent by the participant exceeds the maximum")
		}

		for i := 0; i < sendParticipant.MultiMaximum; i++ {
			key2 := fmt.Sprintf("%d", i)
			newAtomicMsg := Message{
				MessageID:             collectiveMsgName,
				SendParticipantKey:    key1,
				ReceiveParticipantKey: key2,
				FireflyTranID:         "",
			}
			collectiveMsg.Messages[key1][key2] = newAtomicMsg
		}

		for key, value := range collectiveMsg.Messages[key1] {
			msgsToHandle = append(msgsToHandle, value)
			eventsToTrigger = append(eventsToTrigger, fmt.Sprintf("Send_Message_0gswvmq_%s", key))
		}

	} else if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == true {
		// 多对多 UnSupport Type
		errorMessage = "Multi To Multi Task, Unsupported Operation"
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	for _, event := range eventsToTrigger {
		res, _ := cc.Invoke_Other_chaincode(ctx, "stateCharts:v1", "default",
			stateCharts.EncodeTriggerActionArgs(instance.StateMachineDescription, instance.CurrentState, event))
		state, changed := stateCharts.DecodeTriggerActionResult(res)
		if !changed {
			return fmt.Errorf("The state machine does not change")
		}
		instance.CurrentState = state
	}

	for _, msg := range msgsToHandle {
		cc.ChangeMsgFireflyTranID(ctx, instance, fireflyTranID, msg.MessageID, key1, key2)
	}

	stub.SetEvent(collectiveMsgName, []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_0gswvmq_Complete(ctx contractapi.TransactionContextInterface, targetTaskID int, ConfirmTargetX509 string, instanceID string) error {
	stub := ctx.GetStub()
	instance, _ := cc.GetInstance(ctx, instanceID)

	collectiveMsgName := "Message_0gswvmq"
	collectiveMsg, _ := cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)
	participant_id := collectiveMsg.ReceiveParticipantID

	// MultiTask Address Located
	choreographyTaskID := collectiveMsg.ChoreographyTaskID

	choreographyTask, _ := cc.ReadChoreographyTask(ctx, instanceID, choreographyTaskID)
	if choreographyTask.IsMulti == true {
		collectiveMsgName = fmt.Sprintf("Message_0gswvmq_%d", targetTaskID)
	}

	collectiveMsg, _ = cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)
	sendParticipantID := collectiveMsg.SendParticipantID
	receiveParticipantID := collectiveMsg.ReceiveParticipantID
	sendParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, sendParticipantID)
	receiveParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, receiveParticipantID)

	var errorMessage string
	var key1, key2 string
	var msgsToHandle []Message = make([]Message, 0)
	var eventsToTrigger []string = make([]string, 0)
	if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == false {
		// 一对一
		key1 = "nonMulti"
		key2 = "nonMulti"
		msgsToHandle = append(msgsToHandle, collectiveMsg.Messages[key1][key2])
		eventsToTrigger = append(eventsToTrigger, "Confirm_Message_0gswvmq")

		participant_key := key2
		if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
			errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
			fmt.Println(errorMessage)
			return fmt.Errorf(errorMessage)
		}

	} else if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == false {
		// 多对一 回应
		// 1. 响应所有消息
		// 2. 添加Target

		key1 = ConfirmTargetX509
		key2 = "nonMulti"

		participant_key := key2
		if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
			errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
			fmt.Println(errorMessage)
			return fmt.Errorf(errorMessage)
		}

		// Which To Confirm? Decided By ConfirmTargetX509
		confirmTargetSender, ok := sendParticipant.Participants[key1]
		if !ok {
			errorMessage := "UnExisted ConfirmTarget"
			return fmt.Errorf(errorMessage)
		}

		msgsToHandle = append(msgsToHandle, collectiveMsg.Messages[key1]["nonMulti"])
		eventsToTrigger = append(eventsToTrigger, fmt.Sprintf("Confirm_Message_0gswvmq_%s", confirmTargetSender.ParticipantID))
	} else if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == true {
		// 一对多 回应，响应自己的部分，修改计数器
		key1 = "nonMulti"
		key2 = cc.get_X509_identity(ctx)

		if receiveParticipant.IsLocked == true {
			// check if key2 in it
			if _, ok := receiveParticipant.Participants[key2]; ok {
				// check Participant
				participant_key := key2
				if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
					errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
					fmt.Println(errorMessage)
					return fmt.Errorf(errorMessage)
				}
			} else {
				return fmt.Errorf("The participant is locked and the participant is not registered")
			}
		} else {

			if receiveParticipant.MultiMaximum <= len(receiveParticipant.Participants) {
				errorMessage := "ReceiveParticipants Has Reach the Maximum"
				return fmt.Errorf(errorMessage)
			}

			if cc.check_participant(ctx, instanceID, participant_id, "") != true {
				errorMessage := "Not Allowed To participate as a Receiver"
				return fmt.Errorf(errorMessage)
			}

			// create new Participant if not exist
			x509 := cc.get_X509_identity(ctx)
			participant_increasing_key := len(receiveParticipant.Participants)
			msp, _ := ctx.GetClientIdentity().GetMSPID()
			newParticipant := Participant{
				ParticipantID: fmt.Sprintf("%d", participant_increasing_key),
				MSP:           msp,
				IsMulti:       true,
				X509:          x509,
			}
			receiveParticipant.Participants[key2] = newParticipant
		}

		// get the message and increase it's confirmedCount

		if collectiveMsg.MessageConfirmedCount >= receiveParticipant.MultiMaximum {
			return fmt.Errorf("The number of messages sent by the participant exceeds the maximum")
		}

		message_increasing_key := fmt.Sprintf("%d", collectiveMsg.MessageConfirmedCount)
		msg := collectiveMsg.Messages[key1][message_increasing_key]
		delete(collectiveMsg.Messages[key1], message_increasing_key)
		collectiveMsg.Messages[key1][key2] = msg
		collectiveMsg.MessageConfirmedCount += 1

		msgsToHandle = append(msgsToHandle, msg)
		eventsToTrigger = append(eventsToTrigger, fmt.Sprintf("Send_Message_0gswvmq_%d", message_increasing_key))

	} else if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == true {
		// 多对多 UnSupported Operations?
		errorMessage = fmt.Sprintf("UnSupported Operation")
		return fmt.Errorf(errorMessage)
	}

	for _, event := range eventsToTrigger {
		res, err := cc.Invoke_Other_chaincode(ctx, "stateCharts:v1", "default",
			stateCharts.EncodeTriggerActionArgs(instance.StateMachineDescription, instance.CurrentState, event))
		if err != nil {
			return err
		}
		state, changed := stateCharts.DecodeTriggerActionResult(res)

		if !changed {
			return fmt.Errorf("The state machine does not change")
		}

		instance.CurrentState = state
	}

	stub.SetEvent(collectiveMsgName, []byte("Message is Confirmed !"))
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_0gswvmq_Advance(
	ctx contractapi.TransactionContextInterface,
	instanceID string,
	targetTaskID string,
) error {
	stub := ctx.GetStub()
	instance, _ := cc.GetInstance(ctx, instanceID)

	collectiveMsgName := "Message_0gswvmq"
	collectiveMsg, _ := cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)

	// MultiTask Address Located
	choreographyTaskID := collectiveMsg.ChoreographyTaskID

	choreographyTask, _ := cc.ReadChoreographyTask(ctx, instanceID, choreographyTaskID)
	if choreographyTask.IsMulti == true {
		collectiveMsgName = fmt.Sprintf("Message_0gswvmq_%d", targetTaskID)
	}

	collectiveMsg, _ = cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)

	sendParticipantID := collectiveMsg.SendParticipantID
	receiveParticipantID := collectiveMsg.ReceiveParticipantID
	sendParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, sendParticipantID)
	receiveParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, receiveParticipantID)

	// Check if Multi
	if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == true {
		return fmt.Errorf("Unsupport Operation")
	}

	if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == false {
		return fmt.Errorf("Not Invalid Operation")
	}

	var participantToLock *CollectiveParticipant
	if sendParticipant.IsMulti {
		// check if invoker in receiveParticipants
		if cc.check_participant(ctx, instanceID, receiveParticipantID, "") == false {
			return fmt.Errorf("Not Allowed To Advance")
		}
		participantToLock = receiveParticipant
	} else {
		// check if invoker in senderParticipants
		if cc.check_participant(ctx, instanceID, sendParticipantID, "") == false {
			return fmt.Errorf("Not Allowd To Advance")
		}
		participantToLock = sendParticipant
	}

	if len(participantToLock.Participants) < participantToLock.MultiMinimum {
		errorMessage := fmt.Sprintf(
			"Messages count %d does not meet the minimum requirement %d for participant %s",
			len(collectiveMsg.Messages),
			participantToLock.MultiMinimum,
			participantToLock.ParticipantID,
		)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	res, err := cc.Invoke_Other_chaincode(ctx, "stateCharts:v1", "default",
		stateCharts.EncodeTriggerActionArgs(instance.StateMachineDescription, instance.CurrentState, "AdvanceMessage_0gswvmq"))
	if err != nil {
		return fmt.Errorf("failed to trigger stateCharts action: %v", err)
	}
	state, changed := stateCharts.DecodeTriggerActionResult(res)

	if !changed {
		return fmt.Errorf("Invalid Operation")
	}
	instance.CurrentState = state

	participantToLock.IsLocked = true

	err = cc.SetInstance(ctx, instance)
	if err != nil {
		return fmt.Errorf("failed to set instance: %v", err)
	}

	stub.SetEvent("AdvanceMessage_0gswvmq", []byte("CollectiveMessage advanced successfully"))
	return nil
}

func (cc *SmartContract) Message_0wq8mc6_Send(ctx contractapi.TransactionContextInterface, instanceID string, targetTaskID int, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, _ := cc.GetInstance(ctx, instanceID)

	collectiveMsgName := "Message_0wq8mc6"
	collectiveMsg, _ := cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)
	participant_id := collectiveMsg.SendParticipantID

	// MultiTask Address Located
	choreographyTaskID := collectiveMsg.ChoreographyTaskID

	choreographyTask, _ := cc.ReadChoreographyTask(ctx, instanceID, choreographyTaskID)
	if choreographyTask.IsMulti == true {
		collectiveMsgName = fmt.Sprintf("Message_0wq8mc6_%d", targetTaskID)
	}

	// MultiParticipant Address Located

	collectiveMsg, _ = cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)
	sendParticipantID := collectiveMsg.SendParticipantID
	receiveParticipantID := collectiveMsg.ReceiveParticipantID
	sendParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, sendParticipantID)
	receiveParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, receiveParticipantID)

	var errorMessage string
	var key1, key2 string
	var msgsToHandle []Message = make([]Message, 0)
	var eventsToTrigger []string = make([]string, 0)
	if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == false {
		// 一对一
		key1 = "nonMulti"
		key2 = "nonMulti"

		msgsToHandle = append(msgsToHandle, collectiveMsg.Messages[key1][key2])
		eventsToTrigger = append(eventsToTrigger, "Send_Message_0wq8mc6")

		participant_key := key1
		if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
			errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
			fmt.Println(errorMessage)
			return fmt.Errorf(errorMessage)
		}

	} else if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == false {
		// 多对一
		key1 = cc.get_X509_identity(ctx)
		key2 = "nonMulti"

		// // Auth

		// Check if Locked
		if sendParticipant.IsLocked == true {
			// check if registered
			if _, ok := sendParticipant.Participants[key1]; ok {
				// check X509
				participant_key := key1
				if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
					errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
					fmt.Println(errorMessage)
					return fmt.Errorf(errorMessage)
				}
			} else {
				return fmt.Errorf("The participant is locked and the participant is not registered")
			}
		} else {
			// else check if Participant has reach Maximum
			if sendParticipant.MultiMaximum <= len(sendParticipant.Participants) {
				return fmt.Errorf("The number of messages sent by the participant exceeds the maximum")
			}

			// Attributes Based Access Control
			if cc.check_participant(ctx, instanceID, participant_id, "") == false {
				errorMessage = fmt.Sprintf("Participant can't not register itself due to no conformance attributes")
				return fmt.Errorf(errorMessage)
			}

			// Register self, using a increasing key
			participant_increasing_key := fmt.Sprintf("%d", len(sendParticipant.Participants))
			// create new Participant if not exist
			msp, _ := ctx.GetClientIdentity().GetMSPID()
			newParticipant := Participant{
				ParticipantID: participant_increasing_key,
				MSP:           msp,
				IsMulti:       true,
				X509:          key1,
			}
			sendParticipant.Participants[key1] = newParticipant
		}

		// Created Message

		if _, ok := collectiveMsg.Messages[key1]; ok {

		} else {
			collectiveMsg.Messages[key1] = make(map[string]Message)
			newAtomicMsg := Message{
				MessageID:             collectiveMsgName,
				SendParticipantKey:    key1,
				ReceiveParticipantKey: key2,
				FireflyTranID:         "",
			}
			collectiveMsg.Messages[key1][key2] = newAtomicMsg
		}

		message_increasing_key := len(sendParticipant.Participants)
		msgsToHandle = append(msgsToHandle, collectiveMsg.Messages[key1][key2])
		eventsToTrigger = append(eventsToTrigger, fmt.Sprintf("Send_Message_0wq8mc6_%d", message_increasing_key))

	} else if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == true {
		// 一对多
		key1 = "nonMulti"

		participant_key := key1
		if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
			errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
			fmt.Println(errorMessage)
			return fmt.Errorf(errorMessage)
		}

		// create Maximum Number of Message
		if _, ok := collectiveMsg.Messages[key1]; ok {
			// Have Been Created, Repeated Operation
		} else {
			collectiveMsg.Messages[key1] = make(map[string]Message)
		}

		if len(collectiveMsg.Messages[key1]) >= sendParticipant.MultiMaximum {
			fmt.Println("The number of messages sent by the participant exceeds the maximum")
			return fmt.Errorf("The number of messages sent by the participant exceeds the maximum")
		}

		for i := 0; i < sendParticipant.MultiMaximum; i++ {
			key2 := fmt.Sprintf("%d", i)
			newAtomicMsg := Message{
				MessageID:             collectiveMsgName,
				SendParticipantKey:    key1,
				ReceiveParticipantKey: key2,
				FireflyTranID:         "",
			}
			collectiveMsg.Messages[key1][key2] = newAtomicMsg
		}

		for key, value := range collectiveMsg.Messages[key1] {
			msgsToHandle = append(msgsToHandle, value)
			eventsToTrigger = append(eventsToTrigger, fmt.Sprintf("Send_Message_0wq8mc6_%s", key))
		}

	} else if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == true {
		// 多对多 UnSupport Type
		errorMessage = "Multi To Multi Task, Unsupported Operation"
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	for _, event := range eventsToTrigger {
		res, _ := cc.Invoke_Other_chaincode(ctx, "stateCharts:v1", "default",
			stateCharts.EncodeTriggerActionArgs(instance.StateMachineDescription, instance.CurrentState, event))
		state, changed := stateCharts.DecodeTriggerActionResult(res)
		if !changed {
			return fmt.Errorf("The state machine does not change")
		}
		instance.CurrentState = state
	}

	for _, msg := range msgsToHandle {
		cc.ChangeMsgFireflyTranID(ctx, instance, fireflyTranID, msg.MessageID, key1, key2)
	}

	stub.SetEvent(collectiveMsgName, []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_0wq8mc6_Complete(ctx contractapi.TransactionContextInterface, targetTaskID int, ConfirmTargetX509 string, instanceID string) error {
	stub := ctx.GetStub()
	instance, _ := cc.GetInstance(ctx, instanceID)

	collectiveMsgName := "Message_0wq8mc6"
	collectiveMsg, _ := cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)
	participant_id := collectiveMsg.ReceiveParticipantID

	// MultiTask Address Located
	choreographyTaskID := collectiveMsg.ChoreographyTaskID

	choreographyTask, _ := cc.ReadChoreographyTask(ctx, instanceID, choreographyTaskID)
	if choreographyTask.IsMulti == true {
		collectiveMsgName = fmt.Sprintf("Message_0wq8mc6_%d", targetTaskID)
	}

	collectiveMsg, _ = cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)
	sendParticipantID := collectiveMsg.SendParticipantID
	receiveParticipantID := collectiveMsg.ReceiveParticipantID
	sendParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, sendParticipantID)
	receiveParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, receiveParticipantID)

	var errorMessage string
	var key1, key2 string
	var msgsToHandle []Message = make([]Message, 0)
	var eventsToTrigger []string = make([]string, 0)
	if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == false {
		// 一对一
		key1 = "nonMulti"
		key2 = "nonMulti"
		msgsToHandle = append(msgsToHandle, collectiveMsg.Messages[key1][key2])
		eventsToTrigger = append(eventsToTrigger, "Confirm_Message_0wq8mc6")

		participant_key := key2
		if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
			errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
			fmt.Println(errorMessage)
			return fmt.Errorf(errorMessage)
		}

	} else if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == false {
		// 多对一 回应
		// 1. 响应所有消息
		// 2. 添加Target

		key1 = ConfirmTargetX509
		key2 = "nonMulti"

		participant_key := key2
		if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
			errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
			fmt.Println(errorMessage)
			return fmt.Errorf(errorMessage)
		}

		// Which To Confirm? Decided By ConfirmTargetX509
		confirmTargetSender, ok := sendParticipant.Participants[key1]
		if !ok {
			errorMessage := "UnExisted ConfirmTarget"
			return fmt.Errorf(errorMessage)
		}

		msgsToHandle = append(msgsToHandle, collectiveMsg.Messages[key1]["nonMulti"])
		eventsToTrigger = append(eventsToTrigger, fmt.Sprintf("Confirm_Message_0wq8mc6_%s", confirmTargetSender.ParticipantID))
	} else if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == true {
		// 一对多 回应，响应自己的部分，修改计数器
		key1 = "nonMulti"
		key2 = cc.get_X509_identity(ctx)

		if receiveParticipant.IsLocked == true {
			// check if key2 in it
			if _, ok := receiveParticipant.Participants[key2]; ok {
				// check Participant
				participant_key := key2
				if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
					errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
					fmt.Println(errorMessage)
					return fmt.Errorf(errorMessage)
				}
			} else {
				return fmt.Errorf("The participant is locked and the participant is not registered")
			}
		} else {

			if receiveParticipant.MultiMaximum <= len(receiveParticipant.Participants) {
				errorMessage := "ReceiveParticipants Has Reach the Maximum"
				return fmt.Errorf(errorMessage)
			}

			if cc.check_participant(ctx, instanceID, participant_id, "") != true {
				errorMessage := "Not Allowed To participate as a Receiver"
				return fmt.Errorf(errorMessage)
			}

			// create new Participant if not exist
			x509 := cc.get_X509_identity(ctx)
			participant_increasing_key := len(receiveParticipant.Participants)
			msp, _ := ctx.GetClientIdentity().GetMSPID()
			newParticipant := Participant{
				ParticipantID: fmt.Sprintf("%d", participant_increasing_key),
				MSP:           msp,
				IsMulti:       true,
				X509:          x509,
			}
			receiveParticipant.Participants[key2] = newParticipant
		}

		// get the message and increase it's confirmedCount

		if collectiveMsg.MessageConfirmedCount >= receiveParticipant.MultiMaximum {
			return fmt.Errorf("The number of messages sent by the participant exceeds the maximum")
		}

		message_increasing_key := fmt.Sprintf("%d", collectiveMsg.MessageConfirmedCount)
		msg := collectiveMsg.Messages[key1][message_increasing_key]
		delete(collectiveMsg.Messages[key1], message_increasing_key)
		collectiveMsg.Messages[key1][key2] = msg
		collectiveMsg.MessageConfirmedCount += 1

		msgsToHandle = append(msgsToHandle, msg)
		eventsToTrigger = append(eventsToTrigger, fmt.Sprintf("Send_Message_0wq8mc6_%d", message_increasing_key))

	} else if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == true {
		// 多对多 UnSupported Operations?
		errorMessage = fmt.Sprintf("UnSupported Operation")
		return fmt.Errorf(errorMessage)
	}

	for _, event := range eventsToTrigger {
		res, err := cc.Invoke_Other_chaincode(ctx, "stateCharts:v1", "default",
			stateCharts.EncodeTriggerActionArgs(instance.StateMachineDescription, instance.CurrentState, event))
		if err != nil {
			return err
		}
		state, changed := stateCharts.DecodeTriggerActionResult(res)

		if !changed {
			return fmt.Errorf("The state machine does not change")
		}

		instance.CurrentState = state
	}

	stub.SetEvent(collectiveMsgName, []byte("Message is Confirmed !"))
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_0wq8mc6_Advance(
	ctx contractapi.TransactionContextInterface,
	instanceID string,
	targetTaskID string,
) error {
	stub := ctx.GetStub()
	instance, _ := cc.GetInstance(ctx, instanceID)

	collectiveMsgName := "Message_0wq8mc6"
	collectiveMsg, _ := cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)

	// MultiTask Address Located
	choreographyTaskID := collectiveMsg.ChoreographyTaskID

	choreographyTask, _ := cc.ReadChoreographyTask(ctx, instanceID, choreographyTaskID)
	if choreographyTask.IsMulti == true {
		collectiveMsgName = fmt.Sprintf("Message_0wq8mc6_%d", targetTaskID)
	}

	collectiveMsg, _ = cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)

	sendParticipantID := collectiveMsg.SendParticipantID
	receiveParticipantID := collectiveMsg.ReceiveParticipantID
	sendParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, sendParticipantID)
	receiveParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, receiveParticipantID)

	// Check if Multi
	if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == true {
		return fmt.Errorf("Unsupport Operation")
	}

	if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == false {
		return fmt.Errorf("Not Invalid Operation")
	}

	var participantToLock *CollectiveParticipant
	if sendParticipant.IsMulti {
		// check if invoker in receiveParticipants
		if cc.check_participant(ctx, instanceID, receiveParticipantID, "") == false {
			return fmt.Errorf("Not Allowed To Advance")
		}
		participantToLock = receiveParticipant
	} else {
		// check if invoker in senderParticipants
		if cc.check_participant(ctx, instanceID, sendParticipantID, "") == false {
			return fmt.Errorf("Not Allowd To Advance")
		}
		participantToLock = sendParticipant
	}

	if len(participantToLock.Participants) < participantToLock.MultiMinimum {
		errorMessage := fmt.Sprintf(
			"Messages count %d does not meet the minimum requirement %d for participant %s",
			len(collectiveMsg.Messages),
			participantToLock.MultiMinimum,
			participantToLock.ParticipantID,
		)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	res, err := cc.Invoke_Other_chaincode(ctx, "stateCharts:v1", "default",
		stateCharts.EncodeTriggerActionArgs(instance.StateMachineDescription, instance.CurrentState, "AdvanceMessage_0wq8mc6"))
	if err != nil {
		return fmt.Errorf("failed to trigger stateCharts action: %v", err)
	}
	state, changed := stateCharts.DecodeTriggerActionResult(res)

	if !changed {
		return fmt.Errorf("Invalid Operation")
	}
	instance.CurrentState = state

	participantToLock.IsLocked = true

	err = cc.SetInstance(ctx, instance)
	if err != nil {
		return fmt.Errorf("failed to set instance: %v", err)
	}

	stub.SetEvent("AdvanceMessage_0wq8mc6", []byte("CollectiveMessage advanced successfully"))
	return nil
}

func (cc *SmartContract) Message_1vzqd37_Send(ctx contractapi.TransactionContextInterface, instanceID string, targetTaskID int, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, _ := cc.GetInstance(ctx, instanceID)

	collectiveMsgName := "Message_1vzqd37"
	collectiveMsg, _ := cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)
	participant_id := collectiveMsg.SendParticipantID

	// MultiTask Address Located
	choreographyTaskID := collectiveMsg.ChoreographyTaskID

	choreographyTask, _ := cc.ReadChoreographyTask(ctx, instanceID, choreographyTaskID)
	if choreographyTask.IsMulti == true {
		collectiveMsgName = fmt.Sprintf("Message_1vzqd37_%d", targetTaskID)
	}

	// MultiParticipant Address Located

	collectiveMsg, _ = cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)
	sendParticipantID := collectiveMsg.SendParticipantID
	receiveParticipantID := collectiveMsg.ReceiveParticipantID
	sendParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, sendParticipantID)
	receiveParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, receiveParticipantID)

	var errorMessage string
	var key1, key2 string
	var msgsToHandle []Message = make([]Message, 0)
	var eventsToTrigger []string = make([]string, 0)
	if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == false {
		// 一对一
		key1 = "nonMulti"
		key2 = "nonMulti"

		msgsToHandle = append(msgsToHandle, collectiveMsg.Messages[key1][key2])
		eventsToTrigger = append(eventsToTrigger, "Send_Message_1vzqd37")

		participant_key := key1
		if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
			errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
			fmt.Println(errorMessage)
			return fmt.Errorf(errorMessage)
		}

	} else if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == false {
		// 多对一
		key1 = cc.get_X509_identity(ctx)
		key2 = "nonMulti"

		// // Auth

		// Check if Locked
		if sendParticipant.IsLocked == true {
			// check if registered
			if _, ok := sendParticipant.Participants[key1]; ok {
				// check X509
				participant_key := key1
				if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
					errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
					fmt.Println(errorMessage)
					return fmt.Errorf(errorMessage)
				}
			} else {
				return fmt.Errorf("The participant is locked and the participant is not registered")
			}
		} else {
			// else check if Participant has reach Maximum
			if sendParticipant.MultiMaximum <= len(sendParticipant.Participants) {
				return fmt.Errorf("The number of messages sent by the participant exceeds the maximum")
			}

			// Attributes Based Access Control
			if cc.check_participant(ctx, instanceID, participant_id, "") == false {
				errorMessage = fmt.Sprintf("Participant can't not register itself due to no conformance attributes")
				return fmt.Errorf(errorMessage)
			}

			// Register self, using a increasing key
			participant_increasing_key := fmt.Sprintf("%d", len(sendParticipant.Participants))
			// create new Participant if not exist
			msp, _ := ctx.GetClientIdentity().GetMSPID()
			newParticipant := Participant{
				ParticipantID: participant_increasing_key,
				MSP:           msp,
				IsMulti:       true,
				X509:          key1,
			}
			sendParticipant.Participants[key1] = newParticipant
		}

		// Created Message

		if _, ok := collectiveMsg.Messages[key1]; ok {

		} else {
			collectiveMsg.Messages[key1] = make(map[string]Message)
			newAtomicMsg := Message{
				MessageID:             collectiveMsgName,
				SendParticipantKey:    key1,
				ReceiveParticipantKey: key2,
				FireflyTranID:         "",
			}
			collectiveMsg.Messages[key1][key2] = newAtomicMsg
		}

		message_increasing_key := len(sendParticipant.Participants)
		msgsToHandle = append(msgsToHandle, collectiveMsg.Messages[key1][key2])
		eventsToTrigger = append(eventsToTrigger, fmt.Sprintf("Send_Message_1vzqd37_%d", message_increasing_key))

	} else if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == true {
		// 一对多
		key1 = "nonMulti"

		participant_key := key1
		if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
			errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
			fmt.Println(errorMessage)
			return fmt.Errorf(errorMessage)
		}

		// create Maximum Number of Message
		if _, ok := collectiveMsg.Messages[key1]; ok {
			// Have Been Created, Repeated Operation
		} else {
			collectiveMsg.Messages[key1] = make(map[string]Message)
		}

		if len(collectiveMsg.Messages[key1]) >= sendParticipant.MultiMaximum {
			fmt.Println("The number of messages sent by the participant exceeds the maximum")
			return fmt.Errorf("The number of messages sent by the participant exceeds the maximum")
		}

		for i := 0; i < sendParticipant.MultiMaximum; i++ {
			key2 := fmt.Sprintf("%d", i)
			newAtomicMsg := Message{
				MessageID:             collectiveMsgName,
				SendParticipantKey:    key1,
				ReceiveParticipantKey: key2,
				FireflyTranID:         "",
			}
			collectiveMsg.Messages[key1][key2] = newAtomicMsg
		}

		for key, value := range collectiveMsg.Messages[key1] {
			msgsToHandle = append(msgsToHandle, value)
			eventsToTrigger = append(eventsToTrigger, fmt.Sprintf("Send_Message_1vzqd37_%s", key))
		}

	} else if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == true {
		// 多对多 UnSupport Type
		errorMessage = "Multi To Multi Task, Unsupported Operation"
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	for _, event := range eventsToTrigger {
		res, _ := cc.Invoke_Other_chaincode(ctx, "stateCharts:v1", "default",
			stateCharts.EncodeTriggerActionArgs(instance.StateMachineDescription, instance.CurrentState, event))
		state, changed := stateCharts.DecodeTriggerActionResult(res)
		if !changed {
			return fmt.Errorf("The state machine does not change")
		}
		instance.CurrentState = state
	}

	for _, msg := range msgsToHandle {
		cc.ChangeMsgFireflyTranID(ctx, instance, fireflyTranID, msg.MessageID, key1, key2)
	}

	stub.SetEvent(collectiveMsgName, []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_1vzqd37_Complete(ctx contractapi.TransactionContextInterface, targetTaskID int, ConfirmTargetX509 string, instanceID string) error {
	stub := ctx.GetStub()
	instance, _ := cc.GetInstance(ctx, instanceID)

	collectiveMsgName := "Message_1vzqd37"
	collectiveMsg, _ := cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)
	participant_id := collectiveMsg.ReceiveParticipantID

	// MultiTask Address Located
	choreographyTaskID := collectiveMsg.ChoreographyTaskID

	choreographyTask, _ := cc.ReadChoreographyTask(ctx, instanceID, choreographyTaskID)
	if choreographyTask.IsMulti == true {
		collectiveMsgName = fmt.Sprintf("Message_1vzqd37_%d", targetTaskID)
	}

	collectiveMsg, _ = cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)
	sendParticipantID := collectiveMsg.SendParticipantID
	receiveParticipantID := collectiveMsg.ReceiveParticipantID
	sendParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, sendParticipantID)
	receiveParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, receiveParticipantID)

	var errorMessage string
	var key1, key2 string
	var msgsToHandle []Message = make([]Message, 0)
	var eventsToTrigger []string = make([]string, 0)
	if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == false {
		// 一对一
		key1 = "nonMulti"
		key2 = "nonMulti"
		msgsToHandle = append(msgsToHandle, collectiveMsg.Messages[key1][key2])
		eventsToTrigger = append(eventsToTrigger, "Confirm_Message_1vzqd37")

		participant_key := key2
		if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
			errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
			fmt.Println(errorMessage)
			return fmt.Errorf(errorMessage)
		}

	} else if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == false {
		// 多对一 回应
		// 1. 响应所有消息
		// 2. 添加Target

		key1 = ConfirmTargetX509
		key2 = "nonMulti"

		participant_key := key2
		if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
			errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
			fmt.Println(errorMessage)
			return fmt.Errorf(errorMessage)
		}

		// Which To Confirm? Decided By ConfirmTargetX509
		confirmTargetSender, ok := sendParticipant.Participants[key1]
		if !ok {
			errorMessage := "UnExisted ConfirmTarget"
			return fmt.Errorf(errorMessage)
		}

		msgsToHandle = append(msgsToHandle, collectiveMsg.Messages[key1]["nonMulti"])
		eventsToTrigger = append(eventsToTrigger, fmt.Sprintf("Confirm_Message_1vzqd37_%s", confirmTargetSender.ParticipantID))
	} else if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == true {
		// 一对多 回应，响应自己的部分，修改计数器
		key1 = "nonMulti"
		key2 = cc.get_X509_identity(ctx)

		if receiveParticipant.IsLocked == true {
			// check if key2 in it
			if _, ok := receiveParticipant.Participants[key2]; ok {
				// check Participant
				participant_key := key2
				if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
					errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
					fmt.Println(errorMessage)
					return fmt.Errorf(errorMessage)
				}
			} else {
				return fmt.Errorf("The participant is locked and the participant is not registered")
			}
		} else {

			if receiveParticipant.MultiMaximum <= len(receiveParticipant.Participants) {
				errorMessage := "ReceiveParticipants Has Reach the Maximum"
				return fmt.Errorf(errorMessage)
			}

			if cc.check_participant(ctx, instanceID, participant_id, "") != true {
				errorMessage := "Not Allowed To participate as a Receiver"
				return fmt.Errorf(errorMessage)
			}

			// create new Participant if not exist
			x509 := cc.get_X509_identity(ctx)
			participant_increasing_key := len(receiveParticipant.Participants)
			msp, _ := ctx.GetClientIdentity().GetMSPID()
			newParticipant := Participant{
				ParticipantID: fmt.Sprintf("%d", participant_increasing_key),
				MSP:           msp,
				IsMulti:       true,
				X509:          x509,
			}
			receiveParticipant.Participants[key2] = newParticipant
		}

		// get the message and increase it's confirmedCount

		if collectiveMsg.MessageConfirmedCount >= receiveParticipant.MultiMaximum {
			return fmt.Errorf("The number of messages sent by the participant exceeds the maximum")
		}

		message_increasing_key := fmt.Sprintf("%d", collectiveMsg.MessageConfirmedCount)
		msg := collectiveMsg.Messages[key1][message_increasing_key]
		delete(collectiveMsg.Messages[key1], message_increasing_key)
		collectiveMsg.Messages[key1][key2] = msg
		collectiveMsg.MessageConfirmedCount += 1

		msgsToHandle = append(msgsToHandle, msg)
		eventsToTrigger = append(eventsToTrigger, fmt.Sprintf("Send_Message_1vzqd37_%d", message_increasing_key))

	} else if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == true {
		// 多对多 UnSupported Operations?
		errorMessage = fmt.Sprintf("UnSupported Operation")
		return fmt.Errorf(errorMessage)
	}

	for _, event := range eventsToTrigger {
		res, err := cc.Invoke_Other_chaincode(ctx, "stateCharts:v1", "default",
			stateCharts.EncodeTriggerActionArgs(instance.StateMachineDescription, instance.CurrentState, event))
		if err != nil {
			return err
		}
		state, changed := stateCharts.DecodeTriggerActionResult(res)

		if !changed {
			return fmt.Errorf("The state machine does not change")
		}

		instance.CurrentState = state
	}

	stub.SetEvent(collectiveMsgName, []byte("Message is Confirmed !"))
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_1vzqd37_Advance(
	ctx contractapi.TransactionContextInterface,
	instanceID string,
	targetTaskID string,
) error {
	stub := ctx.GetStub()
	instance, _ := cc.GetInstance(ctx, instanceID)

	collectiveMsgName := "Message_1vzqd37"
	collectiveMsg, _ := cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)

	// MultiTask Address Located
	choreographyTaskID := collectiveMsg.ChoreographyTaskID

	choreographyTask, _ := cc.ReadChoreographyTask(ctx, instanceID, choreographyTaskID)
	if choreographyTask.IsMulti == true {
		collectiveMsgName = fmt.Sprintf("Message_1vzqd37_%d", targetTaskID)
	}

	collectiveMsg, _ = cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)

	sendParticipantID := collectiveMsg.SendParticipantID
	receiveParticipantID := collectiveMsg.ReceiveParticipantID
	sendParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, sendParticipantID)
	receiveParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, receiveParticipantID)

	// Check if Multi
	if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == true {
		return fmt.Errorf("Unsupport Operation")
	}

	if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == false {
		return fmt.Errorf("Not Invalid Operation")
	}

	var participantToLock *CollectiveParticipant
	if sendParticipant.IsMulti {
		// check if invoker in receiveParticipants
		if cc.check_participant(ctx, instanceID, receiveParticipantID, "") == false {
			return fmt.Errorf("Not Allowed To Advance")
		}
		participantToLock = receiveParticipant
	} else {
		// check if invoker in senderParticipants
		if cc.check_participant(ctx, instanceID, sendParticipantID, "") == false {
			return fmt.Errorf("Not Allowd To Advance")
		}
		participantToLock = sendParticipant
	}

	if len(participantToLock.Participants) < participantToLock.MultiMinimum {
		errorMessage := fmt.Sprintf(
			"Messages count %d does not meet the minimum requirement %d for participant %s",
			len(collectiveMsg.Messages),
			participantToLock.MultiMinimum,
			participantToLock.ParticipantID,
		)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	res, err := cc.Invoke_Other_chaincode(ctx, "stateCharts:v1", "default",
		stateCharts.EncodeTriggerActionArgs(instance.StateMachineDescription, instance.CurrentState, "AdvanceMessage_1vzqd37"))
	if err != nil {
		return fmt.Errorf("failed to trigger stateCharts action: %v", err)
	}
	state, changed := stateCharts.DecodeTriggerActionResult(res)

	if !changed {
		return fmt.Errorf("Invalid Operation")
	}
	instance.CurrentState = state

	participantToLock.IsLocked = true

	err = cc.SetInstance(ctx, instance)
	if err != nil {
		return fmt.Errorf("failed to set instance: %v", err)
	}

	stub.SetEvent("AdvanceMessage_1vzqd37", []byte("CollectiveMessage advanced successfully"))
	return nil
}

func (cc *SmartContract) Message_1rqbibd_Send(ctx contractapi.TransactionContextInterface, instanceID string, targetTaskID int, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, _ := cc.GetInstance(ctx, instanceID)

	collectiveMsgName := "Message_1rqbibd"
	collectiveMsg, _ := cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)
	participant_id := collectiveMsg.SendParticipantID

	// MultiTask Address Located
	choreographyTaskID := collectiveMsg.ChoreographyTaskID

	choreographyTask, _ := cc.ReadChoreographyTask(ctx, instanceID, choreographyTaskID)
	if choreographyTask.IsMulti == true {
		collectiveMsgName = fmt.Sprintf("Message_1rqbibd_%d", targetTaskID)
	}

	// MultiParticipant Address Located

	collectiveMsg, _ = cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)
	sendParticipantID := collectiveMsg.SendParticipantID
	receiveParticipantID := collectiveMsg.ReceiveParticipantID
	sendParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, sendParticipantID)
	receiveParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, receiveParticipantID)

	var errorMessage string
	var key1, key2 string
	var msgsToHandle []Message = make([]Message, 0)
	var eventsToTrigger []string = make([]string, 0)
	if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == false {
		// 一对一
		key1 = "nonMulti"
		key2 = "nonMulti"

		msgsToHandle = append(msgsToHandle, collectiveMsg.Messages[key1][key2])
		eventsToTrigger = append(eventsToTrigger, "Send_Message_1rqbibd")

		participant_key := key1
		if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
			errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
			fmt.Println(errorMessage)
			return fmt.Errorf(errorMessage)
		}

	} else if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == false {
		// 多对一
		key1 = cc.get_X509_identity(ctx)
		key2 = "nonMulti"

		// // Auth

		// Check if Locked
		if sendParticipant.IsLocked == true {
			// check if registered
			if _, ok := sendParticipant.Participants[key1]; ok {
				// check X509
				participant_key := key1
				if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
					errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
					fmt.Println(errorMessage)
					return fmt.Errorf(errorMessage)
				}
			} else {
				return fmt.Errorf("The participant is locked and the participant is not registered")
			}
		} else {
			// else check if Participant has reach Maximum
			if sendParticipant.MultiMaximum <= len(sendParticipant.Participants) {
				return fmt.Errorf("The number of messages sent by the participant exceeds the maximum")
			}

			// Attributes Based Access Control
			if cc.check_participant(ctx, instanceID, participant_id, "") == false {
				errorMessage = fmt.Sprintf("Participant can't not register itself due to no conformance attributes")
				return fmt.Errorf(errorMessage)
			}

			// Register self, using a increasing key
			participant_increasing_key := fmt.Sprintf("%d", len(sendParticipant.Participants))
			// create new Participant if not exist
			msp, _ := ctx.GetClientIdentity().GetMSPID()
			newParticipant := Participant{
				ParticipantID: participant_increasing_key,
				MSP:           msp,
				IsMulti:       true,
				X509:          key1,
			}
			sendParticipant.Participants[key1] = newParticipant
		}

		// Created Message

		if _, ok := collectiveMsg.Messages[key1]; ok {

		} else {
			collectiveMsg.Messages[key1] = make(map[string]Message)
			newAtomicMsg := Message{
				MessageID:             collectiveMsgName,
				SendParticipantKey:    key1,
				ReceiveParticipantKey: key2,
				FireflyTranID:         "",
			}
			collectiveMsg.Messages[key1][key2] = newAtomicMsg
		}

		message_increasing_key := len(sendParticipant.Participants)
		msgsToHandle = append(msgsToHandle, collectiveMsg.Messages[key1][key2])
		eventsToTrigger = append(eventsToTrigger, fmt.Sprintf("Send_Message_1rqbibd_%d", message_increasing_key))

	} else if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == true {
		// 一对多
		key1 = "nonMulti"

		participant_key := key1
		if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
			errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
			fmt.Println(errorMessage)
			return fmt.Errorf(errorMessage)
		}

		// create Maximum Number of Message
		if _, ok := collectiveMsg.Messages[key1]; ok {
			// Have Been Created, Repeated Operation
		} else {
			collectiveMsg.Messages[key1] = make(map[string]Message)
		}

		if len(collectiveMsg.Messages[key1]) >= sendParticipant.MultiMaximum {
			fmt.Println("The number of messages sent by the participant exceeds the maximum")
			return fmt.Errorf("The number of messages sent by the participant exceeds the maximum")
		}

		for i := 0; i < sendParticipant.MultiMaximum; i++ {
			key2 := fmt.Sprintf("%d", i)
			newAtomicMsg := Message{
				MessageID:             collectiveMsgName,
				SendParticipantKey:    key1,
				ReceiveParticipantKey: key2,
				FireflyTranID:         "",
			}
			collectiveMsg.Messages[key1][key2] = newAtomicMsg
		}

		for key, value := range collectiveMsg.Messages[key1] {
			msgsToHandle = append(msgsToHandle, value)
			eventsToTrigger = append(eventsToTrigger, fmt.Sprintf("Send_Message_1rqbibd_%s", key))
		}

	} else if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == true {
		// 多对多 UnSupport Type
		errorMessage = "Multi To Multi Task, Unsupported Operation"
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	for _, event := range eventsToTrigger {
		res, _ := cc.Invoke_Other_chaincode(ctx, "stateCharts:v1", "default",
			stateCharts.EncodeTriggerActionArgs(instance.StateMachineDescription, instance.CurrentState, event))
		state, changed := stateCharts.DecodeTriggerActionResult(res)
		if !changed {
			return fmt.Errorf("The state machine does not change")
		}
		instance.CurrentState = state
	}

	for _, msg := range msgsToHandle {
		cc.ChangeMsgFireflyTranID(ctx, instance, fireflyTranID, msg.MessageID, key1, key2)
	}

	stub.SetEvent(collectiveMsgName, []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_1rqbibd_Complete(ctx contractapi.TransactionContextInterface, targetTaskID int, ConfirmTargetX509 string, instanceID string) error {
	stub := ctx.GetStub()
	instance, _ := cc.GetInstance(ctx, instanceID)

	collectiveMsgName := "Message_1rqbibd"
	collectiveMsg, _ := cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)
	participant_id := collectiveMsg.ReceiveParticipantID

	// MultiTask Address Located
	choreographyTaskID := collectiveMsg.ChoreographyTaskID

	choreographyTask, _ := cc.ReadChoreographyTask(ctx, instanceID, choreographyTaskID)
	if choreographyTask.IsMulti == true {
		collectiveMsgName = fmt.Sprintf("Message_1rqbibd_%d", targetTaskID)
	}

	collectiveMsg, _ = cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)
	sendParticipantID := collectiveMsg.SendParticipantID
	receiveParticipantID := collectiveMsg.ReceiveParticipantID
	sendParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, sendParticipantID)
	receiveParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, receiveParticipantID)

	var errorMessage string
	var key1, key2 string
	var msgsToHandle []Message = make([]Message, 0)
	var eventsToTrigger []string = make([]string, 0)
	if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == false {
		// 一对一
		key1 = "nonMulti"
		key2 = "nonMulti"
		msgsToHandle = append(msgsToHandle, collectiveMsg.Messages[key1][key2])
		eventsToTrigger = append(eventsToTrigger, "Confirm_Message_1rqbibd")

		participant_key := key2
		if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
			errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
			fmt.Println(errorMessage)
			return fmt.Errorf(errorMessage)
		}

	} else if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == false {
		// 多对一 回应
		// 1. 响应所有消息
		// 2. 添加Target

		key1 = ConfirmTargetX509
		key2 = "nonMulti"

		participant_key := key2
		if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
			errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
			fmt.Println(errorMessage)
			return fmt.Errorf(errorMessage)
		}

		// Which To Confirm? Decided By ConfirmTargetX509
		confirmTargetSender, ok := sendParticipant.Participants[key1]
		if !ok {
			errorMessage := "UnExisted ConfirmTarget"
			return fmt.Errorf(errorMessage)
		}

		msgsToHandle = append(msgsToHandle, collectiveMsg.Messages[key1]["nonMulti"])
		eventsToTrigger = append(eventsToTrigger, fmt.Sprintf("Confirm_Message_1rqbibd_%s", confirmTargetSender.ParticipantID))
	} else if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == true {
		// 一对多 回应，响应自己的部分，修改计数器
		key1 = "nonMulti"
		key2 = cc.get_X509_identity(ctx)

		if receiveParticipant.IsLocked == true {
			// check if key2 in it
			if _, ok := receiveParticipant.Participants[key2]; ok {
				// check Participant
				participant_key := key2
				if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
					errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
					fmt.Println(errorMessage)
					return fmt.Errorf(errorMessage)
				}
			} else {
				return fmt.Errorf("The participant is locked and the participant is not registered")
			}
		} else {

			if receiveParticipant.MultiMaximum <= len(receiveParticipant.Participants) {
				errorMessage := "ReceiveParticipants Has Reach the Maximum"
				return fmt.Errorf(errorMessage)
			}

			if cc.check_participant(ctx, instanceID, participant_id, "") != true {
				errorMessage := "Not Allowed To participate as a Receiver"
				return fmt.Errorf(errorMessage)
			}

			// create new Participant if not exist
			x509 := cc.get_X509_identity(ctx)
			participant_increasing_key := len(receiveParticipant.Participants)
			msp, _ := ctx.GetClientIdentity().GetMSPID()
			newParticipant := Participant{
				ParticipantID: fmt.Sprintf("%d", participant_increasing_key),
				MSP:           msp,
				IsMulti:       true,
				X509:          x509,
			}
			receiveParticipant.Participants[key2] = newParticipant
		}

		// get the message and increase it's confirmedCount

		if collectiveMsg.MessageConfirmedCount >= receiveParticipant.MultiMaximum {
			return fmt.Errorf("The number of messages sent by the participant exceeds the maximum")
		}

		message_increasing_key := fmt.Sprintf("%d", collectiveMsg.MessageConfirmedCount)
		msg := collectiveMsg.Messages[key1][message_increasing_key]
		delete(collectiveMsg.Messages[key1], message_increasing_key)
		collectiveMsg.Messages[key1][key2] = msg
		collectiveMsg.MessageConfirmedCount += 1

		msgsToHandle = append(msgsToHandle, msg)
		eventsToTrigger = append(eventsToTrigger, fmt.Sprintf("Send_Message_1rqbibd_%d", message_increasing_key))

	} else if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == true {
		// 多对多 UnSupported Operations?
		errorMessage = fmt.Sprintf("UnSupported Operation")
		return fmt.Errorf(errorMessage)
	}

	for _, event := range eventsToTrigger {
		res, err := cc.Invoke_Other_chaincode(ctx, "stateCharts:v1", "default",
			stateCharts.EncodeTriggerActionArgs(instance.StateMachineDescription, instance.CurrentState, event))
		if err != nil {
			return err
		}
		state, changed := stateCharts.DecodeTriggerActionResult(res)

		if !changed {
			return fmt.Errorf("The state machine does not change")
		}

		instance.CurrentState = state
	}

	stub.SetEvent(collectiveMsgName, []byte("Message is Confirmed !"))
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_1rqbibd_Advance(
	ctx contractapi.TransactionContextInterface,
	instanceID string,
	targetTaskID string,
) error {
	stub := ctx.GetStub()
	instance, _ := cc.GetInstance(ctx, instanceID)

	collectiveMsgName := "Message_1rqbibd"
	collectiveMsg, _ := cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)

	// MultiTask Address Located
	choreographyTaskID := collectiveMsg.ChoreographyTaskID

	choreographyTask, _ := cc.ReadChoreographyTask(ctx, instanceID, choreographyTaskID)
	if choreographyTask.IsMulti == true {
		collectiveMsgName = fmt.Sprintf("Message_1rqbibd_%d", targetTaskID)
	}

	collectiveMsg, _ = cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)

	sendParticipantID := collectiveMsg.SendParticipantID
	receiveParticipantID := collectiveMsg.ReceiveParticipantID
	sendParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, sendParticipantID)
	receiveParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, receiveParticipantID)

	// Check if Multi
	if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == true {
		return fmt.Errorf("Unsupport Operation")
	}

	if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == false {
		return fmt.Errorf("Not Invalid Operation")
	}

	var participantToLock *CollectiveParticipant
	if sendParticipant.IsMulti {
		// check if invoker in receiveParticipants
		if cc.check_participant(ctx, instanceID, receiveParticipantID, "") == false {
			return fmt.Errorf("Not Allowed To Advance")
		}
		participantToLock = receiveParticipant
	} else {
		// check if invoker in senderParticipants
		if cc.check_participant(ctx, instanceID, sendParticipantID, "") == false {
			return fmt.Errorf("Not Allowd To Advance")
		}
		participantToLock = sendParticipant
	}

	if len(participantToLock.Participants) < participantToLock.MultiMinimum {
		errorMessage := fmt.Sprintf(
			"Messages count %d does not meet the minimum requirement %d for participant %s",
			len(collectiveMsg.Messages),
			participantToLock.MultiMinimum,
			participantToLock.ParticipantID,
		)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	res, err := cc.Invoke_Other_chaincode(ctx, "stateCharts:v1", "default",
		stateCharts.EncodeTriggerActionArgs(instance.StateMachineDescription, instance.CurrentState, "AdvanceMessage_1rqbibd"))
	if err != nil {
		return fmt.Errorf("failed to trigger stateCharts action: %v", err)
	}
	state, changed := stateCharts.DecodeTriggerActionResult(res)

	if !changed {
		return fmt.Errorf("Invalid Operation")
	}
	instance.CurrentState = state

	participantToLock.IsLocked = true

	err = cc.SetInstance(ctx, instance)
	if err != nil {
		return fmt.Errorf("failed to set instance: %v", err)
	}

	stub.SetEvent("AdvanceMessage_1rqbibd", []byte("CollectiveMessage advanced successfully"))
	return nil
}

func (cc *SmartContract) EndEvent_110myff(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)

	res, err := cc.Invoke_Other_chaincode(ctx, "stateCharts", "default",
		stateCharts.EncodeTriggerActionArgs(instance.StateMachineDescription, instance.CurrentState, "EndEvent_110myff"))

	if err != nil {
		return err
	}

	state, changed := stateCharts.DecodeTriggerActionResult(res)
	if !changed {
		return errors.New("Invalid transition")
	}

	instance.CurrentState = state

	cc.SetInstance(ctx, instance)

	stub.SetEvent("EndEvent_110myff", []byte("Contract has been started successfully"))

	return nil
}

func (cc *SmartContract) Gateway_0o8snyv(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)

	if err != nil {
		return err
	}

	res, err := cc.Invoke_Other_chaincode(ctx, "stateCharts:v1", "default",
		stateCharts.EncodeTriggerActionArgs(instance.StateMachineDescription, instance.CurrentState, "Gateway_0o8snyv"))

	if err != nil {
		return err
	}
	new_status, changed := stateCharts.DecodeTriggerActionResult(res)

	if !changed {
		return errors.New("Invalid transition")
	}

	instance.CurrentState = new_status
	cc.SetInstance(ctx, instance)

	stub.SetEvent("Gateway_0o8snyv", []byte("Gateway has been done"))

	return nil
}

func (cc *SmartContract) Message_0gd0z61_Send(ctx contractapi.TransactionContextInterface, instanceID string, targetTaskID int, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, _ := cc.GetInstance(ctx, instanceID)

	collectiveMsgName := "Message_0gd0z61"
	collectiveMsg, _ := cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)
	participant_id := collectiveMsg.SendParticipantID

	// MultiTask Address Located
	choreographyTaskID := collectiveMsg.ChoreographyTaskID

	choreographyTask, _ := cc.ReadChoreographyTask(ctx, instanceID, choreographyTaskID)
	if choreographyTask.IsMulti == true {
		collectiveMsgName = fmt.Sprintf("Message_0gd0z61_%d", targetTaskID)
	}

	// MultiParticipant Address Located

	collectiveMsg, _ = cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)
	sendParticipantID := collectiveMsg.SendParticipantID
	receiveParticipantID := collectiveMsg.ReceiveParticipantID
	sendParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, sendParticipantID)
	receiveParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, receiveParticipantID)

	var errorMessage string
	var key1, key2 string
	var msgsToHandle []Message = make([]Message, 0)
	var eventsToTrigger []string = make([]string, 0)
	if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == false {
		// 一对一
		key1 = "nonMulti"
		key2 = "nonMulti"

		msgsToHandle = append(msgsToHandle, collectiveMsg.Messages[key1][key2])
		eventsToTrigger = append(eventsToTrigger, "Send_Message_0gd0z61")

		participant_key := key1
		if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
			errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
			fmt.Println(errorMessage)
			return fmt.Errorf(errorMessage)
		}

	} else if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == false {
		// 多对一
		key1 = cc.get_X509_identity(ctx)
		key2 = "nonMulti"

		// // Auth

		// Check if Locked
		if sendParticipant.IsLocked == true {
			// check if registered
			if _, ok := sendParticipant.Participants[key1]; ok {
				// check X509
				participant_key := key1
				if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
					errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
					fmt.Println(errorMessage)
					return fmt.Errorf(errorMessage)
				}
			} else {
				return fmt.Errorf("The participant is locked and the participant is not registered")
			}
		} else {
			// else check if Participant has reach Maximum
			if sendParticipant.MultiMaximum <= len(sendParticipant.Participants) {
				return fmt.Errorf("The number of messages sent by the participant exceeds the maximum")
			}

			// Attributes Based Access Control
			if cc.check_participant(ctx, instanceID, participant_id, "") == false {
				errorMessage = fmt.Sprintf("Participant can't not register itself due to no conformance attributes")
				return fmt.Errorf(errorMessage)
			}

			// Register self, using a increasing key
			participant_increasing_key := fmt.Sprintf("%d", len(sendParticipant.Participants))
			// create new Participant if not exist
			msp, _ := ctx.GetClientIdentity().GetMSPID()
			newParticipant := Participant{
				ParticipantID: participant_increasing_key,
				MSP:           msp,
				IsMulti:       true,
				X509:          key1,
			}
			sendParticipant.Participants[key1] = newParticipant
		}

		// Created Message

		if _, ok := collectiveMsg.Messages[key1]; ok {

		} else {
			collectiveMsg.Messages[key1] = make(map[string]Message)
			newAtomicMsg := Message{
				MessageID:             collectiveMsgName,
				SendParticipantKey:    key1,
				ReceiveParticipantKey: key2,
				FireflyTranID:         "",
			}
			collectiveMsg.Messages[key1][key2] = newAtomicMsg
		}

		message_increasing_key := len(sendParticipant.Participants)
		msgsToHandle = append(msgsToHandle, collectiveMsg.Messages[key1][key2])
		eventsToTrigger = append(eventsToTrigger, fmt.Sprintf("Send_Message_0gd0z61_%d", message_increasing_key))

	} else if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == true {
		// 一对多
		key1 = "nonMulti"

		participant_key := key1
		if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
			errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
			fmt.Println(errorMessage)
			return fmt.Errorf(errorMessage)
		}

		// create Maximum Number of Message
		if _, ok := collectiveMsg.Messages[key1]; ok {
			// Have Been Created, Repeated Operation
		} else {
			collectiveMsg.Messages[key1] = make(map[string]Message)
		}

		if len(collectiveMsg.Messages[key1]) >= sendParticipant.MultiMaximum {
			fmt.Println("The number of messages sent by the participant exceeds the maximum")
			return fmt.Errorf("The number of messages sent by the participant exceeds the maximum")
		}

		for i := 0; i < sendParticipant.MultiMaximum; i++ {
			key2 := fmt.Sprintf("%d", i)
			newAtomicMsg := Message{
				MessageID:             collectiveMsgName,
				SendParticipantKey:    key1,
				ReceiveParticipantKey: key2,
				FireflyTranID:         "",
			}
			collectiveMsg.Messages[key1][key2] = newAtomicMsg
		}

		for key, value := range collectiveMsg.Messages[key1] {
			msgsToHandle = append(msgsToHandle, value)
			eventsToTrigger = append(eventsToTrigger, fmt.Sprintf("Send_Message_0gd0z61_%s", key))
		}

	} else if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == true {
		// 多对多 UnSupport Type
		errorMessage = "Multi To Multi Task, Unsupported Operation"
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	for _, event := range eventsToTrigger {
		res, _ := cc.Invoke_Other_chaincode(ctx, "stateCharts:v1", "default",
			stateCharts.EncodeTriggerActionArgs(instance.StateMachineDescription, instance.CurrentState, event))
		state, changed := stateCharts.DecodeTriggerActionResult(res)
		if !changed {
			return fmt.Errorf("The state machine does not change")
		}
		instance.CurrentState = state
	}

	for _, msg := range msgsToHandle {
		cc.ChangeMsgFireflyTranID(ctx, instance, fireflyTranID, msg.MessageID, key1, key2)
	}

	stub.SetEvent(collectiveMsgName, []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_0gd0z61_Complete(ctx contractapi.TransactionContextInterface, targetTaskID int, ConfirmTargetX509 string, instanceID string) error {
	stub := ctx.GetStub()
	instance, _ := cc.GetInstance(ctx, instanceID)

	collectiveMsgName := "Message_0gd0z61"
	collectiveMsg, _ := cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)
	participant_id := collectiveMsg.ReceiveParticipantID

	// MultiTask Address Located
	choreographyTaskID := collectiveMsg.ChoreographyTaskID

	choreographyTask, _ := cc.ReadChoreographyTask(ctx, instanceID, choreographyTaskID)
	if choreographyTask.IsMulti == true {
		collectiveMsgName = fmt.Sprintf("Message_0gd0z61_%d", targetTaskID)
	}

	collectiveMsg, _ = cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)
	sendParticipantID := collectiveMsg.SendParticipantID
	receiveParticipantID := collectiveMsg.ReceiveParticipantID
	sendParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, sendParticipantID)
	receiveParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, receiveParticipantID)

	var errorMessage string
	var key1, key2 string
	var msgsToHandle []Message = make([]Message, 0)
	var eventsToTrigger []string = make([]string, 0)
	if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == false {
		// 一对一
		key1 = "nonMulti"
		key2 = "nonMulti"
		msgsToHandle = append(msgsToHandle, collectiveMsg.Messages[key1][key2])
		eventsToTrigger = append(eventsToTrigger, "Confirm_Message_0gd0z61")

		participant_key := key2
		if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
			errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
			fmt.Println(errorMessage)
			return fmt.Errorf(errorMessage)
		}

	} else if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == false {
		// 多对一 回应
		// 1. 响应所有消息
		// 2. 添加Target

		key1 = ConfirmTargetX509
		key2 = "nonMulti"

		participant_key := key2
		if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
			errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
			fmt.Println(errorMessage)
			return fmt.Errorf(errorMessage)
		}

		// Which To Confirm? Decided By ConfirmTargetX509
		confirmTargetSender, ok := sendParticipant.Participants[key1]
		if !ok {
			errorMessage := "UnExisted ConfirmTarget"
			return fmt.Errorf(errorMessage)
		}

		msgsToHandle = append(msgsToHandle, collectiveMsg.Messages[key1]["nonMulti"])
		eventsToTrigger = append(eventsToTrigger, fmt.Sprintf("Confirm_Message_0gd0z61_%s", confirmTargetSender.ParticipantID))
	} else if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == true {
		// 一对多 回应，响应自己的部分，修改计数器
		key1 = "nonMulti"
		key2 = cc.get_X509_identity(ctx)

		if receiveParticipant.IsLocked == true {
			// check if key2 in it
			if _, ok := receiveParticipant.Participants[key2]; ok {
				// check Participant
				participant_key := key2
				if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
					errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
					fmt.Println(errorMessage)
					return fmt.Errorf(errorMessage)
				}
			} else {
				return fmt.Errorf("The participant is locked and the participant is not registered")
			}
		} else {

			if receiveParticipant.MultiMaximum <= len(receiveParticipant.Participants) {
				errorMessage := "ReceiveParticipants Has Reach the Maximum"
				return fmt.Errorf(errorMessage)
			}

			if cc.check_participant(ctx, instanceID, participant_id, "") != true {
				errorMessage := "Not Allowed To participate as a Receiver"
				return fmt.Errorf(errorMessage)
			}

			// create new Participant if not exist
			x509 := cc.get_X509_identity(ctx)
			participant_increasing_key := len(receiveParticipant.Participants)
			msp, _ := ctx.GetClientIdentity().GetMSPID()
			newParticipant := Participant{
				ParticipantID: fmt.Sprintf("%d", participant_increasing_key),
				MSP:           msp,
				IsMulti:       true,
				X509:          x509,
			}
			receiveParticipant.Participants[key2] = newParticipant
		}

		// get the message and increase it's confirmedCount

		if collectiveMsg.MessageConfirmedCount >= receiveParticipant.MultiMaximum {
			return fmt.Errorf("The number of messages sent by the participant exceeds the maximum")
		}

		message_increasing_key := fmt.Sprintf("%d", collectiveMsg.MessageConfirmedCount)
		msg := collectiveMsg.Messages[key1][message_increasing_key]
		delete(collectiveMsg.Messages[key1], message_increasing_key)
		collectiveMsg.Messages[key1][key2] = msg
		collectiveMsg.MessageConfirmedCount += 1

		msgsToHandle = append(msgsToHandle, msg)
		eventsToTrigger = append(eventsToTrigger, fmt.Sprintf("Send_Message_0gd0z61_%d", message_increasing_key))

	} else if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == true {
		// 多对多 UnSupported Operations?
		errorMessage = fmt.Sprintf("UnSupported Operation")
		return fmt.Errorf(errorMessage)
	}

	for _, event := range eventsToTrigger {
		res, err := cc.Invoke_Other_chaincode(ctx, "stateCharts:v1", "default",
			stateCharts.EncodeTriggerActionArgs(instance.StateMachineDescription, instance.CurrentState, event))
		if err != nil {
			return err
		}
		state, changed := stateCharts.DecodeTriggerActionResult(res)

		if !changed {
			return fmt.Errorf("The state machine does not change")
		}

		instance.CurrentState = state
	}

	stub.SetEvent(collectiveMsgName, []byte("Message is Confirmed !"))
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_0gd0z61_Advance(
	ctx contractapi.TransactionContextInterface,
	instanceID string,
	targetTaskID string,
) error {
	stub := ctx.GetStub()
	instance, _ := cc.GetInstance(ctx, instanceID)

	collectiveMsgName := "Message_0gd0z61"
	collectiveMsg, _ := cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)

	// MultiTask Address Located
	choreographyTaskID := collectiveMsg.ChoreographyTaskID

	choreographyTask, _ := cc.ReadChoreographyTask(ctx, instanceID, choreographyTaskID)
	if choreographyTask.IsMulti == true {
		collectiveMsgName = fmt.Sprintf("Message_0gd0z61_%d", targetTaskID)
	}

	collectiveMsg, _ = cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)

	sendParticipantID := collectiveMsg.SendParticipantID
	receiveParticipantID := collectiveMsg.ReceiveParticipantID
	sendParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, sendParticipantID)
	receiveParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, receiveParticipantID)

	// Check if Multi
	if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == true {
		return fmt.Errorf("Unsupport Operation")
	}

	if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == false {
		return fmt.Errorf("Not Invalid Operation")
	}

	var participantToLock *CollectiveParticipant
	if sendParticipant.IsMulti {
		// check if invoker in receiveParticipants
		if cc.check_participant(ctx, instanceID, receiveParticipantID, "") == false {
			return fmt.Errorf("Not Allowed To Advance")
		}
		participantToLock = receiveParticipant
	} else {
		// check if invoker in senderParticipants
		if cc.check_participant(ctx, instanceID, sendParticipantID, "") == false {
			return fmt.Errorf("Not Allowd To Advance")
		}
		participantToLock = sendParticipant
	}

	if len(participantToLock.Participants) < participantToLock.MultiMinimum {
		errorMessage := fmt.Sprintf(
			"Messages count %d does not meet the minimum requirement %d for participant %s",
			len(collectiveMsg.Messages),
			participantToLock.MultiMinimum,
			participantToLock.ParticipantID,
		)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	res, err := cc.Invoke_Other_chaincode(ctx, "stateCharts:v1", "default",
		stateCharts.EncodeTriggerActionArgs(instance.StateMachineDescription, instance.CurrentState, "AdvanceMessage_0gd0z61"))
	if err != nil {
		return fmt.Errorf("failed to trigger stateCharts action: %v", err)
	}
	state, changed := stateCharts.DecodeTriggerActionResult(res)

	if !changed {
		return fmt.Errorf("Invalid Operation")
	}
	instance.CurrentState = state

	participantToLock.IsLocked = true

	err = cc.SetInstance(ctx, instance)
	if err != nil {
		return fmt.Errorf("failed to set instance: %v", err)
	}

	stub.SetEvent("AdvanceMessage_0gd0z61", []byte("CollectiveMessage advanced successfully"))
	return nil
}

func (cc *SmartContract) Gateway_1m6dgym(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)

	if err != nil {
		return err
	}

	res, err := cc.Invoke_Other_chaincode(ctx, "stateCharts:v1", "default",
		stateCharts.EncodeTriggerActionArgs(instance.StateMachineDescription, instance.CurrentState, "Gateway_1m6dgym"))

	if err != nil {
		return err
	}
	new_status, changed := stateCharts.DecodeTriggerActionResult(res)

	if !changed {
		return errors.New("Invalid transition")
	}

	instance.CurrentState = new_status
	cc.SetInstance(ctx, instance)

	stub.SetEvent("Gateway_1m6dgym", []byte("Gateway has been done"))

	return nil
}

func (cc *SmartContract) Message_13mh6mk_Send(ctx contractapi.TransactionContextInterface, instanceID string, targetTaskID int, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, _ := cc.GetInstance(ctx, instanceID)

	collectiveMsgName := "Message_13mh6mk"
	collectiveMsg, _ := cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)
	participant_id := collectiveMsg.SendParticipantID

	// MultiTask Address Located
	choreographyTaskID := collectiveMsg.ChoreographyTaskID

	choreographyTask, _ := cc.ReadChoreographyTask(ctx, instanceID, choreographyTaskID)
	if choreographyTask.IsMulti == true {
		collectiveMsgName = fmt.Sprintf("Message_13mh6mk_%d", targetTaskID)
	}

	// MultiParticipant Address Located

	collectiveMsg, _ = cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)
	sendParticipantID := collectiveMsg.SendParticipantID
	receiveParticipantID := collectiveMsg.ReceiveParticipantID
	sendParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, sendParticipantID)
	receiveParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, receiveParticipantID)

	var errorMessage string
	var key1, key2 string
	var msgsToHandle []Message = make([]Message, 0)
	var eventsToTrigger []string = make([]string, 0)
	if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == false {
		// 一对一
		key1 = "nonMulti"
		key2 = "nonMulti"

		msgsToHandle = append(msgsToHandle, collectiveMsg.Messages[key1][key2])
		eventsToTrigger = append(eventsToTrigger, "Send_Message_13mh6mk")

		participant_key := key1
		if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
			errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
			fmt.Println(errorMessage)
			return fmt.Errorf(errorMessage)
		}

	} else if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == false {
		// 多对一
		key1 = cc.get_X509_identity(ctx)
		key2 = "nonMulti"

		// // Auth

		// Check if Locked
		if sendParticipant.IsLocked == true {
			// check if registered
			if _, ok := sendParticipant.Participants[key1]; ok {
				// check X509
				participant_key := key1
				if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
					errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
					fmt.Println(errorMessage)
					return fmt.Errorf(errorMessage)
				}
			} else {
				return fmt.Errorf("The participant is locked and the participant is not registered")
			}
		} else {
			// else check if Participant has reach Maximum
			if sendParticipant.MultiMaximum <= len(sendParticipant.Participants) {
				return fmt.Errorf("The number of messages sent by the participant exceeds the maximum")
			}

			// Attributes Based Access Control
			if cc.check_participant(ctx, instanceID, participant_id, "") == false {
				errorMessage = fmt.Sprintf("Participant can't not register itself due to no conformance attributes")
				return fmt.Errorf(errorMessage)
			}

			// Register self, using a increasing key
			participant_increasing_key := fmt.Sprintf("%d", len(sendParticipant.Participants))
			// create new Participant if not exist
			msp, _ := ctx.GetClientIdentity().GetMSPID()
			newParticipant := Participant{
				ParticipantID: participant_increasing_key,
				MSP:           msp,
				IsMulti:       true,
				X509:          key1,
			}
			sendParticipant.Participants[key1] = newParticipant
		}

		// Created Message

		if _, ok := collectiveMsg.Messages[key1]; ok {

		} else {
			collectiveMsg.Messages[key1] = make(map[string]Message)
			newAtomicMsg := Message{
				MessageID:             collectiveMsgName,
				SendParticipantKey:    key1,
				ReceiveParticipantKey: key2,
				FireflyTranID:         "",
			}
			collectiveMsg.Messages[key1][key2] = newAtomicMsg
		}

		message_increasing_key := len(sendParticipant.Participants)
		msgsToHandle = append(msgsToHandle, collectiveMsg.Messages[key1][key2])
		eventsToTrigger = append(eventsToTrigger, fmt.Sprintf("Send_Message_13mh6mk_%d", message_increasing_key))

	} else if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == true {
		// 一对多
		key1 = "nonMulti"

		participant_key := key1
		if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
			errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
			fmt.Println(errorMessage)
			return fmt.Errorf(errorMessage)
		}

		// create Maximum Number of Message
		if _, ok := collectiveMsg.Messages[key1]; ok {
			// Have Been Created, Repeated Operation
		} else {
			collectiveMsg.Messages[key1] = make(map[string]Message)
		}

		if len(collectiveMsg.Messages[key1]) >= sendParticipant.MultiMaximum {
			fmt.Println("The number of messages sent by the participant exceeds the maximum")
			return fmt.Errorf("The number of messages sent by the participant exceeds the maximum")
		}

		for i := 0; i < sendParticipant.MultiMaximum; i++ {
			key2 := fmt.Sprintf("%d", i)
			newAtomicMsg := Message{
				MessageID:             collectiveMsgName,
				SendParticipantKey:    key1,
				ReceiveParticipantKey: key2,
				FireflyTranID:         "",
			}
			collectiveMsg.Messages[key1][key2] = newAtomicMsg
		}

		for key, value := range collectiveMsg.Messages[key1] {
			msgsToHandle = append(msgsToHandle, value)
			eventsToTrigger = append(eventsToTrigger, fmt.Sprintf("Send_Message_13mh6mk_%s", key))
		}

	} else if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == true {
		// 多对多 UnSupport Type
		errorMessage = "Multi To Multi Task, Unsupported Operation"
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	for _, event := range eventsToTrigger {
		res, _ := cc.Invoke_Other_chaincode(ctx, "stateCharts:v1", "default",
			stateCharts.EncodeTriggerActionArgs(instance.StateMachineDescription, instance.CurrentState, event))
		state, changed := stateCharts.DecodeTriggerActionResult(res)
		if !changed {
			return fmt.Errorf("The state machine does not change")
		}
		instance.CurrentState = state
	}

	for _, msg := range msgsToHandle {
		cc.ChangeMsgFireflyTranID(ctx, instance, fireflyTranID, msg.MessageID, key1, key2)
	}

	stub.SetEvent(collectiveMsgName, []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_13mh6mk_Complete(ctx contractapi.TransactionContextInterface, targetTaskID int, ConfirmTargetX509 string, instanceID string) error {
	stub := ctx.GetStub()
	instance, _ := cc.GetInstance(ctx, instanceID)

	collectiveMsgName := "Message_13mh6mk"
	collectiveMsg, _ := cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)
	participant_id := collectiveMsg.ReceiveParticipantID

	// MultiTask Address Located
	choreographyTaskID := collectiveMsg.ChoreographyTaskID

	choreographyTask, _ := cc.ReadChoreographyTask(ctx, instanceID, choreographyTaskID)
	if choreographyTask.IsMulti == true {
		collectiveMsgName = fmt.Sprintf("Message_13mh6mk_%d", targetTaskID)
	}

	collectiveMsg, _ = cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)
	sendParticipantID := collectiveMsg.SendParticipantID
	receiveParticipantID := collectiveMsg.ReceiveParticipantID
	sendParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, sendParticipantID)
	receiveParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, receiveParticipantID)

	var errorMessage string
	var key1, key2 string
	var msgsToHandle []Message = make([]Message, 0)
	var eventsToTrigger []string = make([]string, 0)
	if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == false {
		// 一对一
		key1 = "nonMulti"
		key2 = "nonMulti"
		msgsToHandle = append(msgsToHandle, collectiveMsg.Messages[key1][key2])
		eventsToTrigger = append(eventsToTrigger, "Confirm_Message_13mh6mk")

		participant_key := key2
		if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
			errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
			fmt.Println(errorMessage)
			return fmt.Errorf(errorMessage)
		}

	} else if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == false {
		// 多对一 回应
		// 1. 响应所有消息
		// 2. 添加Target

		key1 = ConfirmTargetX509
		key2 = "nonMulti"

		participant_key := key2
		if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
			errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
			fmt.Println(errorMessage)
			return fmt.Errorf(errorMessage)
		}

		// Which To Confirm? Decided By ConfirmTargetX509
		confirmTargetSender, ok := sendParticipant.Participants[key1]
		if !ok {
			errorMessage := "UnExisted ConfirmTarget"
			return fmt.Errorf(errorMessage)
		}

		msgsToHandle = append(msgsToHandle, collectiveMsg.Messages[key1]["nonMulti"])
		eventsToTrigger = append(eventsToTrigger, fmt.Sprintf("Confirm_Message_13mh6mk_%s", confirmTargetSender.ParticipantID))
	} else if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == true {
		// 一对多 回应，响应自己的部分，修改计数器
		key1 = "nonMulti"
		key2 = cc.get_X509_identity(ctx)

		if receiveParticipant.IsLocked == true {
			// check if key2 in it
			if _, ok := receiveParticipant.Participants[key2]; ok {
				// check Participant
				participant_key := key2
				if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false {
					errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
					fmt.Println(errorMessage)
					return fmt.Errorf(errorMessage)
				}
			} else {
				return fmt.Errorf("The participant is locked and the participant is not registered")
			}
		} else {

			if receiveParticipant.MultiMaximum <= len(receiveParticipant.Participants) {
				errorMessage := "ReceiveParticipants Has Reach the Maximum"
				return fmt.Errorf(errorMessage)
			}

			if cc.check_participant(ctx, instanceID, participant_id, "") != true {
				errorMessage := "Not Allowed To participate as a Receiver"
				return fmt.Errorf(errorMessage)
			}

			// create new Participant if not exist
			x509 := cc.get_X509_identity(ctx)
			participant_increasing_key := len(receiveParticipant.Participants)
			msp, _ := ctx.GetClientIdentity().GetMSPID()
			newParticipant := Participant{
				ParticipantID: fmt.Sprintf("%d", participant_increasing_key),
				MSP:           msp,
				IsMulti:       true,
				X509:          x509,
			}
			receiveParticipant.Participants[key2] = newParticipant
		}

		// get the message and increase it's confirmedCount

		if collectiveMsg.MessageConfirmedCount >= receiveParticipant.MultiMaximum {
			return fmt.Errorf("The number of messages sent by the participant exceeds the maximum")
		}

		message_increasing_key := fmt.Sprintf("%d", collectiveMsg.MessageConfirmedCount)
		msg := collectiveMsg.Messages[key1][message_increasing_key]
		delete(collectiveMsg.Messages[key1], message_increasing_key)
		collectiveMsg.Messages[key1][key2] = msg
		collectiveMsg.MessageConfirmedCount += 1

		msgsToHandle = append(msgsToHandle, msg)
		eventsToTrigger = append(eventsToTrigger, fmt.Sprintf("Send_Message_13mh6mk_%d", message_increasing_key))

	} else if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == true {
		// 多对多 UnSupported Operations?
		errorMessage = fmt.Sprintf("UnSupported Operation")
		return fmt.Errorf(errorMessage)
	}

	for _, event := range eventsToTrigger {
		res, err := cc.Invoke_Other_chaincode(ctx, "stateCharts:v1", "default",
			stateCharts.EncodeTriggerActionArgs(instance.StateMachineDescription, instance.CurrentState, event))
		if err != nil {
			return err
		}
		state, changed := stateCharts.DecodeTriggerActionResult(res)

		if !changed {
			return fmt.Errorf("The state machine does not change")
		}

		instance.CurrentState = state
	}

	stub.SetEvent(collectiveMsgName, []byte("Message is Confirmed !"))
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_13mh6mk_Advance(
	ctx contractapi.TransactionContextInterface,
	instanceID string,
	targetTaskID string,
) error {
	stub := ctx.GetStub()
	instance, _ := cc.GetInstance(ctx, instanceID)

	collectiveMsgName := "Message_13mh6mk"
	collectiveMsg, _ := cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)

	// MultiTask Address Located
	choreographyTaskID := collectiveMsg.ChoreographyTaskID

	choreographyTask, _ := cc.ReadChoreographyTask(ctx, instanceID, choreographyTaskID)
	if choreographyTask.IsMulti == true {
		collectiveMsgName = fmt.Sprintf("Message_13mh6mk_%d", targetTaskID)
	}

	collectiveMsg, _ = cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)

	sendParticipantID := collectiveMsg.SendParticipantID
	receiveParticipantID := collectiveMsg.ReceiveParticipantID
	sendParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, sendParticipantID)
	receiveParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, receiveParticipantID)

	// Check if Multi
	if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == true {
		return fmt.Errorf("Unsupport Operation")
	}

	if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == false {
		return fmt.Errorf("Not Invalid Operation")
	}

	var participantToLock *CollectiveParticipant
	if sendParticipant.IsMulti {
		// check if invoker in receiveParticipants
		if cc.check_participant(ctx, instanceID, receiveParticipantID, "") == false {
			return fmt.Errorf("Not Allowed To Advance")
		}
		participantToLock = receiveParticipant
	} else {
		// check if invoker in senderParticipants
		if cc.check_participant(ctx, instanceID, sendParticipantID, "") == false {
			return fmt.Errorf("Not Allowd To Advance")
		}
		participantToLock = sendParticipant
	}

	if len(participantToLock.Participants) < participantToLock.MultiMinimum {
		errorMessage := fmt.Sprintf(
			"Messages count %d does not meet the minimum requirement %d for participant %s",
			len(collectiveMsg.Messages),
			participantToLock.MultiMinimum,
			participantToLock.ParticipantID,
		)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	res, err := cc.Invoke_Other_chaincode(ctx, "stateCharts:v1", "default",
		stateCharts.EncodeTriggerActionArgs(instance.StateMachineDescription, instance.CurrentState, "AdvanceMessage_13mh6mk"))
	if err != nil {
		return fmt.Errorf("failed to trigger stateCharts action: %v", err)
	}
	state, changed := stateCharts.DecodeTriggerActionResult(res)

	if !changed {
		return fmt.Errorf("Invalid Operation")
	}
	instance.CurrentState = state

	participantToLock.IsLocked = true

	err = cc.SetInstance(ctx, instance)
	if err != nil {
		return fmt.Errorf("failed to set instance: %v", err)
	}

	stub.SetEvent("AdvanceMessage_13mh6mk", []byte("CollectiveMessage advanced successfully"))
	return nil
}
