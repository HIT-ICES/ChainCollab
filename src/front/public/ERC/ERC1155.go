/*
	2021 Baran Kılıç <baran.kilic@boun.edu.tr>

	SPDX-License-Identifier: Apache-2.0
*/

package chaincode

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"sort"
	"strconv"
	"strings"

	"github.com/hyperledger/fabric-contract-api-go/v2/contractapi"
)

const uriKey = "uri"

const balancePrefix = "account~tokenId~sender"
const approvalPrefix = "account~operator"

//const minterMSPID = "Org1MSP"

// Define key names for options
const nameKey = "name"
const symbolKey = "symbol"

// 用来维护字符串id和uint64 位id 的双向映射
const nextTokenIDKey = "nextTokenID"
const aliasToIDPrefix = "aliasToID-"
const IDToAliasPrefix = "IDToAlias-"

// SmartContract provides functions for transferring tokens between accounts
type SmartContract struct {
	contractapi.Contract
}

// TransferSingle MUST emit when a single token is transferred, including zero
// value transfers as well as minting or burning.
// The operator argument MUST be msg.sender.
// The from argument MUST be the address of the holder whose balance is decreased.
// The to argument MUST be the address of the recipient whose balance is increased.
// The id argument MUST be the token type being transferred.
// The value argument MUST be the number of tokens the holder balance is decreased
// by and match what the recipient balance is increased by.
// When minting/creating tokens, the from argument MUST be set to `0x0` (i.e. zero address).
// When burning/destroying tokens, the to argument MUST be set to `0x0` (i.e. zero address).
type TransferSingle struct {
	Operator string `json:"operator"`
	From     string `json:"from"`
	To       string `json:"to"`
	ID       uint64 `json:"id"`
	Value    uint64 `json:"value"`
}

// TransferBatch MUST emit when tokens are transferred, including zero value
// transfers as well as minting or burning.
// The operator argument MUST be msg.sender.
// The from argument MUST be the address of the holder whose balance is decreased.
// The to argument MUST be the address of the recipient whose balance is increased.
// The ids argument MUST be the list of tokens being transferred.
// The values argument MUST be the list of number of tokens (matching the list
// and order of tokens specified in _ids) the holder balance is decreased by
// and match what the recipient balance is increased by.
// When minting/creating tokens, the from argument MUST be set to `0x0` (i.e. zero address).
// When burning/destroying tokens, the to argument MUST be set to `0x0` (i.e. zero address).
type TransferBatch struct {
	Operator string   `json:"operator"`
	From     string   `json:"from"`
	To       string   `json:"to"`
	IDs      []uint64 `json:"ids"`
	Values   []uint64 `json:"values"`
}
type InstanceMintAuthority struct {
	InstanceID  string   `json:"instance_id"`
	AllowedMSPs []string `json:"allowed_msps"`
}

// TransferBatchMultiRecipient MUST emit when tokens are transferred, including zero value
// transfers as well as minting or burning.
// The operator argument MUST be msg.sender.
// The from argument MUST be the address of the holder whose balance is decreased.
// The to argument MUST be the list of the addresses of the recipients whose balance is increased.
// The ids argument MUST be the list of tokens being transferred.
// The values argument MUST be the list of number of tokens (matching the list
// and order of tokens specified in _ids) the holder balance is decreased by
// and match what the recipient balance is increased by.
// When minting/creating tokens, the from argument MUST be set to `0x0` (i.e. zero address).
// When burning/destroying tokens, the to argument MUST be set to `0x0` (i.e. zero address).
type TransferBatchMultiRecipient struct {
	Operator string   `json:"operator"`
	From     string   `json:"from"`
	To       []string `json:"to"`
	IDs      []uint64 `json:"ids"`
	Values   []uint64 `json:"values"`
}

// ApprovalForAll MUST emit when approval for a second party/operator address
// to manage all tokens for an owner address is enabled or disabled
// (absence of an event assumes disabled).
type ApprovalForAll struct {
	Owner    string `json:"owner"`
	Operator string `json:"operator"`
	Approved bool   `json:"approved"`
}

// URI MUST emit when the URI is updated for a token ID.
// Note: This event is not used in this contract implementation because in this implementation,
// only the programmatic way of setting URI is used. The URI should contain {id} as part of it
// and the clients MUST replace this with the actual token ID.
type URI struct {
	Value string `json:"value"`
	ID    uint64 `json:"id"`
}

// To represents recipient address
// ID represents token ID
type ToID struct {
	To string
	ID uint64
}

func base64decoding(id string) string {
	idbytes, _ := base64.StdEncoding.DecodeString(id)
	return string(idbytes)
}

// 权限相关
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

func (s *SmartContract) getAndIncrementNextTokenID(ctx contractapi.TransactionContextInterface) (uint64, error) {
	// 1. 读取当前计数器
	idBytes, err := ctx.GetStub().GetState(nextTokenIDKey)
	if err != nil {
		return 0, fmt.Errorf("读取 nextTokenIDKey 失败: %v", err)
	}

	var currentID uint64 = 1 // 默认从 1 开始

	if idBytes != nil {
		// 如果计数器已存在，解析它
		currentID, err = strconv.ParseUint(string(idBytes), 10, 64)
		if err != nil {
			return 0, fmt.Errorf("解析 nextTokenID 失败: %v", err)
		}
	}

	// 2. 准备写入下一个 ID (递增)
	nextID, err := add(currentID, 1) // 使用安全加法
	if err != nil {
		return 0, fmt.Errorf("ID 计数器溢出: %v", err)
	}

	// 3. 写入新的计数器值 (N+1)
	nextIDString := strconv.FormatUint(nextID, 10)
	if err := ctx.GetStub().PutState(nextTokenIDKey, []byte(nextIDString)); err != nil {
		return 0, fmt.Errorf("写入 nextTokenID 失败: %v", err)
	}

	// 4. 返回当前 ID (N) 给调用者使用
	return currentID, nil
}

