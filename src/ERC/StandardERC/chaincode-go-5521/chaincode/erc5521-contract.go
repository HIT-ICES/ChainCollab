package chaincode

import (
	"encoding/base64"
	"encoding/binary"
	"encoding/json"
	"errors"
	"fmt"

	"github.com/hyperledger/fabric-contract-api-go/v2/contractapi"
)

const nameKey = "name"
const symbolKey = "symbol"
const RelationshipKey = "relationship"
const chaincodeNameKey = "chaincodeName"

const balancePrefix = "balance"
const nftPrefix = "nft"
const approvalPrefix = "approval"
const ChaincodeOk int32 = 200

type SmartContract struct {
	contractapi.Contract
}

// 当 rNFT 中的节点被引用和更改时记录。
// @notice 当 `node`（即 rNFT）更改时发出事件。
type UpdataNode struct {
	TokenId               string     `Json:"tokenid"`
	Owneraccount          string     `Json:"owneraccount"`
	AddressRefferingList  []string   `Json:"addressRefferingList"`
	TokenIdsRefferingList [][]uint64 `json:"tokenIdsRefferingList"`
	AddressRefferedList   []string   `json:"addressRefferedList"`
	TokenIDsRefferedList  [][]uint64 `json:"tokenIDsRefferedList"`
}

type Relationship struct {
	Reffering        map[string][]string `json:"reffering"`
	Reffered         map[string][]string `json:"reffered"`
	RefferingKeys    []string            `json:"refferingKeys"`
	RefferedKeys     []string            `json:"refferedKeys"`
	CreatedTimestamp uint64              `json:"createdTimestamp"`
}

// ERC721基础
type InstanceMintAuthority struct {
	InstanceID  string   `json:"instance_id"`
	AllowedMSPs []string `json:"allowed_msps"`
}

func (s *SmartContract) AddMintAuthority(ctx contractapi.TransactionContextInterface, instanceID string, allowedMSPs []string) error {
	//test
	// id, err := ctx.GetClientIdentity().GetID()
	// fmt.Println("ctx.GetClientIdentity().GetID() ----" + id)
	// fmt.Println(base64decoding(id))

	key := "instance_auth_" + instanceID
	authority := InstanceMintAuthority{
		InstanceID:  instanceID,
		AllowedMSPs: allowedMSPs,
	}

	data, err := json.Marshal(authority)
	if err != nil {
		return err
	}

	return ctx.GetStub().PutState(key, data)
}

func (s *SmartContract) authorizationHelper(ctx contractapi.TransactionContextInterface, instanceID string) error {

	clientMSPID, err := ctx.GetClientIdentity().GetMSPID()
	if err != nil {
		return fmt.Errorf("failed to get clientMSPID: %v", err)
	}

	key := "instance_auth_" + instanceID
	authJSON, err := ctx.GetStub().GetState(key)
	if err != nil || authJSON == nil {
		return fmt.Errorf("no mint authority found for instance %s", instanceID)
	}

	var auth InstanceMintAuthority
	_ = json.Unmarshal(authJSON, &auth)

	allowed := false
	for _, msp := range auth.AllowedMSPs {
		if msp == clientMSPID {
			allowed = true
			break
		}
	}

	if !allowed {
		return fmt.Errorf("MSP %s not authorized to mint for instance %s", clientMSPID, instanceID)
	}

	return nil
}

func (c *SmartContract) Initialize(ctx contractapi.TransactionContextInterface, name string, symbol string) (bool, error) {
	bytes, err := ctx.GetStub().GetState(nameKey)
	if err != nil {
		return false, fmt.Errorf("failed to get Name: %v", err)
	}
	if bytes != nil {
		return false, fmt.Errorf("contract options are already set, client is not authorized to change them")
	}
	err = ctx.GetStub().PutState(nameKey, []byte(name))
	if err != nil {
		return false, fmt.Errorf("failed to set token name: %v", err)
	}
	err = ctx.GetStub().PutState(symbolKey, []byte(symbol))
	if err != nil {
		return false, fmt.Errorf("failed to set token symbol: %v", err)
	}
	return true, nil
}

func _readNFT(ctx contractapi.TransactionContextInterface, tokenId string) (*Nft, error) {
	nftKey, err := ctx.GetStub().CreateCompositeKey(nftPrefix, []string{tokenId})
	if err != nil {
		return nil, fmt.Errorf("failed to CreateCompositeKey %s: %v", tokenId, err)
	}

	nftBytes, err := ctx.GetStub().GetState(nftKey)
	if err != nil {
		return nil, fmt.Errorf("failed to GetState %s: %v", tokenId, err)
	}

	nft := new(Nft)
	err = json.Unmarshal(nftBytes, nft)
	if err != nil {
		return nil, fmt.Errorf("failed to Unmarshal nftBytes: %v", err)
	}

	return nft, nil
}

func _nftExists(ctx contractapi.TransactionContextInterface, tokenId string) bool {
	nftKey, err := ctx.GetStub().CreateCompositeKey(nftPrefix, []string{tokenId})
	if err != nil {
		panic("error creating CreateCompositeKey:" + err.Error())
	}

	nftBytes, err := ctx.GetStub().GetState(nftKey)
	if err != nil {
		panic("error GetState nftBytes:" + err.Error())
	}

	return len(nftBytes) > 0
}

// BalanceOf counts all non-fungible tokens assigned to an owner
// param owner {String} An owner for whom to query the balance
// returns {int} The number of non-fungible tokens owned by the owner, possibly zero
func (c *SmartContract) BalanceOf(ctx contractapi.TransactionContextInterface, owner string) int {

	// Check if contract has been intilized first
	initialized, err := checkInitialized(ctx)
	if err != nil {
		panic("failed to check if contract is already initialized:" + err.Error())
	}
	if !initialized {
		panic("Contract options need to be set before calling any function, call Initialize() to initialize contract")
	}

	// There is a key record for every non-fungible token in the format of balancePrefix.owner.tokenId.
	// BalanceOf() queries for and counts all records matching balancePrefix.owner.*

	iterator, err := ctx.GetStub().GetStateByPartialCompositeKey(balancePrefix, []string{owner})
	if err != nil {
		panic("Error creating asset chaincode:" + err.Error())
	}

	// Count the number of returned composite keys
	balance := 0
	for iterator.HasNext() {
		_, err := iterator.Next()
		if err != nil {
			return 0
		}
		balance++

	}
	return balance
}

