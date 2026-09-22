package main

import (
	"IBC/Oracle/oracle"
	"fmt"
	"log"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

func main() {
	fmt.Println("Starting Oracle chaincode")
	bpmnChaincode, err := contractapi.NewChaincode(&oracle.Oracle{})
	if err != nil {
		log.Panicf("Error creating bpmn chaincode: %v", err)
	}

	if err := bpmnChaincode.Start(); err != nil {
		log.Panicf("Error starting bpmn chaincode: %v", err)
	}
}
