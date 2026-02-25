// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@chainlink/contracts/src/v0.8/shared/access/ConfirmedOwner.sol";

interface IDataTaskAdapter {
    function requestDataTask(
        bytes32 taskId,
        string calldata sourceUrl,
        string calldata query
    ) external returns (bytes32 requestId);
}

interface IComputeTaskAdapter {
    function requestComputeTask(
        bytes32 taskId,
        string calldata endpoint,
        string calldata script,
        string calldata inputData
    ) external returns (bytes32 requestId);
}

/// @notice 主合约：统一接收业务请求，分发给 Data/Compute 子合约并回收结果。
contract MainOracleRouter is ConfirmedOwner {
    enum TaskType {
        DATA,
        COMPUTE
    }

    enum TaskStatus {
        NONE,
        PENDING,
        COMPLETED,
        FAILED
    }

    struct TaskRecord {
        TaskType taskType;
        TaskStatus status;
        address requester;
        address adapter;
        bytes32 requestId;
        string resultRaw;
        uint256 createdAt;
        uint256 updatedAt;
    }

    address public dataAdapter;
    address public computeAdapter;
    uint256 public nonce;

    mapping(bytes32 => TaskRecord) private tasks;
    mapping(bytes32 => bytes32) public requestIdToTaskId;

    event AdapterUpdated(
        address indexed dataAdapter,
        address indexed computeAdapter
    );
    event TaskCreated(
        bytes32 indexed taskId,
        bytes32 indexed requestId,
        TaskType taskType,
        address requester,
        address adapter
    );
    event TaskCompleted(
        bytes32 indexed taskId,
        bytes32 indexed requestId,
        TaskType taskType,
        string resultRaw
    );
    event TaskFailed(bytes32 indexed taskId, string reason);

    modifier onlyDataAdapter() {
        require(msg.sender == dataAdapter, "caller is not data adapter");
        _;
    }

    modifier onlyComputeAdapter() {
        require(msg.sender == computeAdapter, "caller is not compute adapter");
        _;
    }

    constructor() ConfirmedOwner(msg.sender) {}

    function setAdapters(
        address newDataAdapter,
        address newComputeAdapter
    ) external onlyOwner {
        dataAdapter = newDataAdapter;
        computeAdapter = newComputeAdapter;
        emit AdapterUpdated(newDataAdapter, newComputeAdapter);
    }

    function requestData(
        string calldata sourceUrl,
        string calldata query
    ) external returns (bytes32 taskId, bytes32 requestId) {
        require(dataAdapter != address(0), "data adapter not set");
        taskId = _nextTaskId(msg.sender, TaskType.DATA, sourceUrl, query, "");
        requestId = IDataTaskAdapter(dataAdapter).requestDataTask(
            taskId,
            sourceUrl,
            query
        );
        _storePendingTask(taskId, requestId, TaskType.DATA, dataAdapter);
    }

    function requestCompute(
        string calldata endpoint,
        string calldata script,
        string calldata inputData
    ) external returns (bytes32 taskId, bytes32 requestId) {
        require(computeAdapter != address(0), "compute adapter not set");
        taskId = _nextTaskId(
            msg.sender,
            TaskType.COMPUTE,
            endpoint,
            script,
            inputData
        );
        requestId = IComputeTaskAdapter(computeAdapter).requestComputeTask(
            taskId,
            endpoint,
            script,
            inputData
        );
        _storePendingTask(taskId, requestId, TaskType.COMPUTE, computeAdapter);
    }

    function onDataTaskResult(
        bytes32 taskId,
        bytes32 requestId,
        string calldata raw
    ) external onlyDataAdapter {
        _completeTask(taskId, requestId, TaskType.DATA, raw);
    }

    function onComputeTaskResult(
        bytes32 taskId,
        bytes32 requestId,
        string calldata raw
    ) external onlyComputeAdapter {
        _completeTask(taskId, requestId, TaskType.COMPUTE, raw);
    }

    function markTaskFailed(
        bytes32 taskId,
        string calldata reason
    ) external onlyOwner {
        TaskRecord storage task = tasks[taskId];
        require(task.status == TaskStatus.PENDING, "task is not pending");
        task.status = TaskStatus.FAILED;
        task.updatedAt = block.timestamp;
        emit TaskFailed(taskId, reason);
    }

    function getTask(
        bytes32 taskId
    ) external view returns (TaskRecord memory task) {
        task = tasks[taskId];
    }

    function isTaskCompleted(bytes32 taskId) external view returns (bool) {
        return tasks[taskId].status == TaskStatus.COMPLETED;
    }

    function _nextTaskId(
        address requester,
        TaskType taskType,
        string memory v1,
        string memory v2,
        string memory v3
    ) internal returns (bytes32 taskId) {
        uint256 current = nonce;
        nonce = current + 1;
        taskId = keccak256(
            abi.encodePacked(
                block.chainid,
                address(this),
                requester,
                current,
                taskType,
                v1,
                v2,
                v3,
                block.timestamp
            )
        );
    }

    function _storePendingTask(
        bytes32 taskId,
        bytes32 requestId,
        TaskType taskType,
        address adapter
    ) internal {
        tasks[taskId] = TaskRecord({
            taskType: taskType,
            status: TaskStatus.PENDING,
            requester: msg.sender,
            adapter: adapter,
            requestId: requestId,
            resultRaw: "",
            createdAt: block.timestamp,
            updatedAt: block.timestamp
        });
        requestIdToTaskId[requestId] = taskId;

        emit TaskCreated(taskId, requestId, taskType, msg.sender, adapter);
    }

    function _completeTask(
        bytes32 taskId,
        bytes32 requestId,
        TaskType expectedType,
        string calldata raw
    ) internal {
        TaskRecord storage task = tasks[taskId];
        require(task.status == TaskStatus.PENDING, "task is not pending");
        require(task.requestId == requestId, "requestId mismatch");
        require(task.taskType == expectedType, "task type mismatch");
        task.status = TaskStatus.COMPLETED;
        task.resultRaw = raw;
        task.updatedAt = block.timestamp;

        emit TaskCompleted(taskId, requestId, expectedType, raw);
    }
}
