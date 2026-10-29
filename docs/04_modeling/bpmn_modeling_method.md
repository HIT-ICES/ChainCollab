# 3.2 Collaborative Process Modeling with BPMN Choreography

## 1. 建模目标

这一节要回答的问题是：**多企业协作流程在 `newTranslator` 中如何用 BPMN Choreography 建模。**

对 `newTranslator` 来说，BPMN 不是普通“流程图”，而是后续生成 DSL、Fabric 链码和 Solidity 合约的业务语义输入。因此建模时必须把：

- 参与企业
- 消息交互
- 开始 / 结束
- 控制分支
- 业务规则节点

表达成可解析、可翻译的协作结构。

## 2. 示例文件

- BPMN XML： [bpmn_example.bpmn](/home/shenxz-lab/code/ChainCollab/docs/04_modeling/bpmn_example.bpmn)
- BPMN 图： [bpmn_diagram.png](/home/shenxz-lab/code/ChainCollab/docs/04_modeling/bpmn_diagram.png)
- 元素语义对照表： [bpmn_element_to_collaboration_semantics.xlsx](/home/shenxz-lab/code/ChainCollab/docs/04_modeling/bpmn_element_to_collaboration_semantics.xlsx)

本节使用的示例来自：

- `Experiment/BPMNwithDMNcase/SupplyChain.bpmn`

## 3. 参与方如何建模

在 BPMN Choreography 中，多企业参与方使用 `participant` 表达。

本示例中的参与方有：

| 企业/角色语义 | BPMN participant id | BPMN participant name |
|---|---|---|
| 大宗买家 | `Participant_0w6qkdf` | `Bulk buyer` |
| 制造商 | `Participant_19mgbdn` | `Manufacturer` |
| 中间商 | `Participant_09cjol2` | `Middleman` |
| 供应商 | `Participant_0sa2v7d` | `Supplier` |
| 特殊承运方 | `Participant_19j1e3o` | `Special carrier` |

这说明：

- 一个企业参与方对应一个 BPMN `participant`
- 后续消息发送方/接收方都通过这些 `participant` 进行引用
- 解析器会把它们转成系统内部的 `Participant` 对象，再进入 DSL `participants`

## 4. 消息交互如何建模

在 BPMN Choreography 中，消息交互不是单靠 `message` 表达，而是由三部分共同完成：

- `message`
- `messageFlow`
- `choreographyTask`

### 4.1 `message`

`message` 定义“交换什么”。

例如：

- `Message_1wswgqu`：`order`
- `Message_1ajdm9l`：`placed_order`
- `Message_0cba4t6`：`fwd_order`
- `Message_0pm90nx`：`transport_order`

并且消息的 `documentation` 中还承载 payload/schema。

### 4.2 `messageFlow`

`messageFlow` 定义“谁发给谁”。

例如：

```xml
<bpmn2:messageFlow id="MessageFlow_06374xt"
                   sourceRef="Participant_0w6qkdf"
                   targetRef="Participant_19mgbdn"
                   messageRef="Message_1wswgqu" />
```

它表示：

- `Bulk buyer` 向 `Manufacturer` 发送 `order`

### 4.3 `choreographyTask`

`choreographyTask` 定义“这次交互在流程中的业务位置”。

例如：

```xml
<bpmn2:choreographyTask id="ChoreographyTask_0tyax7p"
                        name="Order goods"
                        initiatingParticipantRef="Participant_0w6qkdf">
  ...
  <bpmn2:participantRef>Participant_0w6qkdf</bpmn2:participantRef>
  <bpmn2:participantRef>Participant_19mgbdn</bpmn2:participantRef>
  <bpmn2:messageFlowRef>MessageFlow_06374xt</bpmn2:messageFlowRef>
</bpmn2:choreographyTask>
```

这意味着：

- 业务动作名：`Order goods`
- 发起方：`Bulk buyer`
- 对端：`Manufacturer`
- 业务消息：`order`

因此，一个完整协作交互的建模语义是：

**参与方 + choreographyTask + messageFlow + message**

## 5. gateway 如何使用

本示例同时使用了：

- `parallelGateway`
- `exclusiveGateway`

### 5.1 并行网关示例

示例中：

- `Gateway_0onpe6x`：把流程分成两条并行路径
  - `Forward order for supplies`
  - `Forward order for transport`
- `Gateway_1fbifca`：把两条并行路径重新汇聚

建模语义是：

- 一个企业动作完成后，可以并行触发多个后续协作任务
- 后续某一步只有在多个并行前驱都到齐后才能继续

### 5.2 条件网关示例

示例中：

- `Gateway_11hmo2k` 是独占网关
- 后续两条边分别带条件：
  - `deliver==true`
  - `deliver==false`

对应片段：

```xml
<bpmn2:sequenceFlow id="Flow_08e1j3x"
                    name="deliver==true"
                    sourceRef="Gateway_11hmo2k"
                    targetRef="ChoreographyTask_1q3p8t2" />
<bpmn2:sequenceFlow id="Flow_1m6p4a5"
                    name="deliver==false"
                    sourceRef="Gateway_11hmo2k"
                    targetRef="Event_0eoqvir" />
```

建模语义是：

- 网关读取某个已生成的业务判断结果
- 根据条件选择继续交付，还是提前结束

## 6. start / end event 如何使用

### 6.1 开始事件

示例入口是：

- `Event_06sexe6`

它的作用是：

- 作为流程实例唯一启动点
- 启用第一条协作任务 `Order goods`

### 6.2 结束事件

示例里有两个结束事件：

- `Event_13pbqdz`：正常完成后结束
- `Event_0eoqvir`：条件分支否定后结束

这说明：

- 一个协作流程可以有多个终止路径
- 但每条路径都必须通过明确的 `endEvent` 建模

## 7. BusinessRuleTask 在 BPMN 中的位置

示例中的业务规则节点是：

- `Activity_0fbi09z`

它位于：

1. `Report start of production` 之后
2. `Gateway_11hmo2k` 之前

也就是：

**先收集业务上下文 -> 执行业务规则 -> 再根据规则结果做分支**

在 BPMN 上，它处于“流程控制”和“决策控制”的交界位置。

## 8. 这种建模方法的本质

对于 `newTranslator` 而言，BPMN Choreography 建模方法可以概括为：

1. 用 `participant` 表示企业主体
2. 用 `message` + `messageFlow` 表示消息交换
3. 用 `choreographyTask` 把消息交换放到流程上下文里
4. 用 `startEvent` / `endEvent` 定义生命周期
5. 用 `parallelGateway` / `exclusiveGateway` 表示控制结构
6. 用 `businessRuleTask` 把业务规则嵌入流程

这样建出来的 BPMN，才足以被后续解析器翻译成 B2CDSL，再进一步生成区块链执行代码。

