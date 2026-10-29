# 实验二：B2CDSL -> 目标代码语义保真验证

这个实验项目用于验证：**B2CDSL 中定义的结构语义与控制语义，是否被当前 `newTranslator` 正确保留到 Go 链码和 Solidity 合约中。**

它不是部署工具，也不验证 Fabric / Geth 运行环境；它只关注 **DSL 到目标代码的静态一致性证据**。

当前断言体系已按确认稿 [2025.04.14-实验二断言fix.md](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/2025.04.14-实验二断言fix.md) 对齐，不再沿用 `check.ocl` 那类目标模型合法性断言。

## 实验目标

给定一份 DSL 正例：

1. 直接复用 `src/newTranslator/MDAcheck/bpmn-positive/b2c/` 中的正例 `.b2c`
2. 基于 `.b2c` 继续生成 `.go` 和 `.sol`
3. 分别解析 B2CDSL、Go AST、Solidity AST
4. 按 DSL -> Go / Solidity 映射契约做自动校验
5. 输出结构化报告和批量汇总结果

重点验证的元素与控制语义包括：

- `participants`
- `globals`
- `messages`
- `gateways`
- `events`
- `businessrules`
- `oracletasks`
- `flows`

换句话说，本实验回答的问题是：

**B2CDSL 中的关键业务元素，在经过代码生成后，是否仍然能在 Go 链码和 Solidity 合约中找到结构上和控制语义上对应的实现证据。**

它不直接回答：

- Go 与 Solidity 是否运行时行为完全等价
- 外部 DMN / Oracle 返回值是否具有真实业务语义正确性
- 链上部署和执行环境差异是否会影响结果

## 当前验证契约

当前断言分成两组：

- 结构一致性：SV01-SV07
- 控制语义一致性：SV08-SV14

1. DSL `globals` -> Go `StateMemory` 字段 / Solidity `StateMemory` 槽位或状态变量
2. DSL `participants` -> Go 身份校验逻辑 / Solidity `_checkParticipant` / `msg.sender` 约束
3. DSL `message` -> Go `<Message>_Send / <Message>_Complete` / Solidity 消息处理函数与消息状态字段
4. DSL `gateway` -> Go `if/switch` / Solidity `if/require`
5. DSL `event` -> Go 事件入口 / Solidity action event 推进函数
6. DSL `businessrule` -> Go 规则处理函数或外部调用 / Solidity `IDmnLite` 请求、轮询、结果回写与 continuation 逻辑
7. DSL `oracletask` -> Go action-event 风格处理函数 / Solidity `IOracle` 调用点
8. DSL `flows` -> 条件逻辑 + 状态迁移 + 变量赋值
9. Go 消息处理 -> `ChangeMsgState` 或等价推进逻辑
10. Solidity 消息处理 -> `m.state = ...` 或等价推进逻辑
11. Go 业务规则 -> 外部规则调用与继续处理控制证据
12. Solidity 业务规则 -> 请求发起、状态查询、结果读取控制证据
13. Solidity 业务规则 -> `output mapping` 对应的结果回写控制证据
14. compare / parallel flow -> 显式条件判断、guard 或 ready 检查

## 项目特点

- 不修改 `newTranslator` 源码，只调用其现有生成链路
- 同时支持复用 `nt.sh` 命令和 `newTranslator` FastAPI 接口
- 不重写 BPMN -> DSL 或 DSL -> 代码生成器
- 以 AST 和结构化语义证据为主，不做纯 grep 级字符串搜索
- 报告可定位到具体 DSL 元素和代码结构证据
- 支持批量 case 验证
- 支持从“结构存在性”“类型对应性”“控制语义证据”三个层次做检查
- 当前解析和映射规则已按 `translator.py`、`b2cdsl-go`、`b2cdsl-solidity` 的真实实现对齐

## 目录结构

```text
Experiment/new/exp2_semantic_verification/
├── ASSERTION_TABLE.md      # 面向 DSL->目标代码语义保真的断言表（可读版）
├── config/
│   └── assertion_table.json # 断言表（机器可读）
├── cases/                  # case 清单
│   ├── Blood_analysis/
│   ├── Hotel_Booking/
│   └── ...
├── cases/_legacy_disabled/ # 归档的旧 BPMN 驱动 case，不参与当前批量实验
├── results/
│   ├── cases/              # 单 case 全部中间产物与报告
│   ├── assertion_coverage.json
│   ├── assertion_coverage.md
│   ├── exp2_summary.json
│   ├── exp2_summary.md
│   └── run_log.json
├── scripts/
│   ├── common.py
│   ├── parse_b2c.py
│   ├── extract_go_ast.go
│   ├── extract_sol_ast.js
│   ├── mapping_rules.py
│   ├── verify_dsl_go_semantics.py
│   ├── verify_dsl_sol_semantics.py
│   ├── summary_report.py
│   └── run_exp2.py
└── requirements.txt
```

