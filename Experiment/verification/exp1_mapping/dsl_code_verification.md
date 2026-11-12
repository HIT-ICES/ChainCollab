## 技术方案：验证 newTranslator 中模型驱动转换的正确性

本方案旨在通过系统化方法验证 newTranslator 框架中 BPMN→B2CDSL 及 B2CDSL→代码 两阶段的转换正确性，确保不依赖人工比对即可实现自动化验证，提升系统可靠性。

---

### 一、BPMN 到 B2CDSL 映射一致性验证

#### 1. 映射契约（Transformation Contracts）定义与验证

- **目标**：确保每类 BPMN 元素在 DSL 中有语义等价的映射，并被完整保留。
- **方法**：
  - 使用 OCL（对象约束语言）或定制 JSON Schema 描述 BPMN → DSL 映射规则。
  - 定义以下契约示例：
    - 每个 BPMN Pool/Lane → DSL participants
    - 每个 BPMN Message Flow → DSL message 定义 + flows 中启用语句
    - 每个 BPMN Gateway → DSL gateway（type 必须一致）
    - BPMN Start/End Events → DSL event + start/flow 定义
    - BPMN BusinessRuleTask → DSL businessrule + dmn 映射
  - 使用 Python 实现契约验证器，输入 BPMN XML 和输出 DSL，检查每项契约是否满足。

#### 2. 模型转换测试（覆盖率验证）

- **目标**：验证转换器对多样化输入模型的鲁棒性。
- **方法**：
  - 设计 BPMN 测试模型集：覆盖不同网关类型、嵌套流程、多参与者消息等场景。
  - 为每个 BPMN 模型运行 BPMN→DSL 转换器。
  - 基于契约验证生成的 DSL 是否满足约束。
  - 自动统计映射成功率、失败原因、覆盖的 DSL 元素类型数。

#### 3. 映射追踪与报告生成

- **目标**：建立从 BPMN 元素 → DSL 元素的追踪关系，便于问题定位。
- **方法**：
  - 转换器在运行时输出 mapping trace（如：BPMN_Element_ID → DSL_LineNumber）。
  - 将 trace 文件解析为报告，标出哪些 BPMN 元素未映射、是否存在一对多/多对一。

---

### 二、B2CDSL 到目标代码的语义保真验证

#### 1. AST 结构提取与比对

- **目标**：验证 DSL 元素在代码中有结构对应。
- **方法**：
  - 解析 DSL 文件，提取 participants、globals、messages、events、gateways、flows。
  - 使用 Go AST / Solidity AST 工具提取代码结构（变量、函数、类型等）。
  - 建立 DSL 元素与 AST 节点的映射规则。例如：
    - DSL global → Go `type State struct {}` / Solidity `contract` 中的 `public` 变量
    - DSL message → Go handler 函数 + 状态转移 / Solidity 函数 + 状态枚举
    - DSL flow 规则 → Go `switch`/`if` 分支 / Solidity `require` + 状态赋值组合
  - 编写 AST 匹配脚本，逐条检查 DSL 中的每个元素是否在代码中出现。

#### 2. 流程逻辑匹配与行为图模板

- **目标**：确保每条 DSL flows 规则在代码中被实现。
- **方法**：
  - 为常见 flow 模式（如 when message M sent then enable X）定义模板模式树。
  - 在 AST 中定位对应逻辑片段，验证其是否包含：
    - 条件判断（处理发送行为）
    - 状态更改语句（X 被置 READY）
    - 可选的变量赋值
  - 若某 DSL flow 在代码中无匹配结构 → 报告遗漏。

---

### 三、执行路径一致性验证（链码行为对比）

- **目标**：验证两个不同平台（如 Fabric 与 Ethereum）上生成的链码/合约，在同样输入路径下的执行行为一致，等价于从 B2CDSL 同源生成的两个实现是否行为等价。

- **方法**：借鉴 https://arxiv.org/pdf/2412.01196 方法：
  - 从 DSL flows 自动构造流程状态图。
  - 使用路径搜索算法（DFS+限制深度）生成 N 条合法执行路径（即消息发送与事件触发顺序）。
  - 对每条路径：
    - 构造两个测试脚本：Fabric 链码调用脚本、Solidity 合约调用脚本
    - 执行时记录：每一步前后状态（全局变量、元素状态）、链上日志或事件
    - 并行使用 DSL 模拟器生成每条路径的状态轨迹作为对照
    - 对比两平台的执行日志与 DSL 模拟的状态轨迹，判断其是否等价
  - 若执行状态、流程推进顺序一致，视为验证通过；若出现差异，记录偏差点、平台差异分析

- **附加工具建议**：
  - 使用统一格式（JSON 或 CSV）记录各平台状态变化
  - 可视化工具（如流程状态动画或状态迁移图）增强分析直观性
  - 支持钩子脚本注入模拟器/测试链码，截取关键状态点

---

### 四、总结

- 本方案提供从模型契约定义、自动转换测试、结构静态比对、跨平台行为对比的系统性验证手段。
- 支持将验证结果纳入 CI/CD 流水线，确保每次模型或生成逻辑修改都伴随一次完整验证。
- 提升模型驱动生成系统的透明度、可信度和自动化程度。

建议以订单处理/审批流程为案例，开发验证工具原型并迭代优化。