// RegisterTokenAlias 注册一个新的代币别名，并为其分配一个自动递增的 uint64 ID。
func (s *SmartContract) RegisterTokenAlias(ctx contractapi.TransactionContextInterface, alias string, InstanceID string) (uint64, error) {
	if err := authorizationHelper(ctx, InstanceID); err != nil {
		return 0, err
	}
	aliasKey := aliasToIDPrefix + alias + InstanceID
	existingIDBytes, err := ctx.GetStub().GetState(aliasKey)
	if err != nil {
		return 0, fmt.Errorf("查询别名键 '%s' 失败: %v", aliasKey, err)
	}

	if existingIDBytes != nil {
		existingID, parseErr := strconv.ParseUint(string(existingIDBytes), 10, 64)
		if parseErr != nil {
			return 0, fmt.Errorf("解析已注册 ID 失败，值 '%s': %v", string(existingIDBytes), parseErr)
		}

		return existingID, nil

	}

	// 2. 获取并递增下一个可用的确定性 ID
	newID, err := s.getAndIncrementNextTokenID(ctx)
	if err != nil {
		return 0, err
	}

	// 3. 构造键和值
	newIDString := strconv.FormatUint(newID, 10)
	idKey := IDToAliasPrefix + newIDString

	// 4. 写入双向映射

	// 写入正向映射： alias -> id
	if err := ctx.GetStub().PutState(aliasKey, []byte(newIDString)); err != nil {
		return 0, fmt.Errorf("写入别名到 ID 映射失败: %v", err)
	}

	// 写入反向映射： id -> alias
	if err := ctx.GetStub().PutState(idKey, []byte(alias)); err != nil {
		return 0, fmt.Errorf("写入 ID 到别名映射失败: %v", err)
	}

	// 成功返回新生成的 ID
	return newID, nil
}

func (s *SmartContract) Getuint64IDByString(ctx contractapi.TransactionContextInterface, alias string, InstanceID string) (uint64, error) {
	StringKey := aliasToIDPrefix + alias + InstanceID
	idBytes, err := ctx.GetStub().GetState(StringKey)
	id, err := strconv.ParseUint(string(idBytes), 10, 64)
	if err != nil {
		return 0, fmt.Errorf("解析存储的 ID 失败，值 '%s': %v", string(idBytes), err)
	}
	return id, nil
}

func (s *SmartContract) GetStringByuint64ID(ctx contractapi.TransactionContextInterface, id uint64) (string, error) {
	idString := strconv.FormatUint(id, 10)
	idKey := IDToAliasPrefix + idString
	aliasBytes, err := ctx.GetStub().GetState(idKey)
	if err != nil {
		return "", fmt.Errorf("查询数字 ID 键 '%s' 失败: %v", idKey, err)
	}

	if aliasBytes == nil {
		return "", fmt.Errorf("数字 ID '%d' 尚未注册别名", id)
	}
	return string(aliasBytes), nil
}
func (s *SmartContract) MultiMint(ctx contractapi.TransactionContextInterface, account []string, stringID string, amount uint64, instanceID string) error {
	for _, account11 := range account {
		s.Mint(ctx, account11, stringID, amount, instanceID)
	}
	return nil
}

func (s *SmartContract) MultiBurn(ctx contractapi.TransactionContextInterface, account []string, stringID string, amount uint64, instanceID string) error {
	for _, accaccount11 := range account {
		s.Burn(ctx, accaccount11, stringID, amount, instanceID)
	}

	return nil
}

// Mint creates amount tokens of token type id and assigns them to account.
// This function emits a TransferSingle event.
func (s *SmartContract) Mint(ctx contractapi.TransactionContextInterface, account string, stringID string, amount uint64, instanceID string) error {
	fmt.Println("---------------------------------------------")
	// Check if contract has been intilized first
	initialized, err := checkInitialized(ctx)
	if err != nil {
		return fmt.Errorf("failed to check if contract is already initialized: %v", err)
	}
	if !initialized {
		return fmt.Errorf("Contract options need to be set before calling any function, call Initialize() to initialize contract")
	}

	// Check minter authorization - this sample assumes Org1 is the central banker with privilege to mint new tokens
	err = authorizationHelper(ctx, instanceID)
	if err != nil {
		return err
	}
	id, err := s.RegisterTokenAlias(ctx, stringID, instanceID)

	// Get ID of submitting client identity
	operator, err := ctx.GetClientIdentity().GetID()
	if err != nil {
		return fmt.Errorf("failed to get client id: %v", err)
	}

	getstringid, _ := s.GetStringByuint64ID(ctx, id)
	getbalance, _ := s.BalanceOf(ctx, account, id)
	fmt.Println("目前账户：" + base64decoding(operator) + "操作账户" + base64decoding(account) + "代币stringid为" + stringID + "存储的stringid为" + getstringid + "当前余额：" + strconv.FormatUint(getbalance, 10))

	// Mint tokens
	err = mintHelper(ctx, operator, account, id, amount)
	if err != nil {
		return err
	}

	// Emit TransferSingle event
	transferSingleEvent := TransferSingle{operator, "0x0", account, id, amount}

	return emitTransferSingle(ctx, transferSingleEvent)
}

