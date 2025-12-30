// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title AggregatingOracle
/// @notice 支持注册任务、授予 Oracle 权限，验证 Oracle 签名后上链数据，并提供多种聚合模式（均值、加权均值、强一致阈值）。
/// @dev 签名格式：对 keccak256(abi.encodePacked(taskId, value)) 做 ECDSA，链上用 ecrecover 校验。
contract AggregatingOracle {
    struct OracleInfo {
        bool active;
    }

    struct Task {
        address requester;
        bool finished;
        bytes32 dataType; // 描述数据类型或单位
        AggregationMode mode;
        uint256 threshold; // 强一致模式使用：需要相同值达到的最小数量
        address[] allowedOracles;
        mapping(address => bool) oracleAllowed;
        mapping(address => bool) responded;
        uint256[] weights; // 与 allowedOracles 对齐
        Submission[] submissions;
        uint256 finalValue;
    }

    struct Submission {
        address oracle;
        uint256 value;
    }

    enum AggregationMode {
        MEAN,
        WEIGHTED_MEAN,
        STRONG_CONSISTENCY
    }

    address public owner;
    uint256 public nextTaskId;
    mapping(address => OracleInfo) public oracleRegistry;
    mapping(uint256 => Task) private tasks;

    event OracleRegistered(address indexed oracle);
    event OracleRemoved(address indexed oracle);
    event TaskRegistered(uint256 indexed taskId, bytes32 dataType, AggregationMode mode);
    event DataSubmitted(uint256 indexed taskId, address indexed oracle, uint256 value);
    event TaskFinalized(uint256 indexed taskId, uint256 finalValue);

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    // ========== Oracle 管理 ==========
    function registerOracle(address oracle) external onlyOwner {
        require(oracle != address(0), "zero address");
        require(!oracleRegistry[oracle].active, "already active");
        oracleRegistry[oracle].active = true;
        emit OracleRegistered(oracle);
    }

    function removeOracle(address oracle) external onlyOwner {
        require(oracleRegistry[oracle].active, "not active");
        oracleRegistry[oracle].active = false;
        emit OracleRemoved(oracle);
    }

    // ========== 任务管理 ==========
    /// @param allowedOracles 允许提交的 oracle 列表（必须在全局注册表 active）
    /// @param weights 对应 oracle 的权重，只有在 WEIGHTED_MEAN 模式下使用；其他模式可传空数组
    /// @param threshold 强一致模式使用，需要相同值的最小数量
    function registerTask(
        bytes32 dataType,
        AggregationMode mode,
        address[] calldata allowedOracles,
        uint256[] calldata weights,
        uint256 threshold
    ) external returns (uint256) {
        require(allowedOracles.length > 0, "no oracles");
        if (mode == AggregationMode.WEIGHTED_MEAN) {
            require(weights.length == allowedOracles.length, "weight length mismatch");
        }
        uint256 taskId = nextTaskId;
        nextTaskId++;

        Task storage t = tasks[taskId];
        t.requester = msg.sender;
        t.dataType = dataType;
        t.mode = mode;
        t.threshold = threshold;
        t.allowedOracles = allowedOracles;
        if (mode == AggregationMode.WEIGHTED_MEAN) {
            t.weights = weights;
        }
        for (uint256 i = 0; i < allowedOracles.length; i++) {
            address o = allowedOracles[i];
            require(oracleRegistry[o].active, "oracle not registered");
            t.oracleAllowed[o] = true;
        }

        emit TaskRegistered(taskId, dataType, mode);
        return taskId;
    }

    // ========== 数据提交 ==========
    /// @param value Oracle 读取到的数值
    /// @param signature 对 keccak256(abi.encodePacked(taskId, value)) 的签名
    function submitData(uint256 taskId, uint256 value, bytes calldata signature) external {
        Task storage t = tasks[taskId];
        require(!t.finished, "task finished");
        require(t.oracleAllowed[msg.sender], "oracle not allowed");
        require(!t.responded[msg.sender], "already responded");

        // 校验签名与 msg.sender 匹配
        bytes32 digest = keccak256(abi.encodePacked(taskId, value));
        address recovered = _recoverSigner(digest, signature);
        require(recovered == msg.sender, "bad signature");

        t.responded[msg.sender] = true;
        t.submissions.push(Submission({oracle: msg.sender, value: value}));

        emit DataSubmitted(taskId, msg.sender, value);

        // 检查是否满足终止条件
        _maybeFinalize(taskId, t);
    }

    // ========== 内部逻辑 ==========
    function _maybeFinalize(uint256 taskId, Task storage t) internal {
        if (t.mode == AggregationMode.STRONG_CONSISTENCY) {
            // 统计相同值出现次数
            uint256 n = t.submissions.length;
            for (uint256 i = 0; i < n; i++) {
                uint256 candidate = t.submissions[i].value;
                uint256 count = 0;
                for (uint256 j = 0; j < n; j++) {
                    if (t.submissions[j].value == candidate) {
                        count++;
                    }
                }
                if (count >= t.threshold) {
                    _finalize(taskId, t, candidate);
                    return;
                }
            }
        } else {
            // 均值或加权均值：需要所有 allowedOracles 都提交才聚合
            if (t.submissions.length == t.allowedOracles.length) {
                uint256 aggregated = _aggregate(t);
                _finalize(taskId, t, aggregated);
            }
        }
    }

    function _aggregate(Task storage t) internal view returns (uint256) {
        if (t.mode == AggregationMode.MEAN) {
            uint256 sum = 0;
            for (uint256 i = 0; i < t.submissions.length; i++) {
                sum += t.submissions[i].value;
            }
            return sum / t.submissions.length;
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

    function _weightOf(Task storage t, address oracle) internal view returns (uint256) {
        for (uint256 i = 0; i < t.allowedOracles.length; i++) {
            if (t.allowedOracles[i] == oracle) {
                return t.weights[i];
            }
        }
        return 0;
    }

    function _finalize(uint256 taskId, Task storage t, uint256 finalValue) internal {
        t.finished = true;
        t.finalValue = finalValue;
        emit TaskFinalized(taskId, finalValue);
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

    // ========== 视图 ==========
    function getTask(uint256 taskId)
        external
        view
        returns (
            address requester,
            bool finished,
            bytes32 dataType,
            AggregationMode mode,
            uint256 threshold,
            uint256 finalValue,
            uint256 submissionCount
        )
    {
        Task storage t = tasks[taskId];
        return (
            t.requester,
            t.finished,
            t.dataType,
            t.mode,
            t.threshold,
            t.finalValue,
            t.submissions.length
        );
    }

    function getSubmission(uint256 taskId, uint256 index) external view returns (address oracle, uint256 value) {
        Task storage t = tasks[taskId];
        require(index < t.submissions.length, "out of range");
        Submission storage s = t.submissions[index];
        return (s.oracle, s.value);
    }
}
