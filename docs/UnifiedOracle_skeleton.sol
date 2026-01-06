// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// 仅保留核心结构与接口签名，适合论文展示。
interface UnifiedOracleSkeleton {
    enum AggregationMode { MEAN, MEDIAN, WEIGHTED_MEAN }

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

    function registerOracle(address oracle) external;
    function registerDataTask(
        string calldata sourceConfig,
        AggregationMode mode,
        address[] calldata allowedOracles,
        uint256[] calldata weights,
        uint256 minResponses
    ) external returns (uint256);
    function submitData(uint256 taskId, uint256 value, bytes calldata signature) external;
    function registerComputeTask(
        bytes32 computeType,
        bytes32 payloadHash,
        address[] calldata allowedOracles,
        uint256 threshold
    ) external returns (uint256);
    function submitComputeResult(uint256 taskId, bytes32 result, bytes calldata signature) external;

    function getDataTaskSummary(uint256 taskId) external view returns (DataTaskMeta memory);
    function getComputeTaskSummary(uint256 taskId) external view returns (ComputeTaskMeta memory);
    function getHealth() external view returns (address, uint256, uint256, uint256, uint256);
}