// OwnerOf finds the owner of a non-fungible token
// param {String} tokenId The identifier for a non-fungible token
// returns {String} Return the owner of the non-fungible token
func (c *SmartContract) OwnerOf(ctx contractapi.TransactionContextInterface, tokenId string) (string, error) {

	// Check if contract has been intilized first
	initialized, err := checkInitialized(ctx)
	if err != nil {
		return "", fmt.Errorf("failed to check if contract is already initialized: %v", err)
	}
	if !initialized {
		return "", errors.New("contract options need to be set before calling any function, call Initialize() to initialize contract")
	}

	nft, err := _readNFT(ctx, tokenId)
	if err != nil {
		return "", fmt.Errorf("could not process OwnerOf for tokenId: %w", err)
	}

	return nft.Owner, nil
}

// Approve changes or reaffirms the approved client for a non-fungible token
// param {String} operator The new approved client
// param {String} tokenId the non-fungible token to approve
// returns {Boolean} Return whether the approval was successful or not
func (c *SmartContract) Approve(ctx contractapi.TransactionContextInterface, operator string, tokenId string) (bool, error) {

	// Check if contract has been intilized first
	initialized, err := checkInitialized(ctx)
	if err != nil {
		return false, fmt.Errorf("failed to check if contract is already initialized: %v", err)
	}
	if !initialized {
		return false, errors.New("contract options need to be set before calling any function, call Initialize() to initialize contract")
	}

	sender64, err := ctx.GetClientIdentity().GetID()
	if err != nil {
		return false, fmt.Errorf("failed to GetClientIdentity: %v", err)
	}

	senderBytes, err := base64.StdEncoding.DecodeString(sender64)
	if err != nil {
		return false, fmt.Errorf("failed to DecodeString senderBytes: %v", err)
	}
	sender := string(senderBytes)

	nft, err := _readNFT(ctx, tokenId)
	if err != nil {
		return false, fmt.Errorf("failed to _readNFT: %v", err)
	}

	// Check if the sender is the current owner of the non-fungible token
	// or an authorized operator of the current owner
	owner := nft.Owner
	operatorApproval, err := c.IsApprovedForAll(ctx, owner, sender)
	if err != nil {
		return false, fmt.Errorf("failed to get IsApprovedForAll: %v", err)
	}
	if owner != sender && !operatorApproval {
		return false, errors.New("the sender is not the current owner nor an authorized operator")
	}

	// Update the approved operator of the non-fungible token
	nft.Approved = operator
	nftKey, err := ctx.GetStub().CreateCompositeKey(nftPrefix, []string{tokenId})
	if err != nil {
		return false, fmt.Errorf("failed to CreateCompositeKey %s: %v", nftKey, err)
	}

	nftBytes, err := json.Marshal(nft)
	if err != nil {
		return false, fmt.Errorf("failed to marshal nftBytes: %v", err)
	}

	err = ctx.GetStub().PutState(nftKey, nftBytes)
	if err != nil {
		return false, fmt.Errorf("failed to PutState for nftKey: %v", err)
	}

	return true, nil
}

// SetApprovalForAll enables or disables approval for a third party ("operator")
// to manage all the message sender's assets
// param {String} operator A client to add to the set of authorized operators
// param {Boolean} approved True if the operator is approved, false to revoke approval
// returns {Boolean} Return whether the approval was successful or not
func (c *SmartContract) SetApprovalForAll(ctx contractapi.TransactionContextInterface, operator string, approved bool) (bool, error) {

	// Check if contract has been intilized first
	initialized, err := checkInitialized(ctx)
	if err != nil {
		return false, fmt.Errorf("failed to check if contract is already initialized: %v", err)
	}
	if !initialized {
		return false, errors.New("contract options need to be set before calling any function, call Initialize() to initialize contract")
	}

	sender64, err := ctx.GetClientIdentity().GetID()
	if err != nil {
		return false, fmt.Errorf("failed to GetClientIdentity: %v", err)
	}

	senderBytes, err := base64.StdEncoding.DecodeString(sender64)
	if err != nil {
		return false, fmt.Errorf("failed to DecodeString sender: %v", err)
	}
	sender := string(senderBytes)

	nftApproval := new(Approval)
	nftApproval.Owner = sender
	nftApproval.Operator = operator
	nftApproval.Approved = approved

	approvalKey, err := ctx.GetStub().CreateCompositeKey(approvalPrefix, []string{sender, operator})
	if err != nil {
		return false, fmt.Errorf("failed to CreateCompositeKey: %v", err)
	}

	approvalBytes, err := json.Marshal(nftApproval)
	if err != nil {
		return false, fmt.Errorf("failed to marshal approvalBytes: %v", err)
	}

	err = ctx.GetStub().PutState(approvalKey, approvalBytes)
	if err != nil {
		return false, fmt.Errorf("failed to PutState approvalBytes: %v", err)
	}

	// Emit the ApprovalForAll event
	err = ctx.GetStub().SetEvent("ApprovalForAll", approvalBytes)
	if err != nil {
		return false, fmt.Errorf("failed to SetEvent ApprovalForAll: %v", err)
	}

	return true, nil
}

