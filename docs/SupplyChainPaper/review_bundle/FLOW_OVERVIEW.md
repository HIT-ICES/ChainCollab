# SupplyChainPaper 主链说明

## 转换期

本轮真实转换链是：

```text
SupplyChainPaper.bpmn
  → BPMN parser
  → SupplyChainPaper.b2c
  → textX parser / platform adapter
  → renderer.build_context()
  → Jinja2 templates
  → SupplyChainPaper.go / SupplyChainPaper.sol
```

BPMN→B2CDSL 阶段读取 BPMN 的消息 schema、BusinessRule documentation 和控制流。它没有解析 `supplyChainPaper.dmn`。Fabric/Go 和 Geth/Solidity 都由 Jinja2 模板生成；`generation_contexts/` 保存了两端实际模板 context。

## 运行期

DMN 在运行期由平台外部决策组件处理：

```text
消息函数写入 NumberOfUnits / Urgent / SupplierReputation
→ Activity_0rm8bkp 收集输入
→ 发起外部 DMN 请求并进入 WAITING
→ 外部决策组件解析并执行 DMN
→ Continue/回调读取 finalPriority
→ 写入 FinalPriority
→ 启用 Gateway_0ep8cuh
→ Low / Medium / High / VeryLow 四分支
```

Fabric 端在初始化时接收 DMN 内容、decision ID 和 ParamMapping，随后调用独立的 `DMNEngine:v1` 链码。Geth 端在初始化时接收 DMN CID、hash、decision ID、`dmnLiteAddress` 和 `dmnEvalUrl`，通过 `IDmnLite` 抽象对接 Chainlink/链下决策流程。

## DMN 未在转换期解析的影响

这不阻断 BPMN→PIM→两端代码的结构串联，也不阻断 request/wait/continue/write-back/gateway 代码生成。实际 decision ID 和 DMN 资源由运行时初始化参数提供，因此 B2CDSL 中按任务 ID 生成的占位绑定没有被两端 renderer 固化为不可修改的运行时值。

缺失的是转换期静态保证：当前链路不会自动验证 `Decision_0zwjfyy`、其对 `decision_0tybghz` 的依赖、字段类型和最终输出。只有运行独立 DMN 链码或 Chainlink 链下流程，才能证明真实决策执行与四分支结果。

## 本轮可声明结论

- BPMN→B2CDSL、DSL 解析、Go 生成、Solidity 生成和模板 context 导出成功。
- Solidity 使用 solc-js 0.8.33 编译成功。
- Go 编译受本机 Go 1.22 与 `go.mod` 要求 1.23.1，以及工具链下载超时阻断；不能据此判定源码编译成功或失败。
- 没有部署网络，没有运行 Fabric DMN 链码或 Chainlink，因此不能声明端到端决策执行通过。
