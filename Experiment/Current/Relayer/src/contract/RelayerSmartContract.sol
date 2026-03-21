// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface RelayerSmartContract {
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

    // ===== key state getters (for core variables) =====
    function owner() external view returns (address);
    function defaultThreshold() external view returns (uint256);
    function registeredNodeCount() external view returns (uint256);
    function processedCount() external view returns (uint256);
    function relayNodeActive(address node) external view returns (bool);
    function processedMsgIds(bytes32 msgId) external view returns (bool);

    // ===== relay node registration =====
    function setRelayNode(address node, bool active) external;
    function setRelayNodes(address[] calldata nodes, bool active) external;
    function setDefaultThreshold(uint256 threshold) external;

    // ===== cross-chain request publish / query =====
    function buildMessageId(RelayRequest calldata req) external view returns (bytes32);
    function getRecord(bytes32 msgId) external view returns (RelayRecord memory);
    function getRequestPayloadHash(bytes32 msgId) external view returns (bytes32);
    function isConfirmedBy(bytes32 msgId, address signer) external view returns (bool);

    // ===== two-step relay pipeline =====
    function submitRequest(
        RelayRequest calldata req
    ) external returns (RelayStatus status, bytes32 msgId);
    function submitConfirmations(
        bytes32 msgId,
        bytes[] calldata signatures
    ) external returns (RelayStatus status, uint256 confirmations);
    function executeRequest(
        bytes32 msgId
    ) external returns (RelayStatus status, bytes memory result);
    function confirmAndExecute(
        bytes32 msgId,
        bytes[] calldata signatures
    )
        external
        returns (
            RelayStatus status,
            uint256 confirmations,
            bytes memory result
        );

    // ===== one-step compatibility =====
    function submitAndExecute(
        RelayRequest calldata req,
        bytes[] calldata signatures
    )
        external
        returns (
            RelayStatus status,
            bytes32 msgId,
            uint256 confirmations,
            bytes memory result
        );
}
