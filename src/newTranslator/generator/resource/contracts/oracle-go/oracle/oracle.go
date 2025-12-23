package oracle

import (
	"encoding/json"
	"fmt"

	"github.com/golang/protobuf/ptypes/timestamp"
	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

// A Contract For Storage Data in Fabric Chain, support CRUD operations
// Every Contract using this Contract with a specific key to divide the data space. then a key-value pair will be stored in the chain

// V1.0 without Access Control and anything else, just set and read
type Oracle struct {
	contractapi.Contract
}

type DataType string

const (
	STRING  DataType = "STRING"
	JSON    DataType = "JSON"
	INTEGER DataType = "INTEGER"
	BOOLEAN DataType = "BOOLEAN"
)

type DataItem struct {
	Key       string              `json:"key"`
	Value     string              `json:"value"`
	Type      DataType            `json:"type"`
	TimeStamp timestamp.Timestamp `json:"timeStamp"`
}

// Register and return the access key for the data space

func getDataTypeFromString(s string) DataType {
	switch s {
	case "STRING":
		return STRING
	case "JSON":
		return JSON
	case "INTEGER":
		return INTEGER
	case "BOOLEAN":
		return BOOLEAN
	default:
		return STRING
	}
}

// What's the function Oracle Want to offer?
// 1. get data immediately
// 	a. the static data saved in oracle contract
//  b. const subscription data from off-chain
// 2. make a request and wait for response
// for 1, use GetDataItem; for 2, use MakeRequest

func (oracle *Oracle) SetDataItem(ctx contractapi.TransactionContextInterface, accessKey string, key string, value string, dataType string) error {
	txTime, err := ctx.GetStub().GetTxTimestamp()
	if err != nil {
		return err
	}

	dataItem := DataItem{
		Key:   key,
		Value: value,
		Type:  getDataTypeFromString(dataType),
		TimeStamp: timestamp.Timestamp{
			Seconds: txTime.Seconds,
			Nanos:   txTime.Nanos,
		},
	}
	// if equal [], set as {}
	dataSpaceJson, err := ctx.GetStub().GetState(accessKey)
	if len(dataSpaceJson) == 0 {
		dataSpaceJson = []byte("{}")
	}

	fmt.Print(dataSpaceJson)
	if err != nil {
		return err
	}

	dataSpace := make(map[string]DataItem)
	err = json.Unmarshal(dataSpaceJson, &dataSpace)

	if err != nil {
		return err
	}

	dataSpace[key] = dataItem

	dataSpaceJson, err = json.Marshal(dataSpace)

	if err != nil {
		return err
	}

	return ctx.GetStub().PutState(accessKey, dataSpaceJson)

}

func (oracle *Oracle) GetDataItem(ctx contractapi.TransactionContextInterface, accessKey string, key string) (*DataItem, error) {
	dataSpaceJson, err := ctx.GetStub().GetState(accessKey)
	if err != nil {
		return nil, err
	}

	dataSpace := make(map[string]DataItem)
	err = json.Unmarshal(dataSpaceJson, &dataSpace)

	if err != nil {
		return nil, err
	}

	dataItem, ok := dataSpace[key]

	if !ok {
		return nil, nil
	}

	return &dataItem, nil
}

// TODO:
// Define the data source and the way to get it, should be decide ahead

func (oracle *Oracle) RequestDataItem(ctx contractapi.TransactionContextInterface, accessKey string, dataId string, fullfilledMethod string) error {
	// TODO
	// get the data and call the callback function
	return nil
}
