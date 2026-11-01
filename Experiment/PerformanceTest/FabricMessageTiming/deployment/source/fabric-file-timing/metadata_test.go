package main

import (
	"testing"
	"chaincode-go-bpmn/chaincode"
	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

func TestGeneratedContractMetadata(t *testing.T) {
	if _, err := contractapi.NewChaincode(&chaincode.SmartContract{}); err != nil {
		t.Fatal(err)
	}
}
