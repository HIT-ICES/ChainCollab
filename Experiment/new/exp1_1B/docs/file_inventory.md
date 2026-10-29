# 实验 1B 文件作用说明

本文档说明 `/root/code/ChainCollab/Experiment/new/exp1_1B` 目录下各文件和目录的作用。由于 `cases/<CaseName>` 下的文件结构相同，本文先说明顶层文件，再说明每个 case 目录中的通用产物。

## 1. 顶层目录

```text
exp1_1B/
  contracts/
  schemas/
  scripts/
  docs/
  cases/
  实验 1B：BPMN→DSL 源目标结构一致性验证详细实验方案.md
```

### 1.1 `实验 1B：BPMN→DSL 源目标结构一致性验证详细实验方案.md`

实验 1B 的详细方案文档。

作用：

```text
1. 定义实验目标；
2. 明确实验边界；
3. 说明 BPMN-TAG、DSL-TAG、映射契约和 trace 的整体思路；
4. 定义 C1-C5 主体检查项；
5. 说明 logical_path 追溯属于附加验证，不纳入 1B 主体判定。
```

这是实验设计层文档，不是运行脚本。

## 2. `contracts/`

### 2.1 `contracts/default_mapping_contract.json`

BPMN->DSL 的默认映射契约。

作用：

```text
1. 声明哪些 BPMN 元素应映射到哪些 DSL 元素；
2. 声明哪些 BPMN 关系应映射到哪些 DSL 关系；
3. 记录 newTranslator 中的特殊映射规则；
4. 为 trace 生成和一致性检查提供判定依据。
```

关键规则包括：

```text
bpmn:participant -> dsl:participant
bpmn:message -> dsl:message
bpmn:startEvent / endEvent -> dsl:event
bpmn:exclusiveGateway / parallelGateway / eventBasedGateway -> dsl:gateway
bpmn:businessRuleTask -> dsl:businessrule
bpmn:receiveTask / scriptTask / dataTask -> dsl:oracletask
bpmn:messageFlow -> dsl:message_sender / dsl:message_receiver
bpmn:choreographyTask -> message 顺序与 enable 关系
BPMN documentation 派生内容 -> dsl:global
```

该文件是实验 1B 中“映射契约”的具体落地文件。

## 3. `schemas/`

### 3.1 `schemas/tag_format.schema.json`

TAG 格式的 JSON Schema。

作用：

```text
1. 规定 BPMN-TAG 和 DSL-TAG 的统一外层结构；
2. 规定 nodes、edges、derived、warnings 等字段格式；
3. 枚举实验 1B 当前支持的 BPMN 节点类型、BPMN 边类型、DSL 节点类型和 DSL 边类型；
4. 作为后续校验和扩展 TAG 格式的依据。
```

需要注意：

```text
BPMN-TAG 和 DSL-TAG 的外层格式相同；
二者的节点类型、边类型、attrs 字段不同；
二者之间如何对应由 default_mapping_contract.json 解释。
```

## 4. `scripts/`

### 4.1 `scripts/run_all_bpmn_cases.py`

批量实验入口脚本。

作用：

```text
1. 扫描 /root/code/ChainCollab/Experiment/BPMNwithDMNcase 下所有 .bpmn 文件；
2. 将 BPMN 文件名转换为合法 case name；
3. 对每个 case 调用单 case runner；
4. 汇总每个 case 的 PASS / FAIL / ERROR；
5. 生成 cases/batch_summary.json 和 cases/batch_summary.md。
```

运行命令：

```bash
python3 /root/code/ChainCollab/Experiment/new/exp1_1B/scripts/run_all_bpmn_cases.py
```

这是当前跑完整个 `BPMNwithDMNcase` 案例集的推荐入口。

### 4.2 `scripts/run_supplychainpaper_demo.py`

单 case 实验入口脚本。

作用：

```text
1. 调用 newTranslator 的 bpmn_to_dsl.py，将 BPMN 翻译成 B2C DSL；
2. 调用 BPMN 结构抽取脚本；
3. 调用 DSL 结构抽取脚本；
4. 调用 trace 生成脚本；
5. 调用一致性检查脚本；
6. 为单个 case 生成完整实验产物。
```

虽然文件名仍保留 `supplychainpaper_demo`，但当前脚本已经支持任意 BPMN case。

