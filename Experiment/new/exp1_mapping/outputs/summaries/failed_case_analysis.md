# 失败案例解析

本文档基于当前实验一最新结果生成。当前验证逻辑已经改为：

- 不再使用 case 中预置的历史 `.b2c`
- 每次实验先调用当前 `newTranslator` 重新生成 `.b2c`
- 再执行 BPMN -> B2CDSL 映射契约验证

因此，本文档中的失败项可视为“在当前生成链路下仍存在的真实缺陷”，而不是旧产物或验证器误报。

## 当前失败案例总览

| Case | Contract Satisfaction | Element Preservation | Mapping Accuracy | 结论 |
|---|---:|---:|---:|---|
| Coffee_machine | 92.31% | 100.00% | 91.67% | BusinessRule 语义不完整 |
| Purchase | 94.74% | 100.00% | 94.44% | Message Flow 推进规则不完整 |

## 1. Coffee_machine

### 基本结论

`Coffee_machine` 不是元素缺失型失败，而是“元素已生成，但业务规则语义不完整”。

### 验证结果

- 汇总见 [summary.csv](/root/code/ChainCollab/Experiment/new/exp1_mapping/outputs/summaries/summary.csv)
- 报告见 [Coffee_machine.mapping_report.md](/root/code/ChainCollab/Experiment/new/exp1_mapping/outputs/reports/Coffee_machine.mapping_report.md)
- 当前生成 DSL 见 [Coffee_machine.generated.b2c](/root/code/ChainCollab/Experiment/new/exp1_mapping/outputs/regenerated/Coffee_machine.generated.b2c)

### 失败项

- BPMN `businessRuleTask`
  - `Activity_0ysk2q6`
- 对应 DSL `businessrule`
  - `Activity_0ysk2q6`
- 失败原因
  - `DSL businessrule missing input mapping`
  - `DSL businessrule missing output mapping`

### 证据

在当前生成出的 DSL 中，`businessrule` 节点已经存在，但 `input mapping` 为空，且没有 `output mapping`：

```b2c
businessrule Activity_0ysk2q6 {
    dmn "Activity_0ysk2q6.dmn"
    decision "Activity_0ysk2q6_DecisionID"
    input mapping {
    }
    initial state INACTIVE
}
```

同时，流程规则已经存在：

```b2c
when gateway ExclusiveGateway_1sp1v7s completed
then enable Activity_0ysk2q6;

when businessrule Activity_0ysk2q6 done
then enable Message_1e90tfn;
```

### 分析

这说明：

- `newTranslator` 已识别该 BPMN `businessRuleTask`
- 也已将其编译为 DSL `businessrule`
- 但未把输入输出映射完整写入 DSL

因此，这不是“完全没生成出来”，而是：

**BusinessRuleTask 已被翻译，但 `input/output mapping` 缺失，导致契约不满足。**

### 根因判断

更可能的根因：

- 生成器对该 `businessRuleTask` 的 documentation / 参数抽取不完整
- 或当前 BPMN 中该任务缺少可被生成器稳定识别的输入输出映射信息

不太可能的根因：

- 验证器误报
- 旧 `.b2c` 文件污染

原因是当前报告使用的是现生成 DSL，而 DSL 中确实存在一个空映射的 `businessrule`。

## 2. Purchase

### 基本结论

`Purchase` 不是元素缺失型失败，而是“消息元素已生成，但缺少对应 flow 推进规则”。

### 验证结果

- 汇总见 [summary.csv](/root/code/ChainCollab/Experiment/new/exp1_mapping/outputs/summaries/summary.csv)
- 报告见 [Purchase.mapping_report.md](/root/code/ChainCollab/Experiment/new/exp1_mapping/outputs/reports/Purchase.mapping_report.md)
- 当前生成 DSL 见 [Purchase.generated.b2c](/root/code/ChainCollab/Experiment/new/exp1_mapping/outputs/regenerated/Purchase.generated.b2c)

### 失败项

- BPMN `messageFlow`
  - `MessageFlow_1qi88x8`
  - 名称：`sale`
- 对应 DSL `message`
  - `Message_08ms1jj`
- 失败原因
  - `DSL flows missing message sent/completed trigger`

### 证据

在当前生成出的 DSL 中，以下元素都已经存在：

- `message Message_08ms1jj`
- `gateway Gateway_13i0b7w`
- `businessrule Activity_12arovy`

DSL 片段如下：

```b2c
message Message_08ms1jj from Participant_0jwk4tk to Participant_0oa2za9 {
    initial state INACTIVE
    schema "{\"properties\":{\"sale\":{\"type\":\"string\",\"description\":\"\"}},\"required\":[\"sale\"],\"files\":{},\"file required\":[]}"
}
```

```b2c
businessrule Activity_12arovy {
    dmn "Activity_12arovy.dmn"
    decision "Activity_12arovy_DecisionID"
    input mapping {
        Price -> Price
    }
    output mapping {
        discount -> Discount
    }
    initial state INACTIVE
}
```

```b2c
when businessrule Activity_12arovy done
then enable Gateway_13i0b7w;
```

但在 `flows` 区域中，没有找到与 `Message_08ms1jj` 相关的：

- `when message Message_08ms1jj sent`
- `when message Message_08ms1jj completed`

### BPMN 侧语义依据

在 BPMN 中，`sale` 并不是孤立消息，而是位于真实的 choreography task 中：

- `Gateway_13i0b7w` 的 `discount==true` 分支进入 `ChoreographyTask_06fwl21`
- `ChoreographyTask_06fwl21` 对应消息 `MessageFlow_1qi88x8`
- 该 task 之后还有后续 sequence flow，而不是直接终止

因此，该 message 正常情况下应在 DSL 中有配套的推进规则。

### 分析

这说明：

- 当前生成器已经正确生成了该 message 定义
- 也正确生成了其前置的 gateway / businessrule
- 但没有补全该 message 在 DSL `flows` 中的状态推进关系

因此，这是：

**Message Flow 定义存在，但 flow 触发规则缺失。**

### 根因判断

更可能的根因：

- 生成器在处理该 choreography task 时，漏生成了该 message 的 `when message ...` 规则
- 或在终止/后继任务拼接时，漏掉了这一条 message completion path

不太可能的根因：

- case 配对错误
- 验证器误报

原因是当前 DSL 中已存在 message 本体，但确实没有相应 flow 规则。

## 总结

当前两个失败案例属于两类不同问题：

1. `Coffee_machine`
   - 类型：`BusinessRule 语义不完整`
   - 表现：`businessrule` 已生成，但 `input/output mapping` 缺失

2. `Purchase`
   - 类型：`Message Flow 语义不完整`
   - 表现：`message` 已生成，但缺少 `when message ... sent/completed` 推进规则

它们的共同点是：

- 元素本体已经被生成
- 失败发生在“关键语义没有完全落到 DSL 契约层”

因此，这两个失败更适合在论文或汇报中表述为：

**当前映射链路已能较完整保留结构元素，但在个别 BusinessRule 参数映射和 Message Flow 推进规则方面仍存在语义保留不足。**
