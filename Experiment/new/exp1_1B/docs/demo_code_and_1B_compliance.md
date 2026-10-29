# 实验 1B Demo 代码与功能说明

本文档说明 `exp1_1B` 中 BPMN->DSL 结构一致性实验流程的代码组成、运行方式、输出产物，以及该实现是否符合实验 1B 的实验目标。

## 1. Demo 目标

本流程可以对 `BPMNwithDMNcase` 目录下的 BPMN 案例批量运行，也可以对单个 BPMN 案例运行。SupplyChainPaper 是最早用于打通流程的示例输入：

```text
/root/code/ChainCollab/Experiment/BPMNwithDMNcase/SupplyChainPaper.bpmn
```

实验流程完成从 BPMN 到 DSL 的结构一致性验证：

```text
BPMN 源模型
  -> 调用 newTranslator 生成 B2C DSL
  -> 抽取 BPMN-TAG
  -> 抽取 DSL-TAG
  -> 根据映射契约生成 BPMN->DSL 追溯关系
  -> 执行结构一致性检查
  -> 输出结构一致性报告
```

该流程只验证 BPMN->DSL 的结构层一致性，不验证 DSL 后续生成 Go / Solidity 的正确性，也不验证 Fabric / Geth 运行结果。

## 2. 代码文件说明

### 2.1 `scripts/run_supplychainpaper_demo.py`

这是单 case 入口脚本，负责串联一个 BPMN 案例的完整实验流程。虽然文件名保留了最初的 SupplyChainPaper demo 名称，但当前脚本已经支持通过参数运行任意 BPMN 文件。

主要功能：

```text
1. 调用 newTranslator 的 bpmn_to_dsl.py，将 SupplyChainPaper.bpmn 翻译为 SupplyChainPaper.b2c；
2. 调用 BPMN 结构抽取脚本，生成 BPMN-TAG；
3. 调用 DSL 结构抽取脚本，生成 DSL-TAG；
4. 调用追溯关系生成脚本，生成 bpmn_dsl_trace.json；
5. 调用一致性检查脚本，生成各项检查报告和 summary。
```

该脚本只调用 `src/newTranslator` 中已有翻译器，不修改 `newTranslator` 源码。

运行方式：

```bash
python3 /root/code/ChainCollab/Experiment/new/exp1_1B/scripts/run_supplychainpaper_demo.py
```

指定任意 BPMN 案例：

```bash
python3 /root/code/ChainCollab/Experiment/new/exp1_1B/scripts/run_supplychainpaper_demo.py \
  --bpmn-file /root/code/ChainCollab/Experiment/BPMNwithDMNcase/Purchase.bpmn \
  --case-name Purchase \
  --out-dir /root/code/ChainCollab/Experiment/new/exp1_1B/cases/Purchase
```

### 2.2 `scripts/run_all_bpmn_cases.py`

这是批量 case 入口脚本，负责遍历 BPMN case 目录下所有 `.bpmn` 文件，并逐个调用单 case 流程。

主要功能：

```text
1. 扫描 /root/code/ChainCollab/Experiment/BPMNwithDMNcase 下所有 BPMN 文件；
2. 将文件名转换为合法 case name，例如 Hotel Booking -> Hotel_Booking；
3. 每个 case 输出到 exp1_1B/cases/<CaseName>；
4. 即使某个 case 的结构一致性检查 FAIL，也继续运行后续 case；
5. 生成 batch_summary.json 和 batch_summary.md。
```

运行方式：

```bash
python3 /root/code/ChainCollab/Experiment/new/exp1_1B/scripts/run_all_bpmn_cases.py
```

### 2.3 `scripts/extract_bpmn_structure.py`

该脚本负责从 BPMN XML 中抽取 BPMN-TAG。

抽取对象包括：

```text
participant
message
startEvent
endEvent
choreographyTask
exclusiveGateway
parallelGateway
eventBasedGateway
businessRuleTask
receiveTask
scriptTask
dataTask
messageFlow
sequenceFlow
participantRef
initiatingParticipant
messageFlowRef
messageRef
incoming / outgoing
documentation 中描述的消息属性、业务规则参数、oracle 输出参数、条件变量
```

输出文件：

```text
bpmn/bpmn_tag.json
bpmn/bpmn_elements.json
bpmn/bpmn_relations.json
```

其中 `bpmn_tag.json` 是核心结构图，`bpmn_elements.json` 和 `bpmn_relations.json` 是便于人工查看的拆分视图。

### 2.4 `scripts/extract_dsl_structure.py`

该脚本负责从 newTranslator 生成的 `.b2c` 文件中抽取 DSL-TAG。

抽取对象包括：

