# 实验 1C：BPMN→DSL 源目标行为一致性验证详细实验方案（B 方案）

## 0. 实验定位

实验 1C 验证的是 **BPMN 源模型与 DSL 目标模型之间的行为语义是否一致**。具体做法是：分别将 BPMN 源模型和 DSL 目标模型映射到统一行为迁移系统（Unified Behavioral Transition System, UBTS）的 JSON 实现，分别生成有界 trace 集合，再通过 trace 集合双向包含、步骤级状态迁移比较和终态比较，判断 BPMN 与 DSL 的行为是否一致。

当前实现已经按该原则修正：`build_bpmn_semantic_graph.py` 直接从 BPMN XML 构建 BPMN 侧 UBTS，`build_dsl_semantic_graph.py` 从 `translator/dsl.b2c` 构建 DSL 侧 UBTS。两侧不再共用由 DSL 反推的同源 UBTS，因此 1C 的比较能够暴露 BPMN→DSL 转换中的行为丢失或额外行为。

有界 trace 集合一致性要求：

```text
BPMN 可产生的有界 trace，DSL 中也能产生；
DSL 可产生的有界 trace，BPMN 中也能产生。
```

因此，1C 的实验链路是：

```text
BPMN 源模型
   ↓ newTranslator：模型转换
DSL 目标模型
   ↓ 1B：结构可追踪
BPMN / DSL canonical UBTS JSON implementation
   ↓ 1C：bounded trace 集合与步骤级状态迁移一致
behavior_summary / path_set_comparison / step_trace_comparison
```

实验 1C 的核心作用是证明：由 `newTranslator` 从 BPMN 案例转换得到的 DSL，不仅在结构上可追踪，而且在有界 trace 和步骤级状态迁移上与源 BPMN 保持一致。

在核心行为一致性验证之外，1C 可以附加生成 `logical_path.json` 格式的路径产物。该产物只用于保持路径表示与后续运行时实验兼容，不作为 1C 的主要证明结果，也不写入或修改其他实验目录。

------

## 1. 实验目标

### 1.1 核心问题

实验 1C 回答以下问题：

> BPMN 源模型经过转换得到 DSL 目标模型后，其可执行行为路径是否被完整、正确地保留？

具体拆成三个子问题：

1. **trace 集合是否一致？** BPMN 生成的有界 trace 集合与 DSL 生成的有界 trace 集合是否相等。
2. **trace 步骤是否一致？** 对应 trace 中的每一步触发元素、执行前可用集合、状态变化、业务变量变化是否一致。
3. **终态是否一致？** 同一条 trace 执行完成后，BPMN 与 DSL 是否进入相同的终止状态、元素状态集合和可触发集合。

### 1.2 能证明什么

如果实验通过，可以证明：

```text
在给定路径深度、循环展开次数和输入空间约束下，
BPMN 源模型与 DSL 目标模型具有一致的有界行为语义。
```

附加的 `logical_path.json` 只提供统一路径格式：

```text
1C 只验证 BPMN 与 DSL 的源目标行为一致性；
行为一致性报告是核心结果；
logical_path.json 是附加格式化产物；
平台代码执行、Fabric/Geth 轨迹采集和三方比较不属于 1C。
```

### 1.3 不能证明什么

1C 不证明无限 trace 完全等价。由于 BPMN 可能存在循环，实验采用有界 trace 枚举，因此结论是 **bounded behavioral consistency**。

1C 不证明 Go 或 Solidity 代码正确，这属于后续代码生成与运行时实验。

1C 不证明运行时性能，这不在当前三部分实验范围内。

------

## 2. 输入与输出总览

### 2.1 输入文件

```text
输入 1：BPMN 源模型
/root/code/ChainCollab/Experiment/BPMNwithDMNcase/<CaseName>.bpmn

输入 2：newTranslator 转换配置或转换命令
/root/code/ChainCollab/src/newTranslator/

输入 3：newTranslator 生成的 DSL 目标模型
/root/code/ChainCollab/Experiment/new/exp1_1C/cases/<CaseName>/translator/dsl.b2c

输入 4：1B 结构映射结果
/root/code/ChainCollab/Experiment/new/exp1_1B/cases/<CaseName>/trace/bpmn_dsl_trace.json

输入 5：路径枚举配置
Experiment/new/exp1_1C/cases/<CaseName>/config/path_bound_config.json
```

其中 `bpmn_dsl_trace.json` 来自实验 1B，用于统一 BPMN 和 DSL 的元素标识，避免两个模型虽然语义相同但 ID 或类型名称不同导致误判。

### 2.2 核心输出文件

以下产物用于证明 BPMN→DSL 行为一致性，是 1C 的主要实验结果：

```text
输出 1：BPMN 统一行为迁移系统 JSON 实现
Experiment/new/exp1_1C/cases/<CaseName>/semantic/bpmn.semantic_graph.json

输出 2：DSL 统一行为迁移系统 JSON 实现
Experiment/new/exp1_1C/cases/<CaseName>/semantic/dsl.semantic_graph.json

输出 3：BPMN 有界 trace 集合
Experiment/new/exp1_1C/cases/<CaseName>/paths/bpmn.paths.json

输出 4：DSL 有界 trace 集合
Experiment/new/exp1_1C/cases/<CaseName>/paths/dsl.paths.json

输出 5：规范化后的 BPMN trace 集合
Experiment/new/exp1_1C/cases/<CaseName>/normalized/bpmn.normalized_paths.json

输出 6：规范化后的 DSL trace 集合
Experiment/new/exp1_1C/cases/<CaseName>/normalized/dsl.normalized_paths.json

输出 7：trace 集合比较结果
Experiment/new/exp1_1C/cases/<CaseName>/comparison/path_set_comparison.json

输出 8：步骤级轨迹比较结果
Experiment/new/exp1_1C/cases/<CaseName>/comparison/step_trace_comparison_summary.json

输出 9：实验报告
Experiment/new/exp1_1C/cases/<CaseName>/reports/behavior_summary.json
Experiment/new/exp1_1C/cases/<CaseName>/reports/behavior_summary.md
```

### 2.3 附加输出文件

以下产物不参与 1C 的行为一致性结论，只用于把已通过验证的路径保存为兼容的路径格式：

```text
附加输出 1：logical_path 格式的行为路径产物
Experiment/new/exp1_1C/cases/<CaseName>/logical_paths/<PathName>/logical_path.json

附加输出 2：logical_path 格式产物生成报告
Experiment/new/exp1_1C/cases/<CaseName>/logical_paths/logical_path_generation_report.json
```

------

## 3. 核心设计思想

实验 1C 的关键不是直接比较 BPMN XML 和 DSL 文本，而是把二者都映射到同一个形式语义域中。本文采用统一行为迁移系统（Unified Behavioral Transition System, UBTS）作为工程化语义表示。UBTS 不是新的流程建模语言，而是对标号迁移系统、带守卫状态迁移系统以及 BPMN token-based execution semantics 的工程化实例。

统一语义表示包括四层：

```text
UBTS / GLSTS：统一行为迁移系统
Path / Trace：有界执行路径及其动作标签序列
TraceStep：单步状态迁移
NormalizedTrace：规范化轨迹
```

