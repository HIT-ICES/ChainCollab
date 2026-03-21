# DMN + Geth + Chainlink OCR 设计文档

## 1. 设计目标

本文档面向论文写作，概括 `features/04-dmn-ocr/README.md` 中实现的核心设计。该方案的目标不是将 DMN 决策逻辑完全搬到链上执行，而是在以太坊兼容网络上构建一种“链上请求、链下计算、多节点聚合、链上校验、结果定稿”的混合执行机制。其核心诉求包括：

- 利用 Geth 搭建可控的以太坊私有网络，作为智能合约和 OCR 聚合结果的可信承载环境。
- 利用 Chainlink 多节点网络完成 DMN 链下计算结果的采集与聚合，避免单节点预言机成为新的信任中心。
- 利用 DMN 服务承载复杂业务规则执行，避免在 Solidity 中直接实现复杂决策逻辑带来的高成本和低可维护性问题。
- 通过“原始结果不上 OCR、只上传结果哈希”的方式，在保持链上可验证性的同时降低链上存储和传输压力。

## 2. 总体思路

该方案采用“双通道协同”的设计。

- 第一条通道是 `directrequest` 基准写入通道。链上合约发起 `requestDMNDecision()` 后，Chainlink 节点监听 `OracleRequest` 事件，调用本地 DMN 服务 `/api/dmn/calc` 执行决策，并将返回的 `raw` 结果通过 `commitBaselineFromRaw(requestId, raw)` 写回合约，形成链上基准结果。
- 第二条通道是 OCR 聚合通道。各 Chainlink 节点从本地缓存接口 `/api/dmn/latest?requireReady=1` 读取最新结果对应的 `hashDec`，并将该数值作为 observation 参与 OCR 共识。OCR 聚合后的结果由 `OffchainAggregator` 写回链上。

双通道的意义在于：

- `directrequest` 通道提供基准原文 `raw` 及其哈希；
- OCR 通道提供多节点一致认可的哈希值；
- 合约通过 `isOcrMatch(requestId)` 比较二者是否一致；
- 一致后再执行 `finalize`，将最终可用结果固化为 `getFinalizedRaw(requestId)` 可查询的状态。

因此，该方案将“复杂决策执行”和“结果可信确认”拆成了两个阶段，分别解决链下灵活计算和链上可信验证的问题。

## 3. 系统组件

### 3.1 区块链网络层

- `Geth` 私有链：提供 EVM 执行环境，部署 LINK 代币、Operator、OCR Aggregator 和 DMN 请求合约。
- `MyChainlinkRequesterDMN.sol`：作为业务入口合约，负责发起 DMN 请求、保存基准结果、校验 OCR 结果并输出最终结果。

### 3.2 预言机网络层

- Bootstrap 节点：负责 OCR 网络引导、OCR writer job 触发等控制逻辑。
- 多个 Chainlink 从节点：负责监听请求、访问本地 DMN 服务、参与 OCR observation 和 report 提交。
- `job-spec-dmn-event.toml`：定义 directrequest job，监听 `OracleRequest` 并回写基准 `raw`。
- `job-spec-ocr-dmn.toml`：定义 OCR job，从本地缓存中读取 `hashDec` 并参与聚合。
- `job-spec-ocr-writer.toml`：定义 finalize webhook job，在 OCR 聚合完成后触发业务合约定稿。

### 3.3 DMN 计算与缓存层

- CDMN 服务：负责执行 DMN 决策逻辑。
- `/api/dmn/calc`：接收 `dmnContent`、`decisionId`、`inputData` 和 `requestId`，执行决策并缓存结果。
- `/api/dmn/latest`：返回最近一次缓存结果，用于 OCR 节点读取 observation。
- `/api/dmn/by-hash`：按 hash 查询原始 `raw`，支持 finalize 或比对逻辑。
- `/api/dmn/ack`：在 OCR 写回链上后清理缓存，避免旧结果污染后续轮次。

### 3.4 监听与收敛层

- `ocr-ack-listener.js`：监听 OCR Aggregator 的 `NewTransmission` 事件，触发 finalize webhook。
- DMN 服务内置 OCR 监听器：收到写回事件后，结合区块时间戳 ACK 清缓存，避免将更晚产生的新缓存误删。

## 4. 核心数据对象与合约状态

### 4.1 请求输入

业务合约通过 `requestDMNDecision()` 提交以下信息：

- `dmnContent`：DMN XML 内容或其链下引用。
- `decisionId`：目标决策节点标识。
- `inputData`：JSON 格式的输入参数。

### 4.2 链下结果对象

DMN 服务计算后得到：

- `raw`：DMN 决策原始结果字符串。
- `hash`：对 `raw` 执行 `keccak256(raw)` 后得到的哈希。
- `hashDec`：`hash` 的低 128 位十进制表示，作为 OCR observation 上传链上。

这里使用 `hashDec` 而不是直接上传 `raw`，原因有三点：

- OCR observation 更适合数值型聚合；
- 避免在 OCR 报文中携带较大文本；
- 便于在链上使用统一数值字段进行比较。

### 4.3 链上状态

`MyChainlinkRequesterDMN.sol` 中的关键状态包括：

- `rawResults[rawHash]`：保存原始结果文本。
- 按 `requestId` 保存的 baseline hash / raw hash：用于与 OCR 结果比对。
- finalized 结果状态：用于对外输出最终确认后的结果。

关键方法包括：