```text
contract
participant
participant attribute
global
message
gateway
event
businessrule
oracletask
start flow
message flow
gateway flow
rule flow
oracle task flow
parallel join
message sender / receiver
enable / disable / set global
gateway branch
parameter mapping
```

输出文件：

```text
dsl/dsl_tag.json
dsl/dsl_elements.json
dsl/dsl_relations.json
```

该脚本按照当前 `newTranslator` 的 B2C DSL 输出格式设计。例如，BPMN 的 `messageFlow` 在 DSL 中不是独立业务节点，而是体现为 `message` 的 `sender`、`receiver` 关系；`choreographyTask` 也不是 DSL 独立节点，而是通过消息顺序和 `enable` 关系展开。

### 2.5 `scripts/build_bpmn_dsl_trace.py`

该脚本根据 BPMN-TAG、DSL-TAG 和映射契约生成源目标追溯关系。

输入：

```text
bpmn/bpmn_tag.json
dsl/dsl_tag.json
contracts/default_mapping_contract.json
```

输出：

```text
trace/bpmn_dsl_trace.json
```

追溯关系包括：

```text
直接元素映射：
  bpmn:participant -> dsl:participant
  bpmn:message -> dsl:message
  bpmn:startEvent / bpmn:endEvent -> dsl:event
  bpmn:exclusiveGateway / parallelGateway / eventBasedGateway -> dsl:gateway
  bpmn:businessRuleTask -> dsl:businessrule
  bpmn:receiveTask / scriptTask / dataTask -> dsl:oracletask

关系映射：
  bpmn:messageFlow -> dsl:message_sender / dsl:message_receiver

展开映射：
  bpmn:choreographyTask -> message order / enable relations

派生映射：
  BPMN documentation 中的属性、参数、条件变量 -> dsl:global
```

### 2.6 `scripts/check_structure_consistency.py`

该脚本负责执行实验 1B 的结构一致性检查。

检查项包括：

```text
C1 element_coverage：
  BPMN 中应转换的元素是否能在 DSL 中找到对应结构。

C2 type_consistency：
  BPMN 元素类型是否映射为契约规定的 DSL 类型。

C3 attribute_preservation：
  BPMN 关键属性是否在 DSL 中保持一致。

C4 relation_preservation：
  BPMN 结构关系是否在 DSL 中被保留。

C5 target_traceability：
  DSL 中关键业务元素是否都有 BPMN 来源或派生来源。
```

输出报告：

```text
reports/element_coverage_report.json
reports/type_consistency_report.json
reports/attribute_preservation_report.json
reports/relation_preservation_report.json
reports/spurious_target_report.json
reports/structure_summary.json
reports/structure_summary.md
```

### 2.7 `scripts/tag_utils.py`

该文件提供 TAG 构造、JSON 读写、BPMN 类型映射、documentation 解析、message schema 规整、条件表达式解析等公共函数。

该工具文件的目的不是定义新的实验逻辑，而是保证 BPMN 抽取、DSL 抽取、追溯生成和一致性检查使用同一套数据表示方式。

## 3. 映射契约与 TAG 格式

本 demo 使用的映射契约为：

```text
contracts/default_mapping_contract.json
```

TAG 格式定义为：

```text
schemas/tag_format.schema.json
```

TAG 的统一外层结构为：

```json
{
  "tag_version": "0.1.0",
  "case_name": "SupplyChainPaper",
  "model_type": "bpmn 或 dsl",
  "source_file": "...",
  "extractor": {},
  "nodes": [],
  "edges": [],
  "derived": [],
  "warnings": []
}
```

BPMN-TAG 和 DSL-TAG 使用相同的容器格式，但节点类型、边类型和属性字段不同。两者之间的对应关系由映射契约解释。

特别需要注意：

```text
1. BPMN messageFlow 不要求映射为 DSL messageFlow 节点，而是映射为 DSL message 的 sender / receiver 关系；
2. BPMN choreographyTask 不要求映射为 DSL choreographyTask 节点，而是映射为 message 顺序和 enable 关系；
3. DSL global 可能来自 BPMN documentation 中的消息属性、业务规则参数、oracle 输出参数或 sequenceFlow 条件变量，属于派生结构；
4. 因此 C5 检查无来源 DSL 目标时，不应把具有派生来源的 global 判为伪目标。
```

这些规则与 `newTranslator` 当前 BPMN->B2C DSL 的生成方式一致。

## 4. Cases 输出产物

所有 case 的输出目录为：

```text
/root/code/ChainCollab/Experiment/new/exp1_1B/cases
```

单个 case 的输出目录形如：

```text
/root/code/ChainCollab/Experiment/new/exp1_1B/cases/SupplyChainPaper
```

主要产物：