## 实验流程

一轮完整实验的执行逻辑如下：

1. 从 `cases/` 中读取 case 清单
2. 对每个 case 直接引用 `MDAcheck/bpmn-positive/b2c` 中对应的 `.b2c`
3. 基于这份 `.b2c` 调用当前生成链路，生成 `.go` 和 `.sol`
4. 解析 B2CDSL，抽取统一结构 JSON
5. 解析 Go，抽取统一 AST JSON
6. 解析 Solidity，抽取统一 AST JSON
7. 基于映射契约逐项校验 DSL -> Go
8. 基于映射契约逐项校验 DSL -> Solidity
9. 在单 case 内根据断言表检查该 case 是否满足/违反各条断言
10. 输出单 case 报告与批量汇总表

断言覆盖统计里，case 默认按 `positive` 处理；如果你要加入负例，请在 `cases/<case>/case.json` 中声明：

```json
{
  "case_name": "invalid_xxx",
  "case_type": "negative"
}
```

当前默认数据源是：

- `src/newTranslator/MDAcheck/bpmn-positive/b2c/*.b2c`

当前 `cases/` 目录中的启用 case 名称、目录名和生成产物文件名保持一致。
旧的 BPMN 驱动样例已归档到 `cases/_legacy_disabled/`，不参与默认批量运行。

这意味着当前实验结果默认反映的是：

- `MDAcheck` 已确认通过模型合法性校验的正例 DSL
- 当前版本的 `newTranslator`
- 基于这些 DSL 重新生成的 `.go` / `.sol`

而不是历史运行目录中遗留的旧产物，也不是实验二自己从 BPMN 重新生成出来的 DSL。

## 运行方式

### 安装依赖

```bash
cd /root/code/ChainCollab/Experiment/new/exp2_semantic_verification
/root/code/ChainCollab/src/newTranslator/.venv/bin/pip install -r requirements.txt
```

### 批量运行

```bash
/root/code/ChainCollab/src/newTranslator/.venv/bin/python \
  /root/code/ChainCollab/Experiment/new/exp2_semantic_verification/scripts/run_exp2.py
```

### 指定输入输出目录

```bash
/root/code/ChainCollab/src/newTranslator/.venv/bin/python \
  /root/code/ChainCollab/Experiment/new/exp2_semantic_verification/scripts/run_exp2.py \
  --cases-dir /root/code/ChainCollab/Experiment/new/exp2_semantic_verification/cases \
  --results-dir /root/code/ChainCollab/Experiment/new/exp2_semantic_verification/results
```

### 通过 FastAPI 接口运行

如果已经启动 `newTranslator` 的 API 服务，可以直接复用现有接口：

```bash
/root/code/ChainCollab/src/newTranslator/.venv/bin/python \
  /root/code/ChainCollab/Experiment/new/exp2_semantic_verification/scripts/run_exp2.py \
  --backend api \
  --api-base-url http://127.0.0.1:8000
```

当前 API 模式复用：

- `/api/v1/chaincode/generate`
- `/api/v1/chaincode/compile`

## 脚本说明

- `scripts/run_exp2.py`
  - 批量入口
  - 负责扫描 case、调用 `newTranslator` 生成 `.b2c` / `.go` / `.sol`、执行解析和校验、写出汇总结果

- `scripts/parse_b2c.py`
  - 将 `.b2c` 抽取为统一 JSON
  - 重点会解析 `participants / globals / messages / gateways / events / businessrules / flows`

- `scripts/extract_go_ast.go`
  - 使用 `go/parser` 和 `go/ast` 解析生成的 Go 链码
  - 输出 `structs / state_fields / functions / if_conditions / switches / assignments / external_calls`

- `scripts/extract_sol_ast.js`
  - 解析 `solc --standard-json` 产出的 Solidity AST
  - 保留 `inst.stateMemory.X`、`inst.messages[...] .state`、`dmnLite.requestDMNDecision(...)` 这类完整访问路径
  - 输出 `contracts / state_variables / enums / functions / requires / assignments / events / external_calls`

