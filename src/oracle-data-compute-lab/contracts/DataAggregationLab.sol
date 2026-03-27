// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface ISlotRegistryForAggregation {
    function setSlot(bytes32 slotKey, string calldata value, string calldata source) external;
}

contract DataAggregationLab {
    enum AggregationMethod {
        MEAN,
        MEDIAN,
        TRIMMED_MEAN,
        WEIGHTED_MEAN
    }

    struct Task {
        bytes32 slotKey;
        string sourceUrl;
        string jsonPath;
        AggregationMethod method;
        uint16 trimBps;
        uint32 minSubmissions;
        bool finalized;
        uint256 result;
    }

    struct Submission {
        address oracle;
        uint256 value;
        uint256 weight;
    }

    address public owner;
    mapping(address => bool) public oracles;
    ISlotRegistryForAggregation public slotRegistry;
    uint256 public nextTaskId;

    mapping(uint256 => Task) public tasks;
    mapping(uint256 => Submission[]) private taskSubmissions;
    mapping(uint256 => mapping(address => bool)) public hasSubmitted;

    event OracleUpdated(address indexed oracle, bool enabled);
    event SlotRegistryUpdated(address indexed slotRegistry);
    event TaskRequested(
        uint256 indexed taskId,
        bytes32 indexed slotKey,
        AggregationMethod method,
        uint32 minSubmissions
    );
    event Submitted(
        uint256 indexed taskId,
        address indexed oracle,
        uint256 value,
        uint256 weight
    );
    event Finalized(
        uint256 indexed taskId,
        bytes32 indexed slotKey,
        AggregationMethod method,
        uint256 result
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    modifier onlyOracle() {
        require(oracles[msg.sender], "not oracle");
        _;
    }

    constructor(address slotRegistryAddress) {
        require(slotRegistryAddress != address(0), "zero registry");
        owner = msg.sender;
        slotRegistry = ISlotRegistryForAggregation(slotRegistryAddress);
        emit SlotRegistryUpdated(slotRegistryAddress);
    }

    function setOracle(address oracle, bool enabled) external onlyOwner {
        require(oracle != address(0), "zero oracle");
        oracles[oracle] = enabled;
        emit OracleUpdated(oracle, enabled);
    }

    function setSlotRegistry(address slotRegistryAddress) external onlyOwner {
        require(slotRegistryAddress != address(0), "zero registry");
        slotRegistry = ISlotRegistryForAggregation(slotRegistryAddress);
        emit SlotRegistryUpdated(slotRegistryAddress);
    }

    function requestTask(
        bytes32 slotKey,
        string calldata sourceUrl,
        string calldata jsonPath,
        AggregationMethod method,
        uint32 minSubmissions,
        uint16 trimBps
    ) external returns (uint256 taskId) {
        require(slotKey != bytes32(0), "invalid slot");
        require(minSubmissions > 0, "minSubmissions=0");
        if (method == AggregationMethod.TRIMMED_MEAN) {
            require(trimBps < 5000, "trim too large");
        }

        taskId = nextTaskId++;
        tasks[taskId] = Task({
            slotKey: slotKey,
            sourceUrl: sourceUrl,
            jsonPath: jsonPath,
            method: method,
            trimBps: trimBps,
            minSubmissions: minSubmissions,
            finalized: false,
            result: 0
        });
        emit TaskRequested(taskId, slotKey, method, minSubmissions);
    }

    function submit(
        uint256 taskId,
        uint256 value,
        uint256 weight
    ) external onlyOracle {
        Task storage t = tasks[taskId];
        require(t.minSubmissions > 0, "task missing");
        require(!t.finalized, "task finalized");
        require(!hasSubmitted[taskId][msg.sender], "already submitted");
        if (t.method == AggregationMethod.WEIGHTED_MEAN) {
            require(weight > 0, "weight=0");
        }

        hasSubmitted[taskId][msg.sender] = true;
        uint256 safeWeight = t.method == AggregationMethod.WEIGHTED_MEAN ? weight : 1;
        taskSubmissions[taskId].push(
            Submission({
                oracle: msg.sender,
                value: value,
                weight: safeWeight
            })
        );
        emit Submitted(taskId, msg.sender, value, safeWeight);
    }

    function finalize(uint256 taskId) external returns (uint256 aggregated) {
        Task storage t = tasks[taskId];
        require(t.minSubmissions > 0, "task missing");
        require(!t.finalized, "already finalized");
        require(taskSubmissions[taskId].length >= t.minSubmissions, "not enough submissions");

        if (t.method == AggregationMethod.MEAN) {
            aggregated = _mean(taskId);
        } else if (t.method == AggregationMethod.MEDIAN) {
            aggregated = _median(taskId);
        } else if (t.method == AggregationMethod.TRIMMED_MEAN) {
            aggregated = _trimmedMean(taskId, t.trimBps);
        } else if (t.method == AggregationMethod.WEIGHTED_MEAN) {
            aggregated = _weightedMean(taskId);
        } else {
            revert("unknown method");
        }

        t.finalized = true;
        t.result = aggregated;
        slotRegistry.setSlot(t.slotKey, _toString(aggregated), "external-aggregation");
        emit Finalized(taskId, t.slotKey, t.method, aggregated);
    }

    function getSubmissionCount(uint256 taskId) external view returns (uint256) {
        return taskSubmissions[taskId].length;
    }

    function getSubmission(
        uint256 taskId,
        uint256 index
    ) external view returns (address oracle, uint256 value, uint256 weight) {
        Submission storage s = taskSubmissions[taskId][index];
        return (s.oracle, s.value, s.weight);
    }

    function _mean(uint256 taskId) internal view returns (uint256) {
        Submission[] storage arr = taskSubmissions[taskId];
        uint256 sum = 0;
        for (uint256 i = 0; i < arr.length; i++) {
            sum += arr[i].value;
        }
        return sum / arr.length;
    }

    function _weightedMean(uint256 taskId) internal view returns (uint256) {
        Submission[] storage arr = taskSubmissions[taskId];
        uint256 weightedSum = 0;
        uint256 totalWeight = 0;
        for (uint256 i = 0; i < arr.length; i++) {
            weightedSum += arr[i].value * arr[i].weight;
            totalWeight += arr[i].weight;
        }
        require(totalWeight > 0, "total weight=0");
        return weightedSum / totalWeight;
    }

    function _median(uint256 taskId) internal view returns (uint256) {
        uint256[] memory values = _sortedValues(taskId);
        uint256 n = values.length;
        if (n % 2 == 1) {
            return values[n / 2];
        }
        return (values[(n / 2) - 1] + values[n / 2]) / 2;
    }

    function _trimmedMean(uint256 taskId, uint16 trimBps) internal view returns (uint256) {
        uint256[] memory values = _sortedValues(taskId);
        uint256 n = values.length;
        uint256 trim = (n * trimBps) / 10000;
        require(n > (trim * 2), "trim too aggressive");

        uint256 sum = 0;
        uint256 count = 0;
        for (uint256 i = trim; i < n - trim; i++) {
            sum += values[i];
            count += 1;
        }
        return sum / count;
    }

    function _sortedValues(uint256 taskId) internal view returns (uint256[] memory values) {
        Submission[] storage arr = taskSubmissions[taskId];
        values = new uint256[](arr.length);
        for (uint256 i = 0; i < arr.length; i++) {
            values[i] = arr[i].value;
        }
        for (uint256 i = 0; i < values.length; i++) {
            for (uint256 j = i + 1; j < values.length; j++) {
                if (values[j] < values[i]) {
                    uint256 tmp = values[i];
                    values[i] = values[j];
                    values[j] = tmp;
                }
            }
        }
    }

    function _toString(uint256 value) internal pure returns (string memory) {
        if (value == 0) {
            return "0";
        }
        uint256 temp = value;
        uint256 digits;
        while (temp != 0) {
            digits++;
            temp /= 10;
        }
        bytes memory buffer = new bytes(digits);
        while (value != 0) {
            digits -= 1;
            buffer[digits] = bytes1(uint8(48 + uint256(value % 10)));
            value /= 10;
        }
        return string(buffer);
    }
}
