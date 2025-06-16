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

type ProcessData struct {
	DoneParticipants map[string]bool `json:"done_participants"`
	Participants     []string        `json:"participants"`
	K                int             `json:"k"`
	PDone            bool            `json:"p_done"`
}

// =====================
// InitProcess
// =====================
func (s *SmartContract) InitProcess(ctx contractapi.TransactionContextInterface, participantsJSON string, k string) error {
	var participants []string
	if err := json.Unmarshal([]byte(participantsJSON), &participants); err != nil {
		return fmt.Errorf("invalid participants input: %v", err)
	}

	kInt, err := strconv.Atoi(k)
	if err != nil {
		return fmt.Errorf("invalid k input: %v", err)
	}

	process := &ProcessData{
		DoneParticipants: make(map[string]bool),
		Participants:     participants,
		K:                kInt,
		PDone:            false,
	}

	data, err := json.Marshal(process)
	if err != nil {
		return err
	}

	return ctx.GetStub().PutState("process_data", data)
}

// =====================
// MarkDone
// =====================
func (s *SmartContract) MarkDone(ctx contractapi.TransactionContextInterface, participantID string) error {
	process, err := getProcessData(ctx)
	if err != nil {
		return err
	}

	if process.PDone {
		return fmt.Errorf("process already completed")
	}

	// Check if participant is valid
	valid := false
	for _, p := range process.Participants {
		if p == participantID {
			valid = true
			break
		}
	}
	if !valid {
		return fmt.Errorf("invalid participant: %s", participantID)
	}

	if !process.DoneParticipants[participantID] {
		process.DoneParticipants[participantID] = true
	}

	// Count how many are done
	doneCount := 0
	for _, done := range process.DoneParticipants {
		if done {
			doneCount++
		}
	}

	if doneCount >= process.K {
		process.PDone = true
	}

	return putProcessData(ctx, process)
}

// =====================
// QueryStatus
// =====================
func (s *SmartContract) QueryStatus(ctx contractapi.TransactionContextInterface) (string, error) {
	process, err := getProcessData(ctx)
	if err != nil {
		return "", err
	}

	result := map[string]interface{}{
		"done_participants": process.DoneParticipants,
		"k":                 process.K,
		"p_done":            process.PDone,
	}
	jsonBytes, err := json.Marshal(result)
	if err != nil {
		return "", err
	}
	return string(jsonBytes), nil
}

// =====================
// Helper Functions
// =====================

func getProcessData(ctx contractapi.TransactionContextInterface) (*ProcessData, error) {
	data, err := ctx.GetStub().GetState("process_data")
	if err != nil {
		return nil, err
	}
	if data == nil {
		return nil, fmt.Errorf("process not initialized")
	}
	var process ProcessData
	if err := json.Unmarshal(data, &process); err != nil {
		return nil, err
	}
	return &process, nil
}

func putProcessData(ctx contractapi.TransactionContextInterface, process *ProcessData) error {
	data, err := json.Marshal(process)
	if err != nil {
		return err
	}
	return ctx.GetStub().PutState("process_data", data)
}

// =====================
// main
// =====================

func main() {
	chaincode, err := contractapi.NewChaincode(new(SmartContract))
	if err != nil {
		panic("Error creating chaincode")
	}
	if err := chaincode.Start(); err != nil {
		panic("Error starting chaincode")
	}
}