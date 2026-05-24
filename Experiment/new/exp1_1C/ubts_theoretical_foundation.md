# UBTS 统一行为迁移系统的理论来源与采用理由

本文档用于支撑实验 1C，解释为什么在 BPMN->DSL 源目标行为一致性验证中采用 UBTS，即 Unified Behavioral Transition System，统一行为迁移系统。

本文中的 UBTS 不是临时自造的流程建模语言，而是对标号迁移系统（Labeled Transition System, LTS）、带守卫状态迁移系统（Guarded State Transition System, GSTS）、带守卫标号状态迁移系统（Guarded Labeled State Transition System, GLSTS）以及 BPMN token-based execution semantics 的工程化采用。实验 1C 将 BPMN 源模型和 DSL 目标模型都映射到 UBTS，是为了在统一的行为语义域上执行有界 trace 枚举、路径集合双向包含、步骤级迁移保持和终态保持检查。

## 1. UBTS 的基本含义

UBTS 是 Unified Behavioral Transition System 的缩写，可翻译为“统一行为迁移系统”。

在实验 1C 中，一个 UBTS 由以下信息组成：

```text
participants：流程参与者上下文；
nodes：可触发流程元素；
states：运行时状态；
actions：动作标签；
transition templates：从模型结构中抽取出的迁移模板；
runtime transitions：在具体状态下实际可执行的迁移；
guards：迁移守卫；
effects：迁移效果；
initial state：初始状态；
final states：终止状态集合；
business variables：业务变量。
```

因此，实验 1C 中的 UBTS 可写为：

```text
UBTS = (P, N, S, A, R, T, s0, F, V, guard, effect, type)
```

其中：

```text
P 表示参与者集合，例如 customer、supplier、carrier；
N 表示流程元素集合，例如 event、message、gateway、businessrule、oracletask；
S 表示运行状态集合；
A 表示动作标签集合；
R 表示迁移模板集合；
T 表示运行时迁移关系；
s0 表示初始状态；
F 表示终止状态集合；
V 表示业务变量集合；
guard 表示迁移守卫条件；
effect 表示迁移产生的状态更新；
type 表示节点类型函数。
```

实验 1C 中的 UBTS 是一种行为语义中间表示，用于比较 BPMN 与 DSL 的可执行行为，不等同于 BPMN 标准本身，也不等同于 DSL 语法本身。

## 2. 理论来源一：LTS 用状态和迁移描述系统行为

标号迁移系统（LTS）是描述离散系统行为的经典形式。一个基础 LTS 通常可以写为：

```text
LTS = (S, A, T, s0)
```

其中：

```text
S 表示状态集合；
A 表示动作标签集合；
T ⊆ S × A × S 表示迁移关系；
s0 表示初始状态。
```

LTS 的基本思想是：

```text
系统处于某个状态；
执行某个动作；
系统进入下一个状态。
```

BPMN 和 DSL 都可以从执行角度理解为这种状态迁移系统：

```text
某个 event 被触发；
某个 message 被完成；
某个 gateway 被求值；
某个 businessrule 产生输出；
某个后继元素变为 enabled。
```

因此，用状态迁移系统表示 BPMN 和 DSL 的行为，是进行行为一致性验证的自然选择。

## 3. 理论来源二：Guarded Transition System 支持条件分支

基础 LTS 只描述动作和状态变化，但实验 1C 需要处理大量条件逻辑，例如：

```text
if Confirm == true then enable Message_A;
if FinalPriority == "High" then enable Message_B;
if InvoiceAvailable == false then enable EndEvent_C;
```

这些行为不能只靠动作标签表达，还需要引入 guard，即迁移守卫。

因此，实验 1C 使用 LTS 的扩展形式：带守卫状态迁移系统。其直觉是：

```text
只有当当前状态满足 guard 时，迁移才可执行；
迁移执行后，effect 更新元素状态和业务变量。
```

对应到实验实现：

```text
guard_result = true
  -> 迁移可执行；

guard_result = false
  -> 迁移不可执行。
```

这使得 exclusive gateway、event-based gateway、DMN 输出分支和 DSL `choose` 分支都可以在统一语义域中处理。

## 4. 理论来源三：GLSTS 同时保留动作标签与状态更新

实验 1C 不仅要知道“状态能否到达”，还要知道“通过哪个动作到达”。因此，UBTS 实际采用的是带守卫标号状态迁移系统（GLSTS）的思想：

