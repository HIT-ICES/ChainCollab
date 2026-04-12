# 实验二项目总结

这份文档用于帮助你**快速掌握** `exp2_semantic_fidelity` 这个实验目录。

如果只想快速接手，请先读这份，再读 `README.md`。

如果你想先看实验二的断言体系，可以直接读：

- [ASSERTION_TABLE.md](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/ASSERTION_TABLE.md:1)

## 1. 一句话概括

这个项目做的是：

**把 B2CDSL、Go、Solidity 都抽成统一语义 IR，然后自动比较 DSL 语义是否被目标代码保留。**

## 2. 项目定位

它是实验二：

**B2CDSL 到目标代码的语义保真验证**

它的定位是一个：

- 独立实验目录
- 静态验证工具链
- 不修改 `newTranslator` 核心逻辑

## 3. 它验证什么

主要验证两件事：

### 结构语义

DSL 中的这些元素是否都落到了代码里：

- participants
- globals
- messages
- events
- gateways
- businessrules

### 流程语义

DSL 中的每条 flow 在 Go / Solidity 中是否存在语义等价逻辑：

- trigger 是否存在
- action 是否被实现
- `set` 是否变成赋值
- `enable / disable / complete` 是否变成状态推进
- 分支条件是否在代码里体现

## 4. 它不做什么

这个实验不做：

- 不部署合约
- 不跑链
- 不做 Fabric / Geth 执行
- 不做链上验证
- 不改生成器源代码
- 不做运行时 trace 验证

所以这是一个：

**静态语义验证项目，不是执行验证项目。**

## 5. 和 newTranslator 的关系

这个实验目录本身不生成 DSL / Go / Solidity 的核心逻辑。

它做的是：

1. 调用 `newTranslator` 现有命令生成产物
2. 在实验目录外部提取语义
3. 做自动比较
4. 生成报告

复用的关键入口：

- grammar：`src/newTranslator/DSL/B2CDSL/b2cdsl/b2c.tx`
- `nt-bpmn-to-b2c`
- `nt-go-gen`
- `nt-sol-gen`

## 6. 主流程

主流程非常清晰：

```text
输入 .b2c 或 .bpmn
  -> 调用 newTranslator 生成 DSL / Go / Solidity
  -> 提取 DSL IR
  -> 提取 Go IR
  -> 提取 Solidity IR
  -> 比较 IR
  -> 生成 JSON 报告
  -> 生成 Markdown 报告
```

## 7. 关键文件怎么看

### 总控入口

- [run_exp2.py](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/run_exp2.py:1)

你可以把它理解为“实验流水线 orchestrator”。

### DSL 提取

- [tools/extract_dsl_ir.py](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/tools/extract_dsl_ir.py:1)

作用：

- 用 textX 官方方式解析 DSL
- 输出统一 DSL-IR

### Go 提取

- [tools/extract_go_ir.go](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/tools/extract_go_ir.go:1)
- [tools/extract_go_ir.py](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/tools/extract_go_ir.py:1)

作用：

- 用 Go 官方 AST 提取函数、赋值、分支、调用
- 标准化为统一 Go-IR

### Solidity 提取

- [tools/extract_sol_ir.py](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/tools/extract_sol_ir.py:1)

作用：

- 调用 `solc --standard-json`
- 读取官方 AST
- 标准化为统一 Solidity-IR

### IR 统一与比较

- [tools/normalize_ir.py](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/tools/normalize_ir.py:1)
- [tools/compare_ir.py](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/tools/compare_ir.py:1)

作用：

- 统一 trigger / action 表达
- 做结构与 flow 比较

## 8. IR 设计思路

本项目不做“原始 AST 树同构比较”，而是：

**AST -> 统一语义 IR -> 语义匹配**

这是整个实验能落地的关键。

因为：

- DSL AST、Go AST、Solidity AST 的结构天然不同
- 直接做树级同构基本不可行
- 但把它们统一到 flow 语义层之后，就能比较

## 9. 输出怎么看

每个 case 目录里最重要的是：

- `report.md`
- `compare_go.json`
- `compare_sol.json`
- `dsl_ir.json`
- `go_ir.json`
- `sol_ir.json`

建议阅读顺序：

