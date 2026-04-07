# 第X章 Relayer跨链实验设计与结果分析

## 1. 实验目标

本章验证两个核心问题：

1. BPMN 流程拆分并跨链部署后，执行语义是否保持正确。  
2. 相比 Full 全链上执行，Split 跨链执行在 Gas 与 E2E 延迟上引入了多少额外代价。  

---

## 2. 实验设置

- 实验目录：`/home/logres/system/Experiment/Current/Relayer`
- 区块链环境：双链本地 EVM（Anvil）
  - 源链 `chainA`：`31337`
  - 目标链 `chainB`：`31338`
- 数据集：`relayer_split_user3_points_v1`，共 3 个 BPMN 案例
- 每场景实验次数：10（统一）
- 执行口径：
  - **Full**：对每个 BPMN，先经 Translator 生成 full 合约，再按函数可执行顺序逐步推进执行
  - **Split**：对同一 BPMN 按 split-mode 生成子合约，源链执行到分界点后由 Relayer 推进目标链子流程，再回到后续流程
- 运行参数：`RELAYER_INLINE=1`、`RELAYER_USE_BATCH=0`、`ANVIL_BLOCK_TIME=0`、`RELAYER_LATENCY_BASELINE_MS=20000`
- 拆分规则：按“拆分点 -> 聚合点”的闭区间摘取子流程（split-mode 中使用 `splitPointIds` 与 `mergePointId`）。

---

## 3. 正确性与开销实验（按场景）

### 3.1 实验结果

| 场景 | 成功率 | Full平均Gas（gas） | Split平均Gas（gas） | 跨链附加开销（gas） | 总成本变化（gas） | 总成本变化比例 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 单车租赁 | 100.00% | 1,434,903.60 | 2,365,191.00 | 460,984.20 | 930,287.40 | 64.83% |
| 酒店预订 | 100.00% | 986,260.60 | 1,516,458.30 | 460,943.10 | 530,197.70 | 53.76% |
| 客户服务 | 100.00% | 1,131,809.80 | 1,512,918.30 | 460,922.10 | 381,108.50 | 33.67% |

### 3.2 结果分析

1. 三个场景成功率均为 100%，说明闭区间拆分后流程仍可稳定完成。  
2. `Full平均Gas` 与 `Split平均Gas` 在三个场景均表现为 Split 高于 Full，未出现“拆分后反而更省”的反直觉结果。  
3. `跨链附加开销` 均约为 46 万 gas，体现出 Relayer handoff 的结构性固定代价。  
4. `总成本变化比例` 在 `+33.67% ~ +64.83%`，说明在闭区间拆分场景下，跨链协同引入了可量化且稳定的额外链上成本。  

---

## 4. Latency 实验（按场景）

### 4.1 实验结果

| 场景 | Full E2E均值（s, wall-clock） | Split E2E均值（s, wall-clock） | 延迟开销比例 |
| --- | ---: | ---: | ---: |
| 单车租赁 | 20.322 | 22.926 | 12.81% |
| 酒店预订 | 20.282 | 21.638 | 6.69% |
| 客户服务 | 20.150 | 21.649 | 7.44% |

### 4.2 结果分析

1. 在统一业务基线时延（20s）口径下，三个场景的 Full 端到端均值均为 20s+，Split 在此基础上小幅增加。  
2. Split 的延迟开销比例为 `6.69% ~ 12.81%`，体现了“可接受的小幅时延代价”。  
3. 该结果与开销结果一致：Relayer 方案在保证可用性的同时，以可控延迟和固定附加 Gas 实现跨链流程衔接。  

---

## 5. 复现实验

```bash
cd /home/logres/system/Experiment/Current/Relayer
npm install
npm run experiment:relayer:full
```

导出产物：

- `deployments/RELAYER_UNIFIED_EXPERIMENT_REPORT.md`
- `deployments/relayer-unified-report.json`
- `deployments/CORRECTNESS_SPLIT_LATENCY_REPORT.md`
- `deployments/LATENCY_FULL_VS_SPLIT_REPORT.md`
