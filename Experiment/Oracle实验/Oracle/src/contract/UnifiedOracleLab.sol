// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract UnifiedOracleLab {
    enum AggregationMode {
        MEAN,
        MEDIAN,
        WEIGHTED_MEAN,
        TRIMMED_MEAN
    }

    struct DataTaskMeta {
        bytes32 sourceHash;
        AggregationMode mode;
        uint256 minResponses;
        bool finished;
    }

    struct ComputeTaskMeta {
        bytes32 computeType;
        bytes32 payloadHash;
        uint256 threshold;
        bool finished;
    }

    struct DataTask {
        bytes32 sourceHash;
        AggregationMode mode;
        uint256 minResponses;
        bool finished;
        uint256 result;
        uint256 submissionCount;
        address[] allowedOracles;
        uint256[] submissions;
        address[] submitters;
        mapping(address => bool) allowed;
        mapping(address => bool) submitted;
        mapping(address => uint256) weightOf;
    }

    struct ComputeTask {
        bytes32 computeType;
        bytes32 payloadHash;
        uint256 threshold;
        bool finished;
        bytes32 result;
        uint256 submissionCount;
        mapping(address => bool) allowed;
        mapping(address => bool) submitted;
        mapping(bytes32 => uint256) voteCount;
    }

    address public owner;

    uint256 public totalDataTasks;
    uint256 public totalComputeTasks;
    uint256 public finishedTaskCount;
    uint256 public registeredOracleCount;

    mapping(address => bool) public registeredOracles;
    mapping(uint256 => DataTask) private dataTasks;
    mapping(uint256 => ComputeTask) private computeTasks;
    mapping(bytes32 => bool) private liteComputeUsed;

    event OracleRegistered(address indexed oracle);
    event DataTaskRegistered(uint256 indexed taskId, AggregationMode mode, uint256 minResponses, bytes32 sourceHash);
    event DataSubmitted(uint256 indexed taskId, address indexed oracle, uint256 value);
    event DataTaskFinalized(uint256 indexed taskId, uint256 result, AggregationMode mode);
    event ComputeTaskRegistered(uint256 indexed taskId, bytes32 computeType, uint256 threshold, bytes32 payloadHash);
    event ComputeSubmitted(uint256 indexed taskId, address indexed oracle, bytes32 result);
    event ComputeTaskFinalized(uint256 indexed taskId, bytes32 result, uint256 confirmations);
    event ComputeResultLiteSubmitted(bytes32 indexed computeType, bytes32 indexed payloadHash, bytes32 result, address indexed oracle);

    uint256 internal constant TRIM_BPS_DEFAULT = 2500; // 25%
    bytes32 internal constant DATA_DOMAIN = keccak256("DATA");
    bytes32 internal constant COMPUTE_DOMAIN = keccak256("COMPUTE");

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function registerOracle(address oracle) external onlyOwner {
        require(oracle != address(0), "zero address");
        if (!registeredOracles[oracle]) {
            registeredOracles[oracle] = true;
            registeredOracleCount += 1;
            emit OracleRegistered(oracle);
        }
    }

    function registerDataTask(
        string calldata sourceConfig,
        AggregationMode mode,
        address[] calldata allowedOracles,
        uint256[] calldata weights,
        uint256 minResponses
    ) external returns (uint256) {
        require(allowedOracles.length > 0, "empty oracle set");
        require(minResponses > 0 && minResponses <= allowedOracles.length, "invalid minResponses");
        if (mode == AggregationMode.WEIGHTED_MEAN) {
            require(weights.length == allowedOracles.length, "weights length mismatch");
        }

        unchecked {
            totalDataTasks += 1;
        }
        uint256 taskId = totalDataTasks;
        DataTask storage task = dataTasks[taskId];
        task.sourceHash = keccak256(bytes(sourceConfig));
        task.mode = mode;
        task.minResponses = minResponses;

        for (uint256 i = 0; i < allowedOracles.length; ) {
            address oracle = allowedOracles[i];
            require(registeredOracles[oracle], "oracle not registered");
            require(!task.allowed[oracle], "duplicate oracle");
            task.allowed[oracle] = true;
            task.allowedOracles.push(oracle);
            if (mode == AggregationMode.WEIGHTED_MEAN) {
                task.weightOf[oracle] = weights[i];
            }
            unchecked {
                i++;
            }
        }

        emit DataTaskRegistered(taskId, mode, minResponses, task.sourceHash);
        return taskId;
    }

    function submitData(uint256 taskId, uint256 value, bytes calldata signature) external {
        DataTask storage task = dataTasks[taskId];
        require(task.minResponses > 0, "task not found");
        require(!task.finished, "task already finished");
        require(task.allowed[msg.sender], "oracle not allowed");
        require(!task.submitted[msg.sender], "oracle already submitted");

        bytes32 digest = keccak256(abi.encodePacked(address(this), DATA_DOMAIN, taskId, value));
        address signer = _recoverSigner(_toEthSignedMessageHash(digest), signature);
        require(signer == msg.sender, "invalid signature");

        task.submitted[msg.sender] = true;
        task.submissions.push(value);
        task.submitters.push(msg.sender);
        unchecked {
            task.submissionCount += 1;
        }

        emit DataSubmitted(taskId, msg.sender, value);

        if (task.submissionCount >= task.minResponses) {
            _finalizeDataTask(taskId);
        }
    }

    function registerComputeTask(
        bytes32 computeType,
        bytes32 payloadHash,
        address[] calldata allowedOracles,
        uint256 threshold
    ) external returns (uint256) {
        require(computeType != bytes32(0), "empty computeType");
        require(payloadHash != bytes32(0), "empty payloadHash");
        require(allowedOracles.length > 0, "empty oracle set");
        require(threshold > 0 && threshold <= allowedOracles.length, "invalid threshold");

        unchecked {
            totalComputeTasks += 1;
        }
        uint256 taskId = totalComputeTasks;
        ComputeTask storage task = computeTasks[taskId];
        task.computeType = computeType;
        task.payloadHash = payloadHash;
        task.threshold = threshold;

        for (uint256 i = 0; i < allowedOracles.length; ) {
            address oracle = allowedOracles[i];
            require(registeredOracles[oracle], "oracle not registered");
            require(!task.allowed[oracle], "duplicate oracle");
            task.allowed[oracle] = true;
            unchecked {
                i++;
            }
        }

        emit ComputeTaskRegistered(taskId, computeType, threshold, payloadHash);
        return taskId;
    }

    function submitComputeResult(uint256 taskId, bytes32 result, bytes calldata signature) external {
        ComputeTask storage task = computeTasks[taskId];
        require(task.threshold > 0, "task not found");
        require(!task.finished, "task already finished");
        require(task.allowed[msg.sender], "oracle not allowed");
        require(!task.submitted[msg.sender], "oracle already submitted");

        bytes32 digest = keccak256(abi.encodePacked(address(this), COMPUTE_DOMAIN, taskId, result));
        address signer = _recoverSigner(_toEthSignedMessageHash(digest), signature);
        require(signer == msg.sender, "invalid signature");

        _submitComputeVote(task, taskId, result, msg.sender);
    }

    function submitComputeResultBatch(
        uint256 taskId,
        bytes32 result,
        bytes[] calldata signatures
    ) external {
        ComputeTask storage task = computeTasks[taskId];
        require(task.threshold > 0, "task not found");
        require(!task.finished, "task already finished");
        require(signatures.length > 0, "empty signatures");

        bytes32 digest = keccak256(abi.encodePacked(address(this), COMPUTE_DOMAIN, taskId, result));
        bytes32 ethSignedDigest = _toEthSignedMessageHash(digest);

        for (uint256 i = 0; i < signatures.length; ) {
            if (task.finished) {
                break;
            }

            address signer = _recoverSigner(ethSignedDigest, signatures[i]);
            require(task.allowed[signer], "oracle not allowed");
            if (!task.submitted[signer]) {
                _submitComputeVote(task, taskId, result, signer);
            }

            unchecked {
                i++;
            }
        }
    }

    // Low-overhead mode for trusted consortium scenarios:
    // one whitelisted oracle submits one finalized compute result bound to payloadHash.
    function submitComputeResultLite(
        bytes32 computeType,
        bytes32 payloadHash,
        bytes32 result
    ) external {
        require(computeType != bytes32(0), "empty computeType");
        require(payloadHash != bytes32(0), "empty payloadHash");
        require(registeredOracles[msg.sender], "oracle not registered");

        bytes32 key = keccak256(abi.encodePacked(msg.sender, computeType, payloadHash));
        require(!liteComputeUsed[key], "already submitted");
        liteComputeUsed[key] = true;

        unchecked {
            finishedTaskCount += 1;
        }
        emit ComputeResultLiteSubmitted(computeType, payloadHash, result, msg.sender);
    }

    function getDataTaskSummary(uint256 taskId) external view returns (DataTaskMeta memory) {
        DataTask storage task = dataTasks[taskId];
        require(task.minResponses > 0, "task not found");
        return
            DataTaskMeta({
                sourceHash: task.sourceHash,
                mode: task.mode,
                minResponses: task.minResponses,
                finished: task.finished
            });
    }

    function getComputeTaskSummary(uint256 taskId) external view returns (ComputeTaskMeta memory) {
        ComputeTask storage task = computeTasks[taskId];
        require(task.threshold > 0, "task not found");
        return
            ComputeTaskMeta({
                computeType: task.computeType,
                payloadHash: task.payloadHash,
                threshold: task.threshold,
                finished: task.finished
            });
    }

    function getHealth() external view returns (address, uint256, uint256, uint256, uint256) {
        return (owner, registeredOracleCount, totalDataTasks, totalComputeTasks, finishedTaskCount);
    }

    function getDataTaskResult(uint256 taskId) external view returns (bool, uint256, uint256) {
        DataTask storage task = dataTasks[taskId];
        require(task.minResponses > 0, "task not found");
        return (task.finished, task.result, task.submissionCount);
    }

    function getComputeTaskResult(uint256 taskId) external view returns (bool, bytes32, uint256, uint256) {
        ComputeTask storage task = computeTasks[taskId];
        require(task.threshold > 0, "task not found");
        uint256 confirmCount = task.finished ? task.voteCount[task.result] : 0;
        return (task.finished, task.result, confirmCount, task.submissionCount);
    }

    function _finalizeDataTask(uint256 taskId) internal {
        DataTask storage task = dataTasks[taskId];
        require(!task.finished, "already finalized");
        uint256 result;
        if (task.mode == AggregationMode.MEAN) {
            result = _mean(task.submissions);
        } else if (task.mode == AggregationMode.MEDIAN) {
            result = _median(task.submissions);
        } else if (task.mode == AggregationMode.TRIMMED_MEAN) {
            result = _trimmedMean(task.submissions, TRIM_BPS_DEFAULT);
        } else {
            result = _weightedMean(task.submissions, task.submitters, task);
        }
        task.result = result;
        task.finished = true;
        unchecked {
            finishedTaskCount += 1;
        }
        emit DataTaskFinalized(taskId, result, task.mode);
    }

    function _mean(uint256[] storage values) internal view returns (uint256) {
        uint256 sum = 0;
        for (uint256 i = 0; i < values.length; ) {
            sum += values[i];
            unchecked {
                i++;
            }
        }
        return sum / values.length;
    }

    function _median(uint256[] storage values) internal view returns (uint256) {
        uint256[] memory copy = new uint256[](values.length);
        for (uint256 i = 0; i < values.length; ) {
            copy[i] = values[i];
            unchecked {
                i++;
            }
        }
        _insertionSort(copy);
        uint256 n = copy.length;
        if (n % 2 == 1) {
            return copy[n / 2];
        }
        return (copy[(n / 2) - 1] + copy[n / 2]) / 2;
    }

    function _weightedMean(
        uint256[] storage values,
        address[] storage submitters,
        DataTask storage task
    ) internal view returns (uint256) {
        uint256 weightedSum = 0;
        uint256 totalWeight = 0;

        for (uint256 i = 0; i < values.length; ) {
            uint256 w = task.weightOf[submitters[i]];
            weightedSum += values[i] * w;
            totalWeight += w;
            unchecked {
                i++;
            }
        }

        if (totalWeight == 0) {
            return _mean(values);
        }
        return weightedSum / totalWeight;
    }

    function _trimmedMean(uint256[] storage values, uint256 trimBps) internal view returns (uint256) {
        require(values.length > 0, "empty values");
        uint256[] memory copy = new uint256[](values.length);
        for (uint256 i = 0; i < values.length; ) {
            copy[i] = values[i];
            unchecked {
                i++;
            }
        }
        _insertionSort(copy);

        uint256 n = copy.length;
        uint256 trimEachSide = (n * trimBps) / 10000;
        if (trimEachSide * 2 >= n) {
            return _median(values);
        }

        uint256 sum = 0;
        uint256 count = 0;
        for (uint256 i = trimEachSide; i < n - trimEachSide; ) {
            sum += copy[i];
            unchecked {
                count += 1;
                i++;
            }
        }
        return sum / count;
    }

    function _insertionSort(uint256[] memory arr) internal pure {
        for (uint256 i = 1; i < arr.length; ) {
            uint256 key = arr[i];
            uint256 j = i;
            while (j > 0 && arr[j - 1] > key) {
                arr[j] = arr[j - 1];
                unchecked {
                    j--;
                }
            }
            arr[j] = key;
            unchecked {
                i++;
            }
        }
    }

    function _toEthSignedMessageHash(bytes32 hash) internal pure returns (bytes32) {
        return keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", hash));
    }

    function _submitComputeVote(
        ComputeTask storage task,
        uint256 taskId,
        bytes32 result,
        address signer
    ) internal {
        task.submitted[signer] = true;
        unchecked {
            task.submissionCount += 1;
            task.voteCount[result] += 1;
        }

        emit ComputeSubmitted(taskId, signer, result);

        uint256 votes = task.voteCount[result];
        if (votes >= task.threshold) {
            task.finished = true;
            task.result = result;
            unchecked {
                finishedTaskCount += 1;
            }
            emit ComputeTaskFinalized(taskId, result, votes);
        }
    }

    function _recoverSigner(bytes32 digest, bytes memory signature) internal pure returns (address) {
        require(signature.length == 65, "invalid signature length");
        bytes32 r;
        bytes32 s;
        uint8 v;
        assembly {
            r := mload(add(signature, 0x20))
            s := mload(add(signature, 0x40))
            v := byte(0, mload(add(signature, 0x60)))
        }
        if (v < 27) {
            v += 27;
        }
        require(v == 27 || v == 28, "invalid signature v");
        address recovered = ecrecover(digest, v, r, s);
        require(recovered != address(0), "ecrecover failed");
        return recovered;
    }
}
