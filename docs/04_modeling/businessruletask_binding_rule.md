# 3.4 Binding DMN Decisions to BPMN BusinessRuleTask

## 1. 这一节的核心结论

`newTranslator` 的建模贡献核心，不是单独支持 BPMN 或单独支持 DMN，而是让：

- BPMN 中的 `BusinessRuleTask`

与：

- DMN 中的 decision

建立可翻译、可生成的绑定关系。

## 2. 当前绑定规则

当前实现里的绑定规则可以概括为：

1. 在 BPMN 中识别 `BusinessRuleTask`
2. 读取其 `documentation` JSON
3. 从 `documentation.inputs` 生成 `input mapping`
4. 从 `documentation.outputs` 生成 `output mapping`
5. 用 `BusinessRuleTask.id` 推导：
   - `dmnResource = "<rule.id>.dmn"`
   - `decisionID = "<rule.id>_DecisionID"`
6. 生成 B2CDSL `businessrule`

## 3. 当前绑定的显式部分与隐式部分

### 3.1 显式部分

显式来自 BPMN `documentation`：

- 输入变量列表
- 输出变量列表

### 3.2 隐式部分

隐式来自命名约定：

- DMN 文件路径
- decision id

它们当前不是从 BPMN 的标准字段中直接解析出来的。

## 4. 具体格式

### 4.1 BPMN 侧

```xml
<bpmn2:businessRuleTask id="Activity_0fbi09z" name="">
  <bpmn2:documentation>
    {"inputs":[{"name":"amount","type":"number","description":""},{"name":"Self_pickup","type":"boolean","description":""}],"outputs":[{"name":"deliver","type":"boolean","description":""}]}
  </bpmn2:documentation>
  <bpmn2:incoming>Flow_1hbgb5i</bpmn2:incoming>
  <bpmn2:outgoing>Flow_0i9c5yv</bpmn2:outgoing>
</bpmn2:businessRuleTask>
```

### 4.2 生成后的 DSL 侧

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

## 5. 绑定后的内部数据结构

当前虽然没有单独定义一个“Binding 类”，但从实现逻辑看，绑定后的内部结构可以抽象成：

- `rule_id`
- `rule_name`
- `documentation_payload`
- `inferred_dmn_resource`
- `inferred_decision_id`
- `input_mappings`
- `output_mappings`
- `state`

这个抽象结构已经足以驱动 DSL 生成与后续代码生成。

## 6. 绑定失败时当前怎么处理

当前实现里的失败处理逻辑偏“宽松降级”，而不是“严格报错”。

### 6.1 `documentation` 缺失或非法 JSON

当前行为：

- `parse_json_documentation()` 返回空字典
- 结果是：
  - `input mapping` 为空
  - `output mapping` 为空

即：

- **不会在这一层直接抛出绑定异常**
- 但生成出来的 `businessrule` 语义会不完整

### 6.2 BPMN 中没有显式 DMN 路径 / decision id

当前行为：

- 不报错
- 直接使用命名约定推导：
  - `<rule.id>.dmn`
  - `<rule.id>_DecisionID`

### 6.3 真正的风险

这意味着：

- 如果真实 DMN 文件名或 decision id 与约定不一致
- 当前绑定不会在 BPMN 解析阶段被及时发现

因此，当前更准确的说法是：

- **绑定失败没有完全显式的强校验逻辑**
- 更多是“约定优先、宽松生成、后续再暴露问题”

## 7. 与 `supplyChainPaper.dmn` 的关系

需要明确：

- `SupplyChain.bpmn` 中规则任务 ID：`Activity_0fbi09z`
- `supplyChainPaper.dmn` 主决策 ID：`Decision_0zwjfyy`

它们并不是当前实现里可直接自动对齐的一组名字。

所以这份示例能够说明：

- 当前绑定机制已经有“流程节点 -> 规则节点 -> 映射 -> DSL”的通路
- 但“BPMN 节点 -> 具体 DMN 文件 / 具体 decision id”的显式绑定还没有建模标准化

## 8. 一句话总结

当前 `newTranslator` 的 BPMN-DMN 绑定规则，本质上是：

**用 BusinessRuleTask + documentation 提供映射元数据，再用规则任务 ID 约定性推导 DMN 资源名和 decision id，最终生成 DSL businessrule。**

