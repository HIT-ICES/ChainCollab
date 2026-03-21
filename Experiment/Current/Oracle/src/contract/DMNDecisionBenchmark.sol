// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract DMNDecisionBenchmark {
    uint256 public lastResult;

    event DecisionEvaluated(bytes32 indexed modelType, uint256 result, uint256 scale);

    function evalDecisionTableFirst(
        uint256 x,
        uint256 y,
        uint256[] calldata packedRules
    ) external returns (uint256) {
        require(packedRules.length > 0, "empty rules");
        require(packedRules.length % 5 == 0, "invalid packed rules");
        uint256 ruleCount = packedRules.length / 5;

        uint256 result = 0;
        for (uint256 i = 0; i < ruleCount; ) {
            uint256 off = i * 5;
            uint256 xMin = packedRules[off];
            uint256 xMax = packedRules[off + 1];
            uint256 yMin = packedRules[off + 2];
            uint256 yMax = packedRules[off + 3];
            uint256 output = packedRules[off + 4];
            if (x >= xMin && x <= xMax && y >= yMin && y <= yMax) {
                result = output;
                break;
            }
            unchecked {
                i++;
            }
        }

        lastResult = result;
        emit DecisionEvaluated("table_first", result, ruleCount);
        return result;
    }

    function evalDecisionTableCollect(
        uint256 x,
        uint256 y,
        uint256[] calldata packedRules
    ) external returns (uint256) {
        require(packedRules.length > 0, "empty rules");
        require(packedRules.length % 5 == 0, "invalid packed rules");
        uint256 ruleCount = packedRules.length / 5;

        uint256 sum = 0;
        for (uint256 i = 0; i < ruleCount; ) {
            uint256 off = i * 5;
            uint256 xMin = packedRules[off];
            uint256 xMax = packedRules[off + 1];
            uint256 yMin = packedRules[off + 2];
            uint256 yMax = packedRules[off + 3];
            uint256 output = packedRules[off + 4];
            if (x >= xMin && x <= xMax && y >= yMin && y <= yMax) {
                sum += output;
            }
            unchecked {
                i++;
            }
        }

        lastResult = sum;
        emit DecisionEvaluated("table_collect", sum, ruleCount);
        return sum;
    }

    function evalScorecard(
        uint256[] calldata features,
        uint256[] calldata thresholds,
        uint256[] calldata highWeights,
        uint256[] calldata lowWeights,
        uint256 baseScore
    ) external returns (uint256) {
        uint256 n = features.length;
        require(n > 0, "empty features");
        require(
            thresholds.length == n &&
                highWeights.length == n &&
                lowWeights.length == n,
            "length mismatch"
        );

        uint256 score = baseScore;
        for (uint256 i = 0; i < n; ) {
            if (features[i] >= thresholds[i]) {
                score += highWeights[i];
            } else {
                score += lowWeights[i];
            }
            unchecked {
                i++;
            }
        }

        lastResult = score;
        emit DecisionEvaluated("scorecard", score, n);
        return score;
    }

    function evalDecisionGraph(
        uint256[] calldata features,
        uint256[] calldata weights,
        uint256[] calldata biases,
        uint256 nodeCount,
        uint256 iterations
    ) external returns (uint256) {
        uint256 f = features.length;
        require(f > 0, "empty features");
        require(nodeCount > 0, "nodeCount=0");
        require(iterations > 0, "iterations=0");
        require(weights.length == nodeCount * f, "weights mismatch");
        require(biases.length == nodeCount, "bias mismatch");

        uint256 acc = 0;
        for (uint256 it = 0; it < iterations; ) {
            for (uint256 n = 0; n < nodeCount; ) {
                uint256 s = biases[n] + acc;
                uint256 off = n * f;
                for (uint256 j = 0; j < f; ) {
                    s += weights[off + j] * features[j];
                    unchecked {
                        j++;
                    }
                }
                acc = (acc + (s % 1000003)) % 1000003;
                unchecked {
                    n++;
                }
            }
            unchecked {
                it++;
            }
        }

        lastResult = acc;
        emit DecisionEvaluated("decision_graph", acc, nodeCount * iterations);
        return acc;
    }
}