// MintBatch creates amount tokens for each token type id and assigns them to account.
// This function emits a TransferBatch event.
func (s *SmartContract) MintBatch(ctx contractapi.TransactionContextInterface, account string, ids []uint64, amounts []uint64, instanceID string) error {

	// Check if contract has been intilized first
	initialized, err := checkInitialized(ctx)
	if err != nil {
		return fmt.Errorf("failed to check if contract is already initialized: %v", err)
	}
	if !initialized {
		return fmt.Errorf("Contract options need to be set before calling any function, call Initialize() to initialize contract")
	}

	if len(ids) != len(amounts) {
		return fmt.Errorf("ids and amounts must have the same length")
	}

	// Check minter authorization - this sample assumes Org1 is the central banker with privilege to mint new tokens
	err = authorizationHelper(ctx, instanceID)
	if err != nil {
		return err
	}

	// Get ID of submitting client identity
	operator, err := ctx.GetClientIdentity().GetID()
	if err != nil {
		return fmt.Errorf("failed to get client id: %v", err)
	}

	// Group amount by token id because we can only send token to a recipient only one time in a block. This prevents key conflicts
	amountToSend := make(map[uint64]uint64) // token id => amount

	for i := 0; i < len(amounts); i++ {
		amountToSend[ids[i]], err = add(amountToSend[ids[i]], amounts[i])
		if err != nil {
			return err
		}
	}

	// Copy the map keys and sort it. This is necessary because iterating maps in Go is not deterministic
	amountToSendKeys := sortedKeys(amountToSend)

	// Mint tokens
	for _, id := range amountToSendKeys {
		amount := amountToSend[id]
		err = mintHelper(ctx, operator, account, id, amount)
		if err != nil {
			return err
		}
	}

	// Emit TransferBatch event
	transferBatchEvent := TransferBatch{operator, "0x0", account, ids, amounts}
	return emitTransferBatch(ctx, transferBatchEvent)
}

// Burn destroys amount tokens of token type id from account.
// This function triggers a TransferSingle event.
func (s *SmartContract) Burn(ctx contractapi.TransactionContextInterface, account string, stringID string, amount uint64, instanceID string) error {
	fmt.Println("------------------------")
	// Check if contract has been intilized first
	initialized, err := checkInitialized(ctx)
	if err != nil {
		return fmt.Errorf("failed to check if contract is already initialized: %v", err)
	}
	if !initialized {
		return fmt.Errorf("Contract options need to be set before calling any function, call Initialize() to initialize contract")
	}

	if account == "0x0" {
		return fmt.Errorf("burn to the zero address")
	}

	// Check minter authorization - this sample assumes Org1 is the central banker with privilege to burn new tokens
	err = authorizationHelper(ctx, instanceID)
	if err != nil {
		return err
	}

	id, err := s.Getuint64IDByString(ctx, stringID, instanceID)
	// Get ID of submitting client identity
	operator, err := ctx.GetClientIdentity().GetID()
	if err != nil {
		return fmt.Errorf("failed to get client id: %v", err)
	}

	getstringid, _ := s.GetStringByuint64ID(ctx, id)
	getbalance, _ := s.BalanceOf(ctx, account, id)
	fmt.Println("目前账户：" + base64decoding(operator) + "操作账户" + base64decoding(account) + "代币stringid为" + stringID + "存储的stringid为" + getstringid + "当前余额：" + strconv.FormatUint(getbalance, 10))

	// Burn tokens
	err = removeBalance(ctx, account, []uint64{id}, []uint64{amount})
	if err != nil {
		return err
	}

	transferSingleEvent := TransferSingle{operator, account, "0x0", id, amount}
	return emitTransferSingle(ctx, transferSingleEvent)
}

// BurnBatch destroys amount tokens of for each token type id from account.
// This function emits a TransferBatch event.
func (s *SmartContract) BurnBatch(ctx contractapi.TransactionContextInterface, account string, ids []uint64, amounts []uint64, instanceID string) error {

	// Check if contract has been intilized first
	initialized, err := checkInitialized(ctx)
	if err != nil {
		return fmt.Errorf("failed to check if contract is already initialized: %v", err)
	}
	if !initialized {
		return fmt.Errorf("Contract options need to be set before calling any function, call Initialize() to initialize contract")
	}

	if account == "0x0" {
		return fmt.Errorf("burn to the zero address")
	}

	if len(ids) != len(amounts) {
		return fmt.Errorf("ids and amounts must have the same length")
	}

	// Check minter authorization - this sample assumes Org1 is the central banker with privilege to burn new tokens
	err = authorizationHelper(ctx, instanceID)
	if err != nil {
		return err
	}

	// Get ID of submitting client identity
	operator, err := ctx.GetClientIdentity().GetID()
	if err != nil {
		return fmt.Errorf("failed to get client id: %v", err)
	}

	err = removeBalance(ctx, account, ids, amounts)
	if err != nil {
		return err
	}

	transferBatchEvent := TransferBatch{operator, account, "0x0", ids, amounts}
	return emitTransferBatch(ctx, transferBatchEvent)
}

