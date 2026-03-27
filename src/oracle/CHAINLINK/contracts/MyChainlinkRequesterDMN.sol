// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@chainlink/contracts/src/v0.8/operatorforwarder/ChainlinkClient.sol";
import "@chainlink/contracts/src/v0.8/shared/access/ConfirmedOwner.sol";

contract MyChainlinkRequesterDMN is ChainlinkClient, ConfirmedOwner {

    using Chainlink for Chainlink.Request;

    enum RequestState {
        None,
        Pending,
        Fulfilled
    }

    // 返回值存储（存储 DMN 决策结果的字节数组）
    bytes public dmnResult;

    // oracle 节点地址
    address private oracle;
    // job ID: 你的节点 Job 的 ID，按 bytes32 传入
    bytes32 private jobId;
    // 支付给 Chainlink 节点的 LINK 金额（根据你的 Job 配置而定）
    uint256 private fee;
    // OCR 聚合合约地址（用于读取最新 hash）
    address public ocrAggregator;
    // 允许写入基准结果的地址
    mapping(address => bool) public baselineWriters;

    struct BaselineResult {
        bytes32 hash;
        uint128 hashLow;
        string raw;
        bool exists;
    }

    // requestId -> baseline
    mapping(bytes32 => BaselineResult) public baselines;
    mapping(bytes32 => RequestState) private requestStates;
    mapping(bytes32 => address) private requestRequesters;
    mapping(bytes32 => uint256) private requestCreatedAt;
    mapping(bytes32 => uint256) private requestFulfilledAt;
    mapping(bytes32 => bool) private requestListed;
    bytes32[] private requestIds;
    // requestId -> OCR hashLow
    mapping(bytes32 => uint128) public ocrHashByRequestId;
    mapping(bytes32 => bool) public ocrHashExists;
    // requestId -> finalized
    mapping(bytes32 => bool) public finalized;
    // requestId -> finalized raw
    mapping(bytes32 => string) private finalizedRaw;

    mapping(bytes32 => string) public rawResults;
    mapping(bytes32 => bool) private rawResultExists;
    bytes32[] private rawResultHashes;

    event RequestSent(bytes32 indexed requestId, uint256 timestamp);
    event DecisionFulfilled(bytes32 indexed requestId, bytes result);
    event RawResultStored(bytes32 indexed hash, string raw);
    event BaselineCommitted(bytes32 indexed requestId, bytes32 hash, uint128 hashLow, string raw);
    event Finalized(bytes32 indexed requestId, bytes32 hash, uint128 hashLow);
    event OcrAggregatorUpdated(address indexed aggregator);
    event BaselineWriterUpdated(address indexed writer, bool allowed);
    event OcrAnswerSet(bytes32 indexed requestId, uint128 hashLow);
    event RequestPending(bytes32 indexed requestId, address indexed requester, uint256 timestamp);
    event RequestFulfilled(bytes32 indexed requestId, uint256 timestamp);

    constructor(
        address _linkToken,     // LINK 代币地址
        address _oracle,         // 你 Chainlink 节点的 oracle 合约地址
        bytes32 _jobId,          // 你创建的 Job ID
        uint256 _fee             // LINK 支付数量，比如 0.1 * 10**18
    ) ConfirmedOwner(msg.sender) {
        _setChainlinkToken(_linkToken);  // 设置 LINK 代币
        oracle = _oracle;
        jobId = _jobId;
        fee = _fee;
    }

    // 调用这个函数发起 DMN 决策请求
    function requestDMNDecision(
        string calldata url,
        string calldata dmnContent,
        string calldata decisionId,
        string calldata inputData  // 输入数据的 JSON 字符串
    ) external returns (bytes32 requestId) {
        Chainlink.Request memory req = _buildChainlinkRequest(jobId, address(this), this.fulfill.selector);

        // 添加参数:这是传给节点的参数,节点会根据 Job Spec 去处理
        req._add("url", url);
        req._add("dmnContent", dmnContent);
        req._add("decisionId", decisionId);
        req._add("inputData", inputData);

        // 发出请求
        requestId = _sendChainlinkRequestTo(oracle, req, fee);
        requestStates[requestId] = RequestState.Pending;
        requestRequesters[requestId] = msg.sender;
        requestCreatedAt[requestId] = block.timestamp;
        _trackRequestId(requestId);
        emit RequestPending(requestId, msg.sender, block.timestamp);

        emit RequestSent(requestId, block.timestamp);
        return requestId;
    }

    // Chainlink 节点执行完成后回调这个函数
    function fulfill(bytes32 _requestId, bytes memory _data) public recordChainlinkFulfillment(_requestId) {
        dmnResult = _data;
        _markRequestFulfilled(_requestId);
        emit DecisionFulfilled(_requestId, _data);
    }

    // 允许合约 OWNER 提取 LINK
    function withdrawLink() external onlyOwner {
        LinkTokenInterface link = LinkTokenInterface(_chainlinkTokenAddress());
        require(link.transfer(msg.sender, link.balanceOf(address(this))), "Unable to transfer");
    }

    // 更新 Job ID
    function setJobId(bytes32 _jobId) external onlyOwner {
        jobId = _jobId;
    }

    function getJobId() external view returns (bytes32) {
        return jobId;
    }

    // 设置 OCR 聚合合约地址
    function setOcrAggregator(address _aggregator) external onlyOwner {
        ocrAggregator = _aggregator;
        emit OcrAggregatorUpdated(_aggregator);
    }

    // 设置基准结果写入地址
    function setBaselineWriter(address writer, bool allowed) external onlyOwner {
        baselineWriters[writer] = allowed;
        emit BaselineWriterUpdated(writer, allowed);
    }

    function _isAuthorizedBaselineWriter() internal view returns (bool) {
        return msg.sender == owner() || baselineWriters[msg.sender];
    }

    // 写入 raw 结果（要求与 OCR 最新 hash 一致）
    function storeRawResult(bytes32 expectedHash, string calldata raw) external {
        require(_isAuthorizedBaselineWriter(), "Not authorized");
        require(ocrAggregator != address(0), "OCR aggregator not set");
        int256 latest = IOCRAggregator(ocrAggregator).latestAnswer();
        require(latest >= 0, "Negative OCR hash");
        uint256 ocrHash = uint256(uint192(uint256(latest)));
        bytes32 rawHash = keccak256(bytes(raw));
        require(uint256(rawHash) & ((uint256(1) << 128) - 1) == ocrHash, "Hash mismatch");
        require(expectedHash == rawHash, "Expected hash mismatch");
        rawResults[rawHash] = raw;
        if (!rawResultExists[rawHash]) {
            rawResultExists[rawHash] = true;
            rawResultHashes.push(rawHash);
        }
        emit RawResultStored(rawHash, raw);
    }

    // 由合约内部计算 hash 并校验 OCR latestAnswer（供 job 直接传 raw）
    function storeRawResultFromRaw(string calldata raw) external {
        require(_isAuthorizedBaselineWriter(), "Not authorized");
        require(ocrAggregator != address(0), "OCR aggregator not set");
        int256 latest = IOCRAggregator(ocrAggregator).latestAnswer();
        require(latest >= 0, "Negative OCR hash");
        uint256 ocrHash = uint256(uint192(uint256(latest)));
        bytes32 rawHash = keccak256(bytes(raw));
        require(uint256(rawHash) & ((uint256(1) << 128) - 1) == ocrHash, "Hash mismatch");
        rawResults[rawHash] = raw;
        if (!rawResultExists[rawHash]) {
            rawResultExists[rawHash] = true;
            rawResultHashes.push(rawHash);
        }
        emit RawResultStored(rawHash, raw);
    }

    // directrequest Job 写入基准结果（raw + hash）
    function commitBaselineFromRaw(bytes32 requestId, string calldata raw) external {
        require(_isAuthorizedBaselineWriter(), "Not authorized");
        bytes32 rawHash = keccak256(bytes(raw));
        uint128 hashLow = uint128(uint256(rawHash));

        BaselineResult storage existing = baselines[requestId];
        if (existing.exists) {
            require(existing.hash == rawHash, "Baseline hash mismatch");
        } else {
            baselines[requestId] = BaselineResult({
                hash: rawHash,
                hashLow: hashLow,
                raw: raw,
                exists: true
            });
        }

        rawResults[rawHash] = raw;
        if (!rawResultExists[rawHash]) {
            rawResultExists[rawHash] = true;
            rawResultHashes.push(rawHash);
        }

        if (requestStates[requestId] == RequestState.None) {
            requestStates[requestId] = RequestState.Pending;
            requestCreatedAt[requestId] = block.timestamp;
        }
        _trackRequestId(requestId);
        _markRequestFulfilled(requestId);

        emit BaselineCommitted(requestId, rawHash, hashLow, raw);
    }

    // 校验 OCR 最新结果是否匹配基准 hash
    function isOcrMatch(bytes32 requestId) public view returns (bool) {
        BaselineResult storage baseline = baselines[requestId];
        if (!baseline.exists || !ocrHashExists[requestId]) {
            return false;
        }
        return baseline.hashLow == ocrHashByRequestId[requestId];
    }

    // 记录 OCR answer（hashLow）
    function setOcrAnswer(bytes32 requestId, uint128 hashLow) external {
        require(_isAuthorizedBaselineWriter(), "Not authorized");
        ocrHashByRequestId[requestId] = hashLow;
        ocrHashExists[requestId] = true;
        emit OcrAnswerSet(requestId, hashLow);
    }

    // 结果只在 finalize 后才可用
    function finalize(bytes32 requestId) external {
        _finalize(requestId);
    }

    // 在 finalize 前写入 OCR answer（推荐）
    function finalizeWithOcrAnswer(bytes32 requestId, uint128 hashLow) external {
        require(_isAuthorizedBaselineWriter(), "Not authorized");
        ocrHashByRequestId[requestId] = hashLow;
        ocrHashExists[requestId] = true;
        emit OcrAnswerSet(requestId, hashLow);
        _finalize(requestId);
    }

    function _finalize(bytes32 requestId) internal {
        BaselineResult storage baseline = baselines[requestId];
        require(baseline.exists, "Baseline not found");
        require(isOcrMatch(requestId), "OCR mismatch");
        if (!finalized[requestId]) {
            finalized[requestId] = true;
            finalizedRaw[requestId] = baseline.raw;
            emit Finalized(requestId, baseline.hash, baseline.hashLow);
        }
    }

    function getFinalizedRaw(bytes32 requestId) external view returns (string memory) {
        require(finalized[requestId], "Not finalized");
        return finalizedRaw[requestId];
    }

    function getRequestStatus(bytes32 requestId)
        external
        view
        returns (
            RequestState state,
            address requester,
            uint256 createdAt,
            uint256 fulfilledAt,
            bool exists
        )
    {
        state = requestStates[requestId];
        requester = requestRequesters[requestId];
        createdAt = requestCreatedAt[requestId];
        fulfilledAt = requestFulfilledAt[requestId];
        exists = state != RequestState.None;
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

    function getAllRequests()
        external
        view
        returns (
            bytes32[] memory ids,
            uint8[] memory states,
            address[] memory requesters,
            uint256[] memory createdAts,
            uint256[] memory fulfilledAts
        )
    {
        uint256 count = requestIds.length;
        ids = new bytes32[](count);
        states = new uint8[](count);
        requesters = new address[](count);
        createdAts = new uint256[](count);
        fulfilledAts = new uint256[](count);
        for (uint256 i = 0; i < count; i++) {
            bytes32 requestId = requestIds[i];
            ids[i] = requestId;
            states[i] = uint8(requestStates[requestId]);
            requesters[i] = requestRequesters[requestId];
            createdAts[i] = requestCreatedAt[requestId];
            fulfilledAts[i] = requestFulfilledAt[requestId];
        }
        return (ids, states, requesters, createdAts, fulfilledAts);
    }

    // 获取当前存储的结果（以字节数组形式）
    function getDMNResult() external view returns (bytes memory) {
        return dmnResult;
    }

    function _markRequestFulfilled(bytes32 requestId) internal {
        requestStates[requestId] = RequestState.Fulfilled;
        if (requestFulfilledAt[requestId] == 0) {
            requestFulfilledAt[requestId] = block.timestamp;
        }
        emit RequestFulfilled(requestId, requestFulfilledAt[requestId]);
    }

    function _trackRequestId(bytes32 requestId) internal {
        if (!requestListed[requestId]) {
            requestListed[requestId] = true;
            requestIds.push(requestId);
        }
    }
}

interface IOCRAggregator {
    function latestAnswer() external view returns (int256);
}
