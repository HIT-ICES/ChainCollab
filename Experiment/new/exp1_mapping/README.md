# 实验一：BPMN -> B2CDSL 映射一致性验证

这个实验项目用于验证：**BPMN/DMN 中的关键业务语义，是否被当前 `newTranslator` 正确保留到 B2CDSL 中。**

它不是部署工具，也不验证链码生成结果；它只关注模型映射正确性。

## 实验目标

给定一份 BPMN/DMN：

1. 调用当前 `newTranslator` 生成最新 `.b2c`
2. 解析 BPMN 和 B2CDSL
3. 按映射契约做自动校验
4. 输出结构化报告和批量汇总结果

重点验证的语义包括：

- `participants`
- `messages`
- `gateways`
- `events`
- `businessrules`
- `flows`

换句话说，本实验回答的问题是：

**原始 BPMN/DMN 中的关键业务元素，在经过 `newTranslator` 转换后，是否仍然能在 B2CDSL 中找到结构上和语义上对应的表示。**

## 当前验证契约

1. BPMN Pool/Lane -> DSL participants
2. BPMN Message Flow -> DSL message + flow 推进规则
3. BPMN Gateway -> DSL gateway 且 type 一致
4. BPMN Start/End Event -> DSL event + start/event flow
5. BPMN BusinessRuleTask -> DSL businessrule + dmn/decision/input/output mapping

## 项目特点

- 不修改 `newTranslator` 源码，只调用其现有生成链路
- 不依赖历史 `.b2c` 产物，默认每次重新生成 `.b2c`
- 报告可定位到具体 BPMN 元素和 DSL 节点
- 支持批量 case 验证
- 支持从“元素存在性”“类型一致性”“关键字段一致性”“flow 推进关系”四个层次做检查

## 目录结构

```text
Experiment/new/exp1_mapping/
├── cases/                  # case 清单
├── outputs/
│   ├── regenerated/        # 当前 newTranslator 现生成的 .b2c
│   ├── parsed/             # BPMN / B2C 统一 JSON
│   ├── reports/            # 单 case mapping_report.json / .md
│   └── summaries/          # summary.csv / summary.md / 失败分析
├── scripts/
│   ├── common.py
│   ├── parse_bpmn_to_json.py
│   ├── parse_b2c_to_json.py
│   ├── verify_bpmn_to_dsl.py
│   └── run_exp1_batch.py
└── tests/
```

## 实验流程

一轮完整实验的执行逻辑如下：

1. 从 `cases/` 中读取 case 清单
2. 对每个 BPMN 调用当前 `newTranslator`，生成新的 `.b2c`
3. 解析 BPMN，抽取统一结构 JSON
4. 解析 B2CDSL，抽取统一结构 JSON
5. 基于映射契约逐项校验
6. 输出单 case 报告与批量汇总表

这意味着当前实验结果默认反映的是：

- 当前仓库中的 BPMN / DMN 输入
- 当前版本的 `newTranslator`
- 当前重新生成的 `.b2c`

而不是历史运行目录中遗留的旧 DSL 文件。

## 运行方式

### 批量运行

```bash
/root/code/ChainCollab/src/newTranslator/.venv/bin/python \
  /root/code/ChainCollab/Experiment/new/exp1_mapping/scripts/run_exp1_batch.py
```

### 自检

```bash
/root/code/ChainCollab/src/newTranslator/.venv/bin/python \
  /root/code/ChainCollab/Experiment/new/exp1_mapping/tests/test_exp1_smoke.py
```

## 脚本说明

- `scripts/run_exp1_batch.py`
  - 批量入口
  - 负责扫描 case、调用 `newTranslator` 生成 `.b2c`、执行解析和校验、写出汇总结果

- `scripts/parse_bpmn_to_json.py`
  - 将 BPMN/DMN 抽取为统一 JSON
  - 便于做结构化比较，而不是字符串对比

- `scripts/parse_b2c_to_json.py`
  - 将 `.b2c` 抽取为统一 JSON
  - 特别会解析 `flows`，把 trigger 和 actions 拆出来

- `scripts/verify_bpmn_to_dsl.py`
  - 执行映射契约
  - 计算指标
  - 输出 `mapping_report.json` 和 `mapping_report.md`

- `scripts/common.py`
  - 放公共逻辑
  - 包括 BPMN/DMN/B2C 解析、名称标准化、flow 结构化、报告生成、调用 `newTranslator` 生成 DSL