// TransferFrom transfers tokens from sender account to recipient account
// recipient account must be a valid clientID as returned by the ClientID() function
// This function triggers a TransferSingle event
func (s *SmartContract) TransferFrom(ctx contractapi.TransactionContextInterface, sender string, recipient string, stringID string, amount uint64, instanceID string) error {

	// Check if contract has been intilized first
	initialized, err := checkInitialized(ctx)
	if err != nil {
		return fmt.Errorf("failed to check if contract is already initialized: %v", err)
	}
	if !initialized {
		return fmt.Errorf("Contract options need to be set before calling any function, call Initialize() to initialize contract")
	}

	if sender == recipient {
		return fmt.Errorf("transfer to self")
	}

	id, err := s.Getuint64IDByString(ctx, stringID, instanceID)

	// Get ID of submitting client identity
	operator, err := ctx.GetClientIdentity().GetID()
	if err != nil {
		return fmt.Errorf("failed to get client id: %v", err)
	}

	// Check whether operator is owner or approved
	if operator != sender {
		approved, err := _isApprovedForAll(ctx, sender, operator)
		if err != nil {
			return err
		}
		if !approved {
			return fmt.Errorf("caller is not owner nor is approved")
		}
	}

	// Withdraw the funds from the sender address
	err = removeBalance(ctx, sender, []uint64{id}, []uint64{amount})
	if err != nil {
		return err
	}

	if recipient == "0x0" {
		return fmt.Errorf("transfer to the zero address")
	}

	// Deposit the fund to the recipient address
	err = addBalance(ctx, sender, recipient, id, amount)
	if err != nil {
		return err
	}

	// Emit TransferSingle event
	transferSingleEvent := TransferSingle{operator, sender, recipient, id, amount}
	return emitTransferSingle(ctx, transferSingleEvent)
}

// BatchTransferFrom transfers multiple tokens from sender account to recipient account
// recipient account must be a valid clientID as returned by the ClientID() function
// This function triggers a TransferBatch event
func (s *SmartContract) BatchTransferFrom(ctx contractapi.TransactionContextInterface, sender string, recipient string, ids []uint64, amounts []uint64) error {

	// Check if contract has been intilized first
	initialized, err := checkInitialized(ctx)
	if err != nil {
		return fmt.Errorf("failed to check if contract is already initialized: %v", err)
	}
	if !initialized {
		return fmt.Errorf("Contract options need to be set before calling any function, call Initialize() to initialize contract")
	}

	if sender == recipient {
		return fmt.Errorf("transfer to self")
	}

	if len(ids) != len(amounts) {
		return fmt.Errorf("ids and amounts must have the same length")
	}

	// Get ID of submitting client identity
	operator, err := ctx.GetClientIdentity().GetID()
	if err != nil {
		return fmt.Errorf("failed to get client id: %v", err)
	}

	// Check whether operator is owner or approved
	if operator != sender {
		approved, err := _isApprovedForAll(ctx, sender, operator)
		if err != nil {
			return err
		}
		if !approved {
			return fmt.Errorf("caller is not owner nor is approved")
		}
	}

	// Withdraw the funds from the sender address
	err = removeBalance(ctx, sender, ids, amounts)
	if err != nil {
		return err
	}

	if recipient == "0x0" {
		return fmt.Errorf("transfer to the zero address")
	}

	// Group amount by token id because we can only send token to a recipient only one time in a block. This prevents key conflicts
	amountToSend := make(map[uint64]uint64) // token id => amount

	for i := 0; i < len(amounts); i++ {
		amountToSend[ids[i]], err = add(amountToSend[ids[i]], amounts[i])
		if err != nil {
			return err
		}
	}

	// Copy the map keys and sort it. This is necessary because iterating maps in Go is not deterministic
	amountToSendKeys := sortedKeys(amountToSend)

	// Deposit the funds to the recipient address
	for _, id := range amountToSendKeys {
		amount := amountToSend[id]
		err = addBalance(ctx, sender, recipient, id, amount)
		if err != nil {
			return err
		}
	}

	transferBatchEvent := TransferBatch{operator, sender, recipient, ids, amounts}
	return emitTransferBatch(ctx, transferBatchEvent)
}

// BatchTransferFromMultiRecipient transfers multiple tokens from sender account to multiple recipient accounts
// recipient account must be a valid clientID as returned by the ClientID() function
// This function triggers a TransferBatchMultiRecipient event
func (s *SmartContract) BatchTransferFromMultiRecipient(ctx contractapi.TransactionContextInterface, sender string, recipients []string, ids []uint64, amounts []uint64) error {

	// Check if contract has been intilized first
	initialized, err := checkInitialized(ctx)
	if err != nil {
		return fmt.Errorf("failed to check if contract is already initialized: %v", err)
	}
	if !initialized {
		return fmt.Errorf("Contract options need to be set before calling any function, call Initialize() to initialize contract")
	}

	if len(recipients) != len(ids) || len(ids) != len(amounts) {
		return fmt.Errorf("recipients, ids, and amounts must have the same length")
	}

	for _, recipient := range recipients {
		if sender == recipient {
			return fmt.Errorf("transfer to self")
		}
	}

	// Get ID of submitting client identity
	operator, err := ctx.GetClientIdentity().GetID()
	if err != nil {
		return fmt.Errorf("failed to get client id: %v", err)
	}

	// Check whether operator is owner or approved
	if operator != sender {
		approved, err := _isApprovedForAll(ctx, sender, operator)
		if err != nil {
			return err
		}
		if !approved {
			return fmt.Errorf("caller is not owner nor is approved")
		}
	}

	// Withdraw the funds from the sender address
	err = removeBalance(ctx, sender, ids, amounts)
	if err != nil {
		return err
	}

	// Group amount by (recipient, id ) pair because we can only send token to a recipient only one time in a block. This prevents key conflicts
	amountToSend := make(map[ToID]uint64) // (recipient, id ) => amount

	for i := 0; i < len(amounts); i++ {
		amountToSend[ToID{recipients[i], ids[i]}], err = add(amountToSend[ToID{recipients[i], ids[i]}], amounts[i])
		if err != nil {
			return err
		}
	}

	// Copy the map keys and sort it. This is necessary because iterating maps in Go is not deterministic
	amountToSendKeys := sortedKeysToID(amountToSend)

	// Deposit the funds to the recipient addresses
	for _, key := range amountToSendKeys {
		if key.To == "0x0" {
			return fmt.Errorf("transfer to the zero address")
		}

		amount := amountToSend[key]

		err = addBalance(ctx, sender, key.To, key.ID, amount)
		if err != nil {
			return err
		}
	}

	// Emit TransferBatchMultiRecipient event
	transferBatchMultiRecipientEvent := TransferBatchMultiRecipient{operator, sender, recipients, ids, amounts}
	return emitTransferBatchMultiRecipient(ctx, transferBatchMultiRecipientEvent)
}

