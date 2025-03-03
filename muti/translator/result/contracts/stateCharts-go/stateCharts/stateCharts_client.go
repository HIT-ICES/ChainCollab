package stateCharts

import "encoding/json"

type ExecuteStateMachineResult struct {
	Snapshot string `json:"snapshot"`
	Changed  bool   `json:"changed"`
}

func EncodeGetDefaultSnapshotArgs(stateMachineDescription string) [][]byte {
	_args := make([][]byte, 4)
	_args[0] = []byte("GetDefaultSnapshot")
	_args[1] = []byte(stateMachineDescription)
	return _args
}

func DecodeGetDefaultSnapshotResult(b []byte) string {
	return string(b)
}

func EncodeExecuteStateMachineArgs(stateMachineDescription string, currentState string, event string) [][]byte {
	_args := make([][]byte, 4)
	_args[0] = []byte("ExecuteStateMachine")
	_args[1] = []byte(stateMachineDescription)
	_args[2] = []byte(currentState)
	_args[3] = []byte(event)
	return _args
}

func DecodeTriggerActionResult(b []byte) (string, bool) {

	var result ExecuteStateMachineResult

	json.Unmarshal(b, &result)

	return result.Snapshot, result.Changed
}
