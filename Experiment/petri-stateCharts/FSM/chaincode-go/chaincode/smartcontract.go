package chaincode

import (
	"encoding/json"
	"fmt"
	"sort"
	"strconv"
	"strings"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

type SmartContract struct {
	contractapi.Contract
}

type FSMState string

type FSMData struct {
	CurrentState FSMState `json:"current_state"`
}

type TransitionTable map[string]map[string]string

// 初始化 Task（FSM 初始化）
func (s *SmartContract) InitProcess(ctx contractapi.TransactionContextInterface, participantsJSON string, k string) error {
	var participants []string
	if err := json.Unmarshal([]byte(participantsJSON), &participants); err != nil {
		return fmt.Errorf("invalid participants input: %v", err)
	}

	kInt, err := strconv.Atoi(k)
	if err != nil {
		return fmt.Errorf("invalid k input: %v", err)
	}

	_, table := GenerateFSM(participants, kInt)

	// 存储 transitionTable 到状态数据库
	tableBytes, err := json.Marshal(table)
	if err != nil {
		return fmt.Errorf("failed to marshal transition table: %v", err)
	}
	if err := ctx.GetStub().PutState("TransitionTable", tableBytes); err != nil {
		return fmt.Errorf("failed to put transition table to state: %v", err)
	}

	initial := &FSMData{CurrentState: FSMState("Init")}
	return putFSMState(ctx, initial)
}

// 标记参与者完成
func (s *SmartContract) MarkDone(ctx contractapi.TransactionContextInterface, participantID string) error {
	state, err := getFSMState(ctx)
	if err != nil {
		return err
	}

	// 获取 transitionTable
	tableBytes, err := ctx.GetStub().GetState("TransitionTable")
	if err != nil || tableBytes == nil {
		return fmt.Errorf("transition table not found")
	}
	var transitionTable TransitionTable
	if err := json.Unmarshal(tableBytes, &transitionTable); err != nil {
		return fmt.Errorf("failed to unmarshal transition table: %v", err)
	}

	current := string(state.CurrentState)
	nextMap, ok := transitionTable[current]
	if !ok {
		return fmt.Errorf("invalid current state: %s", current)
	}

	next, found := nextMap[participantID]
	if !found {
		if next, found = nextMap["any"]; !found {
			return fmt.Errorf("no transition for participant %s in state %s", participantID, current)
		}
	}

	state.CurrentState = FSMState(next)
	return putFSMState(ctx, state)
}

// 查询 Task 状态
func (s *SmartContract) QueryStatus(ctx contractapi.TransactionContextInterface) (string, error) {
	state, err := getFSMState(ctx)
	if err != nil {
		return "", err
	}
	result := map[string]interface{}{
		"current_state": state.CurrentState,
		"p_done":        state.CurrentState == "Completed",
	}
	jsonBytes, err := json.Marshal(result)
	if err != nil {
		return "", err
	}
	return string(jsonBytes), nil
}

// ======================
// 辅助函数
// ======================

func getFSMState(ctx contractapi.TransactionContextInterface) (*FSMData, error) {
	data, err := ctx.GetStub().GetState("fsm_state")
	if err != nil {
		return nil, err
	}
	if data == nil {
		return nil, fmt.Errorf("FSM not initialized")
	}
	var state FSMData
	if err := json.Unmarshal(data, &state); err != nil {
		return nil, err
	}
	return &state, nil
}

func putFSMState(ctx contractapi.TransactionContextInterface, state *FSMData) error {
	data, err := json.Marshal(state)
	if err != nil {
		return err
	}
	return ctx.GetStub().PutState("fsm_state", data)
}

// 生成 FSM 状态机
func GenerateFSM(participants []string, k int) ([]string, TransitionTable) {
	stateSet := make(map[string]struct{})
	transitionTable := TransitionTable{}

	stateSet["Init"] = struct{}{}
	for _, p := range participants {
		stateSet[p+"_Done"] = struct{}{}
	}

	transitionTable["Init"] = map[string]string{}
	for _, p := range participants {
		transitionTable["Init"][p] = p + "_Done"
	}

	for i := 1; i < k; i++ {
		combos := combinations(participants, i)
		for _, combo := range combos {
			state := formatState(combo)
			stateSet[state] = struct{}{}
			transitionTable[state] = map[string]string{}
			for _, p := range participants {
				if contains(combo, p) {
					continue
				}
				newCombo := append(combo, p)
				nextState := formatState(newCombo)
				stateSet[nextState] = struct{}{}
				transitionTable[state][p] = nextState
			}
		}
	}

	kCombos := combinations(participants, k)
	for _, combo := range kCombos {
		state := formatState(combo)
		stateSet[state] = struct{}{}
		transitionTable[state] = map[string]string{"any": "Completed"}
	}
	stateSet["Completed"] = struct{}{}

	var states []string
	for s := range stateSet {
		states = append(states, s)
	}
	sort.Strings(states)
	return states, transitionTable
}

func combinations(elements []string, n int) [][]string {
	var helper func(int, []string)
	res := [][]string{}
	helper = func(start int, comb []string) {
		if len(comb) == n {
			tmp := make([]string, n)
			copy(tmp, comb)
			res = append(res, tmp)
			return
		}
		for i := start; i < len(elements); i++ {
			helper(i+1, append(comb, elements[i]))
		}
	}
	helper(0, []string{})
	return res
}

func formatState(parts []string) string {
	sort.Strings(parts)
	return strings.Join(parts, "_") + "_Done"
}

func contains(arr []string, target string) bool {
	for _, v := range arr {
		if v == target {
			return true
		}
	}
	return false
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