// IsApprovedForAll returns true if operator is approved to transfer account's tokens.
func (s *SmartContract) IsApprovedForAll(ctx contractapi.TransactionContextInterface, account string, operator string) (bool, error) {
	return _isApprovedForAll(ctx, account, operator)
}

// _isApprovedForAll returns true if operator is approved to transfer account's tokens.
func _isApprovedForAll(ctx contractapi.TransactionContextInterface, account string, operator string) (bool, error) {

	// Check if contract has been intilized first
	initialized, err := checkInitialized(ctx)
	if err != nil {
		return false, fmt.Errorf("failed to check if contract is already initialized: %v", err)
	}
	if !initialized {
		return false, fmt.Errorf("Contract options need to be set before calling any function, call Initialize() to initialize contract")
	}

	approvalKey, err := ctx.GetStub().CreateCompositeKey(approvalPrefix, []string{account, operator})
	if err != nil {
		return false, fmt.Errorf("failed to create the composite key for prefix %s: %v", approvalPrefix, err)
	}

	approvalBytes, err := ctx.GetStub().GetState(approvalKey)
	if err != nil {
		return false, fmt.Errorf("failed to read approval of operator %s for account %s from world state: %v", operator, account, err)
	}

	if approvalBytes == nil {
		return false, nil
	}

	var approved bool
	err = json.Unmarshal(approvalBytes, &approved)
	if err != nil {
		return false, fmt.Errorf("failed to decode approval JSON of operator %s for account %s: %v", operator, account, err)
	}

	return approved, nil
}

// SetApprovalForAll returns true if operator is approved to transfer account's tokens.
func (s *SmartContract) SetApprovalForAll(ctx contractapi.TransactionContextInterface, operator string, approved bool) error {

	// Check if contract has been intilized first
	initialized, err := checkInitialized(ctx)
	if err != nil {
		return fmt.Errorf("failed to check if contract is already initialized: %v", err)
	}
	if !initialized {
		return fmt.Errorf("Contract options need to be set before calling any function, call Initialize() to initialize contract")
	}

	// Get ID of submitting client identity
	account, err := ctx.GetClientIdentity().GetID()
	if err != nil {
		return fmt.Errorf("failed to get client id: %v", err)
	}

	if account == operator {
		return fmt.Errorf("setting approval status for self")
	}

	approvalForAllEvent := ApprovalForAll{account, operator, approved}
	approvalForAllEventJSON, err := json.Marshal(approvalForAllEvent)
	if err != nil {
		return fmt.Errorf("failed to obtain JSON encoding: %v", err)
	}
	err = ctx.GetStub().SetEvent("ApprovalForAll", approvalForAllEventJSON)
	if err != nil {
		return fmt.Errorf("failed to set event: %v", err)
	}

	approvalKey, err := ctx.GetStub().CreateCompositeKey(approvalPrefix, []string{account, operator})
	if err != nil {
		return fmt.Errorf("failed to create the composite key for prefix %s: %v", approvalPrefix, err)
	}

	approvalJSON, err := json.Marshal(approved)
	if err != nil {
		return fmt.Errorf("failed to encode approval JSON of operator %s for account %s: %v", operator, account, err)
	}

	err = ctx.GetStub().PutState(approvalKey, approvalJSON)
	if err != nil {
		return err
	}

	return nil
}

// BalanceOf returns the balance of the given account
func (s *SmartContract) BalanceOf(ctx contractapi.TransactionContextInterface, account string, id uint64) (uint64, error) {

	// Check if contract has been intilized first
	initialized, err := checkInitialized(ctx)
	if err != nil {
		return 0, fmt.Errorf("failed to check if contract is already initialized: %v", err)
	}
	if !initialized {
		return 0, fmt.Errorf("Contract options need to be set before calling any function, call Initialize() to initialize contract")
	}

	return balanceOfHelper(ctx, account, id)
}

// BalanceOfBatch returns the balance of multiple account/token pairs
func (s *SmartContract) BalanceOfBatch(ctx contractapi.TransactionContextInterface, accounts []string, ids []uint64) ([]uint64, error) {

	// Check if contract has been intilized first
	initialized, err := checkInitialized(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to check if contract is already initialized: %v", err)
	}
	if !initialized {
		return nil, fmt.Errorf("Contract options need to be set before calling any function, call Initialize() to initialize contract")
	}

	if len(accounts) != len(ids) {
		return nil, fmt.Errorf("accounts and ids must have the same length")
	}

	balances := make([]uint64, len(accounts))

	for i := 0; i < len(accounts); i++ {
		var err error
		balances[i], err = balanceOfHelper(ctx, accounts[i], ids[i])
		if err != nil {
			return nil, err
		}
	}

	return balances, nil
}

// ClientAccountBalance returns the balance of the requesting client's account
func (s *SmartContract) ClientAccountBalance(ctx contractapi.TransactionContextInterface, id uint64) (uint64, error) {

	// Check if contract has been intilized first
	initialized, err := checkInitialized(ctx)
	if err != nil {
		return 0, fmt.Errorf("failed to check if contract is already initialized: %v", err)
	}
	if !initialized {
		return 0, fmt.Errorf("Contract options need to be set before calling any function, call Initialize() to initialize contract")
	}

	// Get ID of submitting client identity
	clientID, err := ctx.GetClientIdentity().GetID()
	if err != nil {
		return 0, fmt.Errorf("failed to get client id: %v", err)
	}

	return balanceOfHelper(ctx, clientID, id)
}