整体过程如下：

```text
BPMN XML
  → BPMN UBTS JSON implementation
  → BPMN bounded traces
  → BPMN normalized traces
  → path set / step trace comparison

DSL Model
  → DSL UBTS JSON implementation
  → DSL bounded traces
  → DSL normalized traces
  → path set / step trace comparison
```

核心比较完成后，可以把通过 BPMN 与 DSL 双方验证的路径附加写入 1C 自身的 `logical_path.json` 格式产物。

### 3.1 理论基础：基于带守卫标号状态迁移系统的统一语义域

标号迁移系统（Labeled Transition System, LTS）通常用状态、动作标签和迁移关系描述系统的可观察行为。BPMN 与 DSL 在语法层面差异较大，不能直接比较 XML 结构、DSL 文本或局部连接关系，因此需要先把二者映射到同一个形式语义域中，再比较二者在该语义域中的行为。

实验 1C 不仅需要描述动作序列，还需要描述分支条件、状态更新、业务变量和执行前后的 enabled set。因此，本文采用 LTS 的扩展形式，即带守卫状态迁移系统（Guarded State Transition System, GSTS）/ 带守卫标号状态迁移系统（Guarded Labeled State Transition System, GLSTS），并在工程实现中称为统一行为迁移系统（Unified Behavioral Transition System, UBTS）。其中：

```text
状态用于表示流程元素标记和业务变量；
动作标签用于表示触发的 event、message、gateway、businessrule 等业务动作；
guard 描述迁移可执行条件；
effect 描述迁移执行后的元素状态和业务变量更新；
enabled set 描述某一状态下当前可触发的流程元素集合。
```

BPMN 的 token-flow / enabled-set 执行直觉可以映射为 UBTS 中的元素状态和迁移规则。例如，某个 BPMN 元素被启用可以表示为该元素处于 `READY` 状态；元素触发后进入 `DONE`；后继元素是否变为 `READY` 由 BPMN 的 sequence flow、message flow、gateway 条件和 join 规则共同决定。DSL 中的 `flows`、guard、output 和状态推进关系也被映射到同一类状态、动作、守卫和效果结构中。

在这个统一语义域中：

```text
trace 集合双向包含对应 bounded trace equivalence；
步骤级轨迹比较对应 bounded step-wise transition preservation；
终态比较对应 final-state preservation。
```

因此，1C 的比较是在相同边界条件下对两个有界迁移系统进行 bounded trace comparison，并进一步检查每一步状态迁移是否保持。

------

## 4. 统一语义模型定义

### 4.1 统一行为迁移系统定义

本文将 BPMN 和 DSL 都映射为统一行为迁移系统（UBTS）。UBTS 是带守卫标号状态迁移系统（GLSTS）的工程化表示。为了区分模型结构中抽取出的迁移模板和运行时实际可执行迁移，形式化定义为：

```text
UBTS = (P, N, S, A, R, T, s0, F, V, guard, effect, type)
```

其中：

| 符号 | 含义 |
| ---- | ---- |
| `P` | 参与者集合，对应 BPMN participant 以及 DSL participants，用于消息端点、身份元数据和多实例上下文 |
| `N` | 可触发流程元素集合，例如 event、message、gateway、businessrule、oracletask |
| `S` | 运行状态集合，状态由元素标记和业务变量估值共同组成 |
| `A` | 动作标签集合，对应触发元素或业务动作 |
| `R` | 迁移模板集合，从 BPMN sequence/message/gateway 结构或 DSL flows 中静态抽取 |
| `T` | 运行时迁移关系，由 `R` 在具体状态下经 guard 判定和 effect 应用后诱导得到，`T ⊆ S × A × S` |
| `s0` | 初始状态 |
| `F` | 终止状态集合 |
| `V` | 业务变量集合 |
| `guard` | 迁移守卫条件 |
| `effect` | 迁移产生的状态更新 |
| `type` | 节点类型函数，用于区分 event、message、gateway、businessrule 等 |

其中运行状态 `s ∈ S` 定义为：

```text
s = (μ, ν)
```

`μ` 是元素标记函数，记录每个可触发流程元素 `n ∈ N` 当前处于 `INIT`、`READY`、`PENDING_CONFIRMATION`、`DONE`、`INACTIVE` 等状态；`ν` 是业务变量估值函数，记录变量集合 `V` 中每个业务变量的当前取值。参与者 `P` 不进入 enabled set，也不作为动作标签触发，但作为 message 的 sender/receiver、身份属性和多实例上下文参与语义解释。

运行时迁移关系 `T` 不是直接从文件中静态读取的边集合，而是由迁移模板 `R` 在状态 `s=(μ,ν)` 上动态诱导：当某个模板 `r ∈ R` 的触发元素在 `μ` 中处于 enabled / READY，且 `guard(r)` 在 `ν` 下为真时，执行 `effect(r)` 产生新状态 `s'=(μ',ν')`，从而得到一条运行时迁移 `(s, a, s') ∈ T`。

实验产物中的 `semantic_graph.json` 是该形式语义模型的 JSON 实现形式，而不是新的理论模型。文件中的 `participants`、`nodes`、`transitions`、`start_nodes` 和 `end_nodes` 分别对应 UBTS 的工程化表示：`participants` 对应 `P`，`nodes` 对应 `N`，`transitions` 对应迁移模板集合 `R`，`start_nodes` 用于构造初始状态 `s0`，`end_nodes` 用于判断终止状态集合 `F`。运行时迁移关系 `T` 由路径生成器根据 `transitions`、当前状态、`guard` 和 `effect` 动态计算。

建议格式：

```json
{
  "case_name": "SupplyChainPaper",
  "model_type": "bpmn",
  "participants": [
    {
      "id": "Participant_1",
      "name": "Buyer",
      "is_multi": false,
      "metadata": {
        "msp": "BuyerMSP",
        "attributes": {
          "role": "Buyer"
        }
      }
    }
  ],
  "nodes": [
    {
      "id": "Event_06sexe6",
      "type": "start_event",
      "name": "Start"
    },
    {
      "id": "Message_1wswgqu",
      "type": "message",
      "name": "SubmitOrder",
      "sender": "Participant_1",
      "receiver": "Participant_2",
      "schema": {}
    }
  ],
  "transitions": [
    {
      "id": "t_001",
      "source": "Event_06sexe6",
      "target": "Message_1wswgqu",
      "trigger": "Message_1wswgqu",
      "guard": null,
      "effect": {
        "Event_06sexe6": ["READY", "DONE"],
        "Message_1wswgqu": ["INIT", "READY"]
      },
      "relation_type": "sequence"
    }
  ],
  "start_nodes": ["Event_06sexe6"],
  "end_nodes": ["Event_13pbqdz"]
}
```

字段含义如下：

