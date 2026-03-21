// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract MonolithicTaskFlow {
    struct Task {
        bool exists;
        bool processed;
        address requester;
        bytes32 payloadHash;
        uint256 nonce;
        uint256 createdAt;
        uint256 processedAt;
    }

    uint256 public nextNonce;
    mapping(bytes32 => Task) private tasks;

    event TaskRequested(
        bytes32 indexed taskId,
        address indexed requester,
        bytes32 payloadHash,
        uint256 nonce,
        uint256 chainId
    );
    event TaskProcessed(
        bytes32 indexed taskId,
        bytes32 payloadHash,
        address indexed processor,
        uint256 chainId
    );

    function requestTask(bytes32 payloadHash) external returns (bytes32 taskId) {
        require(payloadHash != bytes32(0), "empty payload hash");
        uint256 nonce = nextNonce;
        unchecked {
            nextNonce = nonce + 1;
        }
        taskId = keccak256(
            abi.encodePacked(block.chainid, address(this), msg.sender, nonce, payloadHash)
        );
        require(!tasks[taskId].exists, "task exists");

        tasks[taskId] = Task({
            exists: true,
            processed: false,
            requester: msg.sender,
            payloadHash: payloadHash,
            nonce: nonce,
            createdAt: block.timestamp,
            processedAt: 0
        });
        emit TaskRequested(taskId, msg.sender, payloadHash, nonce, block.chainid);
    }

    function processTask(bytes32 taskId, bytes32 payloadHash) external {
        Task storage task = tasks[taskId];
        require(task.exists, "task not found");
        require(!task.processed, "task processed");
        require(task.payloadHash == payloadHash, "payload mismatch");

        task.processed = true;
        task.processedAt = block.timestamp;
        emit TaskProcessed(taskId, payloadHash, msg.sender, block.chainid);
    }

    function isProcessed(bytes32 taskId) external view returns (bool) {
        return tasks[taskId].processed;
    }

    function getTask(bytes32 taskId) external view returns (Task memory) {
        return tasks[taskId];
    }
}
