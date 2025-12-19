package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
	"time"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

type SmartContract struct {
	contractapi.Contract
}

type ElementState int

const (
	DISABLED ElementState = iota
	ENABLED
	WAITINGFORCONFIRMATION
	COMPLETED
)

type StateMemory struct {
	DriverVerified  bool `json:"driverVerified"`
	VehicleVerified bool `json:"vehicleVerified"`
	PickedUp        bool `json:"pickedUp"`
	Delivered       bool `json:"delivered"`
	BorderOK        bool `json:"borderOK"`
}

type Participant struct {
	ParticipantID string            `json:"ParticipantID"`
	MSP           string            `json:"MSP"`
	Attributes    map[string]string `json:"Attributes"`
	IsMulti       bool              `json:"IsMulti"`
	MultiMaximum  int               `json:"MultiMaximum"`
	MultiMinimum  int               `json:"MultiMinimum"`
	X509          string            `json:"X509"`
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
	CID            string            `json:"Cid"`
	Hash           string            `json:"Hash"`
	DecisionID     string            `json:"DecisionID"`
	ParamMapping   map[string]string `json:"ParamMapping"`
	State          ElementState      `json:"State"`
}

type VCStatus struct {
	Verified               bool              `json:"verified"`
	Issuer                 string            `json:"issuer"`
	CredentialID           string            `json:"credentialId"`
	PresentationExchangeID string            `json:"presentationExchangeId"`
	EvidenceHash           string            `json:"evidenceHash"`
	Meta                   map[string]string `json:"meta"`
}

type VehicleVCStatus struct {
	Verified               bool              `json:"verified"`
	YearlyInspection       string            `json:"yearlyInspection"`
	InsuranceCoverage      string            `json:"insuranceCoverage"`
	HazmatVehiclePermit    bool              `json:"hazmatVehiclePermit"`
	Issuer                 string            `json:"issuer"`
	CredentialID           string            `json:"credentialId"`
	PresentationExchangeID string            `json:"presentationExchangeId"`
	EvidenceHash           string            `json:"evidenceHash"`
	Meta                   map[string]string `json:"meta"`
}

type ContractInstance struct {
	InstanceID            string                   `json:"InstanceID"`
	InstanceStateMemory   StateMemory              `json:"stateMemory"`
	InstanceMessages      map[string]*Message      `json:"InstanceMessages"`
	InstanceGateways      map[string]*Gateway      `json:"InstanceGateways"`
	InstanceActionEvents  map[string]*ActionEvent  `json:"InstanceActionEvents"`
	InstanceBusinessRules map[string]*BusinessRule `json:"InstanceBusinessRule"`
	InstanceParticipants  map[string]*Participant  `json:"InstanceParticipants"`
	DriverVC              VCStatus                 `json:"DriverVC"`
	VehicleVC             VehicleVCStatus          `json:"VehicleVC"`
}

type InitParameters struct {
	Participant_Shipper Participant `json:"Participant_Shipper"`
	Participant_Carrier Participant `json:"Participant_Carrier"`
	Participant_Border  Participant `json:"Participant_Border"`
}

func (cc *SmartContract) InitLedger(ctx contractapi.TransactionContextInterface) error {
	b, err := ctx.GetStub().GetState("isInited")
	if err != nil {
		return err
	}
	if b != nil {
		return fmt.Errorf("already initialized")
	}
	if err := ctx.GetStub().PutState("isInited", []byte("true")); err != nil {
		return err
	}
	ctx.GetStub().PutState("currentInstanceID", []byte("0"))
	ctx.GetStub().SetEvent("initContractEvent", []byte("initialized"))
	return nil
}

func (cc *SmartContract) hashXML(ctx contractapi.TransactionContextInterface, xmlString string) (string, error) {
	h := sha256.Sum256([]byte(xmlString))
	return hex.EncodeToString(h[:]), nil
}

func (cc *SmartContract) UpdateCID(ctx contractapi.TransactionContextInterface, instanceID string, BusinessRuleID string, cid string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	br, ok := inst.InstanceBusinessRules[BusinessRuleID]
	if !ok {
		return fmt.Errorf("not found")
	}
	br.CID = cid
	return cc.SetInstance(ctx, inst)
}

func (cc *SmartContract) CreateParticipant(ctx contractapi.TransactionContextInterface, instance *ContractInstance, participantID string, msp string, attributes map[string]string, x509 string, IsMulti bool, MultiMaximum int, MultiMinimum int) (*Participant, error) {
	instance.InstanceParticipants[participantID] = &Participant{ParticipantID: participantID, MSP: msp, Attributes: attributes, IsMulti: IsMulti, MultiMaximum: MultiMaximum, MultiMinimum: MultiMinimum, X509: x509}
	p := instance.InstanceParticipants[participantID]
	if p == nil {
		return nil, fmt.Errorf("create participant failed")
	}
	return p, nil
}

func (cc *SmartContract) CreateMessage(ctx contractapi.TransactionContextInterface, instance *ContractInstance, messageID string, sendParticipantID string, receiveParticipantID string, fireflyTranID string, msgState ElementState, format string) (*Message, error) {
	instance.InstanceMessages[messageID] = &Message{MessageID: messageID, SendParticipantID: sendParticipantID, ReceiveParticipantID: receiveParticipantID, FireflyTranID: fireflyTranID, MsgState: msgState, Format: format}
	m := instance.InstanceMessages[messageID]
	if m == nil {
		return nil, fmt.Errorf("create message failed")
	}
	return m, nil
}

func (cc *SmartContract) CreateGateway(ctx contractapi.TransactionContextInterface, instance *ContractInstance, gatewayID string, gatewayState ElementState) (*Gateway, error) {
	instance.InstanceGateways[gatewayID] = &Gateway{GatewayID: gatewayID, GatewayState: gatewayState}
	g := instance.InstanceGateways[gatewayID]
	if g == nil {
		return nil, fmt.Errorf("create gateway failed")
	}
	return g, nil
}

func (cc *SmartContract) CreateActionEvent(ctx contractapi.TransactionContextInterface, instance *ContractInstance, eventID string, eventState ElementState) (*ActionEvent, error) {
	instance.InstanceActionEvents[eventID] = &ActionEvent{EventID: eventID, EventState: eventState}
	e := instance.InstanceActionEvents[eventID]
	if e == nil {
		return nil, fmt.Errorf("create event failed")
	}
	return e, nil
}

func (cc *SmartContract) CreateBusinessRule(ctx contractapi.TransactionContextInterface, instance *ContractInstance, BusinessRuleID string, Content string, DecisionID string, ParamMapping map[string]string) (*BusinessRule, error) {
	h, err := cc.hashXML(ctx, Content)
	if err != nil {
		return nil, err
	}
	instance.InstanceBusinessRules[BusinessRuleID] = &BusinessRule{BusinessRuleID: BusinessRuleID, CID: "", Hash: h, DecisionID: DecisionID, ParamMapping: ParamMapping, State: DISABLED}
	b := instance.InstanceBusinessRules[BusinessRuleID]
	if b == nil {
		return nil, fmt.Errorf("create business rule failed")
	}
	return b, nil
}

