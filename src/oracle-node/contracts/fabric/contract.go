package main

import (
    "encoding/json"
    "fmt"
    "strconv"

    "github.com/hyperledger/fabric-contract-api-go/contractapi"
)

type SmartContract struct {
    contractapi.Contract
}

// Task 结构体映射到世界状态的 JSON
type Task struct {
    ID        string            `json:"id"`
    Params    string            `json:"params"`
    Finished  bool              `json:"finished"`
    FinalResult string          `json:"finalResult"`
    MinResponses int            `json:"minResponses"`
    // oracleId -> result
    Responses map[string]string `json:"responses"`
}

// CreateTask(ctx, taskId, params, minResponses)
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

    task := Task{
        ID:          taskId,
        Params:      params,
        Finished:    false,
        FinalResult: "",
        MinResponses: mr,
        Responses:   make(map[string]string),
    }

    b, err := json.Marshal(task)
    if err != nil {
        return err
    }

    return ctx.GetStub().PutState(taskId, b)
}

// SubmitResult(ctx, taskId, oracleId, result)
func (s *SmartContract) SubmitResult(ctx contractapi.TransactionContextInterface,
    taskId string, oracleId string, result string) error {

    task, err := s.ReadTask(ctx, taskId)
    if err != nil {
        return err
    }

    if task.Finished {
        return fmt.Errorf("task %s already finished", taskId)
    }

    // 记录当前 oracle 的结果（覆盖旧值）
    if task.Responses == nil {
        task.Responses = make(map[string]string)
    }
    task.Responses[oracleId] = result

    // 统计不同结果的出现次数
    countMap := make(map[string]int)
    for _, r := range task.Responses {
        countMap[r]++
    }

    // 判断是否有结果达到 MinResponses
    for r, c := range countMap {
        if c >= task.MinResponses {
            task.Finished = true
            task.FinalResult = r
            break
        }
    }

    b, err := json.Marshal(task)
    if err != nil {
        return err
    }

    return ctx.GetStub().PutState(taskId, b)
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

func main() {
    chaincode, err := contractapi.NewChaincode(new(SmartContract))
    if err != nil {
        panic(fmt.Sprintf("Error create chaincode: %v", err))
    }

    if err := chaincode.Start(); err != nil {
        panic(fmt.Sprintf("Error starting chaincode: %v", err))
    }
}
