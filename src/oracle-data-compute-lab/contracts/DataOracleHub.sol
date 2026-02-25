// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface ISlotRegistryForData {
    function setSlot(bytes32 slotKey, string calldata value, string calldata source) external;
}

contract DataOracleHub {
    enum TaskStatus {
        NONE,
        REQUESTED,
        FULFILLED,
        FAILED
    }

    struct ExternalDataTask {
        bytes32 slotKey;
        string sourceUrl;
        string jsonPath;
        address requester;
        TaskStatus status;
        string lastError;
    }

    address public owner;
    mapping(address => bool) public relayers;
    ISlotRegistryForData public slotRegistry;

    uint256 public nextTaskId;
    mapping(uint256 => ExternalDataTask) public tasks;

    event RelayerUpdated(address indexed relayer, bool enabled);
    event SlotRegistryUpdated(address indexed slotRegistry);
    event ExternalDataTaskRequested(
        uint256 indexed taskId,
        bytes32 indexed slotKey,
        string sourceUrl,
        string jsonPath,
        address requester
    );
    event ExternalDataTaskFulfilled(
        uint256 indexed taskId,
        bytes32 indexed slotKey,
        string value,
        address relayer
    );
    event ExternalDataTaskFailed(uint256 indexed taskId, string reason, address relayer);

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
        slotRegistry = ISlotRegistryForData(slotRegistryAddress);
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
        slotRegistry = ISlotRegistryForData(slotRegistryAddress);
        emit SlotRegistryUpdated(slotRegistryAddress);
    }

    function requestExternalDataTask(
        bytes32 slotKey,
        string calldata sourceUrl,
        string calldata jsonPath
    ) external returns (uint256 taskId) {
        require(slotKey != bytes32(0), "invalid slot key");
        require(bytes(sourceUrl).length > 0, "empty source");

        taskId = nextTaskId++;
        ExternalDataTask storage t = tasks[taskId];
        t.slotKey = slotKey;
        t.sourceUrl = sourceUrl;
        t.jsonPath = jsonPath;
        t.requester = msg.sender;
        t.status = TaskStatus.REQUESTED;

        emit ExternalDataTaskRequested(taskId, slotKey, sourceUrl, jsonPath, msg.sender);
    }

    function fulfillExternalDataTask(
        uint256 taskId,
        string calldata value
    ) external onlyRelayer {
        ExternalDataTask storage t = tasks[taskId];
        require(t.status == TaskStatus.REQUESTED, "task not pending");

        t.status = TaskStatus.FULFILLED;
        slotRegistry.setSlot(t.slotKey, value, "external-data");
        emit ExternalDataTaskFulfilled(taskId, t.slotKey, value, msg.sender);
    }

    function failExternalDataTask(
        uint256 taskId,
        string calldata reason
    ) external onlyRelayer {
        ExternalDataTask storage t = tasks[taskId];
        require(t.status == TaskStatus.REQUESTED, "task not pending");

        t.status = TaskStatus.FAILED;
        t.lastError = reason;
        emit ExternalDataTaskFailed(taskId, reason, msg.sender);
    }
}
