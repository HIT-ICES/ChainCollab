# Oracle 数据任务调研与实验方案（工业互联网场景）

## 1. 目标与范围

本方案聚焦 Oracle 的**数据采集任务合约**及其链下节点协同实验，覆盖两类实验：

1. **微小差异数据聚合效果实验**  
   多个链下节点读取“同一真实量”的近似观测，比较聚合方法的精度和链上成本。
2. **恶意节点鲁棒性实验**  
   在部分节点上传恶意数据时，比较聚合方法的抗攻击能力与代价。

### 1.1 当前计算任务实验的数据集边界（已落地）

为保证实验叙事一致性，当前 `compute_tasks_10_scenarios.json` 已统一约束为工业互联网/CPS相关来源，不再混入通用市场型案例。当前仅使用以下 6 类来源：

1. UCI Steel Industry Energy Consumption
2. UCI SECOM
3. SWaT
4. WADI
5. BATADAL
6. NASA C-MAPSS

---

## 2. 数据集调研（含文献背景）

## 2.1 工业控制/IIoT 网络采集场景（推荐）

### A. SWaT / WaDi（iTrust）
- 机构页（含数据说明与引用信息）：  
  https://itrust.sutd.edu.sg/itrust-labs_datasets/dataset_info/
- 背景：
  - SWaT: 水处理 CPS 高保真测试床，含正常与攻击运行数据。
  - WaDi: 城市级配水场景缩比测试床，含多传感器与攻击场景。
- 论文：
  - SWaT: Mathur & Tippenhauer, 2016（CySWATER）
  - WaDi: Ahmed et al., 2017（CySWATER）
- 备注：需按 iTrust 规则申请，不可二次分发。

### B. BATADAL（水务 SCADA 攻击检测竞赛数据）
- 官方数据页：  
  https://www.batadal.net/data.html
- 论文（竞赛综述，明确引用）：  
  DOI: https://doi.org/10.1061/(ASCE)WR.1943-5452.0000969
- 特点：
  - 提供正常、部分标注攻击、测试集（无标注）；
  - 适合做“多节点对同一量观测并聚合”的离线回放实验。

### C. TON_IoT（IIoT+IoT 异构遥测/网络/系统日志）
- 官方项目页：  
  https://research.unsw.edu.au/projects/toniot-datasets
- 遥测数据论文入口（含摘要）：  
  https://opal.latrobe.edu.au/articles/journal_contribution/TON_IoT_telemetry_dataset_a_new_generation_dataset_of_IoT_and_IIoT_for_data-driven_Intrusion_Detection_Systems/13239347
- 特点：
  - 含 IoT/IIoT 传感器遥测 + 网络流量 + OS 日志；
  - 适合“网络采集节点”实验以及恶意数据注入模拟。

## 2.2 外部数据场景（推荐）

### D. 钢铁行业能耗（UCI Steel Industry Energy Consumption）
- 数据页：  
  https://archive.ics.uci.edu/dataset/851
- 说明：
  - 韩国钢铁企业实际能耗数据（云端记录），工业背景强；
  - 可作为“外部业务数据源”用于链下节点抓取与聚合。

### E. 联合循环电站（UCI Combined Cycle Power Plant）
- 数据页：  
  https://archive.ics.uci.edu/dataset/294/com-
- 原始论文信息（数据页内给出）：
  - Tüfekci, 2014, Int. J. Electrical Power & Energy Systems
- 说明：
  - 环境变量（温度/湿度/压力/真空）与发电输出关系明确；
  - 适合构造“多数据源同指标聚合”与“偏差注入”实验。

### F. 实时外部 API（可选）
- EIA Open Data（电力、负荷、发电等）：  
  https://www.eia.gov/opendata/
- EIA API 技术文档：  
  https://www.eia.gov/opendata/documentation.php
- Open-Meteo 历史/实时气象 API：  
  https://open-meteo.com/en/docs/historical-weather-api
- 说明：可用于“在线采集 + Oracle 上链”端到端验证。

---

## 3. 聚合方法与文献支撑

建议首批 `m=4` 种聚合方法：

1. `MEAN`
2. `MEDIAN`
3. `TRIMMED_MEAN`（去极值比例可调，如 10%/20%）
4. `WEIGHTED_MEAN`（节点权重按历史信誉或源质量）