func (cc *SmartContract) GetInstance(ctx contractapi.TransactionContextInterface, instanceID string) (*ContractInstance, error) {
	bs, err := ctx.GetStub().GetState(instanceID)
	if err != nil {
		return nil, err
	}
	if bs == nil {
		return nil, fmt.Errorf("instance not exist")
	}
	var inst ContractInstance
	if err := json.Unmarshal(bs, &inst); err != nil {
		return nil, err
	}
	return &inst, nil
}

func (cc *SmartContract) SetInstance(ctx contractapi.TransactionContextInterface, instance *ContractInstance) error {
	b, err := json.Marshal(instance)
	if err != nil {
		return err
	}
	return ctx.GetStub().PutState(instance.InstanceID, b)
}

func (cc *SmartContract) ReadMsg(ctx contractapi.TransactionContextInterface, instanceID string, messageID string) (*Message, error) {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return nil, err
	}
	m, ok := inst.InstanceMessages[messageID]
	if !ok {
		return nil, fmt.Errorf("message not exist")
	}
	return m, nil
}

func (cc *SmartContract) ReadGtw(ctx contractapi.TransactionContextInterface, instanceID string, gatewayID string) (*Gateway, error) {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return nil, err
	}
	g, ok := inst.InstanceGateways[gatewayID]
	if !ok {
		return nil, fmt.Errorf("gateway not exist")
	}
	return g, nil
}

func (cc *SmartContract) ReadEvent(ctx contractapi.TransactionContextInterface, instanceID string, eventID string) (*ActionEvent, error) {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return nil, err
	}
	e, ok := inst.InstanceActionEvents[eventID]
	if !ok {
		return nil, fmt.Errorf("event not exist")
	}
	return e, nil
}

func (cc *SmartContract) ChangeMsgState(ctx contractapi.TransactionContextInterface, instance *ContractInstance, messageID string, msgState ElementState) error {
	m, ok := instance.InstanceMessages[messageID]
	if !ok {
		return fmt.Errorf("message not exist")
	}
	m.MsgState = msgState
	return nil
}

func (cc *SmartContract) ChangeMsgFireflyTranID(ctx contractapi.TransactionContextInterface, instance *ContractInstance, fireflyTranID string, messageID string) error {
	m, ok := instance.InstanceMessages[messageID]
	if !ok {
		return fmt.Errorf("message not exist")
	}
	m.FireflyTranID = fireflyTranID
	return nil
}

func (cc *SmartContract) ChangeGtwState(ctx contractapi.TransactionContextInterface, instance *ContractInstance, gatewayID string, gtwState ElementState) error {
	g, ok := instance.InstanceGateways[gatewayID]
	if !ok {
		return fmt.Errorf("gateway not exist")
	}
	g.GatewayState = gtwState
	return nil
}

func (cc *SmartContract) ChangeEventState(ctx contractapi.TransactionContextInterface, instance *ContractInstance, eventID string, eventState ElementState) error {
	e, ok := instance.InstanceActionEvents[eventID]
	if !ok {
		return fmt.Errorf("event not exist")
	}
	e.EventState = eventState
	return nil
}

func (cc *SmartContract) ChangeBusinessRuleState(ctx contractapi.TransactionContextInterface, instance *ContractInstance, BusinessRuleID string, state ElementState) error {
	b, ok := instance.InstanceBusinessRules[BusinessRuleID]
	if !ok {
		return fmt.Errorf("business rule not exist")
	}
	b.State = state
	return nil
}

func (cc *SmartContract) GetAllMessages(ctx contractapi.TransactionContextInterface, instanceID string) ([]*Message, error) {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return nil, err
	}
	res := make([]*Message, 0, len(inst.InstanceMessages))
	for _, m := range inst.InstanceMessages {
		res = append(res, m)
	}
	return res, nil
}

func (cc *SmartContract) GetAllGateways(ctx contractapi.TransactionContextInterface, instanceID string) ([]*Gateway, error) {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return nil, err
	}
	res := make([]*Gateway, 0, len(inst.InstanceGateways))
	for _, g := range inst.InstanceGateways {
		res = append(res, g)
	}
	return res, nil
}

func (cc *SmartContract) GetAllActionEvents(ctx contractapi.TransactionContextInterface, instanceID string) ([]*ActionEvent, error) {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return nil, err
	}
	res := make([]*ActionEvent, 0, len(inst.InstanceActionEvents))
	for _, e := range inst.InstanceActionEvents {
		res = append(res, e)
	}
	return res, nil
}

func (cc *SmartContract) GetAllParticipants(ctx contractapi.TransactionContextInterface, instanceID string) ([]*Participant, error) {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return nil, err
	}
	res := make([]*Participant, 0, len(inst.InstanceParticipants))
	for _, p := range inst.InstanceParticipants {
		res = append(res, p)
	}
	return res, nil
}

func (cc *SmartContract) GetAllBusinessRules(ctx contractapi.TransactionContextInterface, instanceID string) ([]*BusinessRule, error) {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return nil, err
	}
	res := make([]*BusinessRule, 0, len(inst.InstanceBusinessRules))
	for _, b := range inst.InstanceBusinessRules {
		res = append(res, b)
	}
	return res, nil
}

func (cc *SmartContract) check_msp(ctx contractapi.TransactionContextInterface, instanceID string, target_participant string) bool {
	p, err := cc.ReadParticipant(ctx, instanceID, target_participant)
	if err != nil {
		return false
	}
	msp, err := ctx.GetClientIdentity().GetMSPID()
	if err != nil {
		return false
	}
	if p.MSP == "" {
		return true
	}
	return strings.EqualFold(p.MSP, msp)
}

func (cc *SmartContract) check_attribute(ctx contractapi.TransactionContextInterface, instanceID string, target_participant string, attributeName string) bool {
    p, err := cc.ReadParticipant(ctx, instanceID, target_participant)
    if err != nil {
        return false
    }
    if p.Attributes == nil || len(p.Attributes) == 0 {
        return true
    }
    val, found, err := ctx.GetClientIdentity().GetAttributeValue(attributeName)
    if err != nil {
        return false
    }
    if !found {
        return false
    }
    expected := p.Attributes[attributeName]
    if expected == "" {
        return val != ""
    }
    return strings.EqualFold(val, expected)
}

func (cc *SmartContract) check_participant(ctx contractapi.TransactionContextInterface, instanceID string, target_participant string) bool {
	if !cc.check_msp(ctx, instanceID, target_participant) {
		return false
	}
	p, err := cc.ReadParticipant(ctx, instanceID, target_participant)
	if err != nil {
		return false
	}
	for k := range p.Attributes {
		if !cc.check_attribute(ctx, instanceID, target_participant, k) {
			return false
		}
	}
	return true
}

