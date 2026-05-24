# 实验 1B：BPMN→DSL 源目标结构一致性验证详细实验方案

## 1. 实验目标

实验 1B 用于验证 BPMN 源模型转换为 DSL 目标模型后，源模型中的关键结构信息是否被完整、正确、可追踪地保留。

本实验只关注结构层一致性，不验证路径执行行为、不验证状态迁移结果、不验证 Go / Solidity 代码生成结果，也不验证 Fabric / Geth 上的运行结果。

实验目标包括：

```text
1. BPMN 中应转换的元素，在 DSL 中是否存在对应元素；
2. BPMN 元素的关键属性，在 DSL 中是否保持一致；
3. BPMN 中的结构关系，在 DSL 中是否被正确保留；
4. DSL 中是否不存在无 BPMN 来源的关键业务元素。
```

此外，本方案单独设置一项附加验证：

```text
实验三 logical_path.json 中使用的 DSL 元素，是否都能追溯到 BPMN 源元素。
```

该附加验证只检查实验三路径的结构来源，不检查路径是否可执行，也不检查运行时行为是否一致。

------

## 2. 实验边界

### 2.1 本实验验证内容

```text
BPMN 元素是否被 DSL 覆盖；
BPMN 元素类型是否被正确映射；
BPMN 元素关键属性是否保持；
BPMN 结构关系是否保持；
DSL 中是否存在无 BPMN 来源的关键元素。
```

### 2.2 附加验证内容

```text
实验三 logical_path 中的步骤是否具有 BPMN 来源。
```

该部分作为 1B 与实验三的衔接检查，不纳入 1B 主体结构一致性判定。

### 2.3 本实验不验证内容

```text
路径是否可执行；
guard 条件是否运行正确；
状态迁移是否一致；
业务规则输出是否一致；
DSL→Go / DSL→Solidity 代码是否保真；
Fabric / Geth 执行结果是否一致。
```

这些内容分别由 1C、实验 2 和实验 3 负责。

------

## 3. 实验总体思路

实验 1B 的核心做法是：

```text
BPMN 源模型
  ↓ 结构抽取
BPMN-TAG：BPMN 类型化属性图

DSL 目标模型
  ↓ 结构抽取
DSL-TAG：DSL 类型化属性图

BPMN-TAG + DSL-TAG
  ↓ 映射契约
bpmn_dsl_trace.json：源目标追踪关系

bpmn_dsl_trace.json
  ↓ 结构一致性检查
结构一致性报告

bpmn_dsl_trace.json + logical_path.json
  ↓ 附加路径来源检查
实验三路径结构可追踪性报告
```

其中 TAG 表示 Typed Attributed Graph，即类型化属性图。一个 TAG 由三部分组成：

```text
nodes：模型元素；
edges：元素之间的结构关系；
attrs：元素或关系携带的关键字段。
```

本实验不直接比较 BPMN XML 和 DSL 文本，而是先把它们抽取成统一结构图，再基于映射契约和 traceability link 进行对比。

------

## 4. 实验输入

### 4.1 BPMN 源模型

输入文件示例：

```text
BPMNwithDMNcase/<CaseName>.bpmn
```

需要从 BPMN 中抽取：

```text
participant / pool / lane
startEvent
endEvent
messageFlow
choreographyTask
businessRuleTask
exclusiveGateway
parallelGateway
sequenceFlow
dataInputAssociation
dataOutputAssociation
sourceRef
targetRef
message sender
message receiver
gateway branch
gateway join
```

### 4.2 DSL 目标模型

输入文件示例：

```text
exp2_semantic_verification/results/cases/<CaseName>/dsl.b2c
```

或者：

```text
exp2_semantic_verification/results/cases/<CaseName>/dsl_model.json
```

需要从 DSL 中抽取：

```text
participant
event
message
gateway
businessrule
flow
enable relation
guard
caller
callee
input
output
asset / token 相关字段
operation 相关字段
```

### 4.3 实验三路径文件（附加验证输入）

输入文件示例：

```text
exp3/cases/<CaseName>/paths/<PathName>/logical_path.json
```

用途：作为附加验证输入，检查实验三中用于回放的每个 logical step 是否能追溯到 BPMN 源元素。

------

## 5. 实验输出目录

建议目录如下：

```text
exp1/1B_structure_consistency/
  cases/
    <CaseName>/
      input_index.json

      bpmn/
        bpmn_elements.json
        bpmn_relations.json
        bpmn_tag.json

      dsl/
        dsl_elements.json
        dsl_relations.json
        dsl_tag.json

      trace/
        mapping_contract.json
        bpmn_dsl_trace.json

      reports/
        element_coverage_report.json
        type_consistency_report.json
        attribute_preservation_report.json
        relation_preservation_report.json
        spurious_target_report.json
        # 附加验证报告
        path_traceability_report.json
        structure_summary.json
        structure_summary.md
```

------

## 6. 核心中间产物设计

### 6.1 input_index.json

记录一个 case 的所有输入路径。

```json
{
  "case_name": "SupplyChainPaper",
  "bpmn_file": "BPMNwithDMNcase/SupplyChainPaper.bpmn",
  "dsl_file": "exp2_semantic_verification/results/cases/SupplyChainPaper/dsl.b2c",
  "logical_paths_dir": "exp3/cases/SupplyChainPaper/paths"
}
```

