# 1B Mapping Contract And TAG Format Draft

本文档说明 `contracts/default_mapping_contract.json` 和 `schemas/tag_format.schema.json` 的设计依据。

## 1. 总体原则

1B 使用同一种 TAG 容器格式表示 BPMN 和 DSL：

```text
{
  tag_version,
  case_name,
  model_type,
  source_file,
  extractor,
  nodes,
  edges,
  derived?,
  warnings?
}
```

BPMN-TAG 和 DSL-TAG 的外层格式相同，但节点类型、边类型和 `attrs` 字段不同。差异由 `default_mapping_contract.json` 解释。

## 2. newTranslator 中需要特别处理的映射

### 2.1 messageFlow 不是 DSL 节点

在 `newTranslator` 中，BPMN `messageFlow` 用于提供：

```text
messageRef -> DSL message id
sourceRef  -> DSL message sender
targetRef  -> DSL message receiver
```

因此 1B 不能要求存在 `dsl:messageFlow` 节点，而应检查：

```text
bpmn:messageFlow.message == dsl:message.id
bpmn:messageFlow.source == dsl:message.sender
bpmn:messageFlow.target == dsl:message.receiver
```

### 2.2 choreographyTask 不是 DSL 节点

`choreographyTask` 在 translator 中通过 `_activation_target` 展开：

```text
如果有 init message flow，激活目标是 init message id；
否则如果有 return message flow，激活目标是 return message id；
否则不生成直接 DSL 目标。
```

因此 1B 不要求 `choreographyTask.id` 出现在 DSL 节点中，而应检查：

```text
choreographyTask.messageFlowRef 对应的 message 是否存在于 DSL；
choreographyTask 的后继 sequenceFlow 是否被转成 message/gateway/event/businessrule/oracletask 的 enable 关系。
```

### 2.3 globals 是派生结构

DSL `globals` 不是 BPMN 原生节点，而是由以下来源推导：

```text
message.documentation.properties
businessRuleTask.documentation.inputs
businessRuleTask.documentation.outputs
receiveTask/scriptTask.documentation.outputMappings
sequenceFlow.conditionExpression 或 sequenceFlow.name 中的条件变量
```

所以 `dsl:global` 不应被 C5 误判为无来源伪目标，只要它能追溯到上述来源即可。

## 3. 推荐 BPMN-TAG 示例

```json
{
  "tag_version": "0.1.0",
  "case_name": "SupplyChainPaper",
  "model_type": "bpmn",
  "source_file": "build/bpmn/SupplyChainPaper7777_zh_name.bpmn",
  "extractor": {
    "name": "extract_bpmn_structure",
    "version": "0.1.0",
    "implementation_basis": [
      "src/newTranslator/generator/parser/choreography_parser/parser.py",
      "src/newTranslator/generator/parser/choreography_parser/elements.py"
    ]
  },
  "nodes": [
    {
      "id": "Participant_Buyer",
      "type": "bpmn:participant",
      "name": "Buyer",
      "attrs": {
        "is_multi": false,
        "multi_minimum": 0,
        "multi_maximum": 0
      }
    },
    {
      "id": "Message_Order",
      "type": "bpmn:message",
      "name": "Order",
      "attrs": {
        "documentation": "{\"properties\":{\"amount\":{\"type\":\"number\"}}}"
      }
    },
    {
      "id": "Task_SubmitOrder",
      "type": "bpmn:choreographyTask",
      "name": "Submit order",
      "attrs": {
        "incoming": "Flow_1",
        "outgoing": "Flow_2",
        "participants": ["Participant_Buyer", "Participant_Seller"],
        "initiatingParticipantRef": "Participant_Buyer",
        "messageFlowRefs": ["MessageFlow_Order"]
      }
    }
  ],
  "edges": [
    {
      "id": "MessageFlow_Order",
      "type": "bpmn:messageFlow",
      "source": "Participant_Buyer",
      "target": "Participant_Seller",
      "attrs": {
        "message": "Message_Order",
        "name": ""
      }
    },
    {
      "id": "Flow_2",
      "type": "bpmn:sequenceFlow",
      "source": "Task_SubmitOrder",
      "target": "Gateway_Check",
      "attrs": {
        "condition_expression": ""
      }
    }
  ],
  "derived": [
    {
      "id": "Derive_Amount",
      "type": "bpmn:condition_variable",
      "target": "Amount",
      "sources": ["Message_Order"],
      "rule": "MessageProperty2GlobalVar",
      "attrs": {
        "name": "amount",
        "type": "number"
      }
    }
  ]
}
```

## 4. 推荐 DSL-TAG 示例

