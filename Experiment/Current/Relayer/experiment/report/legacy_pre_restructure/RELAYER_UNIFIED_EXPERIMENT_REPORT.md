# Relayer 实验报告（正确性与开销/延迟）

生成时间：2026-03-04T13:54:51.447Z

## 1. 实验设置

- 配置文件：`/home/logres/system/Experiment/Current/Relayer/experiment/datasets/relayer_experiment_dataset.json`
- 数据集名称：`N/A`
- BPMN 案例数：0
- 每场景实验次数：不统一
- 源链：chainA (31337)
- 目标链：chainB (31338)
- 执行口径：Full 与 Split 均采用“逐函数推进”执行（不是单笔占位交易）。
- 说明：部分场景在流程结构上存在重合，用于验证 Relayer 机制在相近流程模板下的稳定性。

| 场景（中文） | 场景标识 | BPMN路径 |
| --- | --- | --- |
## 4. 一键复现实验与导出

```bash
cd /home/logres/system/Experiment/Current/Relayer
npm install
npm run experiment:relayer:full
```

产物：
- `deployments/RELAYER_UNIFIED_EXPERIMENT_REPORT.md`
- `deployments/relayer-unified-report.json`
- `deployments/LATENCY_FULL_VS_SPLIT_REPORT.md`
- `deployments/latency-full-vs-split-report.json`
- `deployments/CORRECTNESS_SPLIT_LATENCY_REPORT.md`
