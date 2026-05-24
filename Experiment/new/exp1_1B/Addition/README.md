# 实验 1B 附加验证：实验三 logical_path 结构可追踪性

本目录只保存实验 1B 的附加验证实现与结果。该附加验证对应 `实验 1B：BPMN→DSL 源目标结构一致性验证详细实验方案.md` 中的“第二部分：附加验证：实验三 logical_path 结构可追踪性检查”。

## 1. 验证目的

检查实验三中使用的每个 `logical_path.json` 的每个执行 step，是否都能追溯到 BPMN 源模型结构。

该检查只验证结构来源：

```text
logical_path step.element
  -> 是否存在于 DSL-TAG
  -> 是否能通过 bpmn_dsl_trace.json 追溯到 BPMN 来源
```

该检查不验证：

```text
1. 路径是否可执行；
2. guard 条件是否运行正确；
3. 状态迁移结果是否正确；
4. Fabric / Geth 平台运行结果是否一致。
```

## 2. 输入来源

本附加实验只读取以下目录，不修改它们：

```text
实验三 logical_path：
/root/code/ChainCollab/Experiment/new/exp3/cases

实验 1B 主体结构结果：
/root/code/ChainCollab/Experiment/new/exp1_1B/cases
```

每个 case 使用三个输入：

```text
exp3/cases/<CaseName>/paths/*/logical_path.json
exp1_1B/cases/<CaseName>/dsl/dsl_tag.json
exp1_1B/cases/<CaseName>/trace/bpmn_dsl_trace.json
```

## 3. 脚本说明

### 3.1 `scripts/check_exp3_path_traceability.py`

单 case 附加验证脚本。

功能：

```text
1. 读取某个 case 的所有 logical_path.json；
2. 按优先级从 step 中提取 DSL 元素 id：
   step.trigger.element
   step.element
   step.activity_id
   step.id
   step.target
3. 检查该元素是否存在于 dsl_tag.nodes；
4. 检查该元素是否出现在 bpmn_dsl_trace.json 的追溯关系中；
5. 输出该 case 的 path_traceability_report.json 和 path_traceability_summary.md。
```

### 3.2 `scripts/run_all_addition_cases.py`

批量附加验证脚本。

功能：

```text
1. 遍历 exp3/cases 下所有 case；
2. 对每个 case 调用 check_exp3_path_traceability.py；
3. 汇总所有 case 的路径可追踪率；
4. 输出 addition_batch_summary.json 和 addition_batch_summary.md。
```

运行命令：

```bash
python3 /root/code/ChainCollab/Experiment/new/exp1_1B/Addition/scripts/run_all_addition_cases.py
```

## 4. 输出目录

输出全部位于：

```text
/root/code/ChainCollab/Experiment/new/exp1_1B/Addition/cases
```

批量汇总：

```text
cases/addition_batch_summary.json
cases/addition_batch_summary.md
```

单 case 输出：

```text
cases/<CaseName>/path_traceability_report.json
cases/<CaseName>/path_traceability_summary.md
```

## 5. 当前运行结果

已执行：

```bash
python3 /root/code/ChainCollab/Experiment/new/exp1_1B/Addition/scripts/run_all_addition_cases.py
```

批量结果：

```text
total_cases: 11
passed: 11
failed: 0
errored: 0
logical_paths: 75
logical_path_steps: 1100
traceable_logical_path_steps: 1100
untraceable_logical_path_steps: 0
overall_path_traceability: 1.0000
```

结论：

```text
Exp3PathTraceability = PASS
```

说明实验三当前使用的 75 条 logical_path 中，所有 1100 个执行 step 都能在 DSL-TAG 中找到对应元素，并能通过 `bpmn_dsl_trace.json` 追溯到 BPMN 源模型结构。

## 6. 与实验 1B 主体的关系

本目录内容是实验 1B 的附加验证，不改变 1B 主体 C1-C5 结构一致性结果。

关系如下：

```text
1B 主体验证：
  BPMN-TAG + DSL-TAG + mapping_contract
  -> bpmn_dsl_trace.json
  -> C1-C5 结构一致性报告

1B 附加验证：
  bpmn_dsl_trace.json + dsl_tag.json + exp3 logical_path.json
  -> path_traceability_report.json
  -> 判断实验三路径步骤是否具有 BPMN 来源
```

因此，本附加验证证明的是：

```text
实验三使用的 logical_path 不是 DSL-only 路径；
其中每个执行步骤都具有 BPMN 源模型结构依据。
```
