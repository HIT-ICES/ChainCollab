package chaincode

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"reflect"
	"strconv"
	"strings"

	"github.com/hyperledger/fabric-chaincode-go/shim"
	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)


type InitParameters struct {
	Participant_0oa2za9           Participant       `json:"Participant_0oa2za9"`
	Participant_0jwk4tk           Participant       `json:"Participant_0jwk4tk"`
	Participant_0cb2p7d           Participant       `json:"Participant_0cb2p7d"`
	Activity_12arovy_DecisionID   string            `json:"Activity_12arovy_DecisionID"`
	Activity_12arovy_ParamMapping map[string]string `json:"Activity_12arovy_ParamMapping"`
	Activity_12arovy_Content      string            `json:"Activity_12arovy_Content"`
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



type Membership struct {
	MSP           string
	Attributes    map[string]string
	enable        bool
}

type Participant struct {
	ParticipantID string            `json:"ParticipantID"`
	MSPList       *Membership       `json:"MSPList"`
	IsMulti       bool              `json:"IsMulti"`
	MultiMaximum  int               `json:"MultiMaximum"`
	MultiMinimum  int               `json:"MultiMinimum"`
	locked        bool
	X509          string            `json:"X509"`
}

type Message struct {
	MessageID            string       `json:"MessageID"`
	MsgState             ElementState `json:"MsgState"`  //disable/enable/completed
	MiniMsgList          *string      //存minimsgInstanceID 也可以map:minimsginstanceID-->minimsgstate
	SendParticipantID    string
	ReceiveParticipantID string   
}

type MiniMessage struct {
	MessageInstanceID    string 
	FireflyTranID        string       `json:"FireflyTranID"`
	MiniMsgState         ElementState `json:"MsgState"`  //enable/wtf/completed
	Format               string       `json:"Format"`
	SendMSP              string       //这个消息指定的发送方
	receiveMSP           string       //这个消息指定的接收方
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


func (cc *SmartContract) Create_mini_message(ctx contractapi.TransactionContextInterface, instanceID string, bigMessageID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)

	msg, err := cc.ReadMsg(ctx, instanceID, "bigMessageID")


	//这一块可以封装为readLocked函数
	sendParticipant, err := cc.ReadParticipant(ctx, instanceID, msg.SendParticipantID)
	receiveParticipant, err := cc.ReadParticipant(ctx, instanceID, msg.receiveParticipantID)
	if sendParticipant.locked==false{
		//遍历msp
	}else{
		//遍历enable的msp
	}
	if receiveParticipant.locked==false{
		//TODO:遍历msp
	}else{
		//遍历enable的msp
	}


	//动态生成消息
	cc.createmini()

	cc.SetInstance(ctx, instance)
	return nil
}


func (cc *SmartContract) readminiMsg(ctx contractapi.TransactionContextInterface, instanceID string, target_participant string) bool {
	return true
}
func (cc *SmartContract) readMsg(ctx contractapi.TransactionContextInterface, instanceID string, target_participant string) bool {
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
	}

	// Update the currentInstanceID

	cc.CreateParticipant(ctx, &instance, "Participant_0oa2za9", initParameters.Participant_0oa2za9.MSP, initParameters.Participant_0oa2za9.Attributes, initParameters.Participant_0oa2za9.X509, initParameters.Participant_0oa2za9.IsMulti, 0, 0)
	cc.CreateParticipant(ctx, &instance, "Participant_0jwk4tk", initParameters.Participant_0jwk4tk.MSP, initParameters.Participant_0jwk4tk.Attributes, initParameters.Participant_0jwk4tk.X509, initParameters.Participant_0jwk4tk.IsMulti, 0, 0)
	cc.CreateParticipant(ctx, &instance, "Participant_0cb2p7d", initParameters.Participant_0cb2p7d.MSP, initParameters.Participant_0cb2p7d.Attributes, initParameters.Participant_0cb2p7d.X509, initParameters.Participant_0cb2p7d.IsMulti, 0, 0)
	cc.CreateActionEvent(ctx, &instance, "Event_0ehnwwz", ENABLED)

	cc.CreateActionEvent(ctx, &instance, "Event_0e3j88g", DISABLED)

	cc.CreateActionEvent(ctx, &instance, "Event_1o9guxu", DISABLED)

	cc.CreateActionEvent(ctx, &instance, "Event_194zr5n", DISABLED)


	//创建大消息
    cc.CreateMessage(Message_01k4b43)


	//默认创建max个mini消息
	/*
	while(i<max){
		cc.CreateMiniMessage(ctx, &instance, "Message_01k4b43_{instanceID}",发送方i,接收方i)
	}
	*/



	cc.CreateMessage(ctx, &instance, "Message_1f0gefc", "Participant_0oa2za9", "Participant_0jwk4tk", "", DISABLED, `{"properties":{"MessageContent":{"type":"string","description":""},"priceOK":{"type":"boolean","description":""}},"required":["MessageContent","priceOK"],"files":{},"file required":[]}`)
	cc.CreateGateway(ctx, &instance, "Gateway_1ltys0e", DISABLED)

	cc.CreateGateway(ctx, &instance, "Gateway_025uwvp", DISABLED)

	cc.CreateGateway(ctx, &instance, "Gateway_13i0b7w", DISABLED)

	cc.CreateBusinessRule(ctx, &instance, "Activity_12arovy", initParameters.Activity_12arovy_Content, initParameters.Activity_12arovy_DecisionID, initParameters.Activity_12arovy_ParamMapping)

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
		"InstanceID":       instanceID,
		"Activity_12arovy": initParameters.Activity_12arovy_Content,
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

//TODO:需要实现的函数
/*
ChangeMiniMsgState
check_MAX
check_MIN
LockParticipant
ChangeMsgState
ChangeSendParticipantMsgListState
ChangeReceiveParticipantMsgListState
*/

func (cc *SmartContract) Event_0ehnwwz(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)

	actionEvent, err := cc.ReadEvent(ctx, instanceID, "Event_0ehnwwz")
	if err != nil {
		return err
	}

	if actionEvent.EventState != ENABLED {
		errorMessage := fmt.Sprintf("Event state %s is not allowed", actionEvent.EventID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.ChangeEventState(ctx, instance, "Event_0ehnwwz", COMPLETED)
	stub.SetEvent("Event_0ehnwwz", []byte("Contract has been started successfully"))
	cc.SetInstance(ctx, instance)

	cc.ChangeMsgState(ctx, instance, "Message_aaaaa", ENABLED)
	//如果下一个元素是消息，则动态创建小消息
	cc.Create_mini_message(ctx, instance, "Message_aaaaa")

	cc.SetInstance(ctx, instance)
	return nil
}


func (cc *SmartContract) Message_aaaaa_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string, minimsginstanceID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)

	minimsg, err := cc.ReadminiMsg(ctx, instanceID, "Message_aaaaa", minimsginstanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_aaaaa")

	if err != nil {
		return err
	}

	
	//检查大消息状态
	if msg.MsgState != ENABLED {
		errorMessage := fmt.Sprintf("Message state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}
	//检查小消息状态
	if minimsg.miniMsgState != ENABLED {
		errorMessage := fmt.Sprintf("Message state %s is not allowed", minimsg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}



	//可以检查MAX也可以不检查，因为存在"发的时候可以超过max,但confirm的人少于max"的情况
	//论文中max的含义是最多有多少人发，所有在这里检查max
	//检查max
	if cc.check_MAX() == false {
		return

	}

	
	if cc.check_participant(ctx, instanceID, msg.SendParticipantID) == false {
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}


	cc.ChangeMsgFireflyTranID(ctx, instance, fireflyTranID, msg.MessageID)

	

	cc.ChangeMiniMsgState(ctx, instance, "Message_aaaaa", WAITINGFORCONFIRMATION,minimsginstanceID)


	stub.SetEvent("Message_1ajdm9l_{minimsginstanceID}", []byte("Message is waiting for confirmation"))


	cc.SetInstance(ctx, instance)

	return nil
}

func (cc *SmartContract) Message_aaaaa_Confirm(ctx contractapi.TransactionContextInterface, instanceID string, minimsginstanceID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)

	minimsg, err := cc.ReadMiniMsg(ctx, instanceID, "Message_aaaaa", minimsginstanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_aaaaa")

	if err != nil {
		return err
	}

	
	if cc.check_participant(ctx, instanceID, msg.ReceiveParticipantID) == false {
		errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	//先检查大消息
	if msg.MsgState != ENABLED{
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	//再检查小消息
	if minimsg.MsgState != WAITINGFORCONFIRMATION{
		errorMessage := fmt.Sprintf("Event state %s is not allowed", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}


	//分别将MSP接受方和发送方改为true
	sendParticipant, err := cc.ReadParticipant(ctx, instanceID, msg.SendParticipantID)
	receiveParticipant, err := cc.ReadParticipant(ctx, instanceID, msg.receiveParticipantID)
	if sendParticipant.locked==false{
		//修改mspList状态
	}
	if receiveParticipant.locked==false{
		//修改mspList状态
	}

	//完成单个小消息
	cc.ChangeMiniMsgState(ctx, instance, minimsg.minimsgInstanceID, COMPLETED)
	stub.SetEvent("Message_aaaaa_{InstanceID}", []byte("Message has been COMPLETED"))
	cc.SetInstance(ctx, instance)
	
	return nil
}

//第一次涉及到某Participant时调用
func (cc *SmartContract) Message_aaaaa_Advance(ctx contractapi.TransactionContextInterface, instanceID string) error {
	stub := ctx.GetStub()
	instance, err := cc.GetInstance(ctx, instanceID)
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_aaaaa")
	if err != nil {
		return err
	}

	//这里设想默认接收方和发送方都有权利推进
	if cc.check_participant(ctx, instanceID, {msg.ReceiveParticipantID, msg.sendParticipantID}) == false {
		errorMessage := fmt.Sprintf("Participant %s is not allowed to Advance", msg.SendParticipantID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	if check_MIN() == false {
		errorMessage := fmt.Sprintf("message %s is not available to advance", msg.MessageID)
		fmt.Println(errorMessage)
		return fmt.Errorf(errorMessage)
	}

	cc.LockParticipant()

	cc.ChangeMsgState(COMPLETED)

	stub.SetEvent()

	cc.SetInstance(ctx, instance)
}


//TODO：任务muti 可以参考使用 建模参数 