| JSON 字段 | UBTS 对应含义 |
| --------- | ------------- |
| `participants` | 对应参与者集合 `P`，保存 sender/receiver、MSP、X509、多实例和属性等上下文 |
| `nodes` | 对应可触发流程元素集合 `N`，并通过节点 `type` 标记元素类型 |
| `transitions` | 对应迁移模板集合 `R`，从 BPMN / DSL 模型结构中静态抽取 |
| `trigger` | 对应动作标签集合 `A` 中的动作 |
| `guard` | 对应迁移条件，决定某一迁移在当前状态下是否可执行 |
| `effect` | 对应状态更新函数，用于从 `s=(μ,ν)` 计算后继状态 `s'=(μ',ν')` |
| `start_nodes` | 用于构造初始状态 `s0` |
| `end_nodes` | 用于判断终止状态集合 `F` |

### 4.1.1 newTranslator 参与元素覆盖范围

实验 1C 的 UBTS 映射需要覆盖 `newTranslator` 从 BPMN 解析并写入 B2CDSL 的主要元素。覆盖范围如下：

| newTranslator 来源 | B2CDSL 区块 | UBTS / 语义角色 |
| ------------------ | ----------- | --------------- |
| `participant` | `participants` | 参与者集合 `P`，作为 message sender/receiver、身份属性和多实例上下文 |
| message / messageFlow | `messages` | 可触发节点 `N` 中的 message；messageFlow 提供 sender、receiver 和 message 绑定 |
| message documentation schema | `messages.schema`、`globals` | payload 字段和业务变量集合 `V` 的来源 |
| startEvent / endEvent | `events` | start event 构造 `s0`；end event 用于判断 `F` |
| exclusiveGateway | `gateways`、`flows.choose` | guard 分支和互斥迁移模板 `R` |
| eventBasedGateway | `gateways(type=event)`、`disable/enable` flow | 事件竞争分支；被选分支启用时禁用其他候选分支 |
| parallelGateway | `gateways(type=parallel)`、`parallel gateway await` | 并行 split / join 迁移模板；join 需要多个前驱均完成 |
| choreographyTask | `messages`、`flows` | 被转换为发起消息和可选返回消息的推进关系 |
| businessRuleTask | `businessrules`、`globals`、`flows` | DMN 输入/输出映射，完成后更新业务变量并启用后继 |
| receiveTask | `oracletasks(type=external-data)` | 外部数据 oracle task，完成后更新 output mapping 并启用后继 |
| scriptTask | `oracletasks(type=compute-task)` | 计算型 oracle task，完成后更新 output mapping 并启用后继 |
| sequenceFlow condition | `globals`、`flows.choose` | guard 条件和比较字面量，参与 trace 分支选择 |
| flow actions | `flows` | `enable`、`disable`、`set` 对应 effect 中的元素状态和变量更新 |

其中 `participants`、message schema 和身份属性属于语义上下文，不作为 enabled set 中的可触发节点；message、event、gateway、businessrule 和 oracletask 才进入元素标记函数 `μ`。这样可以覆盖转换器参与元素，同时避免把参与者误解释为运行时动作。

### 4.2 Path

`Path` 表示一条抽象业务路径，也是 bounded trace 的工程化输入形式。它保留动作标签序列对应的执行元素顺序和必要输入，用于后续 trace 枚举、规范化和轨迹回放。

```json
{
  "path_id": "bpmn_path_001",
  "steps": [
    {
      "element": "Event_06sexe6",
      "type": "event"
    },
    {
      "element": "Message_1wswgqu",
      "type": "message",
      "payload": {}
    }
  ]
}
```

### 4.3 TraceStep

`TraceStep` 表示路径执行中的一步状态迁移。

```json
{
  "trigger": "Message_1wswgqu",
  "enabled_before": ["Message_1wswgqu"],
  "guard_result": true,
  "state_diff": {
    "Message_1wswgqu": ["READY", "DONE"]
  },
  "global_diff": {},
  "enabled_after": ["Gateway_1fbifca"]
}
```

### 4.4 NormalizedTrace

`NormalizedTrace` 是用于比较的统一轨迹格式，也可以与 `logical_path.json` 路径格式保持同一套字段口径。

```json
{
  "schema_version": "exp1c.normalized_trace.v1",
  "model_type": "bpmn",
  "case_name": "SupplyChainPaper",
  "path_id": "bpmn_path_001",
  "trace_signature": "9c1d9b31049d2e69",
  "steps": [],
  "final_state": {
    "status": "COMPLETED",
    "element_states": {},
    "enabled_elements": [],
    "globals": {}
  }
}
```

------

## 5. 路径有界策略

### 5.1 为什么需要有界

BPMN 和 DSL 都可能包含循环、回退或重复执行逻辑。如果直接枚举所有 trace，trace 集合可能是无限的。因此实验 1C 采用有界 trace 枚举。

### 5.2 建议配置

`path_bound_config.json`：

```json
{
  "max_depth": 20,
  "max_loop_unroll": 2,
  "max_paths": 200,
  "include_invalid_paths": false,
  "parallel_policy": "interleaving_canonical",
  "guard_policy": "symbolic_label",
  "dmn_policy": "decision_table_rows",
  "dmn_output_bound": 20,
  "dmn_fallback_policy": "fixed_sample"
}
```

### 5.3 配置含义

| 参数                    | 作用                 | 为什么必要                      |
| ----------------------- | -------------------- | ------------------------------- |
| `max_depth`             | 限制单条路径最大长度 | 防止路径爆炸                    |
| `max_loop_unroll`       | 限制循环展开次数     | 保证循环模型可分析              |
| `max_paths`             | 限制最大路径数量     | 控制实验时间                    |
| `include_invalid_paths` | 是否生成非法路径     | 1C 主要验证合法路径，默认 false |
| `parallel_policy`       | 并行路径规范化策略   | 避免并发交错导致误判            |
| `guard_policy`          | 分支条件比较策略     | 统一 BPMN 条件与 DSL guard      |
| `dmn_policy`            | DMN 输出枚举策略     | businessrule 输出会影响业务变量和后续 guard |
| `dmn_output_bound`      | DMN 输出组合上限     | 防止决策表行或输出组合过多导致 trace 爆炸 |
| `dmn_fallback_policy`   | DMN 不可解析时的降级策略 | 保证缺少 DMN 文件或复杂决策时仍可形成可复现实验输入 |

### 5.4 DMN 策略

实验 1C 需要考虑 DMN 策略，但 DMN 不是 1C 的独立验证目标。1C 不验证 DMN 决策表本身的业务正确性，也不比较不同 DMN 引擎的执行结果；1C 只要求 BPMN 侧和 DSL 侧在**相同 DMN 输出策略**下进行 bounded trace 枚举和步骤级轨迹比较。

推荐默认策略为：

```text
dmn_policy = decision_table_rows
```

当前实现采用工程化的 `decision_table_rows` 近似策略：从已发现的 DMN 文件中读取 decision output 名称和 outputEntry 取值，形成代表性输出估值集合，并在执行 businessrule 时写回对应 global 变量。如果 businessrule 的输出变量会被后续 gateway guard 使用，则不同 DMN 输出会诱导不同后续 trace，因此必须纳入路径生成输入空间。

需要注意，当前实现不是完整 DMN 引擎：它不根据输入条件精确命中某一条规则，而是枚举决策表中出现过的代表性输出值。该策略用于覆盖由 DMN 输出导致的流程分支差异，而不验证 DMN 决策表本身的业务正确性。