------

### 6.2 bpmn_tag.json

BPMN 源模型的结构图。

```json
{
  "case_name": "SupplyChainPaper",
  "model_type": "bpmn",
  "nodes": [
    {
      "id": "MessageFlow_001",
      "type": "message",
      "name": "SubmitOrder",
      "attrs": {
        "sender": "Buyer",
        "receiver": "Seller",
        "source_ref": "Participant_Buyer",
        "target_ref": "Participant_Seller"
      }
    },
    {
      "id": "Gateway_001",
      "type": "gateway",
      "name": "CheckPriority",
      "attrs": {
        "gateway_type": "exclusive"
      }
    }
  ],
  "edges": [
    {
      "id": "SequenceFlow_001",
      "source": "MessageFlow_001",
      "target": "Gateway_001",
      "type": "sequence"
    }
  ]
}
```

------

### 6.3 dsl_tag.json

DSL 目标模型的结构图。

```json
{
  "case_name": "SupplyChainPaper",
  "model_type": "dsl",
  "nodes": [
    {
      "id": "MessageFlow_001",
      "type": "message",
      "name": "SubmitOrder",
      "attrs": {
        "caller": "Buyer",
        "callee": "Seller"
      }
    },
    {
      "id": "Gateway_001",
      "type": "gateway",
      "name": "CheckPriority",
      "attrs": {
        "gateway_type": "exclusive"
      }
    }
  ],
  "edges": [
    {
      "id": "Enable_001",
      "source": "MessageFlow_001",
      "target": "Gateway_001",
      "type": "enable"
    }
  ]
}
```

------

### 6.4 mapping_contract.json

映射契约，用于定义 BPMN 元素与 DSL 元素之间的合法映射关系。

```json
{
  "element_rules": [
    {
      "rule_name": "Participant2Participant",
      "source_type": "bpmn:Participant",
      "target_type": "dsl:participant",
      "required_attrs": ["id", "name"]
    },
    {
      "rule_name": "Pool2Participant",
      "source_type": "bpmn:Pool",
      "target_type": "dsl:participant",
      "required_attrs": ["id", "name"]
    },
    {
      "rule_name": "Lane2Participant",
      "source_type": "bpmn:Lane",
      "target_type": "dsl:participant",
      "required_attrs": ["id", "name"]
    },
    {
      "rule_name": "MessageFlow2Message",
      "source_type": "bpmn:MessageFlow",
      "target_type": "dsl:message",
      "required_attrs": ["id", "name", "sender", "receiver"]
    },
    {
      "rule_name": "StartEvent2Event",
      "source_type": "bpmn:StartEvent",
      "target_type": "dsl:event",
      "required_attrs": ["id", "event_type"]
    },
    {
      "rule_name": "EndEvent2Event",
      "source_type": "bpmn:EndEvent",
      "target_type": "dsl:event",
      "required_attrs": ["id", "event_type"]
    },
    {
      "rule_name": "ExclusiveGateway2Gateway",
      "source_type": "bpmn:ExclusiveGateway",
      "target_type": "dsl:gateway",
      "required_attrs": ["id", "gateway_type", "condition"]
    },
    {
      "rule_name": "ParallelGateway2Gateway",
      "source_type": "bpmn:ParallelGateway",
      "target_type": "dsl:gateway",
      "required_attrs": ["id", "gateway_type"]
    },
    {
      "rule_name": "BusinessRuleTask2BusinessRule",
      "source_type": "bpmn:BusinessRuleTask",
      "target_type": "dsl:businessrule",
      "required_attrs": ["id", "name", "input", "output"]
    }
  ],
  "relation_rules": [
    {
      "rule_name": "SequenceFlow2Enable",
      "source_relation": "bpmn:sequenceFlow",
      "target_relation": "dsl:enable",
      "preserve_direction": true
    },
    {
      "rule_name": "MessageFlow2MessageRelation",
      "source_relation": "bpmn:messageFlow",
      "target_relation": "dsl:message",
      "preserve_sender_receiver": true
    },
    {
      "rule_name": "ExclusiveBranch2Guard",
      "source_relation": "bpmn:branch",
      "target_relation": "dsl:guard",
      "preserve_condition": true
    },
    {
      "rule_name": "ParallelJoin2Join",
      "source_relation": "bpmn:join",
      "target_relation": "dsl:join",
      "preserve_join_precondition": true
    }
  ],
  "allowed_synthetic": [
    {
      "type": "synthetic_start",
      "reason": "runtime bootstrap helper"
    },
    {
      "type": "synthetic_parallel_join",
      "reason": "normalization helper"
    },
    {
      "type": "runtime_helper",
      "reason": "internal execution helper"
    }
  ]
}
```

------

### 6.5 bpmn_dsl_trace.json

源目标追踪文件，用于记录 BPMN 元素到 DSL 元素的映射。

```json
{
  "case_name": "SupplyChainPaper",
  "links": [
    {
      "source_id": "MessageFlow_001",
      "source_type": "bpmn:MessageFlow",
      "target_id": "MessageFlow_001",
      "target_type": "dsl:message",
      "rule_name": "MessageFlow2Message",
      "status": "matched",
      "match_method": "id",
      "preserved_attributes": {
        "id": true,
        "name": true,
        "sender": true,
        "receiver": true
      }
    }
  ],
  "unmatched_sources": [],
  "unmatched_targets": []
}
```

