# BPMN-DSL 一致性实验思路

## 本测试与 OCL 测试的区别

在这个实验里，需要先明确两类验证不是一回事。

### 1. OCL 测试在验证什么

当前 `src/newTranslator/MDAcheck/check.ocl` 的作用是：

- 检查 **DSL 模型自身** 是否合法
- 检查 DSL 是否满足语法补充约束、引用约束、类型约束、flow 结构约束
- 检查 DSL 是否满足代码生成器默认依赖的建模前提

因此，OCL 测试回答的是：

- “转换结果产出的 DSL 是否是一个**良构且可生成**的 DSL 模型”

它能证明：

- 目标 DSL 模型合法
- 目标 DSL 模型内部一致

它不能单独证明：

- 这个 DSL 是否**完整保留了源 BPMN 的元素与关系**
- 这个 DSL 是否与源 BPMN **一致**

换句话说：

- OCL 测试属于 **目标模型正确性 / 合法性验证**
- 不是严格意义上的 **源模型到目标模型一致性验证**


### 2. 本测试在验证什么

本实验要验证的是：

- 给定一个具体 BPMN 模型
- 转换后得到一个具体 DSL 模型
- 两者之间是否在结构和语义上保持一致

因此，本实验回答的是：

- “这个 BPMN 模型转换后得到的 DSL，是否**覆盖了源模型应保留的元素、属性、关系与流程语义**”

它关注的是：

- 元素有没有丢失
- 属性有没有保留
- 前后继关系有没有保留
- 条件分支和业务规则语义有没有保留
- 是否出现了无来源的目标元素

所以，两类测试的区别可以概括为：

| 项目 | OCL 测试 | BPMN-DSL 一致性测试 |
| --- | --- | --- |
| 验证对象 | DSL 模型自身 | BPMN 模型 + DSL 模型 + 二者映射关系 |
| 主要问题 | 目标模型是否合法 | 源模型语义是否被目标模型保留 |
| 验证层次 | 目标模型正确性 | 源目标一致性 |
| 能否证明“转换一致” | 不能单独证明 | 可以直接验证 |
| 是否需要 trace | 不一定 | 建议需要 |

因此，在整体实验设计中，建议将两者表述为：

1. `check.ocl`
   - 用于验证 BPMN->DSL 转换结果是否产生了一个合法 DSL
2. `BPMN-DSL 一致性实验`
   - 用于验证该 DSL 是否忠实保留了源 BPMN 的关键信息与流程语义

这两者是互补关系，而不是替代关系。


## 一、问题分层

如果要验证 BPMN 到 DSL 的一致性，不能简单地“比较 BPMN.ecore 和 DSL.ecore”。

需要先把层次分开：

### 1. 元模型层

这一层回答的是：

- BPMN 语言如何定义
- DSL 语言如何定义
- 哪些概念之间存在映射关系

例如：

- `Participant / Lane -> DSL Participant`
- `MessageFlow -> DSL Message`
- `ExclusiveGateway -> DSL Gateway(type=exclusive)`
- `BusinessRuleTask -> DSL BusinessRule`

这一层主要定义“映射设计”，但不能直接证明某个具体模型转换是否正确。

### 2. 模型实例层

这一层回答的是：

- 这个具体 BPMN 模型
- 转成的这个具体 DSL 模型
- 二者是否一致

真正的转换一致性验证，应该落在这一层。


## 二、总体思路

本实验建议采用“目标合法性 + 源目标一致性”双层结构：

1. **目标模型合法性**
   - 由 `check.ocl` 负责
   - 验证 DSL 是否良构、可生成

2. **源目标一致性**
   - 由本实验负责
   - 验证 BPMN 到 DSL 的元素、属性、关系、流程语义是否被保留


## 三、推荐的技术路线

不建议走“两个 Ecore 直接 diff”的路线。

更合理的方案是：

1. 使用现成 BPMN metamodel
2. 使用 DSL 的 Ecore/metamodel
3. 将 BPMN 与 DSL 都落成实例模型
4. 在实例层建立 trace
5. 再做结构与语义一致性检查


## 四、BPMN 是否需要转成 Ecore

需要，但准确说法不是“把 BPMN 文件转成 Ecore”，而是：

- 让 BPMN 文件进入 BPMN 的 metamodel / EMF 实例体系

也就是说：

- BPMN 有自己的 metamodel
- `.bpmn` 文件是这个 metamodel 的实例
- DSL 也有自己的 metamodel
- `.b2c` 文件或 `.xmi` 是 DSL metamodel 的实例

这样，验证的对象就变成：

- 源实例模型（BPMN）
- 目标实例模型（DSL）

