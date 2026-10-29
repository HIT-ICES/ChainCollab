# 决策结果如何影响后续流程路径

## 1. 核心机制

在 `newTranslator` 中，决策结果影响后续流程路径的基本模式是：

1. `BusinessRuleTask` 执行
2. 决策输出写回 DSL 全局变量
3. 后续 `exclusive gateway` 读取该全局变量
4. 不同分支条件触发不同流程路径

也就是说，**决策不会直接“跳转”流程，而是先写状态，再由网关读状态完成分支选择。**

## 2. 当前 `SupplyChain.bpmn` 中的真实例子

在 [bpmn_example.bpmn](/home/shenxz-lab/code/ChainCollab/docs/04_modeling/bpmn_example.bpmn) 中：

- `BusinessRuleTask`：`Activity_0fbi09z`
- 输出：`deliver`
- 后继网关：`Gateway_11hmo2k`

对应 BPMN 片段是：

```xml
<bpmn2:businessRuleTask id="Activity_0fbi09z" name="">
  <bpmn2:documentation>
    {"inputs":[{"name":"amount","type":"number","description":""},{"name":"Self_pickup","type":"boolean","description":""}],"outputs":[{"name":"deliver","type":"boolean","description":""}]}
  </bpmn2:documentation>
  <bpmn2:incoming>Flow_1hbgb5i</bpmn2:incoming>
  <bpmn2:outgoing>Flow_0i9c5yv</bpmn2:outgoing>
</bpmn2:businessRuleTask>

<bpmn2:exclusiveGateway id="Gateway_11hmo2k">
  <bpmn2:incoming>Flow_0i9c5yv</bpmn2:incoming>
  <bpmn2:outgoing>Flow_08e1j3x</bpmn2:outgoing>
  <bpmn2:outgoing>Flow_1m6p4a5</bpmn2:outgoing>
</bpmn2:exclusiveGateway>

<bpmn2:sequenceFlow id="Flow_08e1j3x" name="deliver==true" sourceRef="Gateway_11hmo2k" targetRef="ChoreographyTask_1q3p8t2" />
<bpmn2:sequenceFlow id="Flow_1m6p4a5" name="deliver==false" sourceRef="Gateway_11hmo2k" targetRef="Event_0eoqvir" />
```

### 2.1 业务含义

- 如果决策结果 `deliver == true`
  - 流程进入 `ChoreographyTask_1q3p8t2`，继续执行 `Deliver goods`
- 如果决策结果 `deliver == false`
  - 流程进入 `Event_0eoqvir`，提前结束

### 2.2 在 DSL 中对应的形态

大致会表现为：

```text
businessrule Activity_0fbi09z {
    ...
    output mapping {
        deliver -> Deliver
    }
}

when businessrule Activity_0fbi09z done
then enable Gateway_11hmo2k;

when gateway Gateway_11hmo2k completed
choose {
    if Deliver == true
    then enable ChoreographyTask_1q3p8t2;
    if Deliver == false
    then enable Event_0eoqvir;
}
```

意思是：

- 规则节点完成后先启用网关
- 网关再读取决策结果对应的全局变量
- 不同结果驱动不同后续路径

## 3. 用 `supplyChainPaper.dmn` 解释同样机制

在 [dmn_example.dmn](/home/shenxz-lab/code/ChainCollab/docs/04_modeling/dmn_example.dmn) 中，主决策是：

- `Decision_0zwjfyy`
- 输出：`finalPriority`

这个输出不是布尔值，而是：

- `"VeryLow"`
- `"Low"`
- `"Medium"`
- `"High"`

如果把它接到 BPMN 的后续路径选择中，典型写法会是：

```text
output mapping {
    finalPriority -> FinalPriority
}

when businessrule PriorityRule done
then enable PriorityGateway;

when gateway PriorityGateway completed
choose {
    if FinalPriority == "VeryLow" then enable SlowDelivery;
    if FinalPriority == "Low" then enable StandardDelivery;
    if FinalPriority == "Medium" then enable ExpeditedDelivery;
    if FinalPriority == "High" then enable AirliftDelivery;
}
```

这就是“DMN 决策结果影响后续路径”的更典型形态：

- 决策输出不是简单 `true/false`
- 而是一个业务分类值
- 网关根据该分类值路由到不同任务

## 4. 当前例子里的一个实现现状

需要注意：

- `SupplyChain.bpmn` 当前规则输出是 `deliver`
- `supplyChainPaper.dmn` 当前主决策输出是 `finalPriority`

它们不是同一个变量，因此这两份示例文件不是严格同版模型。

所以从文档角度应区分：

- `SupplyChain.bpmn`：展示“布尔型决策结果如何决定是否继续流程”
- `supplyChainPaper.dmn`：展示“枚举/分类型决策结果如何驱动多分支路由”

## 5. 一句话总结

在 `newTranslator` 中，决策结果影响流程路径的方式不是“规则节点直接跳转”，而是：

**规则节点输出全局变量，后续独占网关读取该变量，再把流程导向不同分支。**

