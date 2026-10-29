# 实验二：B2CDSL 到目标代码的语义保真验证

本目录实现了一个**独立的静态正确性验证工具链**，用于验证：

- `B2CDSL -> Go`
- `B2CDSL -> Solidity`

是否完整保留了 DSL 的结构语义与流程语义。

## 一、设计目标

本实验的核心目标是：

1. 解析 B2CDSL，提取统一 DSL-IR
2. 解析生成后的 Go 代码，提取统一 Go-IR
3. 解析生成后的 Solidity 代码，提取统一 Solidity-IR
4. 自动比较 DSL-IR 与 Go-IR / Solidity-IR
5. 输出机器可读 JSON 与人工可读 Markdown 报告

## 二、边界说明

本实验**只做静态语义验证**，不做以下内容：

- 不修改 `src/newTranslator` 现有核心生成器逻辑
- 不侵入已有 DSL / Go / Solidity 生成实现
- 不做合约部署
- 不做 Fabric / Geth 运行
- 不做链上执行验证
- 不做运行时 trace 验证

本实验通过**调用仓库现有入口**完成代码生成，再在实验目录外部进行解析、抽取、比较与报告生成。

## 三、复用的仓库入口

本实验优先复用了仓库中的现有入口：

- B2CDSL grammar：`src/newTranslator/DSL/B2CDSL/b2cdsl/b2c.tx`
- BPMN -> B2CDSL：`src/newTranslator/nt.sh` 中的 `nt-bpmn-to-b2c`
- B2CDSL -> Go：`src/newTranslator/nt.sh` 中的 `nt-go-gen`
- B2CDSL -> Solidity：`src/newTranslator/nt.sh` 中的 `nt-sol-gen`

AST / 解析方案：

- DSL：使用 textX 官方 metamodel 解析
- Go：使用官方 `go/parser`、`go/ast`
- Solidity：使用官方 `solc --standard-json`

## 四、目录结构

```text
Experiment/new/exp2_semantic_fidelity/
  ASSERTION_TABLE.md
  README.md
  PROJECT_SUMMARY.md
  requirements.txt
  run_exp2.py
  config/
    assertion_table.yaml
    case_assertion_matrix.yaml
    mapping_rules.yaml
  cases/
    positive/
      *.b2c
    negative/
      *.b2c
    reference_bpmn/
      *.bpmn
  outputs/
    positive/
      <case_name>/
        dsl_ir.json
        go_ir.json
        sol_ir.json
        compare_go.json
        compare_sol.json
        report.md
    negative/
      <case_name>/
        dsl_ir.json
        go_ir.json
        sol_ir.json
        compare_go.json
        compare_sol.json
        report.md
    summary.json
    summary.md
  tools/
    common.py
    extract_dsl_ir.py
    extract_go_ir.go
    extract_go_ir.py
    extract_sol_ir.py
    normalize_ir.py
    compare_ir.py
    generate_negative_cases.py
  tests/
    fixtures/
    test_dsl_parser.py
    test_go_extractor.py
    test_sol_extractor.py
    test_compare_ir.py
```

## 五、各脚本职责

### 1. 总控入口

- [run_exp2.py](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/run_exp2.py:1)

职责：

- 接收 `.b2c` 或 `.bpmn` 输入
- 调用 `newTranslator` 现有命令生成 DSL / Go / Solidity
- 调用各 IR 提取器
- 进行语义比较
- 生成 JSON 与 Markdown 报告

### 2. DSL 提取

- [tools/extract_dsl_ir.py](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/tools/extract_dsl_ir.py:1)

职责：

- 用 textX 官方方式解析 B2CDSL
- 抽取 `participants / globals / messages / events / gateways / businessrules / flows`
- 将 flow 规范化为统一的 trigger + actions + branches 表示

### 3. Go 提取

- [tools/extract_go_ir.go](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/tools/extract_go_ir.go:1)
- [tools/extract_go_ir.py](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/tools/extract_go_ir.py:1)

职责：

- 使用 Go 官方 AST 提取结构体、函数、条件分支、赋值与调用
- 进一步标准化为统一 Go-IR
- 识别与 DSL flow 对应的 handler、trigger、action