```json
{
  "tag_version": "0.1.0",
  "case_name": "SupplyChainPaper",
  "model_type": "dsl",
  "source_file": "build/b2c/SupplyChainPaper7777.b2c",
  "extractor": {
    "name": "extract_dsl_structure",
    "version": "0.1.0",
    "implementation_basis": [
      "src/newTranslator/DSL/B2CDSL/b2cdsl/b2c.tx",
      "src/newTranslator/MDAcheck/b2c.ecore"
    ]
  },
  "nodes": [
    {
      "id": "Participant_Buyer",
      "type": "dsl:participant",
      "name": "Participant_Buyer",
      "attrs": {
        "msp": "BuyerMSP",
        "x509": "",
        "isMulti": false,
        "multiMin": 0,
        "multiMax": 0,
        "attributes": {
          "role": "Buyer"
        }
      }
    },
    {
      "id": "Amount",
      "type": "dsl:global",
      "name": "Amount",
      "attrs": {
        "type": "int"
      }
    },
    {
      "id": "Message_Order",
      "type": "dsl:message",
      "name": "Message_Order",
      "attrs": {
        "sender": "Participant_Buyer",
        "receiver": "Participant_Seller",
        "schema": "{\"properties\":{\"amount\":{\"type\":\"number\"}}}",
        "initialState": "INACTIVE"
      }
    }
  ],
  "edges": [
    {
      "id": "Message_Order__sender",
      "type": "dsl:message_sender",
      "source": "Message_Order",
      "target": "Participant_Buyer",
      "attrs": {}
    },
    {
      "id": "Message_Order__receiver",
      "type": "dsl:message_receiver",
      "source": "Message_Order",
      "target": "Participant_Seller",
      "attrs": {}
    },
    {
      "id": "Flow_Message_Order__Gateway_Check",
      "type": "dsl:enable",
      "source": "Message_Order",
      "target": "Gateway_Check",
      "attrs": {
        "trigger_type": "message",
        "trigger_condition": "completed",
        "flow_item": "MessageFlow"
      }
    }
  ],
  "derived": [
    {
      "id": "Derive_Amount",
      "type": "dsl:global_derivation",
      "target": "Amount",
      "sources": ["Message_Order"],
      "rule": "MessageProperty2GlobalVar",
      "attrs": {
        "source_field": "amount"
      }
    }
  ]
}
```

## 5. 初版检查器应优先支持的字段

P0 阶段建议优先支持：

```text
nodes[].id
nodes[].type
nodes[].name
nodes[].attrs
edges[].id
edges[].type
edges[].source
edges[].target
edges[].attrs
derived[].target
derived[].sources
derived[].rule
```

后续如果需要定位 XML 行号或 DSL 行号，再补 `source_location`。

## 6. TAG 类型覆盖说明

`schemas/tag_format.schema.json` 中的类型词表分为两层：

### 6.1 P0 必须抽取的直接业务节点

BPMN 侧：

```text
bpmn:participant
bpmn:message
bpmn:startEvent
bpmn:endEvent
bpmn:choreographyTask
bpmn:exclusiveGateway
bpmn:parallelGateway
bpmn:eventBasedGateway
bpmn:businessRuleTask
bpmn:receiveTask
bpmn:scriptTask
```

DSL 侧：

```text
dsl:participant
dsl:global
dsl:message
dsl:gateway
dsl:event
dsl:businessrule
dsl:oracletask
```

### 6.2 P0 必须抽取的结构边

```text
bpmn:messageFlow
bpmn:sequenceFlow
bpmn:participantRef
bpmn:initiatingParticipant
bpmn:messageFlowRef
bpmn:messageRef

dsl:message_sender
dsl:message_receiver
dsl:start_enables
dsl:enable
dsl:disable
dsl:gateway_branch
dsl:parallel_join_source
dsl:businessrule_input
dsl:businessrule_output
dsl:oracletask_output
```

### 6.3 P1 可选细粒度节点

以下 DSL 语法对象参与结构一致性，但不一定要在 P0 中作为独立节点抽取；可以先作为 `edges[].attrs` 表示：

```text
dsl:flowItem
dsl:startFlow
dsl:messageFlow
dsl:gatewayFlow
dsl:ruleFlow
dsl:oracleTaskFlow
dsl:eventFlow
dsl:parallelJoin
dsl:gatewayCompareBranch
dsl:gatewayExpressionBranch
dsl:gatewayElseBranch
dsl:paramMapping
dsl:literal
```

如果后续检查需要定位到具体 flow item 或 branch，再把这些类型提升为独立 TAG 节点。
