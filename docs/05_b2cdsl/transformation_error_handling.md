# 4.3 Transformation Error Handling

本节只描述当前代码里已经实现或可明确观察到的异常处理，不把“应当如何做”与“已经如何做”混写。

## 1. BPMN 文档 JSON 不合法

相关实现：

- `translator.py::parse_json_documentation()`

当前行为：

- 如果 `documentation` 为空，返回 `{}`。
- 如果 JSON 解析失败，返回 `{}`。

影响：

- 不会直接抛异常中断转换。
- 但消息 schema、BusinessRule 输入输出映射、Oracle 输出映射可能被静默丢失。

## 2. 缺少 DMN decision 或 DMN path

相关实现：

- `translator.py::_build_business_rules_section()`

当前行为：

- 不从 BPMN XML 显式读取 DMN 文件路径。
- 不从 BPMN XML 显式读取 decision id。
- 直接按 `BusinessRuleTask.id` 生成：
  - `dmn = "{rule.id}.dmn"`
  - `decision = "{rule.id}_DecisionID"`

影响：

- 转换阶段通常不会因为“缺少 DMN 绑定字段”失败。
- 但如果真实运行时找不到对应 DMN 资源，问题会延迟到执行或集成阶段暴露。

## 3. DMN 文件中不存在唯一主决策

相关实现：

- `parser/dmn_parser/parser.py::get_main_decision_id()`

当前行为：

- 如果主决策多于一个，抛出 `ValueError("More than one main decision")`。
- 如果不存在主决策，抛出 `ValueError("No main decision")`。

影响：

- 对 DMN 分析类工具或说明性输出会构成直接错误。
- 这类错误应被视为 DMN 模型本身不满足当前解析器假设。

## 4. Mapping 不完整

### BusinessRule 输入映射不完整

当前行为：

- 如果 `documentation.inputs` 缺失，对应 `input mapping` 会为空。
- 规则节点仍可能被生成到 DSL 中。

影响：

- 代码可以生成；
- 但规则执行时缺少稳定输入来源，行为语义不完整。

### BusinessRule 输出映射不完整

当前行为：

- 如果 `documentation.outputs` 缺失，`output mapping` 为空或不完整。

影响：

- 决策结果无法可靠写回 `globals`。
- 后续 gateway 条件如果依赖该变量，将无法保证语义正确性。

## 5. Unsupported BPMN element 或分支形式

### 元素层面

当前行为：

- 解析器优先处理已识别节点类型。
- 未进入现有分支的元素通常不会被完整转换为 DSL 一等元素。

结论：

- 当前系统并不是“任意 BPMN 元素全覆盖转换器”，而是“面向 Choreography + 代码生成约束”的子集转换器。

### 分支表达式层面

已有约束说明见 `MDAcheck/校验规则汇总.md`：

- `NotSupportedByCurrentCodeGen` 禁止当前代码生成器尚未实现的表达式分支。

影响：

- 虽然 DSL grammar 允许 `GatewayExpressionBranch`：

```dsl
if "some expression" then ...
```

- 但当前代码生成器更稳定支持的是“变量-关系-字面量”的比较式分支。

## 6. 生成 DSL 后为空

相关实现：

- `translator.py::_render_solidity_bundle()`

当前行为：

- 如果 DSL 模型中没有 `contracts`，抛出 `ValueError("No contracts defined in DSL.")`。

影响：

- 该错误出现在 DSL 进入后续生成阶段时，说明前一步未产出有效 contract。

## 7. 论文中建议的表述方式

- 当前实现对格式错误的 `documentation` 偏向“容错但可能静默降级”。
- 对 DMN 主决策结构错误采用“显式异常”。
- 对 BPMN/DMN 绑定缺失采用“约定式补全”。
- 对超出当前代码生成能力的建模形式，通过建模约束或校验规则提前限制。
