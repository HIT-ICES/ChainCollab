# 实验 1B：BPMN→DSL 源目标结构一致性验证详细实验方案

## 1. 实验目标

实验 1B 用于验证 BPMN 源模型转换为 DSL 目标模型后，源模型中的关键结构信息是否被完整、正确、可追踪地保留。

本实验关注 BPMN→DSL 转换后的结构层一致性，围绕元素覆盖、类型映射、属性保持、关系保持和目标可追踪性形成闭环验证。

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

该附加验证用于确认实验三路径文件中的 DSL 步骤具备 BPMN 源模型依据。

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

该部分作为 1B 与实验三的衔接检查，形成对实验三路径输入的结构来源确认。


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
/root/code/ChainCollab/Experiment/BPMNwithDMNcase/<CaseName>.bpmn
```

需要从 BPMN 中抽取：

```text
participant
message
startEvent
endEvent
messageFlow
choreographyTask
businessRuleTask
receiveTask
scriptTask
exclusiveGateway
parallelGateway
eventBasedGateway
sequenceFlow
sourceRef
targetRef
message sender
message receiver
message documentation properties
businessRuleTask documentation inputs / outputs
sequenceFlow conditionExpression / name
gateway branch
gateway join
```

### 4.2 DSL 目标模型

输入文件示例：

```text
/root/code/ChainCollab/Experiment/new/exp1_1B/cases/<CaseName>/dsl/<CaseName>.b2c
```

该文件由实验入口脚本调用 `src/newTranslator/generator/bpmn_to_dsl.py` 从 BPMN 实时生成，不再使用旧方案中的 exp2 输出目录作为 1B 主输入。

调试时也可以直接传入已有 DSL 文件给 `extract_dsl_structure.py`：

```text
任意可解析的 .b2c 文件
```

需要从 DSL 中抽取：

```text
participant
event
message
gateway
businessrule
oracletask
global
flow
enable relation
start_enables relation
disable relation
gateway_branch relation
parallel_join_source relation
message_sender relation
message_receiver relation
sender
receiver
input
output
msp
x509
attributes
```

### 4.3 实验三路径文件（附加验证输入）

输入文件示例：

```text
/root/code/ChainCollab/Experiment/new/exp3/cases/<CaseName>/paths/<PathName>/logical_path.json
```

用途：作为附加验证输入，检查实验三中用于回放的每个 logical step 是否能追溯到 BPMN 源元素。

------

## 5. 实验输出目录

实际输出目录如下：

```text
/root/code/ChainCollab/Experiment/new/exp1_1B/
  contracts/
    default_mapping_contract.json

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
        bpmn_dsl_trace.json

      reports/
        element_coverage_report.json
        type_consistency_report.json
        attribute_preservation_report.json
        relation_preservation_report.json
        spurious_target_report.json
        structure_summary.json
        structure_summary.md

    batch_summary.json
    batch_summary.md

  Addition/
    cases/
      <CaseName>/
        path_traceability_report.json
        path_traceability_summary.md

      addition_batch_summary.json
      addition_batch_summary.md
