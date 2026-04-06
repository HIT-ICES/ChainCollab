# 实验二校验映射规则说明

本文档说明实验二“B2CDSL -> 目标代码语义保真验证”所采用的**校验映射规则**、**证据类型**、**判定逻辑**与**指标计算方式**。

实验二的目标不是判断“代码是否能生成”，而是判断：

**B2CDSL 中定义的结构语义与控制语义，是否在生成出的 Go 链码和 Solidity 合约中得到正确保留。**

---

## 1. 规则设计原则

实验二的映射校验遵循以下原则：

1. 不修改 `newTranslator` 主工程代码
2. 只做旁路验证，不改生成链路
3. 优先基于 AST 和结构化信息做判断
4. 不做纯文本全文匹配，不依赖模板字面字符串
5. 规则优先对齐 `newTranslator` 当前真实代码生成行为
6. 规则尽量保守，优先降低误判
7. 每个“通过”结论都尽量附带可解释证据

因此，实验二采用的是：

- **结构匹配**
- **类型匹配**
- **控制语义证据匹配**

三层组合的验证方式。

---

## 2. 输入与中间表示

实验二的校验建立在 3 类统一中间表示之上：

### 2.1 DSL 侧

由 [parse_b2c.py](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/scripts/parse_b2c.py) 从 `.b2c` 中提取：

- `participants`
- `globals`
- `messages`
- `gateways`
- `events`
- `businessrules`
- `oracletasks`
- `flows`

其中 `flows` 被结构化为：

- `trigger`
- `conditions`
- `actions`

### 2.2 Go 侧

由 [extract_go_ast.go](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/scripts/extract_go_ast.go) 从生成的 `.go` 文件中提取：

- `structs`
- `state_fields`
- `functions`
- `if_conditions`
- `switches`
- `assignments`
- `external_calls`
- `calls`
- `string_literals`

### 2.3 Solidity 侧

由 [extract_sol_ast.js](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/scripts/extract_sol_ast.js) 从 `solc` AST 输出中提取：

- `contracts`
- `state_variables`
- `enums`
- `functions`
- `requires`
- `assignments`
- `events`
- `external_calls`
- `calls`
- `if_conditions`
- `string_literals`

当前 Solidity 提取器会尽量保留完整成员访问路径，例如：

- `inst.stateMemory.Result`
- `inst.gateways[GatewayKey.X].state`
- `dmnLite.requestDMNDecision`

---

## 3. 实验总控与执行流程

实验二的总控逻辑由：
[run_exp2.py](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/scripts/run_exp2.py)
负责。

它对每个 case 执行如下步骤：

1. 从 `cases/<case>/input.bpmn` 读取输入 BPMN
2. 调用 `newTranslator` 现有命令或 FastAPI 接口生成 `.b2c`
3. 基于 `.b2c` 继续生成 `.go`
4. 基于 `.b2c` 继续生成 `.sol`
5. 解析 `.b2c`，得到 `dsl_ast.json`
6. 解析 `.go`，得到 `go_ast.json`
7. 调用 `solc --standard-json` 生成原始 Solidity AST
8. 将原始 AST 转换为统一 JSON，得到 `sol_ast.json`
9. 执行 DSL -> Go 校验
10. 执行 DSL -> Solidity 校验
11. 汇总所有 case 结果，生成 `run_log.json / exp2_summary.json / exp2_summary.md`

### 3.1 case 发现与路径解析

当前 case 发现逻辑位于：
[common.py](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/scripts/common.py)

主要行为：

- 扫描 `cases/` 下所有同时包含 `input.bpmn` 的子目录
- 读取可选的 `case.json`
- 解析：
  - `case_name`
  - `description`
  - `input.bpmn`
  - `input.dmn`

### 3.2 生成链路调用方式

实验二没有重写生成器，而是通过 `common.py` 中的包装函数复用现有命令或 HTTP 接口：

- `generate_b2c()`
  - 调用 `nt-bpmn-to-b2c`
- `generate_go()`
  - 调用 `nt-go-gen`
- `generate_solidity()`
  - 调用 `nt-sol-gen`
- `generate_b2c_via_api()`
  - 调用 `/api/v1/chaincode/generate`
- `compile_dsl_via_api()`
  - 调用 `/api/v1/chaincode/compile`

