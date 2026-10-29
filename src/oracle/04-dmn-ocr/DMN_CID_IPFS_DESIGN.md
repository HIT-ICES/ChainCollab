# DMN CID/IPFS + DMN_lite 设计方案

## 目标

当前 `04-dmn-ocr` 链路默认把 `dmnContent` 直接作为请求参数传给 `DMN_lite` / Chainlink / CDMN。
这有几个直接问题：

- DMN XML 体积大，链上 calldata、事件、日志和任务负载都偏重
- BPMN/EVM 工作流合约如果持久化 DMN 原文，会显著抬高 `createInstance()` 的 gas 和合约复杂度
- 同一份 DMN 内容会在绑定、实例化、请求执行阶段重复传输
- 未来如果要做版本控制、缓存、审计和重放，直接传 XML 不利于治理

目标方案是：

- DMN 内容在绑定阶段上传到 FireFly Data / IPFS
- 合约和 Job 链路只传 `cid`、`hash`、`decisionId`
- `Activity_*` 直接调用现有/演进后的 `DMN_lite` 请求接口
- 链下服务根据 `cid` 从 FireFly/IPFS 取回 DMN 内容，再交给 CDMN 计算
- `Continue()` 仍然从 `DMN_lite` 读取结果继续推进 BPMN 流程

这套方案应作为后续实现的统一方向。

## 总体架构

### 核心思想

1. DMN 内容不再作为工作流实例的大字段存入链上
2. 链上只持有以下最小引用信息：
   - `dmnCid`
   - `dmnHash`
   - `decisionId`
3. Chainlink / CDMN 在链下根据 `cid` 解析真实 DMN XML
4. 工作流合约内部只负责：
   - 保存业务规则绑定信息
   - 发起 DMN 请求
   - 保存 `requestId`
   - 轮询/查询结果并继续执行

### 参与组件

- BPMN / DMN 绑定前后端
- FireFly Data / IPFS
- EVM 工作流合约（newTranslator 生成）
- `DMN_lite` 请求合约
- Chainlink Job
- CDMN Python 服务

## 目标调用链

### 阶段 1：DMN 绑定

1. 用户在前后端绑定 DMN 内容和决策信息
2. 后端把 DMN XML 上传到 FireFly Data
3. FireFly 底层将内容持久化到 IPFS
4. 后端获得：
   - `cid`
   - `hash`
   - `decisionId`
   - 可选 `dataId` / `blobId`
5. 绑定结果保存在业务侧元数据中

输出结果应是：

```json
{
  "dmnCid": "<cid>",
  "dmnHash": "0x...",
  "decisionId": "Priority Decision",
  "name": "SupplyChainPaper7777",
  "version": "v1"
}
```

### 阶段 2：流程实例创建

`createInstance()` 不再接收完整 `dmnContent`。

BusinessRule 初始化参数改为：

```json
{
  "dmnCid": "<cid>",
  "dmnHash": "0x...",
  "decisionId": "<decisionId>",
  "callerRestricted": false,
  "allowedCaller": "0x0000000000000000000000000000000000000000"
}
```

链上实例中只持久化：

- `cid`
- `hashOfDmn`
- `decisionId`
- `requestId`
- `state`

不持久化：

- 完整 DMN XML

### 阶段 3：BusinessRule 发起请求

目标行为：

1. `Activity_*` 从实例状态里取出：
   - `dmnCid`
   - `decisionId`
   - 业务输入参数
2. `Activity_*` 直接调用 `DMN_lite.requestDMNDecision(...)`
3. 同步拿到 `requestId`
4. 合约将 `requestId` 存回 `BusinessRule`
5. 状态改为 `WAITING_FOR_CONFIRMATION`

这里的关键是：`Activity_*` 不再只是发事件等链下再回写 `requestId`，而是直接拿到 requestId。

### 阶段 4：Chainlink / CDMN 执行

`DMN_lite` 请求事件中不再携带完整 XML，而是携带：

- `dmnCid`
- `decisionId`
- `inputData`

Chainlink Job 调用 CDMN 时，请求体应改为类似：

```json
{
  "requestId": "<requestId>",
  "dmnCid": "<cid>",
  "decisionId": "<decisionId>",
  "inputData": { ... }
}
```

CDMN 服务新增能力：

1. 根据 `dmnCid` 调 FireFly / IPFS 取原始 DMN XML
2. 校验 `hash`
3. 调用 CDMN 引擎执行
4. 返回原有 raw/hash 结果

### 阶段 5：流程继续执行

`Activity_*_Continue()` 继续维持以下行为：

1. 调 `DMN_lite.getRequestStatus(requestId)`
2. 调 `DMN_lite.getRawByRequestId(requestId)`
3. 解析业务结果
4. 写回 `stateMemory`
5. 激活后续 Gateway / Message / Event

## 与当前实现的差异

### 当前主要问题

当前实现中常见的重负载点：

- `dmnContent` 作为大字符串进入请求
- BPMN Solidity 合约在实例创建时可能带过大初始化数据
- Chainlink Job 和 CDMN 接口都默认收 `dmnContent`
- BusinessRule 设计容易在链上和链下重复传 DMN XML

### 目标差异

目标实现中：

- 绑定阶段上传一次 DMN XML
- 执行阶段只传 `cid`
- 合约不持久化原文
- CDMN 负责链下取回内容

## 数据模型建议

### 业务侧 DMN 绑定对象

建议为每个绑定的 DMN 保存：

```json
{
  "cid": "<cid>",
  "hash": "0x...",
  "decisionId": "<decisionId>",
  "name": "<dmnName>",
  "version": "<version>",
  "fireflyDataId": "<optional>",
  "blobId": "<optional>"
}
```

