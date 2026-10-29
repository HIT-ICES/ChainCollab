# BusinessRule 生成完整示例

## 1. 示例目标

这一节展示从：

- BPMN `BusinessRuleTask`
- DMN decision
- input/output mapping

到：

- 生成的 B2CDSL `businessrule`

的完整链条。

## 2. BPMN BusinessRuleTask

来自 [businessruletask_xml_snippet.xml](/home/shenxz-lab/code/ChainCollab/docs/04_modeling/businessruletask_xml_snippet.xml)：

```xml
<bpmn2:businessRuleTask id="Activity_0fbi09z" name="">
  <bpmn2:documentation>
    {"inputs":[{"name":"amount","type":"number","description":""},{"name":"Self_pickup","type":"boolean","description":""}],"outputs":[{"name":"deliver","type":"boolean","description":""}]}
  </bpmn2:documentation>
  <bpmn2:incoming>Flow_1hbgb5i</bpmn2:incoming>
  <bpmn2:outgoing>Flow_0i9c5yv</bpmn2:outgoing>
</bpmn2:businessRuleTask>
```

## 3. DMN decision

当前指定的 DMN 文件是 [dmn_example.dmn](/home/shenxz-lab/code/ChainCollab/docs/04_modeling/dmn_example.dmn)。

其中主决策是：

- decision id：`Decision_0zwjfyy`
- decision name：`Final Priority Adjustment Decision`

输入：

- `initialPriority`
- `supplierReputation`

输出：

- `finalPriority`

## 4. input / output mapping

### 4.1 当前 BPMN 示例真实会生成的映射

来自 `BusinessRuleTask.documentation`：

```text
input mapping {
    amount -> Amount
    Self_pickup -> Self_pickup
}

output mapping {
    deliver -> Deliver
}
```

### 4.2 如果显式绑定到 `supplyChainPaper.dmn` 主决策

则更理想的映射会是：

```text
input mapping {
    initialPriority -> InitialPriority
    supplierReputation -> SupplierReputation
}

output mapping {
    finalPriority -> FinalPriority
}
```

## 5. 生成的 B2CDSL businessrule

对当前 `SupplyChain.bpmn`，`newTranslator` 实际生成的是：

```text
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
```

## 6. 这个例子说明了什么

它同时说明了两件事：

### 6.1 已经实现的部分

- BPMN 规则节点可以被识别
- 输入输出列表可以被抽取
- 可以生成 DSL `businessrule`
- 可以继续驱动后续网关分支

### 6.2 还未完全显式化的部分

- `dmn` 文件路径当前靠 `rule.id` 约定生成
- `decision id` 当前也靠 `rule.id` 约定生成
- 这与 `supplyChainPaper.dmn` 中的真实主决策 `Decision_0zwjfyy` 不直接一致

## 7. 一个更理想的最终形态

如果把 BPMN 与 DMN 的绑定做成显式字段，那么最终应更接近：

```text
businessrule Activity_0fbi09z {
    dmn "supplyChainPaper.dmn"
    decision "Decision_0zwjfyy"
    input mapping {
        initialPriority -> InitialPriority
        supplierReputation -> SupplierReputation
    }
    output mapping {
        finalPriority -> FinalPriority
    }
    initial state INACTIVE
}
```

## 8. 一句话总结

这个例子表明，`newTranslator` 已经具备：

- 从 BPMN 规则节点生成 DSL `businessrule`

的核心链路；当前最需要继续增强的是：

- 把 DMN 文件路径和 decision id 的绑定从“命名约定”升级成“显式建模”