因此实验二与主工程之间的关系是：

- **主工程负责生成**
- **实验工程负责解析、验证、汇总**

### 3.3 单 case 输出组织方式

每个 case 的结果统一写入：

- `results/cases/<case>/`

其中包括：

- `<case>.b2c`
- `<case>.go`
- `<case>.sol`
- `dsl_ast.json`
- `go_ast.json`
- `solc_ast_raw.json`
- `sol_ast.json`
- `dsl_go_report.json`
- `dsl_sol_report.json`

这样做的目的有两个：

1. 将实验中间产物与主工程彻底隔离
2. 保证每个 case 可独立检查和复现

---

## 4. DSL 解析逻辑

DSL 解析由：
[parse_b2c.py](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/scripts/parse_b2c.py)
实现。

它的职责不是简单把 `.b2c` 转成文本 JSON，而是把 DSL 结构化成**适合后续映射校验**的统一中间表示。

### 4.1 解析入口

当前实现使用 `textX`：

- 通过 `metamodel_from_file()` 加载
  [b2c.tx](/root/code/ChainCollab/src/newTranslator/DSL/B2CDSL/b2cdsl/b2c.tx)
- 通过 `model_from_file()` 将 `.b2c` 实例化为对象模型

如果模型中不存在 `contract`，解析会直接报错。

### 4.2 section 分派逻辑

`parse_b2c_model()` 会遍历 `contract.sections`，按 section 类型分派：

- `ParticipantSection`
- `GlobalSection`
- `MessageSection`
- `GatewaySection`
- `EventSection`
- `BusinessRuleSection`
- `OracleTaskSection`
- `FlowSection`

这样做的意义是：

- 不依赖 DSL 文本顺序做字符串截取
- 直接基于语法树和对象模型做抽取

### 4.3 participants 解析逻辑

对每个 `participant`，当前会抽取：

- `name`
- `msp`
- `x509`
- `is_multi`
- `multi_min`
- `multi_max`
- `role`
- `attributes`

其中：

- `role` 来自 `attributes { role = "..." }`
- `attributes` 被转成键值字典

这使得后续参与方验证不仅能看“参与者名字在不在”，还能保留其身份约束上下文。

### 4.4 globals 解析逻辑

对每个 `GlobalVar`，当前只保留两个关键字段：

- `name`
- `type`

这是因为在实验二中，`globals` 的主要语义是：

- 是否有对应状态字段
- 类型是否大体一致

### 4.5 messages 解析逻辑

对每个 `message`，抽取：

- `name`
- `from`
- `to`
- `initial_state`
- `schema`

这样后续校验可以检查：

- 是否存在对应消息处理函数
- 是否保留参与方方向
- 是否伴随状态变化

### 4.6 gateways 解析逻辑

对每个 `gateway`，抽取：

- `name`
- `type`
- `initial_state`

其中 `type` 会保留 DSL 原有类型，如：

- `exclusive`
- `parallel`
- `event`

这样后续分支语义验证可以直接根据 gateway 类型选择不同规则。

### 4.7 events 解析逻辑

对每个 `event`，抽取：

- `name`
- `initial_state`

实验二中对 event 的关注重点是：

- 是否存在事件入口函数
- 是否有事件状态推进
- 是否推动了后继元素

### 4.8 businessrules 解析逻辑

对每个 `businessrule`，抽取：

- `name`
- `dmn`
- `decision`
- `input_mapping`
- `output_mapping`
- `initial_state`

其中 `input_mapping / output_mapping` 会进一步被结构化为：

- `dmn_param`
- `global`

这保证后续规则校验不是只看“有没有 businessrule”，而是还能检查：

- 决策标识是否保留
- 全局变量映射是否保留

### 4.9 oracletasks 解析逻辑

对每个 `oracletask`，当前抽取：

- `name`
- `type`
- `data_source`
- `compute_script`
- `output_mapping`
- `initial_state`

这样后续可以区分：

- `external-data` 型 oracle task
- `compute` 型 oracle task
- 以及它写回哪些全局变量

### 4.10 flows 解析逻辑

`flows` 是 DSL 解析中最关键的一部分。

当前实现会先按 flow item 类型分类：

- `StartFlow`
- `MessageFlow`
- `GatewayFlow`
- `RuleFlow`
- `EventFlow`
- `OracleTaskFlow`
- `ParallelJoin`

