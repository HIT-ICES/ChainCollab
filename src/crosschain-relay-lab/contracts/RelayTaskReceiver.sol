// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract RelayTaskReceiver {
    struct DataTaskResult {
        uint256 fromChainId;
        uint256 value;
        string label;
        uint256 timestamp;
    }

    struct ComputeTaskResult {
        uint256 fromChainId;
        uint256 a;
        uint256 b;
        string op;
        int256 result;
        uint256 timestamp;
    }

    DataTaskResult public lastDataTask;
    ComputeTaskResult public lastComputeTask;

    uint256 public dataTaskCount;
    uint256 public computeTaskCount;

    event DataTaskHandled(
        uint256 indexed fromChainId,
        uint256 value,
        string label
    );

    event ComputeTaskHandled(
        uint256 indexed fromChainId,
        uint256 a,
        uint256 b,
        string op,
        int256 result
    );

    function handleDataTask(
        uint256 fromChainId,
        uint256 value,
        string calldata label
    ) external returns (bool) {
        dataTaskCount += 1;

        lastDataTask = DataTaskResult({
            fromChainId: fromChainId,
            value: value,
            label: label,
            timestamp: block.timestamp
        });

        emit DataTaskHandled(fromChainId, value, label);
        return true;
    }

    function handleComputeTask(
        uint256 fromChainId,
        uint256 a,
        uint256 b,
        string calldata op
    ) external returns (int256 result) {
        bytes32 opHash = keccak256(bytes(op));
        if (opHash == keccak256(bytes("add"))) {
            result = int256(a + b);
        } else if (opHash == keccak256(bytes("sub"))) {
            result = int256(a) - int256(b);
        } else if (opHash == keccak256(bytes("mul"))) {
            result = int256(a * b);
        } else if (opHash == keccak256(bytes("div"))) {
            require(b != 0, "div by zero");
            result = int256(a / b);
        } else if (opHash == keccak256(bytes("pow2sum"))) {
            result = int256(a * a + b * b);
        } else {
            revert("unsupported op");
        }

        computeTaskCount += 1;

        lastComputeTask = ComputeTaskResult({
            fromChainId: fromChainId,
            a: a,
            b: b,
            op: op,
            result: result,
            timestamp: block.timestamp
        });

        emit ComputeTaskHandled(fromChainId, a, b, op, result);
    }
}
