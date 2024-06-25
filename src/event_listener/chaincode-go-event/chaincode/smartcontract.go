package chaincode

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

// SmartContract provides functions for managing an Asset
type SmartContract struct {
	contractapi.Contract
}

// Asset describes basic details of what makes up a simple asset
// Insert struct field in alphabetic order => to achieve determinism across languages
// golang keeps the order when marshal to json but doesn't order automatically
type Asset struct {
	AppraisedValue int    `json:"AppraisedValue"`
	Color          string `json:"Color"`
	ID             string `json:"ID"`
	Owner          string `json:"Owner"`
	Size           int    `json:"Size"`
}

// CreateAsset issues a new asset to the world state with given details.
func (s *SmartContract) CreateAsset(ctx contractapi.TransactionContextInterface, id string, color string, size int, owner string, appraisedValue int) error {
	existing, err := s.readState(ctx, id)
	if err == nil && existing != nil {
		return fmt.Errorf("the asset %s already exists", id)
	}

	asset := Asset{
		ID:             id,
		Color:          color,
		Size:           size,
		Owner:          owner,
		AppraisedValue: appraisedValue,
	}
	assetJSON, err := json.Marshal(asset)
	if err != nil {
		return err
	}

	ctx.GetStub().SetEvent("CreateAsset", assetJSON)
	return ctx.GetStub().PutState(id, assetJSON)
}

func (s *SmartContract) readState(ctx contractapi.TransactionContextInterface, id string) ([]byte, error) {
	assetJSON, err := ctx.GetStub().GetState(id)
	if err != nil {
		return nil, fmt.Errorf("failed to read from world state: %w", err)
	}
	if assetJSON == nil {
		return nil, fmt.Errorf("the asset %s does not exist", id)
	}

	return assetJSON, nil
}

// ReadAsset returns the asset stored in the world state with given id.
func (s *SmartContract) ReadAsset(ctx contractapi.TransactionContextInterface, id string) (*Asset, error) {
	assetJSON, err := s.readState(ctx, id)
	if err != nil {
		return nil, err
	}

	var asset Asset
	err = json.Unmarshal(assetJSON, &asset)
	if err != nil {
		return nil, err
	}

	return &asset, nil
}

// UpdateAsset updates an existing asset in the world state with provided parameters.
func (s *SmartContract) UpdateAsset(ctx contractapi.TransactionContextInterface, id string, color string, size int, owner string, appraisedValue int) error {
	_, err := s.readState(ctx, id)
	if err != nil {
		return err
	}

	// overwriting original asset with new asset
	asset := Asset{
		ID:             id,
		Color:          color,
		Size:           size,
		Owner:          owner,
		AppraisedValue: appraisedValue,
	}
	assetJSON, err := json.Marshal(asset)
	if err != nil {
		return err
	}

	ctx.GetStub().SetEvent("UpdateAsset", assetJSON)
	return ctx.GetStub().PutState(id, assetJSON)
}

// DeleteAsset deletes an given asset from the world state.
func (s *SmartContract) DeleteAsset(ctx contractapi.TransactionContextInterface, id string) error {
	assetJSON, err := s.readState(ctx, id)
	if err != nil {
		return err
	}

	ctx.GetStub().SetEvent("DeleteAsset", assetJSON)
	return ctx.GetStub().DelState(id)
}

// TransferAsset updates the owner field of asset with given id in world state, and returns the old owner.
func (s *SmartContract) TransferAsset(ctx contractapi.TransactionContextInterface, id string, newOwner string) (string, error) {
	asset, err := s.ReadAsset(ctx, id)
	if err != nil {
		return "", err
	}

	oldOwner := asset.Owner
	asset.Owner = newOwner

	assetJSON, err := json.Marshal(asset)
	if err != nil {
		return "", err
	}

	ctx.GetStub().SetEvent("TransferAsset", assetJSON)
	err = ctx.GetStub().PutState(id, assetJSON)
	if err != nil {
		return "", err
	}

	return oldOwner, nil
}