鲁棒性理论与实证支撑（重点）：
- Yin et al., ICML 2018（Byzantine-robust，median/trimmed mean）：  
  https://proceedings.mlr.press/v80/yin18a

工程侧多源聚合背书（Oracle 网络）：
- Chainlink Data Feeds（多源、多节点、聚合流程）：  
  https://chain.link/data-feeds
- Chainlink FAQ（OCR/off-chain aggregation 概念）：  
  https://chain.link/faqs

---

## 4. 实验设计（n*m）

## 4.1 实验矩阵

建议 `n=4` 场景、`m=4` 方法，共 `16` 组基础实验：

- `S1`: SWaT/WaDi（过程传感）
- `S2`: BATADAL（SCADA 仿真）
- `S3`: TON_IoT（IIoT 遥测/网络）
- `S4`: Steel 或 CCPP（工业外部数据）

每个场景跑 4 种聚合方法（MEAN/MEDIAN/TRIMMED/WEIGHTED）。

## 4.2 实验一：微小差异聚合效果

### 目标
验证当节点数据仅有轻微偏差时，哪种方法精度/成本最优。

### 做法
1. 从场景数据提取标量目标 `y_t`（如流量、液位、负荷、功率）。
2. 构造 `k` 个节点观测：`x_t^i = y_t + e_t^i`，其中 `e_t^i` 为小噪声（高斯/均匀）。
3. 各节点监听 Task 并上报 `x_t^i`。
4. 合约按聚合方法给出 `ŷ_t`。

### 指标
- 精度：MAE、RMSE、MAPE
- 稳定性：标准差、分位数误差
- 成本：request gas、submit gas、finalize gas、total gas

## 4.3 实验二：恶意节点鲁棒性

### 目标
验证存在恶意节点时聚合结果退化程度。

### 攻击注入
- 恶意比例 `p ∈ {10%,20%,30%,40%}`
- 攻击类型：
  1. 偏置攻击：`x'=x+b`
  2. 极值攻击：上报远离真实值的大数
  3. 随机噪声攻击：高方差噪声
  4. 重放攻击：上报滞后旧值

### 指标
- 鲁棒误差增量：`ΔMAE = MAE_attack - MAE_clean`
- 退化倍数：`MAE_attack / MAE_clean`
- 失效点分析：随恶意比例增加的性能拐点
- 成本增量：在同攻击下的 gas 变化

---

## 5. 合约与节点实现建议（面向后续编码）

## 5.1 数据任务合约（建议最小接口）
- `createTask(sourceId, metric, aggMethod, minResponses, deadline)`
- `submitObservation(taskId, value, signature)`
- `finalizeTask(taskId)`
- `getTaskResult(taskId)`
- 可选：
  - `setNodeWeight(node, weight)`
  - `slash(node)`（对恶意节点惩罚）

## 5.2 链下节点职责
- 监听 `TaskCreated`；
- 从数据源读取/回放；
- 按节点配置生成观测值（可注入噪声或恶意行为）；
- 签名并提交；
- 记录本地日志供实验复现实验。

---

## 6. 分阶段落地计划

1. **Phase A（数据接入）**  
   先用 BATADAL + Steel/CCPP 跑通离线回放（无需申请）。
2. **Phase B（合约聚合）**  
   实现 4 种聚合方法 + gas 统计。
3. **Phase C（鲁棒性）**  
   加入 4 类攻击注入与比例扫描。
4. **Phase D（扩展）**  
   接入 SWaT/WaDi（获批后）和实时 API（EIA/Open-Meteo）。

---

## 7. 风险与规避

1. **数据可得性风险（SWaT/WaDi）**：先用 BATADAL/TON_IoT/UCI 落地。
2. **指标不可比**：统一时间对齐、采样窗口、归一化流程。
3. **鲁棒实验偏置**：固定随机种子，攻击脚本版本化。
4. **链上成本抖动**：固定链环境与 gas 配置，多轮取均值。

---

## 8. 结论（可执行建议）

- 你当前最可执行路线：  
  `BATADAL + Steel/CCPP` 先做 `n=2,m=4`，快速得到第一版可发表实验结果；  
  再扩展到 `n=4,m=4`，补强工业互联网与外部数据覆盖面。
- 在恶意节点场景下，`MEDIAN/TRIMMED_MEAN` 通常会比 `MEAN` 更稳健；  
  在低噪声场景下，`MEAN` 仍可能在精度与 gas 上占优（需实验验证）。