```text
(s, a, g, e, s')
```

其中：

```text
s 表示迁移前状态；
a 表示动作标签；
g 表示守卫条件；
e 表示状态更新效果；
s' 表示迁移后状态。
```

实验 1C 中的路径不是普通图路径，而是 trace：

```text
trace = [(s0, a1, s1), (s1, a2, s2), ..., (sn-1, an, sn)]
```

每个动作标签 `a` 对应一个可触发流程元素，例如：

```text
Event_1jtgn3j
Message_045i10y
ExclusiveGateway_106je4z
Activity_0ibsbry
```

因此，实验 1C 关注的是“带状态变化的动作序列”，而不是单纯的节点列表。

## 5. 理论来源四：BPMN token-based execution semantics

BPMN 的执行语义通常可以通过 token-flow 直觉理解：

```text
开始事件产生 token；
token 沿 sequence flow / message flow 推进；
任务、事件、网关在满足条件时被启用；
元素执行后 token 继续流向后继元素；
终止事件消费 token 并结束流程路径。
```

实验 1C 将这种执行直觉工程化为 UBTS 中的元素标记：

```text
READY：元素当前 enabled，可以触发；
DONE：元素已经触发完成；
INACTIVE：元素当前不可触发；
PENDING_CONFIRMATION：元素等待确认或外部输入。
```

于是 BPMN token-flow 可以映射为：

```text
token 到达元素
  -> 元素状态变为 READY；

元素执行完成
  -> 元素状态变为 DONE；

后继元素被启用
  -> 后继元素状态变为 READY；

互斥分支未选中
  -> 未选中元素保持 INACTIVE 或被 disable。
```

这种映射使 BPMN 的执行语义可以和 DSL 的 `flows`、`enable`、`disable`、`choose`、`businessrule` 语义在同一套状态迁移系统中比较。

## 6. 状态 S 的定义：元素标记与业务变量估值

实验 1C 中的状态不是单一节点位置，而是由两部分组成：

```text
s = (μ, ν)
```

其中：

```text
μ：元素标记函数，记录每个流程元素的状态；
ν：业务变量估值函数，记录 DSL globals / BPMN 派生变量的当前值。
```

例如：

```text
μ(Message_045i10y) = DONE
μ(ExclusiveGateway_106je4z) = READY
ν(Is_available) = true
ν(InvoiceAvailable) = false
```

这种状态定义是必要的，因为实验 1C 需要同时比较：

```text
1. 哪些元素当前 enabled；
2. 哪些元素已经完成；
3. guard 依赖的业务变量是否保持；
4. DMN 输出是否正确写回变量；
5. 终态时元素状态和业务变量是否一致。
```

如果只记录“当前节点”，就无法表达并行、互斥、event-based gateway、DMN 输出和业务变量驱动分支。

## 7. 迁移模板 R 与运行时迁移关系 T 的区分

实验 1C 明确区分迁移模板 `R` 和运行时迁移关系 `T`。

`R` 来自模型结构，是静态信息，例如：

```text
when message Message_045i10y completed
then enable Message_0r9lypd;

when gateway Gateway_0ivv4vg completed choose {
  if Confirm == false then enable Message_1b1qlzd;
  if Confirm == true then enable Message_01jq2zl;
}
```

`T` 是在具体状态下由 `R`、`guard` 和 `effect` 动态诱导出来的实际迁移：

```text
T ⊆ S × A × S
```

也就是说，同一个迁移模板不一定总是可执行：

```text
如果触发元素不是 READY，则不可执行；
如果 guard 为 false，则不可执行；
如果 parallel join 的前驱尚未全部 DONE，则不可执行。
```

这种区分避免把模型结构图误认为运行时行为图。实验 1C 生成路径时，枚举的是运行时可执行 traces，而不是对 `transitions` 字段做普通 DFS。

## 8. DMN 策略与 businessrule 迁移

实验 1C 中的 businessrule 节点通常依赖 DMN 决策表。DMN 不作为独立验证目标，而是作为路径生成时的输入空间策略。

实验实现采用有界 DMN 输出枚举：

```text
dmn_policy = decision_table_rows
dmn_output_bound = 20
dmn_fallback_policy = fixed_sample
```

当 trace 执行到 businessrule 节点时：