- `scripts/mapping_rules.py`
  - 统一维护 DSL -> Go / Solidity 映射规则
  - 避免将规则散落在各个验证脚本里

- `scripts/verify_dsl_go_semantics.py`
  - 执行 DSL -> Go 语义保真校验
  - 输出 `go_semantic_report.json`

- `scripts/verify_dsl_sol_semantics.py`
  - 执行 DSL -> Solidity 语义保真校验
  - 输出 `solidity_semantic_report.json`

- `scripts/summary_report.py`
  - 汇总多个 case 的结果
  - 优先读取每个 case 已经产出的 `case_assertions.json`
  - 再按 `config/assertion_table.json` 聚合正/负例断言覆盖
  - 输出 `exp2_summary.json`、`exp2_summary.md`、`assertion_coverage.json` 和 `assertion_coverage.md`

- `scripts/common.py`
  - 放公共逻辑
  - 包括 case 发现、路径约定、调用 `newTranslator` 命令或 HTTP 接口生成 DSL / Go / Solidity 等

## 输出说明

每个 case 会输出：

- `results/cases/<case>/dsl.b2c`
  - 当前 `newTranslator` 重新生成的 DSL
- `results/cases/<case>/chaincode.go`
  - 当前 `newTranslator` 重新生成的 Go 链码
- `results/cases/<case>/contract.sol`
  - 当前 `newTranslator` 重新生成的 Solidity 合约
- `results/cases/<case>/dsl_ast.json`
  - B2CDSL 统一解析结果
- `results/cases/<case>/go_ast.json`
  - Go AST 统一解析结果
- `results/cases/<case>/solidity_ast.json`
  - Solidity AST 统一解析结果
- `results/cases/<case>/go_semantic_report.json`
  - 单案例 DSL -> Go 结构化验证报告
- `results/cases/<case>/solidity_semantic_report.json`
  - 单案例 DSL -> Solidity 结构化验证报告
- `results/cases/<case>/case_assertions.json`
  - 单案例断言检查结果
  - 记录该 case 对 `SV01-SV14` 是 `satisfied`、`violated`、`triggered`、`not_triggered` 还是 `unobserved`

批量汇总输出：

- [run_log.json](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/results/run_log.json)
  - 批量运行日志
- [exp2_summary.json](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/results/exp2_summary.json)
  - 批量汇总 JSON
- [exp2_summary.md](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/results/exp2_summary.md)
  - Markdown 汇总表
- [assertion_coverage.json](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/results/assertion_coverage.json)
  - 断言覆盖统计 JSON（按断言 ID 聚合正例通过率与负例触发率）
- [assertion_coverage.md](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/results/assertion_coverage.md)
  - 断言覆盖统计 Markdown

断言表文件：

- [ASSERTION_TABLE.md](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/ASSERTION_TABLE.md)
  - 人类可读的断言体系说明，已与 2025-04-14 确认稿对齐
- [assertion_table.json](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/config/assertion_table.json)
  - 机器可读断言配置

## 指标说明

实验报告中使用 4 个核心指标：

- `dsl_element_coverage`
  - 表示 DSL 中的关键元素，有多少能在目标代码中找到对应实现证据

- `state_transition_preservation_rate`
  - 表示 DSL `flows` 中的状态迁移、启用/禁用、赋值动作，有多少被代码保留

- `branch_logic_preservation_rate`
  - 表示 DSL `gateways` 对应的关键分支逻辑，有多少被目标代码中的 `if/switch/require` 等结构体现

- `businessrule_mapping_accuracy`
  - 表示 DSL 中 `businessrule` 的规则调用、输入输出映射、决策标识等语义，有多少仍被目标代码保留

通常可以这样理解：

- `dsl_element_coverage` 低：说明 DSL 元素本身在目标代码中难以找到
- `state_transition_preservation_rate` 低：说明流程推进逻辑丢失较多
- `branch_logic_preservation_rate` 低：说明网关分支语义没有被充分落实
- `businessrule_mapping_accuracy` 低：说明规则处理或外部调用保真度不足

## 当前实验状态

当前默认批跑集已完成 `11` 个样本的批量验证。

- 运行成功：`11`
- 运行失败：`0`

当前样例包括：

- `BikeRental`
- `Blood_analysis`
- `Coffee_machine`
- `Hotel_Booking`
- `Pizza_Order`
- `SupplyChainPaper7777_zh_name`
- `customer`
- `customer_new`
- `manu2`
- `service_provider_runtime`
- `service_provider_runtime_br`