然后统一转换成：

- `kind`
- `trigger`
- `conditions`
- `actions`

三段式结构。

#### 4.10.1 trigger 结构

`trigger` 至少包含：

- `type`
- `name`
- `state`

例如：

- `message + sent`
- `message + completed`
- `gateway + completed`
- `businessrule + done`
- `parallel + await`
- `oracletask + done`

#### 4.10.2 actions 结构

当前 action 会被规范化为 3 类：

- `enable`
- `disable`
- `set`

分别对应 DSL 中的：

- `enable X`
- `disable X`
- `set G = value`

#### 4.10.3 conditions 结构

对于 gateway branch 和 parallel join，条件会被单独抽取。

当前支持：

- `compare`
  - 变量、关系、常量值
- `expression`
  - DSL 中显式表达式字符串
- `else`
- `await_all`
  - 并行 join 的前置来源列表

### 4.11 为什么 flow 要单独结构化

因为实验二并不是只验证元素存在性，而是验证控制语义。

而控制语义最直接的 DSL 表达正是：

- 谁触发流程推进
- 在什么条件下推进
- 推进时做了什么状态动作

所以如果不把 `flows` 结构化，后续就很难验证：

- `enable / disable`
- `set`
- `choose`
- `parallel await`

这些关键语义。

---

## 5. Go AST 抽取逻辑

Go 侧 AST 抽取由：
[extract_go_ast.go](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/scripts/extract_go_ast.go)
实现。

该脚本的核心思想是：

- 使用标准库 `go/parser` 和 `go/ast`
- 不依赖格式化结果或模板文本
- 将 Go 代码中的控制结构和状态更新提取为统一 JSON

### 5.1 解析入口

脚本使用：

- `token.NewFileSet()`
- `parser.ParseFile(...)`

将目标 `.go` 文件解析成 AST。

解析失败时，脚本会直接退出并返回错误。

### 5.2 structs 抽取逻辑

脚本先遍历所有 `GenDecl -> TypeSpec`：

- 若类型是 `StructType`
- 则提取 struct 名称与全部字段

输出结构为：

- `structs[].name`
- `structs[].fields[].name`
- `structs[].fields[].type`

### 5.3 state_fields 抽取逻辑

当前实现将 `StateMemory` 视为 DSL 全局状态的主要承载结构。

因此：

- 一旦发现 struct 名为 `StateMemory`
- 则其字段会额外写入 `state_fields`

这样后续 `globals` 验证无需在全部 struct 中再次搜索。

### 5.4 functions 抽取逻辑

对每个 `FuncDecl`，当前抽取：

- `name`
- `receiver`
- `params`
- `results`

这一步的目的不是重建完整函数体，而是为后续建立：

- message 函数
- gateway 函数
- event 函数
- businessrule 函数

与 DSL 元素之间的映射基础。

### 5.5 if / switch 抽取逻辑

函数体通过 `ast.Inspect()` 递归遍历。

其中：

- 遇到 `IfStmt`
  - 提取条件表达式文本
- 遇到 `SwitchStmt`
  - 提取 switch tag

并记录所属函数名。

这样后续就可以判断：

- 某个 gateway 是否真的对应了分支结构
- 某个 parallel join 是否有联合条件

### 5.6 assignments 抽取逻辑

遇到 `AssignStmt` 时，脚本提取：

- 左值列表 `LHS`
- 右值列表 `RHS`
- 所属函数

其用途主要是：

- 检测全局变量赋值
- 检测状态字段更新
- 为 flow 中的 `set` 动作提供证据

### 5.7 calls / external_calls 抽取逻辑

遇到 `CallExpr` 时，脚本统一抽取：

- `callee`
- `args`
- `function`

所有调用先进入 `calls`。

其中若命中以下模式，会额外进入 `external_calls`：

- `oracle.`
- `json.`
- `fmt.`
- `ctx.`
- `.GetStub`
- `.GetClientIdentity`
- `.InvokeChaincode`
- `shim.`
- `contractapi.`

这样做的意义是：

- 将“所有调用”与“更像外部依赖/系统交互的调用”分开
- 为 `businessrule`、参与方校验、链外调用提供更直接的证据来源

### 5.8 string_literals 抽取逻辑

