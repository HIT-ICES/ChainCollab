// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract DummyOracle {
    function getExternalData(
        uint256,
        string calldata,
        string calldata,
        string calldata
    ) external pure returns (string memory value) {
        return "0";
    }

    function runComputeTask(
        uint256,
        string calldata,
        string calldata,
        string calldata
    ) external pure returns (string memory value) {
        return "0";
    }

    function getDataItem(
        uint256,
        string calldata
    ) external pure returns (string memory value) {
        return "0";
    }
}

contract DummyIdentityRegistry {
    function getIdentityOrg(address) external pure returns (string memory) {
        return "ORG";
    }
}