### 4. Solidity 提取

- [tools/extract_sol_ir.py](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/tools/extract_sol_ir.py:1)

职责：

- 调用 `solc --standard-json` 输出官方 AST
- 解析 contract、state variables、functions、if/else、require
- 标准化为统一 Solidity-IR

### 5. IR 规范化

- [tools/normalize_ir.py](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/tools/normalize_ir.py:1)

职责：

- 统一 DSL / Go / Solidity 的 trigger 与 action 语义表示
- 尽量把不同语言里的“状态推进”转换成统一规则

### 6. IR 比较

- [tools/compare_ir.py](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/tools/compare_ir.py:1)

职责：

- 做元素结构覆盖率检查
- 做 flow 规则匹配
- 输出 compare JSON 与报告内容

### 7. 负例生成

- [tools/generate_negative_cases.py](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/tools/generate_negative_cases.py:1)

职责：

- 从统一断言表读取 `negative_generators`
- 批量生成非法 DSL / 非法模型负例
- 保证负例与目标断言之间存在清晰映射

## 六、依赖安装

### 1. 实验目录 Python 依赖

建议直接使用 `newTranslator` 已有虚拟环境：

```bash
cd /root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity
/root/code/ChainCollab/src/newTranslator/.venv/bin/pip install -r requirements.txt
```

### 2. newTranslator 生成器依赖

如果 `newTranslator` 侧环境尚未准备，可执行：

```bash
cd /root/code/ChainCollab/src/newTranslator
source newtranslator_env.sh
nt-bootstrap
```

### 3. 额外工具

需要以下工具可用：

- `go`
- `solc`

当前环境中：

- Go AST 提取已可用
- `solc` 已可用

## 六点一、正例输入来源

当前实验输入分成两层：

- 主基准样例
  放在 `cases/positive/` 与 `cases/negative/`

- 参考 BPMN 样例
  放在 `cases/reference_bpmn/`
  作用：保留仓库中已有绘制好的流程图，便于后续从真实 BPMN 进入实验二链路，但默认不纳入“15 个主正例 + 3 个负例”的统计口径

当前主基准目标规模：

- 正例：15 个
- 负例：由断言表驱动生成的多类非法 DSL

当前保留的 BPMN 参考样例包括：

- `BikeRental_from_bpmn.bpmn`
- `Blood_analysis_from_bpmn.bpmn`
- `Coffee_machine_from_bpmn.bpmn`
- `Pizza_Order_from_bpmn.bpmn`
- `Purchase_from_bpmn.bpmn`

## 七、运行方法

## 七点一、正反例组织方式

实验二现在采用**正反例双目录**组织：

- `cases/positive/`
  说明：正面样例，为实验主体，优先用于展示系统可以正确验证的典型流程
  当前以 `.b2c` 主正例为主，目标是形成稳定通过的 15 个基准样例

- `cases/negative/`
  说明：负面样例，为实验补充，专门放置无效 DSL / 非法模型
  这些样例应在 DSL 解析 / 引用解析 / 约束阶段失败
  这些样例由断言表统一管理，可批量扩展

- `cases/reference_bpmn/`
  说明：从仓库已有 BPMN 图直接复用的参考样例
  默认不参与 `--all-seeds` 的主基准统计

当前建议理解方式是：

- 正例为主
- 负例为辅
- 正例用于展示“可正确匹配”
- 负例用于展示“parser / validator 能识别并拒绝非法输入”
- 正反例都回到同一张断言表口径下解释
- `reference_bpmn` 用于展示“从真实绘制流程图进入实验链路”

## 七点二、统一断言表

为了让正例和负例都建立在 `newTranslator` 的真实语法与约束基础上，本实验维护了两张配置表：

- [ASSERTION_TABLE.md](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/ASSERTION_TABLE.md:1)
- [config/assertion_table.yaml](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/config/assertion_table.yaml:1)
- [config/case_assertion_matrix.yaml](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/config/case_assertion_matrix.yaml:1)

其中：

- `ASSERTION_TABLE.md`
  面向阅读者的断言表说明文档，适合快速查看与论文引用