------

## 7. 第一部分：1B 主体结构一致性检查

实验 1B 主体设计五类检查：C1 至 C5。

------

## 7.1 C1：元素覆盖检查

### 检查目的

验证 BPMN 源模型中的可转换元素是否都能在 DSL 中找到对应元素。

### 输入

```text
bpmn_tag.json
dsl_tag.json
mapping_contract.json
bpmn_dsl_trace.json
```

### 检查对象

```text
participant
pool
lane
startEvent
endEvent
messageFlow
businessRuleTask
exclusiveGateway
parallelGateway
choreographyTask
```

### 检查逻辑

```text
for each source_node in bpmn_tag.nodes:
    if source_node.type belongs to convertible_types:
        find trace link where link.source_id == source_node.id

        if link exists:
            mark source_node as mapped
        else:
            mark source_node as missing
```

### 输出

```text
element_coverage_report.json
```

示例：

```json
{
  "case_name": "SupplyChainPaper",
  "convertible_source_elements": 45,
  "mapped_source_elements": 45,
  "missing_elements": [],
  "element_coverage": 1.0
}
```

### 验收标准

```text
missing_elements = 0
element_coverage = 1.0
```

如果存在无法转换或不需要转换的 BPMN 元素，必须在 mapping_contract.json 中声明为 ignored 或 non_convertible。

### 该步骤证明什么

```text
BPMN 源模型中的关键结构元素没有在 DSL 转换过程中丢失。
```

------

## 7.2 C2：类型一致性检查

### 检查目的

验证每个 BPMN 元素是否被映射为正确类型的 DSL 元素。

### 输入

```text
mapping_contract.json
bpmn_dsl_trace.json
bpmn_tag.json
dsl_tag.json
```

### 检查逻辑

```text
for each trace_link in bpmn_dsl_trace.links:
    source_type = trace_link.source_type
    target_type = trace_link.target_type

    find rule in mapping_contract.element_rules
    check source_type and target_type are consistent with the rule
```

### 类型映射示例

```text
bpmn:Participant       → dsl:participant
bpmn:Pool              → dsl:participant
bpmn:Lane              → dsl:participant
bpmn:StartEvent        → dsl:event(type=start)
bpmn:EndEvent          → dsl:event(type=end)
bpmn:MessageFlow       → dsl:message
bpmn:ExclusiveGateway  → dsl:gateway(type=exclusive)
bpmn:ParallelGateway   → dsl:gateway(type=parallel)
bpmn:BusinessRuleTask  → dsl:businessrule
```

### 输出

```text
type_consistency_report.json
```

示例：

```json
{
  "case_name": "SupplyChainPaper",
  "total_trace_links": 45,
  "type_matched_links": 45,
  "type_mismatches": [],
  "type_consistency": 1.0
}
```

### 验收标准

```text
type_mismatches = 0
type_consistency = 1.0
```

### 该步骤证明什么

```text
转换过程中没有发生元素类别错误。
例如，message 没有被转成 gateway，exclusive gateway 没有被转成 parallel gateway。
```

------

## 7.3 C3：属性保持检查

### 检查目的

验证 BPMN 元素的关键属性是否在 DSL 元素中保持。

### 输入

```text
bpmn_tag.json
dsl_tag.json
mapping_contract.json
bpmn_dsl_trace.json
```

### 检查内容

#### MessageFlow / Message

```text
BPMN name      == DSL name
BPMN sender    == DSL caller 或 sender
BPMN receiver  == DSL callee 或 receiver
```

#### Participant

```text
BPMN id    == DSL id
BPMN name  == DSL name
```

#### Gateway

```text
BPMN gateway_type == DSL gateway_type
BPMN condition    == DSL guard / condition
```

#### BusinessRuleTask / BusinessRule

```text
BPMN rule_name == DSL name
BPMN input     == DSL input
BPMN output    == DSL output
```

#### Asset / DataObject 相关字段

如果 BPMN 扩展中包含 Asset / AssetTask，需要检查：

```text
assetType
tokenType
tokenName
tokenId
refTokens
operation
caller
callee
tokenNumber
```

### 检查逻辑

```text
for each trace_link in bpmn_dsl_trace.links:
    source_node = find bpmn node by trace_link.source_id
    target_node = find dsl node by trace_link.target_id

    required_attrs = mapping_contract[trace_link.rule_name].required_attrs

    for each attr in required_attrs:
        normalize source attr
        normalize target attr
        compare source attr and target attr
```

### 属性规范化规则

```text
去除首尾空格；
统一大小写；
统一布尔值 true / false；
统一列表排序；
统一 participant id 与 participant name 的别名映射；
统一 guard 表达式中的空格；
统一 sender/receiver 与 caller/callee 的字段名。
```

### 输出

```text
attribute_preservation_report.json
```

示例：

```json
{
  "case_name": "SupplyChainPaper",
  "total_attribute_checks": 132,
  "passed_attribute_checks": 132,
  "failed_attribute_checks": 0,
  "attribute_preservation": 1.0,
  "failures": []
}
```

失败示例：

```json
{
  "source_id": "MessageFlow_003",
  "target_id": "Message_003",
  "attribute": "receiver",
  "source_value": "Seller",
  "target_value": "Logistics",
  "failure_type": "AttributeMismatch"
}
```

