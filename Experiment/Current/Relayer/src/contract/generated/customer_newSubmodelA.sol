// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract customer_newSubmodelA {
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
        if (keccak256(bytes(nodeId)) == keccak256(bytes("Event_1jtgn3j"))) return 0;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("ChoreographyTask_1jv6c24"))) return 1;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("ExclusiveGateway_106je4z"))) return 2;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("ChoreographyTask_13nkbkb"))) return 3;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("ExclusiveGateway_0hs3ztq"))) return 4;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("EventBasedGateway_1fxpmyn"))) return 5;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("ChoreographyTask_177ikw5"))) return 6;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("ChoreographyTask_09lf521"))) return 7;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("Event_0366pfz"))) return 8;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("ChoreographyTask_0suxm4u"))) return 9;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("ExclusiveGateway_0nzwv7v"))) return 10;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("ChoreographyTask_1iimt7t"))) return 11;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("Event_146eii4"))) return 12;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("ChoreographyTask_1khafgk"))) return 13;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("Gateway_1bhtapl"))) return 14;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("Gateway_04h9e6e"))) return 15;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("ChoreographyTask_1c9swul"))) return 16;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("Activity_1yl9tfp"))) return 17;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("Activity_0ibsbry"))) return 18;
        if (keccak256(bytes(nodeId)) == keccak256(bytes("Event_143ykco"))) return 19;
        revert("unknown node id");
    }

    function Event_1jtgn3j(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "Event_1jtgn3j", payloadHash);
    }
    function ChoreographyTask_1jv6c24(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "ChoreographyTask_1jv6c24", payloadHash);
    }
    function ExclusiveGateway_106je4z(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "ExclusiveGateway_106je4z", payloadHash);
    }
    function ChoreographyTask_13nkbkb(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "ChoreographyTask_13nkbkb", payloadHash);
    }
    function ExclusiveGateway_0hs3ztq(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "ExclusiveGateway_0hs3ztq", payloadHash);
    }
    function EventBasedGateway_1fxpmyn(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "EventBasedGateway_1fxpmyn", payloadHash);
    }
    function ChoreographyTask_177ikw5(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "ChoreographyTask_177ikw5", payloadHash);
    }
    function ChoreographyTask_09lf521(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "ChoreographyTask_09lf521", payloadHash);
    }
    function Event_0366pfz(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "Event_0366pfz", payloadHash);
    }
    function ChoreographyTask_0suxm4u(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "ChoreographyTask_0suxm4u", payloadHash);
    }
    function ExclusiveGateway_0nzwv7v(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "ExclusiveGateway_0nzwv7v", payloadHash);
    }
    function ChoreographyTask_1iimt7t(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "ChoreographyTask_1iimt7t", payloadHash);
    }
    function Event_146eii4(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "Event_146eii4", payloadHash);
    }
    function ChoreographyTask_1khafgk(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "ChoreographyTask_1khafgk", payloadHash);
    }
    function Gateway_1bhtapl(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "Gateway_1bhtapl", payloadHash);
    }
    function Gateway_04h9e6e(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "Gateway_04h9e6e", payloadHash);
    }
    function ChoreographyTask_1c9swul(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "ChoreographyTask_1c9swul", payloadHash);
    }
    function Activity_1yl9tfp(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "Activity_1yl9tfp", payloadHash);
    }
    function Activity_0ibsbry(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "Activity_0ibsbry", payloadHash);
    }
    function Event_143ykco(bytes32 taskId, bytes32 payloadHash) external {
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "Event_143ykco", payloadHash);
    }
}
