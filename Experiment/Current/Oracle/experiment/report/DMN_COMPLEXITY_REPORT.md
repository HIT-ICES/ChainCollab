# DMN 决策任务链上复杂度实验报告

生成时间：2026-03-03T14:40:06.276Z

案例数：10

| 序号 | 案例 | 模型类型 | 复杂度规模 | 链上Gas | 说明 |
| --- | --- | --- | ---: | ---: | --- |
| 1 | 钢铁产线质量放行 | DecisionTable-FIRST | 20 | 77791 | FIRST hit policy over quality rules (x,y -> release decision) |
| 2 | 钢铁产线质量放行（高规则数） | DecisionTable-FIRST | 60 | 129510 | FIRST hit policy with larger decision table |
| 3 | SWaT 多维告警聚合 | DecisionTable-COLLECT | 30 | 79649 | COLLECT SUM over alarm rules |
| 4 | WADI 漏损告警聚合（高规则数） | DecisionTable-COLLECT | 80 | 163861 | COLLECT SUM with dense rule set |
| 5 | SECOM 评分卡判定 | Scorecard | 16 | 46770 | Scorecard aggregation over 16 indicators |
| 6 | SECOM 评分卡判定（高维） | Scorecard | 48 | 91570 | Scorecard aggregation over 48 indicators |
| 7 | BATADAL 决策图推理 | DecisionGraph | 960 | 487777 | Decision-graph iterative evaluation (8x12x10) |
| 8 | BATADAL 决策图推理（中高复杂） | DecisionGraph | 2800 | 1311865 | Decision-graph iterative evaluation (10x20x14) |
| 9 | C-MAPSS 退化决策图推理 | DecisionGraph | 6048 | 2728373 | Decision-graph iterative evaluation (12x28x18) |
| 10 | C-MAPSS 退化决策图推理（高复杂） | DecisionGraph | 12096 | 5323135 | Decision-graph iterative evaluation (14x36x24) |

## 分模型统计

| 模型 | 平均Gas | 最小Gas | 最大Gas |
| --- | ---: | ---: | ---: |
| DecisionTable-FIRST | 103650.5 | 77791 | 129510 |
| DecisionTable-COLLECT | 121755.0 | 79649 | 163861 |
| Scorecard | 69170.0 | 46770 | 91570 |
| DecisionGraph | 2462787.5 | 487777 | 5323135 |

## 结论

1. 总体平均链上Gas为 1044030.1，其中最高复杂度案例达到 5323135。
2. DecisionGraph 随 node/feature/iteration 增长呈明显高开销，适合作为链下计算候选。
3. FIRST/COLLECT/Scorecard 类 DMN 规则在低维规模下可直接链上执行，在高规则数场景建议采用链下执行+链上确认。