## 输出说明

- `outputs/regenerated/*.generated.b2c`
  - 当前 `newTranslator` 重新生成的 DSL
- `outputs/parsed/*.bpmn.json`
  - BPMN 统一解析结果
- `outputs/parsed/*.b2c.json`
  - B2CDSL 统一解析结果
- `outputs/reports/*.mapping_report.json`
  - 单案例结构化验证报告
- `outputs/reports/*.mapping_report.md`
  - 单案例可读报告
- `outputs/summaries/summary.csv`
  - 批量汇总表
- `outputs/summaries/summary.md`
  - Markdown 汇总表
- `outputs/summaries/failed_case_analysis.md`
  - 当前失败案例分析

## 指标说明

实验报告中使用 3 个核心指标：

- `Element Preservation Rate`
  - 表示 BPMN/DMN 中的关键元素，有多少能在 DSL 中找到对应表示

- `Mapping Accuracy`
  - 表示已经找到对应元素之后，其中有多少在类型和关键语义字段上仍然正确

- `Contract Satisfaction Rate`
  - 表示全部映射契约中，有多少项最终通过

通常可以这样理解：

- `Element Preservation Rate` 低：说明元素本身就丢了
- `Mapping Accuracy` 低：说明元素虽然还在，但语义不完整或字段不一致
- `Contract Satisfaction Rate` 低：说明整体映射质量仍有明显缺口

## 当前实验状态

当前已完成 `30` 个样本的批量验证。

- 通过：`28`
- 失败：`2`

失败案例目前为：

- `Coffee_machine`
- `Purchase`

失败分析见：

- [failed_case_analysis.md](/root/code/ChainCollab/Experiment/new/exp1_mapping/outputs/summaries/failed_case_analysis.md)

汇总结果见：

- [summary.csv](/root/code/ChainCollab/Experiment/new/exp1_mapping/outputs/summaries/summary.csv)
- [summary.md](/root/code/ChainCollab/Experiment/new/exp1_mapping/outputs/summaries/summary.md)

从当前结果看：

- 大多数样本已经能达到 `100%` Contract Satisfaction
- 剩余失败案例集中在两个边界问题：
  - `Coffee_machine`：BusinessRule input/output mapping 缺失
  - `Purchase`：某条 message 的 flow 推进规则缺失

这说明当前 `newTranslator` 在主体映射上已经较稳定，但在少量业务规则参数映射和个别 flow 生成上仍有边界缺口。

## 依赖与复用

本实验复用了仓库中已有的核心能力：

- BPMN 解析：
  [parser.py](/root/code/ChainCollab/src/newTranslator/generator/parser/choreography_parser/parser.py)
- DMN 解析：
  [parser.py](/root/code/ChainCollab/src/newTranslator/generator/parser/dmn_parser/parser.py)
- DSL 语法：
  [b2c.tx](/root/code/ChainCollab/src/newTranslator/DSL/B2CDSL/b2cdsl/b2c.tx)
- BPMN -> B2C 生成入口：
  [bpmn_to_dsl.py](/root/code/ChainCollab/src/newTranslator/generator/bpmn_to_dsl.py)

## 设计原则

这个实验项目在设计上有几个明确原则：

- 只做验证，不改生成器逻辑
- 尽量复用仓库原有解析与生成能力
- 不把验证建立在历史产物上，而是建立在“当前输入 + 当前生成器 + 当前输出”上
- 报告必须可定位，不能只给出笼统的“失败”
- 比对尽量做语义对齐，而不是全文字符串强匹配

## 适用场景

这个实验项目适合用于：

- 论文中的“映射正确性验证”实验
- 回归检查 `newTranslator` 的模型转换稳定性
- 快速定位 BPMN 元素在 DSL 中的缺失或语义不一致问题

## 当前限制

- 某些 BPMN `businessRuleTask` 的 documentation 只提供 `inputs/outputs`，不一定显式提供 `dmn/decision`
- 对这类 case，验证器会优先检查 DSL 中是否存在 `businessrule`、是否存在 input/output mapping，以及是否有相关 flow 规则
- 个别 BPMN 文件结构比较特殊时，BPMN 解析会依赖仓库现有解析器的行为；实验工具尽量兼容，但不会改写 `newTranslator` 核心实现