### Solidity 侧 BusinessRule

建议结构：

```solidity
struct BusinessRule {
    bool exists;
    string dmnCid;
    bytes32 hashOfDmn;
    string decisionId;
    bool callerRestricted;
    address allowedCaller;
    ElementState state;
    bytes32 requestId;
    uint256 requestedAt;
    uint256 fulfilledAt;
    string lastRawResult;
}
```

如果考虑进一步缩小链上存储，可把 `string dmnCid` 替换为固定长度编码或外部 registry key。

## 对现有模块的改造方向

### 1. BPMN / DMN 绑定前后端

需要新增：

- DMN 上传到 FireFly Data 的能力
- 保存 `cid/hash/decisionId`
- createInstance 参数组装时不再传完整 `dmnContent`

### 2. newTranslator / Solidity 模板

需要改造：

- `BusinessRuleInit`：`dmnContent -> dmnCid + dmnHash`
- `BusinessRule` 持久化字段调整
- `Activity_*` 直接调用 `DMN_lite.requestDMNDecision(...)`
- `Continue()` 保持读取结果并推进状态

### 3. DMN_lite 请求接口

存在两种选择：

#### 方案 A：显式升级接口

将接口改为：

```solidity
requestDMNDecision(
  string calldata url,
  string calldata dmnCid,
  string calldata decisionId,
  string calldata inputData
)
```

优点：

- 语义干净
- Job / CDMN 层也更容易理解

缺点：

- 需要同步改 `DMN_lite` 合约及其上下游

#### 方案 B：兼容旧字段名

继续使用原字段名 `dmnContent`，但实际上传 CID。

优点：

- 改动面小

缺点：

- 语义污染严重
- 后续维护成本高

建议采用方案 A。

### 4. Chainlink Job

`job-spec-dmn-event.toml` 的 `call_cache` 请求体应从：

```toml
requestData="{\"requestId\": $(decode_log.requestId), \"dmnContent\": $(decode_cbor.dmnContent), \"decisionId\": $(decode_cbor.decisionId), \"inputData\": $(parse_input)}"
```

改为：

```toml
requestData="{\"requestId\": $(decode_log.requestId), \"dmnCid\": $(decode_cbor.dmnCid), \"decisionId\": $(decode_cbor.decisionId), \"inputData\": $(parse_input)}"
```

### 5. CDMN 服务

`cdmn-python-server` 需要新增：

- `cid -> FireFly/IPFS -> dmnContent` 解析逻辑
- 可选 `hash` 校验

推荐方式：

1. 新增独立 resolver 模块
2. `/api/dmn/calc` 支持 `dmnCid`
3. 保持兼容旧 `dmnContent` 模式一段时间，便于平滑迁移

## 与 Fabric 方案的关系

本方案不是全新路线，而是复用现有 Fabric 的成熟经验：

- DMN 内容先存链下
- 链上/链码只记录引用
- 执行时再按引用取内容

已有可参考位置：

- `backend/apps/api/management/commands/listeners/dmn_create_listener.py`
- `backend/apps/api/management/commands/listeners/dmn_execute_listener.py`
- `newTranslator/generator/resource/chaincode.sol`

实现时应尽量复用这些已有思路，而不是重新发明一套内容寻址机制。

## 分阶段实施建议

### 第一阶段：链下 CID 通路打通

先实现：

- DMN 上传到 FireFly / IPFS
- 后端拿到 `cid/hash`
- CDMN 能根据 `cid` 取到 DMN XML

此阶段先不改工作流合约。

### 第二阶段：Chainlink Job 改成传 CID

实现：

- `DMN_lite` / Job / CDMN 全链路以 `cid` 为主要载荷
- directrequest 仍然跑通

### 第三阶段：newTranslator / Solidity 接入

实现：

- `createInstance()` 只记录 `cid/hash/decisionId`
- `Activity_*` 直接调用 `DMN_lite`
- `Continue()` 按 requestId 取结果

## 风险与边界

### 风险 1：CID 取回失败

需要定义清楚：

- FireFly 不可达
- IPFS Gateway 不可达
- CID 对应内容丢失

这类情况下 CDMN 应明确返回失败，并让请求状态保持可追踪。

### 风险 2：CID 内容与 hash 不一致

如果同时保存了 `cid` 和 `hash`，CDMN 在执行前应校验：

- `keccak256(dmnContent) == hash`

否则拒绝计算。

### 风险 3：接口兼容期

过渡期内很可能会同时存在两类请求：

- 旧版 `dmnContent`
- 新版 `dmnCid`

需要明确兼容期和切换点，否则会出现 Job / CDMN / 合约版本错配。

## 实施原则

后续实现应遵循以下原则：

1. 不再把完整 DMN XML 作为主执行载荷在链上长距离流转
2. 不在工作流实例中持久化完整 DMN XML
3. `cid/hash/decisionId` 作为唯一稳定引用
4. 内容解析和 DMN XML 获取放到链下
5. `Activity_*` 尽量直接拿到 `requestId`，减少额外回写步骤

## 结论

后续 `04-dmn-ocr`、`DMN_lite`、`newTranslator`、CDMN 和 BPMN/EVM 工作流的统一方向应为：

- DMN 内容绑定到 FireFly/IPFS
- 合约只存 `cid/hash/decisionId`
- `Activity_*` 直接发起 `DMN_lite` 请求
- Chainlink / CDMN 根据 `cid` 解析 DMN 内容
- `Continue()` 从 `DMN_lite` 读取结果继续流程

后续代码实现应以本设计为准。