### 验收标准

```text
failed_attribute_checks = 0
attribute_preservation = 1.0
```

如果某些属性在 DSL 中被重命名，需要在字段映射表中声明。

### 该步骤证明什么

```text
BPMN 元素的语义身份和关键业务属性在 DSL 中被保持。
```

------

## 7.4 C4：关系保持检查

### 检查目的

验证 BPMN 中的结构关系是否在 DSL 中保持。

### 输入

```text
bpmn_tag.json
dsl_tag.json
mapping_contract.json
bpmn_dsl_trace.json
```

### 检查关系类型

```text
sequenceFlow
messageFlow
branch relation
join relation
participant ownership
dataInputAssociation
dataOutputAssociation
asset-task binding relation
```

### 检查逻辑

#### 1. sequenceFlow → enable relation

```text
BPMN sequenceFlow(A → B)
  通过 trace 找到 A' 和 B'
  检查 DSL 中是否存在 enable(A' → B')
```

#### 2. messageFlow → message relation

```text
BPMN messageFlow(sender=A, receiver=B)
  检查 DSL message 中 caller/callee 是否对应 A/B
```

#### 3. exclusive branch → guard relation

```text
BPMN exclusiveGateway 分支条件 cond_i
  检查 DSL 对应分支是否保留 guard cond_i
```

该检查只验证分支条件文本或规范化表达式是否被结构性保留，不判断 guard 的运行结果或行为语义等价性。

#### 4. parallel split / join → parallel relation

```text
BPMN parallel split 后继集合 {A, B, C}
  检查 DSL 中对应元素是否同时被 enable

BPMN parallel join 前驱集合 {A, B, C}
  检查 DSL 中 join precondition 是否要求所有前驱完成
```

#### 5. DataObject / AssetTask 绑定关系

```text
BPMN AssetTask 通过 DataInputAssociation / DataOutputAssociation 绑定 DataObject
  检查 DSL 中对应 tokenElement 是否保留该绑定关系
```

### 输出

```text
relation_preservation_report.json
```

示例：

```json
{
  "case_name": "SupplyChainPaper",
  "total_source_relations": 38,
  "preserved_relations": 38,
  "missing_relations": [],
  "direction_mismatches": [],
  "relation_preservation": 1.0
}
```

失败示例：

```json
{
  "failure_type": "RelationMissing",
  "source_relation": {
    "type": "sequence",
    "source": "MessageFlow_001",
    "target": "Gateway_001"
  },
  "expected_target_relation": {
    "type": "enable",
    "source": "MessageFlow_001",
    "target": "Gateway_001"
  },
  "actual": "not_found"
}
```

### 验收标准

```text
missing_relations = 0
direction_mismatches = 0
relation_preservation = 1.0
```

### 该步骤证明什么

```text
BPMN 中的控制流、消息协作关系、分支关系、并行同步关系和资产绑定关系，在 DSL 中被结构性保留。
```

------

## 7.5 C5：无伪造目标元素检查

### 检查目的

验证 DSL 中不存在无 BPMN 来源的关键业务元素。

### 输入

```text
dsl_tag.json
bpmn_dsl_trace.json
mapping_contract.json
```

### 检查逻辑

```text
for each target_node in dsl_tag.nodes:
    if target_node.type belongs to critical_types:
        check exists trace link where link.target_id == target_node.id

        if no trace link:
            check whether target_node is declared in allowed_synthetic

        if not traceable and not allowed:
            mark as spurious target
```

### critical_types 示例

```text
participant
event
message
gateway
businessrule
asset
assetTask
tokenElement
```

### 允许的辅助元素

```text
synthetic_start
synthetic_parallel_join
runtime_helper
internal_variable
normalization_helper
```

这些元素可以存在，但必须显式声明。

### 输出

```text
spurious_target_report.json
```

示例：

```json
{
  "case_name": "SupplyChainPaper",
  "critical_target_elements": 45,
  "traceable_target_elements": 45,
  "allowed_synthetic_elements": [],
  "spurious_targets": [],
  "target_traceability": 1.0
}
```

### 验收标准

```text
spurious_targets = []
target_traceability = 1.0
```

### 该步骤证明什么

```text
DSL 目标模型没有引入未经 BPMN 源模型解释的关键业务结构。
```

------

## 8. 第二部分：附加验证：实验三 logical_path 结构可追踪性检查

该部分是 1B 与实验三之间的衔接验证，不属于 1B 主体结构一致性检查项。它只验证实验三路径中的 DSL 元素是否具有 BPMN 来源，不验证路径可执行性、guard 运行结果、状态迁移一致性或平台运行结果。

### 8.1 检查目的

验证实验三使用的 logical_path 中每一个执行步骤是否都能追溯到 BPMN 源元素。

### 8.2 输入

```text
logical_path.json
dsl_tag.json
bpmn_dsl_trace.json
```

### 8.3 logical_path 可能结构

不同实验三实现中 logical_path 可能有不同字段，检查器应兼容以下字段：

```text
step.element
step.trigger.element
step.activity_id
step.id
step.target
```

建议按以下优先级读取：

```text
1. step.trigger.element
2. step.element
3. step.activity_id
4. step.id
5. step.target
```

### 8.4 检查逻辑

