// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract SimpleMultiOracle {
    address public owner;
    uint256 public nextTaskId;
    uint256 public minResponses;

    struct OracleNode {
        bool active;
    }

    struct Task {
        address requester;
        bytes params;
        bool finished;
        bytes finalResult;
        uint256 deadline;
        mapping(address => bool) responded;
        mapping(bytes32 => uint256) resultCount; // resultHash -> count
    }

    mapping(address => OracleNode) public oracleNodes;
    uint256 public oracleCount;

    mapping(uint256 => Task) private tasks;

    event OracleRegistered(address indexed oracle);
    event OracleRemoved(address indexed oracle);
    event TaskRequested(uint256 indexed taskId, address indexed requester, bytes params);
    event ResultSubmitted(uint256 indexed taskId, address indexed oracle, bytes result);
    event TaskFinalized(uint256 indexed taskId, bytes result);

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    modifier onlyOracle() {
        require(oracleNodes[msg.sender].active, "not oracle");
        _;
    }

    constructor(uint256 _minResponses) {
        require(_minResponses > 0, "minResponses must be > 0");
        owner = msg.sender;
        minResponses = _minResponses;
    }

    // === 管理 Oracle 节点 ===

    function registerOracle(address _oracle) external onlyOwner {
        require(_oracle != address(0), "zero addr");
        require(!oracleNodes[_oracle].active, "already active");
        oracleNodes[_oracle] = OracleNode({active: true});
        oracleCount += 1;
        emit OracleRegistered(_oracle);
    }

    function removeOracle(address _oracle) external onlyOwner {
        require(oracleNodes[_oracle].active, "not active");
        oracleNodes[_oracle].active = false;
        oracleCount -= 1;
        emit OracleRemoved(_oracle);
    }

    function setMinResponses(uint256 _minResponses) external onlyOwner {
        require(_minResponses > 0, "minResponses must be > 0");
        minResponses = _minResponses;
    }

    // === 用户发起任务 ===

    function requestTask(bytes calldata params, uint256 deadline) external returns (uint256) {
        uint256 taskId = nextTaskId;
        nextTaskId++;

        Task storage t = tasks[taskId];
        t.requester = msg.sender;
        t.params = params;
        t.finished = false;
        t.deadline = deadline;

        emit TaskRequested(taskId, msg.sender, params);
        return taskId;
    }

    // === Oracle 提交结果 ===

    function submitResult(uint256 taskId, bytes calldata result) external onlyOracle {
        Task storage t = tasks[taskId];
        require(!t.finished, "task finished");
        if (t.deadline != 0) {
            require(block.number <= t.deadline, "deadline passed");
        }
        require(!t.responded[msg.sender], "already responded");

        t.responded[msg.sender] = true;

        bytes32 h = keccak256(result);
        t.resultCount[h] += 1;

        emit ResultSubmitted(taskId, msg.sender, result);

        // 多数决判断：达到 minResponses 就定案
        if (t.resultCount[h] >= minResponses) {
            t.finished = true;
            t.finalResult = result;
            emit TaskFinalized(taskId, result);
        }
    }

    // === 查询接口 ===

    function getTask(
        uint256 taskId
    )
        external
        view
        returns (
            address requester,
            bytes memory params,
            bool finished,
            bytes memory finalResult,
            uint256 deadline
        )
    {
        Task storage t = tasks[taskId];
        return (t.requester, t.params, t.finished, t.finalResult, t.deadline);
    }
}