// IsApprovedForAll returns if a client is an authorized operator for another client
// param {String} owner The client that owns the non-fungible tokens
// param {String} operator The client that acts on behalf of the owner
// returns {Boolean} Return true if the operator is an approved operator for the owner, false otherwise
func (c *SmartContract) IsApprovedForAll(ctx contractapi.TransactionContextInterface, owner string, operator string) (bool, error) {

	// Check if contract has been intilized first
	initialized, err := checkInitialized(ctx)
	if err != nil {
		return false, fmt.Errorf("failed to check if contract is already initialized: %v", err)
	}
	if !initialized {
		return false, errors.New("contract options need to be set before calling any function, call Initialize() to initialize contract")
	}

	approvalKey, err := ctx.GetStub().CreateCompositeKey(approvalPrefix, []string{owner, operator})
	if err != nil {
		return false, fmt.Errorf("failed to CreateCompositeKey: %v", err)
	}
	approvalBytes, err := ctx.GetStub().GetState(approvalKey)
	if err != nil {
		return false, fmt.Errorf("failed to GetState approvalBytes %s: %v", approvalBytes, err)
	}

	if len(approvalBytes) < 1 {
		return false, nil
	}

	approval := new(Approval)
	err = json.Unmarshal(approvalBytes, approval)
	if err != nil {
		return false, fmt.Errorf("failed to Unmarshal: %v, string %s", err, string(approvalBytes))
	}

	return approval.Approved, nil

}

// GetApproved returns the approved client for a single non-fungible token
// param {String} tokenId the non-fungible token to find the approved client for
// returns {Object} Return the approved client for this non-fungible token, or null if there is none
func (c *SmartContract) GetApproved(ctx contractapi.TransactionContextInterface, tokenId string) (string, error) {

	// Check if contract has been intilized first
	initialized, err := checkInitialized(ctx)
	if err != nil {
		return "false", fmt.Errorf("failed to check if contract is already initialized: %v", err)
	}
	if !initialized {
		return "false", errors.New("contract options need to be set before calling any function, call Initialize() to initialize contract")
	}

	nft, err := _readNFT(ctx, tokenId)
	if err != nil {
		return "false", fmt.Errorf("failed GetApproved for tokenId : %v", err)
	}
	return nft.Approved, nil
}

// TransferFrom transfers the ownership of a non-fungible token
// from one owner to another owner
// param {String} from The current owner of the non-fungible token
// param {String} to The new owner
// param {String} tokenId the non-fungible token to transfer
// returns {Boolean} Return whether the transfer was successful or not

func (c *SmartContract) TransferFrom(ctx contractapi.TransactionContextInterface, from string, to string, tokenId string) (bool, error) {

	// Check if contract has been intilized first
	initialized, err := checkInitialized(ctx)
	if err != nil {
		return false, fmt.Errorf("failed to check if contract is already initialized: %v", err)
	}
	if !initialized {
		return false, errors.New("contract options need to be set before calling any function, call Initialize() to initialize contract")
	}

	// Get ID of submitting client identity
	sender64, err := ctx.GetClientIdentity().GetID()
	if err != nil {
		return false, fmt.Errorf("failed to GetClientIdentity: %v", err)
	}

	senderBytes, err := base64.StdEncoding.DecodeString(sender64)
	if err != nil {
		return false, fmt.Errorf("failed to DecodeString sender: %v", err)
	}
	sender := string(senderBytes)

	nft, err := _readNFT(ctx, tokenId)
	if err != nil {
		return false, fmt.Errorf("failed to _readNFT : %v", err)
	}

	owner := nft.Owner
	operator := nft.Approved
	operatorApproval, err := c.IsApprovedForAll(ctx, owner, sender)
	if err != nil {
		return false, fmt.Errorf("failed to get IsApprovedForAll : %v", err)
	}
	if owner != sender && operator != sender && !operatorApproval {
		return false, errors.New("the sender is not the current owner nor an authorized operator")
	}

	// Check if `from` is the current owner
	if owner != from {
		return false, errors.New("the from is not the current owner")
	}

	// Clear the approved client for this non-fungible token
	nft.Approved = ""

	// Overwrite a non-fungible token to assign a new owner.
	nft.Owner = to
	nftKey, err := ctx.GetStub().CreateCompositeKey(nftPrefix, []string{tokenId})
	if err != nil {
		return false, fmt.Errorf("failed to CreateCompositeKey: %v", err)
	}

	nftBytes, err := json.Marshal(nft)
	if err != nil {
		return false, fmt.Errorf("failed to marshal approval: %v", err)
	}

	err = ctx.GetStub().PutState(nftKey, nftBytes)
	if err != nil {
		return false, fmt.Errorf("failed to PutState nftBytes %s: %v", nftBytes, err)
	}

	// Remove a composite key from the balance of the current owner
	balanceKeyFrom, err := ctx.GetStub().CreateCompositeKey(balancePrefix, []string{from, tokenId})
	if err != nil {
		return false, fmt.Errorf("failed to CreateCompositeKey from: %v", err)
	}

	err = ctx.GetStub().DelState(balanceKeyFrom)
	if err != nil {
		return false, fmt.Errorf("failed to DelState balanceKeyFrom %s: %v", nftBytes, err)
	}

	// Save a composite key to count the balance of a new owner
	balanceKeyTo, err := ctx.GetStub().CreateCompositeKey(balancePrefix, []string{to, tokenId})
	if err != nil {
		return false, fmt.Errorf("failed to CreateCompositeKey to: %v", err)
	}
	err = ctx.GetStub().PutState(balanceKeyTo, []byte{0})
	if err != nil {
		return false, fmt.Errorf("failed to PutState balanceKeyTo %s: %v", balanceKeyTo, err)
	}

	// Emit the Transfer event
	transferEvent := new(Transfer)
	transferEvent.From = from
	transferEvent.To = to
	transferEvent.TokenId = tokenId

	transferEventBytes, err := json.Marshal(transferEvent)
	if err != nil {
		return false, fmt.Errorf("failed to marshal transferEventBytes: %v", err)
	}

	err = ctx.GetStub().SetEvent("Transfer", transferEventBytes)
	if err != nil {
		return false, fmt.Errorf("failed to SetEvent transferEventBytes %s: %v", transferEventBytes, err)
	}
	return true, nil
}

