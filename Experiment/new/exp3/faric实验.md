# Fabric 实验说明

这份文档只说明 Fabric 部分的路径来源和最终 `outputs/` 中的结果怎么看。

## 1. 路径从哪里来

Fabric 不单独维护一套路径文件，而是直接复用实验三统一路径：

```text
cases/<CaseName>/paths/<PathName>/logical_path.json
```

这份 `logical_path.json` 是平台无关路径，DSL、Solidity、Fabric 都围绕它执行。区别是：

- DSL 会从它派生 `dsl/<CaseName>/paths/<PathName>/case.json`
- Solidity 会从它派生 `solidity/<CaseName>/paths/<PathName>/execution_sequence.json`
- Fabric 直接把它作为 `--sequence-file` 读取，不再生成 Fabric 专用路径文件

批量跑 Fabric 时使用：

```bash
cd /root/code/ChainCollab/Experiment/new/exp3
python3 scripts/run_fabric_case_paths.py \
  --config fabric/fabric_replay_config.from_frontend_param.json \
  --paths-dir cases/<CaseName>/paths
```

脚本会自动发现：

```text
cases/<CaseName>/paths/*/logical_path.json
```

然后逐条调用 `replay_fabric_instance.py`。

## 2. Fabric 中间产物

Fabric 原始执行结果保存在：

```text
fabric/<CaseName>/paths/<PathName>/replays/replay_<timestamp>.json
fabric/<CaseName>/paths/<PathName>/replays/replay_<timestamp>.md
```

批量汇总保存在：

```text
fabric/<CaseName>/batch/fabric_batch_<timestamp>.json
fabric/<CaseName>/batch/fabric_batch_<timestamp>.md
```

这里的 `replay` 指“按照预定义路径重新触发 Fabric 执行并记录轨迹”，不是读取历史日志做离线回放。

## 3. outputs 中的最终结果

Fabric 跑完后，会把可对比结果写到统一输出目录：

```text
outputs/<CaseName>/paths/<PathName>/
```

关键文件是：

```text
outputs/<CaseName>/paths/<PathName>/normalized/fabric.normalized.json
outputs/<CaseName>/paths/<PathName>/comparison.dsl_fabric.json
outputs/<CaseName>/paths/<PathName>/comparison.dsl_fabric.md
outputs/<CaseName>/paths/<PathName>/comparison.solidity_fabric.json
outputs/<CaseName>/paths/<PathName>/comparison.solidity_fabric.md
```

含义如下：

- `fabric.normalized.json`
  - Fabric 原始 replay 归一化后的标准轨迹
- `comparison.dsl_fabric.*`
  - DSL normalized trace 与 Fabric normalized trace 的对比
- `comparison.solidity_fabric.*`
  - Solidity normalized trace 与 Fabric normalized trace 的对比

第一阶段 `Geth/Solidity vs DSL` 已经生成：

```text
outputs/<CaseName>/paths/<PathName>/comparison.json
outputs/<CaseName>/paths/<PathName>/comparison.md
```

所以判断三方是否一致时，最终看三组报告：

```text
comparison.json                  # DSL vs Solidity
comparison.dsl_fabric.json       # DSL vs Fabric
comparison.solidity_fabric.json  # Solidity vs Fabric
```

如果三组 JSON 里 `consistent` 都是 `true`，说明该路径在当前归一化口径下三方对齐。
