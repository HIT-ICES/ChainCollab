# Oracle 可靠性实验设计（多数签名 + ZK）

本实验目标：验证当前 Oracle 合约/链码的可靠性与安全性，确保「仅达到多数（阈值）签名后才可定案」以及「ZK 证明路径必须验证通过才能定案」。

## 目录
- 实验环境
- 实验 1：多数签名门限控制（Solidity & Fabric）
- 实验 2：ZK 证明强制校验（Solidity）
- 实验 3：恶意/重复签名与重放防御
- 实验 4：性能与可用性（延迟/吞吐/gas）
- 可选拓展实验

## 实验环境
- Solidity 合约：`src/oracle-node/contracts/solidity/legacy/contract.sol` 部署到本地 EVM (Hardhat/Anvil)。
- Groth16 Verifier：`src/oracle-node/contracts/solidity/legacy/SimpleZKVerifier.sol` 部署并通过 `setZKVerifier` 绑定。
- Fabric 链码：`src/oracle-node/contracts/fabric/contract.go` 部署到测试网络。
- Oracle 节点：`src/oracle-node/oracle_node/main.py`（EVM），Fabric 端可用伪客户端或适配器实现。
- 工具脚本：
  - 阈值签名：`src/oracle-node/scripts/threshold_experiment.py`
  - ZK 提交：`src/oracle-node/scripts/zk_submit_example.py`（使用 `scripts/zk_sample/proof.json/public.json`）

## 实验 1：多数签名门限控制
**目的**：验证只有达到 `minResponses` 的有效签名才会定案，少于门限或无效签名不会改变状态。

步骤（Solidity/EVM）：
1. 部署合约，设置 `minResponses = 2`，注册 3 个 oracle 地址。
2. `requestTask(params, deadline)` 创建任务。
3. 仅 1 个节点调用 `submitResult` → 期望：`Task.finished == false`。
4. 第 2 个节点提交相同结果 → 期望：`Task.finished == true`，`finalResult` 已写入。
5. 使用 `submitThresholdResult`：同时提交 2 份有效签名 → 期望一次性定案；若仅 1 份签名 → 期望 revert。

步骤（Fabric）：
1. 部署链码，设置 `MinResponses = 2`，注册 3 个 oracle 公钥。
2. 调用 `CreateTask` 创建任务。
3. 使用 `SubmitResult`：先 1 份，再 2 份 → 观察 `Finished` 标志与 `FinalResult`。
4. 使用 `SubmitThresholdResult` 提交签名 JSON：1 份 vs 2 份 → 验证只有达门限才 `Finished=true`。

指标记录：
- 状态转移：`finished`/`FinalResult` 变化。
- 错误路径：签名不足/无效签名时的 revert/错误信息。

## 实验 2：ZK 证明强制校验
**目的**：验证 ZK 模式下，没有有效 Groth16 证明无法定案；公开输入需匹配任务登记的 `zkPublicInput`。

步骤（Solidity）：
1. `requestZKTask(params, deadline, publicInput=11)` 创建 ZK 任务。
2. 使用示例证明（publicSignals[0]=输出，publicSignals[1]=11）通过 `zk_submit_example.py` → 期望任务定案。
3. 改写 `public.json` 的第二个元素为错误值再提交 → 期望 revert（public input mismatch）。
4. 修改 `resultBytes32` 与 `publicSignals[0]` 不一致 → 期望 revert（result/public mismatch）。
5. 随机篡改 proof → 期望 `verifyProof` 失败，状态不变。

指标记录：
- 成功/失败交易的状态与事件：`ZKResultSubmitted`、`TaskFinalized`。
- 失败原因日志：合约 revert 消息。

## 实验 3：恶意/重复签名与重放防御
**目的**：验证重复提交、无权限节点或已响应节点的签名不会被接受，防止重放。

步骤（Solidity/Fabric）：
1. 同一 oracle 地址对同一任务多次提交 → 期望第二次被拒绝。
2. 未注册的地址提交签名 → 期望 revert/错误。
3. 使用过期 `deadline` 后提交 → 期望被拒绝。
4. 在 `submitThresholdResult` 中混入重复 signer → 期望被拒绝。

指标记录：
- 交易失败原因（revert/错误）。
- `responded`/`Responses` 去重行为。

## 实验 4：性能与可用性
**目的**：评估阈值签名 vs ZK 验证的开销和延迟。

步骤（Solidity）：
1. 阈值签名路径：记录单次 `submitThresholdResult` 的 gas 消耗。
2. ZK 路径：记录 `submitZKResult` 的 gas 消耗，比较差异。
3. 并发提交：模拟多任务批量创建与提交，统计链上确认延迟与失败率。

步骤（Fabric）：
1. 统计 `SubmitThresholdResult` 在不同签名数量下的执行时间。
2. 观察在高并发/丢包（可用网络工具模拟）情况下的任务完成率。

## 可选拓展实验
- **恶意比例容忍度**：随机让 f 个 oracle 返回错误结果，测量最终正确率；验证门限 f < minResponses 的安全性。
- **数据篡改攻击**：在链下修改 params/结果后重新签名，验证合约能否察觉（应该被 resultHash/zkPublicInput 防护）。
- **跨链/跨流程集成**：结合 BPMN 流程，引入事件监听，观察任务完成后是否能驱动下一步业务动作。
- **Verifer 升级/失效**：切换新的 ZK Verifier 地址后再次提交，确保旧的 verifier 无效，新的 verifier 生效。

## 输出与验收
- 每个实验的执行脚本、交易哈希、链上状态截图或日志。
- Gas/耗时的对比表格。
- 结论：满足“仅多数签名或有效 ZK 证明才能定案”；异常输入/攻击向量未能破坏流程。