func (cc *SmartContract) ReadBusinessRule(ctx contractapi.TransactionContextInterface, instanceID string, BusinessRuleID string) (*BusinessRule, error) {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return nil, err
	}
	b, ok := inst.InstanceBusinessRules[BusinessRuleID]
	if !ok {
		return nil, fmt.Errorf("business rule not exist")
	}
	return b, nil
}

func (cc *SmartContract) ReadParticipant(ctx contractapi.TransactionContextInterface, instanceID string, participantID string) (*Participant, error) {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return nil, err
	}
	p, ok := inst.InstanceParticipants[participantID]
	if !ok {
		return nil, fmt.Errorf("participant not exist")
	}
	return p, nil
}

func (cc *SmartContract) WriteParticipant(ctx contractapi.TransactionContextInterface, instanceID string, participantID string, participant *Participant) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	inst.InstanceParticipants[participantID] = participant
	return cc.SetInstance(ctx, inst)
}

func (cc *SmartContract) ReadGlobalVariable(ctx contractapi.TransactionContextInterface, instanceID string) (*StateMemory, error) {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return nil, err
	}
	return &inst.InstanceStateMemory, nil
}

func (cc *SmartContract) SetGlobalVariable(ctx contractapi.TransactionContextInterface, instance *ContractInstance, globalVariable *StateMemory) error {
	instance.InstanceStateMemory = *globalVariable
	return nil
}

func (cc *SmartContract) CreateInstance(ctx contractapi.TransactionContextInterface, initParametersBytes string) (string, error) {
	b, err := ctx.GetStub().GetState("isInited")
	if err != nil {
		return "", err
	}
	if b == nil {
		return "", fmt.Errorf("not initialized")
	}
	idBytes, err := ctx.GetStub().GetState("currentInstanceID")
	if err != nil {
		return "", err
	}
	instanceID := string(idBytes)
	var initParameters InitParameters
	if err := json.Unmarshal([]byte(initParametersBytes), &initParameters); err != nil {
		return "", err
	}
	inst := ContractInstance{InstanceID: instanceID, InstanceStateMemory: StateMemory{}, InstanceMessages: make(map[string]*Message), InstanceGateways: make(map[string]*Gateway), InstanceActionEvents: make(map[string]*ActionEvent), InstanceBusinessRules: make(map[string]*BusinessRule), InstanceParticipants: make(map[string]*Participant)}
	cc.CreateParticipant(ctx, &inst, "Participant_Shipper", initParameters.Participant_Shipper.MSP, initParameters.Participant_Shipper.Attributes, initParameters.Participant_Shipper.X509, initParameters.Participant_Shipper.IsMulti, 0, 0)
	cc.CreateParticipant(ctx, &inst, "Participant_Carrier", initParameters.Participant_Carrier.MSP, initParameters.Participant_Carrier.Attributes, initParameters.Participant_Carrier.X509, initParameters.Participant_Carrier.IsMulti, 0, 0)
	cc.CreateParticipant(ctx, &inst, "Participant_Border", initParameters.Participant_Border.MSP, initParameters.Participant_Border.Attributes, initParameters.Participant_Border.X509, initParameters.Participant_Border.IsMulti, 0, 0)
	cc.CreateParticipant(ctx, &inst, "Participant_Issuer", "", map[string]string{}, "", false, 0, 0)
	cc.CreateActionEvent(ctx, &inst, "StartEvent_Start", ENABLED)
	cc.CreateActionEvent(ctx, &inst, "EndEvent_Success", DISABLED)
	cc.CreateActionEvent(ctx, &inst, "EndEvent_Reject", DISABLED)
	cc.CreateMessage(ctx, &inst, "Message_VC_Publish_Driver", "Participant_Issuer", "Participant_Carrier", "", DISABLED, "{}")
	cc.CreateMessage(ctx, &inst, "Message_VerificationRequest_Driver", "Participant_Border", "Participant_Carrier", "", DISABLED, "{}")
	cc.CreateMessage(ctx, &inst, "Message_ProofSubmit_Driver", "Participant_Carrier", "Participant_Border", "", DISABLED, "{}")
	cc.CreateMessage(ctx, &inst, "Message_VC_Publish_Vehicle", "Participant_Issuer", "Participant_Carrier", "", DISABLED, "{}")
	cc.CreateMessage(ctx, &inst, "Message_VerificationRequest_Vehicle", "Participant_Border", "Participant_Carrier", "", DISABLED, "{}")
	cc.CreateMessage(ctx, &inst, "Message_ProofSubmit_Vehicle", "Participant_Carrier", "Participant_Border", "", DISABLED, "{}")
	cc.CreateMessage(ctx, &inst, "Message_Pickup", "Participant_Carrier", "Participant_Shipper", "", DISABLED, "{}")
	cc.CreateMessage(ctx, &inst, "Message_BorderCheck", "Participant_Border", "Participant_Carrier", "", DISABLED, "{}")
	cc.CreateMessage(ctx, &inst, "Message_DeliveryConfirm", "Participant_Shipper", "Participant_Carrier", "", DISABLED, "{}")
	cc.CreateGateway(ctx, &inst, "ExclusiveGateway_VCDecision", DISABLED)
	cc.CreateBusinessRule(ctx, &inst, "Activity_IssueDriverVC", "{}", "", map[string]string{})
	cc.CreateBusinessRule(ctx, &inst, "Activity_VerifierCreateDriverRequest", "{}", "", map[string]string{})
	cc.CreateBusinessRule(ctx, &inst, "Activity_HolderSubmitDriverProof", "{}", "", map[string]string{})
	cc.CreateBusinessRule(ctx, &inst, "Activity_VerifyDriverVC", "{}", "", map[string]string{})
	cc.CreateBusinessRule(ctx, &inst, "Activity_IssueVehicleVC", "{}", "", map[string]string{})
	cc.CreateBusinessRule(ctx, &inst, "Activity_VerifierCreateVehicleRequest", "{}", "", map[string]string{})
	cc.CreateBusinessRule(ctx, &inst, "Activity_HolderSubmitVehicleProof", "{}", "", map[string]string{})
	cc.CreateBusinessRule(ctx, &inst, "Activity_VerifyVehicleVC", "{}", "", map[string]string{})
	bs, err := json.Marshal(inst)
	if err != nil {
		return "", err
	}
	if err := ctx.GetStub().PutState(instanceID, bs); err != nil {
		return "", err
	}
	ctx.GetStub().SetEvent("InstanceCreated", []byte(instanceID))
	idInt, err := strconv.Atoi(instanceID)
	if err != nil {
		return "", err
	}
	idInt++
	instanceID = strconv.Itoa(idInt)
	if err := ctx.GetStub().PutState("currentInstanceID", []byte(instanceID)); err != nil {
		return "", err
	}
	return instanceID, nil
}