// ============== ERC721 metadata extension ===============

// Name returns a descriptive name for a collection of non-fungible tokens in this contract
// returns {String} Returns the name of the token

func (c *SmartContract) Name(ctx contractapi.TransactionContextInterface) (string, error) {

	// Check if contract has been intilized first
	initialized, err := checkInitialized(ctx)
	if err != nil {
		return "", fmt.Errorf("failed to check if contract is already initialized: %v", err)
	}
	if !initialized {
		return "", errors.New("contract options need to be set before calling any function, call Initialize() to initialize contract")
	}

	bytes, err := ctx.GetStub().GetState(nameKey)
	if err != nil {
		return "", fmt.Errorf("failed to get Name bytes: %s", err)
	}

	return string(bytes), nil
}

// Symbol returns an abbreviated name for non-fungible tokens in this contract.
// returns {String} Returns the symbol of the token

func (c *SmartContract) Symbol(ctx contractapi.TransactionContextInterface) (string, error) {

	// Check if contract has been intilized first
	initialized, err := checkInitialized(ctx)
	if err != nil {
		return "", fmt.Errorf("failed to check if contract is already initialized: %v", err)
	}
	if !initialized {
		return "", errors.New("contract options need to be set before calling any function, call Initialize() to initialize contract")
	}

	bytes, err := ctx.GetStub().GetState(symbolKey)
	if err != nil {
		return "", fmt.Errorf("failed to get Symbol: %v", err)
	}

	return string(bytes), nil
}

// TokenURI returns a distinct Uniform Resource Identifier (URI) for a given token.
// param {string} tokenId The identifier for a non-fungible token
// returns {String} Returns the URI of the token

func (c *SmartContract) TokenURI(ctx contractapi.TransactionContextInterface, tokenId string) (string, error) {

	// Check if contract has been intilized first
	initialized, err := checkInitialized(ctx)
	if err != nil {
		return "", fmt.Errorf("failed to check if contract is already initialized: %v", err)
	}
	if !initialized {
		return "", errors.New("contract options need to be set before calling any function, call Initialize() to initialize contract")
	}

	nft, err := _readNFT(ctx, tokenId)
	if err != nil {
		return "", fmt.Errorf("failed to get TokenURI: %v", err)
	}
	return nft.TokenURI, nil
}

// ============== ERC721 enumeration extension ===============
// TotalSupply counts non-fungible tokens tracked by this contract.
//
// @param {Context} ctx the transaction context
// @returns {Number} Returns a count of valid non-fungible tokens tracked by this contract,
// where each one of them has an assigned and queryable owner.

func (c *SmartContract) TotalSupply(ctx contractapi.TransactionContextInterface) int {

	// Check if contract has been intilized first
	initialized, err := checkInitialized(ctx)
	if err != nil {
		panic("failed to check if contract is already initialized:" + err.Error())
	}
	if !initialized {
		panic("Contract options need to be set before calling any function, call Initialize() to initialize contract")
	}

	// There is a key record for every non-fungible token in the format of nftPrefix.tokenId.
	// TotalSupply() queries for and counts all records matching nftPrefix.*

	iterator, err := ctx.GetStub().GetStateByPartialCompositeKey(nftPrefix, []string{})
	if err != nil {
		panic("Error creating GetStateByPartialCompositeKey:" + err.Error())
	}
	// Count the number of returned composite keys

	totalSupply := 0
	for iterator.HasNext() {
		_, err := iterator.Next()
		if err != nil {
			return 0
		}
		totalSupply++

	}
	return totalSupply

}

// ============== ERC721 enumeration extension ===============
// Set information for a token and intialize contract.
// param {String} name The name of the token
// param {String} symbol The symbol of the token

// Mint a new non-fungible token
// param {String} tokenId Unique ID of the non-fungible token to be minted
// param {String} tokenURI URI containing metadata of the minted non-fungible token
// returns {Object} Return the non-fungible token object

func (c *SmartContract) mintWithTokenURI(ctx contractapi.TransactionContextInterface, tokenId string, tokenURI string, instanceID string) (*Nft, error) {

	// Check if contract has been intilized first
	initialized, err := checkInitialized(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to check if contract is already initialized: %v", err)
	}
	if !initialized {
		return nil, errors.New("contract options need to be set before calling any function, call Initialize() to initialize contract")
	}

	// Check minter authorization - this sample assumes Org1 is the issuer with privilege to mint a new token
	clientMSPID, err := ctx.GetClientIdentity().GetMSPID()
	if err != nil {
		return nil, fmt.Errorf("failed to get clientMSPID: %v", err)
	}

	key := "instance_auth_" + instanceID
	authJSON, err := ctx.GetStub().GetState(key)
	if err != nil || authJSON == nil {
		return nil, fmt.Errorf("no mint authority found for instance %s", instanceID)
	}

	var auth InstanceMintAuthority
	_ = json.Unmarshal(authJSON, &auth)

	allowed := false
	for _, msp := range auth.AllowedMSPs {
		if msp == clientMSPID {
			allowed = true
			break
		}
	}

	if !allowed {
		return nil, fmt.Errorf("MSP %s not authorized to mint for instance %s", clientMSPID, instanceID)
	}

	// Get ID of submitting client identity
	minter64, err := ctx.GetClientIdentity().GetID()
	if err != nil {
		return nil, fmt.Errorf("failed to get minter id: %v", err)
	}

	minterBytes, err := base64.StdEncoding.DecodeString(minter64)
	if err != nil {
		return nil, fmt.Errorf("failed to DecodeString minter64: %v", err)
	}
	minter := string(minterBytes)

	// Check if the token to be minted does not exist
	exists := _nftExists(ctx, tokenId)
	if exists {
		return nil, fmt.Errorf("the token %s is already minted.: %v", tokenId, err)
	}

	// Add a non-fungible token
	nft := new(Nft)
	nft.TokenId = tokenId
	nft.Owner = minter
	nft.TokenURI = tokenURI

	nftKey, err := ctx.GetStub().CreateCompositeKey(nftPrefix, []string{tokenId})
	if err != nil {
		return nil, fmt.Errorf("failed to CreateCompositeKey to nftKey: %v", err)
	}

	nftBytes, err := json.Marshal(nft)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal nft: %v", err)
	}

	err = ctx.GetStub().PutState(nftKey, nftBytes)
	if err != nil {
		return nil, fmt.Errorf("failed to PutState nftBytes %s: %v", nftBytes, err)
	}

	// A composite key would be balancePrefix.owner.tokenId, which enables partial
	// composite key query to find and count all records matching balance.owner.*
	// An empty value would represent a delete, so we simply insert the null character.

	balanceKey, err := ctx.GetStub().CreateCompositeKey(balancePrefix, []string{minter, tokenId})
	if err != nil {
		return nil, fmt.Errorf("failed to CreateCompositeKey to balanceKey: %v", err)
	}

	err = ctx.GetStub().PutState(balanceKey, []byte{'\u0000'})
	if err != nil {
		return nil, fmt.Errorf("failed to PutState balanceKey %s: %v", nftBytes, err)
	}

	// Emit the Transfer event
	transferEvent := new(Transfer)
	transferEvent.From = "0x0"
	transferEvent.To = minter
	transferEvent.TokenId = tokenId

	transferEventBytes, err := json.Marshal(transferEvent)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal transferEventBytes: %v", err)
	}

	err = ctx.GetStub().SetEvent("Transfer", transferEventBytes)
	if err != nil {
		return nil, fmt.Errorf("failed to SetEvent transferEventBytes %s: %v", transferEventBytes, err)
	}

	return nft, nil
}