```text
for each logical_path in logical_paths_dir:
    for each step in logical_path.steps:
        element_id = extract_element_id(step)

        check element_id exists in dsl_tag.nodes
        check element_id has trace link in bpmn_dsl_trace.json

        if exists:
            mark step as traceable
        else:
            mark step as untraceable
```

### 8.5 输出

```text
path_traceability_report.json
```

示例：

```json
{
  "case_name": "SupplyChainPaper",
  "paths": [
    {
      "path_name": "path_001",
      "total_steps": 8,
      "traceable_steps": 8,
      "untraceable_steps": [],
      "path_traceability": 1.0
    },
    {
      "path_name": "path_002",
      "total_steps": 10,
      "traceable_steps": 10,
      "untraceable_steps": [],
      "path_traceability": 1.0
    }
  ],
  "overall_total_steps": 18,
  "overall_traceable_steps": 18,
  "overall_path_traceability": 1.0
}
```

失败示例：

```json
{
  "path_name": "path_003",
  "step_index": 5,
  "element_id": "SyntheticTask_01",
  "failure_type": "PathStepUntraceable",
  "reason": "element not found in bpmn_dsl_trace.json"
}
```

### 8.6 验收标准

```text
untraceable_steps = []
overall_path_traceability = 1.0
```

### 8.7 该步骤证明什么

```text
实验三使用的回放路径不是 DSL-only 路径，而是具有 BPMN 源模型结构依据的路径。
```

------

## 9. 实验指标

### 9.1 主体结构一致性指标

#### 9.1.1 元素覆盖率

```text
ElementCoverage = mapped_source_elements / convertible_source_elements
```

#### 9.1.2 类型一致率

```text
TypeConsistency = type_matched_links / total_trace_links
```

#### 9.1.3 属性保持率

```text
AttributePreservation = passed_attribute_checks / total_attribute_checks
```

#### 9.1.4 关系保持率

```text
RelationPreservation = preserved_relations / total_source_relations
```

#### 9.1.5 目标元素可追踪率

```text
TargetTraceability = traceable_target_elements / critical_target_elements
```

### 9.2 附加验证指标

#### 9.2.1 实验三路径可追踪率

```text
PathTraceability = traceable_logical_path_steps / total_logical_path_steps
```

### 9.3 总体判定

#### 9.3.1 1B 主体结构一致性判定

建议使用严格判定：

```text
StructuralConsistency = PASS
当且仅当：
  ElementCoverage = 1.0
  TypeConsistency = 1.0
  AttributePreservation = 1.0
  RelationPreservation = 1.0
  TargetTraceability = 1.0
```

如果允许部分属性不一致，则必须把例外规则写入 mapping_contract.json。

#### 9.3.2 附加验证判定

```text
Exp3PathTraceability = PASS
当且仅当：
  PathTraceability = 1.0
```

最终报告可以同时给出两个状态：

```text
1B 主体结构一致性状态：StructuralConsistency
实验三路径结构可追踪性状态：Exp3PathTraceability
```

------

## 10. 实验脚本设计

### 10.1 总入口脚本

```text
scripts/run_1b_structure_consistency.py
```

运行示例：

```bash
python scripts/run_1b_structure_consistency.py \
  --case-name SupplyChainPaper \
  --bpmn-file BPMNwithDMNcase/SupplyChainPaper.bpmn \
  --dsl-file exp2_semantic_verification/results/cases/SupplyChainPaper/dsl.b2c \
  --logical-path-dir exp3/cases/SupplyChainPaper/paths \
  --out-dir exp1/1B_structure_consistency/cases/SupplyChainPaper
```

### 10.2 子脚本列表

```text
scripts/extract_bpmn_structure.py
scripts/extract_dsl_structure.py
scripts/build_mapping_contract.py
scripts/build_bpmn_dsl_trace.py
scripts/check_element_coverage.py
scripts/check_type_consistency.py
scripts/check_attribute_preservation.py
scripts/check_relation_preservation.py
scripts/check_spurious_targets.py
scripts/check_exp3_path_traceability.py
scripts/generate_1b_summary.py
```

------

## 11. 实验执行流程

### Step 1：建立 case 输入索引

生成：

```text
input_index.json
```

检查：

```text
BPMN 文件是否存在；
DSL 文件是否存在；
如执行附加验证，logical_path 目录是否存在；
输出目录是否可写。
```

------

### Step 2：抽取 BPMN 结构

执行：

```bash
python scripts/extract_bpmn_structure.py \
  --bpmn-file BPMNwithDMNcase/SupplyChainPaper.bpmn \
  --out-dir exp1/1B_structure_consistency/cases/SupplyChainPaper/bpmn
```

生成：

```text
bpmn_elements.json
bpmn_relations.json
bpmn_tag.json
```

------

### Step 3：抽取 DSL 结构

执行：

```bash
python scripts/extract_dsl_structure.py \
  --dsl-file exp2_semantic_verification/results/cases/SupplyChainPaper/dsl.b2c \
  --out-dir exp1/1B_structure_consistency/cases/SupplyChainPaper/dsl
```

生成：

```text
dsl_elements.json
dsl_relations.json
dsl_tag.json
```

------

### Step 4：生成映射契约

执行：

```bash
python scripts/build_mapping_contract.py \
  --out-file exp1/1B_structure_consistency/cases/SupplyChainPaper/trace/mapping_contract.json
```

生成：