func (cc *SmartContract) StartEvent_Start(ctx contractapi.TransactionContextInterface, instanceID string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	ev, err := cc.ReadEvent(ctx, instanceID, "StartEvent_Start")
	if err != nil {
		return err
	}
	if ev.EventState != ENABLED {
		return fmt.Errorf("state not allowed")
	}
	cc.ChangeEventState(ctx, inst, "StartEvent_Start", COMPLETED)
	cc.ChangeBusinessRuleState(ctx, inst, "Activity_IssueDriverVC", ENABLED)
	cc.ChangeBusinessRuleState(ctx, inst, "Activity_IssueVehicleVC", ENABLED)
	cc.ChangeBusinessRuleState(ctx, inst, "Activity_VerifierCreateDriverRequest", ENABLED)
	cc.ChangeBusinessRuleState(ctx, inst, "Activity_VerifierCreateVehicleRequest", ENABLED)
	cc.SetInstance(ctx, inst)
	ctx.GetStub().SetEvent("StartEvent", []byte("started"))
	return nil
}

func (cc *SmartContract) Activity_VerifyDriverVC(ctx contractapi.TransactionContextInterface, instanceID string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	br, err := cc.ReadBusinessRule(ctx, instanceID, "Activity_VerifyDriverVC")
	if err != nil {
		return err
	}
	if br.State != ENABLED {
		return fmt.Errorf("state")
	}
	payload := map[string]string{"type": "driver", "instanceID": instanceID, "func": "Activity_VerifyDriverVC_Continue"}
	b, _ := json.Marshal(payload)
	ctx.GetStub().SetEvent("VCVerificationRequired", b)
	cc.ChangeBusinessRuleState(ctx, inst, "Activity_VerifyDriverVC", WAITINGFORCONFIRMATION)
	return cc.SetInstance(ctx, inst)
}

func (cc *SmartContract) Activity_IssueDriverVC(ctx contractapi.TransactionContextInterface, instanceID string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	br, err := cc.ReadBusinessRule(ctx, instanceID, "Activity_IssueDriverVC")
	if err != nil {
		return err
	}
	if br.State != ENABLED {
		return fmt.Errorf("state")
	}
	payload := map[string]string{"type": "driver", "instanceID": instanceID, "func": "Activity_IssueDriverVC_Continue"}
	b, _ := json.Marshal(payload)
	ctx.GetStub().SetEvent("VCIssuanceRequired", b)
	cc.ChangeBusinessRuleState(ctx, inst, "Activity_IssueDriverVC", WAITINGFORCONFIRMATION)
	return cc.SetInstance(ctx, inst)
}

func (cc *SmartContract) Activity_IssueDriverVC_Continue(ctx contractapi.TransactionContextInterface, instanceID string, issuanceJSON string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	br, err := cc.ReadBusinessRule(ctx, instanceID, "Activity_IssueDriverVC")
	if err != nil {
		return err
	}
	if br.State != WAITINGFORCONFIRMATION {
		return fmt.Errorf("state")
	}
	var v VCStatus
	if err := json.Unmarshal([]byte(issuanceJSON), &v); err != nil {
		return err
	}
	v.Verified = false
	inst.DriverVC = v
	cc.ChangeBusinessRuleState(ctx, inst, "Activity_IssueDriverVC", COMPLETED)
	cc.ChangeMsgState(ctx, inst, "Message_VC_Publish_Driver", ENABLED)
	return cc.SetInstance(ctx, inst)
}

func (cc *SmartContract) Activity_VerifyDriverVC_Continue(ctx contractapi.TransactionContextInterface, instanceID string, resultJSON string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	br, err := cc.ReadBusinessRule(ctx, instanceID, "Activity_VerifyDriverVC")
	if err != nil {
		return err
	}
	if br.State != WAITINGFORCONFIRMATION {
		return fmt.Errorf("state")
	}
	var v VCStatus
	if err := json.Unmarshal([]byte(resultJSON), &v); err != nil {
		return err
	}
	if inst.DriverVC.CredentialID != "" && v.CredentialID != "" && !strings.EqualFold(inst.DriverVC.CredentialID, v.CredentialID) {
		return fmt.Errorf("credential mismatch")
	}
	if v.CredentialID == "" {
		v.CredentialID = inst.DriverVC.CredentialID
	}
	if v.Issuer == "" {
		v.Issuer = inst.DriverVC.Issuer
	}
	if v.EvidenceHash == "" {
		v.EvidenceHash = inst.DriverVC.EvidenceHash
	}
	inst.DriverVC = v
	gm := inst.InstanceStateMemory
	gm.DriverVerified = v.Verified
	inst.InstanceStateMemory = gm
	cc.ChangeBusinessRuleState(ctx, inst, "Activity_VerifyDriverVC", COMPLETED)
	cc.ChangeGatewayForVCDecision(ctx, inst)
	return cc.SetInstance(ctx, inst)
}

func (cc *SmartContract) Activity_VerifyVehicleVC(ctx contractapi.TransactionContextInterface, instanceID string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	br, err := cc.ReadBusinessRule(ctx, instanceID, "Activity_VerifyVehicleVC")
	if err != nil {
		return err
	}
	if br.State != ENABLED {
		return fmt.Errorf("state")
	}
	payload := map[string]string{"type": "vehicle", "instanceID": instanceID, "func": "Activity_VerifyVehicleVC_Continue"}
	b, _ := json.Marshal(payload)
	ctx.GetStub().SetEvent("VCVerificationRequired", b)
	cc.ChangeBusinessRuleState(ctx, inst, "Activity_VerifyVehicleVC", WAITINGFORCONFIRMATION)
	return cc.SetInstance(ctx, inst)
}

func (cc *SmartContract) Activity_IssueVehicleVC(ctx contractapi.TransactionContextInterface, instanceID string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	br, err := cc.ReadBusinessRule(ctx, instanceID, "Activity_IssueVehicleVC")
	if err != nil {
		return err
	}
	if br.State != ENABLED {
		return fmt.Errorf("state")
	}
	payload := map[string]string{"type": "vehicle", "instanceID": instanceID, "func": "Activity_IssueVehicleVC_Continue"}
	b, _ := json.Marshal(payload)
	ctx.GetStub().SetEvent("VCIssuanceRequired", b)
	cc.ChangeBusinessRuleState(ctx, inst, "Activity_IssueVehicleVC", WAITINGFORCONFIRMATION)
	return cc.SetInstance(ctx, inst)
}

func (cc *SmartContract) Activity_IssueVehicleVC_Continue(ctx contractapi.TransactionContextInterface, instanceID string, issuanceJSON string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	br, err := cc.ReadBusinessRule(ctx, instanceID, "Activity_IssueVehicleVC")
	if err != nil {
		return err
	}
	if br.State != WAITINGFORCONFIRMATION {
		return fmt.Errorf("state")
	}
	var v VehicleVCStatus
	if err := json.Unmarshal([]byte(issuanceJSON), &v); err != nil {
		return err
	}
	v.Verified = false
	inst.VehicleVC = v
	cc.ChangeBusinessRuleState(ctx, inst, "Activity_IssueVehicleVC", COMPLETED)
	cc.ChangeMsgState(ctx, inst, "Message_VC_Publish_Vehicle", ENABLED)
	return cc.SetInstance(ctx, inst)
}

