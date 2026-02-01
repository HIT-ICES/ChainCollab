# B2CDSL（DSL）详细描述

## 0. 依据与定位

- 论文第 18–25 页指出：智能合约自动生成正在从“单合约模板化”走向多源输入协同驱动，并强调通过**DSL/元模型形成稳定中间表示**以解耦目标链平台、支撑验证/审计/跨平台部署。
- 在 newTranslator 中，这个稳定的中间表示即 **B2CDSL**（Business‑to‑Chain DSL），用于把 BPMN/DMN 的业务语义落到可生成链码/合约的统一结构。
- **元模型与示例位置**：\n+  - 元模型（语法定义）：`code/ChainCollab/src/newTranslator/DSL/B2CDSL/b2cdsl/b2c.tx`\n+  - 示例 DSL 文件（手工/生成样例）：\n+    - `code/ChainCollab/src/newTranslator/example/chaincode.b2c`\n+    - `code/ChainCollab/src/newTranslator/example/chaincode copy.b2c`\n+  - 生成物示例（构建产物，非手写）：`code/ChainCollab/src/newTranslator/build/b2c/chaincode.b2c`

> 下面的语法与元素语义以 `code/ChainCollab/src/newTranslator/DSL/B2CDSL/b2cdsl/b2c.tx` 为准，并结合 `code/ChainCollab/src/newTranslator/模型驱动原理文档.md` 中的流程与示例说明。

---

## 1. DSL 的总体结构

B2CDSL 的最外层是 **Model**，包含一个或多个 **Contract**：

```text
Model:
    contracts+=Contract
;

Contract:
    'contract' name=ID '{'
        sections+=ContractSection*
    '}'
;
```

**ContractSection** 由多个可选区块组成（顺序可变、可省略）：

- participants：参与者定义
- globals：全局变量
- messages：消息定义
- gateways：网关定义
- events：事件定义
- businessrules：DMN 业务规则定义
- flows：流程控制语义

---

## 2. 核心元素与语义

### 2.1 participants（参与者）

```text
participant Name {
    msp "MSP_ID"
    x509 "CERT"
    isMulti true|false
    multiMin 1
    multiMax 3
    attributes { key = "value" }
}
```

- `msp` / `x509`：Fabric 场景的身份绑定信息。
- `isMulti`/`multiMin`/`multiMax`：多实例参与者配置。
- `attributes`：扩展属性，供业务校验或权限控制使用。

### 2.2 globals（全局变量）

```text
globals {
    VarName: string|int|bool|float
}
```

- 支持的标量类型：`string`、`int`、`bool`、`float`。
- 在流程中通过 `set` 动作赋值（当前语法仅支持字面量赋值）。

### 2.3 messages（消息）

```text
message MsgName from Sender to Receiver {
    initial state INACTIVE
    schema "field1 + field2"
}
```

- `from/to` 明确消息发送者和接收者。
- `schema` 用于描述消息载荷结构。
- `initial state` 定义初始状态。

### 2.4 gateways（网关）

```text
gateway GName {
    type exclusive|event|parallel
    initial state INACTIVE
}
```

- `exclusive`：条件分支。
- `event`：事件驱动分支。
- `parallel`：并行分支/同步。

### 2.5 events（事件）

```text
event EName {
    initial state READY
}
```

- 用于流程起点或中间/结束事件的语义承载。

### 2.6 businessrules（业务规则 / DMN）

```text
businessrule RuleName {
    dmn "rule.dmn"
    decision "DecisionID"
    input mapping { dmnParam -> globalVar }
    output mapping { dmnResult -> globalVar }
    initial state READY
}
```

- `dmn`：DMN 文件路径。
- `decision`：DMN 决策 ID。
- `input/output mapping`：DMN 变量与 DSL 全局变量的映射。

---

## 3. 状态模型

DSL 统一定义了元素状态：

```text
INACTIVE | READY | PENDING_CONFIRMATION | DONE
```

- **INACTIVE**：未激活、不可触发。
- **READY**：可触发/可执行。
- **PENDING_CONFIRMATION**：待确认（例如多方确认、外部回执）。
- **DONE**：已完成。

状态通过 **flows** 中的动作驱动转换。

---

