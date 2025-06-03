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

type ProcessState struct {
	Participants []string        `json:"participants"`
	K            int             `json:"k"`
	DoneMap      map[string]bool `json:"done_map"`
	PDone        bool            `json:"p_done"`
}

func (s *SmartContract) InitProcess(ctx contractapi.TransactionContextInterface, participantsJSON string, k int) error {
	var participants []string
	if err := json.Unmarshal([]byte(participantsJSON), &participants); err != nil {
		return fmt.Errorf("invalid participants input: %v", err)
	}

	triggeredMap := make(map[string]bool)
	combinations := getCombinations(participants, k)
	for _, combo := range combinations {
		key := comboKey(combo)
		triggeredMap[key] = false
	}

	state := ProcessState{
		Participants: participants,
		K:            k,
		DoneMap:      make(map[string]bool),
		PDone:        false,
	}

	data, _ := json.Marshal(state)
	return ctx.GetStub().PutState("process", data)
}

func (s *SmartContract) MarkDone(ctx contractapi.TransactionContextInterface, actor string) error {
	data, err := ctx.GetStub().GetState("process")
	if err != nil || data == nil {
		return fmt.Errorf("process not initialized")
	}

	var state ProcessState
	json.Unmarshal(data, &state)

	if state.PDone {
		return nil
	}

	state.DoneMap[actor] = true

	// Check all C(N, K) combinations
	combinations := getCombinations(state.Participants, state.K)
	for _, combo := range combinations {
		if allDone(combo, state.DoneMap) {
			state.PDone = true
			break
		}
	}
	newData, _ := json.Marshal(state)
	return ctx.GetStub().PutState("process", newData)
}

func (s *SmartContract) QueryStatus(ctx contractapi.TransactionContextInterface) (string, error) {
	data, err := ctx.GetStub().GetState("process")
	if err != nil {
		return "", err
	}
	return string(data), nil
}

// --- Helper Functions ---

func allDone(combo []string, doneMap map[string]bool) bool {
	for _, participant := range combo {
		if !doneMap[participant] {
			return false
		}
	}
	return true
}

func comboKey(combo []string) string {
	sort.Strings(combo)
	return strings.Join(combo, "_")
}

func getCombinations(arr []string, k int) [][]string {
	var result [][]string
	var comb []string
	var backtrack func(start int)

	backtrack = func(start int) {
		if len(comb) == k {
			comboCopy := make([]string, k)
			copy(comboCopy, comb)
			result = append(result, comboCopy)
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

func main() {
	chaincode, err := contractapi.NewChaincode(new(SmartContract))
	if err != nil {
		panic("Error creating chaincode")
	}
	if err := chaincode.Start(); err != nil {
		panic("Error starting chaincode")
	}
}