// ClientAccountID returns the id of the requesting client's account
// In this implementation, the client account ID is the clientId itself
// Users can use this function to get their own account id, which they can then give to others as the payment address
func (s *SmartContract) ClientAccountID(ctx contractapi.TransactionContextInterface) (string, error) {

	// Check if contract has been intilized first
	initialized, err := checkInitialized(ctx)
	if err != nil {
		return "", fmt.Errorf("failed to check if contract is already initialized: %v", err)
	}
	if !initialized {
		return "", fmt.Errorf("Contract options need to be set before calling any function, call Initialize() to initialize contract")
	}

	// Get ID of submitting client identity
	clientAccountID, err := ctx.GetClientIdentity().GetID()
	if err != nil {
		return "", fmt.Errorf("failed to get client id: %v", err)
	}

	return clientAccountID, nil
}

// SetURI set the URI value
// This function triggers URI event for each token id
func (s *SmartContract) SetURI(ctx contractapi.TransactionContextInterface, uri string, instanceID string) error {

	// Check if contract has been intilized first
	initialized, err := checkInitialized(ctx)
	if err != nil {
		return fmt.Errorf("failed to check if contract is already initialized: %v", err)
	}
	if !initialized {
		return fmt.Errorf("Contract options need to be set before calling any function, call Initialize() to initialize contract")
	}

	// Check minter authorization - this sample assumes Org1 is the central banker with privilege to mint new tokens
	err = authorizationHelper(ctx, instanceID)
	if err != nil {
		return err
	}

	if !strings.Contains(uri, "{id}") {
		return fmt.Errorf("failed to set uri, uri should contain '{id}'")
	}

	err = ctx.GetStub().PutState(uriKey, []byte(uri))
	if err != nil {
		return fmt.Errorf("failed to set uri: %v", err)
	}

	return nil
}

// URI returns the URI
func (s *SmartContract) URI(ctx contractapi.TransactionContextInterface, id uint64) (string, error) {

	// Check if contract has been intilized first
	initialized, err := checkInitialized(ctx)
	if err != nil {
		return "", fmt.Errorf("failed to check if contract is already initialized: %v", err)
	}
	if !initialized {
		return "", fmt.Errorf("Contract options need to be set before calling any function, call Initialize() to initialize contract")
	}

	uriBytes, err := ctx.GetStub().GetState(uriKey)
	if err != nil {
		return "", fmt.Errorf("failed to get uri: %v", err)
	}

	if uriBytes == nil {
		return "", fmt.Errorf("no uri is set: %v", err)
	}

	return string(uriBytes), nil
}

func (s *SmartContract) BroadcastTokenExistance(ctx contractapi.TransactionContextInterface, id uint64, instanceID string) error {

	// Check if contract has been intilized first
	initialized, err := checkInitialized(ctx)
	if err != nil {
		return fmt.Errorf("failed to check if contract is already initialized: %v", err)
	}
	if !initialized {
		return fmt.Errorf("Contract options need to be set before calling any function, call Initialize() to initialize contract")
	}

	// Check minter authorization - this sample assumes Org1 is the central banker with privilege to mint new tokens
	err = authorizationHelper(ctx, instanceID)
	if err != nil {
		return err
	}

	// Get ID of submitting client identity
	operator, err := ctx.GetClientIdentity().GetID()
	if err != nil {
		return fmt.Errorf("failed to get client id: %v", err)
	}

	// Emit TransferSingle event
	transferSingleEvent := TransferSingle{operator, "0x0", "0x0", id, 0}
	return emitTransferSingle(ctx, transferSingleEvent)
}

// Name returns a descriptive name for fungible tokens in this contract
// returns {String} Returns the name of the token

func (s *SmartContract) Name(ctx contractapi.TransactionContextInterface) (string, error) {

	// Check if contract has been intilized first
	initialized, err := checkInitialized(ctx)
	if err != nil {
		return "", fmt.Errorf("failed to check if contract is already initialized: %v", err)
	}
	if !initialized {
		return "", fmt.Errorf("Contract options need to be set before calling any function, call Initialize() to initialize contract")
	}

	bytes, err := ctx.GetStub().GetState(nameKey)
	if err != nil {
		return "", fmt.Errorf("failed to get Name bytes: %s", err)
	}

	return string(bytes), nil
}

// Symbol returns an abbreviated name for fungible tokens in this contract.
// returns {String} Returns the symbol of the token

func (s *SmartContract) Symbol(ctx contractapi.TransactionContextInterface) (string, error) {

	// Check if contract has been intilized first
	initialized, err := checkInitialized(ctx)
	if err != nil {
		return "", fmt.Errorf("failed to check if contract is already initialized: %v", err)
	}
	if !initialized {
		return "", fmt.Errorf("Contract options need to be set before calling any function, call Initialize() to initialize contract")
	}

	bytes, err := ctx.GetStub().GetState(symbolKey)
	if err != nil {
		return "", fmt.Errorf("failed to get Symbol: %v", err)
	}

	return string(bytes), nil
}

// Set information for a token and intialize contract.
// param {String} name The name of the token
// param {String} symbol The symbol of the token
func (s *SmartContract) Initialize(ctx contractapi.TransactionContextInterface, name string, symbol string) (bool, error) {

	// Check minter authorization - this sample assumes Org1 is the central banker with privilege to intitialize contract

	// Check contract options are not already set, client is not authorized to change them once intitialized
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
		return false, fmt.Errorf("failed to set symbol: %v", err)
	}

	return true, nil
}

// Helper Functions

