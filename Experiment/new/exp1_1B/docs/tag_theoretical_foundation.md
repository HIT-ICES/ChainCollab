# TAG 类型化属性图的理论来源与采用理由

本文档用于支撑实验 1B 论文写作，解释为什么在 BPMN->DSL 源目标结构一致性验证中采用 TAG，即 Typed Attributed Graph，类型化属性图。

本文中的 TAG 不是临时自造的数据格式，而是对软件模型工程中“类型化图、属性图、图转换、模型转换追溯”相关理论的工程化采用。实验 1B 将 BPMN 源模型和 DSL 目标模型都规整为 TAG，是为了在统一的结构表示上执行元素覆盖、类型一致性、属性保持、关系保持和目标可追溯性检查。

## 1. TAG 的基本含义

TAG 是 Typed Attributed Graph 的缩写，可翻译为“类型化属性图”。

在实验 1B 中，一个 TAG 由三类信息组成：

```text
nodes：模型元素；
edges：模型元素之间的结构关系；
attrs：节点或边携带的关键属性。
```

因此，BPMN-TAG 和 DSL-TAG 的统一形式是：

```text
TAG = (Nodes, Edges, Type, Attrs)
```

其中：

```text
Nodes 表示模型中的对象，例如 participant、message、gateway、event；
Edges 表示对象之间的关系，例如 messageFlow、sequenceFlow、sender、receiver、enable；
Type 表示每个节点或边的类型，例如 bpmn:message、dsl:message；
Attrs 表示关键属性，例如 id、name、schema、gatewayType、initialState。
```

实验 1B 中的 TAG 是一种实验中间表示，用于比较 BPMN 与 DSL 的结构，不等同于 BPMN 标准本身，也不等同于 DSL 语法本身。

## 2. 理论来源一：软件模型可以表示为图

在模型驱动工程中，模型通常由“元素”和“元素之间的引用关系”组成。这种结构天然可以表示为图：

```text
模型元素 -> 图节点
模型引用 / 关联 / 依赖 -> 图边
模型字段 / 标记 / 配置 -> 图属性
元模型类型 -> 图类型
```

BPMN 和 DSL 都符合这个特征。

例如 BPMN：

```text
participant、message、gateway、event、task 可以表示为节点；
messageFlow、sequenceFlow、participantRef、messageRef 可以表示为边；
name、id、documentation、conditionExpression 可以表示为属性。
```

例如 DSL：

```text
participant、message、gateway、event、businessrule、oracletask 可以表示为节点；
sender、receiver、enable、gateway_branch、parallel_join_source 可以表示为边；
schema、initialState、gatewayType、dmnResource 可以表示为属性。
```

因此，把 BPMN 和 DSL 都抽取成图结构，是模型比较和结构一致性验证的自然选择。

## 3. 理论来源二：Typed Graph 提供类型约束

普通图只能表达“点”和“边”，但 BPMN 和 DSL 中的元素不是同质对象。一个 `message`、一个 `gateway`、一个 `businessrule` 的语义完全不同。

因此实验 1B 使用 typed graph 思路，即每个节点和边都带有类型：

```text
bpmn:message
bpmn:parallelGateway
bpmn:messageFlow
dsl:message
dsl:gateway
dsl:enable
```

类型化图的价值在于：

```text
1. 可以区分不同模型元素；
2. 可以基于类型定义合法映射；
3. 可以检查源类型和目标类型是否一致；
4. 可以避免只靠字符串 id 做弱匹配。
```

实验 1B 的 C2 `type_consistency` 就是基于 typed graph 思路：

```text
如果 BPMN 中的 bpmn:message 映射到了 DSL 中的 dsl:message，则类型一致；
如果 BPMN 中的 bpmn:message 映射到了 DSL 中的 dsl:gateway，则类型不一致。
```

这说明 TAG 中的 `type` 字段不是辅助信息，而是结构一致性判定的核心依据。

## 4. 理论来源三：Attributed Graph 支持属性保持检查

仅有类型还不够。模型转换不仅要保留元素和关系，还需要保留关键属性。

例如：

```text
BPMN message 的 documentation schema 应保留到 DSL message.schema；
BPMN participant 的多实例属性应保留到 DSL participant；
BPMN gateway 类型应保留到 DSL gateway.gatewayType；
BPMN businessRuleTask 的规则信息应体现在 DSL businessrule 中。
```

这就需要 attributed graph，即节点和边不仅有类型，还携带属性。