```

------

## 6. 核心中间产物设计

### 6.1 input_index.json

记录一个 case 的所有输入路径。

```json
{
  "case_name": "SupplyChainPaper",
  "bpmn_file": "/root/code/ChainCollab/Experiment/BPMNwithDMNcase/SupplyChainPaper.bpmn",
  "dsl_file": "/root/code/ChainCollab/Experiment/new/exp1_1B/cases/SupplyChainPaper/dsl/SupplyChainPaper.b2c",
  "mapping_contract": "/root/code/ChainCollab/Experiment/new/exp1_1B/contracts/default_mapping_contract.json",
  "translator_root": "/root/code/ChainCollab/src/newTranslator"
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
      "id": "Message_001",
      "type": "message",
      "name": "SubmitOrder",
      "attrs": {
        "message_ref": "Message_001",
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
      "source": "Message_001",
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
      "id": "Message_001",
      "type": "message",
      "name": "Message_001",
      "attrs": {
        "source": "Participant_Buyer",
        "target": "Participant_Seller",
        "schema": "{}"
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
      "source": "Message_001",
      "target": "Gateway_001",
      "type": "enable"
    }
  ]
}
```

------

### 6.4 mapping_contract.json

映射契约用于定义 BPMN 元素、派生元素和结构关系到 DSL 的合法映射关系。本实验以 `contracts/default_mapping_contract.json` 为准，契约分为 `element_rules`、`non_direct_element_rules`、`relation_rules`、`activation_target_policy`、`allowed_synthetic_targets`、`ignored_or_non_convertible_sources` 和 `normalization` 等部分。

```json
{
  "contract_version": "0.1.0",
  "element_rules": [
    {
      "rule_name": "Participant2Participant",
      "source_type": "bpmn:participant",
      "target_type": "dsl:participant",
      "cardinality": "1:1"
    },
    {
      "rule_name": "MessageRef2Message",
      "source_type": "bpmn:message",
      "source_context": "referenced by bpmn:messageFlow.messageRef",
      "target_type": "dsl:message",
      "cardinality": "1:1"
    },
    {
      "rule_name": "MessageFlowEndpoints2MessageParticipants",
      "source_type": "bpmn:messageFlow",
      "target_type": "dsl:message",
      "cardinality": "1:1 via messageRef"
    },
    {
      "rule_name": "StartEvent2Event",
      "source_type": "bpmn:startEvent",
      "target_type": "dsl:event",
      "target_expected_attributes": {
        "initialState": "READY"
      }
    },
    {
      "rule_name": "EndEvent2Event",
      "source_type": "bpmn:endEvent",
      "target_type": "dsl:event",
      "target_expected_attributes": {
        "initialState": "INACTIVE"
      }
    },
    {
      "rule_name": "ExclusiveGateway2Gateway",
      "source_type": "bpmn:exclusiveGateway",
      "target_type": "dsl:gateway",
      "target_expected_attributes": {
        "gatewayType": "exclusive",
        "initialState": "INACTIVE"
      }
    },
    {
      "rule_name": "ParallelGateway2Gateway",
      "source_type": "bpmn:parallelGateway",
      "target_type": "dsl:gateway",
      "target_expected_attributes": {
        "gatewayType": "parallel",
        "initialState": "INACTIVE"
      }
    },
    {
      "rule_name": "EventBasedGateway2Gateway",
      "source_type": "bpmn:eventBasedGateway",
      "target_type": "dsl:gateway",
      "target_expected_attributes": {
        "gatewayType": "event",
        "initialState": "INACTIVE"
      }
    },
    {
      "rule_name": "BusinessRuleTask2BusinessRule",
      "source_type": "bpmn:businessRuleTask",
      "target_type": "dsl:businessrule",
      "target_expected_attributes": {
        "dmnResource": "{source.id}.dmn",
        "decisionID": "{source.id}_DecisionID",
        "initialState": "INACTIVE"
      }
    },
    {
      "rule_name": "ReceiveTask2OracleTask",
      "source_type": "bpmn:receiveTask",
      "target_type": "dsl:oracletask",
      "required": false
    },
    {
      "rule_name": "ScriptTask2OracleTask",
      "source_type": "bpmn:scriptTask",
      "target_type": "dsl:oracletask",
      "required": false
    },
    {
      "rule_name": "MessageProperty2GlobalVar",
      "source_type": "bpmn:messageProperty",
      "source_context": "message.documentation.properties",
      "target_type": "dsl:global",
      "cardinality": "n:1 by property name",
      "required": false
    },
    {
      "rule_name": "BusinessRuleIO2GlobalVar",
      "source_type": "bpmn:businessRuleParameter",
      "source_context": "businessRuleTask.documentation.inputs/outputs",
      "target_type": "dsl:global",
      "cardinality": "n:1 by parameter name",
      "required": false
    },
    {
      "rule_name": "SequenceConditionVariable2GlobalVar",
      "source_type": "bpmn:sequenceConditionVariable",
      "source_context": "sequenceFlow.conditionExpression or sequenceFlow.name",
      "target_type": "dsl:global",
      "cardinality": "n:1 by variable name",
      "required": false
    }
  ],
  "non_direct_element_rules": [
    {
      "rule_name": "ChoreographyTaskExpansion",
      "source_type": "bpmn:choreographyTask",
      "target_type": "none",
      "status": "expanded"
    },
    {
      "rule_name": "MessageFlowNoDirectNode",
      "source_type": "bpmn:messageFlow",
      "target_type": "none",
      "status": "represented_by_message_node_and_sender_receiver_attrs"
    }
  ],
  "relation_rules": [
    {
      "rule_name": "StartEventSequence2StartFlow",
      "source_relation": "bpmn:sequenceFlow",
      "target_relation": "dsl:start_enables",
      "preserve_direction": true
    },
    {
      "rule_name": "ChoreographyTaskMessageOrder2MessageFlow",
      "source_relation": "bpmn:choreographyTask.messageFlowRef",
      "target_relation": "dsl:enable",
      "preserve_direction": true
    },
    {
      "rule_name": "SequenceFlow2FlowEnable",
      "source_relation": "bpmn:sequenceFlow",
      "target_relation": "dsl:enable",
      "required": false
    },
    {
      "rule_name": "EventBasedGatewayBranches2DisableEnable",
      "source_relation": "bpmn:eventBasedGateway.branch",
      "target_relation": "dsl:disable + dsl:enable"
    },
    {
      "rule_name": "ExclusiveGatewayCondition2GatewayBranch",
      "source_relation": "bpmn:sequenceFlow.condition",
      "target_relation": "dsl:gateway_branch"
    },
    {
      "rule_name": "ParallelGatewayJoin2ParallelJoin",
      "source_relation": "bpmn:parallelGateway.join",
      "target_relation": "dsl:parallel_join_source + dsl:enable"
    },
    {
      "rule_name": "BusinessRuleSequence2RuleFlow",
      "source_relation": "bpmn:sequenceFlow",
      "target_relation": "dsl:enable"
    },
    {
      "rule_name": "OracleTaskSequence2OracleTaskFlow",
      "source_relation": "bpmn:sequenceFlow",
      "target_relation": "dsl:enable"
    },
    {
      "rule_name": "MessageFlowEndpoints2SenderReceiver",
      "source_relation": "bpmn:messageFlow",
      "target_relation": "dsl:message_sender + dsl:message_receiver",
      "preserve_direction": true
    }
  ],
  "allowed_synthetic_targets": [
    {
      "type": "dsl:global",
      "reason": "derived from BPMN message documentation, business rule I/O, oracle output mappings, or sequence-flow condition variables"
    },
    {
      "type": "dsl:participant.msp",
      "reason": "derived from generator bindings/default identity policy"
    },
    {
      "type": "dsl:participant.x509",
      "reason": "derived from generator bindings/default identity policy"
    },
    {
      "type": "dsl:participant.attributes",
      "reason": "derived from generator bindings/default role policy"
    }
  ]
}
```

注意：`default_mapping_contract.json` 是完整映射契约；当前 1B 检查脚本只实现了其中的一个主体子集。实际 PASS/FAIL 以 `build_bpmn_dsl_trace.py` 和 `check_structure_consistency.py` 中的 `DIRECT_RULES`、`DIRECT_TYPES`、关系检查函数和 spurious target 集合为准。

------

### 6.5 bpmn_dsl_trace.json

源目标追踪文件，用于记录 BPMN 元素到 DSL 元素的映射。

```json
{
  "case_name": "SupplyChainPaper",
  "links": [
    {
      "source_id": "Message_001",
      "source_type": "bpmn:message",
      "target_id": "Message_001",
      "target_type": "dsl:message",
      "rule_name": "MessageRef2Message",
      "status": "matched",
      "match_method": "id",
      "preserved_attributes": {
        "id": true,
        "name": true,
        "schema": true
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
bpmn_dsl_trace.json
```

### 检查对象

```text
participant
message
startEvent
endEvent
exclusiveGateway
parallelGateway
eventBasedGateway
businessRuleTask
receiveTask
scriptTask
dataTask（按 ReceiveTask2OracleTask 映射到 oracletask）
choreographyTask
```

当前实现中，`messageFlow` 是 BPMN edge，不计入 C1 的直接节点覆盖率，而是在 C4 关系保持中检查 sender/receiver；`messageProperty`、`businessRuleParameter`、`sequenceConditionVariable` 作为 derived 信息参与 trace 构建，但不计入当前 C1/C2 的主体通过率。

### 检查逻辑

```text
for each source_node in bpmn_tag.nodes:
    if source_node.type belongs to DIRECT_TYPES:
        find trace link where link.source_id == source_node.id

        if link exists:
            mark source_node as mapped
        else:
            mark source_node as missing

for each choreographyTask in bpmn_tag.nodes:
    check represented_sources has non-empty represented_by
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

如果存在无法转换或不需要转换的 BPMN 元素，必须在 mapping_contract.json 中声明为 ignored 或 non_convertible。当前契约中 `choreographyTask`、`messageFlow`、`sequenceFlow` 不要求生成同名 DSL 节点：`choreographyTask` 展开为消息与流程关系，`messageFlow` 由 message 节点及 sender/receiver 关系表示，`sequenceFlow` 由 DSL flow/action 关系表示。

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
bpmn:participant                 → dsl:participant
bpmn:message                     → dsl:message
bpmn:startEvent                  → dsl:event(initialState=READY)
bpmn:endEvent                    → dsl:event(initialState=INACTIVE)
bpmn:exclusiveGateway            → dsl:gateway(gatewayType=exclusive)
bpmn:parallelGateway             → dsl:gateway(gatewayType=parallel)
bpmn:eventBasedGateway           → dsl:gateway(gatewayType=event)
bpmn:businessRuleTask            → dsl:businessrule
bpmn:receiveTask                 → dsl:oracletask
bpmn:scriptTask                  → dsl:oracletask
bpmn:dataTask                    → dsl:oracletask
```

`bpmn:messageFlow → dsl:message via messageRef` 当前记录在 `relation_links`，不进入 C2 的 `total_trace_links` 统计。

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
bpmn_dsl_trace.json
```

### 检查内容

#### MessageFlow / Message

```text
BPMN message.id             == DSL message.id
BPMN message.id             == DSL message.name
BPMN message.documentation  == DSL message.schema（按契约 schema 规则规范化）
```

messageFlow 的 source/target 不在 C3 属性保持中检查，而是在 C4 关系保持中检查 `dsl:message_sender` 和 `dsl:message_receiver`。

#### Participant

```text
BPMN id    == DSL id
BPMN id    == DSL name
BPMN is_multi / multi_minimum / multi_maximum == DSL isMulti / multiMin / multiMax
BPMN name  不要求等于 DSL name，只作为 msp / attributes 默认值的 name_hint
```

#### Event

```text
BPMN startEvent.id == DSL event.id
BPMN startEvent.id == DSL event.name
DSL startEvent.initialState == READY
BPMN endEvent.id == DSL event.id
BPMN endEvent.id == DSL event.name
DSL endEvent.initialState == INACTIVE
```

#### Gateway

```text
BPMN exclusiveGateway.id  == DSL gateway.id
BPMN parallelGateway.id   == DSL gateway.id
BPMN eventBasedGateway.id == DSL gateway.id
DSL gateway.gatewayType   == exclusive / parallel / event
```

#### BusinessRuleTask / BusinessRule

```text
BPMN businessRuleTask.id == DSL businessrule.id
BPMN businessRuleTask.id == DSL businessrule.name
DSL dmnResource                   == {source.id}.dmn
DSL decisionID                    == {source.id}_DecisionID
```

BPMN documentation 中的 inputs / outputs 通过 DSL paramMapping 及相关结构关系保留。

#### ReceiveTask / ScriptTask / OracleTask

```text
BPMN receiveTask.id / scriptTask.id == DSL oracletask.id
BPMN receiveTask.id / scriptTask.id == DSL oracletask.name
```

#### Global 变量

```text
DSL global 的生成来源保留在 bpmn_tag.derived 与 trace links 中；
global 作为 message schema、businessrule output、oracletask output 和 guard 变量的结构上下文参与可追踪性检查。
```

### 检查逻辑

```text
for each trace_link in bpmn_dsl_trace.links:
    source_node = find bpmn node by trace_link.source_id
    target_node = find dsl node by trace_link.target_id

    attribute_checks = hardcoded checks in check_structure_consistency.py

    for each check in attribute_checks:
        normalize source value with local helper when needed
        normalize target value with local helper when needed
        compare source value and target value
```

### 属性规范化规则

```text
去除首尾空格；
直接元素使用 BPMN id 与 DSL id / name 比较；
message schema 使用 summarize_message_schema 从 BPMN documentation 生成可比较字符串；
participant multiplicity 转换为布尔值和整数后比较；
gatewayType、event initialState、businessrule dmnResource / decisionID 使用脚本中的期望值比较。
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
  "attribute": "message_receiver",
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
bpmn_dsl_trace.json
```

### 检查关系类型

```text
messageFlow
choreographyTask.messageFlowRef
startEvent sequenceFlow
parallelGateway join
parallelGateway outgoing enable
```

### 检查逻辑

#### 1. startEvent sequenceFlow → start_enables relation

```text
BPMN startEvent --sequenceFlow--> activation_target(B)
  检查 DSL 中是否存在 start_enables(startEvent.id → activation_target(B))
```

#### 2. choreographyTask.messageFlowRef → message enable relation

```text
BPMN choreographyTask 的 init message 和 return message
  如果 init 和 return 均存在，检查 enable(init.messageRef → return.messageRef)
  如果只有 init，检查 enable(init.messageRef → activation_target(choreographyTask.outgoing.target))
  如果存在 return，检查 enable(return.messageRef → activation_target(choreographyTask.outgoing.target))
```

#### 3. parallelGateway outgoing → enable relation

```text
BPMN parallelGateway with zero or one incoming
  对每个 outgoing sequenceFlow，找到 activation_target(outgoing.target)
  检查 DSL 中存在 enable(gateway.id → activation_target(outgoing.target))
```


#### 4. messageFlow endpoint → message sender / receiver relation

```text
BPMN messageFlow(messageRef=M, sourceRef=A, targetRef=B)
  检查 DSL message(M) 存在
  检查 DSL 中存在 message_sender(M → A)
  检查 DSL 中存在 message_receiver(M → B)
```

#### 5. eventBasedGateway branch → disable + enable relation

```text
BPMN eventBasedGateway 的每个候选分支映射为 DSL 中的 event gateway 分支启用关系；
被选中的 message 分支通过 disable relation 排除其他候选 message。
```

#### 6. exclusiveGateway condition → gateway_branch relation

```text
BPMN exclusiveGateway 的 outgoing conditionExpression / name
  映射为 DSL gateway_branch relation 中的 guard 条件；
  检查分支目标 activation_target 是否与 DSL enable action 对齐。
```


#### 7. parallelGateway join → parallel_join_source + enable relation

```text
BPMN parallelGateway with more than one incoming
  检查每个 incoming.source 的 activation_target 到 gateway 存在 parallel_join_source
  检查 gateway 到每个 outgoing.target 的 activation_target 存在 enable
```

#### 8. businessRuleTask / oracleTask sequenceFlow → typed flow relation

```text
BPMN businessRuleTask / receiveTask / scriptTask 的 outgoing sequenceFlow
  映射为 DSL 中对应 businessrule / oracletask 完成后的 enable relation；
  检查后继 activation_target 是否被结构性保留。
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
    "source": "Message_001",
    "target": "Gateway_001"
  },
  "expected_target_relation": {
    "type": "enable",
    "source": "Message_001",
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
BPMN 中的消息协作关系、start event 启动关系、choreography task 消息展开关系、parallel gateway join/source 关系以及 parallel gateway outgoing enable 关系，在 DSL 中被结构性保留。
```

------

## 7.5 C5：无伪造目标元素检查

### 检查目的

验证 DSL 中不存在无 BPMN 来源的关键业务元素。

### 输入

```text
dsl_tag.json
bpmn_dsl_trace.json
```

### 检查逻辑

```text
for each target_node in dsl_tag.nodes:
    if target_node.type belongs to critical_types:
        check exists trace link where link.target_id == target_node.id

        if not traceable:
            mark as spurious target
```

### critical_types 示例

```text
participant
event
message
gateway
businessrule
oracletask
```

### 上下文元素

```text
dsl:global
dsl:attribute
dsl:paramMapping
dsl:participant.msp
dsl:participant.x509
dsl:participant.attributes
```

这些元素作为 DSL 的结构上下文参与属性、参数映射和关系解释；C5 的关键目标元素聚焦 participant、event、message、gateway、businessrule、oracletask 六类可触发或业务关键节点。

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

该部分是 1B 与实验三之间的衔接验证，用于确认实验三路径中的 DSL 元素具有 BPMN 来源。

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
  "exp3_path_traceability_status": "PASS",
  "logical_paths": 2,
  "logical_path_steps": 18,
  "traceable_logical_path_steps": 18,
  "untraceable_logical_path_steps": 0,
  "overall_path_traceability": 1.0,
  "paths": [
    {
      "path_name": "path_001",
      "logical_path_file": ".../path_001/logical_path.json",
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
  ]
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

当前实现采用严格判定，不支持通过配置放宽某个属性或关系检查；如果后续允许部分属性不一致，需要同步修改 `default_mapping_contract.json` 和 `check_structure_consistency.py`。

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

### 10.1 单 case 主入口脚本

```text
scripts/run_supplychainpaper_demo.py
```

运行示例：

```bash
cd /root/code/ChainCollab
python Experiment/new/exp1_1B/scripts/run_supplychainpaper_demo.py \
  --case-name SupplyChainPaper \
  --bpmn-file Experiment/BPMNwithDMNcase/SupplyChainPaper.bpmn \
  --out-dir Experiment/new/exp1_1B/cases/SupplyChainPaper
```

该脚本实际执行以下动作：

```text
1. 调用 src/newTranslator/generator/bpmn_to_dsl.py 生成 cases/<CaseName>/dsl/<CaseName>.b2c；
2. 抽取 BPMN TAG；
3. 抽取 DSL TAG；
4. 使用 contracts/default_mapping_contract.json 生成 bpmn_dsl_trace.json；
5. 调用 check_structure_consistency.py 一次性生成 C1-C5 报告和 structure_summary。
```

### 10.2 批量主入口脚本

```text
scripts/run_all_bpmn_cases.py
```

运行示例：

```bash
cd /root/code/ChainCollab
python Experiment/new/exp1_1B/scripts/run_all_bpmn_cases.py \
  --bpmn-dir Experiment/BPMNwithDMNcase \
  --out-dir Experiment/new/exp1_1B/cases
```

### 10.3 附加验证脚本

```text
Addition/scripts/check_exp3_path_traceability.py
Addition/scripts/run_all_addition_cases.py
```

运行示例：

```bash
cd /root/code/ChainCollab
python Experiment/new/exp1_1B/Addition/scripts/run_all_addition_cases.py
```

### 10.4 子脚本列表

```text
scripts/extract_bpmn_structure.py
scripts/extract_dsl_structure.py
scripts/build_bpmn_dsl_trace.py
scripts/check_structure_consistency.py
scripts/run_supplychainpaper_demo.py
scripts/run_all_bpmn_cases.py
Addition/scripts/check_exp3_path_traceability.py
Addition/scripts/run_all_addition_cases.py
```

C1-C5 的检查逻辑集中在 `scripts/check_structure_consistency.py` 中执行；映射契约生成、trace 构建、结构检查和汇总由主流程统一调度。

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
translator-root 是否存在；
translator-python 是否存在；
输出目录是否可写。
```

------

### Step 2：生成 DSL

执行：

```bash
/root/code/ChainCollab/src/newTranslator/.venv/bin/python \
  /root/code/ChainCollab/src/newTranslator/generator/bpmn_to_dsl.py \
  /root/code/ChainCollab/Experiment/BPMNwithDMNcase/SupplyChainPaper.bpmn \
  -o /root/code/ChainCollab/Experiment/new/exp1_1B/cases/SupplyChainPaper/dsl/SupplyChainPaper.b2c \
  --name SupplyChainPaper
```

生成：

```text
cases/SupplyChainPaper/dsl/SupplyChainPaper.b2c
```

------

### Step 3：抽取 BPMN 结构

执行：

```bash
python Experiment/new/exp1_1B/scripts/extract_bpmn_structure.py \
  --bpmn-file Experiment/BPMNwithDMNcase/SupplyChainPaper.bpmn \
  --case-name SupplyChainPaper \
  --out-dir Experiment/new/exp1_1B/cases/SupplyChainPaper/bpmn
```

生成：

```text
bpmn_elements.json
bpmn_relations.json
bpmn_tag.json
```

------

### Step 4：抽取 DSL 结构

执行：

```bash
python Experiment/new/exp1_1B/scripts/extract_dsl_structure.py \
  --dsl-file Experiment/new/exp1_1B/cases/SupplyChainPaper/dsl/SupplyChainPaper.b2c \
  --case-name SupplyChainPaper \
  --out-dir Experiment/new/exp1_1B/cases/SupplyChainPaper/dsl
```

生成：

```text
dsl_elements.json
dsl_relations.json
dsl_tag.json
```

------

### Step 5：生成 traceability link

执行：

```bash
python Experiment/new/exp1_1B/scripts/build_bpmn_dsl_trace.py \
  --bpmn-tag Experiment/new/exp1_1B/cases/SupplyChainPaper/bpmn/bpmn_tag.json \
  --dsl-tag Experiment/new/exp1_1B/cases/SupplyChainPaper/dsl/dsl_tag.json \
  --contract Experiment/new/exp1_1B/contracts/default_mapping_contract.json \
  --out-file Experiment/new/exp1_1B/cases/SupplyChainPaper/trace/bpmn_dsl_trace.json
```

生成：

```text
bpmn_dsl_trace.json
```

当前匹配实现：

```text
1. DIRECT_RULES 中声明的直接元素按 same_id 匹配；
2. bpmn:messageFlow 通过 messageRef 匹配 dsl:message，并写入 relation_links；
3. bpmn:choreographyTask 写入 represented_sources，用其 messageFlowRef 对应的 message 表示；
4. bpmn_tag.derived 中的派生变量按 derived_target 匹配 DSL global；
5. 未匹配的关键 DSL 目标元素写入 unmatched_targets。
```

------

### Step 6：执行 C1-C5 主体结构一致性检查

执行：

```bash
python Experiment/new/exp1_1B/scripts/check_structure_consistency.py \
  --bpmn-tag Experiment/new/exp1_1B/cases/SupplyChainPaper/bpmn/bpmn_tag.json \
  --dsl-tag Experiment/new/exp1_1B/cases/SupplyChainPaper/dsl/dsl_tag.json \
  --trace Experiment/new/exp1_1B/cases/SupplyChainPaper/trace/bpmn_dsl_trace.json \
  --report-dir Experiment/new/exp1_1B/cases/SupplyChainPaper/reports
```

该脚本一次性生成 `element_coverage_report.json`、`type_consistency_report.json`、`attribute_preservation_report.json`、`relation_preservation_report.json`、`spurious_target_report.json`、`structure_summary.json` 和 `structure_summary.md`。

------

### Step 7：执行附加 logical_path 结构可追踪性检查

执行：

```bash
python Experiment/new/exp1_1B/Addition/scripts/check_exp3_path_traceability.py \
  --case-name SupplyChainPaper \
  --logical-paths-dir Experiment/new/exp3/cases/SupplyChainPaper/paths \
  --dsl-tag Experiment/new/exp1_1B/cases/SupplyChainPaper/dsl/dsl_tag.json \
  --trace Experiment/new/exp1_1B/cases/SupplyChainPaper/trace/bpmn_dsl_trace.json \
  --out-dir Experiment/new/exp1_1B/Addition/cases/SupplyChainPaper
```

生成：

```text
Addition/cases/SupplyChainPaper/path_traceability_report.json
Addition/cases/SupplyChainPaper/path_traceability_summary.md
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

4. C = load(default_mapping_contract.json)

5. T = build_traceability_links(G_bpmn, G_dsl, C)

6. {R_element, R_type, R_attr, R_rel, R_spur}
      = check_structure_consistency(G_bpmn, G_dsl, T)

7. StructuralSummary = aggregate(R_element, R_type, R_attr, R_rel, R_spur)

8. if P is provided:
        R_path = []
        for each logical_path in P:
            r = check_path_traceability(logical_path, G_dsl, T)
            R_path.append(r)
        Exp3PathSummary = aggregate(R_path)

9. write all reports

10. if StructuralSummary satisfies all main pass conditions:
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
  "metrics": {
    "element_coverage": 1.0,
    "type_consistency": 1.0,
    "attribute_preservation": 1.0,
    "relation_preservation": 1.0,
    "target_traceability": 1.0
  },
  "counts": {
    "bpmn_nodes": 60,
    "bpmn_edges": 123,
    "dsl_nodes": 72,
    "dsl_edges": 115
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

## Main Metrics

| Metric | Value |
|---|---:|
| Element Coverage | 100% |
| Type Consistency | 100% |
| Attribute Preservation | 100% |
| Relation Preservation | 100% |
| Target Traceability | 100% |

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

------

## 15. 批量实验设计

当前实现不使用 `cases_index.json`。批量脚本直接扫描 BPMN 目录中的 `*.bpmn` 文件，并对每个文件调用单 case 主入口。

批量运行：

```bash
cd /root/code/ChainCollab
python Experiment/new/exp1_1B/scripts/run_all_bpmn_cases.py \
  --bpmn-dir Experiment/BPMNwithDMNcase \
  --out-dir Experiment/new/exp1_1B/cases
```

批量汇总输出：

```text
Experiment/new/exp1_1B/cases/batch_summary.json
Experiment/new/exp1_1B/cases/batch_summary.md
```

当前已完成 11 个 BPMN case 的批量验证：`Blood_analysis`、`Hotel_Booking`、`ManagementSystem`、`Pizza_Order`、`Purchase`、`Rental_Claim`、`SupplyChain`、`SupplyChainPaper`、`amazon`、`customer`、`manufactory`，主体结构一致性结果均为 PASS。

------

## 16. 批量汇总表格式

```markdown
# Experiment 1B Batch Summary

| Metric | Value |
|---|---:|
| total_cases | 11 |
| passed | 11 |
| failed | 0 |
| errored | 0 |

| Case | Status | Return Code | Summary |
|---|---|---:|---|
| SupplyChainPaper | PASS | 0 | `.../cases/SupplyChainPaper/reports/structure_summary.md` |
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
3. trace link 可以来自 links、relation_links 或 represented_sources；
4. 因此，该 logical_path 的每个步骤元素具有 BPMN 来源。
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

已实现：

```text
extract_bpmn_structure.py
extract_dsl_structure.py
build_bpmn_dsl_trace.py
check_structure_consistency.py
run_supplychainpaper_demo.py
```

必须产出：

```text
bpmn_tag.json
dsl_tag.json
bpmn_dsl_trace.json
element_coverage_report.json
relation_preservation_report.json
type_consistency_report.json
attribute_preservation_report.json
spurious_target_report.json
structure_summary.md
```

附加验证已实现：

```text
Addition/scripts/check_exp3_path_traceability.py
```

附加验证必须产出：

```text
path_traceability_report.json
```

### P1：增强检查

当前增强检查已并入 `check_structure_consistency.py`：

```text
type_consistency_report.json
attribute_preservation_report.json
spurious_target_report.json
```

### P2：批量与可视化

批量已实现，可视化仍为可选后续项：

```text
run_all_bpmn_cases.py
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
5. 检查 BPMN start sequence、choreography message order、message endpoint、exclusive/event branch、parallel join、business rule/oracle task 后继关系是否映射到 DSL；
6. 输出 structure_summary.md；
7. 如果需要衔接实验三，再执行 logical_path 附加可追踪性检查。
```

最小闭环完成后，1B 主体验证已经可以支撑后续 1C；附加验证通过后，可以支撑实验三路径回放。

------

## 20. 目录结构建议

```text
Experiment/
  new/
    exp1_1B/
      scripts/
        run_supplychainpaper_demo.py
        run_all_bpmn_cases.py
        extract_bpmn_structure.py
        extract_dsl_structure.py
        build_bpmn_dsl_trace.py
        check_structure_consistency.py
        tag_utils.py

      contracts/
        default_mapping_contract.json

      cases/
        batch_summary.json
        batch_summary.md
        <CaseName>/
          input_index.json
          bpmn/
          dsl/
          trace/
          reports/

      Addition/
        scripts/
          check_exp3_path_traceability.py
          run_all_addition_cases.py
        cases/
          <CaseName>/
            path_traceability_report.json
            path_traceability_summary.md
```

------

## 21. 实验完成标准

一个 case 的 1B 实验完成标准：

```text
1. bpmn_tag.json 已生成；
2. dsl_tag.json 已生成；
3. default_mapping_contract.json 已存在并被 trace 构建脚本引用；
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
  path_traceability_summary.md

批量结果：
  cases/batch_summary.json
  cases/batch_summary.md
  Addition/cases/addition_batch_summary.json
  Addition/cases/addition_batch_summary.md
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
