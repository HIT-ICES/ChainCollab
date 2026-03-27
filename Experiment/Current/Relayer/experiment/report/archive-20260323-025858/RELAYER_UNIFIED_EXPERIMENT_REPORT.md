# Relayer 实验报告（正确性与开销/延迟）

生成时间：2026-03-04T14:03:48.394Z

## 1. 实验设置

- 配置文件：`/home/logres/system/Experiment/Current/Relayer/experiment/dataset/relayer_experiment_dataset.json`
- 数据集名称：`relayer_split_industrial_cases_v3_cn10`
- BPMN 案例数：10
- 每场景实验次数：10（统一）
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
| 单车租赁 | 100.00% | 1434903.60 | 2365191.00 | 460984.20 | 930287.40 | 64.83% |
| 酒店预订 | 100.00% | 986260.60 | 1516458.30 | 460943.10 | 530197.70 | 53.76% |
| 客户服务 | 100.00% | 1131809.80 | 1512918.30 | 460922.10 | 381108.50 | 33.67% |

## 3. Latency 实验结果（按场景）

| 场景 | Full E2E均值（s, wall-clock） | Split E2E均值（s, wall-clock） | 延迟开销比例 |
| --- | ---: | ---: | ---: |
| 单车租赁 | 20.322 | 22.926 | 12.81% |
| 酒店预订 | 20.282 | 21.638 | 6.69% |
| 客户服务 | 20.150 | 21.649 | 7.44% |

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