```text
dsl/SupplyChainPaper.b2c
  newTranslator 生成的 B2C DSL。

bpmn/bpmn_tag.json
  BPMN 源模型的类型化属性图。

dsl/dsl_tag.json
  DSL 目标模型的类型化属性图。

trace/bpmn_dsl_trace.json
  BPMN 到 DSL 的追溯关系。

reports/structure_summary.md
  最终结构一致性摘要报告。

batch_summary.json / batch_summary.md
  批量运行的总汇总报告，位于 cases 目录下。
```

当前 demo 抽取规模：

```text
BPMN-TAG nodes: 60
BPMN-TAG edges: 123
DSL-TAG nodes: 72
DSL-TAG edges: 115
trace direct links: 43
trace relation links: 13
represented choreography sources: 26
```

## 5. 当前批量测试结果

已执行命令：

```bash
python3 /root/code/ChainCollab/Experiment/new/exp1_1B/scripts/run_all_bpmn_cases.py
```

批量最终报告：

```text
/root/code/ChainCollab/Experiment/new/exp1_1B/cases/batch_summary.md
```

批量结果：

```text
total_cases: 11
passed: 11
failed: 0
errored: 0
```

已运行 case：

```text
Blood_analysis
Hotel_Booking
ManagementSystem
Pizza_Order
Purchase
Rental_Claim
SupplyChain
SupplyChainPaper
amazon
customer
manufactory
```

SupplyChainPaper 的单 case 报告：

```text
/root/code/ChainCollab/Experiment/new/exp1_1B/cases/SupplyChainPaper/reports/structure_summary.md
```

报告结果：

```text
Case: SupplyChainPaper
Status: PASS

element_coverage        1.0000
type_consistency        1.0000
attribute_preservation  1.0000
relation_preservation   1.0000
target_traceability     1.0000

Failures: 0
```

同时已验证以下 JSON 文件格式合法：

```text
bpmn/bpmn_tag.json
dsl/dsl_tag.json
trace/bpmn_dsl_trace.json
reports/structure_summary.json
```

## 6. 是否符合实验 1B

结论：当前 demo 符合实验 1B 的主体计划。

对应关系如下：

| 实验 1B 要求 | 当前实现 | 是否满足 |
|---|---|---|
| 定义 BPMN-TAG 和 DSL-TAG | 已通过 `tag_format.schema.json` 和两个抽取脚本实现 | 满足 |
| 定义 BPMN->DSL 映射契约 | 已通过 `default_mapping_contract.json` 实现 | 满足 |
| BPMN 元素覆盖检查 | `element_coverage_report.json` | 满足 |
| 类型一致性检查 | `type_consistency_report.json` | 满足 |
| 属性保持检查 | `attribute_preservation_report.json` | 满足 |
| 关系保持检查 | `relation_preservation_report.json` | 满足 |
| DSL 无来源关键元素检查 | `spurious_target_report.json` | 满足 |
| 生成可复现实验摘要 | `structure_summary.json` 和 `structure_summary.md` | 满足 |
| 使用 newTranslator 生成 DSL | `run_supplychainpaper_demo.py` 调用 `src/newTranslator/generator/bpmn_to_dsl.py` | 满足 |

因此，当前 1B 流程已经完成从 BPMN 输入、DSL 生成、双方 TAG 抽取、追溯关系构造到一致性报告生成的闭环验证，并已对 `BPMNwithDMNcase` 下 11 个案例完成批量运行。

## 7. 与实验 1B 边界的关系

当前流程严格位于实验 1B 的结构一致性范围内：

```text
验证：
  BPMN->DSL 结构覆盖；
  类型映射；
  关键属性保持；
  结构关系保持；
  DSL 关键目标可追溯。

不验证：
  DSL 路径是否可执行；
  guard 条件运行语义是否正确；
  状态迁移运行结果是否正确；
  DMN 决策结果是否正确；
  Go / Solidity 代码生成是否保真；
  Fabric / Geth 执行结果是否一致。
```

这些未验证内容属于后续实验或附加验证范围，不影响本 demo 对实验 1B 主体目标的符合性。

## 8. 当前限制

当前实现是面向 `newTranslator` 当前生成格式的 1B 实验流程。它已经覆盖 `BPMNwithDMNcase` 下 11 个案例中参与 BPMN->DSL 结构映射的主要元素和关系，但仍有以下边界：

```text
1. DSL 抽取器基于当前 B2C 文本格式解析，如果 newTranslator 的 DSL 语法大幅调整，需要同步更新抽取规则；
2. 当前 demo 未实现实验三 logical_path 的附加追溯检查；
3. 当前一致性检查关注结构保真，不判断业务语义执行结果；
4. 对于其他 BPMN 案例，若出现新的 BPMN 扩展元素，需要在 TAG schema、抽取器和映射契约中补充类型。
```

这些限制与实验 1B 的主体边界一致，不影响当前批量 case 的结构一致性验证结论。
