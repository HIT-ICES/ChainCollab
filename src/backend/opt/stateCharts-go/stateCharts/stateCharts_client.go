package stateCharts

import (
	"encoding/json"
	"fmt"
)

type ExecuteStateMachineResult struct {
	Snapshot string `json:"snapshot"`
	Changed  bool   `json:"changed"`
}

func EncodeGetDefaultSnapshotArgs(stateMachineDescription string, additionalContent string) [][]byte {
	_args := make([][]byte, 3)
	_args[0] = []byte("GetDefaultSnapshot")
	_args[1] = []byte(stateMachineDescription)
	_args[2] = []byte(additionalContent)
	return _args
}

func DecodeGetDefaultSnapshotResult(b []byte) string {
	fmt.Printf("DecodeGetDefaultSnapshotResult\n")
	fmt.Printf(string(b))
	return string(b)
}

func EncodeExecuteStateMachineArgs(stateMachineDescription string, additionalContent string, currentState string, event string) [][]byte {
	_args := make([][]byte, 5)
	_args[0] = []byte("ExecuteStateMachine")
	_args[1] = []byte(stateMachineDescription)
	_args[2] = []byte(additionalContent)
	_args[3] = []byte(currentState)
	_args[4] = []byte(event)
	return _args
}

func DecodeTriggerActionResult(b []byte) (string, bool) {

	fmt.Print("DecodeTriggerActionResult\n")
	fmt.Printf(string(b))

	var result ExecuteStateMachineResult

	json.Unmarshal(b, &result)

	return result.Snapshot, result.Changed
}