```text
mapping_contract.json
```

初期可以手工维护，后续可以从转换规则中自动导出。

------

### Step 5：生成 traceability link

执行：

```bash
python scripts/build_bpmn_dsl_trace.py \
  --bpmn-tag exp1/1B_structure_consistency/cases/SupplyChainPaper/bpmn/bpmn_tag.json \
  --dsl-tag exp1/1B_structure_consistency/cases/SupplyChainPaper/dsl/dsl_tag.json \
  --contract exp1/1B_structure_consistency/cases/SupplyChainPaper/trace/mapping_contract.json \
  --out-file exp1/1B_structure_consistency/cases/SupplyChainPaper/trace/bpmn_dsl_trace.json
```

生成：

```text
bpmn_dsl_trace.json
```

匹配优先级建议：

```text
1. 转换器原始 trace；
2. 完全 id 匹配；
3. id 规范化匹配；
4. type + name 匹配；
5. relation context 辅助匹配；
6. 无法匹配则记为 unmatched。
```

------

### Step 6：执行元素覆盖检查

执行：

```bash
python scripts/check_element_coverage.py \
  --bpmn-tag exp1/1B_structure_consistency/cases/SupplyChainPaper/bpmn/bpmn_tag.json \
  --trace exp1/1B_structure_consistency/cases/SupplyChainPaper/trace/bpmn_dsl_trace.json \
  --contract exp1/1B_structure_consistency/cases/SupplyChainPaper/trace/mapping_contract.json \
  --out-file exp1/1B_structure_consistency/cases/SupplyChainPaper/reports/element_coverage_report.json
```

------

### Step 7：执行类型一致性检查

执行：

```bash
python scripts/check_type_consistency.py \
  --trace exp1/1B_structure_consistency/cases/SupplyChainPaper/trace/bpmn_dsl_trace.json \
  --contract exp1/1B_structure_consistency/cases/SupplyChainPaper/trace/mapping_contract.json \
  --out-file exp1/1B_structure_consistency/cases/SupplyChainPaper/reports/type_consistency_report.json
```

------

### Step 8：执行属性保持检查

执行：

```bash
python scripts/check_attribute_preservation.py \
  --bpmn-tag exp1/1B_structure_consistency/cases/SupplyChainPaper/bpmn/bpmn_tag.json \
  --dsl-tag exp1/1B_structure_consistency/cases/SupplyChainPaper/dsl/dsl_tag.json \
  --trace exp1/1B_structure_consistency/cases/SupplyChainPaper/trace/bpmn_dsl_trace.json \
  --contract exp1/1B_structure_consistency/cases/SupplyChainPaper/trace/mapping_contract.json \
  --out-file exp1/1B_structure_consistency/cases/SupplyChainPaper/reports/attribute_preservation_report.json
```

------

### Step 9：执行关系保持检查

执行：

```bash
python scripts/check_relation_preservation.py \
  --bpmn-tag exp1/1B_structure_consistency/cases/SupplyChainPaper/bpmn/bpmn_tag.json \
  --dsl-tag exp1/1B_structure_consistency/cases/SupplyChainPaper/dsl/dsl_tag.json \
  --trace exp1/1B_structure_consistency/cases/SupplyChainPaper/trace/bpmn_dsl_trace.json \
  --contract exp1/1B_structure_consistency/cases/SupplyChainPaper/trace/mapping_contract.json \
  --out-file exp1/1B_structure_consistency/cases/SupplyChainPaper/reports/relation_preservation_report.json
```

------

### Step 10：执行无伪造目标元素检查

执行：

```bash
python scripts/check_spurious_targets.py \
  --dsl-tag exp1/1B_structure_consistency/cases/SupplyChainPaper/dsl/dsl_tag.json \
  --trace exp1/1B_structure_consistency/cases/SupplyChainPaper/trace/bpmn_dsl_trace.json \
  --contract exp1/1B_structure_consistency/cases/SupplyChainPaper/trace/mapping_contract.json \
  --out-file exp1/1B_structure_consistency/cases/SupplyChainPaper/reports/spurious_target_report.json
```

------

### Step 11：执行附加 logical_path 结构可追踪性检查

执行：

```bash
python scripts/check_exp3_path_traceability.py \
  --logical-path-dir exp3/cases/SupplyChainPaper/paths \
  --dsl-tag exp1/1B_structure_consistency/cases/SupplyChainPaper/dsl/dsl_tag.json \
  --trace exp1/1B_structure_consistency/cases/SupplyChainPaper/trace/bpmn_dsl_trace.json \
  --out-file exp1/1B_structure_consistency/cases/SupplyChainPaper/reports/path_traceability_report.json
```

------

### Step 12：生成汇总报告

执行：

```bash
python scripts/generate_1b_summary.py \
  --report-dir exp1/1B_structure_consistency/cases/SupplyChainPaper/reports \
  --out-json exp1/1B_structure_consistency/cases/SupplyChainPaper/reports/structure_summary.json \
  --out-md exp1/1B_structure_consistency/cases/SupplyChainPaper/reports/structure_summary.md
```

------

## 12. 总入口伪代码