DMN 策略可分为以下几类：

| 策略 | 含义 | 适用场景 |
| ---- | ---- | -------- |
| `decision_table_rows` | 按 DMN 决策表规则行枚举代表性输出 | 默认策略，覆盖业务规则导致的分支差异 |
| `symbolic_outputs` | 按输出变量类型枚举代表性符号值，例如 bool 的 true/false | DMN 文件不可直接解析但输出类型已知 |
| `fixed_sample` | 使用固定样例输出 | 最小实现或 smoke test |
| `external_mock` | 从外部 mock 文件读取 businessrule 输入/输出 | 需要复现实验数据或人工指定边界时 |

执行到 businessrule 节点时，路径生成器应按以下规则处理：

```text
1. 根据 case 的 BPMN 文件发现同目录 DMN 文件，包含去掉空格、下划线等非字母数字字符后的同名匹配，例如 `Pizza_Order.bpmn` 对应 `PizzaOrder.dmn`。
2. 从 DMN decision output / outputEntry 中提取代表性输出值。
3. 执行 businessrule 时，将 output mapping 写回业务变量估值 `ν`，形成后继状态 `s'=(μ',ν')`。
4. 如果输出变量影响后续 gateway guard，则继续按不同 `ν'` 枚举后续 traces。
5. BPMN UBTS 和 DSL UBTS 使用同一组 DMN 输出估值进行比较。
```

因此，DMN 策略是 trace 生成的输入空间约束，而不是额外实验边界。当前实验已采用上述代表性 outputEntry 枚举方式，并用 `dmn_output_bound` 控制组合规模；完整 DMN 条件求值仍属于暂缓范围。

------

## 6. 实验步骤详解

## Step 0：准备实验目录和配置

### 做什么

为每个 Case 建立 1C 实验目录，准备 `newTranslator` 转换配置和路径枚举配置。

### 输入

```text
/root/code/ChainCollab/Experiment/BPMNwithDMNcase/<CaseName>.bpmn
/root/code/ChainCollab/src/newTranslator/
/root/code/ChainCollab/Experiment/new/exp1_1B/cases/<CaseName>/trace/bpmn_dsl_trace.json
```

### 输出

```text
Experiment/new/exp1_1C/cases/<CaseName>/config/path_bound_config.json
Experiment/new/exp1_1C/cases/<CaseName>/config/run_config.json
```

### 中间产物

```json
{
  "case_name": "SupplyChainPaper",
  "bpmn_file": ".../SupplyChainPaper.bpmn",
  "translator_root": ".../src/newTranslator",
  "dsl_file": ".../Experiment/new/exp1_1C/cases/SupplyChainPaper/translator/dsl.b2c",
  "trace_file": ".../bpmn_dsl_trace.json",
  "bound_config": ".../path_bound_config.json"
}
```

### 为什么必要

统一目录和配置可以保证不同案例使用相同实验口径，避免每个模型单独手工设置导致结果不可复现。

### 能证明什么

这一步本身不证明一致性，但它证明实验具有可重复的输入边界和配置条件。

------

## Step 1：使用 newTranslator 生成 DSL 目标模型

### 做什么

调用 `newTranslator`，将 BPMN 案例转换为 DSL 目标模型，并把转换产物固定保存到 1C 的 case 目录中。

### 输入

```text
/root/code/ChainCollab/Experiment/BPMNwithDMNcase/<CaseName>.bpmn
/root/code/ChainCollab/src/newTranslator/
Experiment/new/exp1_1C/cases/<CaseName>/config/run_config.json
```

### 输出

```text
Experiment/new/exp1_1C/cases/<CaseName>/translator/dsl.b2c
Experiment/new/exp1_1C/cases/<CaseName>/translator/newtranslator_report.json
```

### 为什么必要

1C 验证的是 BPMN 经转换得到 DSL 后的源目标行为一致性，因此 DSL 输入必须来自同一个 BPMN 案例的 `newTranslator` 转换结果，而不是复用其他实验目录中的 DSL 文件。

### 能证明什么

这一步本身不证明行为一致性，但它固定了“源 BPMN → 目标 DSL”的生成关系，保证后续比较对象确实来自待验证的转换链路。

------

## Step 2：解析 BPMN 源模型

### 做什么

读取 BPMN XML，提取与行为相关的元素和关系。

需要提取的 BPMN 元素包括：

```text
Participant
StartEvent
EndEvent
IntermediateEvent
ChoreographyTask / Task / BusinessRuleTask
ReceiveTask
ScriptTask
ExclusiveGateway
ParallelGateway
EventBasedGateway
SequenceFlow
MessageFlow
ConditionExpression
Message documentation / task documentation
ParticipantRef / initiatingParticipantRef
```

### 输入

```text
/root/code/ChainCollab/Experiment/BPMNwithDMNcase/<CaseName>.bpmn
```

### 输出

```text
Experiment/new/exp1_1C/cases/<CaseName>/raw/bpmn.raw_elements.json
Experiment/new/exp1_1C/cases/<CaseName>/raw/bpmn.raw_relations.json
```

### 为什么必要

BPMN XML 是建模语言层面的源文件，不能直接用于 bounded trace comparison。必须先抽取行为相关元素，去掉图形坐标、样式、无关扩展字段等信息。

### 能证明什么

这一步证明 BPMN 源模型中的行为元素和行为关系被完整识别，为后续映射到统一形式语义域提供基础。

------

## Step 3：将 BPMN 映射为统一行为迁移系统

### 做什么

直接解析 BPMN XML，将 BPMN 原始元素和关系映射为统一行为迁移系统（UBTS / GLSTS）的 JSON 实现，即 `bpmn.semantic_graph.json`。该步骤不读取 `translator/dsl.b2c`，避免 BPMN 侧和 DSL 侧同源导致比较失效。

转换规则示例：

| BPMN 元素                      | UBTS / GLSTS 表示         |
| ------------------------------ | ------------------------ |
| Participant                    | participant context `P`  |
| StartEvent                     | start node               |
| EndEvent                       | end node                 |
| MessageFlow / ChoreographyTask | message node             |
| BusinessRuleTask               | businessrule node        |
| ReceiveTask                    | oracletask node, type external-data |
| ScriptTask                     | oracletask node, type compute-task |
| ExclusiveGateway               | exclusive gateway node   |
| EventBasedGateway              | event gateway node       |
| ParallelGateway                | parallel split/join node |
| SequenceFlow                   | transition               |
| ConditionExpression            | guard                    |
| Message sender/receiver        | participant context and transition metadata |
| Message / task documentation   | schema, globals, DMN/oracle mappings |

### 输入

```text
/root/code/ChainCollab/Experiment/BPMNwithDMNcase/<CaseName>.bpmn
```

### 输出

```text
Experiment/new/exp1_1C/cases/<CaseName>/semantic/bpmn.semantic_graph.json
```

### 为什么必要

BPMN 原始结构不等于执行语义。比如网关、消息流、业务规则、并行 join 都需要解释为带守卫的状态迁移规则。当前实现从 BPMN XML 直接构建这套迁移系统，使 BPMN 能与 DSL 进入同一个统一形式语义域。

### 能证明什么

这一步证明 BPMN 源模型可以被解释为同一形式语义域中的可比较迁移系统。真正的行为一致性由后续 trace 集合双向包含和步骤级轨迹比较证明。

------

## Step 4：解析 DSL 目标模型

### 做什么

读取由 `newTranslator` 生成的 DSL 文件，提取 DSL 中的元素、flows、guards、outputs、状态推进关系等。

需要提取的 DSL 内容包括：

```text
participant
participant attributes / msp / x509 / isMulti / multiMin / multiMax
global
event
message
message sender / receiver / schema
gateway
businessrule
oracletask
flow / enable relation
guard
output
state update
set global operation
```

### 输入

```text
Experiment/new/exp1_1C/cases/<CaseName>/translator/dsl.b2c
```

### 输出

```text
Experiment/new/exp1_1C/cases/<CaseName>/raw/dsl.raw_elements.json
Experiment/new/exp1_1C/cases/<CaseName>/raw/dsl.raw_relations.json
```

### 为什么必要

DSL 是转换后的目标模型。1C 需要检查的不是代码执行结果，而是 DSL 本身是否保留了 BPMN 行为。因此必须从 DSL 中独立抽取行为信息。

### 能证明什么

这一步证明 DSL 中存在可用于行为分析的结构化执行信息。

------

## Step 5：将 DSL 映射为统一行为迁移系统

### 做什么

直接读取 `translator/dsl.b2c`，将其中的元素、`flows`、guard、output 和状态推进关系映射为统一行为迁移系统（UBTS / GLSTS）的 JSON 实现，即 `dsl.semantic_graph.json`。`raw/dsl.raw_elements.json` 和 `raw/dsl.raw_relations.json` 会作为可复查的抽取产物保留，但当前 UBTS 构建以 `dsl.b2c` 为真实输入。

其中 `participants` 和 `globals` 需要作为 UBTS 的上下文一起保留：`participants` 构成参与者集合 `P`，用于解释 message 的 sender/receiver 和多实例身份属性；`globals` 构成业务变量集合 `V`，用于解释 guard、set action、businessrule output 和 oracletask output。message、event、gateway、businessrule、oracletask 则映射为可触发流程元素集合 `N`。

### 输入

```text
Experiment/new/exp1_1C/cases/<CaseName>/translator/dsl.b2c
```

### 输出

```text
Experiment/new/exp1_1C/cases/<CaseName>/semantic/dsl.semantic_graph.json
```

### 为什么必要

BPMN 和 DSL 的语法不同，不能直接比较。只有映射到统一形式语义域后，才能比较二者诱导出的有界 trace 集合、状态迁移和终态。

### 能证明什么

这一步证明 DSL 目标模型可以被解释为同一形式语义域中的可比较迁移系统。真正的行为一致性由后续 trace 集合双向包含和步骤级轨迹比较证明。

------

## Step 6：利用 1B 映射统一元素标识

### 做什么

使用实验 1B 输出的 `bpmn_dsl_trace.json`，记录 BPMN UBTS 和 DSL UBTS 的元素可追踪关系，并生成 canonical 版本的语义图。

当前 11 个 case 中，BPMN XML 与 newTranslator 生成的 DSL 已基本保留相同的行为元素 ID，因此当前实现主要把 semantic graph 原样写入 canonical 目录，并在 `canonicalization` 字段和 `id_normalization_report.json` 中记录 1B trace 来源与映射数量。也就是说，canonicalization 当前是显式标注与可追溯确认，不是复杂 ID 重写。

例如：

```text
BPMN: MessageFlow_001
DSL : Message_1wswgqu
统一为 canonical_id: Message_1wswgqu
```

### 输入

```text
bpmn.semantic_graph.json
dsl.semantic_graph.json
bpmn_dsl_trace.json
```

### 输出

```text
Experiment/new/exp1_1C/cases/<CaseName>/canonical/bpmn.semantic_graph.canonical.json
Experiment/new/exp1_1C/cases/<CaseName>/canonical/dsl.semantic_graph.canonical.json
Experiment/new/exp1_1C/cases/<CaseName>/canonical/id_normalization_report.json
```

### 为什么必要

如果不做 ID 统一，bounded trace comparison 可能把语义相同但 ID 不同的元素误判为不一致。1C 的行为比较必须建立在 1B 的结构可追踪基础上。

### 能证明什么

这一步证明 BPMN 与 DSL 的行为元素具备可追踪对应关系；在当前数据集中也确认了两侧行为元素 ID 已可直接比较。

------

## Step 7：从 BPMN UBTS 生成有界 trace 集合

### 做什么

基于 BPMN UBTS / GLSTS 诱导出的有界迁移系统进行 bounded trace 枚举。这里生成的是动作标签序列及其对应状态序列。若 trace 执行到 businessrule 节点，应按照 `path_bound_config.json` 中的 `dmn_policy` 生成 DMN 输出估值，并写回业务变量估值 `ν`。

搜索规则：

```text
1. 当前状态中某元素处于 enabled / READY 时才允许触发。
2. guard 为真时迁移可执行。
3. 触发动作标签后执行 effect，更新元素状态和业务变量。
4. 后继元素的 enabled set 由 sequence flow、message flow、gateway 和 join 规则共同决定。
5. ExclusiveGateway 只选择一个满足条件的分支。
6. ParallelGateway split 同时启用多个分支。
7. ParallelGateway join 只有当前置分支全部 DONE 后才能触发。
8. BusinessRuleTask 按统一 DMN 策略更新输出变量，后续 guard 在更新后的 ν 上求值。
9. 到达 EndEvent 或达到边界条件时结束。
```

### 输入

```text
bpmn.semantic_graph.canonical.json
path_bound_config.json
```

### 输出

```text
Experiment/new/exp1_1C/cases/<CaseName>/paths/bpmn.paths.json
Experiment/new/exp1_1C/cases/<CaseName>/paths/bpmn.path_generation_report.json
```

### 为什么必要

1C 需要证明 BPMN 的行为没有在 DSL 中丢失。因此必须从 BPMN 端独立生成 trace 集合，而不能只依赖 DSL 生成 trace。

### 能证明什么

这一步证明 BPMN 源模型诱导出的 UBTS 在给定边界下有哪些可执行 bounded traces。

------

## Step 8：从 DSL UBTS 生成有界 trace 集合

### 做什么

基于 DSL UBTS / GLSTS 诱导出的有界迁移系统，使用与 BPMN 相同的路径边界、guard 求值策略、DMN 输出策略和 effect 更新规则，枚举 DSL 的合法 bounded trace 集合。

### 输入

```text
dsl.semantic_graph.canonical.json
path_bound_config.json
```

### 输出

```text
Experiment/new/exp1_1C/cases/<CaseName>/paths/dsl.paths.json
Experiment/new/exp1_1C/cases/<CaseName>/paths/dsl.path_generation_report.json
```

### 为什么必要

仅从 BPMN 生成 trace 无法发现 DSL 中额外产生的非法行为。必须从 DSL 端独立枚举 trace，才能检查 DSL 是否引入了 BPMN 中不存在的行为。

### 能证明什么

这一步证明 DSL 目标模型诱导出的 UBTS 在给定边界下有哪些可执行 bounded traces。

------

## Step 9：trace 规范化

### 做什么

对 BPMN trace 和 DSL trace 进行规范化，消除语法层面的差异，只保留语义相关信息。

当前实现中，主要规范化工作已经在 UBTS 构建、canonical semantic graph 和 trace 生成阶段完成，因此 Step 9 是轻量落盘步骤：将 `paths/bpmn.paths.json` 和 `paths/dsl.paths.json` 原样保存为 `normalized/bpmn.normalized_paths.json` 和 `normalized/dsl.normalized_paths.json`，并生成 `path_normalization_report.json`。该步骤保留为独立环节，是为了让比较输入和后续实验产物边界更清晰。

规范化内容包括：

```text
1. 使用 canonical semantic graph 中的元素 ID 和类型。
2. 保留 trace steps、states、final_state 等比较所需字段。
3. 生成规范化输入文件，供 path set comparison 和 step trace comparison 使用。
4. 非语义字段，例如图形坐标、注释、XML 顺序，已经在 BPMN/DSL UBTS 构建阶段被排除。
```

### 输入

```text
bpmn.paths.json
dsl.paths.json
id_normalization_report.json
path_bound_config.json
```

### 输出

```text
Experiment/new/exp1_1C/cases/<CaseName>/normalized/bpmn.normalized_paths.json
Experiment/new/exp1_1C/cases/<CaseName>/normalized/dsl.normalized_paths.json
Experiment/new/exp1_1C/cases/<CaseName>/normalized/path_normalization_report.json
```

### 为什么必要

BPMN 和 DSL 的执行表示可能存在细节差异。当前实现把这些差异前移到 UBTS 构建和 canonicalization 阶段处理，Step 9 负责固定比较输入，避免后续步骤直接读取生成路径时边界不清。

### 能证明什么

这一步证明比较对象已经被规约到相同语义层面，后续差异更可能是真正的行为差异，而不是表示差异。

------

## Step 10：有界 trace 集合双向包含比较

### 做什么

比较两个规范化后的有界 trace 集合：

```text
BPMN traces ⊆ DSL traces
DSL traces ⊆ BPMN traces
```

具体检查：

```text
1. 每条 BPMN trace 是否存在等价 DSL trace。
2. 每条 DSL trace 是否存在等价 BPMN trace。
3. 两边 trace 数量是否一致。
4. 两边 trace_signature 是否一致。
5. 如果不一致，输出 missing / extra / mismatch。
```

这里的 `BPMN traces ⊆ DSL traces` 与 `DSL traces ⊆ BPMN traces` 是对两个有界 trace 集合做双向包含检查，对应 bounded trace equivalence。比较对象是由动作标签序列、规范化元素 ID、guard 标签和必要输入共同构成的有界 trace 表示。

`trace_signature` 是用于集合比较的规范化 trace 标识，建议定义为：

```text
trace_signature =
  hash([
    (step_index,
     canonical_element_id,
     action_type,
     normalized_guard_label,
     normalized_payload_shape,
     normalized_outputs)
  ])
