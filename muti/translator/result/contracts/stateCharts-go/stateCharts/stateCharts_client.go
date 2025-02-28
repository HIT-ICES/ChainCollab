package stateCharts

func EncodeIfActionValidArgs(stateMachineDescription string, currentState string, action string) [][]byte {
	_args := make([][]byte, 4)
	_args[0] = []byte("IfActionValid")
	_args[1] = []byte(stateMachineDescription)
	_args[2] = []byte(currentState)
	_args[3] = []byte(action)
	return _args
}

func DecodeIfActionValidResult(b []byte) bool {
	return string(b) == "true"
}

func EncodeTriggerActionArgs(stateMachineDescription string, currentState string, action string) [][]byte {
	_args := make([][]byte, 4)
	_args[0] = []byte("TriggerAction")
	_args[1] = []byte(stateMachineDescription)
	_args[2] = []byte(currentState)
	_args[3] = []byte(action)
	return _args
}

func DecodeTriggerActionResult(b []byte) (string, bool) {
	return string(b), true
}