// Burn a non-fungible token
// param {String} tokenId Unique ID of a non-fungible token
// returns {Boolean} Return whether the burn was successful or not
func (c *SmartContract) Burn(ctx contractapi.TransactionContextInterface, tokenId string) (bool, error) {

	// Check if contract has been intilized first
	initialized, err := checkInitialized(ctx)
	if err != nil {
		return false, fmt.Errorf("failed to check if contract is already initialized: %v", err)
	}
	if !initialized {
		return false, errors.New("contract options need to be set before calling any function, call Initialize() to initialize contract")
	}

	owner64, err := ctx.GetClientIdentity().GetID()
	if err != nil {
		return false, fmt.Errorf("failed to GetClientIdentity owner64: %v", err)
	}

	ownerBytes, err := base64.StdEncoding.DecodeString(owner64)
	if err != nil {
		return false, fmt.Errorf("failed to DecodeString owner64: %v", err)
	}
	owner := string(ownerBytes)

	// Check if a caller is the owner of the non-fungible token
	nft, err := _readNFT(ctx, tokenId)
	if err != nil {
		return false, fmt.Errorf("failed to _readNFT nft : %v", err)
	}
	if nft.Owner != owner {
		return false, fmt.Errorf("non-fungible token %s is not owned by %s", tokenId, owner)
	}

	// Delete the token
	nftKey, err := ctx.GetStub().CreateCompositeKey(nftPrefix, []string{tokenId})
	if err != nil {
		return false, fmt.Errorf("failed to CreateCompositeKey tokenId: %v", err)
	}

	err = ctx.GetStub().DelState(nftKey)
	if err != nil {
		return false, fmt.Errorf("failed to DelState nftKey: %v", err)
	}

	// Remove a composite key from the balance of the owner
	balanceKey, err := ctx.GetStub().CreateCompositeKey(balancePrefix, []string{owner, tokenId})
	if err != nil {
		return false, fmt.Errorf("failed to CreateCompositeKey balanceKey %s: %v", balanceKey, err)
	}

	err = ctx.GetStub().DelState(balanceKey)
	if err != nil {
		return false, fmt.Errorf("failed to DelState balanceKey %s: %v", balanceKey, err)
	}

	// Emit the Transfer event
	transferEvent := new(Transfer)
	transferEvent.From = owner
	transferEvent.To = "0x0"
	transferEvent.TokenId = tokenId

	transferEventBytes, err := json.Marshal(transferEvent)
	if err != nil {
		return false, fmt.Errorf("failed to marshal transferEventBytes: %v", err)
	}

	err = ctx.GetStub().SetEvent("Transfer", transferEventBytes)
	if err != nil {
		return false, fmt.Errorf("failed to SetEvent transferEventBytes: %v", err)
	}

	return true, nil
}

// ClientAccountBalance returns the balance of the requesting client's account.
// returns {Number} Returns the account balance
func (c *SmartContract) ClientAccountBalance(ctx contractapi.TransactionContextInterface) (int, error) {

	// Check if contract has been intilized first
	initialized, err := checkInitialized(ctx)
	if err != nil {
		return 0, fmt.Errorf("failed to check if contract is already initialized: %v", err)
	}
	if !initialized {
		return 0, errors.New("contract options need to be set before calling any function, call Initialize() to initialize contract")
	}

	// Get ID of submitting client identity
	clientAccountID64, err := ctx.GetClientIdentity().GetID()
	if err != nil {
		return 0, fmt.Errorf("failed to GetClientIdentity minter: %v", err)
	}

	clientAccountIDBytes, err := base64.StdEncoding.DecodeString(clientAccountID64)
	if err != nil {
		return 0, fmt.Errorf("failed to DecodeString sender: %v", err)
	}

	clientAccountID := string(clientAccountIDBytes)

	return c.BalanceOf(ctx, clientAccountID), nil
}

// ClientAccountID returns the id of the requesting client's account.
// In this implementation, the client account ID is the clientId itself.
// Users can use this function to get their own account id, which they can then give to others as the payment address