- `assertion_table.yaml`
  基于 `src/newTranslator/DSL/B2CDSL/b2cdsl/b2c.tx` 与 `src/newTranslator/MDAcheck/check.ocl` 提取出的统一断言表
- `case_assertion_matrix.yaml`
  描述“哪个正例覆盖哪些断言”“哪个负例针对哪些断言”

统一断言表中的每条断言至少包含：

- 断言编号
- 标题
- 维度
- 正例/负例适用模式
- 来源文件
- 来源规则
- 语义说明

当前断言主要覆盖：

- flow target 不存在
- set 变量不存在
- gateway 类型非法
- message trigger 不存在
- message sender 不存在
- businessrule mapping 引用不存在全局变量
- parallel await source 不存在
- start event 引用不存在

在这套机制下：

- 现有 15 个正例保持不变
- 正例通过矩阵文件标注各自覆盖的断言
- 负例通过断言表中的 `negative_generators` 自动生成
- 每个 case 的报告都会附带对应断言编号

基于统一断言表，负例可通过脚本自动生成：

- [tools/generate_negative_cases.py](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/tools/generate_negative_cases.py:1)

生成命令：

```bash
cd /root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity
PYTHONPATH=. /root/code/ChainCollab/src/newTranslator/.venv/bin/python tools/generate_negative_cases.py
```

## 七点三、断言表驱动关系

现在实验二采用如下关系：

1. `newTranslator` grammar / OCL -> 统一断言表
2. 统一断言表 -> 正例覆盖矩阵 / 负例目标矩阵
3. 正例保留现有 case，不改动样例本身，只补充覆盖断言说明
4. 负例根据断言表中的生成器定义批量构造
5. 运行报告按 case 输出，并附带断言编号

### 1. 运行单个正例 case

```bash
cd /root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity
PYTHONPATH=. /root/code/ChainCollab/src/newTranslator/.venv/bin/python run_exp2.py \
  --input cases/positive/basic_linear_case.b2c \
  --outdir outputs/positive/basic_linear_case
```

### 2. 运行单个负例 case

```bash
cd /root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity
PYTHONPATH=. /root/code/ChainCollab/src/newTranslator/.venv/bin/python run_exp2.py \
  --input cases/negative/invalid_missing_flow_target.b2c \
  --outdir outputs/negative/invalid_missing_flow_target
```

### 3. 从 BPMN 输入开始运行

```bash
cd /root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity
PYTHONPATH=. /root/code/ChainCollab/src/newTranslator/.venv/bin/python run_exp2.py \
  --input /root/code/ChainCollab/Experiment/BPMNwithDMNcase/Blood_analysis.bpmn \
  --outdir outputs/Blood_analysis
```

### 4. 批量运行主正例与负例

```bash
cd /root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity
PYTHONPATH=. /root/code/ChainCollab/src/newTranslator/.venv/bin/python run_exp2.py --all-seeds
```

批量运行后：

- 正例输出在 `outputs/positive/`
- 负例输出在 `outputs/negative/`
- 总览在 `outputs/summary.json` 与 `outputs/summary.md`

说明：

- `--all-seeds` 默认只跑 `positive` 与 `negative`
- `reference_bpmn` 中的 BPMN 参考样例不纳入该主基准统计
- `outputs/summary.md` 会附带每个 case 对应的断言编号

## 八、输出文件说明

每个 case 目录下会生成：

- `dsl_ir.json`
  说明：从 DSL 中提取的统一语义 IR

- `go_ir.json`
  说明：从 Go 代码中提取的统一语义 IR

- `sol_ir.json`
  说明：从 Solidity 代码中提取的统一语义 IR

- `compare_go.json`
  说明：DSL 与 Go 的比较结果

- `compare_sol.json`
  说明：DSL 与 Solidity 的比较结果

- `report.md`
  说明：人工可读报告

对于负例，还会额外生成：

- `dsl_parse_error.txt`
  说明：DSL 解析 / 引用解析失败信息

- `negative_check.json`
  说明：是否按预期拒绝非法输入

批量运行后还会生成：

