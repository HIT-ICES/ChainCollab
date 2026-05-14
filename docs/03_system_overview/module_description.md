# newTranslator 模块职责说明

## 1. 顶层模块

| 模块 | 关键文件/目录 | 职责 | 输入 | 输出 |
|---|---|---|---|---|
| `generator/` | `translator.py`、`bpmn_to_dsl.py`、`b2c_to_solidity.py`、`split_mode.py` | 主转换引擎；负责 BPMN/DMN 解析后的编排、DSL 生成、Solidity 绑定生成、split mode 处理 | BPMN、DMN、配置 | B2CDSL、Solidity、FFI、split 计划 |
| `generator/parser/choreography_parser/` | `parser.py`、`elements.py`、`protocals.py` | BPMN Choreography 解析器；构造图模型并建立节点/边引用关系 | BPMN XML | `Choreography` 图对象 |
| `generator/parser/dmn_parser/` | `parser.py` | DMN 决策解析器；抽取决策、输入、输出、依赖并识别主决策 | DMN XML | Decision 列表、主决策 ID |
| `service/` | `api.py` | 后端接口层；把转换能力封装为 REST API | BPMN/DMN/DSL 文本 | DSL、Go/Solidity 代码、FFI、元数据、决策分析结果 |
| `dashboard/` | `src/components/TranslatorWorkbench.tsx`、`src/services/translator.ts` | 前端工作台；负责文件上传、接口调用、结果展示 | 用户上传/粘贴的 BPMN/DMN | 前端展示结果 |
| `DSL/B2CDSL/` | `b2cdsl/b2c.tx` | 定义中间语言语法与元模型 | DSL 语法设计 | textX 元模型 |
| `CodeGenerator/b2cdsl-go/` | `b2cdsl_go/__init__.py`、`templates/*.jinja` | DSL 到 Hyperledger Fabric Go 链码生成器 | B2CDSL | Go 链码 |
| `CodeGenerator/b2cdsl-solidity/` | `b2cdsl_solidity/__init__.py`、`templates/contract.sol.jinja` | DSL 到 Solidity 合约生成器 | B2CDSL | Solidity 合约 |
| `subgraph_analysis/` | `analyze_bpmn_sese.py`、`annotate_bpmn_groups.py` | BPMN 子图/SESE 分析与可视化标注 | BPMN | SESE JSON、HTML、分组 BPMN |
| `MDAcheck/` | `校验规则汇总.md`、`bpmn-positive/`、`datasets/` | MDA/OCL 校验与实验数据管理 | DSL/XMI/变异模型 | 校验报告、规则覆盖、数据集 |
| `example/` | `chaincode.b2c`、`chaincode.go` | 历史示例与参考工件 | 手工/生成示例 | 示例 DSL/Go |
| `build/` | `bpmn/`、`b2c/`、`chaincode/`、`solidity/` | 默认构建输出目录 | 生成过程产物 | 中间与最终工件 |

## 2. 核心类与职责

### 2.1 BPMN 解析侧

- `Choreography`
  - BPMN 图模型容器。
  - 负责加载 XML、解析节点/边、建立 ID 到对象的映射、生成拓扑图。
- `Participant` / `Message` / `ChoreographyTask` / `BusinessRuleTask` / `ReceiveTask` / `ScriptTask`
  - BPMN 元素对象。
  - 用统一对象接口支撑后续 DSL 映射。
- `MessageFlow` / `SequenceFlow`
  - 表示消息流与控制流。
  - `SequenceFlow` 会保留条件表达式，供网关分支翻译使用。

### 2.2 规则与参数抽取侧

- `ParameterExtractor`
  - 从消息文档 JSON、BusinessRuleTask 文档、网关条件中推导全局变量定义。
  - 负责把 BPMN 中隐式的数据概念整理成 DSL `globals`。
- `ParticipantMetadataResolver`
  - 从 `generator/bindings.json` 中补全参与者 `msp/x509/attributes`。
- `MessageCatalog`
  - 汇总消息、消息流和 schema 信息。
- `FlowPlanner`
  - 把 BPMN 控制流翻译成 DSL `flows` 语句。
  - 负责 start flow、message flow、gateway choose、parallel join、businessrule/oracle flow 的拼接。

### 2.3 DSL 生成侧

- `DSLContractBuilder`
  - 把参与者、全局变量、消息、网关、事件、业务规则、Oracle 任务、流程语句组织成完整合约文本。