func (c *SmartContract) ClientAccountID(ctx contractapi.TransactionContextInterface) (string, error) {

	// Check if contract has been intilized first
	initialized, err := checkInitialized(ctx)
	if err != nil {
		return "", fmt.Errorf("failed to check if contract is already initialized: %v", err)
	}
	if !initialized {
		return "", errors.New("contract options need to be set before calling any function, call Initialize() to initialize contract")
	}

	// Get ID of submitting client identity
	clientAccountID64, err := ctx.GetClientIdentity().GetID()
	if err != nil {
		return "", fmt.Errorf("failed to GetClientIdentity minter: %v", err)
	}

	clientAccountBytes, err := base64.StdEncoding.DecodeString(clientAccountID64)
	if err != nil {
		return "", fmt.Errorf("failed to DecodeString clientAccount64: %v", err)
	}
	clientAccount := string(clientAccountBytes)

	return clientAccount, nil
}

// Checks that contract options have been already initialized
func checkInitialized(ctx contractapi.TransactionContextInterface) (bool, error) {
	tokenName, err := ctx.GetStub().GetState(nameKey)
	if err != nil {
		return false, fmt.Errorf("failed to get token name: %v", err)
	}
	if tokenName == nil {
		return false, nil
	}
	return true, nil
}

// ERC5521部分
type resultOf struct {
	Keys  []string            `json:"keys"`
	Value map[string][]string `json:"value"`
}

func (c *SmartContract) SetChaincodeName(ctx contractapi.TransactionContextInterface, chaincodeName string) (bool, error) {
	bytes, err := ctx.GetStub().GetState(chaincodeNameKey)
	if err != nil {
		return false, fmt.Errorf("fail to get chaincodeName")
	}
	if bytes != nil {
		return false, fmt.Errorf("chaincodeName has already exist")
	}
	err = ctx.GetStub().PutState(chaincodeNameKey, []byte(chaincodeName))
	if err != nil {
		return false, fmt.Errorf("fail to set chaincodeName")
	}
	return true, nil
}

func (c *SmartContract) getChaincodeName(ctx contractapi.TransactionContextInterface) (string, error) {
	bytes, err := ctx.GetStub().GetState(chaincodeNameKey)
	if err != nil {
		return "", fmt.Errorf("fail to get chaincodeName")
	}
	if bytes == nil {
		return "", fmt.Errorf("the chaincodeName is empty")
	}
	chaincodeName := string(bytes)
	return chaincodeName, nil
}

// 实现一个relationship键值映射结构
// mapping (uint256 => Relationship) internal _relationship;
func (c *SmartContract) GetRelationshipById(ctx contractapi.TransactionContextInterface, Id string) (*Relationship, error) {
	//构造一个复合键
	var IdKey []string
	IdKey = append(IdKey, Id)
	Key, err := ctx.GetStub().CreateCompositeKey(RelationshipKey, IdKey)
	if err != nil {
		return nil, fmt.Errorf("fail to get compositekey to get relationship")
	}
	if Key == "" {
		return nil, fmt.Errorf("the compositekey of relationship which you try to get is empty")
	}
	relationshipJson, err := ctx.GetStub().GetState(Key)
	if err != nil {
		return nil, fmt.Errorf("getrelationshipBYkey fail to getstate")
	}
	if relationshipJson == nil {
		temp := &Relationship{
			Reffering: make(map[string][]string),
			Reffered:  make(map[string][]string),
		}
		err := c.SetRelationshipById(ctx, Id, temp)
		if err != nil {
			return nil, fmt.Errorf("failed to create empty relationship for %s: %w", Id, err)
		}
		return temp, nil
	}
	var relationship Relationship
	err = json.Unmarshal(relationshipJson, &relationship)
	if err != nil {
		return nil, fmt.Errorf("the fail to get relationship")
	}
	return &relationship, nil
}

func (c *SmartContract) SetRelationshipById(ctx contractapi.TransactionContextInterface, Id string, relationship *Relationship) error {
	var IdKey []string
	IdKey = append(IdKey, Id)
	Key, err := ctx.GetStub().CreateCompositeKey(RelationshipKey, IdKey)
	if err != nil {
		return fmt.Errorf("fail to get compositekey to get relationship")
	}
	if Key == "" {
		return fmt.Errorf("the compositekey of relationship which you try to get is empty")
	}
	tempRelationship := Relationship{
		Reffering:        relationship.Reffering,
		Reffered:         relationship.Reffered,
		RefferingKeys:    relationship.RefferingKeys,
		RefferedKeys:     relationship.RefferedKeys,
		CreatedTimestamp: relationship.CreatedTimestamp,
	}

	JsonBytes, err := json.Marshal(tempRelationship)
	if err != nil {
		return fmt.Errorf("fail to Marshal")
	}
	err = ctx.GetStub().PutState(Key, JsonBytes)
	if err != nil {
		return fmt.Errorf("fail to store relationship of %s ", Id)
	}
	return nil
}

// 传入时必须一一对应
// 参数分析_tokenIds 为被引用id，二维数组，一维表示对应和chaincodeName，chaincodeName 二维表示tokenID（实现跨合约调用）
// 这里要求chaincodeName和_tokenid[]一一对应
func (c *SmartContract) SafeMint(ctx contractapi.TransactionContextInterface, tokenid string, tokenURI string, instanceID string, chaincodeName []string, _tokenIds [][]string) (*Nft, error) {
	err := c.authorizationHelper(ctx, instanceID)
	if err != nil {
		return nil, fmt.Errorf("caller is not allowed")
	}
	getnft, err := c.mintWithTokenURI(ctx, tokenid, tokenURI, instanceID)
	if err != nil {
		return nil, fmt.Errorf("safemint fail to execute mintwithtokenURI")
	}
	if err := c.setNode(ctx, tokenid, chaincodeName, _tokenIds); err != nil {
		return nil, fmt.Errorf("setNode failed: %w", err)
	}
	return getnft, nil
}