// DMNContentRecord describes a simple asset to be stored in the ledger
type DMNContentRecord struct {
	ID   string `json:"id"`
	Hash string `json:"hash"`
	Cid  string `json:"cid"`
}

// CreateDMNContent adds a new DMNContentRecord to the ledger and emits an event
func (s *SmartContract) CreateDMNContent(ctx contractapi.TransactionContextInterface, id string, dmnContent string) error {
	hashString, _ := s.hashXML(ctx, dmnContent)
	fmt.Print(hashString)

	record := DMNContentRecord{
		ID:   id,
		Hash: hashString,
	}

	recordAsBytes, err := json.Marshal(record)
	if err != nil {
		return fmt.Errorf("failed to marshal DMNContentRecord: %v", err)
	}

	err = ctx.GetStub().PutState(id, recordAsBytes)
	if err != nil {
		return fmt.Errorf("failed to put state: %v", err)
	}

	eventPayload := map[string]string{
		"ID":         id,
		"DMNContent": dmnContent,
	}

	eventPayloadAsBytes, err := json.Marshal(eventPayload)
	if err != nil {
		return fmt.Errorf("failed to marshal event payload: %v", err)
	}

	err = ctx.GetStub().SetEvent("DMNContentCreated", eventPayloadAsBytes)
	if err != nil {
		return fmt.Errorf("failed to set event: %v", err)
	}

	return nil
}

// HashXML calculates the SHA-256 hash of the provided XML string
func (s *SmartContract) hashXML(ctx contractapi.TransactionContextInterface, xmlString string) (string, error) {
	// Calculate SHA-256 hash
	hash := sha256.New()
	hash.Write([]byte(xmlString))
	hashInBytes := hash.Sum(nil)
	hashString := hex.EncodeToString(hashInBytes)
	fmt.Print(hashString)
	return hashString, nil
}

// UpdateCid updates the Cid field of the DMNContentRecord with the given id
func (s *SmartContract) UpdateCid(ctx contractapi.TransactionContextInterface, id string, cid string) error {
	// Retrieve the DMNContentRecord from the ledger using the ID
	recordJSON, err := ctx.GetStub().GetState(id)
	if err != nil {
		return fmt.Errorf("failed to read from world state: %v", err)
	}
	if recordJSON == nil {
		return fmt.Errorf("the record %s does not exist", id)
	}

	// Unmarshal the JSON to a DMNContentRecord struct
	var record DMNContentRecord
	err = json.Unmarshal(recordJSON, &record)
	if err != nil {
		return fmt.Errorf("failed to unmarshal JSON: %v", err)
	}

	// Update the Cid field
	record.Cid = cid

	// Marshal the updated struct to JSON
	recordJSON, err = json.Marshal(record)
	if err != nil {
		return fmt.Errorf("failed to marshal JSON: %v", err)
	}

	// Put the updated record back into the ledger
	err = ctx.GetStub().PutState(id, recordJSON)
	if err != nil {
		return fmt.Errorf("failed to update record in world state: %v", err)
	}

	return nil
}

// QueryDMNContentRecord retrieves a DMNContentRecord from the ledger by ID
func (s *SmartContract) QueryDMNContentRecord(ctx contractapi.TransactionContextInterface, id string) (*DMNContentRecord, error) {
	// Retrieve the DMNContentRecord from the ledger using the ID
	recordJSON, err := ctx.GetStub().GetState(id)
	if err != nil {
		return nil, fmt.Errorf("failed to read from world state: %v", err)
	}
	if recordJSON == nil {
		return nil, fmt.Errorf("the record %s does not exist", id)
	}

	// Unmarshal the JSON to a DMNContentRecord struct
	var record DMNContentRecord
	err = json.Unmarshal(recordJSON, &record)
	if err != nil {
		return nil, fmt.Errorf("failed to unmarshal JSON: %v", err)
	}

	return &record, nil
}
