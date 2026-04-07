// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract Coffee_machineSubmodelA {
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
        if (keccak256(bytes(nodeId)) == keccak256(bytes("StartEvent_1v2ab61"))) return 0;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("ChoreographyTask_164ymrj"))) return 1;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("ChoreographyTask_0mnrjy0"))) return 2;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("ChoreographyTask_08f0s86"))) return 3;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("ChoreographyTask_0gwsf88"))) return 4;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("ExclusiveGateway_0c8hy9b"))) return 5;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("ExclusiveGateway_1sp1v7s"))) return 6;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("EndEvent_17h95ah"))) return 7;
        revert("unknown node id");
    }

    function StartEvent_1v2ab61(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "StartEvent_1v2ab61", payloadHash);
    }
    function ChoreographyTask_164ymrj(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "ChoreographyTask_164ymrj", payloadHash);
    }
    function ChoreographyTask_0mnrjy0(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "ChoreographyTask_0mnrjy0", payloadHash);
    }
    function ChoreographyTask_08f0s86(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "ChoreographyTask_08f0s86", payloadHash);
    }
    function ChoreographyTask_0gwsf88(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "ChoreographyTask_0gwsf88", payloadHash);
    }
    function ExclusiveGateway_0c8hy9b(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "ExclusiveGateway_0c8hy9b", payloadHash);
    }
    function ExclusiveGateway_1sp1v7s(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "ExclusiveGateway_1sp1v7s", payloadHash);
    }
    function EndEvent_17h95ah(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "EndEvent_17h95ah", payloadHash);
    }
}