```text
读取 businessrule 的 output mapping；
读取对应 DMN 决策表的 outputEntry；
枚举有限个可能输出；
将输出写回业务变量估值 ν；
再继续执行后继 gateway guard。
```

例如：

```text
confirm -> Confirm
externalAvailable -> ExternalAvailable
invoiceAvailable -> InvoiceAvailable
finalPriority -> FinalPriority
```

这使得 DSL 中由 DMN 输出驱动的分支可以被 UBTS trace 枚举覆盖。

## 9. 为什么不直接比较 BPMN XML 和 DSL 文本

如果直接比较 BPMN XML 与 DSL 文本，会遇到几个问题：

```text
1. 两者语法完全不同；
2. BPMN 的 messageFlow 在 DSL 中可能表现为 message sender / receiver；
3. BPMN 的 sequenceFlow 在 DSL 中可能表现为 enable / disable；
4. BPMN 的 businessRuleTask 在 DSL 中表现为 businessrule + DMN mapping；
5. gateway 行为依赖运行时 guard，不是文本片段；
6. 行为一致性关注的是可执行路径，而不是文本顺序。
```

例如：

```text
BPMN 中一个 exclusiveGateway 的多个 outgoing sequenceFlow，
在 DSL 中可能被转换为 choose 分支。
```

两者文本不同，但行为可能一致。UBTS 的作用就是把这种语法差异规整为：

```text
相同的状态空间；
相同的动作标签；
相同的 guard 判断；
相同的 effect 更新；
相同的终止条件。
```

## 10. 为什么不只用普通图结构

普通图结构可以表达节点和边，但实验 1C 验证的是“运行时行为”，不是“静态连接关系”。

普通图 DFS 只能回答：

```text
从节点 A 是否能沿边走到节点 B。
```

但实验 1C 需要回答：

```text
当前状态下 A 是否 enabled；
guard 是否为 true；
effect 是否正确更新业务变量；
并行 join 是否满足；
event-based gateway 是否正确禁用未选分支；
终态状态是否一致。
```

因此，UBTS 不是“自定义行为图”，也不是简单图结构比较。它是对 LTS/GSTS/GLSTS 的工程化 JSON 实现，用来枚举和比较有状态 traces。

## 11. 为什么不只用 Petri Net

Petri Net 很适合描述 token 流、并发和同步，因此也常用于 BPMN 形式化语义研究。但实验 1C 没有直接采用完整 Petri Net，原因是：

```text
1. 实验需要同时保留 BPMN 与 DSL 的动作标签；
2. 实验需要直接表达 DSL globals、guard、set action、DMN output；
3. 实验需要产出可读的 step trace 和 logical_path.json；
4. 实验目标是转换结果行为一致性验证，而不是对 BPMN 本身做 Petri Net 可达性分析。
```

UBTS 可以吸收 token-flow 的核心直觉，同时以更贴近当前 DSL 运行模型的方式表示：

```text
enabled set；
guard；
effect；
business variables；
trace signature；
final state。
```

因此，UBTS 是实验 1C 中更轻量、更直接的中间表示。

## 12. UBTS 与 trace_signature 的关系

实验 1C 不直接用路径文件名或数组下标判断两条路径是否相同，而是为 trace 构造 `trace_signature`。

`trace_signature` 由以下信息归一化得到：

```text
动作标签序列；
节点类型序列；
guard 序列；
payload shape；
businessrule / oracletask outputs。
```

其目的不是做密码学证明，而是为 BPMN trace 与 DSL trace 提供稳定、可计算的匹配键。

如果两个 trace 的 `trace_signature` 相同，说明二者在实验关注的行为观测维度上相同：

```text
执行了相同类型的动作；
经过了相同分支条件；
产生了相同业务输出；
具有可比较的路径结构。
```

后续仍需要步骤级迁移比较确认 enabled set、state diff、enabled_after 和 final_state 是否保持。

## 13. UBTS 与实验 1C 三类证明目标的对应关系

| 实验目标 | 依赖的 UBTS 信息 | 说明 |
|---|---|---|
| bounded trace equivalence | `S, A, T, s0, F` | 比较 BPMN 与 DSL 在有界范围内生成的 trace 集合是否双向包含 |
| step-wise transition preservation | `enabled_before, guard, effect, state_diff, enabled_after` | 检查每个对应迁移是否保持 |
| final-state preservation | `F, μ, ν` | 检查路径结束时元素状态和业务变量估值是否一致 |