默认运行 SupplyChainPaper：

```bash
python3 /root/code/ChainCollab/Experiment/new/exp1_1B/scripts/run_supplychainpaper_demo.py
```

指定 case 运行：

```bash
python3 /root/code/ChainCollab/Experiment/new/exp1_1B/scripts/run_supplychainpaper_demo.py \
  --bpmn-file /root/code/ChainCollab/Experiment/BPMNwithDMNcase/Purchase.bpmn \
  --case-name Purchase \
  --out-dir /root/code/ChainCollab/Experiment/new/exp1_1B/cases/Purchase
```

### 4.3 `scripts/extract_bpmn_structure.py`

BPMN 结构化抽取脚本。

输入：

```text
一个 .bpmn XML 文件
```

输出：

```text
bpmn/bpmn_tag.json
bpmn/bpmn_elements.json
bpmn/bpmn_relations.json
```

作用：

```text
1. 解析 BPMN XML；
2. 抽取 participant、message、event、gateway、task 等 BPMN 节点；
3. 抽取 messageFlow、sequenceFlow、participantRef、incoming/outgoing 等 BPMN 关系；
4. 从 documentation 中解析消息属性、业务规则参数、oracle 输出、条件变量等派生信息；
5. 生成 BPMN-TAG。
```

它把 BPMN 源模型转换成实验 1B 可比较的类型化属性图。

### 4.4 `scripts/extract_dsl_structure.py`

DSL 结构化抽取脚本。

输入：

```text
newTranslator 生成的 .b2c 文件
```

输出：

```text
dsl/dsl_tag.json
dsl/dsl_elements.json
dsl/dsl_relations.json
```

作用：

```text
1. 解析 B2C DSL 文本；
2. 抽取 contract、participant、global、message、gateway、event、businessrule、oracletask 等 DSL 节点；
3. 抽取 message sender/receiver、enable、disable、set global、gateway branch、parallel join 等 DSL 关系；
4. 将 DSL 目标模型转换成 DSL-TAG。
```

该脚本按照当前 newTranslator 生成的 B2C DSL 格式编写。

### 4.5 `scripts/build_bpmn_dsl_trace.py`

BPMN->DSL 追溯关系生成脚本。

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

作用：

```text
1. 根据映射契约建立 BPMN 节点到 DSL 节点的直接追溯关系；
2. 根据 messageFlow 建立 BPMN 关系到 DSL sender/receiver 关系的追溯；
3. 处理 choreographyTask 这种没有 DSL 同名节点、而是展开为消息顺序和 enable 关系的情况；
4. 记录 BPMN documentation 派生出的 DSL global 来源；
5. 为后续 C1-C5 检查提供 traceability links。
```

该脚本是连接 BPMN-TAG 与 DSL-TAG 的核心步骤。

### 4.6 `scripts/check_structure_consistency.py`

结构一致性检查脚本。

输入：

```text
bpmn/bpmn_tag.json
dsl/dsl_tag.json
trace/bpmn_dsl_trace.json
```

输出：

```text
reports/element_coverage_report.json
reports/type_consistency_report.json
reports/attribute_preservation_report.json
reports/relation_preservation_report.json
reports/spurious_target_report.json
reports/structure_summary.json
reports/structure_summary.md
```

作用：

```text
C1 element_coverage：
  检查 BPMN 中应转换的元素是否被 DSL 覆盖。

C2 type_consistency：
  检查 BPMN 元素类型是否映射为契约规定的 DSL 类型。

C3 attribute_preservation：
  检查 BPMN 关键属性是否在 DSL 中保持一致。

C4 relation_preservation：
  检查 BPMN 结构关系是否在 DSL 中被正确保留。

C5 target_traceability：
  检查 DSL 中关键业务元素是否都有 BPMN 来源或派生来源。
```

该脚本给出实验 1B 主体判定结果。

### 4.7 `scripts/tag_utils.py`

公共工具函数文件。

作用：

```text
1. 读写 JSON；
2. 构造 TAG 节点和边；
3. 查找节点和关系；
4. 解析 BPMN documentation；
5. 规整 message schema；
6. 解析条件表达式；
7. 提供 DSL 文本块解析辅助函数。
```

该文件不单独运行，供其他脚本复用。

## 5. `docs/`

### 5.1 `docs/mapping_and_tag_design.md`

