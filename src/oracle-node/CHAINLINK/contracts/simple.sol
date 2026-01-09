// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@chainlink/contracts/src/v0.8/operatorforwarder/ChainlinkClient.sol";
import "@chainlink/contracts/src/v0.8/shared/access/ConfirmedOwner.sol";

contract MyChainlinkRequester is ChainlinkClient, ConfirmedOwner {

    using Chainlink for Chainlink.Request;

    // 返回值存储
    uint256 public result;

    // oracle 节点地址
    address private oracle;
    // job ID: 你的节点 Job 的 ID，按 bytes32 传入
    bytes32 private jobId;
    // 支付给 Chainlink 节点的 LINK 金额（根据你的 Job 配置而定）
    uint256 private fee;

    event RequestSent(bytes32 indexed requestId, uint256 timestamp);

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

    // 调用这个函数发起请求
    function requestOffchainData(string calldata url) external onlyOwner returns (bytes32 requestId) {
        Chainlink.Request memory req = _buildChainlinkRequest(jobId, address(this), this.fulfill.selector);

        // 添加参数:这是传给节点的参数,节点会根据 Job Spec 去处理
        req._add("get", url);
        req._add("path", "value"); // 假设返回 JSON 中有 key 为 value

        // 发出请求
        requestId = _sendChainlinkRequestTo(oracle, req, fee);

        emit RequestSent(requestId, block.timestamp);
        return requestId;
    }

    // Chainlink 节点执行完成后回调这个函数
    function fulfill(bytes32 _requestId, uint256 _data) public recordChainlinkFulfillment(_requestId) {
        result = _data;
    }

    // 允许合约 OWNER 提取 LINK
    function withdrawLink() external onlyOwner {
        LinkTokenInterface link = LinkTokenInterface(_chainlinkTokenAddress());
        require(link.transfer(msg.sender, link.balanceOf(address(this))), "Unable to transfer");
    }
}
