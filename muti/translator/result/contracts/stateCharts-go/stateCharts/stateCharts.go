package stateCharts

import (
	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

// A Contract For Storage Data in Fabric Chain, support CRUD operations
// Every Contract using this Contract with a specific key to divide the data space. then a key-value pair will be stored in the chain

// V1.0 without Access Control and anything else, just set and read
type StateCharts struct {
	contractapi.Contract
}

// Three Function need to Be Provided
// 1. To Check if the Current Action is Valid (stateMachineDescription, currentState, action) => bool
// 2. To Trigger the Action, and return the new State (stateMachineDescription, currentState, action) => newState

func IfActionValid(stateMachineDescription string, currentState string, action string) bool {
	return true
}

func TriggerAction(stateMachineDescription string, currentState string, action string) string {
	return "newState"
}
