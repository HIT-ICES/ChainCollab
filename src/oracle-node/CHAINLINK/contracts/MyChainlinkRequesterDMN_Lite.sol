// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@chainlink/contracts/src/v0.8/operatorforwarder/ChainlinkClient.sol";
import "@chainlink/contracts/src/v0.8/shared/access/ConfirmedOwner.sol";

/// @notice 轻量版 DMN 请求合约：仅依赖 Operator 直写回，不引入 OCR 聚合。
contract MyChainlinkRequesterDMN_Lite is ChainlinkClient, ConfirmedOwner {
    using Chainlink for Chainlink.Request;

    bytes public dmnResult;

    address private oracle;
    bytes32 private jobId;
    uint256 private fee;

    mapping(address => bool) public baselineWriters;

    struct BaselineResult {
        bytes32 hash;
        string raw;
        bool exists;
    }

    mapping(bytes32 => BaselineResult) public baselines;
    mapping(bytes32 => string) private rawByRequestId;
    mapping(bytes32 => bool) private rawByRequestExists;

    mapping(bytes32 => string) public rawResults;
    mapping(bytes32 => bool) private rawResultExists;
    bytes32[] private rawResultHashes;

    event RequestSent(bytes32 indexed requestId, uint256 timestamp);
    event DecisionFulfilled(bytes32 indexed requestId, bytes result);
    event RawResultStored(bytes32 indexed hash, string raw);
    event BaselineCommitted(bytes32 indexed requestId, bytes32 hash, string raw);
    event BaselineWriterUpdated(address indexed writer, bool allowed);

    constructor(
        address _linkToken,
        address _oracle,
        bytes32 _jobId,
        uint256 _fee
    ) ConfirmedOwner(msg.sender) {
        _setChainlinkToken(_linkToken);
        oracle = _oracle;
        jobId = _jobId;
        fee = _fee;
    }

    function requestDMNDecision(
        string calldata url,
        string calldata dmnContent,
        string calldata decisionId,
        string calldata inputData
    ) external onlyOwner returns (bytes32 requestId) {
        Chainlink.Request memory req = _buildChainlinkRequest(jobId, address(this), this.fulfill.selector);

        req._add("url", url);
        req._add("dmnContent", dmnContent);
        req._add("decisionId", decisionId);
        req._add("inputData", inputData);

        requestId = _sendChainlinkRequestTo(oracle, req, fee);
        emit RequestSent(requestId, block.timestamp);
        return requestId;
    }

    function fulfill(bytes32 _requestId, bytes memory _data)
        public
        recordChainlinkFulfillment(_requestId)
    {
        dmnResult = _data;
        emit DecisionFulfilled(_requestId, _data);
    }

    function withdrawLink() external onlyOwner {
        LinkTokenInterface link = LinkTokenInterface(_chainlinkTokenAddress());
        require(link.transfer(msg.sender, link.balanceOf(address(this))), "Unable to transfer");
    }

    function setJobId(bytes32 _jobId) external onlyOwner {
        jobId = _jobId;
    }

    function getJobId() external view returns (bytes32) {
        return jobId;
    }

    function setBaselineWriter(address writer, bool allowed) external onlyOwner {
        baselineWriters[writer] = allowed;
        emit BaselineWriterUpdated(writer, allowed);
    }

    function _isAuthorizedBaselineWriter() internal view returns (bool) {
        return msg.sender == owner() || baselineWriters[msg.sender];
    }

    function commitBaselineFromRaw(bytes32 requestId, string calldata raw) external {
        require(_isAuthorizedBaselineWriter(), "Not authorized");

        bytes32 rawHash = keccak256(bytes(raw));

        BaselineResult storage existing = baselines[requestId];
        if (existing.exists) {
            require(existing.hash == rawHash, "Baseline hash mismatch");
        } else {
            baselines[requestId] = BaselineResult({
                hash: rawHash,
                raw: raw,
                exists: true
            });
        }

        rawByRequestId[requestId] = raw;
        rawByRequestExists[requestId] = true;

        rawResults[rawHash] = raw;
        if (!rawResultExists[rawHash]) {
            rawResultExists[rawHash] = true;
            rawResultHashes.push(rawHash);
        }

        emit RawResultStored(rawHash, raw);
        emit BaselineCommitted(requestId, rawHash, raw);
    }

    function getRawByRequestId(bytes32 requestId) external view returns (string memory) {
        require(rawByRequestExists[requestId], "Result not found");
        return rawByRequestId[requestId];
    }

    function rawResultCount() external view returns (uint256) {
        return rawResultHashes.length;
    }

    function rawResultHashAt(uint256 index) external view returns (bytes32) {
        return rawResultHashes[index];
    }

    function getAllRawResults() external view returns (bytes32[] memory hashes, string[] memory raws) {
        uint256 count = rawResultHashes.length;
        hashes = new bytes32[](count);
        raws = new string[](count);
        for (uint256 i = 0; i < count; i++) {
            bytes32 hash = rawResultHashes[i];
            hashes[i] = hash;
            raws[i] = rawResults[hash];
        }
        return (hashes, raws);
    }

    function getDMNResult() external view returns (bytes memory) {
        return dmnResult;
    }
}
