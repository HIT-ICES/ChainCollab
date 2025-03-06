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
	"time"
)

type SmartContract struct {
	contractapi.Contract
}

type StateMemory struct {
}

type InitParameters struct {
	Participant_17tx0st     ParticipantForInit `json:"Participant_17tx0st"`
	Participant_00k92jw     ParticipantForInit `json:"Participant_00k92jw"`
	StateMachineDescription string             `json:"stateMachineDescription"`
	AdditionalContent       string             `json:"additionalContent"`
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
	AdditionalContent       string `json:"AdditionalContent"`
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
		collectiveMessage.Messages["nonMulti"] = make(map[string]Message)
		message := Message{
			MessageID:             fmt.Sprintf("%s", messageID),
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

func (cc *SmartContract) ReadBusinessRule(ctx contractapi.TransactionContextInterface, instance *ContractInstance, BusinessRuleID string) (*BusinessRule, error) {
	businessRule, ok := instance.InstanceBusinessRules[BusinessRuleID]
	if !ok {
		errorMessage := fmt.Sprintf("BusinessRule %s does not exist", BusinessRuleID)
		fmt.Println(errorMessage)
		return nil, errors.New(errorMessage)
	}

	return businessRule, nil
}

func (cc *SmartContract) ReadCollectiveParticipant(ctx contractapi.TransactionContextInterface, instance *ContractInstance, participantID string) (*CollectiveParticipant, error) {
	collectiveParticipant, ok := instance.InstanceParticipants[participantID]
	if !ok {
		errorMessage := fmt.Sprintf("CollectiveParticipant %s does not exist", participantID)
		fmt.Println(errorMessage)
		return nil, errors.New(errorMessage)
	}

	return collectiveParticipant, nil
}

func (cc *SmartContract) ReadAtomicParticipant(ctx contractapi.TransactionContextInterface, instance *ContractInstance, participantID string, key string) (*Participant, error) {
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

func (cc *SmartContract) check_msp(ctx contractapi.TransactionContextInterface, instance *ContractInstance, target_participant string, key string) bool {
	targetParticipant, err := cc.ReadAtomicParticipant(ctx, instance, target_participant, key)
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

func (cc *SmartContract) check_attribute(ctx contractapi.TransactionContextInterface, instance *ContractInstance, target_participant string, attributeName string) bool {
	collectiveParticipant, err := cc.ReadCollectiveParticipant(ctx, instance, target_participant)
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

func (cc *SmartContract) check_participant(ctx contractapi.TransactionContextInterface, instance *ContractInstance, target_participant string, key string) bool {
	collectiveParticipant, err := cc.ReadCollectiveParticipant(ctx, instance, target_participant)
	if err != nil {
		fmt.Printf("Failed to read collective participant: %v\n", err)
		return false
	}

	if key == "" {
		// only check Participant based on Attributes in CollectiveParticipant
		for attrName := range collectiveParticipant.Attributes {
			if !cc.check_attribute(ctx, instance, target_participant, attrName) {
				fmt.Printf("Attribute check failed for attribute %s\n", attrName)
				return false
			}
		}
		return true
	}

	if !collectiveParticipant.IsMulti {
		defaultKey := fmt.Sprintf("%s", target_participant)
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
			if !cc.check_attribute(ctx, instance, target_participant, attrName) {
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
		if !cc.check_attribute(ctx, instance, target_participant, attrName) {
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

func (c *SmartContract) ReadCollectiveMsg(ctx contractapi.TransactionContextInterface, instance *ContractInstance, messageID string) (*CollectiveMessage, error) {
	collectiveMsg, ok := instance.InstanceMessages[messageID]
	if !ok {
		errorMessage := fmt.Sprintf("CollectiveMessage %s does not exist", messageID)
		fmt.Println(errorMessage)
		return nil, errors.New(errorMessage)
	}

	return collectiveMsg, nil
}

func (c *SmartContract) ReadAtomicMsg(ctx contractapi.TransactionContextInterface, instance *ContractInstance, messageID string, key1 string, key2 string) (*Message, error) {
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

func (c *SmartContract) ReadChoreographyTask(ctx contractapi.TransactionContextInterface, instance *ContractInstance, choreographyTaskID string) (*ChoreographyTask, error) {
	choreographyTask, ok := instance.InstanceChoreographyTasks[choreographyTaskID]
	if !ok {
		errorMessage := fmt.Sprintf("ChoreographyTask %s does not exist", choreographyTaskID)
		fmt.Println(errorMessage)
		return nil, errors.New(errorMessage)
	}

	return choreographyTask, nil
}

func (c *SmartContract) GetCurrentState(ctx contractapi.TransactionContextInterface, instanceID string) (string, error) {
	instance, err := c.GetInstance(ctx, instanceID)
	if err != nil {
		return "", err
	}

	return instance.CurrentState, nil
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

	fmt.Println("InitParameters: ", initParameters.StateMachineDescription)
	fmt.Println("InitParameters: ", initParameters.AdditionalContent)

	res, err := cc.Invoke_Other_chaincode(ctx, "StateChartEngine:v1", "default", stateCharts.EncodeGetDefaultSnapshotArgs(initParameters.StateMachineDescription, initParameters.AdditionalContent))

	if err != nil {
		fmt.Println("Error Happend")
		fmt.Print(err.Error())
	}

	fmt.Println("Res:")
	fmt.Println(string(res))

	initialSnapshot := stateCharts.DecodeGetDefaultSnapshotResult(res)

	fmt.Println("InitialSnapshot")
	fmt.Println(initialSnapshot)

	instance := ContractInstance{
		InstanceID:                instanceID,
		InstanceStateMemory:       StateMemory{},
		InstanceMessages:          make(map[string]*CollectiveMessage),
		InstanceParticipants:      make(map[string]*CollectiveParticipant),
		InstanceBusinessRules:     make(map[string]*BusinessRule),
		InstanceChoreographyTasks: make(map[string]*ChoreographyTask),
		CurrentState:              initialSnapshot,
		StateMachineDescription:   initParameters.StateMachineDescription,
		AdditionalContent:         initParameters.AdditionalContent,
	}

	// Update the currentInstanceID

	cc.CreateParticipant(ctx, &instance, "Participant_17tx0st", initParameters.Participant_17tx0st.MSP, initParameters.Participant_17tx0st.Attributes, initParameters.Participant_17tx0st.X509, initParameters.Participant_17tx0st.IsMulti, 10, 0)
	cc.CreateParticipant(ctx, &instance, "Participant_00k92jw", initParameters.Participant_00k92jw.MSP, initParameters.Participant_00k92jw.Attributes, initParameters.Participant_00k92jw.X509, initParameters.Participant_00k92jw.IsMulti, 0, 0)
	cc.CreateMessage(ctx, &instance, "Message_0j305jt", "Participant_17tx0st", "Participant_00k92jw", "", `{"properties":{"aaa":{"type":"string","description":""}},"required":[],"files":{},"file required":[]}`, true, "ChoreographyTask_18l96lu")
	cc.CreateMessage(ctx, &instance, "Message_0ip1epl", "Participant_00k92jw", "Participant_17tx0st", "", `{"properties":{"fff":{"type":"string","description":""}},"required":[],"files":{},"file required":[]}`, true, "ChoreographyTask_0qwd0ib")
	cc.CreateChoreographyTask(ctx, &instance, "ChoreographyTask_18l96lu", false, "TaskLoopType.NONE", "Message_0j305jt", "")
	cc.CreateChoreographyTask(ctx, &instance, "ChoreographyTask_0qwd0ib", false, "TaskLoopType.NONE", "Message_0ip1epl", "")

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

func (cc *SmartContract) Event_0ooh8t8(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)

	event := map[string]interface{}{
		"type": "Event_0ooh8t8",
	}

	eventJsonBytes, _ := json.Marshal(event)

	eventJsonString := string(eventJsonBytes)

	res, err := cc.Invoke_Other_chaincode(ctx, "stateCharts", "default",
		stateCharts.EncodeExecuteStateMachineArgs(instance.StateMachineDescription, instance.AdditionalContent, instance.CurrentState, eventJsonString))

	if err != nil {
		return err
	}

	state, changed := stateCharts.DecodeTriggerActionResult(res)

	fmt.Println("State")
	fmt.Println(state)

	fmt.Println("Changed")
	fmt.Println(changed)

	if !changed {
		return errors.New("Invalid transition")
	}

	instance.CurrentState = state

	cc.SetInstance(ctx, instance)

	stub.SetEvent("Event_0ooh8t8", []byte("Contract has been started successfully"))

	return nil
}

func (cc *SmartContract) Message_0j305jt_Send(ctx contractapi.TransactionContextInterface, instanceID string, targetTaskID int, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, _ := cc.GetInstance(ctx, instanceID)

	collectiveMsgName := "Message_0j305jt"
	collectiveMsg, _ := cc.ReadCollectiveMsg(ctx, instance, collectiveMsgName)
	participant_id := collectiveMsg.SendParticipantID

	// MultiTask Address Located
	choreographyTaskID := collectiveMsg.ChoreographyTaskID

	choreographyTask, _ := cc.ReadChoreographyTask(ctx, instance, choreographyTaskID)
	if choreographyTask.IsMulti == true {
		if targetTaskID == 0 {
			collectiveMsgName = "Message_0j305jt"
		} else {
			collectiveMsgName = fmt.Sprintf("Message_0j305jt_%d", targetTaskID)
		}
	}

	// MultiParticipant Address Located

	collectiveMsg, _ = cc.ReadCollectiveMsg(ctx, instance, collectiveMsgName)
	sendParticipantID := collectiveMsg.SendParticipantID
	receiveParticipantID := collectiveMsg.ReceiveParticipantID
	sendParticipant, _ := cc.ReadCollectiveParticipant(ctx, instance, sendParticipantID)
	receiveParticipant, _ := cc.ReadCollectiveParticipant(ctx, instance, receiveParticipantID)

	var errorMessage string
	var key1, key2 string
	var msgsToHandle []Message = make([]Message, 0)
	var eventsToTrigger []string = make([]string, 0)
	var event map[string]interface{}
	var eventJsonBytes []byte
	var eventJsonString string
	if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == false {
		// 一对一
		key1 = "nonMulti"
		key2 = "nonMulti"

		msgsToHandle = append(msgsToHandle, collectiveMsg.Messages[key1][key2])

		event = map[string]interface{}{
			"type": "Send_Message_0j305jt",
		}

		eventJsonBytes, _ = json.Marshal(event)

		eventJsonString = string(eventJsonBytes)

		eventsToTrigger = append(eventsToTrigger, eventJsonString)

		participant_key := key1
		if cc.check_participant(ctx, instance, participant_id, participant_key) == false {
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
				if cc.check_participant(ctx, instance, participant_id, participant_key) == false {
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
			if cc.check_participant(ctx, instance, participant_id, "") == false {
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
			fmt.Println("The number of messages sent by the participant exceeds the maximum")
		} else {
			collectiveMsg.Messages[key1] = make(map[string]Message)
			newAtomicMsg := Message{
				MessageID:             collectiveMsgName,
				SendParticipantKey:    key1,
				ReceiveParticipantKey: key2,
				FireflyTranID:         "",
			}
			collectiveMsg.Messages[key1][key2] = newAtomicMsg
			messageJsonBytes, _ := json.Marshal(collectiveMsg.Messages[key1][key2])
			fmt.Println(string(messageJsonBytes))
		}

		message_increasing_key := len(sendParticipant.Participants) - 1 // reduce the one increased by self
		msgsToHandle = append(msgsToHandle, collectiveMsg.Messages[key1][key2])

		event = map[string]interface{}{
			"type": fmt.Sprintf("Send_Message_0j305jt_%d", message_increasing_key),
		}

		eventJsonBytes, _ = json.Marshal(event)

		eventJsonString = string(eventJsonBytes)

		eventsToTrigger = append(eventsToTrigger, eventJsonString)

	} else if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == true {
		// 一对多
		key1 = "nonMulti"

		participant_key := key1
		if cc.check_participant(ctx, instance, participant_id, participant_key) == false {
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

		if len(collectiveMsg.Messages[key1]) >= receiveParticipant.MultiMaximum {
			fmt.Println("The number of messages sent by the participant exceeds the maximum")
			return fmt.Errorf("The number of messages sent by the participant exceeds the maximum")
		}

		for i := 0; i < receiveParticipant.MultiMaximum; i++ {
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
			event = map[string]interface{}{
				"type": fmt.Sprintf("Send_Message_0j305jt_%s", key),
			}
			eventJsonBytes, _ = json.Marshal(event)
			eventJsonString = string(eventJsonBytes)
			eventsToTrigger = append(eventsToTrigger, eventJsonString)
		}

	} else if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == true {
		// 多对多 UnSupport Type
		errorMessage = "Multi To Multi Task, Unsupported Operation"
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	for _, event := range eventsToTrigger {

		fmt.Printf(event)

		res, err := cc.Invoke_Other_chaincode(ctx, "StateChartEngine:v1", "default",
			stateCharts.EncodeExecuteStateMachineArgs(instance.StateMachineDescription, instance.AdditionalContent, instance.CurrentState, event))

		if err != nil {
			fmt.Printf(err.Error())
			return err
		}

		fmt.Printf(string(res))

		state, changed := stateCharts.DecodeTriggerActionResult(res)

		fmt.Printf("State: %s\n", state)
		fmt.Printf("Changed: %t\n", changed)

		if !changed {
			return fmt.Errorf("The state machine does not change")
		}
		instance.CurrentState = state
	}

	instanceJson, _ := json.Marshal(instance)
	fmt.Println(string(instanceJson))

	for _, msg := range msgsToHandle {
		cc.ChangeMsgFireflyTranID(ctx, instance, fireflyTranID, msg.MessageID, key1, key2)
	}

	stub.SetEvent(collectiveMsgName, []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_0j305jt_Complete(ctx contractapi.TransactionContextInterface, instanceID string, targetTaskID int, ConfirmTargetX509 string) error {
	stub := ctx.GetStub()
	instance, _ := cc.GetInstance(ctx, instanceID)

	collectiveMsgName := "Message_0j305jt"
	collectiveMsg, _ := cc.ReadCollectiveMsg(ctx, instance, collectiveMsgName)
	participant_id := collectiveMsg.ReceiveParticipantID

	// MultiTask Address Located
	choreographyTaskID := collectiveMsg.ChoreographyTaskID

	choreographyTask, _ := cc.ReadChoreographyTask(ctx, instance, choreographyTaskID)
	if choreographyTask.IsMulti == true {
		if targetTaskID == 0 {
			collectiveMsgName = "Message_0j305jt"
		} else {
			collectiveMsgName = fmt.Sprintf("Message_0j305jt_%d", targetTaskID)
		}
	}

	collectiveMsg, _ = cc.ReadCollectiveMsg(ctx, instance, collectiveMsgName)
	sendParticipantID := collectiveMsg.SendParticipantID
	receiveParticipantID := collectiveMsg.ReceiveParticipantID
	sendParticipant, _ := cc.ReadCollectiveParticipant(ctx, instance, sendParticipantID)
	receiveParticipant, _ := cc.ReadCollectiveParticipant(ctx, instance, receiveParticipantID)

	var errorMessage string
	var key1, key2 string
	var msgsToHandle []Message = make([]Message, 0)
	var eventsToTrigger []string = make([]string, 0)
	var event map[string]interface{}
	var eventJsonString string
	var eventJsonBytes []byte
	if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == false {
		// 一对一
		key1 = "nonMulti"
		key2 = "nonMulti"
		msgsToHandle = append(msgsToHandle, collectiveMsg.Messages[key1][key2])

		event = map[string]interface{}{
			"type": "Confirm_Message_0j305jt",
		}

		eventJsonBytes, _ = json.Marshal(event)

		eventJsonString = string(eventJsonBytes)
		eventsToTrigger = append(eventsToTrigger, eventJsonString)

		participant_key := key2
		if cc.check_participant(ctx, instance, participant_id, participant_key) == false {
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
		if cc.check_participant(ctx, instance, participant_id, participant_key) == false {
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

		event = map[string]interface{}{
			"type": fmt.Sprintf("Confirm_Message_0j305jt_%s", confirmTargetSender.ParticipantID),
		}

		eventJsonBytes, _ = json.Marshal(event)

		eventJsonString = string(eventJsonBytes)

		eventsToTrigger = append(eventsToTrigger, eventJsonString)
	} else if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == true {
		// 一对多 回应，响应自己的部分，修改计数器
		key1 = "nonMulti"
		key2 = cc.get_X509_identity(ctx)

		if receiveParticipant.IsLocked == true {
			// check if key2 in it
			if _, ok := receiveParticipant.Participants[key2]; ok {
				// check Participant
				participant_key := key2
				if cc.check_participant(ctx, instance, participant_id, participant_key) == false {
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

			if cc.check_participant(ctx, instance, participant_id, "") != true {
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

		event = map[string]interface{}{
			"type": fmt.Sprintf("Confirm_Message_0j305jt_%d", message_increasing_key),
		}

		eventJsonBytes, _ = json.Marshal(event)

		eventJsonString = string(eventJsonBytes)

		eventsToTrigger = append(eventsToTrigger, eventJsonString)

	} else if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == true {
		// 多对多 UnSupported Operations?
		errorMessage = fmt.Sprintf("UnSupported Operation")
		return fmt.Errorf(errorMessage)
	}

	for _, event := range eventsToTrigger {

		fmt.Println("Event")
		fmt.Println(event)

		res, err := cc.Invoke_Other_chaincode(ctx, "StateChartEngine:v1", "default",
			stateCharts.EncodeExecuteStateMachineArgs(instance.StateMachineDescription, instance.AdditionalContent, instance.CurrentState, event))
		if err != nil {
			return err
		}
		state, changed := stateCharts.DecodeTriggerActionResult(res)

		fmt.Println("State")
		fmt.Println(state)

		fmt.Println("Changed")
		fmt.Println(changed)

		if !changed {
			return fmt.Errorf("The state machine does not change")
		}

		instance.CurrentState = state
	}

	stub.SetEvent(collectiveMsgName, []byte("Message is Confirmed !"))
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_0j305jt_Advance(
	ctx contractapi.TransactionContextInterface,
	instanceID string,
	targetTaskID string,
) error {
	stub := ctx.GetStub()
	instance, _ := cc.GetInstance(ctx, instanceID)

	collectiveMsgName := "Message_0j305jt"
	collectiveMsg, _ := cc.ReadCollectiveMsg(ctx, instance, collectiveMsgName)

	// MultiTask Address Located
	choreographyTaskID := collectiveMsg.ChoreographyTaskID

	choreographyTask, _ := cc.ReadChoreographyTask(ctx, instance, choreographyTaskID)
	if choreographyTask.IsMulti == true {
		collectiveMsgName = fmt.Sprintf("Message_0j305jt_%d", targetTaskID)
	}

	collectiveMsg, _ = cc.ReadCollectiveMsg(ctx, instance, collectiveMsgName)

	sendParticipantID := collectiveMsg.SendParticipantID
	receiveParticipantID := collectiveMsg.ReceiveParticipantID
	sendParticipant, _ := cc.ReadCollectiveParticipant(ctx, instance, sendParticipantID)
	receiveParticipant, _ := cc.ReadCollectiveParticipant(ctx, instance, receiveParticipantID)

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
		if cc.check_participant(ctx, instance, receiveParticipantID, "") == false {
			return fmt.Errorf("Not Allowed To Advance")
		}
		participantToLock = receiveParticipant
	} else {
		// check if invoker in senderParticipants
		if cc.check_participant(ctx, instance, sendParticipantID, "") == false {
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

	event := map[string]interface{}{
		"type": "advance_Message_0j305jt",
	}
	eventJsonBytes, _ := json.Marshal(event)

	eventJsonString := string(eventJsonBytes)

	fmt.Println("Event")
	fmt.Println(eventJsonString)

	bT := time.Now() // 开始时间

	res, err := cc.Invoke_Other_chaincode(ctx, "StateChartEngine:v1", "default",
		stateCharts.EncodeExecuteStateMachineArgs(instance.StateMachineDescription, instance.AdditionalContent, instance.CurrentState, eventJsonString))

	eT := time.Since(bT) // 从开始到当前所消耗的时间
	fmt.Println("*****Run time******: ", eT)

	if err != nil {
		return fmt.Errorf("failed to trigger stateCharts action: %v", err)
	}
	state, changed := stateCharts.DecodeTriggerActionResult(res)

	fmt.Println("State")
	fmt.Println(state)
	fmt.Println("Changed")
	fmt.Println(changed)

	if !changed {
		return fmt.Errorf("Invalid Operation")
	}
	instance.CurrentState = state

	participantToLock.IsLocked = true

	err = cc.SetInstance(ctx, instance)
	if err != nil {
		return fmt.Errorf("failed to set instance: %v", err)
	}

	stub.SetEvent("AdvanceMessage_0j305jt", []byte("CollectiveMessage advanced successfully"))
	return nil
}

func (cc *SmartContract) Message_0ip1epl_Send(ctx contractapi.TransactionContextInterface, instanceID string, targetTaskID int, fireflyTranID string) error {
	stub := ctx.GetStub()
	instance, _ := cc.GetInstance(ctx, instanceID)

	collectiveMsgName := "Message_0ip1epl"
	collectiveMsg, _ := cc.ReadCollectiveMsg(ctx, instance, collectiveMsgName)
	participant_id := collectiveMsg.SendParticipantID

	// MultiTask Address Located
	choreographyTaskID := collectiveMsg.ChoreographyTaskID

	choreographyTask, _ := cc.ReadChoreographyTask(ctx, instance, choreographyTaskID)
	if choreographyTask.IsMulti == true {
		if targetTaskID == 0 {
			collectiveMsgName = "Message_0ip1epl"
		} else {
			collectiveMsgName = fmt.Sprintf("Message_0ip1epl_%d", targetTaskID)
		}
	}

	// MultiParticipant Address Located

	collectiveMsg, _ = cc.ReadCollectiveMsg(ctx, instance, collectiveMsgName)
	sendParticipantID := collectiveMsg.SendParticipantID
	receiveParticipantID := collectiveMsg.ReceiveParticipantID
	sendParticipant, _ := cc.ReadCollectiveParticipant(ctx, instance, sendParticipantID)
	receiveParticipant, _ := cc.ReadCollectiveParticipant(ctx, instance, receiveParticipantID)

	var errorMessage string
	var key1, key2 string
	var msgsToHandle []Message = make([]Message, 0)
	var eventsToTrigger []string = make([]string, 0)
	var event map[string]interface{}
	var eventJsonBytes []byte
	var eventJsonString string
	if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == false {
		// 一对一
		key1 = "nonMulti"
		key2 = "nonMulti"

		msgsToHandle = append(msgsToHandle, collectiveMsg.Messages[key1][key2])

		event = map[string]interface{}{
			"type": "Send_Message_0ip1epl",
		}

		eventJsonBytes, _ = json.Marshal(event)

		eventJsonString = string(eventJsonBytes)

		eventsToTrigger = append(eventsToTrigger, eventJsonString)

		participant_key := key1
		if cc.check_participant(ctx, instance, participant_id, participant_key) == false {
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
				if cc.check_participant(ctx, instance, participant_id, participant_key) == false {
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
			if cc.check_participant(ctx, instance, participant_id, "") == false {
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
			fmt.Println("The number of messages sent by the participant exceeds the maximum")
		} else {
			collectiveMsg.Messages[key1] = make(map[string]Message)
			newAtomicMsg := Message{
				MessageID:             collectiveMsgName,
				SendParticipantKey:    key1,
				ReceiveParticipantKey: key2,
				FireflyTranID:         "",
			}
			collectiveMsg.Messages[key1][key2] = newAtomicMsg
			messageJsonBytes, _ := json.Marshal(collectiveMsg.Messages[key1][key2])
			fmt.Println(string(messageJsonBytes))
		}

		message_increasing_key := len(sendParticipant.Participants) - 1 // reduce the one increased by self
		msgsToHandle = append(msgsToHandle, collectiveMsg.Messages[key1][key2])

		event = map[string]interface{}{
			"type": fmt.Sprintf("Send_Message_0ip1epl_%d", message_increasing_key),
		}

		eventJsonBytes, _ = json.Marshal(event)

		eventJsonString = string(eventJsonBytes)

		eventsToTrigger = append(eventsToTrigger, eventJsonString)

	} else if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == true {
		// 一对多
		key1 = "nonMulti"

		participant_key := key1
		if cc.check_participant(ctx, instance, participant_id, participant_key) == false {
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

		if len(collectiveMsg.Messages[key1]) >= receiveParticipant.MultiMaximum {
			fmt.Println("The number of messages sent by the participant exceeds the maximum")
			return fmt.Errorf("The number of messages sent by the participant exceeds the maximum")
		}

		for i := 0; i < receiveParticipant.MultiMaximum; i++ {
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
			event = map[string]interface{}{
				"type": fmt.Sprintf("Send_Message_0ip1epl_%s", key),
			}
			eventJsonBytes, _ = json.Marshal(event)
			eventJsonString = string(eventJsonBytes)
			eventsToTrigger = append(eventsToTrigger, eventJsonString)
		}

	} else if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == true {
		// 多对多 UnSupport Type
		errorMessage = "Multi To Multi Task, Unsupported Operation"
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	for _, event := range eventsToTrigger {

		fmt.Printf(event)

		res, err := cc.Invoke_Other_chaincode(ctx, "StateChartEngine:v1", "default",
			stateCharts.EncodeExecuteStateMachineArgs(instance.StateMachineDescription, instance.AdditionalContent, instance.CurrentState, event))

		if err != nil {
			fmt.Printf(err.Error())
			return err
		}

		fmt.Printf(string(res))

		state, changed := stateCharts.DecodeTriggerActionResult(res)

		fmt.Printf("State: %s\n", state)
		fmt.Printf("Changed: %t\n", changed)

		if !changed {
			return fmt.Errorf("The state machine does not change")
		}
		instance.CurrentState = state
	}

	instanceJson, _ := json.Marshal(instance)
	fmt.Println(string(instanceJson))

	for _, msg := range msgsToHandle {
		cc.ChangeMsgFireflyTranID(ctx, instance, fireflyTranID, msg.MessageID, key1, key2)
	}

	stub.SetEvent(collectiveMsgName, []byte("Message is waiting for confirmation"))
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_0ip1epl_Complete(ctx contractapi.TransactionContextInterface, instanceID string, targetTaskID int, ConfirmTargetX509 string) error {
	stub := ctx.GetStub()
	instance, _ := cc.GetInstance(ctx, instanceID)

	collectiveMsgName := "Message_0ip1epl"
	collectiveMsg, _ := cc.ReadCollectiveMsg(ctx, instance, collectiveMsgName)
	participant_id := collectiveMsg.ReceiveParticipantID

	// MultiTask Address Located
	choreographyTaskID := collectiveMsg.ChoreographyTaskID

	choreographyTask, _ := cc.ReadChoreographyTask(ctx, instance, choreographyTaskID)
	if choreographyTask.IsMulti == true {
		if targetTaskID == 0 {
			collectiveMsgName = "Message_0ip1epl"
		} else {
			collectiveMsgName = fmt.Sprintf("Message_0ip1epl_%d", targetTaskID)
		}
	}

	collectiveMsg, _ = cc.ReadCollectiveMsg(ctx, instance, collectiveMsgName)
	sendParticipantID := collectiveMsg.SendParticipantID
	receiveParticipantID := collectiveMsg.ReceiveParticipantID
	sendParticipant, _ := cc.ReadCollectiveParticipant(ctx, instance, sendParticipantID)
	receiveParticipant, _ := cc.ReadCollectiveParticipant(ctx, instance, receiveParticipantID)

	var errorMessage string
	var key1, key2 string
	var msgsToHandle []Message = make([]Message, 0)
	var eventsToTrigger []string = make([]string, 0)
	var event map[string]interface{}
	var eventJsonString string
	var eventJsonBytes []byte
	if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == false {
		// 一对一
		key1 = "nonMulti"
		key2 = "nonMulti"
		msgsToHandle = append(msgsToHandle, collectiveMsg.Messages[key1][key2])

		event = map[string]interface{}{
			"type": "Confirm_Message_0ip1epl",
		}

		eventJsonBytes, _ = json.Marshal(event)

		eventJsonString = string(eventJsonBytes)
		eventsToTrigger = append(eventsToTrigger, eventJsonString)

		participant_key := key2
		if cc.check_participant(ctx, instance, participant_id, participant_key) == false {
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
		if cc.check_participant(ctx, instance, participant_id, participant_key) == false {
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

		event = map[string]interface{}{
			"type": fmt.Sprintf("Confirm_Message_0ip1epl_%s", confirmTargetSender.ParticipantID),
		}

		eventJsonBytes, _ = json.Marshal(event)

		eventJsonString = string(eventJsonBytes)

		eventsToTrigger = append(eventsToTrigger, eventJsonString)
	} else if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == true {
		// 一对多 回应，响应自己的部分，修改计数器
		key1 = "nonMulti"
		key2 = cc.get_X509_identity(ctx)

		if receiveParticipant.IsLocked == true {
			// check if key2 in it
			if _, ok := receiveParticipant.Participants[key2]; ok {
				// check Participant
				participant_key := key2
				if cc.check_participant(ctx, instance, participant_id, participant_key) == false {
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

			if cc.check_participant(ctx, instance, participant_id, "") != true {
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

		event = map[string]interface{}{
			"type": fmt.Sprintf("Confirm_Message_0ip1epl_%d", message_increasing_key),
		}

		eventJsonBytes, _ = json.Marshal(event)

		eventJsonString = string(eventJsonBytes)

		eventsToTrigger = append(eventsToTrigger, eventJsonString)

	} else if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == true {
		// 多对多 UnSupported Operations?
		errorMessage = fmt.Sprintf("UnSupported Operation")
		return fmt.Errorf(errorMessage)
	}

	for _, event := range eventsToTrigger {

		fmt.Println("Event")
		fmt.Println(event)

		res, err := cc.Invoke_Other_chaincode(ctx, "StateChartEngine:v1", "default",
			stateCharts.EncodeExecuteStateMachineArgs(instance.StateMachineDescription, instance.AdditionalContent, instance.CurrentState, event))
		if err != nil {
			return err
		}
		state, changed := stateCharts.DecodeTriggerActionResult(res)

		fmt.Println("State")
		fmt.Println(state)

		fmt.Println("Changed")
		fmt.Println(changed)

		if !changed {
			return fmt.Errorf("The state machine does not change")
		}

		instance.CurrentState = state
	}

	stub.SetEvent(collectiveMsgName, []byte("Message is Confirmed !"))
	cc.SetInstance(ctx, instance)
	return nil
}

func (cc *SmartContract) Message_0ip1epl_Advance(
	ctx contractapi.TransactionContextInterface,
	instanceID string,
	targetTaskID string,
) error {
	stub := ctx.GetStub()
	instance, _ := cc.GetInstance(ctx, instanceID)

	collectiveMsgName := "Message_0ip1epl"
	collectiveMsg, _ := cc.ReadCollectiveMsg(ctx, instance, collectiveMsgName)

	// MultiTask Address Located
	choreographyTaskID := collectiveMsg.ChoreographyTaskID

	choreographyTask, _ := cc.ReadChoreographyTask(ctx, instance, choreographyTaskID)
	if choreographyTask.IsMulti == true {
		collectiveMsgName = fmt.Sprintf("Message_0ip1epl_%d", targetTaskID)
	}

	collectiveMsg, _ = cc.ReadCollectiveMsg(ctx, instance, collectiveMsgName)

	sendParticipantID := collectiveMsg.SendParticipantID
	receiveParticipantID := collectiveMsg.ReceiveParticipantID
	sendParticipant, _ := cc.ReadCollectiveParticipant(ctx, instance, sendParticipantID)
	receiveParticipant, _ := cc.ReadCollectiveParticipant(ctx, instance, receiveParticipantID)

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
		if cc.check_participant(ctx, instance, receiveParticipantID, "") == false {
			return fmt.Errorf("Not Allowed To Advance")
		}
		participantToLock = receiveParticipant
	} else {
		// check if invoker in senderParticipants
		if cc.check_participant(ctx, instance, sendParticipantID, "") == false {
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

	event := map[string]interface{}{
		"type": "advance_Message_0ip1epl",
	}
	eventJsonBytes, _ := json.Marshal(event)

	eventJsonString := string(eventJsonBytes)

	fmt.Println("Event")
	fmt.Println(eventJsonString)
	res, err := cc.Invoke_Other_chaincode(ctx, "StateChartEngine:v1", "default",
		stateCharts.EncodeExecuteStateMachineArgs(instance.StateMachineDescription, instance.AdditionalContent, instance.CurrentState, eventJsonString))
	if err != nil {
		return fmt.Errorf("failed to trigger stateCharts action: %v", err)
	}
	state, changed := stateCharts.DecodeTriggerActionResult(res)

	fmt.Println("State")
	fmt.Println(state)
	fmt.Println("Changed")
	fmt.Println(changed)

	if !changed {
		return fmt.Errorf("Invalid Operation")
	}
	instance.CurrentState = state

	participantToLock.IsLocked = true

	err = cc.SetInstance(ctx, instance)
	if err != nil {
		return fmt.Errorf("failed to set instance: %v", err)
	}

	stub.SetEvent("AdvanceMessage_0ip1epl", []byte("CollectiveMessage advanced successfully"))
	return nil
}

func (cc *SmartContract) Event_1rmj9g7(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)

	event := map[string]interface{}{
		"type": "Event_1rmj9g7",
	}

	eventJsonBytes, _ := json.Marshal(event)

	eventJsonString := string(eventJsonBytes)

	res, err := cc.Invoke_Other_chaincode(ctx, "stateCharts", "default",
		stateCharts.EncodeExecuteStateMachineArgs(instance.StateMachineDescription, instance.AdditionalContent, instance.CurrentState, eventJsonString))

	if err != nil {
		return err
	}

	state, changed := stateCharts.DecodeTriggerActionResult(res)

	fmt.Println("State")
	fmt.Println(state)

	fmt.Println("Changed")
	fmt.Println(changed)

	if !changed {
		return errors.New("Invalid transition")
	}

	instance.CurrentState = state

	cc.SetInstance(ctx, instance)

	stub.SetEvent("Event_1rmj9g7", []byte("Contract has been started successfully"))

	return nil
}