汇总结果见：

- [exp2_summary.json](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/results/exp2_summary.json)
- [exp2_summary.md](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/results/exp2_summary.md)

从当前结果看：

- Go 侧在这 11 个样例上的覆盖率均为 `100%`
- Solidity 侧在按真实生成器实现修正解析与映射后，也能稳定识别 DMN 调用、参与方校验、状态推进和 flow 动作证据，当前默认样例集覆盖率均为 `100%`

这说明当前实验框架已经从“通用语义假设”收拢到“当前生成器真实行为”的旁路验证版本。

另有两个保留在 `cases/` 中但默认不参与批跑的已知不稳定案例：

- `Purchase`
  - 当前 Solidity 生成结果包含重复状态字段名，`solc` 无法生成 AST
- `amazon`
  - 当前 Solidity 生成结果出现保留字参数名 `type`，`solc` 无法完成解析

这两个案例保留下来是为了记录当前 `newTranslator` 的真实边界，而不是实验二规则本身的不一致。

## 示例 case

当前内置了 11 个可直接复现实验的默认样例：

- [BikeRental](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/cases/BikeRental)
  - 无 DMN 的基础流程样例
- [Blood_analysis](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/cases/Blood_analysis)
  - 含业务规则 / DMN 的样例
- [Coffee_machine](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/cases/Coffee_machine)
  - 短流程消息与网关样例
- [Hotel_Booking](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/cases/Hotel_Booking)
  - 较长消息链与多网关样例
- [Pizza_Order](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/cases/Pizza_Order)
  - 订单编排样例
- [SupplyChainPaper7777_zh_name](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/cases/SupplyChainPaper7777_zh_name)
  - 经典供应链协同案例
- [customer](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/cases/customer)
  - 长消息序列样例
- [customer_new](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/cases/customer_new)
  - 客户协同扩展样例
- [manu2](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/cases/manu2)
  - 制造协同样例
- [service_provider_runtime](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/cases/service_provider_runtime)
  - 运行时流程样例
- [service_provider_runtime_br](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/cases/service_provider_runtime_br)
  - 带业务规则处理的运行时样例

例如可查看：

- [BikeRental go_semantic_report.json](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/results/cases/BikeRental/go_semantic_report.json)
- [BikeRental solidity_semantic_report.json](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/results/cases/BikeRental/solidity_semantic_report.json)
- [Blood_analysis go_semantic_report.json](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/results/cases/Blood_analysis/go_semantic_report.json)
- [Blood_analysis solidity_semantic_report.json](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/results/cases/Blood_analysis/solidity_semantic_report.json)

## 依赖与复用

本实验复用了仓库中已有的核心能力：

- DSL 语法：
  [b2c.tx](/root/code/ChainCollab/src/newTranslator/DSL/B2CDSL/b2cdsl/b2c.tx)
- BPMN -> B2C 生成入口：
  [bpmn_to_dsl.py](/root/code/ChainCollab/src/newTranslator/generator/bpmn_to_dsl.py)
- 命令行工具：
  [nt.sh](/root/code/ChainCollab/src/newTranslator/nt.sh)
- Go / Solidity 生成链路：
  [translator.py](/root/code/ChainCollab/src/newTranslator/generator/translator.py)

## 设计原则

这个实验项目在设计上有几个明确原则：

- 只做验证，不改生成器逻辑
- 尽量复用仓库原有生成与语法能力
- 不把验证建立在历史产物上，而是建立在“当前输入 + 当前生成器 + 当前输出”上
- 报告必须可定位，不能只给出笼统的“失败”
- 比对尽量做结构和语义对齐，而不是全文字符串强匹配

## 适用场景

这个实验项目适合用于：

- 论文中的“代码生成语义保真验证”实验
- 回归检查 `newTranslator` 的 DSL -> 代码生成稳定性
- 快速定位 DSL 元素在 Go / Solidity 中的缺失或语义不一致问题

## 当前限制

- Solidity 侧当前规则偏保守，容易出现“存在实现但证据未完全识别”的漏判
- 某些 `businessrule` 的输入输出映射在目标代码中可能通过较隐式的方式保存，目前只识别较稳定的结构证据
- 当前实验关注静态结构与控制语义，不包含链上运行时执行路径验证
- 当前不覆盖 Fabric / Geth / Chainlink / Caliper 部署与执行层实验