实验 1B 的 C3 `attribute_preservation` 正是基于 attributed graph 思路：

```text
根据 trace 找到 BPMN 节点和 DSL 节点；
读取二者 attrs 中的关键字段；
检查这些字段是否按映射契约保持一致。
```

因此，TAG 中的 `attrs` 是属性保持验证的必要基础。

## 5. 理论来源四：Typed Attributed Graph Transformation

Typed attributed graph transformation 是图转换理论中的经典方向。Ehrig、Prange、Taentzer 等人的工作对 typed attributed graphs 与 graph transformation 给出了形式化基础，并指出 typed attributed graph transformation 对软件工程中的建模、元建模和可视化语言具有重要意义。

这类理论说明：

```text
1. 软件模型可以被形式化为类型化属性图；
2. 模型转换可以被理解为图之间的结构变换；
3. 节点、边、类型和属性都可以纳入形式化分析；
4. 基于图的表示适合做转换正确性、局部一致性、并发性、冲突和约束等分析。
```

实验 1B 并没有实现完整的代数图转换系统，也没有声明 BPMN->DSL 转换是由图重写规则执行的。实验 1B 的做法是：

```text
借用 typed attributed graph 的表示能力，
将 BPMN 与 DSL 统一成可比较的结构图，
再在该结构图上进行转换结果的一致性验证。
```

换言之，本文采用 TAG 是一种面向实验验证的中间表示，而不是把整个 newTranslator 改写成图重写引擎。

## 6. 理论来源五：Triple Graph Grammars 的追溯思想

在模型转换领域，Triple Graph Grammars，简称 TGG，是一种经典的双向模型转换理论。TGG 的基本思想是同时维护三类图：

```text
source graph：源模型图；
target graph：目标模型图；
correspondence graph：源目标之间的对应关系图。
```

这个思想与实验 1B 的结构非常接近：

```text
BPMN-TAG
  对应 source graph；

DSL-TAG
  对应 target graph；

bpmn_dsl_trace.json
  对应 source-target correspondence / traceability links。
```

实验 1B 没有采用完整 TGG 规则引擎，但采用了 TGG 中非常关键的思想：

```text
源模型和目标模型不应只做文本比较；
应显式建立 source-target correspondence；
一致性检查应基于源模型、目标模型和对应关系共同完成。
```

这就是为什么实验 1B 不直接比较 BPMN XML 和 DSL 文本，而是采用：

```text
BPMN-TAG + DSL-TAG + bpmn_dsl_trace.json
```

作为验证基础。

## 7. 为什么不直接比较 XML 和 DSL 文本

如果直接比较 BPMN XML 与 DSL 文本，会遇到几个问题：

```text
1. 两者语法完全不同，文本结构不可直接对齐；
2. 同一个 BPMN 元素在 DSL 中可能不是同名文本片段；
3. 一个 BPMN 结构可能被展开为多个 DSL 结构；
4. 一个 DSL global 可能来自 BPMN documentation 中的派生信息；
5. 文本顺序变化不一定代表结构变化；
6. 只比较文本很难定位“元素、属性、关系”层面的错误。
```

例如：

```text
BPMN messageFlow 在 DSL 中不是 messageFlow 节点，
而是 DSL message 的 sender / receiver 关系。

BPMN choreographyTask 在 DSL 中不是 choreographyTask 节点，
而是 message 顺序和 enable 关系。
```

如果只比较文本，这类结构等价关系很难表达。TAG 则可以把它们规整为：

```text
节点是否存在；
边是否存在；
边的方向是否正确；
属性是否一致；
目标节点是否有来源。
```

这正好对应实验 1B 的检查目标。

## 8. 为什么不只用 AST

AST，抽象语法树，适合表示单一语言内部的语法结构，但实验 1B 要比较的是两个不同建模语言之间的结构一致性。

BPMN 和 DSL 的结构不是简单树形关系，而是图结构：

```text
messageFlow 可以跨参与者连接；
sequenceFlow 构成控制流图；
gateway 可以有多个输入和输出；
parallelGateway 有 join / split 结构；
message 具有 sender / receiver 双端关系；
DSL 中 enable、branch、parallel join 也都是图关系。
```

这些关系不是单纯父子树结构能够自然表达的。因此，使用图结构比使用 AST 更合适。

## 9. 为什么不只用 RDF / 知识图谱

RDF 或知识图谱也可以表达节点、边和属性，但实验 1B 的重点不是开放域知识表达，而是受控的模型转换一致性验证。

实验 1B 更需要：

