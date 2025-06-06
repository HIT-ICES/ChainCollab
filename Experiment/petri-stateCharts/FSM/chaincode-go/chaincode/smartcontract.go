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

var transitionTable map[string]map[string]string

func (s *SmartContract) InitFSM(ctx contractapi.TransactionContextInterface, participantsCSV string, kStr string) error {
	participants := strings.Split(participantsCSV, ",")
	k, err := strconv.Atoi(kStr)
	if err != nil {
		return fmt.Errorf("invalid k value: %s", kStr)
	}

	_, table := GenerateFSM(participants, k)
	transitionTable = table

	initial := &FSMData{CurrentState: FSMState("Init")}
	return putFSMState(ctx, initial)
}

func (s *SmartContract) MarkDoneFSM(ctx contractapi.TransactionContextInterface, participant string) error {
	state, err := getFSMState(ctx)
	if err != nil {
		return err
	}

	current := string(state.CurrentState)
	nextMap, ok := transitionTable[current]
	if !ok {
		return fmt.Errorf("invalid current state: %s", current)
	}

	next, found := nextMap[participant]
	if !found {
		if next, found = nextMap["any"]; !found {
			return fmt.Errorf("no transition for participant %s in state %s", participant, current)
		}
	}

	state.CurrentState = FSMState(next)
	return putFSMState(ctx, state)
}

func (s *SmartContract) QueryFSMState(ctx contractapi.TransactionContextInterface) (string, error) {
	state, err := getFSMState(ctx)
	if err != nil {
		return "", err
	}
	return string(state.CurrentState), nil
}

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

func GenerateFSM(participants []string, k int) ([]string, map[string]map[string]string) {
	stateSet := make(map[string]struct{})
	transitionTable := map[string]map[string]string{}

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

func contains( []string, target string) bool {
	for _, v := range  {
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