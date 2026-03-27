// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface ISlotRegistryForCompute {
    function setSlot(bytes32 slotKey, string calldata value, string calldata source) external;
}

contract ComputeOracleHub {
    enum TaskStatus {
        NONE,
        REQUESTED,
        FULFILLED,
        FAILED
    }

    struct ComputeTask {
        bytes32 outputSlotKey;
        string expression;
        bytes32[] inputSlotKeys;
        address requester;
        TaskStatus status;
        string lastError;
    }

    address public owner;
    mapping(address => bool) public relayers;
    ISlotRegistryForCompute public slotRegistry;

    uint256 public nextTaskId;
    mapping(uint256 => ComputeTask) private tasks;

    event RelayerUpdated(address indexed relayer, bool enabled);
    event SlotRegistryUpdated(address indexed slotRegistry);
    event ComputeTaskRequested(
        uint256 indexed taskId,
        bytes32 indexed outputSlotKey,
        string expression,
        bytes32[] inputSlotKeys,
        address requester
    );
    event ComputeTaskFulfilled(
        uint256 indexed taskId,
        bytes32 indexed outputSlotKey,
        string result,
        address relayer
    );
    event ComputeTaskFailed(uint256 indexed taskId, string reason, address relayer);

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    modifier onlyRelayer() {
        require(relayers[msg.sender], "not relayer");
        _;
    }

    constructor(address slotRegistryAddress) {
        require(slotRegistryAddress != address(0), "zero registry");
        owner = msg.sender;
        relayers[msg.sender] = true;
        slotRegistry = ISlotRegistryForCompute(slotRegistryAddress);
        emit RelayerUpdated(msg.sender, true);
        emit SlotRegistryUpdated(slotRegistryAddress);
    }

    function setRelayer(address relayer, bool enabled) external onlyOwner {
        require(relayer != address(0), "zero relayer");
        relayers[relayer] = enabled;
        emit RelayerUpdated(relayer, enabled);
    }

    function setSlotRegistry(address slotRegistryAddress) external onlyOwner {
        require(slotRegistryAddress != address(0), "zero registry");
        slotRegistry = ISlotRegistryForCompute(slotRegistryAddress);
        emit SlotRegistryUpdated(slotRegistryAddress);
    }

    function requestComputeTask(
        bytes32 outputSlotKey,
        string calldata expression,
        bytes32[] calldata inputSlotKeys
    ) external returns (uint256 taskId) {
        require(outputSlotKey != bytes32(0), "invalid output key");
        require(bytes(expression).length > 0, "empty expression");
        require(inputSlotKeys.length > 0, "no inputs");

        taskId = nextTaskId++;
        ComputeTask storage t = tasks[taskId];
        t.outputSlotKey = outputSlotKey;
        t.expression = expression;
        t.requester = msg.sender;
        t.status = TaskStatus.REQUESTED;

        for (uint256 i = 0; i < inputSlotKeys.length; i++) {
            require(inputSlotKeys[i] != bytes32(0), "invalid input key");
            t.inputSlotKeys.push(inputSlotKeys[i]);
        }

        emit ComputeTaskRequested(
            taskId,
            outputSlotKey,
            expression,
            inputSlotKeys,
            msg.sender
        );
    }

    function fulfillComputeTask(
        uint256 taskId,
        string calldata result
    ) external onlyRelayer {
        ComputeTask storage t = tasks[taskId];
        require(t.status == TaskStatus.REQUESTED, "task not pending");

        t.status = TaskStatus.FULFILLED;
        slotRegistry.setSlot(t.outputSlotKey, result, "compute-task");
        emit ComputeTaskFulfilled(taskId, t.outputSlotKey, result, msg.sender);
    }

    function failComputeTask(
        uint256 taskId,
        string calldata reason
    ) external onlyRelayer {
        ComputeTask storage t = tasks[taskId];
        require(t.status == TaskStatus.REQUESTED, "task not pending");

        t.status = TaskStatus.FAILED;
        t.lastError = reason;
        emit ComputeTaskFailed(taskId, reason, msg.sender);
    }

    function getTask(
        uint256 taskId
    )
        external
        view
        returns (
            bytes32 outputSlotKey,
            string memory expression,
            address requester,
            TaskStatus statusCode,
            string memory lastError
        )
    {
        ComputeTask storage t = tasks[taskId];
        return (
            t.outputSlotKey,
            t.expression,
            t.requester,
            t.status,
            t.lastError
        );
    }

    function getTaskInputSlotKeys(
        uint256 taskId
    ) external view returns (bytes32[] memory) {
        return tasks[taskId].inputSlotKeys;
    }
}