映射契约与 TAG 格式设计说明。

作用：

```text
1. 解释为什么 BPMN-TAG 和 DSL-TAG 使用相同外层容器；
2. 说明 BPMN 与 DSL 的类型差异；
3. 解释 messageFlow、choreographyTask、global 等特殊映射；
4. 给出 BPMN-TAG 和 DSL-TAG 示例。
```

这是设计依据文档，帮助理解 `default_mapping_contract.json` 和 `tag_format.schema.json`。

### 5.2 `docs/demo_code_and_1B_compliance.md`

实验流程与 1B 符合性说明文档。

作用：

```text
1. 说明实验流程如何运行；
2. 解释各脚本之间的调用关系；
3. 记录批量运行结果；
4. 将当前实现与实验 1B 的 C1-C5 要求逐项对应；
5. 说明当前实现的边界。
```

### 5.3 `docs/file_inventory.md`

当前文档。

作用：

```text
逐个说明 exp1_1B 中各文件和各类输出产物的用途。
```

## 6. `cases/`

`cases/` 是实验运行结果目录。

当前已经对以下 11 个 BPMN case 完成批量运行：

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

### 6.1 `cases/batch_summary.json`

批量运行机器可读汇总。

作用：

```text
1. 记录 BPMN 输入目录；
2. 记录 cases 输出目录；
3. 记录总 case 数、PASS 数、FAIL 数、ERROR 数；
4. 记录每个 case 的运行状态、返回码和 summary 路径。
```

### 6.2 `cases/batch_summary.md`

批量运行人工可读汇总。

作用：

```text
以 Markdown 表格形式展示所有 case 的 PASS / FAIL / ERROR 状态。
```

当前结果：

```text
total_cases: 11
passed: 11
failed: 0
errored: 0
```

## 7. 每个 case 目录的通用结构

每个 case 目录结构如下：

```text
cases/<CaseName>/
  input_index.json
  bpmn/
  dsl/
  trace/
  reports/
```

例如：

```text
cases/SupplyChainPaper/
  input_index.json
  bpmn/bpmn_tag.json
  dsl/SupplyChainPaper.b2c
  trace/bpmn_dsl_trace.json
  reports/structure_summary.md
```

### 7.1 `cases/<CaseName>/input_index.json`

case 输入索引文件。

作用：

```text
1. 记录 case name；
2. 记录 BPMN 源文件路径；
3. 记录生成的 DSL 文件路径；
4. 记录映射契约路径；
5. 记录调用的 translator 根目录。
```

它用于复现实验输入来源。

### 7.2 `cases/<CaseName>/bpmn/bpmn_tag.json`

BPMN 源模型的完整 TAG。

作用：

```text
1. 保存 BPMN 节点；
2. 保存 BPMN 关系；
3. 保存从 documentation 等位置提取的派生信息；
4. 作为 trace 生成和一致性检查的源侧输入。
```

这是 BPMN 侧最重要的结构化产物。

### 7.3 `cases/<CaseName>/bpmn/bpmn_elements.json`

BPMN 元素列表。

作用：

```text
从 bpmn_tag.json 中拆出 nodes，便于人工查看 BPMN 元素。
```

### 7.4 `cases/<CaseName>/bpmn/bpmn_relations.json`

BPMN 关系列表。

作用：

```text
从 bpmn_tag.json 中拆出 edges，便于人工查看 BPMN 结构关系。
```

### 7.5 `cases/<CaseName>/dsl/<CaseName>.b2c`

newTranslator 生成的 B2C DSL 文件。

作用：

```text
1. 作为 BPMN->DSL 翻译结果；
2. 作为 DSL-TAG 抽取输入；
3. 作为实验 1B 的目标模型文本。
```

该文件由 `run_supplychainpaper_demo.py` 调用 `src/newTranslator/generator/bpmn_to_dsl.py` 生成。

### 7.6 `cases/<CaseName>/dsl/dsl_tag.json`

DSL 目标模型的完整 TAG。

作用：

```text
1. 保存 DSL 节点；
2. 保存 DSL 关系；
3. 作为 trace 生成和一致性检查的目标侧输入。
```

这是 DSL 侧最重要的结构化产物。

### 7.7 `cases/<CaseName>/dsl/dsl_elements.json`

DSL 元素列表。