遇到字符串字面量时，脚本会去掉引号或反引号，并写入 `string_literals`。

它的主要用途包括：

- 参与方标识匹配
- `decision` 标识匹配
- mapping 中的全局变量名保留情况匹配

### 5.9 Go 抽取阶段的核心目标

Go AST 抽取不是为了保存完整语法树，而是为了支撑后续 4 类验证：

1. 状态结构是否存在
2. 处理函数是否存在
3. 分支逻辑是否存在
4. 状态迁移或变量更新是否存在

---

## 6. Solidity AST 抽取逻辑

Solidity 侧 AST 抽取由：
[extract_sol_ast.js](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/scripts/extract_sol_ast.js)
实现。

它的职责分为两步：

1. 读取 `solc --standard-json` 的原始输出
2. 从 AST 中抽取实验二关心的统一结构

### 6.1 为什么采用两阶段处理

当前实验实现中，`solc` 的调用由总控脚本：
[run_exp2.py](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/scripts/run_exp2.py)
负责，生成：

- `solc_ast_raw.json`

然后由 `extract_sol_ast.js` 再进行归一化抽取。

这样做的好处是：

- 将编译器输出与实验规则解耦
- 更容易保留原始 AST 作为可复查中间产物
- 便于后续针对 AST 抽取逻辑独立迭代

### 6.2 AST 载入逻辑

`loadAstFromSolcOutput()` 的主要职责是：

1. 清理 `solc` 输出中的额外提示文本
2. 解析标准 JSON
3. 取出 `sources[*].ast`

若 AST 不存在，则直接报错。

### 6.3 统一文本化函数 `text(node)`

Solidity AST 中很多节点的结构层级较深，例如：

- `MemberAccess`
- `Identifier`
- `IndexAccess`
- `BinaryOperation`
- `FunctionCall`

当前脚本通过 `text(node)` 做统一文本化，将不同节点统一转为可比较的字符串表达。

例如：

- `inst.messages[MessageKey.X].state`
- `oracle.getDataItem`
- `a && b`

这一步非常关键，因为后续映射规则依赖这些归一化后的表达式做判断。

### 6.4 contracts / enums / events 抽取逻辑

当遍历到：

- `ContractDefinition`
- `EnumDefinition`
- `EventDefinition`

时，脚本会分别写入：

- `contracts`
- `enums`
- `events`

其作用分别是：

- 识别合约主体
- 识别参与方 / 消息 / 网关等枚举标识
- 识别事件声明

### 6.5 state_variables 抽取逻辑

当前脚本从两类位置抽取状态变量：

1. `VariableDeclaration` 且 `stateVariable=true`
2. `StructDefinition` 中名称为 `StateMemory` 的成员

这样既能覆盖：

- contract 顶层存储变量
- 业务状态结构中的字段

也能直接支持后续 `globals` 映射规则。

### 6.6 functions 抽取逻辑

对每个 `FunctionDefinition`，当前抽取：

- `name`
- `kind`
- `visibility`
- `state_mutability`
- `modifiers`
- `parameters`
- `returns`

这里的重点不是完整还原函数签名，而是为后续识别：

- message handler
- gateway 函数
- event 函数
- businessrule 函数

建立结构基础。

### 6.7 if_conditions / assignments 抽取逻辑

当遍历到：

- `IfStatement`
- `Assignment`

时，分别写入：

- `if_conditions`
- `assignments`

其主要用途是：

- 验证 gateway 的控制分支
- 验证 flow 中的状态推进
- 验证 `set` 动作是否落地

### 6.8 calls / requires / external_calls 抽取逻辑

当遍历到 `FunctionCall` 时，脚本统一先提取：

- `callee`
- `arguments`
- `function`

并写入 `calls`。

然后进一步分类：

- 若 `callee == require` 或 `assert`
  - 写入 `requires`
- 若 `callee` 看起来是成员访问或外部接口调用
  - 写入 `external_calls`

其中，`calls` 是当前 Solidity 语义校验的主证据来源，因为真实生成器中的关键调用通常表现为：

- `dmnLite.requestDMNDecision`
- `dmnLite.getRequestStatus`
- `dmnLite.getRawByRequestId`
- `oracle.getExternalData`
- `oracle.runComputeTask`

这使得后续规则能够区分：

