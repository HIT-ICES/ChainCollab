// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract customer_newSubmodelB {
    enum RelayStatus {
        Rejected,
        Pending,
        Accepted,
        AlreadyProcessed
    }

    struct Delivery {
        bool processed;
        bytes32 msgId;
        bytes32 payloadHash;
        address relayer;
        uint256 sourceChainId;
        uint256 targetChainId;
        address sourceContract;
        uint256 confirmations;
        uint256 firstSeenAt;
        uint256 processedAt;
    }

    struct TaskRuntime {
        uint256 nextOrder;
        uint256 executedCount;
        bytes32 lastPayloadHash;
        address lastCaller;
        uint256 updatedAt;
    }

    address public owner;
    uint256 public processedCount;
    uint256 public confirmationThreshold = 1;
    mapping(address => bool) public allowedRelayers;
    mapping(bytes32 => Delivery) private deliveries;
    mapping(bytes32 => bool) private processedMsgIds;
    mapping(bytes32 => TaskRuntime) private taskRuntime;
    mapping(bytes32 => mapping(bytes32 => bool)) private nodeExecuted;
    mapping(bytes32 => mapping(address => bool)) private confirmedBy;
    bytes32 private constant RELAY_DOMAIN = keccak256("BPMN_SPLIT_RELAY_V1");

    event RelayerUpdated(address indexed relayer, bool allowed);
    event ConfirmationThresholdUpdated(uint256 threshold);
    event ConfirmationAdded(
        bytes32 indexed taskId,
        bytes32 indexed msgId,
        address indexed signer,
        uint256 confirmations
    );
    event ConfirmationPending(
        bytes32 indexed taskId,
        bytes32 indexed msgId,
        uint256 confirmations,
        uint256 threshold
    );
    event HandoffAlreadyProcessed(bytes32 indexed taskId, bytes32 indexed msgId);
    event HandoffAccepted(
        bytes32 indexed taskId,
        bytes32 indexed msgId,
        bytes32 payloadHash,
        address indexed relayer,
        uint256 sourceChainId,
        address sourceContract,
        uint256 confirmations
    );
    event NodeExecuted(
        bytes32 indexed taskId,
        string nodeId,
        bytes32 payloadHash,
        address indexed caller,
        uint256 at
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

    function setConfirmationThreshold(uint256 threshold) external onlyOwner {
        require(threshold > 0, "threshold must be > 0");
        confirmationThreshold = threshold;
        emit ConfirmationThresholdUpdated(threshold);
    }

    function acceptHandoff(
        bytes32 taskId,
        bytes32 payloadHash,
        uint256 sourceChainId,
        address sourceContract,
        bytes calldata signature
    ) external returns (RelayStatus status) {
        bytes[] memory signatures = new bytes[](1);
        signatures[0] = signature;
        (status,,) = acceptHandoffWithSignatures(
            taskId,
            payloadHash,
            sourceChainId,
            sourceContract,
            block.chainid,
            signatures
        );
    }

    function acceptHandoff(
        bytes32 taskId,
        bytes32 payloadHash,
        uint256 sourceChainId,
        address sourceContract,
        uint256 targetChainId,
        bytes[] calldata signatures
    ) external returns (RelayStatus status, bytes32 msgId, uint256 confirmations) {
        return acceptHandoffWithSignatures(
            taskId,
            payloadHash,
            sourceChainId,
            sourceContract,
            targetChainId,
            signatures
        );
    }

    function acceptHandoffWithSignatures(
        bytes32 taskId,
        bytes32 payloadHash,
        uint256 sourceChainId,
        address sourceContract,
        uint256 targetChainId,
        bytes[] memory signatures
    ) public returns (RelayStatus status, bytes32 msgId, uint256 confirmations) {
        if (taskId == bytes32(0) || payloadHash == bytes32(0) || sourceContract == address(0)) {
            return (RelayStatus.Rejected, bytes32(0), 0);
        }
        if (targetChainId != block.chainid) {
            return (RelayStatus.Rejected, bytes32(0), 0);
        }
        if (!allowedRelayers[msg.sender]) {
            return (RelayStatus.Rejected, bytes32(0), 0);
        }

        msgId = _buildMessageId(taskId, payloadHash, sourceChainId, sourceContract, targetChainId);
        if (processedMsgIds[msgId]) {
            emit HandoffAlreadyProcessed(taskId, msgId);
            return (RelayStatus.AlreadyProcessed, msgId, deliveries[taskId].confirmations);
        }
        Delivery storage d = deliveries[taskId];
        if (d.firstSeenAt == 0) {
            deliveries[taskId] = Delivery({
                processed: false,
                msgId: msgId,
                payloadHash: payloadHash,
                relayer: address(0),
                sourceChainId: sourceChainId,
                targetChainId: targetChainId,
                sourceContract: sourceContract,
                confirmations: 0,
                firstSeenAt: block.timestamp,
                processedAt: 0
            });
            d = deliveries[taskId];
        } else {
            if (
                d.msgId != msgId ||
                d.payloadHash != payloadHash ||
                d.sourceChainId != sourceChainId ||
                d.targetChainId != targetChainId ||
                d.sourceContract != sourceContract
            ) {
                return (RelayStatus.Rejected, msgId, d.confirmations);
            }
        }

        if (d.processed) {
            emit HandoffAlreadyProcessed(taskId, d.msgId);
            return (RelayStatus.AlreadyProcessed, d.msgId, d.confirmations);
        }

        bytes32 digest = _toEthSignedMessageHash(
            _relayDigest(taskId, payloadHash, sourceChainId, sourceContract, targetChainId)
        );
        uint256 added = _collectValidConfirmations(
            taskId,
            d.msgId,
            digest,
            d.confirmations,
            signatures
        );
        if (added > 0) {
            d.confirmations += added;
        }
        confirmations = d.confirmations;
        if (confirmations < confirmationThreshold) {
            emit ConfirmationPending(taskId, d.msgId, confirmations, confirmationThreshold);
            return (RelayStatus.Pending, d.msgId, confirmations);
        }

        d.processed = true;
        processedMsgIds[d.msgId] = true;
        d.relayer = msg.sender;
        d.processedAt = block.timestamp;
        taskRuntime[taskId] = TaskRuntime({
            nextOrder: 0,
            executedCount: 0,
            lastPayloadHash: payloadHash,
            lastCaller: msg.sender,
            updatedAt: block.timestamp
        });
        unchecked {
            processedCount += 1;
        }
        emit HandoffAccepted(
            taskId,
            d.msgId,
            payloadHash,
            msg.sender,
            sourceChainId,
            sourceContract,
            confirmations
        );
        return (RelayStatus.Accepted, d.msgId, confirmations);
    }

    function isProcessed(bytes32 taskId) external view returns (bool) {
        return deliveries[taskId].processed;
    }

    function isMessageProcessed(bytes32 msgId) external view returns (bool) {
        return processedMsgIds[msgId];
    }

    function getDelivery(bytes32 taskId) external view returns (Delivery memory) {
        return deliveries[taskId];
    }

    function getTaskRuntime(bytes32 taskId) external view returns (TaskRuntime memory runtime) {
        runtime = taskRuntime[taskId];
    }

    function isNodeExecuted(bytes32 taskId, string calldata nodeId) external view returns (bool) {
        bytes32 key = keccak256(bytes(nodeId));
        return nodeExecuted[taskId][key];
    }

    function executeBatch(bytes32 taskId, string[] calldata nodeIds) external {
        require(deliveries[taskId].processed, "handoff not accepted");
        require(nodeIds.length > 0, "empty node batch");
        bytes32 payloadHash = deliveries[taskId].payloadHash;
        for (uint256 i = 0; i < nodeIds.length; i++) {
            _markNodeExecuted(taskId, nodeIds[i], payloadHash);
        }
    }

    function isConfirmedBy(bytes32 taskId, address signer) external view returns (bool) {
        return confirmedBy[taskId][signer];
    }

    function _markNodeExecuted(bytes32 taskId, string memory nodeId, bytes32 payloadHash) internal {
        require(payloadHash == deliveries[taskId].payloadHash, "payload hash mismatch");
        bytes32 key = keccak256(bytes(nodeId));
        require(!nodeExecuted[taskId][key], "node already executed");

        TaskRuntime storage rt = taskRuntime[taskId];
        uint256 expectedOrder = _nodeOrder(nodeId);

        nodeExecuted[taskId][key] = true;
        if (expectedOrder >= rt.nextOrder) {
            rt.nextOrder = expectedOrder + 1;
        }
        unchecked {
            rt.executedCount += 1;
        }
        rt.lastPayloadHash = payloadHash;
        rt.lastCaller = msg.sender;
        rt.updatedAt = block.timestamp;
        emit NodeExecuted(taskId, nodeId, payloadHash, msg.sender, block.timestamp);
    }

    function _buildMessageId(
        bytes32 taskId,
        bytes32 payloadHash,
        uint256 sourceChainId,
        address sourceContract,
        uint256 targetChainId
    ) internal view returns (bytes32) {
        return keccak256(
            abi.encodePacked(
                RELAY_DOMAIN,
                address(this),
                targetChainId,
                sourceChainId,
                sourceContract,
                taskId,
                payloadHash
            )
        );
    }

    function _relayDigest(
        bytes32 taskId,
        bytes32 payloadHash,
        uint256 sourceChainId,
        address sourceContract,
        uint256 targetChainId
    ) internal view returns (bytes32) {
        return _buildMessageId(taskId, payloadHash, sourceChainId, sourceContract, targetChainId);
    }

    function _collectValidConfirmations(
        bytes32 taskId,
        bytes32 msgId,
        bytes32 digest,
        uint256 baseConfirmations,
        bytes[] memory signatures
    ) internal returns (uint256 added) {
        if (signatures.length == 0) {
            return 0;
        }
        for (uint256 i = 0; i < signatures.length; i++) {
            address signer = _tryRecoverSigner(digest, signatures[i]);
            if (signer == address(0)) {
                continue;
            }
            if (!allowedRelayers[signer]) {
                continue;
            }
            if (confirmedBy[taskId][signer]) {
                continue;
            }
            confirmedBy[taskId][signer] = true;
            unchecked {
                added += 1;
            }
            emit ConfirmationAdded(taskId, msgId, signer, baseConfirmations + added);
        }
    }

    function _toEthSignedMessageHash(bytes32 hash) internal pure returns (bytes32) {
        return keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", hash));
    }

    function _tryRecoverSigner(bytes32 digest, bytes memory signature) internal pure returns (address) {
        if (signature.length != 65) {
            return address(0);
        }
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
        if (!(v == 27 || v == 28)) {
            return address(0);
        }
        address recovered = ecrecover(digest, v, r, s);
        return recovered;
    }
    function _nodeOrder(string memory nodeId) internal pure returns (uint256) {
        if (keccak256(bytes(nodeId)) == keccak256(bytes("UNKNOWN"))) return 0;
        revert("unknown node id");
    }

    function UNKNOWN(bytes32 taskId) external {
        require(deliveries[taskId].processed, "handoff not accepted");
        _markNodeExecuted(taskId, "UNKNOWN", deliveries[taskId].payloadHash);
    }
}
