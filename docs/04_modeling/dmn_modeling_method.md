# 3.3 Decision Modeling with DMN

## 1. 建模目标

这一节要回答的问题是：**业务规则在 `newTranslator` 中如何用 DMN 建模。**

在 `newTranslator` 的当前实现里，DMN 的主要职责不是直接控制流程图，而是：

- 把业务判断结构化为决策表
- 提供输入变量
- 产出决策结果
- 再由 BPMN 的 `BusinessRuleTask` 和后续 `exclusive gateway` 使用这些结果

## 2. 示例文件

- DMN XML： [dmn_example.dmn](/home/shenxz-lab/code/ChainCollab/docs/04_modeling/dmn_example.dmn)
- 决策表示意图： [dmn_table.png](/home/shenxz-lab/code/ChainCollab/docs/04_modeling/dmn_table.png)
- 支持特性说明： [dmn_supported_features.md](/home/shenxz-lab/code/ChainCollab/docs/04_modeling/dmn_supported_features.md)
- 解析结果示例： [dmn_parser_output_example.json](/home/shenxz-lab/code/ChainCollab/docs/04_modeling/dmn_parser_output_example.json)

本节使用的示例来自：

- `Experiment/BPMNwithDMNcase/supplyChainPaper.dmn`

## 3. 这个 DMN 模型表达了什么

该 DMN 示例包含两个决策：

### 3.1 第一个决策

- decision id：`decision_0tybghz`
- decision name：`Initial Priority Decision`

输入：

- `numberOfUnits`
- `urgent`

输出：

- `initialPriority`

业务意义：

- 先根据订单数量与紧急程度，得出初始优先级

### 3.2 第二个决策

- decision id：`Decision_0zwjfyy`
- decision name：`Final Priority Adjustment Decision`

输入：

- `initialPriority`
- `supplierReputation`

输出：

- `finalPriority`

业务意义：

- 再结合供应商信誉，对初始优先级进行修正

## 4. DMN 输入变量列表

按当前示例，决策表直接出现的输入变量如下：

| 变量名 | 类型 | 所属决策 |
|---|---|---|
| `numberOfUnits` | `number` | `decision_0tybghz` |
| `urgent` | `boolean` | `decision_0tybghz` |
| `initialPriority` | `string` | `Decision_0zwjfyy` |
| `supplierReputation` | `number` | `Decision_0zwjfyy` |

如果从整个决策链看，业务上相关的输入变量集合是：

- `numberOfUnits`
- `urgent`
- `supplierReputation`

## 5. DMN 输出变量列表

| 变量名 | 类型 | 所属决策 |
|---|---|---|
| `initialPriority` | `string` | `decision_0tybghz` |
| `finalPriority` | `string` | `Decision_0zwjfyy` |

## 6. DMN decision id

当前示例中的 decision id 为：

- `decision_0tybghz`
- `Decision_0zwjfyy`

其中主决策 id 是：

- `Decision_0zwjfyy`

原因是它没有被其他 decision 再依赖。

## 7. `newTranslator` 中的 DMN 建模方法

在 `newTranslator` 当前实现里，DMN 建模方法可以概括为：

1. 用 `decision` 表示规则节点
2. 用 `decisionTable` 表示规则主体
3. 用 `input` / `inputExpression` 定义决策输入变量
4. 用 `output` 定义决策输出变量
5. 用 `rule` / `inputEntry` / `outputEntry` 定义逐行规则
6. 用 `informationRequirement` 表达：
   - `requiredInput`
   - `requiredDecision`

这样形成一个可以解析的 DRD + decision table 结构。

## 8. 当前实现下的一个关键事实

`newTranslator` 的 DMN 解析器当前主要做的是 **结构提取**，而不是完整 DMN 运行时求值。

它会提取：

- 决策 id / name
- 信息依赖
- 输入变量
- 输出变量
- 主决策

但它不在这个解析阶段负责：

- 直接执行 decision table
- 完整实现 DMN FEEL 语义

因此，DMN 在系统中的主要价值是：

- 作为规则模型输入
- 为 BPMN 绑定与 DSL `businessrule` 生成提供结构基础

## 9. 一句话总结

在 `newTranslator` 中，DMN 建模的核心是：

**用 decision table 把业务规则的输入、输出和依赖关系结构化表达出来，再交给 BPMN 规则节点和 DSL 映射使用。**

