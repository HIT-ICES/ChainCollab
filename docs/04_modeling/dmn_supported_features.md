# DMN 支持特性说明

## 1. 结论

`newTranslator` 当前对 DMN 的支持，重点是 **决策结构解析**，不是完整的 DMN 标准运行时实现。

## 2. 当前明确支持的内容

### 2.1 Decision

支持解析：

- `decision/@id`
- `decision/@name`

### 2.2 Decision Table

支持解析：

- `decisionTable`
- `input`
- `inputExpression`
- `output`
- `rule`
- `inputEntry`
- `outputEntry`

也就是说，当前支持的决策类型本质上是：

- **Decision Table 类型的 DMN 决策**

### 2.3 Information Requirement

支持解析：

- `requiredInput`
- `requiredDecision`

因此可以识别简单的 DRD 依赖关系。

### 2.4 InputData

支持解析：

- `inputData/@id`
- `inputData/@name`

### 2.5 主决策识别

支持：

- 从多个 decision 中找出“没有被其他 decision 依赖的决策”
- 作为 `main_decision_id`

## 3. 当前支持的数据类型

解析器当前会保留 `inputExpression/@typeRef` 与 `output/@typeRef`，示例中可见：

- `number`
- `boolean`
- `string`

也就是说，当前系统对输入输出类型的使用，是以：

- 读取 `typeRef`
- 在后续 DSL/代码生成阶段再做类型映射

为主。

## 4. 当前不应夸大为“已支持”的内容

下面这些内容，在当前代码中**没有看到完整实现**，因此不宜写成“已支持”：

- 完整 FEEL 表达式求值引擎
- BKM
- Context
- Invocation
- Relation
- Literal Expression 作为独立决策类型
- Decision Service
- DMN 运行时执行与回写闭环

## 5. 从 `supplyChainPaper.dmn` 看当前支持边界

当前示例之所以可以被良好解析，是因为它正好属于“当前支持范围”：

- 两个 `decision`
- 都包含 `decisionTable`
- 使用 `requiredInput` / `requiredDecision`
- 输入输出字段清晰

因此它是一个非常合适的展示样例。

## 6. 一句话总结

`newTranslator` 当前支持的 DMN 能力可以准确表述为：

**支持基于 decision table 的 DMN 结构解析、输入输出提取、依赖关系提取和主决策识别。**