- `GoChaincodeTranslator`
  - 历史命名沿用。
  - 实际职责是“BPMN -> B2CDSL + FFI + 元数据提取”。
- `SolidityContractTranslator`
  - 在 `GoChaincodeTranslator` 基础上复用 DSL 生成，再进一步调用 Solidity 渲染器。

### 2.4 代码生成侧

- `DSLContractAdapter`
  - 从 textX 解析后的 Contract 模型里提取 sections，转换成模板友好的结构。
- `GoChaincodeRenderer`
  - 为 Go 模板构造上下文。
  - 负责状态枚举、消息方法、网关方法、规则方法、Oracle 方法的渲染输入。
- `SolidityRenderer`
  - 为 Solidity 模板构造上下文和 execution layout。
  - 除代码渲染外，还会产出前端可消费的执行布局描述。

## 3. 主链路职责拆分

### 3.1 主链路一：BPMN -> B2CDSL

- 入口：`generator/bpmn_to_dsl.py`
- 核心职责：
  - 读取 BPMN。
  - 解析流程结构。
  - 推导数据/条件。
  - 输出 B2CDSL。

### 3.2 主链路二：B2CDSL -> Go

- 入口：`nt.sh` 里的 `nt-go-gen` 或直接调用 `b2cdsl-go`。
- 核心职责：
  - 用 textX 把 DSL 变成模型对象。
  - 用 Jinja 模板输出 Fabric 链码。

### 3.3 主链路三：B2CDSL -> Solidity

- 入口：`generator/b2c_to_solidity.py`、`service/api.py` 的 `/generate-eth` 或 `/compile`。
- 核心职责：
  - 解析 DSL。
  - 输出 Solidity 合约。
  - 附带 execution layout 和 FFI。

## 4. API 模块职责

`service/api.py` 里主要分成三类接口：

- 生成类
  - `/api/v1/chaincode/generate`
  - `/api/v1/chaincode/generate-eth`
  - `/api/v1/chaincode/compile`
- BPMN 元数据洞察类
  - `/api/v1/chaincode/getPartByBpmnC`
  - `/api/v1/chaincode/getMessagesByBpmnC`
  - `/api/v1/chaincode/getBusinessRulesByBpmnC`
- DMN 解析类
  - 决策列表与主决策识别接口

这些接口本身不实现转换规则，主要负责：

- 参数封装
- 调用 translator / renderer
- 返回 JSON
- 可选地把产物落盘到 runtime 目录

## 5. 前端模块职责

`dashboard/src/components/TranslatorWorkbench.tsx` 负责：

- BPMN/DMN 文本编辑与上传
- 发起链码生成
- 发起参与者/消息/业务规则洞察
- 发起 DMN 决策解析
- 展示 DSL/FFI/元数据结果

`dashboard/src/services/translator.ts` 负责：

- 对后端 API 做统一封装
- 隔离 URL 和请求细节

## 6. 辅助模块职责

### 6.1 `subgraph_analysis/`

- 分析 BPMN 的 SESE 子图。
- 支撑流程拆分和可视化。
- 更偏研究与增强能力，不是最短生成链路必需。

### 6.2 `MDAcheck/`

- 通过 OCL 校验 DSL/模型结构正确性。
- 维护正例、负例、变异样本与报告。
- 更偏质量保障与实验支撑。

## 7. 示例说明

本次整理的完整输入输出示例采用 `SupplyChainPaper7777` 业务流程，已放入：

- `docs/03_system_overview/end_to_end_example/example.bpmn`
- `docs/03_system_overview/end_to_end_example/example.dmn`
- `docs/03_system_overview/end_to_end_example/generated.dsl`
- `docs/03_system_overview/end_to_end_example/generated_chaincode.go`
- `docs/03_system_overview/end_to_end_example/generated_contract.sol`

需要注意一个当前实现细节：

- 生成的 DSL 里，`businessrule` 的 `dmn` 字段是按 `BusinessRuleTask.id + ".dmn"` 自动合成的。
- 因此示例中的 `generated.dsl` 会引用 `Activity_0rm8bkp.dmn`，而文档示例文件名是 `example.dmn`。
- 这不影响“模块关系”和“生成链路”的理解，但如果你后面要做文档图或产品化，可以把这部分再做成显式配置映射。

