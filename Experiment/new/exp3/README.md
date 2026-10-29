# Exp3: 多平台代码行为一致性实验

## 目录导航

实验三现在已经落地为一条三方执行与对比流水线：

- 整体流程图：
  [实验整体流程图.md](/root/code/ChainCollab/Experiment/new/exp3/实验整体流程图.md)
- 学习文档：
  [426学习文档.md](/root/code/ChainCollab/Experiment/new/exp3/426学习文档.md)
- DSL：
  [dsl/README.md](/root/code/ChainCollab/Experiment/new/exp3/dsl/README.md)
- Solidity：
  [solidity/README.md](/root/code/ChainCollab/Experiment/new/exp3/solidity/README.md)
- Fabric：
  [fabric/README.md](/root/code/ChainCollab/Experiment/new/exp3/fabric/README.md)
- 平台无关路径输入：
  [cases/](/root/code/ChainCollab/Experiment/new/exp3/cases)

推荐按下面这个心智模型找文件：

- 看统一路径输入：进 `cases/<CaseName>/paths/<PathName>/logical_path.json`
- 看 DSL 参考语义和模拟执行：进 `dsl/`
- 看 Ethereum / FireFly / Solidity 自动执行：进 `solidity/`
- 看 Fabric / FireFly 自动执行：进 `fabric/`
- 看归一化结果和三方对比报告：进 `outputs/`
- 看自动化脚本：进 `scripts/`

当前目录结构可理解为：

```text
exp3/
  cases/      # 平台无关路径
  dsl/        # DSL 输入与模拟执行产物
  solidity/   # Solidity replay 配置和原始产物
  fabric/     # Fabric replay 配置、原始产物和 batch 汇总
  outputs/    # normalized trace 和三方对比报告
  scripts/    # 路径生成、执行、归一化、对比脚本
```

## 实验目标

本实验用于验证：同一个业务流程、同一条平台无关执行路径，在三条执行线中是否表现出一致的流程推进行为。

三条执行线是：

- DSL 参考语义模拟执行
- Geth / Solidity / FireFly 自动执行
- Fabric / FireFly 自动执行

因此，本实验关注的不是“代码结构里有没有对应元素”，而是：

1. DSL 参考语义在该路径下如何推进。
2. Solidity 真实执行是否遵守这份参考语义。
3. Fabric 真实执行是否遵守这份参考语义。
4. Solidity 与 Fabric 彼此是否表现一致。

实验结论来自三组对比：

```text
DSL vs Solidity
DSL vs Fabric
Solidity vs Fabric
```

## 总体流程

完整链路是：

```text
DSL/B2C 模型
  -> 生成或维护平台无关 logical_path.json
  -> DSL 模拟执行
  -> Solidity 自动执行
  -> Fabric 自动执行
  -> 三方原始轨迹分别归一化
  -> 生成三组 normalized trace 对比报告
```

`logical_path.json` 是整个实验的统一路径源。不同平台可以有自己的执行输入格式，但都必须从同一条 logical path 派生或读取。

## 关键脚本

```text
scripts/generate_dsl_paths.py
  基于 DSL 模拟器语义做有界可执行路径枚举。

scripts/materialize_logical_path.py
  把 logical_path.json 派生成 DSL case.json 和 Solidity execution_sequence.json；Fabric 直接复用 logical_path.json。

scripts/run_exp3.py
  运行 DSL 模拟器，生成 dsl_trace.json 和 dsl_model.json。

scripts/run_case_pipeline.py
  DSL + Solidity 一键管线：路径生成、materialize、DSL 执行、Solidity replay、归一化、DSL vs Solidity 对比。

scripts/replay_bound_eth_instance.py
  Solidity/Geth/FireFly 自动执行脚本。

scripts/replay_fabric_instance.py
  Fabric/FireFly 单条路径自动执行脚本。

scripts/run_fabric_case_paths.py
  Fabric 批量入口：读取某个案例 paths 目录下所有 logical_path.json，逐条调用 replay_fabric_instance.py。

scripts/normalize_traces.py
  DSL 与 Solidity replay 归一化脚本。

scripts/compare_normalized_traces.py
  normalized trace 两两对比脚本，当前用于 DSL vs Solidity。

scripts/compare_fabric_replay.py
  Fabric replay 归一化，并自动生成 DSL vs Fabric、Solidity vs Fabric 两组对比。
```

## 关键输入与输出

每个案例的路径输入位于：

```text
cases/<CaseName>/paths/<PathName>/logical_path.json
```

DSL 产物位于：