## 4. flows（流程控制语义）

### 4.1 起始驱动

```text
start event StartEvent enables Target;
```

- 以事件为入口，启用后续目标元素。

### 4.2 消息驱动

```text
when message M sent then enable X, disable Y, set Var = "v";
when message M completed then ...;
```

- 条件：`sent` 或 `completed`。

### 4.3 网关驱动

```text
when gateway G completed then enable X, disable Y;

when gateway G completed choose {
    if var == 1 then enable A;
    if expr "x > 10" then enable B;
    else then enable C;
}
```

- 支持 **比较分支**（`var op literal`）与 **表达式分支**（`expr "..."`）。
- `else` 分支作为兜底。

### 4.4 业务规则驱动

```text
when businessrule R ready then enable X;
when businessrule R waiting then ...;
when businessrule R done then ...;
```

### 4.5 事件驱动

```text
when event E completed then enable X;
```

### 4.6 并行汇聚

```text
parallel gateway G await A, B, C then enable X;
```

- 表示并行网关等待多个来源元素完成后再推进。

### 4.7 动作集合

```text
enable Target
disable Target
set GlobalVar = Literal
```

- `set` 当前仅支持字面量表达式：`STRING | INT | BOOL`。

---

## 5. 语法摘要（精简版）

```text
contract Name {
  participants { participant ... }
  globals { Var: Type }
  messages { message ... }
  gateways { gateway ... }
  events { event ... }
  businessrules { businessrule ... }
  flows {
    start event E enables X;
    when message M sent then enable/disable/set ...;
    when gateway G completed then ... | choose {...};
    when businessrule R ready|waiting|done then ...;
    when event E completed then ...;
    parallel gateway G await A, B then ...;
  }
}
```

完整语法以 `code/ChainCollab/src/newTranslator/DSL/B2CDSL/b2cdsl/b2c.tx` 为准。

---

## 6. 与 BPMN/DMN 的映射关系（要点）

- **BPMN 协作流程** → 解析为 Choreography 图（参与者/消息/网关/事件/连线）。
- **Choreography 元素** → 映射为 B2CDSL 的 participants/messages/gateways/events 等。
- **BPMN BusinessRuleTask** → 映射为 `businessrule`，并携带 DMN 决策信息。
- **流程控制语义** → 以 `flows` 中的规则表达启用/禁用与状态迁移。

---

## 7. 生成链路中的角色

1. **BPMN/DMN 解析**：提取流程元素与决策信息。
2. **B2CDSL 生成**：作为稳定中间表示，承载流程语义与执行约束。
3. **代码生成**：通过模板引擎将 DSL 变为 Go 链码或 Solidity 合约。

对应实现位置：
- 解析器：`code/ChainCollab/src/newTranslator/generator/parser/`
- DSL 元模型：`code/ChainCollab/src/newTranslator/DSL/B2CDSL/b2cdsl/b2c.tx`
- 代码生成：`code/ChainCollab/src/newTranslator/CodeGenerator/`

---

## 8. 最小示例（可读性示例）

```text
contract Demo {
  participants {
    participant Buyer { msp "Org1MSP" }
    participant Seller { msp "Org2MSP" }
  }

  globals {
    Approved: bool
  }

  messages {
    message Order from Buyer to Seller {
      initial state INACTIVE
      schema "item + qty"
    }
  }

  events {
    event Start { initial state READY }
  }

  flows {
    start event Start enables Order;
    when message Order sent then set Approved = true;
  }
}
```

---

## 9. 可扩展性建议（基于当前语法）

- 若需支持复杂计算表达式，可扩展 `SetGlobalAction` 的表达式类型。
- 若需更复杂的条件语义，可扩展 `GatewayExpressionBranch` 的表达式解析器。
- 若需更多状态类型，可在 `ElementState` 增补并同步模板逻辑。

---

## 10. 总结

B2CDSL 作为 DSL/元模型的稳定中间层，将 BPMN/DMN 的协作流程语义抽象为统一的结构与流程控制语言，使模型驱动的多方协作流程能够在不同区块链平台间解耦、复用与验证。这与论文第 18–25 页提出的“通过 DSL/元模型形成稳定中间表示”的技术演进方向一致。
