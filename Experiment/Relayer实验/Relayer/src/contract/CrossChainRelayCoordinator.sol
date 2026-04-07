// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title CrossChainRelayCoordinator
/// @notice Threshold-based relay coordinator with node registration, signature
///         verification, replay protection, and target execution.
contract CrossChainRelayCoordinator {
    enum RelayStatus {
        Rejected,
        Pending,
        Accepted,
        AlreadyProcessed,
        ExecutionFailed
    }

    struct RelayRequest {
        bytes32 requestId;
        uint256 sourceChainId;
        address sourceContract;
        uint256 targetChainId;
        address targetContract;
        bytes payload;
        uint256 threshold; // 0 -> use global threshold
    }

    struct RelayRecord {
        bool exists;
        bool processed;
        bytes32 requestId;
        bytes32 payloadHash;
        uint256 sourceChainId;
        address sourceContract;
        uint256 targetChainId;
        address targetContract;
        uint256 confirmations;
        uint256 threshold;
        uint256 firstSeenAt;
        uint256 processedAt;
        bytes32 resultHash;
    }

    // secp256k1n/2
    uint256 private constant HALF_ORDER =
        0x7fffffffffffffffffffffffffffffff5d576e7357a4501ddfe92f46681b20a0;
    bytes32 private constant RELAY_DOMAIN = keccak256("CROSS_CHAIN_RELAY_V1");

    address public owner;
    uint256 public defaultThreshold = 1;
    uint256 public registeredNodeCount;
    uint256 public processedCount;

    mapping(address => bool) public relayNodeActive;
    mapping(bytes32 => RelayRecord) private records; // key: msgId
    mapping(bytes32 => bytes) private requestPayloads; // key: msgId
    mapping(bytes32 => bool) public processedMsgIds;
    mapping(bytes32 => mapping(address => bool)) private confirmedBy;

    event OwnerTransferred(address indexed previousOwner, address indexed newOwner);
    event RelayNodeUpdated(address indexed node, bool active);
    event DefaultThresholdUpdated(uint256 threshold);

    event RequestRegistered(
        bytes32 indexed msgId,
        bytes32 indexed requestId,
        uint256 sourceChainId,
        address indexed sourceContract,
        uint256 targetChainId,
        address targetContract,
        uint256 threshold
    );
    event ConfirmationAdded(bytes32 indexed msgId, address indexed signer, uint256 confirmations);
    event RequestPending(bytes32 indexed msgId, uint256 confirmations, uint256 threshold);
    event RequestAlreadyProcessed(bytes32 indexed msgId);
    event RequestExecuted(
        bytes32 indexed msgId,
        bytes32 indexed requestId,
        address indexed targetContract,
        bytes32 resultHash
    );
    event RequestExecutionFailed(bytes32 indexed msgId, bytes lowLevelData);
    event RequestStored(bytes32 indexed msgId, bytes32 payloadHash);

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "zero owner");
        address old = owner;
        owner = newOwner;
        emit OwnerTransferred(old, newOwner);
    }

    function setDefaultThreshold(uint256 threshold) external onlyOwner {
        require(threshold > 0, "threshold=0");
        defaultThreshold = threshold;
        emit DefaultThresholdUpdated(threshold);
    }

    function setRelayNode(address node, bool active) external onlyOwner {
        _setRelayNode(node, active);
    }

    function setRelayNodes(address[] calldata nodes, bool active) external onlyOwner {
        for (uint256 i = 0; i < nodes.length; i++) {
            _setRelayNode(nodes[i], active);
        }
    }

    function _setRelayNode(address node, bool active) internal {
        require(node != address(0), "zero node");
        bool old = relayNodeActive[node];
        if (old == active) {
            emit RelayNodeUpdated(node, active);
            return;
        }
        relayNodeActive[node] = active;
        if (active) {
            unchecked {
                registeredNodeCount += 1;
            }
        } else {
            unchecked {
                registeredNodeCount -= 1;
            }
        }
        emit RelayNodeUpdated(node, active);
    }

    function buildMessageId(RelayRequest calldata req) public view returns (bytes32) {
        bytes32 payloadHash = keccak256(req.payload);
        return _buildMessageId(req, payloadHash);
    }

    function getRecord(bytes32 msgId) external view returns (RelayRecord memory) {
        return records[msgId];
    }

    function getRequestPayloadHash(bytes32 msgId) external view returns (bytes32) {
        bytes memory payload = requestPayloads[msgId];
        if (payload.length == 0) {
            return bytes32(0);
        }
        return keccak256(payload);
    }

    function isConfirmedBy(bytes32 msgId, address signer) external view returns (bool) {
        return confirmedBy[msgId][signer];
    }

    /// @notice Step-1: submit/register relay request.
    function submitRequest(
        RelayRequest calldata req
    ) public returns (RelayStatus status, bytes32 msgId) {
        (status, msgId) = _prepareRequest(req);
        if (status != RelayStatus.Pending) {
            return (status, msgId);
        }

        RelayRecord storage rec = records[msgId];
        bytes memory existing = requestPayloads[msgId];
        if (existing.length == 0) {
            requestPayloads[msgId] = req.payload;
            emit RequestStored(msgId, rec.payloadHash);
            return (RelayStatus.Pending, msgId);
        }

        if (keccak256(existing) != rec.payloadHash) {
            return (RelayStatus.Rejected, msgId);
        }
        return (RelayStatus.Pending, msgId);
    }

    /// @notice Step-2a: submit confirmations only.
    function submitConfirmations(
        bytes32 msgId,
        bytes[] calldata signatures
    ) public returns (RelayStatus status, uint256 confirmations) {
        RelayRecord storage rec = records[msgId];
        if (!rec.exists) {
            return (RelayStatus.Rejected, 0);
        }
        if (rec.processed) {
            return (RelayStatus.AlreadyProcessed, rec.confirmations);
        }

        bytes32 digest = _toEthSignedMessageHash(msgId);
        uint256 added = _collectValidConfirmations(msgId, digest, signatures);
        if (added > 0) {
            rec.confirmations += added;
        }
        confirmations = rec.confirmations;
        if (confirmations < rec.threshold) {
            emit RequestPending(msgId, confirmations, rec.threshold);
            return (RelayStatus.Pending, confirmations);
        }
        return (RelayStatus.Accepted, confirmations);
    }

    /// @notice Step-2b: execute target call when threshold reached.
    function executeRequest(
        bytes32 msgId
    ) public returns (RelayStatus status, bytes memory result) {
        RelayRecord storage rec = records[msgId];
        if (!rec.exists) {
            return (RelayStatus.Rejected, bytes(""));
        }
        if (rec.processed) {
            return (RelayStatus.AlreadyProcessed, bytes(""));
        }
        if (rec.targetChainId != block.chainid) {
            return (RelayStatus.Rejected, bytes(""));
        }
        if (rec.confirmations < rec.threshold) {
            emit RequestPending(msgId, rec.confirmations, rec.threshold);
            return (RelayStatus.Pending, bytes(""));
        }

        bytes memory payload = requestPayloads[msgId];
        if (payload.length == 0 || keccak256(payload) != rec.payloadHash) {
            return (RelayStatus.Rejected, bytes(""));
        }

        (bool ok, bytes memory ret) = rec.targetContract.call(payload);
        if (!ok) {
            emit RequestExecutionFailed(msgId, ret);
            return (RelayStatus.ExecutionFailed, ret);
        }

        rec.processed = true;
        rec.processedAt = block.timestamp;
        rec.resultHash = keccak256(ret);
        processedMsgIds[msgId] = true;
        delete requestPayloads[msgId];
        unchecked {
            processedCount += 1;
        }

        emit RequestExecuted(msgId, rec.requestId, rec.targetContract, rec.resultHash);
        return (RelayStatus.Accepted, ret);
    }

    /// @notice Convenience: submit confirmations and trigger completion.
    function confirmAndExecute(
        bytes32 msgId,
        bytes[] calldata signatures
    ) public returns (RelayStatus status, uint256 confirmations, bytes memory result) {
        (RelayStatus s, uint256 c) = submitConfirmations(msgId, signatures);
        confirmations = c;
        if (s == RelayStatus.Rejected || s == RelayStatus.AlreadyProcessed) {
            return (s, confirmations, bytes(""));
        }
        if (s == RelayStatus.Pending) {
            return (RelayStatus.Pending, confirmations, bytes(""));
        }
        (RelayStatus execStatus, bytes memory ret) = executeRequest(msgId);
        return (execStatus, confirmations, ret);
    }

    /// @notice Entry function that matches the algorithm:
    /// 1) validate target chain and request
    /// 2) reject if already processed
    /// 3) filter invalid/duplicate signatures and count valid confirmations
    /// 4) if below threshold -> pending
    /// 5) execute target business call and mark processed
    function submitAndExecute(
        RelayRequest calldata req,
        bytes[] calldata signatures
    )
        external
        returns (RelayStatus status, bytes32 msgId, uint256 confirmations, bytes memory result)
    {
        (status, msgId) = submitRequest(req);
        if (status == RelayStatus.Rejected || status == RelayStatus.AlreadyProcessed) {
            return (status, msgId, records[msgId].confirmations, bytes(""));
        }

        (status, confirmations, result) = confirmAndExecute(msgId, signatures);
        return (status, msgId, confirmations, result);
    }

    function _prepareRequest(
        RelayRequest calldata req
    ) internal returns (RelayStatus status, bytes32 msgId) {
        if (
            req.requestId == bytes32(0) ||
            req.sourceContract == address(0) ||
            req.targetContract == address(0) ||
            req.payload.length == 0
        ) {
            return (RelayStatus.Rejected, bytes32(0));
        }
        if (req.targetChainId != block.chainid) {
            return (RelayStatus.Rejected, bytes32(0));
        }

        bytes32 payloadHash = keccak256(req.payload);
        msgId = _buildMessageId(req, payloadHash);

        if (processedMsgIds[msgId]) {
            emit RequestAlreadyProcessed(msgId);
            return (RelayStatus.AlreadyProcessed, msgId);
        }

        RelayRecord storage rec = records[msgId];
        if (!rec.exists) {
            uint256 threshold = req.threshold == 0 ? defaultThreshold : req.threshold;
            if (threshold == 0) {
                return (RelayStatus.Rejected, bytes32(0));
            }
            records[msgId] = RelayRecord({
                exists: true,
                processed: false,
                requestId: req.requestId,
                payloadHash: payloadHash,
                sourceChainId: req.sourceChainId,
                sourceContract: req.sourceContract,
                targetChainId: req.targetChainId,
                targetContract: req.targetContract,
                confirmations: 0,
                threshold: threshold,
                firstSeenAt: block.timestamp,
                processedAt: 0,
                resultHash: bytes32(0)
            });
            emit RequestRegistered(
                msgId,
                req.requestId,
                req.sourceChainId,
                req.sourceContract,
                req.targetChainId,
                req.targetContract,
                threshold
            );
            return (RelayStatus.Pending, msgId);
        }

        // same msgId should map to same immutable metadata
        if (
            rec.requestId != req.requestId ||
            rec.payloadHash != payloadHash ||
            rec.sourceChainId != req.sourceChainId ||
            rec.sourceContract != req.sourceContract ||
            rec.targetChainId != req.targetChainId ||
            rec.targetContract != req.targetContract
        ) {
            return (RelayStatus.Rejected, msgId);
        }
        if (rec.processed) {
            emit RequestAlreadyProcessed(msgId);
            return (RelayStatus.AlreadyProcessed, msgId);
        }
        return (RelayStatus.Pending, msgId);
    }

    function _buildMessageId(
        RelayRequest calldata req,
        bytes32 payloadHash
    ) internal view returns (bytes32) {
        return keccak256(
            abi.encodePacked(
                RELAY_DOMAIN,
                address(this),
                req.targetChainId,
                req.sourceChainId,
                req.sourceContract,
                req.targetContract,
                req.requestId,
                payloadHash
            )
        );
    }

    function _collectValidConfirmations(
        bytes32 msgId,
        bytes32 digest,
        bytes[] calldata signatures
    ) internal returns (uint256 added) {
        for (uint256 i = 0; i < signatures.length; i++) {
            address signer = _tryRecoverSigner(digest, signatures[i]);
            if (signer == address(0)) {
                continue;
            }
            if (!relayNodeActive[signer]) {
                continue;
            }
            if (confirmedBy[msgId][signer]) {
                continue;
            }
            confirmedBy[msgId][signer] = true;
            unchecked {
                added += 1;
            }
            emit ConfirmationAdded(msgId, signer, records[msgId].confirmations + added);
        }
    }

    function _toEthSignedMessageHash(bytes32 h) internal pure returns (bytes32) {
        return keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", h));
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
        // Reject malleable signatures.
        if (uint256(s) > HALF_ORDER) {
            return address(0);
        }
        return ecrecover(digest, v, r, s);
    }
}
