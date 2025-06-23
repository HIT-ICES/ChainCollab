package chaincode

import (
	"encoding/json"
	"fmt"
	"sort"
	"strings"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

type SmartContract struct {
	contractapi.Contract
}

type Place struct {
	ID    string `json:"id"`    // 参与方 ID
	Token bool   `json:"token"` // 是否已完成
}

type Transition struct {
	ID           string   `json:"id"`           // 组合 key，如 "P1_P3_P4"
	Participants []string `json:"participants"` // 这个 transition 依赖的 K 个参与方
	Fired        bool     `json:"fired"`        // 是否已触发
}

type PetriNetState struct {
	Places      map[string]Place `json:"places"`      // 参与方集合，每个 Place 有一个 Token 状态
	K           int              `json:"k"`           // 至少 K 个完成才能触发 Transition
	Transition  bool             `json:"transition"`  // 是否已触发
	Transitions []Transition     `json:"transitions"` // 所有组合对应的 transitions
}

func (s *SmartContract) InitProcess(ctx contractapi.TransactionContextInterface, participantsJSON string, k int) error {
	var participants []string
	if err := json.Unmarshal([]byte(participantsJSON), &participants); err != nil {
		return fmt.Errorf("invalid participants input: %v", err)
	}

	places := make(map[string]Place)
	for _, p := range participants {
		places[p] = Place{ID: p, Token: false}
	}

	combinations := generateCombinations(participants, k)
	var transitions []Transition
	for _, combo := range combinations {
		t := Transition{
			ID:           getTransitionID(combo),
			Participants: combo,
			Fired:        false,
		}
		transitions = append(transitions, t)
	}

	state := PetriNetState{
		Places:      places,
		K:           k,
		Transition:  false,
		Transitions: transitions,
	}
	data, _ := json.Marshal(state)
	return ctx.GetStub().PutState("petriNet", data)
}

func (s *SmartContract) MarkDone(ctx contractapi.TransactionContextInterface, actor string) error {
	data, err := ctx.GetStub().GetState("petriNet")
	if err != nil || data == nil {
		return fmt.Errorf("petri net not initialized")
	}

	var state PetriNetState
	if err := json.Unmarshal(data, &state); err != nil {
		return err
	}

	if state.Transition {
		return nil // 已经完成，不再触发
	}

	place, exists := state.Places[actor]
	if !exists {
		return fmt.Errorf("actor not found in places")
	}

	place.Token = true
	state.Places[actor] = place

	for i, t := range state.Transitions {
		if t.Fired {
			continue
		}
		ready := true
		for _, pid := range t.Participants {
			if !state.Places[pid].Token {
				ready = false
				break
			}
		}
		if ready {
			state.Transitions[i].Fired = true
			state.Transition = true // 一旦有一组触发，即整体流程完成
			break                   // 可加可不加：如果你只关心任意一组完成
		}
	}

	newData, _ := json.Marshal(state)
	return ctx.GetStub().PutState("petriNet", newData)
}

func (s *SmartContract) QueryStatus(ctx contractapi.TransactionContextInterface) (string, error) {
	data, err := ctx.GetStub().GetState("petriNet")
	if err != nil {
		return "", fmt.Errorf("failed to get state: %v", err)
	}
	if data == nil {
		return "", fmt.Errorf("state not found")
	}

	var state PetriNetState
	if err := json.Unmarshal(data, &state); err != nil {
		return "", fmt.Errorf("failed to parse state: %v", err)
	}

	// 只返回你脚本中关注的字段
	result := map[string]interface{}{
		"p_done": state.Transition,
	}
	resultJSON, _ := json.Marshal(result)
	return string(resultJSON), nil
}

func generateCombinations(arr []string, k int) [][]string {
	var result [][]string
	var comb []string
	var backtrack func(start int)
	backtrack = func(start int) {
		if len(comb) == k {
			tmp := make([]string, k)
			copy(tmp, comb)
			result = append(result, tmp)
			return
		}
		for i := start; i < len(arr); i++ {
			comb = append(comb, arr[i])
			backtrack(i + 1)
			comb = comb[:len(comb)-1]
		}
	}
	backtrack(0)
	return result
}

func getTransitionID(participants []string) string {
	sort.Strings(participants)
	return strings.Join(participants, "_")
}

func main() {
	chaincode, err := contractapi.NewChaincode(new(SmartContract))
	if err != nil {
		panic("Error creating chaincode")
	}
	if err := chaincode.Start(); err != nil {
		panic("Error starting chaincode")
	}
}