```text
dsl/<CaseName>/paths/<PathName>/case.json
dsl/<CaseName>/paths/<PathName>/dsl_model.json
dsl/<CaseName>/paths/<PathName>/dsl_trace.json
```

Solidity 产物位于：

```text
solidity/<CaseName>/paths/<PathName>/execution_sequence.json
solidity/<CaseName>/paths/<PathName>/replays/replay_*.json
```

Fabric 产物位于：

```text
fabric/<CaseName>/paths/<PathName>/replays/replay_*.json
fabric/<CaseName>/batch/fabric_batch_<timestamp>.json
fabric/<CaseName>/batch/fabric_batch_<timestamp>.md
```

三方归一化和对比产物位于：

```text
outputs/<CaseName>/paths/<PathName>/normalized/dsl.normalized.json
outputs/<CaseName>/paths/<PathName>/normalized/solidity.normalized.json
outputs/<CaseName>/paths/<PathName>/normalized/fabric.normalized.json

outputs/<CaseName>/paths/<PathName>/comparison.json
outputs/<CaseName>/paths/<PathName>/comparison.md
outputs/<CaseName>/paths/<PathName>/comparison.dsl_fabric.json
outputs/<CaseName>/paths/<PathName>/comparison.dsl_fabric.md
outputs/<CaseName>/paths/<PathName>/comparison.solidity_fabric.json
outputs/<CaseName>/paths/<PathName>/comparison.solidity_fabric.md
```

其中：

- `comparison.json/md`：DSL vs Solidity。
- `comparison.dsl_fabric.json/md`：DSL vs Fabric。
- `comparison.solidity_fabric.json/md`：Solidity vs Fabric。

## 一键命令

先跑 DSL + Solidity 管线：

```bash
cd /root/code/ChainCollab
/root/code/ChainCollab/src/newTranslator/.venv/bin/python \
  /root/code/ChainCollab/Experiment/new/exp3/scripts/run_case_pipeline.py \
  --case-name SupplyChainPaper \
  --model /root/code/ChainCollab/Experiment/new/exp2_semantic_verification/results/cases/SupplyChainPaper/dsl.b2c \
  --solidity-config /root/code/ChainCollab/Experiment/new/exp3/solidity/SupplyChainPaper/replay_bound_eth_instance.template.json
```

再跑 Fabric 批量回放，并自动补齐 Fabric normalized 和两组 Fabric 对比：

```bash
cd /root/code/ChainCollab/Experiment/new/exp3
python3 scripts/run_fabric_case_paths.py \
  --config fabric/fabric_replay_config.from_frontend_param.json \
  --paths-dir cases/SupplyChainPaper/paths
```

换案例时，Fabric 命令只需要替换 `--paths-dir`：

```bash
python3 scripts/run_fabric_case_paths.py \
  --config fabric/fabric_replay_config.from_frontend_param.json \
  --paths-dir cases/<CaseName>/paths
```

## 判定指标

路径级判断：

- 三组 comparison 是否都存在。
- 三组 comparison 是否都 `consistent = true`。
- 三方最终 `final_state.status` 是否一致。

步级判断：

- `trigger` 是否一致。
- `enabled_before` 是否一致。
- `accepted` 是否一致。
- `state_diff` 是否一致。
- `final_state.element_states` 是否一致。
- `final_state.enabled_elements` 是否一致。

如果三组比较都一致，可以认为该路径在当前归一化口径下通过三方行为一致性检查。

## 与 exp2 的分工

`exp2_semantic_verification` 关注静态语义覆盖：

- DSL 元素是否在生成代码中有对应结构。
- flow 控制语义是否能在代码中找到证据。

`exp3` 关注动态行为一致性：

- 同一条路径在 DSL、Solidity、Fabric 中是否产生一致轨迹。
- 真实平台执行结果是否与 DSL 参考语义对齐。
- 两个链平台之间是否对齐。

可以在论文或报告中形成如下逻辑：

1. `exp2` 证明代码生成结果在结构和控制逻辑上覆盖了 DSL。
2. `exp3` 进一步证明这些结构在有界执行路径上表现一致。

## 当前实验边界

当前实验已经完成 Fabric 自动执行和三方对比接入，但结论仍应按有界实验表达：

- 路径生成是有界枚举，不是无限路径证明。
- 当前主要验证已生成/已选择路径上的行为一致性。
- 循环、复杂表达式分支和大规模性能对比不属于当前核心结论。
- 不建议直接宣称“完全行为等价”，更准确的说法是“在当前有界路径集合和归一化口径下保持一致”。
