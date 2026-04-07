// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract SourceTaskEmitter {
    struct TaskMeta {
        address requester;
        bytes32 payloadHash;
        uint256 nonce;
        uint256 createdAt;
    }

    uint256 public nextNonce;

    mapping(bytes32 => bool) public taskExists;
    mapping(bytes32 => TaskMeta) public tasks;

    event TaskRequested(
        bytes32 indexed taskId,
        address indexed requester,
        bytes32 payloadHash,
        uint256 nonce,
        uint256 sourceChainId
    );

    function requestTask(bytes32 payloadHash) external returns (bytes32 taskId) {
        require(payloadHash != bytes32(0), "empty payload hash");

        uint256 nonce = nextNonce;
        unchecked {
            nextNonce = nonce + 1;
        }

        taskId = keccak256(
            abi.encodePacked(
                block.chainid,
                address(this),
                msg.sender,
                nonce,
                payloadHash
            )
        );

        require(!taskExists[taskId], "task already exists");

        taskExists[taskId] = true;
        tasks[taskId] = TaskMeta({
            requester: msg.sender,
            payloadHash: payloadHash,
            nonce: nonce,
            createdAt: block.timestamp
        });

        emit TaskRequested(taskId, msg.sender, payloadHash, nonce, block.chainid);
    }

    function getTask(
        bytes32 taskId
    ) external view returns (bool exists, TaskMeta memory meta) {
        exists = taskExists[taskId];
        meta = tasks[taskId];
    }
}