```

其中 `canonical_element_id` 来自 canonical semantic graph，`action_type` 对应 event、message、gateway、businessrule 等动作类型，`normalized_guard_label` 是规范化后的 guard 标识，`normalized_payload_shape` 只保留影响分支和状态更新的输入字段结构或符号取值，`normalized_outputs` 用于区分 businessrule / oracle task 产生的不同业务变量结果。`trace_signature` 不包含 BPMN XML 顺序、图形坐标、注释、原始 ID 差异等非语义字段。

由于工程产物需要与既有路径文件命名保持兼容，部分文件名仍沿用 `paths`，但其语义是 UBTS 诱导出的 bounded traces。

### 输入

```text
bpmn.normalized_paths.json
dsl.normalized_paths.json
```

### 输出

```text
Experiment/new/exp1_1C/cases/<CaseName>/comparison/path_set_comparison.json
Experiment/new/exp1_1C/cases/<CaseName>/comparison/path_set_comparison.md
```

### 为什么必要

这是 B 方案的核心。只有做 bounded trace 集合双向包含，才能同时发现两类错误：

```text
BPMN 有但 DSL 没有：转换丢失行为。
DSL 有但 BPMN 没有：转换引入额外行为。
```

### 能证明什么

如果双向包含成立，可以证明 BPMN 与 DSL 在给定边界下具有相同的可执行 trace 集合，即 bounded trace equivalence 成立。

------

## Step 11：生成步骤级标准化轨迹

### 做什么

对 BPMN 和 DSL 的 normalized paths 生成步骤级 `NormalizedTrace` 文件。当前实现的 `simulate_traces()` 一次性处理两侧路径，虽然脚本入口保留 `simulate_bpmn_trace.py` 和 `simulate_dsl_trace.py` 两个名称，但 pipeline 中调用一次即可同时生成 BPMN 与 DSL 两边的 trace 文件。

trace 集合一致只对应 trace-level equivalence。为了进一步检查每一步迁移是否真正保持，需要保留每条路径执行过程中已经计算出的迁移前后状态信息。

每一步记录：

```text
enabled_before
trigger
guard_result
state_diff
global_diff
enabled_after
final_state
```

### 输入

```text
bpmn.normalized_paths.json
dsl.normalized_paths.json
```

### 输出

```text
Experiment/new/exp1_1C/cases/<CaseName>/traces/bpmn/<PathName>/bpmn.normalized.json
Experiment/new/exp1_1C/cases/<CaseName>/traces/dsl/<PathName>/dsl.normalized.json
```

### 为什么必要

trace 集合一致只能证明 trace-level equivalence，不能证明每一步的状态变化一致。比如两个模型动作标签序列相同，但 DSL 可能提前启用了某个后继节点，或者漏掉了某个状态更新。

### 能证明什么

这一步为 bounded step-wise transition preservation 检查提供证据。

------

## Step 12：步骤级轨迹比较

### 做什么

对每一对匹配路径，比较 BPMN trace 与 DSL trace。

当前实现不单独落盘 `matched_paths.json`。`compare_step_traces()` 直接读取 `normalized/bpmn.normalized_paths.json` 和 `normalized/dsl.normalized_paths.json`，按 `trace_signature` 找到双方匹配路径，然后比较双方的 `steps` 和 `final_state`。因为 `steps` 中已经包含触发元素、payload、guard、sender/receiver、businessrule outputs 等动作信息，`final_state` 中包含元素状态、全局变量和最终 enabled set，所以该步骤可以检查有界范围内的 step-wise transition preservation 和 final-state preservation。

比较字段包括：

| 字段 | 比较目的 |
| ---- | -------- |
| `steps` | 动作序列、触发元素、类型、guard、payload、outputs、sender/receiver 是否一致 |
| `final_state.element_states` | 终态元素状态是否一致 |
| `final_state.globals` | 终态业务变量是否一致 |
| `final_state.enabled` | 执行完成后的可触发集合是否一致 |

### 输入

```text
bpmn.normalized_paths.json
dsl.normalized_paths.json
```

### 输出

```text
Experiment/new/exp1_1C/cases/<CaseName>/comparison/traces/<PathName>/trace_comparison.json
Experiment/new/exp1_1C/cases/<CaseName>/comparison/traces/<PathName>/trace_comparison.md
Experiment/new/exp1_1C/cases/<CaseName>/comparison/step_trace_comparison_summary.json
```

### 为什么必要

有界 trace 集合比较发现的是宏观可观察行为是否一致，步骤级轨迹比较进一步检查每一步状态迁移是否保持。两者缺一不可。

### 能证明什么

如果所有匹配 trace 的步骤级轨迹一致，可以证明 DSL 不仅保持了 BPMN 的 bounded trace equivalence，也在当前抽象粒度下保持了动作序列、guard / payload / outputs 和 final state。

------

## Step 13：生成行为一致性报告

### 做什么

汇总每个 Case 的 1C 结果，生成可读、可复查、可统计的实验报告。

### 输入

```text
path_set_comparison.json
step_trace_comparison_summary.json
```

### 输出

```text
Experiment/new/exp1_1C/cases/<CaseName>/reports/behavior_summary.md
Experiment/new/exp1_1C/cases/<CaseName>/reports/behavior_summary.json
Experiment/new/exp1_1C/reports/all_cases_behavior_summary.csv
Experiment/new/exp1_1C/reports/all_cases_behavior_summary.md
```

### 报告内容

```text
1. BPMN bounded trace 数量
2. DSL bounded trace 数量
3. bounded trace equivalence 是否成立
4. step-wise transition preservation 是否成立
5. logical_path 格式路径导出数量
6. case 是否通过
```

更细的 missing / extra trace 信息保存在 `comparison/path_set_comparison.json` 中；每条匹配 trace 的步骤级比较结果保存在 `comparison/step_trace_comparison_summary.json` 和 `comparison/traces/<bpmn_path_id>/trace_comparison.json` 中。

### 为什么必要

实验不能只保留程序中间输出，还需要给出跨案例的统计结果和差异摘要，便于复查行为一致性结论。

### 能证明什么

这一步从多个案例层面证明 BPMN→DSL 的行为一致性不是单个示例偶然成立，而是在测试集上稳定成立。

------

## 附加 Step A：生成 `logical_path.json` 格式产物

### 做什么

将通过 1C 验证的匹配路径转换为 `logical_path.json` 格式产物。这里仅复用 `logical_path` 的数据格式，不写入其他实验目录，也不处理 Fabric/Geth 平台执行所需的运行时参数。

这一步是附加产物生成步骤，不参与 1C 行为一致性是否通过的核心判断。

只有满足以下条件的路径才能生成 `logical_path.json`：

```text
1. trace_signature 在 BPMN 和 DSL 中都存在。
2. step trace comparison 通过。
3. final_state comparison 通过。
```

### 输入

```text
normalized/dsl.normalized_paths.json
step_trace_comparison_summary.json
```

### 输出

```text
Experiment/new/exp1_1C/cases/<CaseName>/logical_paths/<PathName>/logical_path.json
Experiment/new/exp1_1C/cases/<CaseName>/logical_paths/logical_path_generation_report.json
```

### `logical_path.json` 格式要求

1C 生成的 `logical_path.json` 应与现有 `logical_path` 路径文件保持字段兼容，至少包含：

```json
{
  "case_name": "Purchase",
  "path_name": "Purchase_dsl_path_001",
  "description": "Auto materialized from BPMN/DSL consistent path by exp1_1C.",
  "source_model": "Experiment/new/exp1_1C/cases/Purchase/translator/dsl.b2c",
  "expect": "accepted",
  "steps": [
    {
      "type": "message",
      "element": "Message_0q9hvem",
      "payload": {}
    }
  ],
  "generated_path": {
    "final_enabled_elements": [],
    "final_element_states": {},
    "final_globals": {}
  }
}
```

字段含义如下：

| JSON 字段 | 含义 |
| --------- | ---- |
| `case_name` | 案例名称，用于标识该路径所属 BPMN / DSL case |
| `path_name` | 路径产物名称，对应 1C 中通过验证的 matched trace |
| `description` | 路径来源说明，仅描述该文件由 1C 的一致 trace 格式化生成 |
| `source_model` | 生成该路径的 DSL 文件位置，通常指向 1C case 目录下的 `translator/dsl.b2c` |
| `expect` | 该路径的预期接受结果；1C 只导出通过验证的合法路径，因此通常为 `accepted` |
| `steps` | 由 matched trace 转换得到的动作序列，每一步包含动作类型、规范化元素 ID 以及必要 payload |
| `steps[].type` | 对应 UBTS 动作标签的类型，例如 event、message、gateway、businessrule |
| `steps[].element` | canonical semantic graph 中的元素 ID |
| `steps[].sender` / `steps[].receiver` | 可选字段，用于保留 message step 的 participant 端点上下文 |
| `steps[].payload` / `outputs` | 触发该步骤所需的业务输入或业务规则输出，来自 trace 枚举和步骤级回放 |
| `generated_path.final_enabled_elements` | trace 执行完成后的 enabled set |
| `generated_path.final_element_states` | trace 执行完成后的元素标记 `μ` |
| `generated_path.final_globals` | trace 执行完成后的业务变量估值 `ν` |

其中 `steps` 来自 BPMN 与 DSL 双方均通过验证的 matched trace；`generated_path` 来自步骤级轨迹比较通过后的终态信息。1C 不在该文件中加入平台部署信息、交易账户信息或链上调用脚本。

### 为什么必要

这一步保证 1C 的附加路径产物与后续运行时实验使用的 `logical_path` 数据格式一致，避免后续再做一套路径格式转换。

### 能证明什么

这一步不额外证明行为一致性；行为一致性已经由 bounded trace 集合比较、步骤级轨迹比较和行为报告证明。它只说明生成的 `logical_path.json` 格式路径来自已经通过验证的 BPMN / DSL 一致 trace。

------

## 7. 推荐脚本设计

建议新增以下脚本：

```text
Experiment/new/exp1_1C/scripts/
  run_newtranslator.py
  extract_bpmn_raw.py
  build_bpmn_semantic_graph.py
  extract_dsl_raw.py
  build_dsl_semantic_graph.py
  normalize_semantic_ids.py
  generate_bpmn_paths.py
  generate_dsl_paths.py
  normalize_paths.py
  compare_path_sets.py
  simulate_bpmn_trace.py
  simulate_dsl_trace.py
  compare_step_traces.py
  summarize_behavior_results.py
  generate_logical_paths.py