func (c *SmartContract) setNode(ctx contractapi.TransactionContextInterface, tokenid string, chaincodeName []string, _tokenIds [][]string) error {
	if len(chaincodeName) != len(_tokenIds) {
		return fmt.Errorf("chaincodeName and TokenID arrays must have the same length")
	}
	for i := 0; i < len(_tokenIds); i++ {
		if len(_tokenIds[i]) == 0 {
			return fmt.Errorf("ERC5521:the referring list cannot be empty")
		}
	}
	c.setNodeReferring(ctx, chaincodeName, tokenid, _tokenIds)
	c.setNodeReferred(ctx, chaincodeName, tokenid, _tokenIds)
	return nil
}

func (c *SmartContract) setNodeReferring(ctx contractapi.TransactionContextInterface, chaincodeName []string, tokenid string, _tokenIds [][]string) error {
	tempRelationship, _ := c.GetRelationshipById(ctx, tokenid)
	for i := 0; i < len(chaincodeName); i++ {
		if len(tempRelationship.Reffering[chaincodeName[i]]) == 0 {
			tempRelationship.RefferingKeys = append(tempRelationship.RefferingKeys, chaincodeName[i])
		}
		tempRelationship.Reffering[chaincodeName[i]] = _tokenIds[i]
	}
	//事件时间戳
	timestampProto, err := ctx.GetStub().GetTxTimestamp()
	if err != nil {
		return fmt.Errorf("failed to get transaction timestamp: %w", err)
	}
	if timestampProto.Seconds < 0 {
		return fmt.Errorf("transaction timestamp seconds is negative")
	}
	tempRelationship.CreatedTimestamp = uint64(timestampProto.Seconds)
	err = c.SetRelationshipById(ctx, tokenid, tempRelationship)
	if err != nil {
		return fmt.Errorf("fail to set relationshipById or fail to change relationship of tokenid: %s ", tokenid)
	}
	return nil
}
func (c *SmartContract) setNodeReferred(ctx contractapi.TransactionContextInterface, chaincodeName []string, tokenId string, _tokenId [][]string) error {
	thischaincodeName, err := c.getChaincodeName(ctx)
	if err != nil {
		return fmt.Errorf("fail to get chaincode Name and cannot set NodeReffered")
	}
	if thischaincodeName == "" {
		return fmt.Errorf("this chaincodeName is empty and cannot set NodeReffered")
	}
	var tempRelationship *Relationship
	for i := 0; i < len(chaincodeName); i++ {
		if chaincodeName[i] == thischaincodeName {
			for j := 0; j < len(_tokenId[i]); j++ {
				tempRelationship, err = c.GetRelationshipById(ctx, _tokenId[i][j])
				if err != nil {
					return fmt.Errorf("setNoadeReferred fail to execute getrelationshipById")
				}
				if len(tempRelationship.Reffered[chaincodeName[i]]) == 0 {
					tempRelationship.RefferedKeys = append(tempRelationship.RefferedKeys, chaincodeName[i])
				}
				if tokenId == _tokenId[i][j] {
					return fmt.Errorf("self-reference not allowed")
				}
				timestampProto, err := ctx.GetStub().GetTxTimestamp()
				if err != nil {
					return fmt.Errorf("failed to get transaction timestamp: %w", err)
				}
				if timestampProto.Seconds < 0 {
					return fmt.Errorf("transaction timestamp seconds is negative")
				}
				if tempRelationship.CreatedTimestamp != 0 && tempRelationship.CreatedTimestamp > uint64(timestampProto.Seconds) {
					return fmt.Errorf("the referred NFT needs to be a predecessor")
				}

				tempRelationship.Reffered[thischaincodeName] = append(tempRelationship.Reffered[thischaincodeName], tokenId)
				err = c.SetRelationshipById(ctx, _tokenId[i][j], tempRelationship)
				if err != nil {
					return fmt.Errorf("fail to set relationshipById or fail to change relationship of tokenid: %s ", _tokenId[i][j])
				}
			}
		} else {
			//todo invoke_ohterchaincode
			_tokenIdBytes, err := json.Marshal(_tokenId[i])
			if err != nil {
				return fmt.Errorf("cannot marshal tokenidbytes")
			}
			tempchaincode := chaincodeName[i]
			_args := make([][]byte, 4)
			_args[0] = []byte("setNodeReferredExternal")
			_args[1] = []byte(thischaincodeName)
			_args[2] = []byte(tokenId)
			_args[3] = _tokenIdBytes
			_, err = c.Invoke_Other_chaincode(ctx, tempchaincode, "default", _args)
			if err != nil {
				return fmt.Errorf("failed to invoke external chaincode: %w", err)
			}
		}
	}
	return nil
}

func (c *SmartContract) Invoke_Other_chaincode(ctx contractapi.TransactionContextInterface, chaincodeName string, channel string, _args [][]byte) ([]byte, error) {
	stub := ctx.GetStub()
	response := stub.InvokeChaincode(chaincodeName, _args, channel)
	if response.Status != ChaincodeOk {
		return []byte(""), fmt.Errorf("failed to invoke chaincode. Response status: %d. Response message: %s", response.Status, response.Message)
	}
	return response.Payload, nil
}

func (c *SmartContract) setNodeReferredExternal(ctx contractapi.TransactionContextInterface, chaincodeName string, tokenId string, _tokenIds []string) error {
	var tempRelationship *Relationship
	for i := 0; i < len(_tokenIds); i++ {
		var err error
		tempRelationship, err = c.GetRelationshipById(ctx, _tokenIds[i])
		if err != nil {
			return fmt.Errorf("setNodeReferredExternal fail to execute getrelationshipbyid")
		}
		if len(tempRelationship.Reffered[chaincodeName]) == 0 {
			tempRelationship.RefferedKeys = append(tempRelationship.RefferedKeys, chaincodeName)
		}
		thischaincodeName, _ := c.getChaincodeName(ctx)
		if chaincodeName == thischaincodeName {
			return fmt.Errorf("this must be an external contract address")
		}
		timestampProto, err := ctx.GetStub().GetTxTimestamp()
		if err != nil {
			return fmt.Errorf("failed to get transaction timestamp: %w", err)
		}
		if timestampProto.Seconds < 0 {
			return fmt.Errorf("transaction timestamp seconds is negative")
		}
		if tempRelationship.CreatedTimestamp != 0 && tempRelationship.CreatedTimestamp > uint64(timestampProto.Seconds) {
			return fmt.Errorf("the referred NFT needs to be a predecessor")
		}

		tempRelationship.Reffered[chaincodeName] = append(tempRelationship.Reffered[chaincodeName], tokenId)
		err = c.SetRelationshipById(ctx, _tokenIds[i], tempRelationship)
		if err != nil {
			return fmt.Errorf("fail to set relationshipById or fail to change relationship of tokenid: %s ", _tokenIds[i])
		}
	}
	return nil
}

