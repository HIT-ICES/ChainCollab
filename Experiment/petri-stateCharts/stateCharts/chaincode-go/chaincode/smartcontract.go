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

type TaskPhase string

const (
	TaskInProgress TaskPhase = "IN_PROGRESS"
	TaskCompleted  TaskPhase = "COMPLETED"
)

type SubState struct {
	Status string `json:"status"` // 如：WAITING、DONE
}

type TaskState struct {
	Participants []string            `json:"participants"`
	K            int                 `json:"k"`
	DoneMap      map[string]bool     `json:"done_map"`
	Phase        TaskPhase           `json:"phase"`
	SubStates    map[string]SubState `json:"substates"` // 每个参与者子状态
}

// 初始化任务
func (s *SmartContract) InitProcess(ctx contractapi.TransactionContextInterface, n string, k string) error {
	nInt, err := strconv.Atoi(n)
	if err != nil {
		return fmt.Errorf("invalid n input: %v", err)
	}
	kInt, err := strconv.Atoi(k)
	if err != nil {
		return fmt.Errorf("invalid k input: %v", err)
	}

	participants := make([]string, nInt)
	doneMap := make(map[string]bool)
	subStates := make(map[string]SubState)

	for i := 0; i < nInt; i++ {
		pid := fmt.Sprintf("P%d", i)
		participants[i] = pid
		doneMap[pid] = false
		subStates[pid] = SubState{Status: "WAITING"}
	}

	task := TaskState{
		Participants: participants,
		K:            kInt,
		DoneMap:      doneMap,
		Phase:        TaskInProgress,
		SubStates:    subStates,
	}

	data, err := json.Marshal(task)
	if err != nil {
		return fmt.Errorf("marshal task state failed: %v", err)
	}

	return ctx.GetStub().PutState("TaskState", data)
}

// 参与方完成任务
func (s *SmartContract) MarkDone(ctx contractapi.TransactionContextInterface, participantID string) error {
	taskBytes, err := ctx.GetStub().GetState("TaskState")
	if err != nil || taskBytes == nil {
		return fmt.Errorf("task state not found")
	}

	var task TaskState
	if err := json.Unmarshal(taskBytes, &task); err != nil {
		return fmt.Errorf("unmarshal task state failed: %v", err)
	}

	if task.Phase == TaskCompleted {
		return fmt.Errorf("task already completed")
	}

	// 验证参与方
	valid := false
	for _, p := range task.Participants {
		if p == participantID {
			valid = true
			break
		}
	}
	if !valid {
		return fmt.Errorf("invalid participant: %s", participantID)
	}

	// 标记完成
	task.DoneMap[participantID] = true
	task.SubStates[participantID] = SubState{Status: "DONE"}

	// 判断是否完成任务（有 >= K 个 DONE）
	count := 0
	for _, done := range task.DoneMap {
		if done {
			count++
		}
	}
	if count >= task.K {
		task.Phase = TaskCompleted
	}

	updatedBytes, err := json.Marshal(task)
	if err != nil {
		return fmt.Errorf("marshal updated task failed: %v", err)
	}

	return ctx.GetStub().PutState("TaskState", updatedBytes)
}

// 查询任务状态
func (s *SmartContract) QueryStatus(ctx contractapi.TransactionContextInterface) (string, error) {
	taskBytes, err := ctx.GetStub().GetState("TaskState")
	if err != nil || taskBytes == nil {
		return "", fmt.Errorf("task state not found")
	}

	var task TaskState
	if err := json.Unmarshal(taskBytes, &task); err != nil {
		return "", fmt.Errorf("unmarshal task failed: %v", err)
	}

	resp := map[string]interface{}{
		"p_done":   task.Phase == TaskCompleted,
		"phase":    task.Phase,
		"done_map": task.DoneMap}
	out, err := json.Marshal(resp)
	if err != nil {
		return "", fmt.Errorf("marshal response failed: %v", err)
	}

	return string(out), nil
}
