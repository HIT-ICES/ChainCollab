# 工业数据采集聚合实验报告

生成时间：2026-03-03T14:12:17.252Z

## 实验设置（简述）

- 本实验为仿真实验，采用公开数据集并模拟多节点观测。
- 数据集数量：2；聚合方法：MEAN / MEDIAN / WEIGHTED_MEAN / TRIMMED_MEAN。
- 场景：轻微扰动场景、单点异常场景、缺失数据场景。
- 核心表按场景展示（跨数据集平均），不再在表中区分数据集。

## 数据集介绍

| 数据集 | 指标列 | 链接 |
| --- | --- | --- |
| Room Occupancy Estimation | Temp | https://archive.ics.uci.edu/dataset/864/room+occupancy+estimation |
| Room Occupancy Estimation | Light | https://archive.ics.uci.edu/dataset/864/room+occupancy+estimation |

## 核心结果（单表）

| 聚合方法 | 轻微扰动场景-MAPE | 轻微扰动场景-Cost(gas) | 单点异常场景-MAPE | 单点异常场景-Cost(gas) | 缺失数据场景-MAPE | 缺失数据场景-Cost(gas) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| MEAN | 0.10% | 848,193.172 | 10.61% | 848,097.467 | 5.53% | 821,055.706 |
| MEDIAN | 0.09% | 870,395.111 | 0.40% | 870,716.744 | 0.38% | 843,327.061 |
| WEIGHTED_MEAN | 0.10% | 974,039.3 | 10.61% | 974,132.389 | 5.53% | 945,992.856 |
| TRIMMED_MEAN | 0.09% | 871,151.672 | 0.40% | 871,452.706 | 0.36% | 844,198.067 |

## 结果分析

1. 总体上，精度最佳为 TRIMMED_MEAN（平均 MAPE 0.28%），成本最低为 MEAN（平均 Cost 839,115.448 gas）。
2. 在“轻微扰动场景”中，MEDIAN 为精度最佳，更适合较干净数据。
3. 在“单点异常/缺失数据场景”中，MEDIAN 更适合问题数据。
4. 结论可直接用于方法选择：先看数据质量，再在精度与链上成本之间做折中。

## 说明

- MAPE 越低越好；Cost(gas) 越低越好。
- “异构权重”仅作 Gas 测算，不纳入本表精度对比。

## 复现实验命令

```bash
cd /home/logres/system/Experiment/Current/Oracle
npm run experiment:data-industrial-report
```
