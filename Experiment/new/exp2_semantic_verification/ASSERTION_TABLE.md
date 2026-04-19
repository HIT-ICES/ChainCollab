# 实验二语义保真断言表

这份断言表用于 `exp2_semantic_verification`，已按确认稿 [2025.04.14-实验二断言fix.md](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/2025.04.14-实验二断言fix.md) 对齐。

这些断言不再来自 `check.ocl`，而是直接来自 `newTranslator` 的真实代码生成逻辑：

- `src/newTranslator/CodeGenerator/b2cdsl-go/...`
- `src/newTranslator/CodeGenerator/b2cdsl-solidity/...`

因此这里验证的是：

- DSL 元素在 Go / Solidity 中是否具有对应静态结构
- DSL `flow` 的 `trigger / branch / action` 是否在 Go / Solidity 中具有对应控制逻辑证据

而不是：

- 运行时行为轨迹等价
- Go 与 Solidity 执行结果完全一致

机器可读版本：
- [config/assertion_table.json](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/config/assertion_table.json:1)

## 字段说明

- `id`: 断言编号
- `dimension`: 维度（`structural` / `control`）
- `mode`:
  - `positive`: 重点看正例稳定通过
  - `both`: 同时看正例通过与负例触发失败
- `targets`: 断言作用目标（`go` / `solidity`）
- `source`: 对应 `newTranslator` 生成器中的实现来源

## A. 结构一致性

| ID | 断言说明 | 目标语言 | 静态证据 | 通过标准 | 生成逻辑来源 |
| --- | --- | --- | --- | --- | --- |
| SV01 | 全局变量应映射到目标语言状态存储结构 | go + solidity | Go IR 中的 `globals`；Solidity IR 中的 `state_fields` | DSL 中每个 `global` 都能在目标代码状态结构中找到对应字段，且类型映射符合生成器预设类型映射表 | Go 类型映射与 `contract.go.jinja`；Solidity 类型映射与 `contract.sol.jinja` |
| SV02 | 参与方应映射为访问控制相关结构或检查入口 | go + solidity | Go IR 中与 participant 相关的检查函数或调用痕迹；Solidity IR 中 `_checkParticipant` 及相关访问控制逻辑 | DSL 中定义的 participant 在目标代码中存在可识别的访问控制检查入口或身份校验结构 | Go: `check_participant` / `check_msp`；Solidity: `_checkParticipant` |
| SV03 | 消息应映射为消息处理结构 | go + solidity | message 对应的 handler、消息 key、处理函数、消息状态字段 | DSL 中每个 `message` 至少在目标代码中存在一个对应的消息处理结构，并可被识别为流程消息处理入口 | Go: `message_send.go.jinja` / `message_complete.go.jinja`；Solidity: `_render_messages` |
| SV04 | 网关应映射为网关相关结构或条件处理入口 | go + solidity | gateway key、分支处理函数、条件判断块 | DSL 中每个 `gateway` 在目标代码中存在对应的网关枚举项、处理逻辑或条件入口 | Go: `gateway.go.jinja`；Solidity: `_render_gateway_branches` / `_gateway_branch_condition` |
| SV05 | 事件应映射为事件处理结构 | go + solidity | start/event 对应 handler、事件 key、事件相关状态推进入口 | DSL 中每个 `event` 在目标代码中存在可识别的事件处理结构或启动入口 | Go: `start_event.go.jinja` / `event.go.jinja`；Solidity 对应 event 渲染逻辑 |
| SV06 | 业务规则应映射为业务规则处理结构 | go + solidity | businessrule 对应主处理函数、继续处理函数、规则键或生命周期入口 | DSL 中每个 `businessrule` 在目标代码中存在对应的规则处理结构，至少覆盖请求或继续处理的静态入口 | Go / Solidity businessrule 主函数与 `_Continue` 相关逻辑 |
| SV07 | 预言机任务应映射为预言机任务处理结构 | go + solidity | oracle task 对应任务处理函数、任务类型分支、输出写回入口 | DSL 中每个 `oracletask` 在目标代码中存在 external / compute 任务处理结构与输出写回相关代码证据 | `_render_oracle_tasks` 与 output mapping 写回逻辑 |

## B. 控制语义一致性

| ID | 断言说明 | 目标语言 | 静态证据 | 通过标准 | 生成逻辑来源 |
| --- | --- | --- | --- | --- | --- |
| SV08 | Flow 动作应映射为 enable / disable / set 控制代码 | go + solidity | handler 中的状态更新、元素启用/禁用代码、全局变量赋值代码 | DSL flow 中的 `enable / disable / set` 动作可在目标代码 handler 中找到对应状态更新或赋值证据 | `_render_action`、`_change_state_code`、set global 渲染逻辑 |
| SV09 | Go 消息处理函数应包含消息状态推进控制逻辑 | go | Go IR 中的消息 handler、`ChangeMsgState` 或等价状态推进调用 | DSL message 相关 flow 在 Go handler 中存在明确的消息状态推进证据 | `message_send.go.jinja` / `message_complete.go.jinja` |
| SV10 | Solidity 消息处理函数应包含消息状态赋值控制逻辑 | solidity | Solidity IR 中消息处理函数里的 `m.state = ...` 或等价状态赋值 | DSL message 相关 flow 在 Solidity handler 中存在明确的消息状态推进证据 | `_render_messages` 中 `m.state = ElementState.COMPLETED` 等逻辑 |
| SV11 | Go 业务规则处理应存在外部规则调用与继续处理控制证据 | go | 业务规则 handler、外部调用路径、继续执行相关函数调用 | Go 代码中存在与 DSL businessrule 对应的规则调用入口，并存在继续处理或结果推进的静态控制逻辑证据 | `Invoke_Other_chaincode`、Oracle / DMNEngine 调用路径等 |
| SV12 | Solidity 业务规则处理应存在外部规则服务交互控制证据 | solidity | 外部请求函数、请求标识、状态查询、结果读取相关控制逻辑 | Solidity 代码中存在与 DSL businessrule 对应的外部规则服务交互入口，且可识别出请求发起与后续状态查询的静态控制逻辑证据 | `requestDMNDecision`、请求 ID 管理、`getRequestStatus`、`getRawByRequestId` 等路径 |
| SV13 | Solidity 业务规则处理应存在结果回写控制证据 | solidity | 结果提取、类型转换、状态内存写回相关控制逻辑 | Solidity 代码中存在将外部规则返回结果解析并写回 DSL `output mapping` 对应状态字段的静态控制逻辑证据 | `getRawByRequestId` 后的结果解析与 `inst.stateMemory.<slot>` 写回路径 |
| SV14 | Flow 条件语义应映射为 compare / parallel 条件检查 | go + solidity | handler 中的 `if`、`require`、parallel guard、元素 ready 检查 | DSL 中 compare branch 与 parallel join 的条件，在目标代码中存在可识别的条件判断或 guard 检查证据 | `_gateway_branch_condition`、`_parallel_guard_block`、`_element_ready_check` |

## 与覆盖统计的关系

`summary_report.py` 会基于每个 case 的 `dsl_go_report.json` / `dsl_sol_report.json` 自动统计：

- 正例：断言是否通过
- 负例：断言是否被触发失败

统计输出位置：

- `results/assertion_coverage.json`
- `results/assertion_coverage.md`