func (cc *SmartContract) Activity_VerifierCreateDriverRequest(ctx contractapi.TransactionContextInterface, instanceID string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	br, err := cc.ReadBusinessRule(ctx, instanceID, "Activity_VerifierCreateDriverRequest")
	if err != nil {
		return err
	}
	if br.State != ENABLED {
		return fmt.Errorf("state")
	}
	payload := map[string]string{"type": "driver", "role": "verifier", "instanceID": instanceID, "func": "Activity_VerifierCreateDriverRequest_Continue"}
	b, _ := json.Marshal(payload)
	ctx.GetStub().SetEvent("VCVerificationRequestRequired", b)
	cc.ChangeBusinessRuleState(ctx, inst, "Activity_VerifierCreateDriverRequest", WAITINGFORCONFIRMATION)
	return cc.SetInstance(ctx, inst)
}

func (cc *SmartContract) Activity_VerifierCreateDriverRequest_Continue(ctx contractapi.TransactionContextInterface, instanceID string, requestJSON string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	br, err := cc.ReadBusinessRule(ctx, instanceID, "Activity_VerifierCreateDriverRequest")
	if err != nil {
		return err
	}
	if br.State != WAITINGFORCONFIRMATION {
		return fmt.Errorf("state")
	}
	if inst.DriverVC.Meta == nil {
		inst.DriverVC.Meta = map[string]string{}
	}
	inst.DriverVC.Meta["verificationRequest"] = requestJSON
	cc.ChangeBusinessRuleState(ctx, inst, "Activity_VerifierCreateDriverRequest", COMPLETED)
	cc.ChangeMsgState(ctx, inst, "Message_VerificationRequest_Driver", ENABLED)
	return cc.SetInstance(ctx, inst)
}

func (cc *SmartContract) Activity_HolderSubmitDriverProof(ctx contractapi.TransactionContextInterface, instanceID string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	br, err := cc.ReadBusinessRule(ctx, instanceID, "Activity_HolderSubmitDriverProof")
	if err != nil {
		return err
	}
	if br.State != ENABLED {
		return fmt.Errorf("state")
	}
	payload := map[string]string{"type": "driver", "role": "holder", "instanceID": instanceID, "func": "Activity_HolderSubmitDriverProof_Continue"}
	b, _ := json.Marshal(payload)
	ctx.GetStub().SetEvent("VCProofSubmissionRequired", b)
	cc.ChangeBusinessRuleState(ctx, inst, "Activity_HolderSubmitDriverProof", WAITINGFORCONFIRMATION)
	return cc.SetInstance(ctx, inst)
}

func (cc *SmartContract) Activity_HolderSubmitDriverProof_Continue(ctx contractapi.TransactionContextInterface, instanceID string, proofJSON string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	br, err := cc.ReadBusinessRule(ctx, instanceID, "Activity_HolderSubmitDriverProof")
	if err != nil {
		return err
	}
	if br.State != WAITINGFORCONFIRMATION {
		return fmt.Errorf("state")
	}
	if inst.DriverVC.Meta == nil {
		inst.DriverVC.Meta = map[string]string{}
	}
	inst.DriverVC.Meta["submittedProof"] = proofJSON
	cc.ChangeBusinessRuleState(ctx, inst, "Activity_HolderSubmitDriverProof", COMPLETED)
	cc.ChangeMsgState(ctx, inst, "Message_ProofSubmit_Driver", ENABLED)
	return cc.SetInstance(ctx, inst)
}

func (cc *SmartContract) Activity_VerifierCreateVehicleRequest(ctx contractapi.TransactionContextInterface, instanceID string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	br, err := cc.ReadBusinessRule(ctx, instanceID, "Activity_VerifierCreateVehicleRequest")
	if err != nil {
		return err
	}
	if br.State != ENABLED {
		return fmt.Errorf("state")
	}
	payload := map[string]string{"type": "vehicle", "role": "verifier", "instanceID": instanceID, "func": "Activity_VerifierCreateVehicleRequest_Continue"}
	b, _ := json.Marshal(payload)
	ctx.GetStub().SetEvent("VCVerificationRequestRequired", b)
	cc.ChangeBusinessRuleState(ctx, inst, "Activity_VerifierCreateVehicleRequest", WAITINGFORCONFIRMATION)
	return cc.SetInstance(ctx, inst)
}

func (cc *SmartContract) Activity_VerifierCreateVehicleRequest_Continue(ctx contractapi.TransactionContextInterface, instanceID string, requestJSON string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	br, err := cc.ReadBusinessRule(ctx, instanceID, "Activity_VerifierCreateVehicleRequest")
	if err != nil {
		return err
	}
	if br.State != WAITINGFORCONFIRMATION {
		return fmt.Errorf("state")
	}
	if inst.VehicleVC.Meta == nil {
		inst.VehicleVC.Meta = map[string]string{}
	}
	inst.VehicleVC.Meta["verificationRequest"] = requestJSON
	cc.ChangeBusinessRuleState(ctx, inst, "Activity_VerifierCreateVehicleRequest", COMPLETED)
	cc.ChangeMsgState(ctx, inst, "Message_VerificationRequest_Vehicle", ENABLED)
	return cc.SetInstance(ctx, inst)
}

func (cc *SmartContract) Activity_HolderSubmitVehicleProof(ctx contractapi.TransactionContextInterface, instanceID string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	br, err := cc.ReadBusinessRule(ctx, instanceID, "Activity_HolderSubmitVehicleProof")
	if err != nil {
		return err
	}
	if br.State != ENABLED {
		return fmt.Errorf("state")
	}
	payload := map[string]string{"type": "vehicle", "role": "holder", "instanceID": instanceID, "func": "Activity_HolderSubmitVehicleProof_Continue"}
	b, _ := json.Marshal(payload)
	ctx.GetStub().SetEvent("VCProofSubmissionRequired", b)
	cc.ChangeBusinessRuleState(ctx, inst, "Activity_HolderSubmitVehicleProof", WAITINGFORCONFIRMATION)
	return cc.SetInstance(ctx, inst)
}

func (cc *SmartContract) Activity_HolderSubmitVehicleProof_Continue(ctx contractapi.TransactionContextInterface, instanceID string, proofJSON string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	br, err := cc.ReadBusinessRule(ctx, instanceID, "Activity_HolderSubmitVehicleProof")
	if err != nil {
		return err
	}
	if br.State != WAITINGFORCONFIRMATION {
		return fmt.Errorf("state")
	}
	if inst.VehicleVC.Meta == nil {
		inst.VehicleVC.Meta = map[string]string{}
	}
	inst.VehicleVC.Meta["submittedProof"] = proofJSON
	cc.ChangeBusinessRuleState(ctx, inst, "Activity_HolderSubmitVehicleProof", COMPLETED)
	cc.ChangeMsgState(ctx, inst, "Message_ProofSubmit_Vehicle", ENABLED)
	return cc.SetInstance(ctx, inst)
}

