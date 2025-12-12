package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"strconv"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

type SmartContract struct {
	contractapi.Contract
}

type Task struct {
	ID           string `json:"id"`
	Params       string `json:"params"`
	Finished     bool   `json:"finished"`
	FinalResult  string `json:"finalResult"`
	MinResponses int    `json:"minResponses"`
	// oracleId -> result
	Responses map[string]string `json:"responses"`
}

func (s *SmartContract) CreateTask(ctx contractapi.TransactionContextInterface,
	taskId string, params string, minResponses string) error {

	exists, err := s.TaskExists(ctx, taskId)
	if err != nil {
		return err
	}
	if exists {
		return fmt.Errorf("task %s already exists", taskId)
	}

	mr, err := strconv.Atoi(minResponses)
	if err != nil {
		return fmt.Errorf("minResponses must be int: %v", err)
	}

	task, err := newTask(taskId, params, mr)
	if err != nil {
		return err
	}

	return s.saveTask(ctx, task)
}

// SubmitResult(ctx, taskId, oracleId, result)
func (s *SmartContract) SubmitResult(ctx contractapi.TransactionContextInterface,
	taskId string, oracleId string, result string) error {
	return s.updateTask(ctx, taskId, func(task *Task) error {
		return task.addResponse(oracleId, result)
	})
}

func (s *SmartContract) ReadTask(ctx contractapi.TransactionContextInterface, taskId string) (*Task, error) {
	b, err := ctx.GetStub().GetState(taskId)
	if err != nil {
		return nil, fmt.Errorf("failed to read task %s: %v", taskId, err)
	}
	if b == nil {
		return nil, fmt.Errorf("task %s does not exist", taskId)
	}

	var task Task
	if err := json.Unmarshal(b, &task); err != nil {
		return nil, err
	}
	return &task, nil
}

func (s *SmartContract) TaskExists(ctx contractapi.TransactionContextInterface, taskId string) (bool, error) {
	b, err := ctx.GetStub().GetState(taskId)
	if err != nil {
		return false, err
	}
	return b != nil, nil
}

func newTask(taskId string, params string, minResponses int) (*Task, error) {
	if taskId == "" {
		return nil, errors.New("taskId is required")
	}
	if minResponses <= 0 {
		return nil, fmt.Errorf("minResponses must be positive, got %d", minResponses)
	}

	return &Task{
		ID:           taskId,
		Params:       params,
		Finished:     false,
		FinalResult:  "",
		MinResponses: minResponses,
		Responses:    make(map[string]string),
	}, nil
}

func (s *SmartContract) saveTask(ctx contractapi.TransactionContextInterface, task *Task) error {
	if task == nil {
		return errors.New("task is nil")
	}
	b, err := json.Marshal(task)
	if err != nil {
		return err
	}
	return ctx.GetStub().PutState(task.ID, b)
}

func (s *SmartContract) updateTask(ctx contractapi.TransactionContextInterface, taskId string, fn func(*Task) error) error {
	task, err := s.ReadTask(ctx, taskId)
	if err != nil {
		return err
	}

	if err := fn(task); err != nil {
		return err
	}

	return s.saveTask(ctx, task)
}

func (t *Task) addResponse(oracleID string, result string) error {
	if oracleID == "" {
		return errors.New("oracleId is required")
	}
	if result == "" {
		return errors.New("result is required")
	}
	if t.Finished {
		return fmt.Errorf("task %s already finished", t.ID)
	}

	t.ensureResponses()
	t.Responses[oracleID] = result

	if majority, ok := t.majorityResult(); ok {
		t.Finished = true
		t.FinalResult = majority
	}

	return nil
}

func (t *Task) majorityResult() (string, bool) {
	t.ensureResponses()
	countMap := make(map[string]int)
	for _, r := range t.Responses {
		countMap[r]++
		if countMap[r] >= t.MinResponses {
			return r, true
		}
	}
	return "", false
}

func (t *Task) ensureResponses() {
	if t.Responses == nil {
		t.Responses = make(map[string]string)
	}
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
