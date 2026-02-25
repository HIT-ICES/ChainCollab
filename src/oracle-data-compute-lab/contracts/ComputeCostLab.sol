// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract ComputeCostLab {
    uint256 public lastResult;
    uint256 public lastHeavyResult;

    event Computed(address indexed caller, uint256 x0, uint256 x1, uint256 result);
    event ComputedHeavy(address indexed caller, uint256 x0, uint256 x1, uint256 loops, uint256 result);

    function computeRiskOnChain(uint256 x0, uint256 x1) external returns (uint256 result) {
        result = ((x0 * 2) + x1) / 10;
        lastResult = result;
        emit Computed(msg.sender, x0, x1, result);
    }

    function computeRiskHeavyOnChain(
        uint256 x0,
        uint256 x1,
        uint256 loops
    ) external returns (uint256 result) {
        require(loops > 0 && loops <= 10000, "bad loops");
        uint256 acc = ((x0 * 2) + x1) / 10;
        for (uint256 i = 0; i < loops; i++) {
            acc = (acc * 1103515245 + 12345 + i) % 1000000007;
        }
        result = acc;
        lastHeavyResult = result;
        emit ComputedHeavy(msg.sender, x0, x1, loops, result);
    }
}
