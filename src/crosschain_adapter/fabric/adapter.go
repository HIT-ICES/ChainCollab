package main

import (
	"crypto/ecdsa"
	"crypto/sha256"
	"crypto/x509"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"math/big"
	"strconv"
	"time"

	"github.com/hyperledger/fabric-chaincode-go/shim"
	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

type SmartContract struct {
	contractapi.Contract
}

type AdapterConfig struct {
	ChainID   string `json:"chainId"`
	Threshold int    `json:"threshold"`
}

type RelayInfo struct {
	ID     string `json:"id"`
	PubKey string `json:"pubKey"`
	Active bool   `json:"active"`
}

type RelaySignature struct {
	RelayID   string `json:"relayId"`
	Signature string `json:"signature"`
}

type MessagePayload struct {
	Adapter         string `json:"adapter"`
	SrcChainID      string `json:"srcChainId"`
	DstChainID      string `json:"dstChainId"`
	Nonce           string `json:"nonce"`
	TargetChaincode string `json:"targetChaincode"`
	Channel         string `json:"channel"`
	Function        string `json:"function"`
	ArgsHash        string `json:"argsHash"`
}

type CallResult struct {
	MessageID string `json:"messageId"`
	Success   bool   `json:"success"`
	Payload   string `json:"payload"`
	Error     string `json:"error"`
	Timestamp int64  `json:"timestamp"`
}

const (
	configKey      = "xcall::config"
	relayKeyPrefix = "xcall::relay::"
	resultPrefix   = "xcall::result::"
)

func (s *SmartContract) SetConfig(ctx contractapi.TransactionContextInterface, chainID string, threshold string) error {
	if threshold == "" {
		return errors.New("threshold is required")
	}
	th, err := strconv.Atoi(threshold)
	if err != nil || th <= 0 {
		return fmt.Errorf("invalid threshold: %v", err)
	}
	cfg := AdapterConfig{
		ChainID:   chainID,
		Threshold: th,
	}
	return putStateJSON(ctx, configKey, &cfg)
}

func (s *SmartContract) RegisterRelay(ctx contractapi.TransactionContextInterface, relayID string, pubKeyBase64 string) error {
	if relayID == "" {
		return errors.New("relayID is required")
	}
	if pubKeyBase64 == "" {
		return errors.New("pubKey is required")
	}
	relay := &RelayInfo{ID: relayID, PubKey: pubKeyBase64, Active: true}
	return putStateJSON(ctx, relayKeyPrefix+relayID, relay)
}

func (s *SmartContract) DisableRelay(ctx contractapi.TransactionContextInterface, relayID string) error {
	relay, err := getRelay(ctx, relayID)
	if err != nil {
		return err
	}
	relay.Active = false
	return putStateJSON(ctx, relayKeyPrefix+relayID, relay)
}

func (s *SmartContract) ReceiveCrossChainCall(
	ctx contractapi.TransactionContextInterface,
	srcChainID string,
	dstChainID string,
	nonce string,
	targetChaincode string,
	channel string,
	functionName string,
	argsJSON string,
	signaturesJSON string,
) (string, error) {
	cfg, err := getConfig(ctx)
	if err != nil {
		return "", err
	}
	if cfg.ChainID != "" && dstChainID != cfg.ChainID {
		return "", fmt.Errorf("wrong destination chain: %s", dstChainID)
	}
	if targetChaincode == "" || functionName == "" {
		return "", errors.New("targetChaincode and functionName are required")
	}

	argsHash := sha256.Sum256([]byte(argsJSON))
	payload := MessagePayload{
		Adapter:         "fabric-crosschain-adapter",
		SrcChainID:      srcChainID,
		DstChainID:      dstChainID,
		Nonce:           nonce,
		TargetChaincode: targetChaincode,
		Channel:         channel,
		Function:        functionName,
		ArgsHash:        hex.EncodeToString(argsHash[:]),
	}
	payloadBytes, err := json.Marshal(payload)
	if err != nil {
		return "", fmt.Errorf("marshal payload failed: %v", err)
	}
	messageHash := sha256.Sum256(payloadBytes)
	messageID := hex.EncodeToString(messageHash[:])

	exists, err := stateExists(ctx, resultPrefix+messageID)
	if err != nil {
		return "", err
	}
	if exists {
		return "", fmt.Errorf("message %s already processed", messageID)
	}

	if err := verifyThreshold(ctx, messageHash[:], signaturesJSON, cfg.Threshold); err != nil {
		return "", err
	}

	args, err := decodeArgs(functionName, argsJSON)
	if err != nil {
		return "", err
	}

	response := ctx.GetStub().InvokeChaincode(targetChaincode, args, channel)
	success := response.Status == shim.OK
	payloadBase64 := base64.StdEncoding.EncodeToString(response.Payload)
	result := CallResult{
		MessageID: messageID,
		Success:   success,
		Payload:   payloadBase64,
		Error:     response.Message,
		Timestamp: time.Now().Unix(),
	}
	if err := putStateJSON(ctx, resultPrefix+messageID, &result); err != nil {
		return "", err
	}
	if !success {
		return messageID, fmt.Errorf("invoke failed: %s", response.Message)
	}
	return messageID, nil
}

func (s *SmartContract) GetResult(ctx contractapi.TransactionContextInterface, messageID string) (string, error) {
	if messageID == "" {
		return "", errors.New("messageID is required")
	}
	b, err := ctx.GetStub().GetState(resultPrefix + messageID)
	if err != nil {
		return "", err
	}
	if b == nil {
		return "", fmt.Errorf("result %s not found", messageID)
	}
	return string(b), nil
}

func decodeArgs(functionName string, argsJSON string) ([][]byte, error) {
	args := [][]byte{[]byte(functionName)}
	if argsJSON == "" {
		return args, nil
	}
	var argsB64 []string
	if err := json.Unmarshal([]byte(argsJSON), &argsB64); err != nil {
		return nil, fmt.Errorf("invalid argsJSON: %v", err)
	}
	for _, item := range argsB64 {
		decoded, err := base64.StdEncoding.DecodeString(item)
		if err != nil {
			return nil, fmt.Errorf("invalid arg base64: %v", err)
		}
		args = append(args, decoded)
	}
	return args, nil
}

func verifyThreshold(
	ctx contractapi.TransactionContextInterface,
	message []byte,
	signaturesJSON string,
	threshold int,
) error {
	if threshold <= 0 {
		return errors.New("threshold not configured")
	}
	var sigs []RelaySignature
	if err := json.Unmarshal([]byte(signaturesJSON), &sigs); err != nil {
		return fmt.Errorf("invalid signaturesJSON: %v", err)
	}
	if len(sigs) < threshold {
		return errors.New("not enough signatures")
	}

	seen := make(map[string]bool)
	validCount := 0
	for _, sig := range sigs {
		if sig.RelayID == "" || sig.Signature == "" {
			continue
		}
		if seen[sig.RelayID] {
			continue
		}
		relay, err := getRelay(ctx, sig.RelayID)
		if err != nil {
			continue
		}
		if !relay.Active {
			continue
		}
		if err := verifySignature(relay.PubKey, message, sig.Signature); err != nil {
			continue
		}
		seen[sig.RelayID] = true
		validCount += 1
		if validCount >= threshold {
			return nil
		}
	}
	return errors.New("insufficient valid signatures")
}

func verifySignature(pubKeyBase64 string, message []byte, sigBase64 string) error {
	der, err := base64.StdEncoding.DecodeString(pubKeyBase64)
	if err != nil {
		return fmt.Errorf("invalid pubkey base64: %v", err)
	}
	pub, err := x509.ParsePKIXPublicKey(der)
	if err != nil {
		return fmt.Errorf("parse pubkey failed: %v", err)
	}
	ecdsaKey, ok := pub.(*ecdsa.PublicKey)
	if !ok {
		return errors.New("pubkey is not ECDSA")
	}
	sigBytes, err := base64.StdEncoding.DecodeString(sigBase64)
	if err != nil {
		return fmt.Errorf("invalid signature base64: %v", err)
	}
	if len(sigBytes) != 64 {
		return errors.New("signature must be 64 bytes (r||s)")
	}
	r := new(big.Int).SetBytes(sigBytes[:32])
	s := new(big.Int).SetBytes(sigBytes[32:])
	if !ecdsa.Verify(ecdsaKey, message, r, s) {
		return errors.New("verify failed")
	}
	return nil
}

func getRelay(ctx contractapi.TransactionContextInterface, relayID string) (*RelayInfo, error) {
	b, err := ctx.GetStub().GetState(relayKeyPrefix + relayID)
	if err != nil {
		return nil, err
	}
	if b == nil {
		return nil, fmt.Errorf("relay %s not found", relayID)
	}
	var relay RelayInfo
	if err := json.Unmarshal(b, &relay); err != nil {
		return nil, err
	}
	return &relay, nil
}

func getConfig(ctx contractapi.TransactionContextInterface) (*AdapterConfig, error) {
	b, err := ctx.GetStub().GetState(configKey)
	if err != nil {
		return nil, err
	}
	if b == nil {
		return &AdapterConfig{ChainID: "", Threshold: 0}, nil
	}
	var cfg AdapterConfig
	if err := json.Unmarshal(b, &cfg); err != nil {
		return nil, err
	}
	return &cfg, nil
}

func putStateJSON(ctx contractapi.TransactionContextInterface, key string, value interface{}) error {
	b, err := json.Marshal(value)
	if err != nil {
		return err
	}
	return ctx.GetStub().PutState(key, b)
}

func stateExists(ctx contractapi.TransactionContextInterface, key string) (bool, error) {
	b, err := ctx.GetStub().GetState(key)
	if err != nil {
		return false, err
	}
	return b != nil, nil
}

func main() {
	chaincode, err := contractapi.NewChaincode(new(SmartContract))
	if err != nil {
		panic(fmt.Sprintf("Error creating chaincode: %v", err))
	}
	if err := chaincode.Start(); err != nil {
		panic(fmt.Sprintf("Error starting chaincode: %v", err))
	}
}