作用：

```text
从 dsl_tag.json 中拆出 nodes，便于人工查看 DSL 元素。
```

### 7.8 `cases/<CaseName>/dsl/dsl_relations.json`

DSL 关系列表。

作用：

```text
从 dsl_tag.json 中拆出 edges，便于人工查看 DSL 结构关系。
```

### 7.9 `cases/<CaseName>/trace/bpmn_dsl_trace.json`

BPMN->DSL 追溯关系文件。

作用：

```text
1. 记录 BPMN 元素与 DSL 元素的匹配关系；
2. 记录 BPMN 关系与 DSL 关系的匹配关系；
3. 记录 choreographyTask 等展开结构的表示方式；
4. 记录 DSL global 等派生目标的 BPMN 来源；
5. 作为 C1-C5 一致性检查的核心依据。
```

### 7.10 `cases/<CaseName>/reports/element_coverage_report.json`

C1 元素覆盖报告。

作用：

```text
检查 BPMN 中应转换的元素是否在 DSL 中存在对应结构。
```

核心指标：

```text
element_coverage
```

### 7.11 `cases/<CaseName>/reports/type_consistency_report.json`

C2 类型一致性报告。

作用：

```text
检查 trace 中的 BPMN 元素类型是否映射为契约规定的 DSL 元素类型。
```

核心指标：

```text
type_consistency
```

### 7.12 `cases/<CaseName>/reports/attribute_preservation_report.json`

C3 属性保持报告。

作用：

```text
检查 BPMN 关键属性是否在 DSL 中保持。
```

检查内容包括：

```text
元素 id / name
participant 多实例属性
message schema
event initialState
gateway type
businessrule dmnResource / decisionID
```

核心指标：

```text
attribute_preservation
```

### 7.13 `cases/<CaseName>/reports/relation_preservation_report.json`

C4 关系保持报告。

作用：

```text
检查 BPMN 结构关系是否在 DSL 中被正确保留。
```

检查内容包括：

```text
messageFlow sender / receiver
startEvent 到首个目标的 enable
choreographyTask 消息顺序
parallelGateway join / split
gateway enable
```

核心指标：

```text
relation_preservation
```

### 7.14 `cases/<CaseName>/reports/spurious_target_report.json`

C5 目标可追溯报告。

作用：

```text
检查 DSL 中关键业务元素是否都有 BPMN 来源或派生来源。
```

关键 DSL 类型包括：

```text
dsl:participant
dsl:message
dsl:gateway
dsl:event
dsl:businessrule
dsl:oracletask
```

核心指标：

```text
target_traceability
```

### 7.15 `cases/<CaseName>/reports/structure_summary.json`

单 case 结构一致性机器可读摘要。

作用：

```text
1. 汇总 C1-C5 指标；
2. 给出 structural_status；
3. 记录 BPMN-TAG / DSL-TAG 的节点和边数量；
4. 汇总失败项。
```

### 7.16 `cases/<CaseName>/reports/structure_summary.md`

单 case 结构一致性人工可读摘要。

作用：

```text
以 Markdown 表格形式展示当前 case 的 C1-C5 指标和 PASS / FAIL 状态。
```

这是查看单个 case 实验结论最方便的文件。

## 8. 推荐阅读顺序

如果要理解实验设计，建议顺序：

```text
1. 实验 1B：BPMN→DSL 源目标结构一致性验证详细实验方案.md
2. docs/mapping_and_tag_design.md
3. docs/demo_code_and_1B_compliance.md
4. docs/file_inventory.md
```

如果要理解代码执行，建议顺序：

```text
1. scripts/run_all_bpmn_cases.py
2. scripts/run_supplychainpaper_demo.py
3. scripts/extract_bpmn_structure.py
4. scripts/extract_dsl_structure.py
5. scripts/build_bpmn_dsl_trace.py
6. scripts/check_structure_consistency.py
7. scripts/tag_utils.py
```

如果要查看实验结果，建议顺序：

```text
1. cases/batch_summary.md
2. cases/<CaseName>/reports/structure_summary.md
3. cases/<CaseName>/reports/*.json
4. cases/<CaseName>/trace/bpmn_dsl_trace.json
5. cases/<CaseName>/bpmn/bpmn_tag.json
6. cases/<CaseName>/dsl/dsl_tag.json
```