可以看到，如果没有 UBTS：

```text
无法知道某一步是否 enabled；
无法统一解释 BPMN gateway 与 DSL choose；
无法比较 DMN 输出对业务变量的影响；
无法判断两个路径的终态是否一致；
无法将 BPMN 与 DSL 的行为规整到同一语义域。
```

因此，UBTS 是实验 1C 指标可计算化的基础。

## 14. UBTS 与 semantic_graph.json 的关系

实验实现中，UBTS 被落地为 JSON 文件。由于工程产物需要兼容早期命名，文件名仍保留 `semantic_graph.json`：

```text
bpmn.semantic_graph.json
dsl.semantic_graph.json
```

需要注意：

```text
semantic_graph.json 不是新的理论模型；
semantic_graph.json 是 UBTS / GLSTS 的工程化 JSON 实现。
```

JSON 中的字段与 UBTS 的关系如下：

| JSON 字段 | UBTS 对应含义 |
|---|---|
| `participants` | 参与者集合 `P` |
| `nodes` | 流程元素集合 `N` |
| `globals` | 业务变量集合 `V` |
| `dmn_outputs` | DMN 有界输出估值空间 |
| `transitions` | 迁移模板集合 `R` |
| `start_nodes` | 用于构造初始状态 `s0` |
| `end_nodes` | 用于判断终止状态集合 `F` |
| `state_model` | 元素标记 `μ` 的取值空间 |

运行时迁移关系 `T` 不直接静态存储在 JSON 中，而是在路径生成时由以下信息动态诱导：

```text
当前状态 s；
迁移模板 R；
触发元素 enabled 状态；
guard 求值；
effect 状态更新；
DMN 输出策略。
```

## 15. UBTS 与实验 1B TAG 的关系

实验 1B 和实验 1C 的关注层次不同：

```text
实验 1B：结构一致性；
实验 1C：行为一致性。
```

实验 1B 的 TAG 主要回答：

```text
元素是否覆盖；
类型是否一致；
属性是否保持；
关系是否保持；
目标元素是否可追溯。
```

实验 1C 的 UBTS 主要回答：

```text
两侧是否产生相同有界 trace；
对应步骤是否保持 enabled set；
guard 与 effect 是否保持；
终态是否保持。
```

二者是递进关系：

```text
TAG 证明转换后的结构可对齐；
UBTS 证明对齐结构诱导出的行为可对齐。
```

因此，UBTS 不是替代 TAG，而是在结构一致性基础上进一步验证行为一致性。

## 16. 与本文实验实现的对应

本文实验实现中，UBTS 相关产物包括：

```text
semantic/bpmn.semantic_graph.json
semantic/dsl.semantic_graph.json
canonical/bpmn.semantic_graph.canonical.json
canonical/dsl.semantic_graph.canonical.json
paths/bpmn.paths.json
paths/dsl.paths.json
comparison/path_set_comparison.json
comparison/step_trace_comparison_summary.json
```

其中：

```text
semantic/*.json 负责表示 UBTS 静态结构；
canonical/*.json 负责保存 ID 归一化后的 UBTS；
paths/*.json 负责保存由 UBTS 诱导出的 bounded traces；
path_set_comparison.json 负责保存 trace 集合双向包含结果；
step_trace_comparison_summary.json 负责保存步骤级迁移保持结果。
```

这种 JSON UBTS 是对 LTS/GSTS/GLSTS 和 BPMN token-flow 语义的工程化实现，目的是支撑自动化实验，而不是替代完整的流程代数、Petri Net 或模型检测框架。

## 17. 可使用的理论表述

可以这样描述 UBTS：

```text
为避免直接比较 BPMN XML 与 DSL 文本造成的语法差异干扰，本文将 BPMN 源模型与 DSL 目标模型分别映射到统一行为迁移系统（Unified Behavioral Transition System, UBTS）。UBTS 借鉴标号迁移系统、带守卫状态迁移系统和 BPMN token-based execution semantics，以状态、动作标签、守卫、效果和终止状态刻画模型的可执行行为，使 BPMN 与 DSL 能够在统一行为语义域中进行比较。
```

可以这样描述路径集合比较：