- 普通函数调用
- 控制约束调用
- 外部依赖或 Oracle 调用

### 6.9 string_literals 抽取逻辑

当 AST 节点类型为 `Literal` 且值为字符串时，会写入：

- `string_literals`

主要用于：

- `decision` 标识匹配
- 业务规则证据补充

### 6.10 Solidity 抽取阶段的核心目标

Solidity AST 抽取的目标和 Go 侧一致，都是为了支撑：

1. 状态结构存在性验证
2. 函数结构存在性验证
3. 控制分支验证
4. 状态更新与外部调用验证

---

## 7. 报告生成逻辑

单 case 报告生成由：

- [verify_dsl_go_semantics.py](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/scripts/verify_dsl_go_semantics.py)
- [verify_dsl_sol_semantics.py](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/scripts/verify_dsl_sol_semantics.py)

负责。

这两个脚本的结构基本一致，只是目标 AST 不同。

### 7.1 元素遍历顺序

两个验证脚本都会按照同样的顺序遍历 DSL 元素：

1. `globals`
2. `participants`
3. `messages`
4. `gateways`
5. `events`
6. `businessrules`
7. `oracletasks`
8. `flows`

每个 DSL 元素都会生成一条验证记录。

### 7.2 append_result 机制

每条验证结果统一封装为：

- `element_name`
- `element_type`
- `matched`
- `evidence`
- `missing_reason`
- `severity`

这保证 Go 侧和 Solidity 侧的报告结构完全一致。

### 7.3 coverage 计算逻辑

`coverage()` 的逻辑非常直接：

- 如果某一类元素为空，返回 `1.0`
- 否则返回：
  - `matched_elements / total_elements`

它随后被用于计算：

- `dsl_element_coverage`
- `state_transition_preservation_rate`
- `branch_logic_preservation_rate`
- `businessrule_mapping_accuracy`

### 7.4 flow 标识命名

由于 `flow` 在 DSL 中不一定都有单独名称，因此当前实现会自动生成：

- `flow_<index>:<trigger_type>:<trigger_name>`

例如：

- `flow_1:start:StartEvent_0gb8jks`
- `flow_8:message:Message_12n6jjk`

这样可保证：

- 报告项有稳定标识
- 同一份 DSL 中的 flow 可以逐条追踪

### 7.5 汇总报告生成逻辑

批量汇总由：
[summary_report.py](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/scripts/summary_report.py)
负责。

它会读取每个 case 的：

- `dsl_ast.json`
- `dsl_go_report.json`
- `dsl_sol_report.json`

然后汇总出：

- DSL 元素数量
- Go coverage
- Solidity coverage
- 首个主要缺口说明

最终写出：

- `exp2_summary.json`
- `exp2_summary.md`

---

## 8. 基础匹配策略

### 8.1 名称标准化

当前实现中，所有规则先做名称标准化，再进行匹配：

- 转小写
- 非字母数字字符统一替换为 `_`
- 连续 `_` 折叠

对应实现位于：
[mapping_rules.py](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/scripts/mapping_rules.py)
中的 `normalize_name()`

这意味着以下名称会被视为等价或近似等价：

- `Message_01jq2zl`
- `message_01jq2zl`
- `Message-01jq2zl`

### 8.2 类型兼容规则

DSL 类型与目标语言类型不要求完全字面一致，而采用兼容映射：

| DSL 类型 | Go / Solidity 兼容类型 |
| --- | --- |
| `string` | `string`, `string memory` |
| `int` | `int`, `int256`, `int64`, `int32` |
| `bool` | `bool` |
| `float` | `float`, `float64`, `float32` |

对应实现：
`TYPE_ALIASES` + `compatible_type()`

### 8.3 证据优先

实验二不要求“唯一精确还原”每个 DSL 元素，而是要求找到**足够强的结构和控制语义证据**。

因此一个元素被判定为 `matched=true`，通常满足：

- 找到了目标代码中对应结构
- 找到了支撑该结构语义的控制逻辑或赋值证据

---

### 8.4 DSL 元素级映射规则概览

以下规则由 [mapping_rules.py](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/scripts/mapping_rules.py) 集中维护，并由：

- [verify_dsl_go_semantics.py](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/scripts/verify_dsl_go_semantics.py)
- [verify_dsl_sol_semantics.py](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/scripts/verify_dsl_sol_semantics.py)

