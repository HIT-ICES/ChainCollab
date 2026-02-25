// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@chainlink/contracts/src/v0.8/operatorforwarder/ChainlinkClient.sol";
import "@chainlink/contracts/src/v0.8/shared/access/ConfirmedOwner.sol";

interface IMainComputeTaskCallback {
    function onComputeTaskResult(
        bytes32 taskId,
        bytes32 requestId,
        string calldata raw
    ) external;
}

/// @notice 计算任务子合约：由主合约驱动发起 Chainlink 请求，并将结果回调给主合约。
contract ChainlinkComputeTaskAdapter is ChainlinkClient, ConfirmedOwner {
    using Chainlink for Chainlink.Request;

    struct PendingTask {
        bytes32 taskId;
        bool exists;
        bool committed;
        string raw;
        uint256 updatedAt;
    }

    address public controller;
    address public oracle;
    bytes32 public jobId;
    uint256 public fee;

    mapping(bytes32 => PendingTask) public pendingByRequestId;
    mapping(address => bool) public writers;

    event ComputeTaskRequested(
        bytes32 indexed taskId,
        bytes32 indexed requestId,
        string endpoint,
        string script,
        string inputData
    );
    event ComputeTaskCommitted(
        bytes32 indexed taskId,
        bytes32 indexed requestId,
        string raw
    );
    event WriterUpdated(address indexed writer, bool allowed);

    modifier onlyController() {
        require(msg.sender == controller, "not controller");
        _;
    }

    modifier onlyWriter() {
        require(
            msg.sender == owner() || writers[msg.sender],
            "not authorized writer"
        );
        _;
    }

    constructor(
        address linkToken,
        address oracleAddress,
        bytes32 initialJobId,
        uint256 initialFee,
        address controllerAddress
    ) ConfirmedOwner(msg.sender) {
        _setChainlinkToken(linkToken);
        oracle = oracleAddress;
        jobId = initialJobId;
        fee = initialFee;
        controller = controllerAddress;
    }

    function setController(address newController) external onlyOwner {
        controller = newController;
    }

    function setOracle(address newOracle) external onlyOwner {
        oracle = newOracle;
    }

    function setJobId(bytes32 newJobId) external onlyOwner {
        jobId = newJobId;
    }

    function setFee(uint256 newFee) external onlyOwner {
        fee = newFee;
    }

    function setWriter(address writer, bool allowed) external onlyOwner {
        writers[writer] = allowed;
        emit WriterUpdated(writer, allowed);
    }

    function requestComputeTask(
        bytes32 taskId,
        string calldata endpoint,
        string calldata script,
        string calldata inputData
    ) external onlyController returns (bytes32 requestId) {
        Chainlink.Request memory req = _buildChainlinkRequest(
            jobId,
            address(this),
            this.fulfill.selector
        );

        req._add("endpoint", endpoint);
        req._add("script", script);
        req._add("inputData", inputData);

        requestId = _sendChainlinkRequestTo(oracle, req, fee);
        pendingByRequestId[requestId] = PendingTask({
            taskId: taskId,
            exists: true,
            committed: false,
            raw: "",
            updatedAt: block.timestamp
        });

        emit ComputeTaskRequested(taskId, requestId, endpoint, script, inputData);
    }

    /// @notice 标准 Chainlink fulfill 回调（适配返回 bytes 的 Job）
    function fulfill(
        bytes32 requestId,
        bytes memory data
    ) public recordChainlinkFulfillment(requestId) {
        _commit(requestId, string(data));
    }

    /// @notice directrequest Job 可直接调用此方法写回原始结果
    function commitComputeFromRaw(
        bytes32 requestId,
        string calldata raw
    ) external onlyWriter {
        _commit(requestId, raw);
    }

    function _commit(bytes32 requestId, string memory raw) internal {
        PendingTask storage pending = pendingByRequestId[requestId];
        require(pending.exists, "request not found");
        require(!pending.committed, "request already committed");
        require(controller != address(0), "controller not set");

        pending.committed = true;
        pending.raw = raw;
        pending.updatedAt = block.timestamp;

        IMainComputeTaskCallback(controller).onComputeTaskResult(
            pending.taskId,
            requestId,
            raw
        );
        emit ComputeTaskCommitted(pending.taskId, requestId, raw);
    }
}
