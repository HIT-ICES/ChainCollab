# Solidity Track

这一组文件用于实验三中的 Ethereum / Solidity / FireFly 执行回放。

## 入口文件

- 自动化执行脚本：
  [replay_bound_eth_instance.py](/root/code/ChainCollab/Experiment/new/exp3/scripts/replay_bound_eth_instance.py)
- 前端 API 回放说明：
  [FRONTEND_API_REPLAY_GUIDE.md](/root/code/ChainCollab/Experiment/new/exp3/FRONTEND_API_REPLAY_GUIDE.md)

## 输入

- Solidity 执行配置模板：
  [SupplyChainPaper/replay_bound_eth_instance.template.json](/root/code/ChainCollab/Experiment/new/exp3/solidity/SupplyChainPaper/replay_bound_eth_instance.template.json)
- Solidity 路径输入：
  [SupplyChainPaper/paths/paper_very_low_delivery_path/execution_sequence.json](/root/code/ChainCollab/Experiment/new/exp3/solidity/SupplyChainPaper/paths/paper_very_low_delivery_path/execution_sequence.json)

推荐做法：

- 把每个案例的环境、实例、`createInstance` 参数放在 `solidity/<CaseName>/replay_bound_eth_instance*.json`
- 把每条路径的 Solidity 执行序列放在 `solidity/<CaseName>/paths/<PathName>/execution_sequence.json`
- 优先从 `cases/<CaseName>/paths/<PathName>/logical_path.json` 派生 execution sequence，而不是手工维护两份路径

## 当前能力

- 直接复用前端 `createInstance` 参数
- 用单一 signer 调 FireFly 执行
- 支持外部路径文件驱动
- 支持按 DSL 风格顺序逐步等待并执行目标节点

## 这条线当前负责什么

- Ethereum / Solidity / FireFly 自动执行
- 输出链上实例执行报告
- 后续可作为 Solidity 轨迹侧的统一入口