func (cc *SmartContract) Message_VC_Publish_Driver_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_VC_Publish_Driver")
	if err != nil {
		return err
	}
	if !cc.check_participant(ctx, instanceID, msg.SendParticipantID) {
		return fmt.Errorf("not allowed")
	}
	if msg.MsgState != ENABLED {
		return fmt.Errorf("state")
	}
	cc.ChangeMsgFireflyTranID(ctx, inst, fireflyTranID, msg.MessageID)
	cc.ChangeMsgState(ctx, inst, "Message_VC_Publish_Driver", WAITINGFORCONFIRMATION)
	cc.SetInstance(ctx, inst)
	ctx.GetStub().SetEvent("Message_VC_Publish_Driver", []byte(instanceID))
	return nil
}

func (cc *SmartContract) Message_VC_Publish_Driver_Complete(ctx contractapi.TransactionContextInterface, instanceID string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_VC_Publish_Driver")
	if err != nil {
		return err
	}
	if !cc.check_participant(ctx, instanceID, msg.ReceiveParticipantID) {
		return fmt.Errorf("not allowed")
	}
	if msg.MsgState != WAITINGFORCONFIRMATION {
		return fmt.Errorf("state")
	}
	cc.ChangeMsgState(ctx, inst, "Message_VC_Publish_Driver", COMPLETED)
	cc.SetInstance(ctx, inst)
	ctx.GetStub().SetEvent("Message_VC_Publish_Driver_Complete", []byte(instanceID))
	return nil
}

func (cc *SmartContract) Message_VerificationRequest_Driver_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_VerificationRequest_Driver")
	if err != nil {
		return err
	}
	if !cc.check_participant(ctx, instanceID, msg.SendParticipantID) {
		return fmt.Errorf("not allowed")
	}
	if msg.MsgState != ENABLED {
		return fmt.Errorf("state")
	}
	cc.ChangeMsgFireflyTranID(ctx, inst, fireflyTranID, msg.MessageID)
	cc.ChangeMsgState(ctx, inst, "Message_VerificationRequest_Driver", WAITINGFORCONFIRMATION)
	cc.SetInstance(ctx, inst)
	ctx.GetStub().SetEvent("Message_VerificationRequest_Driver", []byte(instanceID))
	return nil
}

func (cc *SmartContract) Message_VerificationRequest_Driver_Complete(ctx contractapi.TransactionContextInterface, instanceID string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_VerificationRequest_Driver")
	if err != nil {
		return err
	}
	if !cc.check_participant(ctx, instanceID, msg.ReceiveParticipantID) {
		return fmt.Errorf("not allowed")
	}
	if msg.MsgState != WAITINGFORCONFIRMATION {
		return fmt.Errorf("state")
	}
	cc.ChangeMsgState(ctx, inst, "Message_VerificationRequest_Driver", COMPLETED)
	cc.ChangeBusinessRuleState(ctx, inst, "Activity_HolderSubmitDriverProof", ENABLED)
	cc.SetInstance(ctx, inst)
	ctx.GetStub().SetEvent("Message_VerificationRequest_Driver_Complete", []byte(instanceID))
	return nil
}

func (cc *SmartContract) Message_ProofSubmit_Driver_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_ProofSubmit_Driver")
	if err != nil {
		return err
	}
	if !cc.check_participant(ctx, instanceID, msg.SendParticipantID) {
		return fmt.Errorf("not allowed")
	}
	if msg.MsgState != ENABLED {
		return fmt.Errorf("state")
	}
	cc.ChangeMsgFireflyTranID(ctx, inst, fireflyTranID, msg.MessageID)
	cc.ChangeMsgState(ctx, inst, "Message_ProofSubmit_Driver", WAITINGFORCONFIRMATION)
	cc.SetInstance(ctx, inst)
	ctx.GetStub().SetEvent("Message_ProofSubmit_Driver", []byte(instanceID))
	return nil
}

func (cc *SmartContract) Message_ProofSubmit_Driver_Complete(ctx contractapi.TransactionContextInterface, instanceID string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_ProofSubmit_Driver")
	if err != nil {
		return err
	}
	if !cc.check_participant(ctx, instanceID, msg.ReceiveParticipantID) {
		return fmt.Errorf("not allowed")
	}
	if msg.MsgState != WAITINGFORCONFIRMATION {
		return fmt.Errorf("state")
	}
	cc.ChangeMsgState(ctx, inst, "Message_ProofSubmit_Driver", COMPLETED)
	cc.ChangeBusinessRuleState(ctx, inst, "Activity_VerifyDriverVC", ENABLED)
	cc.SetInstance(ctx, inst)
	ctx.GetStub().SetEvent("Message_ProofSubmit_Driver_Complete", []byte(instanceID))
	return nil
}

func (cc *SmartContract) Message_VC_Publish_Vehicle_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_VC_Publish_Vehicle")
	if err != nil {
		return err
	}
	if !cc.check_participant(ctx, instanceID, msg.SendParticipantID) {
		return fmt.Errorf("not allowed")
	}
	if msg.MsgState != ENABLED {
		return fmt.Errorf("state")
	}
	cc.ChangeMsgFireflyTranID(ctx, inst, fireflyTranID, msg.MessageID)
	cc.ChangeMsgState(ctx, inst, "Message_VC_Publish_Vehicle", WAITINGFORCONFIRMATION)
	cc.SetInstance(ctx, inst)
	ctx.GetStub().SetEvent("Message_VC_Publish_Vehicle", []byte(instanceID))
	return nil
}

func (cc *SmartContract) Message_VC_Publish_Vehicle_Complete(ctx contractapi.TransactionContextInterface, instanceID string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_VC_Publish_Vehicle")
	if err != nil {
		return err
	}
	if !cc.check_participant(ctx, instanceID, msg.ReceiveParticipantID) {
		return fmt.Errorf("not allowed")
	}
	if msg.MsgState != WAITINGFORCONFIRMATION {
		return fmt.Errorf("state")
	}
	cc.ChangeMsgState(ctx, inst, "Message_VC_Publish_Vehicle", COMPLETED)
	cc.SetInstance(ctx, inst)
	ctx.GetStub().SetEvent("Message_VC_Publish_Vehicle_Complete", []byte(instanceID))
	return nil
}

func (cc *SmartContract) Message_VerificationRequest_Vehicle_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_VerificationRequest_Vehicle")
	if err != nil {
		return err
	}
	if !cc.check_participant(ctx, instanceID, msg.SendParticipantID) {
		return fmt.Errorf("not allowed")
	}
	if msg.MsgState != ENABLED {
		return fmt.Errorf("state")
	}
	cc.ChangeMsgFireflyTranID(ctx, inst, fireflyTranID, msg.MessageID)
	cc.ChangeMsgState(ctx, inst, "Message_VerificationRequest_Vehicle", WAITINGFORCONFIRMATION)
	cc.SetInstance(ctx, inst)
	ctx.GetStub().SetEvent("Message_VerificationRequest_Vehicle", []byte(instanceID))
	return nil
}