```

| 脚本                            | 职责                           |
| ------------------------------- | ------------------------------ |
| `run_newtranslator.py`          | 调用 newTranslator 生成 DSL 目标模型 |
| `extract_bpmn_raw.py`           | 从 BPMN XML 抽取原始元素和关系 |
| `build_bpmn_semantic_graph.py`  | 直接从 BPMN XML 构建 BPMN UBTS / GLSTS JSON 实现 |
| `extract_dsl_raw.py`            | 从 DSL 抽取原始元素和关系      |
| `build_dsl_semantic_graph.py`   | 将 DSL 映射为 UBTS / GLSTS 的 JSON 实现 |
| `normalize_semantic_ids.py`     | 利用 1B 映射统一 ID            |
| `generate_bpmn_paths.py`        | 从 BPMN UBTS 中枚举 bounded traces |
| `generate_dsl_paths.py`         | 从 DSL UBTS 中枚举 bounded traces |
| `normalize_paths.py`            | 规范化路径表示                 |
| `compare_path_sets.py`          | 比较 bounded trace 集合双向包含 |
| `simulate_bpmn_trace.py`        | 执行 BPMN 路径并生成标准化轨迹 |
| `simulate_dsl_trace.py`         | 执行 DSL 路径并生成标准化轨迹  |
| `compare_step_traces.py`        | 比较 BPMN 与 DSL 步骤级轨迹    |
| `summarize_behavior_results.py` | 汇总实验结果                   |
| `generate_logical_paths.py`     | 附加生成 logical_path 格式路径产物 |

------

## 8. 推荐目录结构

```text
Experiment/new/exp1_1C/
  scripts/
  reports/
    all_cases_behavior_summary.csv
  cases/
    <CaseName>/
      config/
        run_config.json
        path_bound_config.json
      translator/
        dsl.b2c
        newtranslator_report.json
      raw/
        bpmn.raw_elements.json
        bpmn.raw_relations.json
        dsl.raw_elements.json
        dsl.raw_relations.json
      semantic/
        bpmn.semantic_graph.json
        dsl.semantic_graph.json
      canonical/
        bpmn.semantic_graph.canonical.json
        dsl.semantic_graph.canonical.json
        id_normalization_report.json
      paths/
        bpmn.paths.json
        dsl.paths.json
        bpmn.path_generation_report.json
        dsl.path_generation_report.json
      normalized/
        bpmn.normalized_paths.json
        dsl.normalized_paths.json
        path_normalization_report.json
      traces/
        bpmn/bpmn_path_001/bpmn.normalized.json
        dsl/dsl_path_001/dsl.normalized.json
      comparison/
        path_set_comparison.json
        path_set_comparison.md
        step_trace_comparison_summary.json
        traces/bpmn_path_001/trace_comparison.json
      reports/
        behavior_summary.json
        behavior_summary.md
      logical_paths/
        <CaseName>_dsl_path_001/logical_path.json
        logical_path_generation_report.json
