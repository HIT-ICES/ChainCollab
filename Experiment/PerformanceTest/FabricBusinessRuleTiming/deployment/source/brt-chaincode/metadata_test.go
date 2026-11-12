package main
import("testing";"chaincode-go-bpmn/chaincode";"github.com/hyperledger/fabric-contract-api-go/contractapi")
func TestMetadata(t *testing.T){if _,e:=contractapi.NewChaincode(&chaincode.SmartContract{});e!=nil{t.Fatal(e)}}
