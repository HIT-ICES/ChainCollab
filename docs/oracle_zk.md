# Oracle 阈值签名 + 零知识证明方案概览

## 1. 背景

- 目标：构建一个链下 Oracle 网络，既能通过阈值签名保证“谁”认可结果，也能通过零知识证明（ZK）保证“结果确实来自指定计算”。
- 当前仓库中的 `src/oracle-node` 与 `contracts/solidity/legacy/contract.sol` 完成了该能力：节点可以选择传统模式（单签 or 阈值签名）或 ZK 模式（Groth16 证明）。
- 设计灵感来自链上多方喂价（Chainlink 等）与跨链 Relayer 的双层可信模型：门限签名解决参与者共识，ZK 证明保证链下计算的正确性。

## 2. 合约层设计

### 2.1 传统模式（多签/阈值签名）

1. 用户调用 `requestTask`，链上记录 `params` 和 `deadline`。
2. 合约维护 `oracleNodes` 集合与 `minResponses`。
3. 任何已注册节点均可 `submitResult`；合约通过 `resultHash -> count` 多数决，一旦 `count >= minResponses` 即确认。
4. 为提升效率，可用 `submitThresholdResult`：链下通过 FROST/MuSig 聚合多个签名，链上循环 `ecrecover` 验证（只要 ≥ `minResponses` 个签名即成功）。

### 2.2 ZK 模式

1. 调用 `setZKVerifier` 指定 Groth16 验证合约（由 `snarkjs zkey export solidityverifier` 生成）。
2. 通过 `requestZKTask(params, deadline, publicInput)` 录入任务，`publicInput` 表示电路的公开输入（例如业务参数承诺值）。
3. Oracle 节点链下执行 Circom 电路 + `snarkjs` 生成 `proof.json`、`publicSignals.json`。
4. 任何 oracle 节点提交 `submitZKResult(taskId, resultBytes, proofA, proofB, proofC, publicSignals)`：
   - `resultBytes` 是 `publicSignals[0]` 的 `bytes32` 编码（链上直接存储最终结果）。
   - `publicSignals[1]` 必须等于合约记录的 `zkPublicInput`，防止替换攻击。
   - 合约内调用 `IGroth16Verifier.verifyProof`，验证成功后写入 `TaskFinalized`，并触发事件 `ZKResultSubmitted`。

### 2.3 兼容性

- 传统模式与 ZK 模式可共存：同一合约中不同任务可选择不同的提交方式。
- `getTaskZKMeta` 可查询 `zkMode` 与 `publicInput`，方便链下调度器区分任务类型。

## 3. 链下节点 / 控制平面

1. `src/oracle-node/oracle_node/main.py` 同时支持 EVM/Fabric 适配器，读取 `config.yml` 后轮询任务。
2. 新增 FastAPI 控制平面（`oracle_node/backend/app.py`）：用于注册数据源、合约信息、事件监听等，并提供 Dashboard（`dashboard/index.html`）。
3. 事件监听由 `EventManager` 驱动，可订阅 EVM 合约事件（如 `TaskRequested`、`TaskFinalized`），触发回调或写入本地日志。
4. 阈值签名实验脚本 `scripts/threshold_experiment.py` 与 ZK 提交脚本 `scripts/zk_submit_example.py` 分别演示两种提交流程。

## 4. 实验思路

1. **阈值签名实验**：部署 `SimpleMultiOracle`，设置 `minResponses=2`，用 3 个本地账户模拟 `submitThresholdResult`。脚本会输出每个签名并可直接上链。
2. **ZK 计算实验**：
   - 使用 Circom 的 `Multiplier(1000)` 电路（参考 `scripts/zk_sample` 中生成的 `proof.json` 与 `public.json`）。
   - 部署 `SimpleZKVerifier.sol`，将地址配置到 `setZKVerifier`。
   - 调用 `requestZKTask(..., publicInput=11)`，再运行 `zk_submit_example.py` 上传示例证明。
   - 观察 `ZKResultSubmitted` 事件与 `TaskFinalized` 状态。
3. **性能/安全对比**：记录传统模式 (Ecrecover+多数决) 与 ZK 模式 (Groth16 pairing) 的 gas 开销、延迟，并分析“签名伪造”和“计算欺骗”两类攻击的抵抗能力。

## 5. 参考文献

1. Boneh, Dan, and Matthew Franklin. “Identity-Based Encryption from the Weil Pairing.” *SIAM Journal on Computing*, 32(3), 2003.（BLS 多签理论基础）  
2. Komlo, Chelsea, and Ian Goldberg. “FROST: Flexible Round-Optimized Schnorr Threshold Signatures.” *USENIX Security 2022*.  
3. Nick, Jonas, Tim Ruffing, and Yannick Seurin. “MuSig2: Simple Two-Round Schnorr Multi-Signatures.” *IEEE S&P 2021*.  
4. Boneh, Dan, Manu Drijvers, and Gregory Neven. “Compact Multi-Signatures for Smaller Blockchains.” *ASIACRYPT 2018*.  
5. Lynn, Ben, and Konstantinos Chalkias. “On Byzantine-Tolerant Threshold Signatures.” *IACR ePrint 2022/178*.  
6. Liao, Di, and Shayan Eskandari. “On the Reliability of Oracle Networks for DeFi.” *arXiv:2305.01843*, 2023.  
7. Ojha, Dev, and Kevin Sekniqi. “BandChain: Decentralized Data Delivery Network.” Whitepaper, 2020.  
8. Nazarov, Sergey et al. “Chainlink 2.0: Next Steps in the Evolution of Decentralized Oracle Networks.” Whitepaper, 2021.  
9. Kilian, Joe et al. “Aggregatable Distributed Key Generation.” *CRYPTO 2022*.  
10. Groth, Jens. “A verifiable secret shared and distributed zero-knowledge proof.” *CRYPTO 2016*.（Groth16 协议）  

> 如需复现 `snarkjs` 生成器，可参考官方文档：<https://github.com/iden3/snarkjs>