```

------

## 9. 判断标准

### 9.1 通过标准

一个 Case 通过 1C，需要同时满足：

```text
1. BPMN UBTS / GLSTS JSON 实现构建成功。
2. DSL UBTS / GLSTS JSON 实现构建成功。
3. semantic graph 已写入 canonical 目录，并记录 1B trace 映射来源。
4. BPMN bounded traces ⊆ DSL bounded traces。
5. DSL bounded traces ⊆ BPMN bounded traces。
6. 所有匹配 trace 的 step-wise transition preservation 检查通过。
7. 所有匹配 trace 的 final-state preservation 检查通过。
```

### 9.2 失败类型

| 失败类型                  | 含义                                         |
| ------------------------- | -------------------------------------------- |
| `MISSING_PATH_IN_DSL`     | BPMN 有 bounded trace 但 DSL 没有，说明转换丢失行为 |
| `EXTRA_PATH_IN_DSL`       | DSL 有 bounded trace 但 BPMN 没有，说明转换引入额外行为 |
| `STEP_TRIGGER_MISMATCH`   | 对应步骤触发元素不同                         |
| `ENABLED_BEFORE_MISMATCH` | 执行前可触发集合不同                         |
| `GUARD_RESULT_MISMATCH`   | 分支条件判断不同                             |
| `STATE_DIFF_MISMATCH`     | 状态变化不同                                 |
| `FINAL_STATE_MISMATCH`    | 终态不同                                     |
| `ID_TRACE_MISSING`        | 1B 映射文件缺失或映射数量异常                 |

------

## 10. 附加产物与 `logical_path` 格式的对应关系

1C 暂时不处理平台执行部分。行为一致性报告是 1C 的核心产物；`logical_path.json` 是附加产物，只要求行为路径产物采用兼容格式。这样后续实验如果需要复用路径，可以直接读取同一格式，而不需要重新定义路径结构。

| 1C 产物                              | 在 1C 中的作用                         | 对应意义                         |
| ------------------------------------ | -------------------------------------- | -------------------------------- |
| `bpmn.normalized_paths.json`         | 证明 bounded trace 可由 BPMN 源模型产生 | 保证源模型行为存在               |
| `dsl.normalized_paths.json`          | 证明 bounded trace 可由 newTranslator 生成的 DSL 产生 | 保证目标模型行为存在             |
| `path_set_comparison.json`           | 筛选 BPMN 与 DSL 双方一致的 bounded traces | 排除缺失 trace 和额外 trace      |
| `step_trace_comparison_summary.json` | 筛选步骤级状态迁移一致的 traces        | 证明 step-wise transition preservation |
| `logical_path.json`                  | 1C 附加路径格式产物                    | 与后续运行时实验保持路径格式兼容 |
| `bpmn_dsl_trace.json`                | 解释路径元素的源目标映射来源           | 证明路径元素可追溯到 BPMN        |

1C 中的逻辑关系是：

```text
newTranslator：BPMN 案例如何得到 DSL？
1B：路径元素从哪里来？
1C：路径行为在 BPMN 和 DSL 中是否一致？
logical_path.json：附加把一致路径保存成统一格式。
```

------

## 11. 最小可实现版本

如果时间有限，B 方案可以先实现一个最小闭环版本。

### 必做

```text
1. newTranslator DSL generation
2. BPMN UBTS / GLSTS JSON implementation
3. DSL UBTS / GLSTS JSON implementation
4. canonical semantic graph generation with 1B trace source recorded
5. BPMN bounded trace generation
6. DSL bounded trace generation
7. outputEntry-based DMN output enumeration
8. normalized trace signature
9. bounded trace set bidirectional comparison
10. behavior summary generation
```

### 附加

```text
1. logical_path.json generation
```

### 暂缓

```text
1. 完整 global_diff 比较
2. 复杂表达式等价求解
3. 多实例循环完整展开
4. 高级并发交错覆盖
5. 完整 DMN 条件求值和组合覆盖
```

### 最小结论

最小版本可以证明：

```text
在给定边界和规范化规则下，BPMN 与 DSL 的 bounded trace 集合一致。
```

完整版本进一步证明：

```text
在 bounded trace 集合一致的基础上，BPMN 与 DSL 的步骤级状态迁移也一致。
```

------

## 12. 1C B 方案一句话总结

实验 1C 的 B 方案本质上是：

```text
让 BPMN 和 DSL 各自独立“说出自己能怎么走”，
再把两边说出的 bounded trace 集合和每一步状态变化放到同一语义格式下比较。
```

如果两边 bounded trace 集合双向包含成立，且每条匹配 trace 的步骤级轨迹和终态一致，就可以证明 BPMN→DSL 转换在有界范围内保持了源模型的行为语义。
