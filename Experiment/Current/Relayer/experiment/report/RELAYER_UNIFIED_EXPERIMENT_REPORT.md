# Relayer 实验报告（正确性与开销/延迟）

生成时间：2026-03-22T19:39:23.148Z

## 1. 实验设置

- 配置文件：`/home/logres/system/Experiment/Current/Relayer/experiment/dataset/relayer_experiment_dataset.json`
- 数据集名称：`relayer_split_industrial_cases_v3_cn10`
- BPMN 案例数：10
- 每场景实验次数：1（统一）
- 源链：chainA (31337)
- 目标链：chainB (31338)
- 执行口径：Full 与 Split 均采用“逐函数推进”执行（不是单笔占位交易）。
- 说明：部分场景在流程结构上存在重合，用于验证 Relayer 机制在相近流程模板下的稳定性。

| 场景（中文） | 场景标识 | BPMN路径 |
| --- | --- | --- |
| 酒店预订 | Hotel_Booking | /home/logres/system/Experiment/CaseTest/Hotel Booking.bpmn |
| 客户服务 | customer_new | /home/logres/system/Experiment/BPMNwithDMNexample/customer_new.bpmn |
| 供应链 | SupplyChain | /home/logres/system/Experiment/CaseTest/SupplyChain.bpmn |
| 血液检测 | Blood_analysis | /home/logres/system/Experiment/CaseTest/Blood_analysis.bpmn |
| Amazon 服务级别协议 | amazon_new2 | /home/logres/system/Experiment/BPMNwithDMNcase/amazon_new2.bpmn |
| 披萨订购 | PizzaOrder | /home/logres/system/Experiment/CaseTest/PizzaOrder.bpmn |
| 租赁理赔 | Rental_Claim | /home/logres/system/Experiment/CaseTest/Rental Claim.bpmn |
| 采购 | Purchase | /home/logres/system/Experiment/CaseTest/Purchase.bpmn |
| 制造业 | Manufactory | /home/logres/system/Experiment/CaseTest/Manufactory.bpmn |
| 管理系统 | ManagementSystem | /home/logres/system/Experiment/CaseTest/ManagementSystem.bpmn |

## 2. 正确性与开销实验结果

| 场景 | 成功率 | Full平均Gas（gas） | Split平均Gas（gas） | 跨链附加开销（gas） | 总成本变化（gas） | 总成本变化比例 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 酒店预订 | 100.00% | 983719.00 | 1827767.00 | 619523.00 | 844048.00 | 85.80% |
| 客户服务 | 100.00% | 1422273.00 | 2253838.00 | 619589.00 | 831565.00 | 58.47% |
| 供应链 | 100.00% | 1157609.00 | 1834041.00 | 619562.00 | 676432.00 | 58.43% |
| 血液检测 | 100.00% | 657537.00 | 1401660.00 | 619511.00 | 744123.00 | 113.17% |
| Amazon 服务级别协议 | 100.00% | 913705.00 | 1903959.00 | 619506.00 | 990254.00 | 108.38% |
| 披萨订购 | 100.00% | 902687.00 | 1542721.00 | 619470.00 | 640034.00 | 70.90% |
| 租赁理赔 | 100.00% | 959319.00 | 1830948.00 | 619523.00 | 871629.00 | 90.86% |
| 采购 | 100.00% | 949522.00 | 1691095.00 | 619501.00 | 741573.00 | 78.10% |
| 制造业 | 100.00% | 802451.00 | 1467703.00 | 619499.00 | 665252.00 | 82.90% |
| 管理系统 | 100.00% | 815502.00 | 1542985.00 | 619550.00 | 727483.00 | 89.21% |

## 3. Latency 实验结果（按场景）

| 场景 | Full E2E均值（s, wall-clock） | Split E2E均值（s, wall-clock） | 延迟开销比例 |
| --- | ---: | ---: | ---: |
| 酒店预订 | 6.023 | 48.363 | 702.96% |
| 客户服务 | 6.060 | 69.270 | 1042.98% |
| 供应链 | 2.848 | 50.852 | 1685.51% |
| 血液检测 | 6.326 | 33.040 | 422.26% |
| Amazon 服务级别协议 | 3.238 | 53.911 | 1565.16% |
| 披萨订购 | 2.836 | 38.912 | 1272.08% |
| 租赁理赔 | 6.325 | 51.212 | 709.73% |
| 采购 | 3.220 | 44.759 | 1290.10% |
| 制造业 | 2.873 | 36.180 | 1159.12% |
| 管理系统 | 9.146 | 38.830 | 324.55% |

## 4. 一键复现实验与导出

```bash
cd /home/logres/system/Experiment/Current/Relayer
npm install
npm run experiment:relayer:full
```

产物：
- `experiment/report/RELAYER_UNIFIED_EXPERIMENT_REPORT.md`
- `experiment/report/relayer-unified-report.json`
- `experiment/report/LATENCY_FULL_VS_SPLIT_REPORT.md`
- `experiment/report/latency-full-vs-split-report.json`
- `experiment/report/CORRECTNESS_SPLIT_LATENCY_REPORT.md`
