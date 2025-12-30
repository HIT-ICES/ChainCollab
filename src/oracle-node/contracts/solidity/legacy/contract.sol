// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IGroth16Verifier {
    function verifyProof(
        uint[2] calldata,
        uint[2][2] calldata,
        uint[2] calldata,
        uint[2] calldata
    ) external view returns (bool);
}

/// @title SimpleThresholdOracle
/// @notice 多链协作的 Oracle 任务管理合约，支持传统“逐个上链”与阈值签名两种提交模式，并可选用 Groth16 ZK 证明直接认证计算结果。
contract SimpleMultiOracle {
    address public owner;
    uint256 public nextTaskId;
    uint256 public minResponses;
    address public zkVerifier;

    struct OracleNode {
        bool active;
    }

    struct Task {
        address requester;
        bytes params;
        bool finished;
        bytes finalResult;
        uint256 deadline;
        bool zkMode;
        uint256 zkPublicInput;
        mapping(address => bool) responded;
        mapping(bytes32 => uint256) resultCount; // resultHash -> count
    }

    mapping(address => OracleNode) public oracleNodes;
    uint256 public oracleCount;

    mapping(uint256 => Task) private tasks;

    event OracleRegistered(address indexed oracle);
    event OracleRemoved(address indexed oracle);
    event TaskRequested(uint256 indexed taskId, address indexed requester, bytes params);
    event ResultSubmitted(uint256 indexed taskId, address indexed oracle, bytes result);
    /// @dev 阈值签名批量提交事件，便于链下监控哪个签名集参与确认
    event ThresholdResultSubmitted(uint256 indexed taskId, bytes result, address[] signers);
    event TaskFinalized(uint256 indexed taskId, bytes result);
    event ZKVerifierUpdated(address indexed verifier);
    event ZKTaskRegistered(uint256 indexed taskId, uint256 publicInput);
    event ZKResultSubmitted(uint256 indexed taskId, uint256 outputSignal, uint256 publicInput);

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    modifier onlyOracle() {
        require(oracleNodes[msg.sender].active, "not oracle");
        _;
    }

    constructor(uint256 _minResponses) {
        require(_minResponses > 0, "minResponses must be > 0");
        owner = msg.sender;
        minResponses = _minResponses;
    }

    // === 管理 Oracle 节点 ===

    function registerOracle(address _oracle) external onlyOwner {
        require(_oracle != address(0), "zero addr");
        require(!oracleNodes[_oracle].active, "already active");
        oracleNodes[_oracle] = OracleNode({active: true});
        oracleCount += 1;
        emit OracleRegistered(_oracle);
    }

    function removeOracle(address _oracle) external onlyOwner {
        require(oracleNodes[_oracle].active, "not active");
        oracleNodes[_oracle].active = false;
        oracleCount -= 1;
        emit OracleRemoved(_oracle);
    }

    function setMinResponses(uint256 _minResponses) external onlyOwner {
        require(_minResponses > 0, "minResponses must be > 0");
        minResponses = _minResponses;
    }

    function setZKVerifier(address verifier) external onlyOwner {
        require(verifier != address(0), "invalid verifier");
        zkVerifier = verifier;
        emit ZKVerifierUpdated(verifier);
    }

    // === 用户发起任务 ===

    function requestTask(bytes calldata params, uint256 deadline) external returns (uint256) {
        uint256 taskId = nextTaskId;
        nextTaskId++;

        Task storage t = tasks[taskId];
        t.requester = msg.sender;
        t.params = params;
        t.finished = false;
        t.deadline = deadline;
        t.zkMode = false;
        t.zkPublicInput = 0;

        emit TaskRequested(taskId, msg.sender, params);
        return taskId;
    }

    /// @notice 注册需要 ZK 证明的任务，publicInput 可表示链下电路的公开输入（例如业务参数承诺值）
    function requestZKTask(bytes calldata params, uint256 deadline, uint256 publicInput) external returns (uint256) {
        uint256 taskId = nextTaskId;
        nextTaskId++;

        Task storage t = tasks[taskId];
        t.requester = msg.sender;
        t.params = params;
        t.finished = false;
        t.deadline = deadline;
        t.zkMode = true;
        t.zkPublicInput = publicInput;

        emit TaskRequested(taskId, msg.sender, params);
        emit ZKTaskRegistered(taskId, publicInput);
        return taskId;
    }

    // === Oracle 提交结果 ===

    function submitResult(uint256 taskId, bytes calldata result) external onlyOracle {
        Task storage t = tasks[taskId];
        require(!t.zkMode, "use ZK submit");
        require(!t.finished, "task finished");
        if (t.deadline != 0) {
            require(block.number <= t.deadline, "deadline passed");
        }
        require(!t.responded[msg.sender], "already responded");

        t.responded[msg.sender] = true;

        bytes32 h = keccak256(result);
        t.resultCount[h] += 1;

        emit ResultSubmitted(taskId, msg.sender, result);

        // 多数决判断：达到 minResponses 就定案
        if (t.resultCount[h] >= minResponses) {
            t.finished = true;
            t.finalResult = result;
            emit TaskFinalized(taskId, result);
        }
    }

    /// @notice 阈值签名模式一次性提交多个 Oracle 的确认
    /// @dev 使用标准 ECDSA 验签，可配合 MuSig/FROST 等协议在链下聚合参与者列表
    function submitThresholdResult(
        uint256 taskId,
        bytes calldata result,
        bytes[] calldata signatures,
        address[] calldata signers
    ) external {
        Task storage t = tasks[taskId];
        require(!t.zkMode, "use ZK submit");
        require(signers.length == signatures.length, "len mismatch");
        require(signers.length >= minResponses, "not enough signatures");

        require(!t.finished, "task finished");
        if (t.deadline != 0) {
            require(block.number <= t.deadline, "deadline passed");
        }

        bytes32 digest = keccak256(abi.encodePacked(taskId, result));

        for (uint256 i = 0; i < signers.length; i++) {
            address signer = signers[i];
            require(oracleNodes[signer].active, "invalid signer");
            require(!t.responded[signer], "signer used");

            address recovered = _recoverSigner(digest, signatures[i]);
            require(recovered == signer, "bad signature");

            t.responded[signer] = true;
        }

        t.finished = true;
        t.finalResult = result;

        emit ThresholdResultSubmitted(taskId, result, signers);
        emit TaskFinalized(taskId, result);
    }

    /// @notice 提交带 Groth16 证明的任务结果，result 需为 32 字节 ABI 编码的 uint256（与电路 publicSignals[0] 对齐）
    function submitZKResult(
        uint256 taskId,
        bytes calldata result,
        uint[2] calldata proofA,
        uint[2][2] calldata proofB,
        uint[2] calldata proofC,
        uint[2] calldata publicSignals
    ) external onlyOracle {
        Task storage t = tasks[taskId];
        require(t.zkMode, "task not zk");
        require(zkVerifier != address(0), "verifier not set");
        require(!t.finished, "task finished");
        if (t.deadline != 0) {
            require(block.number <= t.deadline, "deadline passed");
        }
        require(result.length == 32, "result must be 32 bytes");

        uint256 outputSignal = abi.decode(result, (uint256));
        require(outputSignal == publicSignals[0], "result/public mismatch");
        require(publicSignals[1] == t.zkPublicInput, "public input mismatch");

        bool ok = IGroth16Verifier(zkVerifier).verifyProof(proofA, proofB, proofC, publicSignals);
        require(ok, "zk verify failed");

        t.finished = true;
        t.finalResult = result;

        emit ZKResultSubmitted(taskId, outputSignal, publicSignals[1]);
        emit TaskFinalized(taskId, result);
    }

    /// @dev ECDSA 验签（传入 digest = keccak256 编码，函数内补齐以太坊签名前缀）
    function _recoverSigner(bytes32 digest, bytes memory signature) internal pure returns (address) {
        require(signature.length == 65, "bad sig length");
        bytes32 r;
        bytes32 s;
        uint8 v;

        assembly {
            r := mload(add(signature, 32))
            s := mload(add(signature, 64))
            v := byte(0, mload(add(signature, 96)))
        }

        if (v < 27) v += 27;
        require(v == 27 || v == 28, "bad v");

        bytes32 ethHash = keccak256(
            abi.encodePacked("\x19Ethereum Signed Message:\n32", digest)
        );
        return ecrecover(ethHash, v, r, s);
    }

    // === 查询接口 ===

    function getTask(
        uint256 taskId
    )
        external
        view
        returns (
            address requester,
            bytes memory params,
            bool finished,
            bytes memory finalResult,
            uint256 deadline
        )
    {
        Task storage t = tasks[taskId];
        return (t.requester, t.params, t.finished, t.finalResult, t.deadline);
    }

    function getTaskZKMeta(uint256 taskId) external view returns (bool zkMode, uint256 publicInput) {
        Task storage t = tasks[taskId];
        return (t.zkMode, t.zkPublicInput);
    }
}