逐项应用。

---

## 9. globals 映射规则

### 9.1 DSL 语义

DSL `globals` 表示流程运行过程中被共享、读写的全局状态变量。

### 9.2 Go 侧规则

判定条件：

1. 在 Go AST 的 `state_fields` 中存在同名字段
2. 字段类型与 DSL 类型兼容

主要证据：

- `StateMemory.<field_name> : <type>`

通过示例：

- DSL `Confirm: bool`
- Go `StateMemory.Confirm bool`

失败原因示例：

- `No matching field found in Go StateMemory.`
- `Field exists but type is not aligned.`

### 9.3 Solidity 侧规则

判定条件：

1. 在 Solidity AST 的 `state_variables` 中存在同名状态变量
2. 变量类型与 DSL 类型兼容

这里既允许：

- contract 顶层状态变量
- `StateMemory` 结构中的字段

主要证据：

- `StateMemory.<field_name> : <type>`
- `contract.<field_name> : <type>`

---

## 10. participants 映射规则

### 10.1 DSL 语义

DSL `participants` 表示流程参与方及其身份约束。

### 10.2 Go 侧规则

判定条件：

1. 参与者标识出现在 Go 代码字面量中
2. 存在参与方身份校验辅助逻辑

主要证据：

- 参与者名称出现在 `string_literals`
- 存在 `check_participant`
- 存在 `check_msp`

这表示：

- 参与方被实例化保留
- 调用者身份约束没有在代码生成阶段丢失

### 10.3 Solidity 侧规则

判定条件：

1. `ParticipantKey` 枚举中存在对应参与方
2. 存在 `_checkParticipant` 调用

主要证据：

- `ParticipantKey enum contains <participant>`
- `_checkParticipant(msg.sender/identity registry)`

这表示参与方标识与访问控制逻辑都被落地。

---

## 11. messages 映射规则

### 11.1 DSL 语义

DSL `message` 表示参与方之间的交互动作，通常伴随：

- 发送者 / 接收者约束
- 状态变化
- 流程推进

### 11.2 Go 侧规则

判定条件：

1. 存在对应消息处理函数
2. 函数中存在参与方校验
3. 函数中存在消息状态迁移

典型函数模式：

- `Message_xxx_Send`
- `Message_xxx_Complete`

主要证据：

- `function Message_xxx_Send`
- `function Message_xxx_Complete`
- `participant guard in message handler`
- `message state transition via ChangeMsgState`

### 11.3 Solidity 侧规则

判定条件：

1. 存在对应消息处理函数
2. 函数中存在 `_checkParticipant`
3. 函数中存在消息状态赋值

主要证据：

- `function Message_xxx_Send`
- `participant guard via _checkParticipant`
- `message state assignment in handler`

---

## 12. gateways 映射规则

### 12.1 DSL 语义

DSL `gateway` 表示控制分支语义，类型包括：

- `exclusive`
- `parallel`
- `event`

### 12.2 Go 侧规则

判定条件：

1. 存在同名 gateway 处理函数
2. 根据 gateway 类型找到对应控制结构证据

具体规则：

- `exclusive`
  - 需要存在 `if` 或 `switch`
- `parallel`
  - 需要存在等待多个前驱的联合条件
  - 当前实现用 `if` 条件中出现 `&&` 作为证据
- `event`
  - 需要存在分支消息推进逻辑
  - 当前实现以 `ChangeMsgState` 调用作为证据

主要证据：

- `exclusive gateway backed by conditional branch`
- `parallel join waits for multiple completed predecessors`
- `event gateway advances alternative message branches`

### 12.3 Solidity 侧规则

判定条件：

1. 存在同名 gateway 函数
2. 存在 `if` 或 `require` 等控制证据

具体规则：

- `exclusive`
  - `if_conditions` 非空
- `parallel`
  - `if` 或 `require` 条件中出现 `&&`
- `event`
  - `require` 中存在 gateway 状态约束证据

主要证据：

- `exclusive gateway backed by if branch`
- `parallel gateway requires multi-predecessor condition`
- `gateway guarded by runtime state check`

---

## 13. events 映射规则

### 13.1 DSL 语义

DSL `event` 表示流程起点或推进节点，语义上应体现：

