# 4.2 Core Syntax and State Model

本节说明 `B2CDSL` 的核心语法块，以及这些语法块在 `newTranslator` 中承担的建模职责。完整示例见 [b2cdsl_full_example.dsl](/home/shenxz-lab/code/ChainCollab/docs/05_b2cdsl/b2cdsl_full_example.dsl)。

## 1. 语言整体结构

`B2CDSL` 以 `contract` 为顶层单元，内部由多个 section 组成：

- `participants`：链上参与方定义。
- `globals`：跨步骤共享的业务状态变量。
- `messages`：企业间消息交互。
- `gateways`：控制流分支或并行同步点。
- `events`：开始/结束事件。
- `businessrules`：与 DMN 决策关联的规则任务。
- `oracletasks`：外部数据或外部计算任务。
- `flows`：行为语义与状态推进规则。

## 2. `contract`

语法骨架：

```dsl
contract SupplyChain {
    participants { ... }
    globals { ... }
    messages { ... }
    gateways { ... }
    events { ... }
    businessrules { ... }
    oracletasks { ... }
    flows { ... }
}
```

含义：

- 一个 `contract` 对应一个可生成的协同流程合约单元。
- 在当前实现中，通常一个 BPMN Choreography 文件转换为一个 `contract`。
- `contract name` 会继续传递到 Go/Solidity 生成阶段，成为合约或链码命名的重要输入。

## 3. `participants`

语法骨架：

```dsl
participants {
    participant Participant_0w6qkdf {
        msp "Bulk_buyerMSP"
        x509 ""
        isMulti false
        multiMin 0
        multiMax 0
        attributes {
            role = "Bulk buyer"
        }
    }
}
```

含义：

- `participant` 表示一个链上协作主体。
- `msp` 主要服务于 Fabric 身份校验生成。
- `x509` 预留给证书级身份信息。
- `isMulti`、`multiMin`、`multiMax` 表示是否为多实例参与方及其数量约束。
- `attributes` 存放角色名等扩展属性。

系统位置：

- 在 BPMN 到 DSL 转换阶段，由 `ParticipantMetadataResolver` 补充身份元数据。
- 在代码生成阶段，参与方会映射为 Fabric MSP 校验逻辑或 Solidity 地址/角色槽位。

## 4. `globals`

语法骨架：

```dsl
globals {
    Amount: int
    Deliver: bool
    Order: string
}
```

含义：

- `globals` 是流程实例级共享状态。
- 消息输入、DMN 输入输出、网关条件判断，都通过这些全局变量关联起来。
- 它们是 BPMN 消息载荷和 DMN 参数之间的中间统一表示。

当前实现来源：

- BPMN 消息 `documentation` 中的 `properties`。
- BusinessRuleTask `documentation` 中声明的 `inputs` / `outputs`。
- 顺序流条件表达式里推断出的变量。
- Oracle task 输出映射。

## 5. `messages`

语法骨架：

```dsl
messages {
    message Message_1wswgqu from Participant_0w6qkdf to Participant_19mgbdn {
        initial state INACTIVE
        schema "{\"properties\":{\"order\":{\"type\":\"string\"},\"amount\":{\"type\":\"number\"}}}"
    }
}
```

含义：

- 一个 `message` 表示一条企业间消息交互。
- `from` / `to` 映射消息发送方与接收方。
- `schema` 保留原始消息结构，供后续代码生成器抽取入参字段。
- `initial state` 定义该消息在实例初始化时是否可执行。

## 6. `events`

语法骨架：

```dsl
events {
    event Event_06sexe6 {
        initial state READY
    }
    event Event_13pbqdz {
        initial state INACTIVE
    }
}
```

含义：

- `READY` 的事件通常表示流程开始事件。
- `INACTIVE` 的事件通常表示结束事件，需在流程推进后被启用并完成。
- 在当前 DSL 中，事件不携带业务载荷，主要承担流程边界标记和触发作用。

## 7. `gateways`

语法骨架：

```dsl
gateways {
    gateway Gateway_11hmo2k {
        type exclusive
        initial state INACTIVE
    }
    gateway Gateway_0onpe6x {
        type parallel
        initial state INACTIVE
    }
}
```

含义：

- `exclusive`：互斥分支，根据条件选择后继。
- `parallel`：并行展开或并行汇聚。
- `event`：语法上支持，对应 BPMN Event-based Gateway；是否能完整生成取决于后续生成器能力。

## 8. `businessrules`

语法骨架：

```dsl
businessrules {
    businessrule Activity_0fbi09z {
        dmn "Activity_0fbi09z.dmn"
        decision "Activity_0fbi09z_DecisionID"
        input mapping {
            amount -> Amount
            Self_pickup -> Self_pickup
        }
        output mapping {
            deliver -> Deliver
        }
        initial state INACTIVE
    }
}
```

含义：

- `businessrule` 表示一个由 DMN 支撑的决策节点。
- `dmn` 是 DMN 资源标识。
- `decision` 是待调用的决策 ID。
- `input mapping` 表示 “DMN 输入参数 -> DSL 全局变量”。
- `output mapping` 表示 “DMN 输出参数 -> DSL 全局变量”。

实现说明：

- 当前 `newTranslator` 不是从 BPMN XML 的标准字段里解析出 `dmn` 路径和 `decision id`。
- 当前生成逻辑是约定式生成：
  - `dmn = "{BusinessRuleTask.id}.dmn"`
  - `decision = "{BusinessRuleTask.id}_DecisionID"`
- 输入输出映射主要来自 `BusinessRuleTask.documentation` 的 JSON 内容。

## 9. `flows`

语法骨架：

```dsl
flows {
    start event Event_06sexe6 enables Message_1wswgqu;

    when message Message_1wswgqu completed
    then enable Message_1ajdm9l;

    when gateway Gateway_11hmo2k completed
    choose {
        if Deliver == true
        then enable Message_196q1fj;
        if Deliver == false
        then enable Event_0eoqvir;
    }

    parallel gateway Gateway_1fbifca await Message_0cba4t6, Message_0pm90nx
    then enable Message_0rwz1km;
}
```

含义：

- `start event ... enables ...`：定义起始触发关系。
- `when message ... completed then ...`：消息完成后推进后继状态。
- `when gateway ... completed choose { ... }`：互斥网关分支。
- `parallel gateway ... await ... then ...`：并行汇聚语义。
- `when businessrule ... done then ...`：DMN 决策完成后推进流程。

`flows` 是 B2CDSL 行为语义的核心，也是后续 Go/Solidity 代码生成的主要依据。

## 10. 设计这些语法块的原因

- `participants`：必须显式表达多企业身份，否则无法生成链上权限控制。
- `globals`：把 BPMN 消息字段、DMN 参数和状态条件统一到一个可持久化状态空间。
- `messages`：把 choreography task 显式化，便于生成交易接口。
- `gateways`：把控制流中的选择与同步语义显式化，便于生成状态更新逻辑。
- `events`：定义流程边界和启动点。
- `businessrules`：把决策调用从流程控制中单独抽出，便于双平台生成。
- `flows`：把 “结构元素” 提升为 “可执行语义规则”，服务代码生成和轨迹验证。