而不是两个元模型本身。


## 五、一致性实验的核心方案

### 1. 映射契约定义

先显式定义 BPMN -> DSL 的映射契约。

可以用表格描述：

| BPMN 元素 | DSL 元素 | 一致性要求 |
| --- | --- | --- |
| StartEvent | Event + start flow | 必须保留启动语义 |
| EndEvent | Event | 必须保留终止语义 |
| MessageFlow | Message | `from/to` 必须保留 |
| ExclusiveGateway | Gateway | `type=exclusive` 必须一致 |
| ParallelGateway | Gateway | `type=parallel` 必须一致 |
| BusinessRuleTask | BusinessRule | DMN 引用与映射必须保留 |
| SequenceFlow | Flow relation | 前后继关系必须保留 |

这一步定义的是：

- 什么叫“正确映射”
- 什么叫“一致”


### 2. 生成 trace

建议在转换时同步生成 trace。

最简单的 trace 结构可以包含：

- `sourceId`
- `sourceType`
- `targetId`
- `targetType`
- `rule`
- `note`

更好的做法是直接记录对象引用，而不是只存字符串。

trace 的作用是：

- 证明某个 BPMN 元素映射到了哪个 DSL 元素
- 支持一对一、一对多、多对一映射
- 为后续一致性检查提供定位依据


### 3. 结构一致性检查

这一层检查元素、属性、关系是否保留。

建议至少检查四类性质。

#### 3.1 元素覆盖

每个应保留的 BPMN 元素都必须有对应 DSL 元素。

例如：

- 每个 `StartEvent` 必须映射到一个 DSL `Event`
- 每个 `MessageFlow` 必须映射到一个 DSL `Message`
- 每个 `BusinessRuleTask` 必须映射到一个 DSL `BusinessRule`

#### 3.2 属性保留

关键属性必须保留。

例如：

- gateway 类型一致
- message 的 sender/receiver 一致
- businessrule 的 DMN / decision 一致

#### 3.3 关系保留

流程关系不能丢失。

例如：

- BPMN 中的前后继关系要在 DSL flow 中体现
- BPMN 中的消息方向要在 DSL `from/to` 中体现
- BPMN 中的条件分支要在 DSL `choose` 中体现

#### 3.4 无伪目标元素

DSL 中不应无缘无故出现没有源 BPMN 依据的业务元素。

也就是说：

- 目标 DSL 中的核心业务元素要么有 trace 来源
- 要么被明确标注为 helper / derived


### 4. 语义一致性检查

如果只做元素覆盖，还不足以说明语义没变。

因此建议再做一层弱语义一致性检查。

最现实的做法是：

- 将 BPMN 与 DSL 都规约成统一的流程语义图

例如统一为：

- 节点：start / end / message / gateway / businessrule / event
- 边：enable / sequence / branch / join

然后比较：

- 起点是否一致
- 后继集合是否一致
- 条件分支是否一致
- 消息方向是否一致
- 有界路径集合是否一致

当前建议先做：

- 忽略循环
- 比较 simple paths / basic paths


## 六、推荐的实现方式

### 方案 A：Python 契约验证器

这是最现实、工作量最可控的方案。

流程如下：

1. 读取 BPMN XML
2. 读取转换后的 DSL
3. 解析出统一中间表示
4. 根据映射契约逐项检查
5. 输出：
   - coverage
   - missing mapping
   - attribute mismatch
   - relation mismatch
   - spurious target elements

优点：

- 容易实现
- 可控性强
- 适合当前项目快速落地

### 方案 B：跨模型 OCL

如果后续希望更形式化，可以把：

- BPMN 模型
- DSL 模型
- Trace 模型

放入同一个 ResourceSet，再写跨模型 OCL 约束。

但这一步实现成本更高，不建议作为第一阶段最小方案。


## 七、推荐的实验输出

建议每个 case 输出：

- `bpmn_model`
- `dsl_model`
- `trace`
- `consistency_report.json`
- `consistency_report.md`

报告中至少包括：

- 元素覆盖率
- 缺失元素列表
- 属性不一致列表
- 关系不一致列表
- 无来源目标元素列表
- 是否通过整体一致性检查


## 八、最终建议

如果用一句话总结这个实验：

- `check.ocl` 负责验证“输出 DSL 合法”
- 本实验负责验证“输出 DSL 是否与源 BPMN 一致”

因此，最合理的实验表述应该是：

1. 先用 OCL 证明转换结果在目标语言内部是良构的
2. 再用 BPMN-DSL 一致性实验验证转换是否真正保留了源模型语义

两者结合起来，才能更完整地支撑“BPMN->DSL 转换正确性”。