1. 先看 `report.md`
2. 再看 `compare_go.json` / `compare_sol.json`
3. 如果还要定位原因，再看各自 IR

## 10. 目前成果

这个实验目录已经具备：

- 独立目录结构
- 命令行入口
- 正例 / 负例案例组织
- DSL / Go / Solidity 提取
- JSON 比较结果
- Markdown 报告
- pytest 基础测试

当前测试状态：

- `4 passed`

当前批量 seed case 结果见：

- [outputs/summary.md](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/outputs/summary.md:1)

其中案例按两类组织：

- `cases/positive/`
  作用：正例主集，用于展示系统能正确识别与匹配的典型 DSL 语义
  说明：当前目标是形成 15 个稳定通过的主正例样例

- `cases/negative/`
  作用：负例补充集，用于放置无效 DSL / 非法模型
  说明：这些负例不再是“复杂但合法的困难样例”，而是应当在 DSL 解析 / 引用解析阶段被拒绝的非法输入

- `config/assertion_table.yaml`
  作用：统一断言表
  说明：基于 `src/newTranslator/DSL/B2CDSL/b2cdsl/b2c.tx` 与 `src/newTranslator/MDAcheck/check.ocl` 整理出的 grammar/OCL 断言定义

- `config/case_assertion_matrix.yaml`
  作用：案例-断言矩阵
  说明：描述“哪些正例覆盖哪些断言”“哪些负例针对哪些断言”

- `tools/generate_negative_cases.py`
  作用：基于统一断言表中的 `negative_generators` 批量生成负例 DSL

- `cases/reference_bpmn/`
  作用：保留从仓库现有 BPMN 图直接复用的参考样例
  说明：这些样例便于后续做“从真实 BPMN 图进入实验二”的扩展验证，但默认不纳入 15 个主正例 + 3 个负例的统计口径

现在 summary 与单个 `report.md` 都会带上断言编号，因此你可以从“案例结果”直接追到“被验证的 grammar/OCL 规则”。

## 11. 当前优点

- 完全不改 `newTranslator` 核心代码
- DSL / Go / Solidity 都优先用官方解析机制
- 结构化输出清晰
- 能自动跑多个 case
- 可复现
- 便于后续继续扩展规则

## 12. 当前短板

目前最主要的短板有：

- Go 侧部分复杂流程仍会得到 `PARTIAL`
- 某些表达式比较仍偏“文本证据级”
- Oracle task 只做了预留，没有完整语义对比
- 还没有把仓库里全部 BPMN/DMN 历史案例批量纳入

## 13. 如果你后续要改，优先改哪里

### 想增强匹配准确率

先看：

- [tools/normalize_ir.py](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/tools/normalize_ir.py:1)
- [tools/compare_ir.py](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/tools/compare_ir.py:1)

### 想扩充输入样例

先看：

- `cases/positive/*.b2c`
- `cases/positive/*.bpmn`
- `cases/negative/*.b2c`

如果你想继续增加正例，推荐优先从仓库已有 BPMN 图中挑选：

- `Experiment/new/exp2_semantic_verification/cases/*/input.bpmn`
- `Experiment/CaseTest/*.bpmn`
- `Experiment/BPMNwithDMNcase/*.bpmn`

### 想对接真实仓库案例

可以优先从这些目录开始：

- `Experiment/BPMNwithDMNcase/`
- `Experiment/CaseTest/`

## 14. 最短上手路径

如果你现在就想最快掌握：

1. 看本文件
2. 看 [README.md](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/README.md:1)
3. 跑 `run_exp2.py --all-seeds`
4. 看 [outputs/summary.md](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/outputs/summary.md:1)
5. 打开某个 case 的 `report.md`

如果你要写实验说明，也可以直接把案例分成：

- 正例：证明系统能正确验证
- 负例：证明系统能识别当前不完全支持或不完全匹配的情况

## 15. 结论

这个项目已经不是“想法阶段”，而是已经形成了一个可运行闭环：

- 可生成
- 可提取
- 可比较
- 可报告
- 可测试

如果后续继续迭代，重点就不再是“从 0 到 1 搭框架”，而是：

**继续提升 IR 抽取质量和 flow 语义匹配精度。**
