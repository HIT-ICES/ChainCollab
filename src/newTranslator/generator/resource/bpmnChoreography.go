package main

import (
	"log"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

func main() {
	bpmnChaincode, err := contractapi.NewChaincode(&SmartContract{})
	if err != nil {
		log.Panicf("Error creating bpmn chaincode: %v", err)
	}

	if err := bpmnChaincode.Start(); err != nil {
		log.Panicf("Error starting bpmn chaincode: %v", err)
	}
}
