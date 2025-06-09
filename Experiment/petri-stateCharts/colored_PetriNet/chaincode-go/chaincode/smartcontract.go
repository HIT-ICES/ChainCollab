package main

import (
	"encoding/json"
	"fmt"
	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

// ============================
// 链码结构体
// ============================
type SmartContract struct {
	contractapi.Contract
}

// ============================
// Coloured Petri Net 状态结构体
// ============================
type ColouredPetriNetState struct {
	Tokens       []string `json:"tokens"`       // token 池（颜色）
	Triggered    bool     `json:"triggered"`    // 是否激发 transition
	K            int      `json:"k"`            // 至少 K 个 token 才能触发
	Participants []string `json:"participants"` // 合法参与者白名单
}

// ============================
// 初始化函数（设置 K 和参与者）
// ============================
func (s *SmartContract) InitProcess(ctx contractapi.TransactionContextInterface, k int, participantsJSON string) error {
	var participants []string
	if err := json.Unmarshal([]byte(participantsJSON), &participants); err != nil {
		return fmt.Errorf("invalid participants JSON: %v", err)
	}

	state := ColouredPetriNetState{
		Tokens:       []string{},
		Triggered:    false,
		K:            k,
		Participants: participants,
	}

	return putCPNState(ctx, state)
}

// ============================
// MarkDone：添加参与者 token
// ============================
func (s *SmartContract) MarkDone(ctx contractapi.TransactionContextInterface, participant string) error {
	state, err := getCPNState(ctx)
	if err != nil {
		return err
	}

	if state.Triggered {
		return nil // 已激发，无需处理
	}

	// 校验参与者是否合法
	isValid := false
	for _, p := range state.Participants {
		if p == participant {
			isValid = true
			break
		}
	}
	if !isValid {
		return fmt.Errorf("unauthorized participant: %s", participant)
	}

	// 检查是否重复 token
	for _, t := range state.Tokens {
		if t == participant {
			return nil // 忽略重复
		}
	}

	// 添加新 token
	state.Tokens = append(state.Tokens, participant)

	// 判断是否满足触发条件
	if len(state.Tokens) >= state.K {
		state.Triggered = true
	}

	return putCPNState(ctx, state)
}

// ============================
// 状态查询函数
// ============================
func (s *SmartContract) QueryStatus(ctx contractapi.TransactionContextInterface) (*ColouredPetriNetState, error) {
	state, err := getCPNState(ctx)
	if err != nil {
		return nil, err
	}
	return &state, nil
}

// ============================
// 状态工具函数
// ============================

// 从账本读取状态
func getCPNState(ctx contractapi.TransactionContextInterface) (ColouredPetriNetState, error) {
	var state ColouredPetriNetState
	bytes, err := ctx.GetStub().GetState("state")
	if err != nil || bytes == nil {
		return state, fmt.Errorf("state not found or read error")
	}
	if err := json.Unmarshal(bytes, &state); err != nil {
		return state, fmt.Errorf("unmarshal error: %v", err)
	}
	return state, nil
}

// 写入状态到账本
func putCPNState(ctx contractapi.TransactionContextInterface, state ColouredPetriNetState) error {
	data, err := json.Marshal(state)
	if err != nil {
		return fmt.Errorf("marshal error: %v", err)
	}
	return ctx.GetStub().PutState("state", data)
}

// ============================
// 主函数入口
// ============================
func main() {
	chaincode, err := contractapi.NewChaincode(new(SmartContract))
	if err != nil {
		panic(fmt.Sprintf("Error creating chaincode: %v", err))
	}

	if err := chaincode.Start(); err != nil {
		panic(fmt.Sprintf("Error starting chaincode: %v", err))
	}
}