// authorizationHelper checks minter authorization - this sample assumes Org1 is the central banker with privilege to mint new tokens
func authorizationHelper(ctx contractapi.TransactionContextInterface, instanceID string) error {

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

func mintHelper(ctx contractapi.TransactionContextInterface, operator string, account string, id uint64, amount uint64) error {
	if account == "0x0" {
		return fmt.Errorf("mint to the zero address")
	}

	if amount <= 0 {
		return fmt.Errorf("mint amount must be a positive integer")
	}

	err := addBalance(ctx, operator, account, id, amount)
	if err != nil {
		return err
	}

	return nil
}

func addBalance(ctx contractapi.TransactionContextInterface, sender string, recipient string, id uint64, amount uint64) error {
	// Convert id to string

	fmt.Printf("LOG: >>> addBalance called. Recipient: %s, ID: %d, Amount: %d, Sender(from): %s\n", base64decoding(recipient), id, amount, base64decoding(sender))
	idString := strconv.FormatUint(uint64(id), 10)

	balanceKey, err := ctx.GetStub().CreateCompositeKey(balancePrefix, []string{recipient, idString, sender})
	if err != nil {
		return fmt.Errorf("failed to create the composite key for prefix %s: %v", balancePrefix, err)
	}

	balanceBytes, err := ctx.GetStub().GetState(balanceKey)
	if err != nil {
		return fmt.Errorf("failed to read account %s from world state: %v", recipient, err)
	}

	var balance uint64 = 0
	if balanceBytes != nil {
		balance, _ = strconv.ParseUint(string(balanceBytes), 10, 64)
	}
	fmt.Printf("LOG: addBalance  %s is %d. Adding %d.\n", base64decoding(recipient), balance, amount)
	balance, err = add(balance, amount)
	if err != nil {
		return err
	}

	err = ctx.GetStub().PutState(balanceKey, []byte(strconv.FormatUint(uint64(balance), 10)))
	if err != nil {
		return err
	}
	fmt.Printf("LOG: addBalance new balance  %s set to %d.\n", base64decoding(recipient), balance)
	return nil
}

func setBalance(ctx contractapi.TransactionContextInterface, sender string, recipient string, id uint64, amount uint64) error {
	fmt.Printf("LOG: >>> setBalance called. Recipient: %s, ID: %d, New Amount: %d, Sender(from): %s\n", base64decoding(recipient), id, amount, base64decoding(sender))

	// Convert id to string
	idString := strconv.FormatUint(uint64(id), 10)

	balanceKey, err := ctx.GetStub().CreateCompositeKey(balancePrefix, []string{recipient, idString, sender})
	if err != nil {
		return fmt.Errorf("failed to create the composite key for prefix %s: %v", balancePrefix, err)
	}
	fmt.Printf("LOG: 用户%s 的%s set balance to %d.\n", base64decoding(recipient), idString, amount)
	err = ctx.GetStub().PutState(balanceKey, []byte(strconv.FormatUint(uint64(amount), 10)))
	if err != nil {
		return err
	}

	return nil
}

func removeBalance(ctx contractapi.TransactionContextInterface, sender string, ids []uint64, amounts []uint64) error {
	fmt.Printf("LOG: >>> removeBalance called. Sender: %s, Removing %d items (IDs: %v, Amounts: %v)\n", base64decoding(sender), len(ids), ids, amounts)

	// Calculate the total amount of each token to withdraw
	necessaryFunds := make(map[uint64]uint64) // token id -> necessary amount
	var err error

	for i := 0; i < len(amounts); i++ {
		necessaryFunds[ids[i]], err = add(necessaryFunds[ids[i]], amounts[i])
		if err != nil {
			return err
		}
	}

	// Copy the map keys and sort it. This is necessary because iterating maps in Go is not deterministic
	necessaryFundsKeys := sortedKeys(necessaryFunds)

	// Check whether the sender has the necessary funds and withdraw them from the account
	for _, tokenId := range necessaryFundsKeys {
		neededAmount := necessaryFunds[tokenId]
		idString := strconv.FormatUint(uint64(tokenId), 10)
		fmt.Printf("LOG: removeBalance processing Token ID: %d. Needed Amount: %d.\n", tokenId, neededAmount)
		var partialBalance uint64
		var selfRecipientKeyNeedsToBeRemoved bool
		var selfRecipientKey string

		balanceIterator, err := ctx.GetStub().GetStateByPartialCompositeKey(balancePrefix, []string{sender, idString})
		if err != nil {
			return fmt.Errorf("failed to get state for prefix %v: %v", balancePrefix, err)
		}
		defer balanceIterator.Close()

		// Iterate over keys that store balances and add them to partialBalance until
		// either the necessary amount is reached or the keys ended
		for balanceIterator.HasNext() && partialBalance < neededAmount {
			queryResponse, err := balanceIterator.Next()
			if err != nil {
				return fmt.Errorf("failed to get the next state for prefix %v: %v", balancePrefix, err)
			}

			partBalAmount, _ := strconv.ParseUint(string(queryResponse.Value), 10, 64)

			partialBalance, err = add(partialBalance, partBalAmount)
			if err != nil {
				return err
			}

			_, compositeKeyParts, err := ctx.GetStub().SplitCompositeKey(queryResponse.Key)
			if err != nil {
				return err
			}

			if compositeKeyParts[2] == sender {
				selfRecipientKeyNeedsToBeRemoved = true
				selfRecipientKey = queryResponse.Key

			} else {
				err = ctx.GetStub().DelState(queryResponse.Key)
				if err != nil {
					return fmt.Errorf("failed to delete the state of %v: %v", queryResponse.Key, err)
				}
				fmt.Printf("LOG: removeBalance deleted non-self-recipient key: %s\n", queryResponse.Key)
			}
		}

		if partialBalance < neededAmount {
			return fmt.Errorf("sender has insufficient funds for token %v, needed funds: %v, available fund: %v", tokenId, neededAmount, partialBalance)
		} else if partialBalance > neededAmount {
			// Send the remainder back to the sender
			remainder, err := sub(partialBalance, neededAmount)
			if err != nil {
				return err
			}
			fmt.Printf("LOG: removeBalance needed %d, available %d. Remainder is %d.\n", neededAmount, partialBalance, remainder)
			if selfRecipientKeyNeedsToBeRemoved {
				// Set balance for the key that has the same address for sender and recipient
				err = setBalance(ctx, sender, sender, tokenId, remainder)
				if err != nil {
					return err
				}
			} else {
				fmt.Printf("LOG: removeBalance adding remainder %d back to self-recipient via addBalance\n", remainder)
				err = addBalance(ctx, sender, sender, tokenId, remainder)
				if err != nil {
					return err
				}
			}

		} else {
			// Delete self recipient key
			fmt.Printf("LOG: removeBalance exact match, deleting self-recipient key: %s\n", selfRecipientKey)
			err = ctx.GetStub().DelState(selfRecipientKey)
			if err != nil {
				return fmt.Errorf("failed to delete the state of %v: %v", selfRecipientKey, err)
			}
		}
	}

	return nil
}

func emitTransferSingle(ctx contractapi.TransactionContextInterface, transferSingleEvent TransferSingle) error {
	transferSingleEventJSON, err := json.Marshal(transferSingleEvent)
	if err != nil {
		return fmt.Errorf("failed to obtain JSON encoding: %v", err)
	}

	err = ctx.GetStub().SetEvent("TransferSingle", transferSingleEventJSON)
	if err != nil {
		return fmt.Errorf("failed to set event: %v", err)
	}

	return nil
}

func emitTransferBatch(ctx contractapi.TransactionContextInterface, transferBatchEvent TransferBatch) error {
	transferBatchEventJSON, err := json.Marshal(transferBatchEvent)
	if err != nil {
		return fmt.Errorf("failed to obtain JSON encoding: %v", err)
	}
	err = ctx.GetStub().SetEvent("TransferBatch", transferBatchEventJSON)
	if err != nil {
		return fmt.Errorf("failed to set event: %v", err)
	}

	return nil
}

func emitTransferBatchMultiRecipient(ctx contractapi.TransactionContextInterface, transferBatchMultiRecipientEvent TransferBatchMultiRecipient) error {
	transferBatchMultiRecipientEventJSON, err := json.Marshal(transferBatchMultiRecipientEvent)
	if err != nil {
		return fmt.Errorf("failed to obtain JSON encoding: %v", err)
	}
	err = ctx.GetStub().SetEvent("TransferBatchMultiRecipient", transferBatchMultiRecipientEventJSON)
	if err != nil {
		return fmt.Errorf("failed to set event: %v", err)
	}

	return nil
}

// balanceOfHelper returns the balance of the given account
func balanceOfHelper(ctx contractapi.TransactionContextInterface, account string, id uint64) (uint64, error) {

	if account == "0x0" {
		return 0, fmt.Errorf("balance query for the zero address")
	}

	// Convert id to string
	idString := strconv.FormatUint(uint64(id), 10)

	var balance uint64

	balanceIterator, err := ctx.GetStub().GetStateByPartialCompositeKey(balancePrefix, []string{account, idString})
	if err != nil {
		return 0, fmt.Errorf("failed to get state for prefix %v: %v", balancePrefix, err)
	}
	defer balanceIterator.Close()

	for balanceIterator.HasNext() {
		queryResponse, err := balanceIterator.Next()
		if err != nil {
			return 0, fmt.Errorf("failed to get the next state for prefix %v: %v", balancePrefix, err)
		}

		balAmount, _ := strconv.ParseUint(string(queryResponse.Value), 10, 64)
		balance, err = add(balance, balAmount)
		if err != nil {
			return 0, err
		}
	}

	return balance, nil
}

// Returns the sorted slice ([]uint64) copied from the keys of map[uint64]uint64
func sortedKeys(m map[uint64]uint64) []uint64 {
	// Copy map keys to slice
	keys := make([]uint64, len(m))
	i := 0
	for k := range m {
		keys[i] = k
		i++
	}
	// Sort the slice
	sort.Slice(keys, func(i, j int) bool { return keys[i] < keys[j] })
	return keys
}

// Returns the sorted slice ([]ToID) copied from the keys of map[ToID]uint64
func sortedKeysToID(m map[ToID]uint64) []ToID {
	// Copy map keys to slice
	keys := make([]ToID, len(m))
	i := 0
	for k := range m {
		keys[i] = k
		i++
	}
	// Sort the slice first according to ID if equal then sort by recipient ("To" field)
	sort.Slice(keys, func(i, j int) bool {
		if keys[i].ID != keys[j].ID {
			return keys[i].To < keys[j].To
		}
		return keys[i].ID < keys[j].ID
	})
	return keys
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

// add two number checking for overflow
func add(b uint64, q uint64) (uint64, error) {

	// Check overflow
	var sum uint64
	sum = q + b

	if sum < q {
		return 0, fmt.Errorf("Math: addition overflow occurred %d + %d", b, q)
	}

	return sum, nil
}

// sub two number checking for overflow
func sub(b uint64, q uint64) (uint64, error) {

	// Check overflow
	var diff uint64
	diff = b - q

	if diff > b {
		return 0, fmt.Errorf("Math: subtraction overflow occurred  %d - %d", b, q)
	}

	return diff, nil
}
