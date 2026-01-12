// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// 本地模拟链用的最小 AggregatingOracle 合约（与仓库版本一致，可替换）
contract AggregatingOracle {
    struct OracleInfo {
        bool active;
    }

    struct Task {
        address requester;
        bool finished;
        bytes32 dataType;
        AggregationMode mode;
        uint256 threshold;
        address[] allowedOracles;
        mapping(address => bool) oracleAllowed;
        mapping(address => bool) responded;
        uint256[] weights;
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

    function submitData(uint256 taskId, uint256 value, bytes calldata signature) external {
        Task storage t = tasks[taskId];
        require(!t.finished, "task finished");
        require(t.oracleAllowed[msg.sender], "oracle not allowed");
        require(!t.responded[msg.sender], "already responded");

        bytes32 digest = keccak256(abi.encodePacked(taskId, value));
        address recovered = _recoverSigner(digest, signature);
        require(recovered == msg.sender, "bad signature");

        t.responded[msg.sender] = true;
        t.submissions.push(Submission({oracle: msg.sender, value: value}));
        emit DataSubmitted(taskId, msg.sender, value);

        _maybeFinalize(taskId, t);
    }

    function _maybeFinalize(uint256 taskId, Task storage t) internal {
        if (t.mode == AggregationMode.STRONG_CONSISTENCY) {
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
}