func (c *SmartContract) ReferringOf(ctx contractapi.TransactionContextInterface, chaincodeName string, tokenId string) (*resultOf, error) {

	thischaincodeName, err := c.getChaincodeName(ctx)
	if err != nil {
		return nil, fmt.Errorf("fail to get chaincodeName")
	}
	if chaincodeName == thischaincodeName {
		if !(_nftExists(ctx, tokenId)) {
			return nil, fmt.Errorf("token id not exitsted")
		}
		tempRelationship, err := c.GetRelationshipById(ctx, tokenId)
		if err != nil {
			return nil, fmt.Errorf("there is something wrong when get temprelationship")
		}
		result := resultOf{tempRelationship.RefferingKeys, tempRelationship.Reffering}
		return &result, nil
	} else {
		tempchaincode := chaincodeName
		_args := make([][]byte, 3)
		_args[0] = []byte("referringOf")
		_args[1] = []byte(tempchaincode)
		_args[2] = []byte(tokenId)
		payload, err := c.Invoke_Other_chaincode(ctx, tempchaincode, "default", _args)
		if err != nil {
			return nil, fmt.Errorf("failed to invoke chaincode %s: %w", tempchaincode, err)
		}
		var result resultOf
		err = json.Unmarshal(payload, &result)
		if err != nil {
			return nil, fmt.Errorf("failed to unmarshal result from chaincode %s: %w", tempchaincode, err)
		}
		return &result, nil
	}
}

func (c *SmartContract) ReferredOf(ctx contractapi.TransactionContextInterface, chaincodeName string, tokenId string) (*resultOf, error) {
	thischaincodeName, err := c.getChaincodeName(ctx)
	if err != nil {
		return nil, fmt.Errorf("fail to get chaincodeName")
	}
	if thischaincodeName == chaincodeName {
		if !(_nftExists(ctx, tokenId)) {
			return nil, fmt.Errorf("token id not exitsted")
		}
		tempRelationship, err := c.GetRelationshipById(ctx, tokenId)
		if err != nil {
			return nil, fmt.Errorf("there is something wrong when get temprelationship")
		}
		result := resultOf{tempRelationship.RefferedKeys, tempRelationship.Reffered}
		return &result, nil
	} else {
		tempchaincode := chaincodeName
		_args := make([][]byte, 3)
		_args[0] = []byte("referredOf")
		_args[1] = []byte(tempchaincode)
		_args[2] = []byte(tokenId)
		payload, err := c.Invoke_Other_chaincode(ctx, tempchaincode, "default", _args)
		if err != nil {
			return nil, fmt.Errorf("failed to invoke chaincode %s: %w", tempchaincode, err)
		}
		var result resultOf
		err = json.Unmarshal(payload, &result)
		if err != nil {
			return nil, fmt.Errorf("failed to unmarshal result from chaincode %s: %w", tempchaincode, err)
		}
		return &result, nil
	}

}

func (c *SmartContract) CreatedTimestampOf(ctx contractapi.TransactionContextInterface, chaincodeName string, tokenId string) (uint64, error) {
	thischaincodeName, err := c.getChaincodeName(ctx)
	if err != nil {
		return 0, fmt.Errorf("fail to get chaincodeName")
	}
	if thischaincodeName == chaincodeName {
		if !(_nftExists(ctx, tokenId)) {
			return 0, fmt.Errorf("token id not exitsted")
		}
		tempRelationship, err := c.GetRelationshipById(ctx, tokenId)
		if err != nil {
			return 0, fmt.Errorf("there is something wrong when get temprelationship")
		}
		return tempRelationship.CreatedTimestamp, nil
	} else {
		tempchaincode := chaincodeName
		_args := make([][]byte, 3)
		_args[0] = []byte("createdTimestampOf")
		_args[1] = []byte(tempchaincode)
		_args[2] = []byte(tokenId)
		payload, err := c.Invoke_Other_chaincode(ctx, tempchaincode, "default", _args)
		if err != nil {
			return 0, fmt.Errorf("failed to invoke chaincode %s: %w", tempchaincode, err)
		}
		if len(payload) == 8 {
			return binary.BigEndian.Uint64(payload), nil
		}
		var timestamp uint64
		if err := json.Unmarshal(payload, &timestamp); err != nil {
			return 0, fmt.Errorf("unexpected payload format: %w", err)
		}
		return timestamp, nil
	}
}

// bpmn调用接口
func (c *SmartContract) Branchmint(ctx contractapi.TransactionContextInterface, tokenid string, tokenURI string, instanceID string, chaincodeName string, _tokenIds []string) (*Nft, error) {
	if len(_tokenIds) == 0 {
		getnft, err := c.mintWithTokenURI(ctx, tokenid, tokenURI, instanceID)
		if err != nil {
			return nil, fmt.Errorf("branchmint fail to invoke mintwithtokenURI")
		}
		return getnft, nil
	} else {
		var tempchaincodeName []string
		tempchaincodeName = append(tempchaincodeName, chaincodeName)
		var temp_tokenids [][]string
		temp_tokenids = append(temp_tokenids, _tokenIds)
		getnft, err := c.SafeMint(ctx, tokenid, tokenURI, instanceID, tempchaincodeName, temp_tokenids)
		if err != nil {
			return nil, fmt.Errorf("saft mint do not execute")
		}
		return getnft, nil
	}
}
