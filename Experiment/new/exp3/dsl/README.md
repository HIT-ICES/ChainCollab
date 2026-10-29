# DSL Track

这一组文件用于实验三中的 DSL 参考语义与模拟执行。

## 入口文件

- DSL 模拟器：
  [dsl_simulator.py](/root/code/ChainCollab/Experiment/new/exp3/scripts/dsl_simulator.py)
- 实验入口：
  [run_exp3.py](/root/code/ChainCollab/Experiment/new/exp3/scripts/run_exp3.py)
- DSL 解析辅助：
  [parse_b2c.py](/root/code/ChainCollab/Experiment/new/exp3/scripts/parse_b2c.py)

## 输入

- Case 定义：
  [Hotel_Booking case.json](/root/code/ChainCollab/Experiment/new/exp3/cases/Hotel_Booking/case.json)
  [SupplyChain case.json](/root/code/ChainCollab/Experiment/new/exp3/cases/SupplyChain/case.json)

这些 `case.json` 里的 `paths[].steps` 就是后续三条执行线建议共享的路径格式基线。

## 输出

- DSL 执行输出目录：
  [outputs](/root/code/ChainCollab/Experiment/new/exp3/outputs)

当前已经存在：

- `dsl_model.json`
- `dsl_trace_*.json`
- `report.md`
- `summary.json`
- `summary.md`

## 这条线当前负责什么

- 作为参考语义执行器
- 校验给定路径在 DSL 语义下是否可接受
- 产出统一轨迹，供 Fabric / Solidity 对照