- 事件触发
- 自身状态变化
- 对后续元素的激活

### 13.2 Go 侧规则

判定条件：

1. 存在对应事件函数
2. 存在 `ChangeEventState`
3. 存在对下游 message / gateway 的推进调用

主要证据：

- `event completion updates event state`
- `event triggers downstream state transition`

### 13.3 Solidity 侧规则

判定条件：

1. 存在对应事件函数
2. 存在事件状态变为 `COMPLETED` 的赋值
3. 存在对消息或网关的状态推进赋值

主要证据：

- `event state changes to COMPLETED`
- `event enables downstream message/gateway`

---

## 14. businessrules 映射规则

### 14.1 DSL 语义

DSL `businessrule` 表示规则处理节点，关键语义包括：

- 规则函数或接口存在
- 外部规则执行或 Oracle 调用存在
- `decision` / `dmn` / input-output mapping 证据被保留

### 14.2 Go 侧规则

判定条件：

1. 存在对应业务规则函数
2. 存在外部规则调用点
3. 若可能，保留 `decision` 或 mapping 相关字面量

当前主要证据：

- `Invoke_Other_chaincode`
- `oracle.`
- `decision id preserved in Go string literal`
- `mapping literal preserved for global <x>`

这意味着 Go 侧对 businessrule 的判定是：

- **函数存在**
- **外部规则执行存在**

只要这两点成立，就认为主要语义未丢失。

### 14.3 Solidity 侧规则

判定条件：

1. 存在对应业务规则函数
2. 存在 `IDmnLite` 请求或 continuation 调用
3. 若可能，保留 `decision` 字面量

当前主要证据：

- `dmnLite.requestDMNDecision`
- `dmnLite.getRequestStatus`
- `dmnLite.getRawByRequestId`
- `br.state = ElementState.WAITING_FOR_CONFIRMATION`
- `inst.stateMemory.<X> = ...`
- `decision id preserved in Solidity literal`

说明：

这里的判定逻辑是按 `b2cdsl-solidity` 当前真实实现定义的：

- 先在主函数中发起 DMN 请求
- 再在 `_Continue` 中轮询状态、获取结果
- 最后把输出写回 `StateMemory`

---

## 15. flows 映射规则

`flows` 是实验二中最重要的一组规则，因为它直接对应 DSL 的**控制语义**。

### 15.1 DSL 语义

每条 flow 被拆成：

- `trigger`
- `conditions`
- `actions`

其中：

- `trigger` 表示什么事件驱动流程推进
- `conditions` 表示分支条件或并行等待条件
- `actions` 表示 `enable / disable / set` 等动作

### 15.2 trigger 映射规则

当前实现中，会根据 trigger 类型推导代码中的候选函数名：

- `message + sent`
  - Go: `<Message>_Send`
  - Solidity: `<Message>_Send`
- `message + completed`
  - Go: `<Message>_Complete`
  - Solidity: 当前实现仍优先映射到 `<Message>_Send`
- `gateway`
  - `<GatewayName>`
- `event`
  - `<EventName>`
- `businessrule`
  - `<RuleName>` 或 `<RuleName>_Continue`
- `oracletask`
  - `<OracleTaskName>`
- `parallel`
  - `<GatewayName>`
- `start`
  - `<StartEventName>`

对应实现：
`flow_trigger_candidates()`

### 15.3 action 映射规则

#### A. enable / disable

DSL：

- `enable X`
- `disable X`

Go 侧判定为通过，当候选函数内存在以下调用之一：

- `ChangeMsgState(..., X, ENABLED / DISABLED)`
- `ChangeEventState(..., X, ENABLED / DISABLED)`
- `ChangeGtwState(..., X, ENABLED / DISABLED)`
- `ChangeBusinessRuleState(..., X, ENABLED / DISABLED)`

Solidity 侧判定为通过，当存在赋值：

- `<target>.state = ElementState.ENABLED`
- `<target>.state = ElementState.DISABLED`

#### B. set

DSL：

- `set GlobalVar = value`

Go 侧判定为通过，当满足以下任一条件：

1. 存在直接赋值，左值包含该全局变量
2. 存在 `SetGlobalVariable`
3. 存在 `FieldByName` + 目标全局变量名的反射更新

Solidity 侧判定为通过，当存在赋值：

