package main

import (
	"erc5521/chaincode"

	"github.com/hyperledger/fabric-contract-api-go/v2/contractapi"
)

func main() {
	smartContract := new(chaincode.SmartContract)

	cc, err := contractapi.NewChaincode(smartContract)

	if err != nil {
		panic(err.Error())
	}

	if err := cc.Start(); err != nil {
		panic(err.Error())
	}
}
