package main

import (
	"crypto/ecdsa"
	"crypto/sha256"
	"crypto/x509"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"math/big"
	"strconv"
	"strings"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

// ====== 类型定义 ======

type SmartContract struct {
	contractapi.Contract
}

type AggregationMode string

const (
	ModeMean             AggregationMode = "MEAN"
	ModeWeightedMean     AggregationMode = "WEIGHTED_MEAN"
	ModeStrongConsistency AggregationMode = "STRONG_CONSISTENCY"
)

type Oracle struct {
	ID     string `json:"id"`
	PubKey string `json:"pubKey"` // base64(PKIX)
	Active bool   `json:"active"`
}

type Submission struct {
	Oracle string `json:"oracle"`
	Value  int64  `json:"value"`
}

type DataTask struct {
	ID            string                     `json:"id"`
	Requester     string                     `json:"requester"`
	DataType      string                     `json:"dataType"`
	Mode          AggregationMode            `json:"mode"`
	MinResponses  int                        `json:"minResponses"`
	Threshold     int                        `json:"threshold"`
	Finished      bool                       `json:"finished"`
	FinalValue    int64                      `json:"finalValue"`
	AllowedOracles []string                  `json:"allowedOracles"`
	Weights       map[string]int64           `json:"weights"`
	Responded     map[string]bool            `json:"responded"`
	Submissions   []Submission               `json:"submissions"`
}

type ComputeTask struct {
	ID            string            `json:"id"`
	Requester     string            `json:"requester"`
	ComputeType   string            `json:"computeType"`
	PayloadHash   string            `json:"payloadHash"`
	Threshold     int               `json:"threshold"`
	Finished      bool              `json:"finished"`
	FinalResult   string            `json:"finalResult"`
	AllowedOracles []string         `json:"allowedOracles"`
	Responded     map[string]bool   `json:"responded"`
	ResultCount   map[string]int    `json:"resultCount"`
}

const (
	oracleKeyPrefix = "oracle::"
	dataTaskPrefix  = "dataTask::"
	compTaskPrefix  = "computeTask::"
)

// ====== Oracle 管理 ======

func (s *SmartContract) RegisterOracle(ctx contractapi.TransactionContextInterface, oracleID string, pubKeyBase64 string) error {
	if oracleID == "" {
		return errors.New("oracleID is required")
	}
	if pubKeyBase64 == "" {
		return errors.New("pubKey is required")
	}
	oracle := &Oracle{ID: oracleID, PubKey: pubKeyBase64, Active: true}
	return s.saveOracle(ctx, oracle)
}

func (s *SmartContract) DisableOracle(ctx contractapi.TransactionContextInterface, oracleID string) error {
	oracle, err := s.getOracle(ctx, oracleID)
	if err != nil {
		return err
	}
	oracle.Active = false
	return s.saveOracle(ctx, oracle)
}

// ====== 数据类任务（聚合） ======

func (s *SmartContract) CreateDataTask(
	ctx contractapi.TransactionContextInterface,
	taskID string,
	requester string,
	dataType string,
	mode string,
	allowedOraclesJSON string,
	weightsJSON string,
	minResponses string,
	threshold string,
) error {
	if taskID == "" {
		return errors.New("taskID is required")
	}
	exists, err := s.dataTaskExists(ctx, taskID)
	if err != nil {
		return err
	}
	if exists {
		return fmt.Errorf("data task %s already exists", taskID)
	}

	var allowed []string
	if err := json.Unmarshal([]byte(allowedOraclesJSON), &allowed); err != nil {
		return fmt.Errorf("invalid allowedOracles: %v", err)
	}
	if len(allowed) == 0 {
		return errors.New("allowedOracles is empty")
	}

	var weights map[string]int64
	if weightsJSON != "" {
		if err := json.Unmarshal([]byte(weightsJSON), &weights); err != nil {
			return fmt.Errorf("invalid weights: %v", err)
		}
	}

	mr, err := strconv.Atoi(minResponses)
	if err != nil {
		return fmt.Errorf("minResponses must be int: %v", err)
	}
	th, err := strconv.Atoi(threshold)
	if err != nil {
		return fmt.Errorf("threshold must be int: %v", err)
	}

	task := &DataTask{
		ID:            taskID,
		Requester:     requester,
		DataType:      dataType,
		Mode:          AggregationMode(mode),
		MinResponses:  mr,
		Threshold:     th,
		Finished:      false,
		FinalValue:    0,
		AllowedOracles: allowed,
		Weights:       weights,
		Responded:     make(map[string]bool),
		Submissions:   []Submission{},
	}

	for _, o := range allowed {
		oracle, err := s.getOracle(ctx, o)
		if err != nil {
			return err
		}
		if !oracle.Active {
			return fmt.Errorf("oracle %s inactive", o)
		}
	}

	if task.Mode == ModeWeightedMean && len(task.Weights) == 0 {
		return errors.New("weights required for WEIGHTED_MEAN")
	}

	if task.Mode == ModeStrongConsistency && task.Threshold <= 0 {
		return errors.New("threshold required for STRONG_CONSISTENCY")
	}

	if task.Mode != ModeStrongConsistency && task.MinResponses <= 0 {
		task.MinResponses = len(allowed)
	}

	return s.saveDataTask(ctx, task)
}

func (s *SmartContract) SubmitData(
	ctx contractapi.TransactionContextInterface,
	taskID string,
	oracleID string,
	value string,
	signatureBase64 string,
) error {
	task, err := s.readDataTask(ctx, taskID)
	if err != nil {
		return err
	}
	if task.Finished {
		return fmt.Errorf("task %s already finished", taskID)
	}
	if !contains(task.AllowedOracles, oracleID) {
		return fmt.Errorf("oracle %s not allowed", oracleID)
	}
	if task.Responded[oracleID] {
		return fmt.Errorf("oracle %s already responded", oracleID)
	}

	v, err := strconv.ParseInt(value, 10, 64)
	if err != nil {
		return fmt.Errorf("value must be int64: %v", err)
	}

	msg := buildDataMessage(taskID, v)
	oracle, err := s.getOracle(ctx, oracleID)
	if err != nil {
		return err
	}
	if err := verifySignature(oracle.PubKey, msg, signatureBase64); err != nil {
		return fmt.Errorf("verify signature failed: %v", err)
	}

	task.Responded[oracleID] = true
	task.Submissions = append(task.Submissions, Submission{Oracle: oracleID, Value: v})

	if task.Mode == ModeStrongConsistency {
		if ok, candidate := strongConsistency(task.Submissions, task.Threshold); ok {
			task.Finished = true
			task.FinalValue = candidate
		}
	} else if len(task.Submissions) >= task.MinResponses {
		agg, err := aggregate(task)
		if err != nil {
			return err
		}
		task.Finished = true
		task.FinalValue = agg
	}

	return s.saveDataTask(ctx, task)
}

// ====== 计算类任务（阈值签名） ======

func (s *SmartContract) CreateComputeTask(
	ctx contractapi.TransactionContextInterface,
	taskID string,
	requester string,
	computeType string,
	payloadHash string,
	allowedOraclesJSON string,
	threshold string,
) error {
	if taskID == "" {
		return errors.New("taskID is required")
	}
	exists, err := s.computeTaskExists(ctx, taskID)
	if err != nil {
		return err
	}
	if exists {
		return fmt.Errorf("compute task %s already exists", taskID)
	}
	var allowed []string
	if err := json.Unmarshal([]byte(allowedOraclesJSON), &allowed); err != nil {
		return fmt.Errorf("invalid allowedOracles: %v", err)
	}
	if len(allowed) == 0 {
		return errors.New("allowedOracles is empty")
	}
	th, err := strconv.Atoi(threshold)
	if err != nil {
		return fmt.Errorf("threshold must be int: %v", err)
	}
	if th <= 0 || th > len(allowed) {
		return fmt.Errorf("threshold out of range")
	}

	task := &ComputeTask{
		ID:            taskID,
		Requester:     requester,
		ComputeType:   computeType,
		PayloadHash:   payloadHash,
		Threshold:     th,
		Finished:      false,
		FinalResult:   "",
		AllowedOracles: allowed,
		Responded:     make(map[string]bool),
		ResultCount:   make(map[string]int),
	}

	for _, o := range allowed {
		oracle, err := s.getOracle(ctx, o)
		if err != nil {
			return err
		}
		if !oracle.Active {
			return fmt.Errorf("oracle %s inactive", o)
		}
	}

	return s.saveComputeTask(ctx, task)
}

func (s *SmartContract) SubmitComputeResult(
	ctx contractapi.TransactionContextInterface,
	taskID string,
	oracleID string,
	result string,
	signatureBase64 string,
) error {
	task, err := s.readComputeTask(ctx, taskID)
	if err != nil {
		return err
	}
	if task.Finished {
		return fmt.Errorf("task %s already finished", taskID)
	}
	if !contains(task.AllowedOracles, oracleID) {
		return fmt.Errorf("oracle %s not allowed", oracleID)
	}
	if task.Responded[oracleID] {
		return fmt.Errorf("oracle %s already responded", oracleID)
	}

	msg := buildComputeMessage(taskID, task.PayloadHash, result)
	oracle, err := s.getOracle(ctx, oracleID)
	if err != nil {
		return err
	}
	if err := verifySignature(oracle.PubKey, msg, signatureBase64); err != nil {
		return fmt.Errorf("verify signature failed: %v", err)
	}

	task.Responded[oracleID] = true
	task.ResultCount[result]++
	if task.ResultCount[result] >= task.Threshold {
		task.Finished = true
		task.FinalResult = result
	}

	return s.saveComputeTask(ctx, task)
}

// ====== 查询 ======

func (s *SmartContract) ReadDataTask(ctx contractapi.TransactionContextInterface, taskID string) (*DataTask, error) {
	return s.readDataTask(ctx, taskID)
}

func (s *SmartContract) ReadComputeTask(ctx contractapi.TransactionContextInterface, taskID string) (*ComputeTask, error) {
	return s.readComputeTask(ctx, taskID)
}

// ====== 内部工具 ======

func buildDataMessage(taskID string, value int64) []byte {
	payload := fmt.Sprintf("%s|%d", taskID, value)
	sum := sha256.Sum256([]byte(payload))
	return sum[:]
}

func buildComputeMessage(taskID string, payloadHash string, result string) []byte {
	payload := strings.Join([]string{taskID, payloadHash, result}, "|")
	sum := sha256.Sum256([]byte(payload))
	return sum[:]
}

func aggregate(task *DataTask) (int64, error) {
	if task.Mode == ModeMean {
		var sum int64
		for _, s := range task.Submissions {
			sum += s.Value
		}
		return sum / int64(len(task.Submissions)), nil
	}
	if task.Mode == ModeWeightedMean {
		var sum int64
		var weightTotal int64
		for _, s := range task.Submissions {
			w := task.Weights[s.Oracle]
			sum += s.Value * w
			weightTotal += w
		}
		if weightTotal == 0 {
			return 0, errors.New("zero weight")
		}
		return sum / weightTotal, nil
	}
	return 0, errors.New("unsupported aggregation mode")
}

func strongConsistency(subs []Submission, threshold int) (bool, int64) {
	for i := range subs {
		candidate := subs[i].Value
		count := 0
		for j := range subs {
			if subs[j].Value == candidate {
				count++
			}
		}
		if count >= threshold {
			return true, candidate
		}
	}
	return false, 0
}

func contains(list []string, v string) bool {
	for _, item := range list {
		if item == v {
			return true
		}
	}
	return false
}

func (s *SmartContract) saveOracle(ctx contractapi.TransactionContextInterface, oracle *Oracle) error {
	key := oracleKeyPrefix + oracle.ID
	b, err := json.Marshal(oracle)
	if err != nil {
		return err
	}
	return ctx.GetStub().PutState(key, b)
}

func (s *SmartContract) getOracle(ctx contractapi.TransactionContextInterface, oracleID string) (*Oracle, error) {
	key := oracleKeyPrefix + oracleID
	b, err := ctx.GetStub().GetState(key)
	if err != nil {
		return nil, err
	}
	if b == nil {
		return nil, fmt.Errorf("oracle %s not found", oracleID)
	}
	var oracle Oracle
	if err := json.Unmarshal(b, &oracle); err != nil {
		return nil, err
	}
	return &oracle, nil
}

func (s *SmartContract) dataTaskExists(ctx contractapi.TransactionContextInterface, taskID string) (bool, error) {
	b, err := ctx.GetStub().GetState(dataTaskPrefix + taskID)
	if err != nil {
		return false, err
	}
	return b != nil, nil
}

func (s *SmartContract) computeTaskExists(ctx contractapi.TransactionContextInterface, taskID string) (bool, error) {
	b, err := ctx.GetStub().GetState(compTaskPrefix + taskID)
	if err != nil {
		return false, err
	}
	return b != nil, nil
}

func (s *SmartContract) saveDataTask(ctx contractapi.TransactionContextInterface, task *DataTask) error {
	b, err := json.Marshal(task)
	if err != nil {
		return err
	}
	return ctx.GetStub().PutState(dataTaskPrefix+task.ID, b)
}

func (s *SmartContract) saveComputeTask(ctx contractapi.TransactionContextInterface, task *ComputeTask) error {
	b, err := json.Marshal(task)
	if err != nil {
		return err
	}
	return ctx.GetStub().PutState(compTaskPrefix+task.ID, b)
}

func (s *SmartContract) readDataTask(ctx contractapi.TransactionContextInterface, taskID string) (*DataTask, error) {
	b, err := ctx.GetStub().GetState(dataTaskPrefix + taskID)
	if err != nil {
		return nil, err
	}
	if b == nil {
		return nil, fmt.Errorf("data task %s not found", taskID)
	}
	var task DataTask
	if err := json.Unmarshal(b, &task); err != nil {
		return nil, err
	}
	if task.Responded == nil {
		task.Responded = make(map[string]bool)
	}
	if task.Weights == nil {
		task.Weights = make(map[string]int64)
	}
	return &task, nil
}

func (s *SmartContract) readComputeTask(ctx contractapi.TransactionContextInterface, taskID string) (*ComputeTask, error) {
	b, err := ctx.GetStub().GetState(compTaskPrefix + taskID)
	if err != nil {
		return nil, err
	}
	if b == nil {
		return nil, fmt.Errorf("compute task %s not found", taskID)
	}
	var task ComputeTask
	if err := json.Unmarshal(b, &task); err != nil {
		return nil, err
	}
	if task.Responded == nil {
		task.Responded = make(map[string]bool)
	}
	if task.ResultCount == nil {
		task.ResultCount = make(map[string]int)
	}
	return &task, nil
}

func verifySignature(pubKeyBase64 string, message []byte, sigBase64 string) error {
	der, err := base64.StdEncoding.DecodeString(pubKeyBase64)
	if err != nil {
		return fmt.Errorf("invalid pubkey base64: %v", err)
	}
	pub, err := x509.ParsePKIXPublicKey(der)
	if err != nil {
		return fmt.Errorf("parse pubkey failed: %v", err)
	}
	ecdsaKey, ok := pub.(*ecdsa.PublicKey)
	if !ok {
		return errors.New("pubkey is not ECDSA")
	}
	sigBytes, err := base64.StdEncoding.DecodeString(sigBase64)
	if err != nil {
		return fmt.Errorf("invalid signature base64: %v", err)
	}
	if len(sigBytes) != 64 {
		return errors.New("signature must be 64 bytes (r||s)")
	}
	r := new(big.Int).SetBytes(sigBytes[:32])
	s := new(big.Int).SetBytes(sigBytes[32:])
	if !ecdsa.Verify(ecdsaKey, message, r, s) {
		return errors.New("verify failed")
	}
	return nil
}

func main() {
	chaincode, err := contractapi.NewChaincode(new(SmartContract))
	if err != nil {
		panic(fmt.Sprintf("Error create chaincode: %v", err))
	}
	if err := chaincode.Start(); err != nil {
		panic(fmt.Sprintf("Error starting chaincode: %v", err))
	}
}