- `outputs/summary.json`
- `outputs/summary.md`

其中总报告会区分：

- 正例
- 负例
- 自定义输入

并在正例、负例条目后附带断言编号列表。

## 九、比较逻辑

比较分为两层：

### 第一层：元素结构覆盖率

检查 DSL 中各类元素是否在代码中都有对应实现：

- global 是否落到状态变量
- message 是否有对应处理入口
- event 是否有对应触发入口
- gateway 是否有对应控制逻辑
- businessrule 是否有对应实现

输出：

- `matched`
- `missing`
- `extra`
- `unsupported`

### 第二层：flow 规则匹配

这是核心层。

对每条 DSL flow 检查代码 IR 中是否存在等价逻辑，至少比较：

- trigger 是否存在
- action 是否实现
- `set` 是否映射为赋值
- `enable / disable / complete` 是否映射为状态推进
- 分支条件是否存在对应控制逻辑

## 十、当前支持的 DSL 构造

当前已支持：

- participants
- globals
- messages
- events
- exclusive gateways
- parallel gateways
- businessrules
- start flow
- message flow
- gateway flow
- rule flow
- event flow
- `enable`
- `disable`
- `set`
- parallel join

## 十一、当前未完全支持 / 部分支持

当前仍然是部分支持或后续可扩展状态的内容：

- oracle task 的完整语义比较
- 更复杂表达式的严格语义等价证明
- 与运行时执行轨迹结合的动态验证
- 与所有仓库历史样例的全量适配

另外：

- Solidity 代码中默认占位的 `PlaceholderBusinessRule` 可能会被记为 extra
- Go 侧某些 case 的 flow 匹配仍有进一步增强空间

## 十一点一、当前断言表覆盖方式

当前口径下：

- 正例保留现有 15 个稳定样例
- 这些正例不会因为引入断言表而被替换
- 它们承担“覆盖断言”的角色
- 负例承担“定向触发断言失败”的角色

因此，实验二现在是“断言表 + 样例矩阵 + 自动验证”的组织方式，而不只是松散的 case 集合。

## 十二、PASS / PARTIAL / FAIL 判定

- `PASS`
  所有 flow 均匹配，且没有关键缺失

- `PARTIAL`
  部分 flow 匹配成功，但仍存在未匹配规则或部分结构支持不足

- `FAIL`
  基本无法建立有效语义映射，或 flow 几乎未匹配

对于负例，采用单独口径：

- `EXPECTED_REJECT`
  非法 DSL 已在解析 / 引用解析 / 约束阶段被正确拒绝

- `UNEXPECTED_ACCEPT`
  非法 DSL 未被拒绝，说明 parser / validator 约束不足

## 十三、当前实验结果概览

当前批量 seed case 结果见：

- [outputs/summary.md](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/outputs/summary.md:1)

目前大致情况是：

- 主正例集目标是提升到 15 个，并尽量全部达到 `Go PASS + Solidity PASS`
- 负例主要用于验证非法 DSL 是否会在解析 / 引用解析阶段被拒绝
- Solidity 侧整体匹配程度当前高于 Go 侧

这说明：

- 实验二的主闭环已跑通
- 提取与比较框架已可复用
- 负例能够帮助我们证明 parser / validator 对非法输入具有拦截能力

## 十四、快速查看建议

如果你第一次接手这个实验，建议按下面顺序看：

1. 看 [PROJECT_SUMMARY.md](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/PROJECT_SUMMARY.md:1)
2. 跑 `run_exp2.py --all-seeds`
3. 看 [outputs/summary.md](/root/code/ChainCollab/Experiment/new/exp2_semantic_fidelity/outputs/summary.md:1)
4. 进入某个 case 的 `report.md`
5. 若要深挖，再看 `dsl_ir.json`、`go_ir.json`、`sol_ir.json`

## 十五、补充说明

所有实现都遵守了以下原则：

1. 不改 old code，只加 new code
2. 优先复用仓库现有接口
3. DSL / Go / Solidity 都尽量走官方解析 / AST
4. 不为某个 case 硬编码“匹配成功”
5. 所有结果尽量可复现