```text
1. 明确的节点类型集合；
2. 明确的边类型集合；
3. 明确的映射契约；
4. 可计算的 coverage、consistency、traceability 指标；
5. 与 newTranslator 当前转换规则对齐。
```

因此，实验 1B 使用轻量级 JSON TAG，而不是引入 RDF/OWL 技术栈。

这种选择让实验实现更直接：

```text
TAG JSON 可由脚本直接生成；
mapping_contract.json 可直接描述转换规则；
一致性检查脚本可直接读取 nodes、edges、attrs 和 trace。
```

## 10. TAG 与实验 1B 五个指标的对应关系

| 实验指标 | 依赖的 TAG 信息 | 说明 |
|---|---|---|
| C1 element_coverage | BPMN-TAG nodes + trace links | 检查 BPMN 应转换节点是否有 DSL 对应 |
| C2 type_consistency | node.type + mapping contract | 检查源目标类型是否符合契约 |
| C3 attribute_preservation | node.attrs / edge.attrs | 检查关键属性是否保持 |
| C4 relation_preservation | BPMN-TAG edges + DSL-TAG edges | 检查结构关系是否保留 |
| C5 target_traceability | DSL-TAG nodes + trace links | 检查 DSL 关键元素是否有 BPMN 来源 |

可以看到，如果没有 TAG：

```text
C1 不知道源模型有哪些可转换元素；
C2 不知道元素类型；
C3 没有统一属性读取方式；
C4 无法统一比较关系；
C5 无法反向扫描目标元素。
```

因此 TAG 是实验 1B 指标可计算化的基础。

## 11. TAG 与 bpmn_dsl_trace.json 的关系

TAG 负责描述单个模型的结构：

```text
BPMN-TAG 描述 BPMN 源模型；
DSL-TAG 描述 DSL 目标模型。
```

`bpmn_dsl_trace.json` 负责描述两个 TAG 之间的对应关系：

```text
BPMN-TAG node / edge
  -> DSL-TAG node / edge
```

三者关系可以写成：

```text
Source TAG:
  Gs = (Ns, Es, Ts, As)

Target TAG:
  Gt = (Nt, Et, Tt, At)

Trace:
  R ⊆ (Ns ∪ Es) × (Nt ∪ Et)
```

其中 R 表示源目标追溯关系。

实验 1B 的一致性检查不是只看 trace，而是看：

```text
Gs + Gt + R + mapping_contract
```

也就是：

```text
BPMN-TAG + DSL-TAG + bpmn_dsl_trace.json + default_mapping_contract.json
```

## 12. 与本文实验实现的对应

本文实验实现中，TAG 被落地为 JSON 文件：

```text
bpmn/bpmn_tag.json
dsl/dsl_tag.json
```

每个 TAG 包含：

```json
{
  "case_name": "SupplyChainPaper",
  "model_type": "bpmn",
  "nodes": [],
  "edges": [],
  "derived": []
}
```

其中：

```text
nodes 表示模型元素；
edges 表示结构关系；
derived 表示由 BPMN documentation、条件表达式或参数推导出的派生元素；
attrs 表示节点和边的关键属性。
```

这种 JSON TAG 是对 typed attributed graph 思想的工程化实现，目的是支撑自动化实验，而不是替代完整的图转换理论框架。

## 13. 论文中可使用的表述

论文中可以这样描述：

```text
为避免直接比较 BPMN XML 与 DSL 文本造成的语法差异干扰，本文将源模型和目标模型分别抽取为类型化属性图（Typed Attributed Graph, TAG）。TAG 以节点表示模型元素，以边表示元素间结构关系，并通过类型和属性刻画模型元素的语义类别与关键字段。该表示借鉴了图转换和模型驱动工程中 typed attributed graph 的形式化思想，使 BPMN 与 DSL 能够在统一的结构层上进行比较。
```

也可以这样描述 trace：

```text
在获得 BPMN-TAG 和 DSL-TAG 后，本文根据映射契约生成源目标追溯关系 bpmn_dsl_trace.json。该追溯关系类似于模型转换理论中 source-target correspondence 的工程化实现，用于记录 BPMN 元素、关系及其派生结构与 DSL 元素、关系之间的对应关系。后续一致性检查基于 BPMN-TAG、DSL-TAG 和追溯关系共同完成。
```

也可以这样描述为什么适合 1B：

