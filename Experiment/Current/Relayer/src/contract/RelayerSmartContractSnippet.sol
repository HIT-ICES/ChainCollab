// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @notice Thesis-friendly concise interface snippet
interface RelayerSmartContractSnippet {
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
        uint256 threshold;
    }

    struct RelayRecord {
        bool processed;
        bytes32 payloadHash;
        uint256 confirmations;
        uint256 threshold;
        uint256 processedAt;
        // ... other metadata fields omitted for brevity
    }

    // ===== core state =====
    function owner() external view returns (address);
    function defaultThreshold() external view returns (uint256);
    function relayNodeActive(address node) external view returns (bool);
    function processedMsgIds(bytes32 msgId) external view returns (bool);
    // ... other counters/getters omitted

    // ===== node registration =====
    function setRelayNode(address node, bool active) external;
    function setDefaultThreshold(uint256 threshold) external;
    // ... batch registration omitted

    // ===== relay pipeline =====
    function buildMessageId(RelayRequest calldata req) external view returns (bytes32);
    function getRecord(bytes32 msgId) external view returns (RelayRecord memory);
    function submitRequest(
        RelayRequest calldata req
    ) external returns (RelayStatus status, bytes32 msgId);
    function executeRequest(
        bytes32 msgId
    ) external returns (RelayStatus status, bytes memory result);
    // ... submitConfirmations / confirmAndExecute omitted
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
