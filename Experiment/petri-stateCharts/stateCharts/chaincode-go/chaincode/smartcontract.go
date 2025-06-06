package chaincode

import (
	"encoding/json"
	"fmt"
	"strconv"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

type SmartContract struct {
	contractapi.Contract
}

type TaskState struct {
	Participants []string        `json:"participants"`
	K            int             `json:"k"`
	DoneMap      map[string]bool `json:"done_map"`
	PDone        bool            `json:"p_done"` // 字段名改为 p_done
}

// 初始化 Task
func (s *SmartContract) InitProcess(ctx contractapi.TransactionContextInterface, participantsJSON string, k string) error {
	var participants []string
	if err := json.Unmarshal([]byte(participantsJSON), &participants); err != nil {
		return fmt.Errorf("invalid participants input: %v", err)
	}

	kInt, err := strconv.Atoi(k)
	if err != nil {
		return fmt.Errorf("invalid k input: %v", err)
	}

	doneMap := make(map[string]bool)
	for _, p := range participants {
		doneMap[p] = false
	}

	task := TaskState{
		Participants: participants,
		K:            kInt,
		DoneMap:      doneMap,
		PDone:        false,
	}

	data, err := json.Marshal(task)
	if err != nil {
		return fmt.Errorf("marshal task state failed: %v", err)
	}

	return ctx.GetStub().PutState("TaskState", data)
}

// 完成 Task 的一个参与方
func (s *SmartContract) MarkDone(ctx contractapi.TransactionContextInterface, participantID string) error {
	taskBytes, err := ctx.GetStub().GetState("TaskState")
	if err != nil || taskBytes == nil {
		return fmt.Errorf("task state not found")
	}

	var task TaskState
	if err := json.Unmarshal(taskBytes, &task); err != nil {
		return fmt.Errorf("unmarshal task state failed: %v", err)
	}

	if task.PDone {
		return fmt.Errorf("task already completed")
	}

	// 检查合法参与方
	validParticipant := false
	for _, p := range task.Participants {
		if p == participantID {
			validParticipant = true
			break
		}
	}

	if !validParticipant {
		return fmt.Errorf("participant %s is not part of task", participantID)
	}

	// 标记完成
	task.DoneMap[participantID] = true

	// 统计完成数量
	count := 0
	for _, done := range task.DoneMap {
		if done {
			count++
		}
	}

	// 是否完成Task
	if count >= task.K {
		task.PDone = true
	}

	// 更新状态
	updatedBytes, err := json.Marshal(task)
	if err != nil {
		return fmt.Errorf("marshal updated task state failed: %v", err)
	}

	return ctx.GetStub().PutState("TaskState", updatedBytes)
}

// 查询 Task 状态
func (s *SmartContract) QueryStatus(ctx contractapi.TransactionContextInterface) (string, error) {
	taskBytes, err := ctx.GetStub().GetState("TaskState")
	if err != nil || taskBytes == nil {
		return "", fmt.Errorf("task state not found")
	}

	return string(taskBytes), nil
}
