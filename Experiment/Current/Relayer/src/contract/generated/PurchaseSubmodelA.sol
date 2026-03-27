// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract PurchaseSubmodelA {
    struct HandoffTask {
        address requester;
        bytes32 payloadHash;
        uint256 nonce;
        uint256 createdAt;
    }

    struct TaskRuntime {
        uint256 nextOrder;
        uint256 executedCount;
        bytes32 lastPayloadHash;
        address lastCaller;
        uint256 updatedAt;
    }

    uint256 public nextNonce;
    mapping(bytes32 => bool) public taskExists;
    mapping(bytes32 => HandoffTask) private tasks;
    mapping(bytes32 => TaskRuntime) private taskRuntime;
    mapping(bytes32 => mapping(bytes32 => bool)) private nodeExecuted;

    event HandoffRequested(
        bytes32 indexed taskId,
        address indexed requester,
        bytes32 payloadHash,
        uint256 nonce,
        uint256 sourceChainId
    );
    event NodeExecuted(
        bytes32 indexed taskId,
        string nodeId,
        bytes32 payloadHash,
        address indexed caller,
        uint256 at
    );

    function startAndRequestHandoff(bytes32 payloadHash) external returns (bytes32 taskId) {
        require(payloadHash != bytes32(0), "empty payload hash");
        uint256 nonce = nextNonce;
        unchecked {
            nextNonce = nonce + 1;
        }
        taskId = keccak256(
            abi.encodePacked(block.chainid, address(this), msg.sender, nonce, payloadHash)
        );
        require(!taskExists[taskId], "task already exists");
        taskExists[taskId] = true;
        tasks[taskId] = HandoffTask({
            requester: msg.sender,
            payloadHash: payloadHash,
            nonce: nonce,
            createdAt: block.timestamp
        });
        taskRuntime[taskId] = TaskRuntime({
            nextOrder: 0,
            executedCount: 0,
            lastPayloadHash: payloadHash,
            lastCaller: msg.sender,
            updatedAt: block.timestamp
        });
        emit HandoffRequested(taskId, msg.sender, payloadHash, nonce, block.chainid);
    }

    function getTask(bytes32 taskId) external view returns (bool exists, HandoffTask memory task) {
        exists = taskExists[taskId];
        task = tasks[taskId];
    }

    function getTaskRuntime(bytes32 taskId) external view returns (TaskRuntime memory runtime) {
        runtime = taskRuntime[taskId];
    }

    function isNodeExecuted(bytes32 taskId, string calldata nodeId) external view returns (bool) {
        bytes32 key = keccak256(bytes(nodeId));
        return nodeExecuted[taskId][key];
    }

    function executeBatch(
        bytes32 taskId,
        bytes32 payloadHash,
        string[] calldata nodeIds
    ) external {
        require(taskExists[taskId], "unknown taskId");
        require(nodeIds.length > 0, "empty node batch");
        for (uint256 i = 0; i < nodeIds.length; i++) {
            _markNodeExecuted(taskId, nodeIds[i], payloadHash);
        }
    }

    function _markNodeExecuted(bytes32 taskId, string memory nodeId, bytes32 payloadHash) internal {
        require(payloadHash == tasks[taskId].payloadHash, "payload hash mismatch");
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
    function _nodeOrder(string memory nodeId) internal pure returns (uint256) {
        if (keccak256(bytes(nodeId)) == keccak256(bytes("Event_0ehnwwz"))) return 0;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("ChoreographyTask_1d8axmm"))) return 1;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("Gateway_1ltys0e"))) return 2;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("ChoreographyTask_01rdy6m"))) return 3;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("ChoreographyTask_0huz12d"))) return 4;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("Gateway_025uwvp"))) return 5;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("ChoreographyTask_13g05bg"))) return 6;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("ChoreographyTask_1k9vb6k"))) return 7;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("Event_0e3j88g"))) return 8;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("ChoreographyTask_1yl8kdd"))) return 9;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("Event_1o9guxu"))) return 10;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("Event_194zr5n"))) return 11;
        revert("unknown node id");
    }

    function Event_0ehnwwz(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "Event_0ehnwwz", payloadHash);
    }
    function ChoreographyTask_1d8axmm(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "ChoreographyTask_1d8axmm", payloadHash);
    }
    function Gateway_1ltys0e(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "Gateway_1ltys0e", payloadHash);
    }
    function ChoreographyTask_01rdy6m(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "ChoreographyTask_01rdy6m", payloadHash);
    }
    function ChoreographyTask_0huz12d(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "ChoreographyTask_0huz12d", payloadHash);
    }
    function Gateway_025uwvp(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "Gateway_025uwvp", payloadHash);
    }
    function ChoreographyTask_13g05bg(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "ChoreographyTask_13g05bg", payloadHash);
    }
    function ChoreographyTask_1k9vb6k(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "ChoreographyTask_1k9vb6k", payloadHash);
    }
    function Event_0e3j88g(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "Event_0e3j88g", payloadHash);
    }
    function ChoreographyTask_1yl8kdd(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "ChoreographyTask_1yl8kdd", payloadHash);
    }
    function Event_1o9guxu(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "Event_1o9guxu", payloadHash);
    }
    function Event_194zr5n(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "Event_194zr5n", payloadHash);
    }
}
