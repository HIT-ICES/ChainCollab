# Input / Output Mapping 示例

## 1. 目的

`input mapping` 与 `output mapping` 的作用，是把：

- BPMN/DMN 里的业务变量名

映射到：

- `newTranslator` 生成的 DSL `globals`

这样后续代码生成器才能知道：

- 决策执行前该从哪里取输入
- 决策执行后该把结果写回哪个全局状态变量

## 2. 当前 BPMN 示例里的真实映射来源

在 [bpmn_example.bpmn](/home/shenxz-lab/code/ChainCollab/docs/04_modeling/bpmn_example.bpmn) 中，`BusinessRuleTask` 的 `documentation` 是：

```json
{
  "inputs": [
    {"name": "amount", "type": "number", "description": ""},
    {"name": "Self_pickup", "type": "boolean", "description": ""}
  ],
  "outputs": [
    {"name": "deliver", "type": "boolean", "description": ""}
  ]
}
```

当前转换器会按“同名 + 首字母大写/规范化”的方式生成 DSL 映射。

### 2.1 input mapping 示例

```text
input mapping {
    amount -> Amount
    Self_pickup -> Self_pickup
}
```

含义：

- DMN/BusinessRule 输入变量 `amount` 映射到 DSL 全局变量 `Amount`
- DMN/BusinessRule 输入变量 `Self_pickup` 映射到 DSL 全局变量 `Self_pickup`

### 2.2 output mapping 示例

```text
output mapping {
    deliver -> Deliver
}
```

含义：

- 决策输出 `deliver` 写回 DSL 全局变量 `Deliver`

## 3. 与 `supplyChainPaper.dmn` 对应的映射示例

你要求使用的 DMN 文件 [dmn_example.dmn](/home/shenxz-lab/code/ChainCollab/docs/04_modeling/dmn_example.dmn) 中有两个决策：

- `decision_0tybghz`：`Initial Priority Decision`
- `Decision_0zwjfyy`：`Final Priority Adjustment Decision`，这是主决策

其中主决策直接输入为：

- `initialPriority`
- `supplierReputation`

直接输出为：

- `finalPriority`

如果把这个主决策显式绑定到 BPMN/DSL，最自然的映射会是：

### 3.1 针对主决策的直接映射

```text
input mapping {
    initialPriority -> InitialPriority
    supplierReputation -> SupplierReputation
}

output mapping {
    finalPriority -> FinalPriority
}
```

### 3.2 如果把上游依赖也一起拉平

由于主决策依赖前一个决策 `decision_0tybghz`，在业务上它的完整输入链还涉及：

- `numberOfUnits`
- `urgent`
- `supplierReputation`

于是，一个更贴近“端到端业务输入”的映射也可能写成：

```text
input mapping {
    numberOfUnits -> NumberOfUnits
    urgent -> Urgent
    supplierReputation -> SupplierReputation
}

output mapping {
    finalPriority -> FinalPriority
}
```

注意：

- 这要求系统在运行时能先得到 `initialPriority`，或在决策引擎中递归执行依赖决策。
- 当前 `newTranslator` 的 BPMN 侧并没有把这种 DMN 决策链依赖显式建模出来。

## 4. 这两个例子说明了什么

当前系统里其实存在两层“映射”：

### 4.1 BPMN -> DSL 映射

- 来源：`BusinessRuleTask.documentation`
- 当前已实现

### 4.2 DSL -> 真实 DMN 决策输入输出映射

- 来源：应当由显式 DMN 文件与 decision ID 绑定来确定
- 当前只实现了“约定式命名”，没有完全显式化

## 5. 推荐写法

如果后续要把建模做得更稳妥，建议在 `BusinessRuleTask.documentation` 中同时携带：

```json
{
  "dmn": "supplyChainPaper.dmn",
  "decision": "Decision_0zwjfyy",
  "inputs": [
    {"name": "initialPriority", "type": "string"},
    {"name": "supplierReputation", "type": "number"}
  ],
  "outputs": [
    {"name": "finalPriority", "type": "string"}
  ]
}
```

这样可以把：

- DMN 资源
- 决策 ID
- 输入映射
- 输出映射

放到同一个绑定描述中。

## 6. 一句话总结

`input mapping` / `output mapping` 的本质，是把 DMN 参数名和系统状态变量名关联起来，好让后续 Go 链码 / Solidity 合约知道：

- 从哪些全局状态读取决策输入
- 把决策结果写回哪些状态槽位