func (cc *SmartContract) Message_VerificationRequest_Vehicle_Complete(ctx contractapi.TransactionContextInterface, instanceID string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_VerificationRequest_Vehicle")
	if err != nil {
		return err
	}
	if !cc.check_participant(ctx, instanceID, msg.ReceiveParticipantID) {
		return fmt.Errorf("not allowed")
	}
	if msg.MsgState != WAITINGFORCONFIRMATION {
		return fmt.Errorf("state")
	}
	cc.ChangeMsgState(ctx, inst, "Message_VerificationRequest_Vehicle", COMPLETED)
	cc.ChangeBusinessRuleState(ctx, inst, "Activity_HolderSubmitVehicleProof", ENABLED)
	cc.SetInstance(ctx, inst)
	ctx.GetStub().SetEvent("Message_VerificationRequest_Vehicle_Complete", []byte(instanceID))
	return nil
}

func (cc *SmartContract) Message_ProofSubmit_Vehicle_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_ProofSubmit_Vehicle")
	if err != nil {
		return err
	}
	if !cc.check_participant(ctx, instanceID, msg.SendParticipantID) {
		return fmt.Errorf("not allowed")
	}
	if msg.MsgState != ENABLED {
		return fmt.Errorf("state")
	}
	cc.ChangeMsgFireflyTranID(ctx, inst, fireflyTranID, msg.MessageID)
	cc.ChangeMsgState(ctx, inst, "Message_ProofSubmit_Vehicle", WAITINGFORCONFIRMATION)
	cc.SetInstance(ctx, inst)
	ctx.GetStub().SetEvent("Message_ProofSubmit_Vehicle", []byte(instanceID))
	return nil
}

func (cc *SmartContract) Message_ProofSubmit_Vehicle_Complete(ctx contractapi.TransactionContextInterface, instanceID string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_ProofSubmit_Vehicle")
	if err != nil {
		return err
	}
	if !cc.check_participant(ctx, instanceID, msg.ReceiveParticipantID) {
		return fmt.Errorf("not allowed")
	}
	if msg.MsgState != WAITINGFORCONFIRMATION {
		return fmt.Errorf("state")
	}
	cc.ChangeMsgState(ctx, inst, "Message_ProofSubmit_Vehicle", COMPLETED)
	cc.ChangeBusinessRuleState(ctx, inst, "Activity_VerifyVehicleVC", ENABLED)
	cc.SetInstance(ctx, inst)
	ctx.GetStub().SetEvent("Message_ProofSubmit_Vehicle_Complete", []byte(instanceID))
	return nil
}

func (cc *SmartContract) Activity_VerifyVehicleVC_Continue(ctx contractapi.TransactionContextInterface, instanceID string, resultJSON string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	br, err := cc.ReadBusinessRule(ctx, instanceID, "Activity_VerifyVehicleVC")
	if err != nil {
		return err
	}
	if br.State != WAITINGFORCONFIRMATION {
		return fmt.Errorf("state")
	}
	var v VehicleVCStatus
	if err := json.Unmarshal([]byte(resultJSON), &v); err != nil {
		return err
	}
	if inst.VehicleVC.CredentialID != "" && v.CredentialID != "" && !strings.EqualFold(inst.VehicleVC.CredentialID, v.CredentialID) {
		return fmt.Errorf("credential mismatch")
	}
	if v.CredentialID == "" {
		v.CredentialID = inst.VehicleVC.CredentialID
	}
	if v.Issuer == "" {
		v.Issuer = inst.VehicleVC.Issuer
	}
	if v.EvidenceHash == "" {
		v.EvidenceHash = inst.VehicleVC.EvidenceHash
	}
	inst.VehicleVC = v
	gm := inst.InstanceStateMemory
	gm.VehicleVerified = v.Verified && strings.ToLower(v.YearlyInspection) == "valid" && strings.ToLower(v.InsuranceCoverage) == "active"
	inst.InstanceStateMemory = gm
	cc.ChangeBusinessRuleState(ctx, inst, "Activity_VerifyVehicleVC", COMPLETED)
	cc.ChangeGatewayForVCDecision(ctx, inst)
	return cc.SetInstance(ctx, inst)
}

func (cc *SmartContract) ChangeGatewayForVCDecision(ctx contractapi.TransactionContextInterface, instance *ContractInstance) {
	if instance.InstanceStateMemory.DriverVerified && instance.InstanceStateMemory.VehicleVerified {
		cc.ChangeGtwState(ctx, instance, "ExclusiveGateway_VCDecision", ENABLED)
	}
}

func (cc *SmartContract) ExclusiveGateway_VCDecision(ctx contractapi.TransactionContextInterface, instanceID string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	g, err := cc.ReadGtw(ctx, instanceID, "ExclusiveGateway_VCDecision")
	if err != nil {
		return err
	}
	if g.GatewayState != ENABLED {
		return fmt.Errorf("state")
	}
	cc.ChangeGtwState(ctx, inst, g.GatewayID, COMPLETED)
	if inst.InstanceStateMemory.DriverVerified && inst.InstanceStateMemory.VehicleVerified {
		cc.ChangeMsgState(ctx, inst, "Message_Pickup", ENABLED)
	} else {
		cc.ChangeEventState(ctx, inst, "EndEvent_Reject", ENABLED)
	}
	return cc.SetInstance(ctx, inst)
}

func (cc *SmartContract) Message_Pickup_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_Pickup")
	if err != nil {
		return err
	}
	if !cc.check_participant(ctx, instanceID, msg.SendParticipantID) {
		return fmt.Errorf("not allowed")
	}
	if msg.MsgState != ENABLED {
		return fmt.Errorf("state")
	}
	cc.ChangeMsgFireflyTranID(ctx, inst, fireflyTranID, msg.MessageID)
	cc.ChangeMsgState(ctx, inst, "Message_Pickup", WAITINGFORCONFIRMATION)
	cc.SetInstance(ctx, inst)
	ctx.GetStub().SetEvent("Message_Pickup", []byte(instanceID))
	return nil
}

func (cc *SmartContract) Message_Pickup_Complete(ctx contractapi.TransactionContextInterface, instanceID string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_Pickup")
	if err != nil {
		return err
	}
	if !cc.check_participant(ctx, instanceID, msg.ReceiveParticipantID) {
		return fmt.Errorf("not allowed")
	}
	if msg.MsgState != WAITINGFORCONFIRMATION {
		return fmt.Errorf("state")
	}
	cc.ChangeMsgState(ctx, inst, "Message_Pickup", COMPLETED)
	gm := inst.InstanceStateMemory
	gm.PickedUp = true
	inst.InstanceStateMemory = gm
	cc.ChangeMsgState(ctx, inst, "Message_BorderCheck", ENABLED)
	cc.SetInstance(ctx, inst)
	ctx.GetStub().SetEvent("Message_Pickup_Complete", []byte(instanceID))
	return nil
}