```text
Algorithm: Run1BStructureConsistency

Input:
  BPMN source model M_bpmn
  DSL target model M_dsl
  Exp3 logical path directory P
  Mapping contract C

Output:
  1B structure consistency reports
  optional Exp3 path traceability report

1. create input_index.json

2. G_bpmn = extract_bpmn_structure(M_bpmn)
3. G_dsl  = extract_dsl_structure(M_dsl)

4. C = load_or_build_mapping_contract()

5. T = build_traceability_links(G_bpmn, G_dsl, C)

6. R_element = check_element_coverage(G_bpmn, T, C)
7. R_type    = check_type_consistency(T, C)
8. R_attr    = check_attribute_preservation(G_bpmn, G_dsl, T, C)
9. R_rel     = check_relation_preservation(G_bpmn, G_dsl, T, C)
10. R_spur   = check_spurious_targets(G_dsl, T, C)

11. StructuralSummary = aggregate(R_element, R_type, R_attr, R_rel, R_spur)

12. if P is provided:
        R_path = []
        for each logical_path in P:
            r = check_path_traceability(logical_path, G_dsl, T)
            R_path.append(r)
        Exp3PathSummary = aggregate(R_path)

13. write all reports

14. if StructuralSummary satisfies all main pass conditions:
        return PASS
    else:
        return FAIL
```

------

## 13. 报告格式设计

### 13.1 structure_summary.json

```json
{
  "case_name": "SupplyChainPaper",
  "structural_status": "PASS",
  "exp3_path_traceability_status": "PASS",
  "metrics": {
    "element_coverage": 1.0,
    "type_consistency": 1.0,
    "attribute_preservation": 1.0,
    "relation_preservation": 1.0,
    "target_traceability": 1.0
  },
  "additional_metrics": {
    "path_traceability": 1.0
  },
  "counts": {
    "bpmn_nodes": 45,
    "dsl_nodes": 45,
    "bpmn_edges": 38,
    "dsl_edges": 38,
    "logical_paths": 6,
    "logical_path_steps": 48
  },
  "failures": []
}
```

### 13.2 structure_summary.md

```markdown
# 1B Structure Consistency Summary

## Case

SupplyChainPaper

## Main Status

PASS

## Additional Status

Exp3 Path Traceability: PASS

## Main Metrics

| Metric | Value |
|---|---:|
| Element Coverage | 100% |
| Type Consistency | 100% |
| Attribute Preservation | 100% |
| Relation Preservation | 100% |
| Target Traceability | 100% |

## Additional Metrics

| Metric | Value |
|---|---:|
| Path Traceability | 100% |

## Failures

No failures.
```

------

## 14. 失败类型

| 失败类型             | 含义                             | 常见原因                   | 影响                           |
| -------------------- | -------------------------------- | -------------------------- | ------------------------------ |
| MissingSourceMapping | BPMN 元素没有对应 DSL 元素       | 转换规则遗漏               | 结构丢失                       |
| TypeMismatch         | 源目标元素类型不一致             | 映射规则错误               | 元素语义类别错误               |
| AttributeMismatch    | 关键属性不一致                   | 字段丢失或转换错误         | 元素语义失真                   |
| RelationMissing      | BPMN 关系没有被 DSL 保留         | flow 转换遗漏              | 控制流或协作关系丢失           |
| DirectionMismatch    | 关系方向被反转                   | source/target 解析错误     | 后续路径语义错误               |
| SpuriousTarget       | DSL 中存在无来源元素             | 转换器引入额外结构         | 可能引入额外行为               |
| PathStepUntraceable  | logical_path 步骤无法追溯到 BPMN | 路径生成器使用了无来源元素 | 附加验证失败，实验三路径缺少源模型依据 |
| SyntheticNotDeclared | 辅助元素未声明                   | allowed_synthetic 未配置   | 无法区分合法辅助结构与伪造结构 |

------

## 15. 批量实验设计

如果有多个 case，建议建立：

```text
exp1/1B_structure_consistency/cases_index.json
```

示例：

```json
{
  "cases": [
    {
      "case_name": "SupplyChainPaper",
      "bpmn_file": "BPMNwithDMNcase/SupplyChainPaper.bpmn",
      "dsl_file": "exp2_semantic_verification/results/cases/SupplyChainPaper/dsl.b2c",
      "logical_paths_dir": "exp3/cases/SupplyChainPaper/paths"
    },
    {
      "case_name": "AssetTransfer",
      "bpmn_file": "BPMNwithDMNcase/AssetTransfer.bpmn",
      "dsl_file": "exp2_semantic_verification/results/cases/AssetTransfer/dsl.b2c",
      "logical_paths_dir": "exp3/cases/AssetTransfer/paths"
    }
  ]
}
```

批量运行：

```bash
python scripts/run_1b_batch.py \
  --cases-index exp1/1B_structure_consistency/cases_index.json \
  --out-dir exp1/1B_structure_consistency
```

批量汇总输出：

```text
exp1/1B_structure_consistency/batch_summary.json
exp1/1B_structure_consistency/batch_summary.md
```

------

## 16. 批量汇总表格式

```markdown
# 1B Batch Summary

| Case | Structural Status | Exp3 Path Status | BPMN Nodes | DSL Nodes | Element Coverage | Type Consistency | Attribute Preservation | Relation Preservation | Path Traceability |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| SupplyChainPaper | PASS | PASS | 45 | 45 | 100% | 100% | 100% | 100% | 100% |
| AssetTransfer | PASS | PASS | 52 | 52 | 100% | 100% | 100% | 100% | 100% |
```