- `stateMemory.<global> = <value>`

### 15.4 condition 映射规则

#### A. compare 条件

DSL gateway 分支中的：

- `if var == value`
- `if var != value`
- `if var > value`

Go / Solidity 侧判定为通过，当：

- 相关函数中的 `if` / `switch` / `require` 条件文本中出现对应变量

#### B. parallel await 条件

DSL：

- `parallel gateway X await A, B then ...`

当前实现中，若相关条件表达式中出现：

- `&&`

则作为“等待多个前驱同时满足”的证据。

### 15.5 flow 通过条件

一条 flow 被判定为 `matched=true`，当前要求：

1. 找到 trigger 对应的候选函数
2. flow 中的所有 action 都找到匹配证据
3. 若 flow 含条件，则条件证据也应被发现

因此，`flows` 是当前规则中最严格的一部分。

---

## 16. 判定结果结构

每个 DSL 元素都会生成一条统一记录：

```json
{
  "element_name": "Message_09krt7c",
  "element_type": "message",
  "matched": true,
  "evidence": [
    "function Message_09krt7c_Send",
    "participant guard in message handler",
    "message state transition via ChangeMsgState"
  ],
  "missing_reason": "",
  "severity": "medium"
}
```

字段含义如下：

- `element_name`
  - 当前 DSL 元素名称
- `element_type`
  - 元素类别，如 `global / message / flow`
- `matched`
  - 是否通过当前映射规则
- `evidence`
  - 支持通过判定的关键证据
- `missing_reason`
  - 未通过时的原因
- `severity`
  - 严重程度，当前主要用于报告展示

---

## 17. 指标计算规则

### 17.1 dsl_element_coverage

定义：

> 全部 DSL 元素中，被判定为 `matched=true` 的比例

计算范围包括：

- `global`
- `participant`
- `message`
- `gateway`
- `event`
- `businessrule`
- `flow`

### 17.2 state_transition_preservation_rate

定义：

> DSL `flow` 元素中，被成功匹配的比例

用于反映：

- 触发
- 状态迁移
- 变量更新

等控制推进语义的保真度。

### 17.3 branch_logic_preservation_rate

定义：

> DSL `gateway` 元素中，被成功匹配的比例

用于反映：

- `exclusive`
- `parallel`
- `event`

等控制分支逻辑是否被保留。

### 17.4 businessrule_mapping_accuracy

定义：

> DSL `businessrule` 元素中，被成功匹配的比例

用于反映：

- 规则节点是否存在
- 外部规则调用是否存在
- 输入输出映射证据是否保留

---

## 18. 当前规则的特点与局限

### 18.1 特点

- 规则清晰，可解释
- 每条规则都能落到具体 AST 字段或调用证据
- 不依赖修改主工程
- 对 Go 侧适配较好
- 对论文实验和回归验证比较友好

### 18.2 局限

- Solidity 侧当前规则偏保守，容易漏判
- 某些 `businessrule` 映射可能以较隐式方式保存，当前不一定都能识别
- `message completed` 在 Solidity 侧当前仍较难统一建模
- `parallel await` 目前主要依赖 `&&` 证据，属于保守近似
- 规则仍然是“基于静态结构和控制语义证据”的验证，不是运行时语义等价证明

---

## 19. 文档与代码对应关系

若需要查看当前规则的真实实现位置，可参考：

- 规则定义：
  [mapping_rules.py](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/scripts/mapping_rules.py)
- Go 侧报告生成：
  [verify_dsl_go_semantics.py](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/scripts/verify_dsl_go_semantics.py)
- Solidity 侧报告生成：
  [verify_dsl_sol_semantics.py](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/scripts/verify_dsl_sol_semantics.py)
- 实验总控：
  [run_exp2.py](/root/code/ChainCollab/Experiment/new/exp2_semantic_verification/scripts/run_exp2.py)

---

## 20. 一句话总结

实验二当前采用的是一种：

**“DSL 元素级结构匹配 + 类型兼容匹配 + 控制语义证据匹配”**

的静态校验规则体系。

它不试图证明目标代码与 DSL 完全语义等价，但能够较稳定地验证：

**DSL 中最关键的结构、状态、分支、规则调用与流程推进语义，是否在 Go 和 Solidity 代码中被保留下来。**
