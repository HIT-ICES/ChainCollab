// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract ManufactorySubmodelB {
    struct Delivery {
        bool processed;
        bytes32 payloadHash;
        address relayer;
        uint256 sourceChainId;
        address sourceContract;
        uint256 processedAt;
    }

    address public owner;
    uint256 public processedCount;
    mapping(address => bool) public allowedRelayers;
    mapping(bytes32 => Delivery) private deliveries;
    bytes32 private constant RELAY_DOMAIN = keccak256("BPMN_SPLIT_RELAY_V1");

    event RelayerUpdated(address indexed relayer, bool allowed);
    event HandoffAccepted(
        bytes32 indexed taskId,
        bytes32 payloadHash,
        address indexed relayer,
        uint256 sourceChainId,
        address indexed sourceContract
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function setRelayer(address relayer, bool allowed) external onlyOwner {
        require(relayer != address(0), "zero relayer");
        allowedRelayers[relayer] = allowed;
        emit RelayerUpdated(relayer, allowed);
    }

    function acceptHandoff(
        bytes32 taskId,
        bytes32 payloadHash,
        uint256 sourceChainId,
        address sourceContract,
        bytes calldata signature
    ) external {
        require(taskId != bytes32(0), "empty taskId");
        require(payloadHash != bytes32(0), "empty payloadHash");
        require(sourceContract != address(0), "empty sourceContract");
        require(allowedRelayers[msg.sender], "relayer not allowed");
        require(!deliveries[taskId].processed, "task already processed");

        bytes32 digest = keccak256(
            abi.encodePacked(
                RELAY_DOMAIN,
                address(this),
                block.chainid,
                sourceChainId,
                sourceContract,
                taskId,
                payloadHash
            )
        );

        address signer = _recoverSigner(_toEthSignedMessageHash(digest), signature);
        require(signer == msg.sender, "invalid relay signature");

        deliveries[taskId] = Delivery({
            processed: true,
            payloadHash: payloadHash,
            relayer: msg.sender,
            sourceChainId: sourceChainId,
            sourceContract: sourceContract,
            processedAt: block.timestamp
        });
        unchecked {
            processedCount += 1;
        }

        emit HandoffAccepted(taskId, payloadHash, msg.sender, sourceChainId, sourceContract);
    }

    function isProcessed(bytes32 taskId) external view returns (bool) {
        return deliveries[taskId].processed;
    }

    function getDelivery(bytes32 taskId) external view returns (Delivery memory) {
        return deliveries[taskId];
    }

    function _toEthSignedMessageHash(bytes32 hash) internal pure returns (bytes32) {
        return keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", hash));
    }

    function _recoverSigner(bytes32 digest, bytes memory signature) internal pure returns (address) {
        require(signature.length == 65, "invalid signature length");
        bytes32 r;
        bytes32 s;
        uint8 v;
        assembly {
            r := mload(add(signature, 0x20))
            s := mload(add(signature, 0x40))
            v := byte(0, mload(add(signature, 0x60)))
        }
        if (v < 27) {
            v += 27;
        }
        require(v == 27 || v == 28, "invalid signature v");
        address recovered = ecrecover(digest, v, r, s);
        require(recovered != address(0), "ecrecover failed");
        return recovered;
    }
}
