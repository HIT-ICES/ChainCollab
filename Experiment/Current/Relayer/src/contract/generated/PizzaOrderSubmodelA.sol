// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract PizzaOrderSubmodelA {
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
        if (keccak256(bytes(nodeId)) == keccak256(bytes("Event_1a62z0q"))) return 0;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("ChoreographyTask_1w7glmc"))) return 1;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("Gateway_0nafkvy"))) return 2;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("ChoreographyTask_1jx2djv"))) return 3;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("ChoreographyTask_16rozc7"))) return 4;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("ChoreographyTask_0zxgisv"))) return 5;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("ChoreographyTask_0fdwpvb"))) return 6;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("ChoreographyTask_18fddae"))) return 7;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("Gateway_1pguang"))) return 8;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("Event_04u53jh"))) return 9;
        revert("unknown node id");
    }

    function Event_1a62z0q(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "Event_1a62z0q", payloadHash);
    }
    function ChoreographyTask_1w7glmc(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "ChoreographyTask_1w7glmc", payloadHash);
    }
    function Gateway_0nafkvy(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "Gateway_0nafkvy", payloadHash);
    }
    function ChoreographyTask_1jx2djv(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "ChoreographyTask_1jx2djv", payloadHash);
    }
    function ChoreographyTask_16rozc7(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "ChoreographyTask_16rozc7", payloadHash);
    }
    function ChoreographyTask_0zxgisv(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "ChoreographyTask_0zxgisv", payloadHash);
    }
    function ChoreographyTask_0fdwpvb(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "ChoreographyTask_0fdwpvb", payloadHash);
    }
    function ChoreographyTask_18fddae(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "ChoreographyTask_18fddae", payloadHash);
    }
    function Gateway_1pguang(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "Gateway_1pguang", payloadHash);
    }
    function Event_04u53jh(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "Event_04u53jh", payloadHash);
    }
}