- `requestDMNDecision()`：发起请求。
- `commitBaselineFromRaw(requestId, raw)`：写入基准结果。
- `isOcrMatch(requestId)`：校验 OCR 聚合结果与基准 hash 是否一致。
- `finalize(requestId)` / `finalizeWithOcrAnswer(requestId, hashLow)`：结果定稿。
- `getFinalizedRaw(requestId)`：读取最终结果。

## 5. 执行流程

完整执行流程如下。

1. 业务侧调用 `requestDMNDecision()`，合约发出 `OracleRequest`。
2. directrequest job 监听事件，解析请求参数并调用 `/api/dmn/calc`。
3. DMN 服务执行链下决策，返回并缓存 `raw`、`hash`、`hashDec`。
4. directrequest job 调用 `commitBaselineFromRaw(requestId, raw)`，将基准原始结果写入合约。
5. 各 OCR 节点从 `/api/dmn/latest?requireReady=1` 读取 `hashDec` 作为 observation。
6. OCR 网络聚合 observation，并由 OCR Aggregator 将结果写回 Geth 链上。
7. 业务合约通过 `isOcrMatch(requestId)` 校验 OCR 结果与基准 hash 是否一致。
8. 监听器在 `NewTransmission` 后触发 `finalizeWithOcrAnswer()` 或 `finalize()`。
9. 合约完成结果定稿，业务侧通过 `getFinalizedRaw(requestId)` 获取最终 DMN 结果。
10. DMN 服务收到 ACK 后清理对应缓存，为下一轮请求做准备。

## 6. 可信性与一致性设计

### 6.1 链下计算、链上确认

DMN 规则计算具有明显的链下执行特征：规则表达复杂、输入可能来自企业内部系统、决策原文长度不确定。若直接将 DMN 引擎嵌入链上，将面临 Gas 开销高、可升级性差和实现复杂等问题。因此本方案将 DMN 保留在链下执行，而将“请求记录、结果哈希、聚合结果、最终确认”保留在链上。

### 6.2 基准写入与 OCR 聚合分离

方案没有直接依赖 OCR 返回原始结果文本，而是先由 directrequest job 把 `raw` 写成 baseline，再由 OCR 只对 `hashDec` 做聚合。这样设计的好处是：

- 原始结果可追溯，便于审计和论文实验复现；
- OCR 只处理固定长度数值，降低聚合复杂度；
- 合约端只需比较 baseline hash 和 OCR hash 是否一致，无需在链上重算复杂决策。

### 6.3 低 128 位哈希映射

当前实现中，OCR 上报值为 `keccak256(raw)` 的低 128 位。该做法兼顾了 EVM 上数值处理便利性和 OCR observation 的格式要求，但也带来一个论文中应明确说明的设计假设：合约校验逻辑、服务端哈希生成逻辑和 OCR 上报逻辑必须严格保持一致，否则会导致误判。

### 6.4 缓存 ACK 机制

OCR 写回后如果不及时清理缓存，后续请求可能读到旧结果。为此，该方案设计了两层防护：

- 以 `requestId` 为主键定向清理与本轮请求相关的缓存；
- 以区块时间戳作为辅助条件，仅当缓存写入时间不晚于链上写回时间时才清除最新缓存。

这保证了并发或连续请求场景下不会误删更晚产生的新结果。

## 7. 部署与实现映射

从工程角度，该方案由以下步骤组成：

1. 启动 Geth 私链并完成基础合约部署。
2. 启动多节点 Chainlink OCR 网络。
3. 启动 CDMN 服务容器，暴露缓存与查询接口。
4. 部署 DMN 请求合约并配置 OCR aggregator、writer 地址和 Job ID。
5. 创建 directrequest job 与 OCR job。
6. 为请求合约充值 LINK。
7. 发起 `requestDMNDecision()` 并完成链下计算、OCR 聚合与结果定稿。

README 中的 `run-setup.sh` 已经把 OCR 网络、DMN 服务、合约部署、job 创建和配置串联起来，适合实验复现。

## 8. 相对已有 BlockCollab 工作的扩展意义

相对现有基于 Hyperledger Fabric 的 BlockCollab 方案，本设计的增量价值主要体现在以下几个方面：

- 执行底座从联盟链扩展到以太坊兼容网络，验证了多方协作决策执行方法在 permissionless 风格架构上的可迁移性。
- 决策执行方式从“平台内 BRT 驱动的外部执行”进一步细化为“Chainlink OCR 驱动的链下计算结果聚合与校验”，增强了预言机层设计。
- 通过 Geth + Chainlink + DMN 的组合，形成了面向异构区块链环境的另一条实现路线，为论文中“兼容异构区块链与可信预言机”的研究主线提供了更强的工程支撑。

## 9. 论文写作建议

论文中建议将该工作定位为“面向以太坊兼容环境的 DMN 链下计算与可信预言机扩展方案”，并突出以下几点：

- 这是对已有 BlockCollab/IBC 权限链执行框架的补充，而不是替代。
- 该方案重点解决的是“复杂决策规则如何在保持链上确定性的前提下被可信引入”。
- 方法贡献不在于重新实现 DMN 引擎，而在于提出了一种基于 Chainlink OCR 的多节点结果聚合与链上定稿机制。
- 工程贡献在于打通了 Geth、Chainlink、DMN 服务和业务合约之间的完整执行链路。

如果写成论文章节，可按照“问题动机 -> 架构设计 -> 执行流程 -> 一致性机制 -> 与既有工作的关系 -> 小结”展开。
