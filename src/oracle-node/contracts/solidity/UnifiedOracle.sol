// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title UnifiedOracle
/// @notice 数据类任务走“聚合”，计算类任务走“阈值签名”，统一在一个合约中管理。
/// @dev Oracle 节点签名规则：keccak256(abi.encodePacked(taskId, value)) 或 keccak256(abi.encodePacked(taskId, payloadHash, result))
contract UnifiedOracle {
    enum AggregationMode {
        MEAN,
        MEDIAN,
        WEIGHTED_MEAN
    }

    struct OracleInfo {
        bool active;
    }

    struct DataTask {
        address requester;
        string sourceConfig;
        bytes32 sourceHash;
        AggregationMode mode;
        uint256 minResponses;
        bool finished;
        uint256 finalValue;
        address[] allowedOracles;
        uint256[] weights;
        mapping(address => bool) oracleAllowed;
        mapping(address => bool) responded;
        Submission[] submissions;
    }

    struct ComputeTask {
        address requester;
        bytes32 computeType;
        bytes32 payloadHash;
        uint256 threshold;
        bool finished;
        bytes32 finalResult;
        uint256 responseCount;
        address[] allowedOracles;
        mapping(address => bool) oracleAllowed;
        mapping(address => bool) responded;
        mapping(bytes32 => uint256) resultCount;
    }

    struct Submission {
        address oracle;
        uint256 value;
    }

    address public owner;
    uint256 public oracleCount;
    uint256 public nextDataTaskId;
    uint256 public nextComputeTaskId;

    mapping(address => OracleInfo) public oracleRegistry;
    mapping(uint256 => DataTask) private dataTasks;
    mapping(uint256 => ComputeTask) private computeTasks;

    event OracleRegistered(address indexed oracle);
    event OracleRemoved(address indexed oracle);
    event DataTaskRegistered(uint256 indexed taskId, bytes32 sourceHash, AggregationMode mode);
    event ComputeTaskRegistered(uint256 indexed taskId, bytes32 computeType, bytes32 payloadHash);
    event DataSubmitted(uint256 indexed taskId, address indexed oracle, uint256 value);
    event ComputeSubmitted(uint256 indexed taskId, address indexed oracle, bytes32 result);
    event DataTaskFinalized(uint256 indexed taskId, uint256 finalValue);
    event ComputeTaskFinalized(uint256 indexed taskId, bytes32 finalResult);

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    // ========= Oracle 注册 =========
    function registerOracle(address oracle) external onlyOwner {
        require(oracle != address(0), "zero address");
        require(!oracleRegistry[oracle].active, "already active");
        oracleRegistry[oracle].active = true;
        oracleCount += 1;
        emit OracleRegistered(oracle);
    }

    function removeOracle(address oracle) external onlyOwner {
        require(oracleRegistry[oracle].active, "not active");
        oracleRegistry[oracle].active = false;
        oracleCount -= 1;
        emit OracleRemoved(oracle);
    }

    // ========= 数据任务注册（聚合） =========
    /// @param sourceConfig 数据源配置（JSON 或其他编码字符串）
    /// @param mode 聚合模式：均值/中位数/加权均值
    /// @param allowedOracles 可参与的 oracle 列表
    /// @param weights 加权均值时传入；其余模式可为空
    /// @param minResponses 均值/加权均值的最小响应数（为 0 则默认=允许列表长度）
    function registerDataTask(
        string calldata sourceConfig,
        AggregationMode mode,
        address[] calldata allowedOracles,
        uint256[] calldata weights,
        uint256 minResponses
    ) external returns (uint256) {
        require(allowedOracles.length > 0, "no oracles");
        if (mode == AggregationMode.WEIGHTED_MEAN) {
            require(weights.length == allowedOracles.length, "weight length mismatch");
        } else {
            require(weights.length == 0, "weights not needed");
        }

        uint256 taskId = nextDataTaskId;
        nextDataTaskId++;

        DataTask storage t = dataTasks[taskId];
        t.requester = msg.sender;
        t.sourceConfig = sourceConfig;
        t.sourceHash = keccak256(bytes(sourceConfig));
        t.mode = mode;
        t.minResponses = minResponses == 0 ? allowedOracles.length : minResponses;
        t.allowedOracles = allowedOracles;
        if (mode == AggregationMode.WEIGHTED_MEAN) {
            t.weights = weights;
        }
        for (uint256 i = 0; i < allowedOracles.length; i++) {
            address o = allowedOracles[i];
            require(oracleRegistry[o].active, "oracle not registered");
            t.oracleAllowed[o] = true;
        }

        emit DataTaskRegistered(taskId, t.sourceHash, mode);
        return taskId;
    }

    // ========= 计算任务注册（阈值签名） =========
    /// @param computeType 计算类型标识（例如 CREDIT_SCORE / ROUTE_PLAN）
    /// @param payloadHash 计算输入的哈希（绑定任务与输入，防止替换）
    /// @param allowedOracles 可参与 oracle 列表
    /// @param threshold 需要相同结果的最小签名数量
    function registerComputeTask(
        bytes32 computeType,
        bytes32 payloadHash,
        address[] calldata allowedOracles,
        uint256 threshold
    ) external returns (uint256) {
        require(allowedOracles.length > 0, "no oracles");
        require(threshold > 0 && threshold <= allowedOracles.length, "bad threshold");

        uint256 taskId = nextComputeTaskId;
        nextComputeTaskId++;

        ComputeTask storage t = computeTasks[taskId];
        t.requester = msg.sender;
        t.computeType = computeType;
        t.payloadHash = payloadHash;
        t.threshold = threshold;
        t.allowedOracles = allowedOracles;
        for (uint256 i = 0; i < allowedOracles.length; i++) {
            address o = allowedOracles[i];
            require(oracleRegistry[o].active, "oracle not registered");
            t.oracleAllowed[o] = true;
        }

        emit ComputeTaskRegistered(taskId, computeType, payloadHash);
        return taskId;
    }

    // ========= 数据提交 =========
    /// @param signature 对 keccak256(abi.encodePacked(taskId, value)) 的签名
    function submitData(uint256 taskId, uint256 value, bytes calldata signature) external {
        DataTask storage t = dataTasks[taskId];
        require(!t.finished, "task finished");
        require(t.oracleAllowed[msg.sender], "oracle not allowed");
        require(!t.responded[msg.sender], "already responded");

        bytes32 digest = keccak256(abi.encodePacked(taskId, value));
        address recovered = _recoverSigner(digest, signature);
        require(recovered == msg.sender, "bad signature");

        t.responded[msg.sender] = true;
        t.submissions.push(Submission({oracle: msg.sender, value: value}));
        emit DataSubmitted(taskId, msg.sender, value);

        _maybeFinalizeData(taskId, t);
    }

    // ========= 计算结果提交 =========
    /// @param result 计算结果哈希或结果本体（建议 bytes32）
    /// @param signature 对 keccak256(abi.encodePacked(taskId, payloadHash, result)) 的签名
    function submitComputeResult(uint256 taskId, bytes32 result, bytes calldata signature) external {
        ComputeTask storage t = computeTasks[taskId];
        require(!t.finished, "task finished");
        require(t.oracleAllowed[msg.sender], "oracle not allowed");
        require(!t.responded[msg.sender], "already responded");

        bytes32 digest = keccak256(abi.encodePacked(taskId, t.payloadHash, result));
        address recovered = _recoverSigner(digest, signature);
        require(recovered == msg.sender, "bad signature");

        t.responded[msg.sender] = true;
        t.responseCount += 1;
        bytes32 h = keccak256(abi.encodePacked(result));
        t.resultCount[h] += 1;

        emit ComputeSubmitted(taskId, msg.sender, result);

        if (t.resultCount[h] >= t.threshold) {
            t.finished = true;
            t.finalResult = result;
            emit ComputeTaskFinalized(taskId, result);
        }
    }

    // ========= 内部聚合 =========
    function _maybeFinalizeData(uint256 taskId, DataTask storage t) internal {
        if (t.submissions.length >= t.minResponses) {
            uint256 aggregated = _aggregate(t);
            _finalizeData(taskId, t, aggregated);
        }
    }

    function _aggregate(DataTask storage t) internal view returns (uint256) {
        if (t.mode == AggregationMode.MEAN) {
            uint256 sum = 0;
            for (uint256 i = 0; i < t.submissions.length; i++) {
                sum += t.submissions[i].value;
            }
            return sum / t.submissions.length;
        } else if (t.mode == AggregationMode.MEDIAN) {
            uint256 n = t.submissions.length;
            uint256[] memory values = new uint256[](n);
            for (uint256 i = 0; i < n; i++) {
                values[i] = t.submissions[i].value;
            }
            for (uint256 i = 1; i < n; i++) {
                uint256 key = values[i];
                uint256 j = i;
                while (j > 0 && values[j - 1] > key) {
                    values[j] = values[j - 1];
                    j--;
                }
                values[j] = key;
            }
            if (n % 2 == 1) {
                return values[n / 2];
            }
            uint256 a = values[(n / 2) - 1];
            uint256 b = values[n / 2];
            return (a + b) / 2;
        } else if (t.mode == AggregationMode.WEIGHTED_MEAN) {
            uint256 weightedSum = 0;
            uint256 weightTotal = 0;
            for (uint256 i = 0; i < t.submissions.length; i++) {
                address o = t.submissions[i].oracle;
                uint256 w = _weightOf(t, o);
                weightedSum += t.submissions[i].value * w;
                weightTotal += w;
            }
            require(weightTotal > 0, "zero weight");
            return weightedSum / weightTotal;
        } else {
            revert("unknown mode");
        }
    }

    function _weightOf(DataTask storage t, address oracle) internal view returns (uint256) {
        for (uint256 i = 0; i < t.allowedOracles.length; i++) {
            if (t.allowedOracles[i] == oracle) {
                return t.weights[i];
            }
        }
        return 0;
    }

    function _finalizeData(uint256 taskId, DataTask storage t, uint256 finalValue) internal {
        t.finished = true;
        t.finalValue = finalValue;
        emit DataTaskFinalized(taskId, finalValue);
    }

    function _recoverSigner(bytes32 digest, bytes memory signature) internal pure returns (address) {
        require(signature.length == 65, "bad sig length");
        bytes32 r;
        bytes32 s;
        uint8 v;
        assembly {
            r := mload(add(signature, 32))
            s := mload(add(signature, 64))
            v := byte(0, mload(add(signature, 96)))
        }
        if (v < 27) v += 27;
        require(v == 27 || v == 28, "bad v");
        bytes32 ethHash = keccak256(
            abi.encodePacked("\x19Ethereum Signed Message:\n32", digest)
        );
        return ecrecover(ethHash, v, r, s);
    }

    // ========= 视图 =========
    function getDataTask(uint256 taskId)
        external
        view
        returns (
            address requester,
            bytes32 sourceHash,
            AggregationMode mode,
            uint256 minResponses,
            bool finished,
            uint256 finalValue,
            uint256 submissionCount
        )
    {
        DataTask storage t = dataTasks[taskId];
        return (
            t.requester,
            t.sourceHash,
            t.mode,
            t.minResponses,
            t.finished,
            t.finalValue,
            t.submissions.length
        );
    }

    function getDataSourceConfig(uint256 taskId) external view returns (string memory) {
        return dataTasks[taskId].sourceConfig;
    }

    function getComputeTask(uint256 taskId)
        external
        view
        returns (
            address requester,
            bytes32 computeType,
            bytes32 payloadHash,
            uint256 threshold,
            bool finished,
            bytes32 finalResult
        )
    {
        ComputeTask storage t = computeTasks[taskId];
        return (
            t.requester,
            t.computeType,
            t.payloadHash,
            t.threshold,
            t.finished,
            t.finalResult
        );
    }

    // ========= 健康性/可观测性 =========
    function isOracleActive(address oracle) external view returns (bool) {
        return oracleRegistry[oracle].active;
    }

    function getCounts()
        external
        view
        returns (uint256 dataTasks, uint256 computeTasks, uint256 activeOracles)
    {
        return (nextDataTaskId, nextComputeTaskId, oracleCount);
    }

    function getHealth()
        external
        view
        returns (
            address ownerAddr,
            uint256 dataTasks,
            uint256 computeTasks,
            uint256 activeOracles,
            uint256 blockNumber
        )
    {
        return (owner, nextDataTaskId, nextComputeTaskId, oracleCount, block.number);
    }

    function getDataTaskSummary(uint256 taskId)
        external
        view
        returns (
            bytes32 sourceHash,
            AggregationMode mode,
            bool finished,
            uint256 finalValue,
            uint256 submissionCount,
            uint256 minResponses
        )
    {
        DataTask storage t = dataTasks[taskId];
        return (
            t.sourceHash,
            t.mode,
            t.finished,
            t.finalValue,
            t.submissions.length,
            t.minResponses
        );
    }

    function getComputeTaskSummary(uint256 taskId)
        external
        view
        returns (
            bytes32 computeType,
            bytes32 payloadHash,
            bool finished,
            bytes32 finalResult,
            uint256 threshold,
            uint256 responseCount
        )
    {
        ComputeTask storage t = computeTasks[taskId];
        return (
            t.computeType,
            t.payloadHash,
            t.finished,
            t.finalResult,
            t.threshold,
            t.responseCount
        );
    }

    function getAllDataTaskIds() external view returns (uint256[] memory) {
        uint256 count = nextDataTaskId;
        uint256[] memory ids = new uint256[](count);
        for (uint256 i = 0; i < count; i++) {
            ids[i] = i;
        }
        return ids;
    }

    function getAllComputeTaskIds() external view returns (uint256[] memory) {
        uint256 count = nextComputeTaskId;
        uint256[] memory ids = new uint256[](count);
        for (uint256 i = 0; i < count; i++) {
            ids[i] = i;
        }
        return ids;
    }

    function isComputeOracleAllowed(uint256 taskId, address oracle) external view returns (bool) {
        ComputeTask storage t = computeTasks[taskId];
        return t.oracleAllowed[oracle];
    }
}