func (cc *SmartContract) Message_BorderCheck_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string, result string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_BorderCheck")
	if err != nil {
		return err
	}
	if !cc.check_participant(ctx, instanceID, msg.SendParticipantID) {
		return fmt.Errorf("not allowed")
	}
	if msg.MsgState != ENABLED {
		return fmt.Errorf("state")
	}
	cc.ChangeMsgFireflyTranID(ctx, inst, fireflyTranID, msg.MessageID)
	cc.ChangeMsgState(ctx, inst, "Message_BorderCheck", WAITINGFORCONFIRMATION)
	gm := inst.InstanceStateMemory
	gm.BorderOK = strings.ToLower(result) == "ok"
	inst.InstanceStateMemory = gm
	cc.SetInstance(ctx, inst)
	ctx.GetStub().SetEvent("Message_BorderCheck", []byte(instanceID))
	return nil
}

func (cc *SmartContract) Message_BorderCheck_Complete(ctx contractapi.TransactionContextInterface, instanceID string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_BorderCheck")
	if err != nil {
		return err
	}
	if !cc.check_participant(ctx, instanceID, msg.ReceiveParticipantID) {
		return fmt.Errorf("not allowed")
	}
	if msg.MsgState != WAITINGFORCONFIRMATION {
		return fmt.Errorf("state")
	}
	cc.ChangeMsgState(ctx, inst, "Message_BorderCheck", COMPLETED)
	if inst.InstanceStateMemory.BorderOK {
		cc.ChangeMsgState(ctx, inst, "Message_DeliveryConfirm", ENABLED)
	} else {
		cc.ChangeEventState(ctx, inst, "EndEvent_Reject", ENABLED)
	}
	cc.SetInstance(ctx, inst)
	ctx.GetStub().SetEvent("Message_BorderCheck_Complete", []byte(instanceID))
	return nil
}

func (cc *SmartContract) Message_DeliveryConfirm_Send(ctx contractapi.TransactionContextInterface, instanceID string, fireflyTranID string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_DeliveryConfirm")
	if err != nil {
		return err
	}
	if !cc.check_participant(ctx, instanceID, msg.SendParticipantID) {
		return fmt.Errorf("not allowed")
	}
	if msg.MsgState != ENABLED {
		return fmt.Errorf("state")
	}
	cc.ChangeMsgFireflyTranID(ctx, inst, fireflyTranID, msg.MessageID)
	cc.ChangeMsgState(ctx, inst, "Message_DeliveryConfirm", WAITINGFORCONFIRMATION)
	cc.SetInstance(ctx, inst)
	ctx.GetStub().SetEvent("Message_DeliveryConfirm", []byte(instanceID))
	return nil
}

func (cc *SmartContract) Message_DeliveryConfirm_Complete(ctx contractapi.TransactionContextInterface, instanceID string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	msg, err := cc.ReadMsg(ctx, instanceID, "Message_DeliveryConfirm")
	if err != nil {
		return err
	}
	if !cc.check_participant(ctx, instanceID, msg.ReceiveParticipantID) {
		return fmt.Errorf("not allowed")
	}
	if msg.MsgState != WAITINGFORCONFIRMATION {
		return fmt.Errorf("state")
	}
	gm := inst.InstanceStateMemory
	if !gm.PickedUp {
		return fmt.Errorf("not picked up")
	}
	cc.ChangeMsgState(ctx, inst, "Message_DeliveryConfirm", COMPLETED)
	gm.Delivered = true
	inst.InstanceStateMemory = gm
	cc.ChangeEventState(ctx, inst, "EndEvent_Success", ENABLED)
	cc.SetInstance(ctx, inst)
	ctx.GetStub().SetEvent("Message_DeliveryConfirm_Complete", []byte(instanceID))
	return nil
}

func (cc *SmartContract) EndEvent_Success(ctx contractapi.TransactionContextInterface, instanceID string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	e, err := cc.ReadEvent(ctx, instanceID, "EndEvent_Success")
	if err != nil {
		return err
	}
	if e.EventState != ENABLED {
		return fmt.Errorf("state")
	}
	cc.ChangeEventState(ctx, inst, "EndEvent_Success", COMPLETED)
	cc.SetInstance(ctx, inst)
	ctx.GetStub().SetEvent("EndEvent_Success", []byte(time.Now().Format(time.RFC3339)))
	return nil
}

func (cc *SmartContract) EndEvent_Reject(ctx contractapi.TransactionContextInterface, instanceID string) error {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return err
	}
	e, err := cc.ReadEvent(ctx, instanceID, "EndEvent_Reject")
	if err != nil {
		return err
	}
	if e.EventState != ENABLED {
		return fmt.Errorf("state")
	}
	cc.ChangeEventState(ctx, inst, "EndEvent_Reject", COMPLETED)
	cc.SetInstance(ctx, inst)
	ctx.GetStub().SetEvent("EndEvent_Reject", []byte(time.Now().Format(time.RFC3339)))
	return nil
}

type InstanceSummary struct {
	InstanceID    string                  `json:"instanceID"`
	Memory        StateMemory             `json:"memory"`
	Messages      map[string]ElementState `json:"messages"`
	Gateways      map[string]ElementState `json:"gateways"`
	ActionEvents  map[string]ElementState `json:"actionEvents"`
	BusinessRules map[string]ElementState `json:"businessRules"`
	DriverVC      VCStatus                `json:"driverVC"`
	VehicleVC     VehicleVCStatus         `json:"vehicleVC"`
}

func (cc *SmartContract) GetDriverVCStatus(ctx contractapi.TransactionContextInterface, instanceID string) (*VCStatus, error) {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return nil, err
	}
	return &inst.DriverVC, nil
}

func (cc *SmartContract) GetVehicleVCStatus(ctx contractapi.TransactionContextInterface, instanceID string) (*VehicleVCStatus, error) {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return nil, err
	}
	return &inst.VehicleVC, nil
}

func (cc *SmartContract) GetInstanceSummary(ctx contractapi.TransactionContextInterface, instanceID string) (*InstanceSummary, error) {
	inst, err := cc.GetInstance(ctx, instanceID)
	if err != nil {
		return nil, err
	}
	mStates := make(map[string]ElementState)
	for id, m := range inst.InstanceMessages {
		mStates[id] = m.MsgState
	}
	gStates := make(map[string]ElementState)
	for id, g := range inst.InstanceGateways {
		gStates[id] = g.GatewayState
	}
	eStates := make(map[string]ElementState)
	for id, e := range inst.InstanceActionEvents {
		eStates[id] = e.EventState
	}
	bStates := make(map[string]ElementState)
	for id, b := range inst.InstanceBusinessRules {
		bStates[id] = b.State
	}
	s := &InstanceSummary{InstanceID: inst.InstanceID, Memory: inst.InstanceStateMemory, Messages: mStates, Gateways: gStates, ActionEvents: eStates, BusinessRules: bStates, DriverVC: inst.DriverVC, VehicleVC: inst.VehicleVC}
	return s, nil
}

func main() {
	cc, err := contractapi.NewChaincode(new(SmartContract))
	if err != nil {
		panic(err)
	}
	if err := cc.Start(); err != nil {
		panic(err)
	}
}
