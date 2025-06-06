package chaincode_test

import (
	"chaincode-go-bpmn/chaincode"
	"chaincode-go-bpmn/chaincode/mocks"
	"encoding/json"
	"fmt"
	"github.com/hyperledger/fabric-chaincode-go/shim"
	"github.com/hyperledger/fabric-contract-api-go/contractapi"
	"github.com/hyperledger/fabric-protos-go/ledger/queryresult"
	"github.com/stretchr/testify/require"
	"testing"
)

//go:generate counterfeiter -o mocks/transaction.go -fake-name TransactionContext . transactionContext
type transactionContext interface {
	contractapi.TransactionContextInterface
}

//go:generate counterfeiter -o mocks/chaincodestub.go -fake-name ChaincodeStub . chaincodeStub
type chaincodeStub interface {
	shim.ChaincodeStubInterface
}

//go:generate counterfeiter -o mocks/statequeryiterator.go -fake-name StateQueryIterator . stateQueryIterator
type stateQueryIterator interface {
	shim.StateQueryIteratorInterface
}

func TestInitLedger(t *testing.T) {
	chaincodeStub := &mocks.ChaincodeStub{}
	transactionContext := &mocks.TransactionContext{}
	transactionContext.GetStubReturns(chaincodeStub)

	assetTransfer := chaincode.SmartContract{}
	err := assetTransfer.InitLedger(transactionContext)
	require.NoError(t, err)

	chaincodeStub.PutStateReturns(fmt.Errorf("failed inserting key"))
	err = assetTransfer.InitLedger(transactionContext)
	require.EqualError(t, err, "Chaincode has already been initialized")
}

func TestCreateMessage(t *testing.T) {
	chaincodeStub := &mocks.ChaincodeStub{}
	transactionContext := &mocks.TransactionContext{}
	transactionContext.GetStubReturns(chaincodeStub)

	assetTransfer := chaincode.SmartContract{}
	_, err := assetTransfer.CreateMessage(transactionContext, "", "", "", "", 0)
	require.NoError(t, err)

	chaincodeStub.GetStateReturns([]byte{}, nil)
	_, err = assetTransfer.CreateMessage(transactionContext, "message1", "", "", "", 0)
	require.EqualError(t, err, "消息 message1 已存在")

	chaincodeStub.GetStateReturns(nil, fmt.Errorf("unable to retrieve asset"))
	_, err = assetTransfer.CreateMessage(transactionContext, "asset1", "", "", "", 0)
	require.EqualError(t, err, "获取状态数据时出错: unable to retrieve asset")
}

func TestReadMessage(t *testing.T) {
	chaincodeStub := &mocks.ChaincodeStub{}
	transactionContext := &mocks.TransactionContext{}
	transactionContext.GetStubReturns(chaincodeStub)

	expectedAsset := &chaincode.Message{MessageID: "asset1"}
	bytes, err := json.Marshal(expectedAsset)
	require.NoError(t, err)

	chaincodeStub.GetStateReturns(bytes, nil)
	messageTransfer := chaincode.SmartContract{}
	asset, err := messageTransfer.ReadMsg(transactionContext, "")
	require.NoError(t, err)
	require.Equal(t, expectedAsset, asset)

	chaincodeStub.GetStateReturns(nil, fmt.Errorf("unable to retrieve asset"))
	_, err = messageTransfer.ReadMsg(transactionContext, "")
	require.EqualError(t, err, "unable to retrieve asset")

	chaincodeStub.GetStateReturns(nil, nil)
	asset, err = messageTransfer.ReadMsg(transactionContext, "msg1")
	require.EqualError(t, err, "Message msg1 does not exist")
	require.Nil(t, asset)
}

func TestGetAllMessages(t *testing.T) {
	asset := &chaincode.Message{MessageID: "asset1"}
	bytes, err := json.Marshal(asset)
	require.NoError(t, err)

	iterator := &mocks.StateQueryIterator{}
	iterator.HasNextReturnsOnCall(0, true)
	iterator.HasNextReturnsOnCall(1, false)
	iterator.NextReturns(&queryresult.KV{Value: bytes}, nil)

	chaincodeStub := &mocks.ChaincodeStub{}
	transactionContext := &mocks.TransactionContext{}
	transactionContext.GetStubReturns(chaincodeStub)

	chaincodeStub.GetStateByRangeReturns(iterator, nil)
	messageTransfer := &chaincode.SmartContract{}
	messages, err := messageTransfer.GetAllMessages(transactionContext)
	require.NoError(t, err)
	require.Equal(t, []*chaincode.Message{asset}, messages)

	iterator.HasNextReturns(true)
	iterator.NextReturns(nil, fmt.Errorf("failed retrieving next item"))
	messages, err = messageTransfer.GetAllMessages(transactionContext)
	require.EqualError(t, err, "迭代状态数据时出错: failed retrieving next item")
	require.Nil(t, messages)

	chaincodeStub.GetStateByRangeReturns(nil, fmt.Errorf("failed retrieving all messages"))
	messages, err = messageTransfer.GetAllMessages(transactionContext)
	require.EqualError(t, err, "获取状态数据时出错: failed retrieving all messages")
	require.Nil(t, messages)
}