------

## 17. 与实验三的衔接方式

实验三使用的路径文件：

```text
logical_path.json
```

附加验证对实验三的前置保障是：

```text
1. logical_path 中的每个 step.element 存在于 DSL-TAG；
2. 每个 step.element 都存在 BPMN→DSL trace link；
3. 每个 step.element 的关键前后继关系，在 BPMN-TAG 和 DSL-TAG 中保持一致；
4. 因此，该 logical_path 的结构来源可以追溯到 BPMN。
```

建议在实验执行流程中设置两个 gate：

```text
if StructuralConsistency == PASS:
    allow running 1C
else:
    stop and report structural inconsistency

if StructuralConsistency == PASS and Exp3PathTraceability == PASS:
    allow running Exp3
else:
    stop and report path traceability issue
```

------

## 18. 推荐实现优先级

### P0：最小闭环

必须实现：

```text
extract_bpmn_structure.py
extract_dsl_structure.py
build_bpmn_dsl_trace.py
check_element_coverage.py
check_relation_preservation.py
generate_1b_summary.py
```

必须产出：

```text
bpmn_tag.json
dsl_tag.json
bpmn_dsl_trace.json
element_coverage_report.json
relation_preservation_report.json
structure_summary.md
```

附加验证必须实现：

```text
check_exp3_path_traceability.py
```

附加验证必须产出：

```text
path_traceability_report.json
```

### P1：增强检查

继续实现：

```text
check_type_consistency.py
check_attribute_preservation.py
check_spurious_targets.py
```

### P2：批量与可视化

最后实现：

```text
run_1b_batch.py
batch_summary.md
failure_diff_viewer.py
```

------

## 19. 最小闭环流程

如果时间有限，按以下顺序做：

```text
1. 解析 BPMN，生成 bpmn_tag.json；
2. 解析 DSL，生成 dsl_tag.json；
3. 根据 id 和映射契约生成 bpmn_dsl_trace.json；
4. 检查 BPMN 元素是否都映射到 DSL；
5. 检查 BPMN sequence/message/branch/join 关系是否映射到 DSL；
6. 输出 structure_summary.md；
7. 如果需要衔接实验三，再执行 logical_path 附加可追踪性检查。
```

最小闭环完成后，1B 主体验证已经可以支撑后续 1C；附加验证通过后，可以支撑实验三路径回放。

------

## 20. 目录结构建议

```text
Experiment/
  exp1/
    1B_structure_consistency/
      scripts/
        run_1b_structure_consistency.py
        run_1b_batch.py
        extract_bpmn_structure.py
        extract_dsl_structure.py
        build_mapping_contract.py
        build_bpmn_dsl_trace.py
        check_element_coverage.py
        check_type_consistency.py
        check_attribute_preservation.py
        check_relation_preservation.py
        check_spurious_targets.py
        check_exp3_path_traceability.py
        generate_1b_summary.py

      contracts/
        default_mapping_contract.json

      cases_index.json

      cases/
        <CaseName>/
          input_index.json
          bpmn/
          dsl/
          trace/
          reports/

      batch_summary.json
      batch_summary.md
```

------

## 21. 实验完成标准

一个 case 的 1B 实验完成标准：

```text
1. bpmn_tag.json 已生成；
2. dsl_tag.json 已生成；
3. mapping_contract.json 已生成；
4. bpmn_dsl_trace.json 已生成；
5. 五类主体结构检查报告已生成；
6. structure_summary.json 已生成；
7. structure_summary.md 已生成；
8. structural_status 为 PASS 或明确列出所有失败项；
9. 所有主体结构失败项都能定位到具体 source element 或 target element。
```

附加验证完成标准：

```text
1. logical_path 可追踪性检查已完成；
2. path_traceability_report.json 已生成；
3. exp3_path_traceability_status 为 PASS 或明确列出所有失败项；
4. 所有附加验证失败项都能定位到具体 path step。
```

批量实验完成标准：

```text
1. 所有 case 均完成 1B 检查；
2. batch_summary.json 已生成；
3. batch_summary.md 已生成；
4. 每个 FAIL case 均有 failure 明细；
5. 每个 StructuralConsistency PASS case 均可进入 1C；
6. 每个 StructuralConsistency 与 Exp3PathTraceability 均 PASS 的 case 均可进入实验三。
```

------

## 22. 实验最终产物清单

最终应保留以下文件：

```text
default_mapping_contract.json
cases_index.json

每个 case：
  input_index.json
  bpmn_tag.json
  dsl_tag.json
  bpmn_dsl_trace.json
  element_coverage_report.json
  type_consistency_report.json
  attribute_preservation_report.json
  relation_preservation_report.json
  spurious_target_report.json
  structure_summary.json
  structure_summary.md

附加验证：
  path_traceability_report.json

批量结果：
  batch_summary.json
  batch_summary.md
```

------

## 23. 一句话总结

实验 1B 的完整执行逻辑是：

```text
先把 BPMN 和 DSL 各自抽取成类型化属性图，
再根据映射契约建立 BPMN→DSL traceability link，
然后检查元素、类型、属性、关系和无来源目标元素是否一致，
最终输出结构一致性报告。

实验三 logical_path 可追踪性作为附加验证单独执行，
用于确认实验三路径步骤具有 BPMN 源模型结构依据。
```