```text
实验 1B 关注的是 BPMN 到 DSL 转换后的结构保持性，包括元素覆盖、类型一致性、属性保持、关系保持和目标可追溯性。TAG 同时包含节点、边、类型和属性，能够直接支撑上述五类指标的自动计算，因此被用作本实验的核心中间表示。
```

## 14. 与现有理论的关系边界

需要注意，本文采用 TAG 时应避免过度声明。

可以声明：

```text
本文借鉴 typed attributed graph 和 model transformation traceability 的思想；
本文将 BPMN 与 DSL 工程化抽取为 TAG；
本文基于 TAG 和 trace 执行结构一致性验证。
```

不宜声明：

```text
本文实现了完整的代数图转换系统；
本文实现了完整 TGG 转换引擎；
本文证明了 BPMN->DSL 转换在图转换理论上的完备性和正确性。
```

更准确的表述是：

```text
TAG 在本文中作为源目标模型结构比较的中间表示，
用于支持实验层面的结构一致性验证。
```

## 15. 参考文献建议

以下文献可以作为 TAG 理论来源和相关背景引用。

### 15.1 Typed attributed graph transformation

Hartmut Ehrig, Karsten Ehrig, Ulrike Prange, and Gabriele Taentzer.  
“Fundamental Theory for Typed Attributed Graphs and Graph Transformation based on Adhesive HLR Categories.”  
Fundamenta Informaticae, 74(1), 31-61, 2006.  
DOI: `10.3233/FUN-2006-74103`  
链接：https://journals.sagepub.com/doi/pdf/10.3233/FUN-2006-74103

可用于支撑：

```text
typed attributed graphs 是软件工程建模、元建模和可视化语言中的重要形式；
节点和边可以带类型和属性；
typed attributed graph transformation 有形式化理论基础。
```

### 15.2 Graph transformation and model-driven software development

Frederik Deckwerth.  
“Static Verification Techniques for Attributed Graph Transformations.”  
Dissertation, Technische Universität Darmstadt, 2017.  
DOI: `10.26083/tuprints-00006150`  
链接：https://tuprints.ulb.tu-darmstadt.de/handle/tuda/3539

可用于支撑：

```text
图转换具有形式化基础和工具支持；
图转换可用于模型驱动软件开发中的分析和验证。
```

### 15.3 Triple Graph Grammars and model transformation traceability

Stephan Hildebrandt, Leen Lambers, Holger Giese, Jan Rieke, Joel Greenyer, Wilhelm Schäfer, Marius Lauder, Anthony Anjorin, and Andy Schürr.  
“A Survey of Triple Graph Grammar Tools.”  
Electronic Communications of the EASST, 2013.  
DOI: `10.14279/tuj.eceasst.57.865`  
链接：https://eceasst.org/index.php/eceasst/article/view/2083

可用于支撑：

```text
TGG 是形式化的双向模型转换语言；
TGG 在实践中用于模型转换；
source、target 和 correspondence 的思想适合解释源目标追溯。
```

### 15.4 TGG correctness and completeness

Hartmut Ehrig, Claudia Ermel, Frank Hermann, and others.  
“On-the-Fly Construction, Correctness and Completeness of Model Transformations based on Triple Graph Grammars.”  
MODELS 2009.  
链接：https://orbilu.uni.lu/handle/10993/5601

可用于支撑：

```text
TGG 可用于模型转换的一致性、正确性和完备性讨论；
source-target correspondence 是模型转换验证的重要基础。
```

### 15.5 Recent TGG formulation

“Incremental model transformations with triple graph grammars for multi-version models and multi-version pattern matching.”  
Software and Systems Modeling, 2024.  
链接：https://link.springer.com/article/10.1007/s10270-024-01238-1

可用于支撑：

```text
TGG 通过 source、correspondence、target 三部分关联源目标建模语言；
TGG 规则可同时构造一致的源-对应-目标图结构。
```

## 16. 小结

实验 1B 采用 TAG 的原因可以概括为：

```text
1. BPMN 和 DSL 都可以自然表示为节点、边、属性组成的模型图；
2. 类型化图支持检查源目标元素类型是否正确映射；
3. 属性图支持检查关键字段是否保留；
4. 图结构支持检查 messageFlow、sequenceFlow、enable、gateway branch 等关系是否保持；
5. TAG 与 trace 结合后，可以支撑源目标可追溯性验证；
6. 该做法与 typed attributed graph transformation 和 TGG 中的 source-target correspondence 思想一致。
```

因此，TAG 是实验 1B 的合适中间表示：它既有现有理论基础，又足够轻量，能够直接服务于本实验的自动化结构一致性检查。