```text
在获得 BPMN-UBTS 和 DSL-UBTS 后，本文在相同路径边界、DMN 输出策略和 guard 求值规则下分别枚举 bounded traces。随后通过 BPMN traces ⊆ DSL traces 与 DSL traces ⊆ BPMN traces 的双向包含检查验证 bounded trace equivalence。
```

可以这样描述步骤级比较：

```text
路径集合一致只能说明两侧在观测动作序列层面一致。为进一步验证迁移语义保持性，本文对匹配 trace 的每一步迁移比较 enabled_before、guard_result、state_diff、enabled_after 和 final_state，从而检查有界范围内的 step-wise transition preservation 与 final-state preservation。
```

## 18. 与现有理论的关系边界

需要注意，本文采用 UBTS 时应避免过度声明。

可以声明：

```text
本文借鉴 LTS、GSTS、GLSTS 和 BPMN token-flow 语义；
本文将 BPMN 与 DSL 工程化映射为 UBTS；
本文基于 UBTS 执行有界 trace equivalence 和 step-wise transition preservation 检查。
```

不宜声明：

```text
本文提出了一种全新的流程建模语言；
本文完整形式化了 BPMN 标准的所有执行语义；
本文实现了完整模型检测器；
本文证明了 BPMN->DSL 转换在无界状态空间上的完备正确性。
```

更准确的表述是：

```text
UBTS 在本文中作为源目标模型行为比较的统一中间语义域，
用于支持实验层面的有界行为一致性验证。
```

## 19. 参考文献建议

以下文献和标准可以作为 UBTS 理论来源和相关背景引用。

### 19.1 Labeled Transition Systems / Process Algebra

Robin Milner.  
“Communication and Concurrency.”  
Prentice Hall, 1989.

可用于支撑：

```text
系统行为可以通过状态、动作和迁移关系进行描述；
动作标签序列可以作为进程行为的可观测表示。
```

### 19.2 Model Checking and Transition Systems

Christel Baier and Joost-Pieter Katoen.  
“Principles of Model Checking.”  
MIT Press, 2008.

可用于支撑：

```text
transition system 是模型检测和行为验证的基础表示；
trace、路径、可达状态和终止状态可以在 transition system 上定义。
```

### 19.3 Model Checking

Edmund M. Clarke, Orna Grumberg, and Doron A. Peled.  
“Model Checking.”  
MIT Press, 1999.

可用于支撑：

```text
有限状态系统可以通过状态迁移结构进行自动化验证；
有界路径枚举和状态比较是验证系统行为的重要基础。
```

### 19.4 BPMN Standard and Token-based Execution Semantics

Object Management Group.  
“Business Process Model and Notation (BPMN), Version 2.0.2.”  
OMG, 2013.

可用于支撑：

```text
BPMN 流程执行可以从 token 流、事件、任务、网关和 sequence flow 的角度解释；
enabled 元素、分支选择和终止事件是 BPMN 行为语义的重要组成部分。
```

### 19.5 BPMN Formal Semantics

Remco Dijkman, Marlon Dumas, and Chun Ouyang.  
“Semantics and Analysis of Business Process Models in BPMN.”  
Information and Software Technology, 50(12), 1281-1294, 2008.

可用于支撑：

```text
BPMN 模型可以被映射到形式化语义域以进行行为分析；
流程模型的控制流、事件和网关可以进行形式化解释。
```

## 20. 小结

实验 1C 采用 UBTS 的原因可以概括为：

```text
1. BPMN 和 DSL 都可以被解释为状态迁移系统；
2. LTS 提供状态、动作标签和迁移关系的基础形式；
3. GSTS / GLSTS 支持 guard、effect 和业务变量；
4. BPMN token-flow 语义可以映射为元素标记和 enabled set；
5. DMN 输出可以作为 businessrule 迁移中的有界输入空间；
6. bounded trace equivalence 可以表达路径集合层面的行为一致；
7. step-wise transition preservation 可以表达步骤级迁移语义保持；
8. final-state preservation 可以表达终态行为保持；
9. UBTS JSON 形式足够轻量，能够直接服务于自动化实验。
```

因此，UBTS 是实验 1C 的合适中间语义表示：它既有现有形式化理论基础，又能覆盖 `newTranslator` 生成 DSL 中的 message、gateway、event、businessrule、oracletask、guard、effect 和 DMN 输出等行为要素。
