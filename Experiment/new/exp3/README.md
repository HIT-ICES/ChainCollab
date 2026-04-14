# Exp3: 多平台代码行为一致性实验

## 实验目标

本实验用于验证：

- 同一份 B2CDSL 生成的 Fabric/Go 版本代码
- 同一份 B2CDSL 生成的 Ethereum/Solidity 版本代码

在相同流程输入下，是否表现出一致的**流程推进行为**。

这里关注的不是“代码结构里有没有对应元素”，而是：

1. DSL 的参考语义是什么。
2. Go 与 Solidity 是否都遵守这份参考语义。
3. Go 与 Solidity 彼此是否表现一致。

因此，这个实验属于**行为一致性实验**，与 `exp2_semantic_fidelity` 的静态结构/控制语义验证形成互补。


## 与 NoiseExperiment 的关系

`NoiseExperiment` 的核心思想是：

- 先准备一条或多条基线路径
- 再生成扰动路径
- 逐条回放到链上实例
- 用状态检查判断路径是否被接受或拒绝

`exp3` 可以复用其中“路径驱动执行 + 状态记录”的基本框架，但实验目的要改成：

- 不再以“扰动路径是否被拒绝”作为核心结论
- 而是以“同一条合法/非法路径在 DSL、Go、Solidity 三方中的行为是否一致”作为核心结论

换句话说：

- `NoiseExperiment` 主要检验单平台流程约束能力
- `exp3` 主要检验跨平台代码行为一致性


## 实验范围

本实验验证三方一致性：

- `DSL vs Go`
- `DSL vs Solidity`
- `Go vs Solidity`

当前建议先做：

- 有界深度路径
- 忽略循环
- 关注流程状态推进与拒绝行为

当前不优先处理：

- 无限路径空间
- 全量循环展开
- 性能/吞吐量比较


## 总体方法

实验分为四个部分。

### 1. DSL 参考语义构造

首先从 DSL 的 `flows` 构造参考状态迁移系统。

状态机的基本元素包括：

- `event`
- `message`
- `gateway`
- `businessrule`
- `oracletask`

需要显式建模的关系包括：

- `enable`
- `disable`
- `choose`
- `parallel join`
- `complete`
- `continue`
- `set global`

参考状态至少包括：

- `INACTIVE`
- `READY`
- `PENDING_CONFIRMATION`
- `DONE`

如果生成器或执行器中还使用其他中间状态，也应在参考语义中补齐。

DSL 参考语义的作用是：

- 给出每一步执行前哪些元素可触发
- 给出每一步执行后元素状态与全局变量如何变化
- 作为 Go/Solidity 的共同对照基线


### 2. 合法路径生成

基于 DSL 参考语义自动生成若干条**代表性执行路径**。

建议至少覆盖以下路径类型：

- 基本顺序路径
- 含 `exclusive gateway` 的不同分支路径
- 含 `parallel gateway` 的分叉/汇聚路径
- 含 `businessrule` 的路径
- 含 `oracletask` 的路径
- 非法输入路径或应被拒绝的路径

当前阶段建议采用：

- 有界深度
- 忽略循环
- 每类结构至少生成 1 到若干条代表路径

可直接复用 `NoiseExperiment` 的经验：

- 先从 basic path 出发
- 再补充手工指定的边界路径
- 但这里的重点不是“随机噪声”，而是“语义代表性路径”


### 3. 双平台执行与轨迹记录

对每条路径，分别执行：

1. DSL 模拟器
2. Fabric/Go 版本
3. Geth/Solidity 版本

每一步都记录统一格式的轨迹信息。

建议最少记录以下字段：

- 当前步骤 ID
- 当前触发元素
- 当前可触发元素集合
- 条件判断结果
- 元素状态变化
- 全局变量变化
- 事件日志 / 回执
- 本步是否接受或拒绝
- 拒绝原因
- 最终状态

这里建议定义统一轨迹模型，例如：

```json
{
  "case_name": "purchase_path_01",
  "platform": "dsl|go|solidity",
  "steps": [
    {
      "index": 0,
      "trigger": "Message_0q9hvem",
      "enabled_before": ["Message_0q9hvem"],
      "guard_result": true,
      "state_diff": {
        "Message_0q9hvem": ["READY", "DONE"],
        "Gateway_1ltys0e": ["INACTIVE", "READY"]
      },
      "global_diff": {
        "priceOK": true
      },
      "accepted": true,
      "logs": []
    }
  ],
  "final_state": {
    "status": "accepted"
  }
}
```


### 4. 三方一致性比较

对每条路径生成三份轨迹后，进行三组比较：

- `DSL vs Go`
- `DSL vs Solidity`
- `Go vs Solidity`

重点比较以下维度：

- `trigger` 是否一致
- `guard` 是否一致
- `state effect` 是否一致
- 后继启用集合是否一致
- `global` 变量更新是否一致
- 终态是否一致
- 非法输入拒绝行为是否一致

如果三方都接受，则比较：

- 每一步的状态变化是否一致

如果三方都拒绝，则比较：

- 拒绝发生的步数是否一致
- 拒绝原因类别是否一致


## 建议的实验输入

建议直接复用 `exp2` 或 `newTranslator` 的 DSL 正例作为实验种子，例如：

- 含基本消息流的 case
- 含 exclusive gateway 的 case
- 含 parallel gateway 的 case
- 含 businessrule 的 case
- 含 oracletask 的 case

对于每个种子，生成：

- 一组合法路径
- 一组应拒绝路径

形成实验输入矩阵。


## 建议的实验输出

建议输出以下结果文件：

```text
exp3/
  README.md
  cases/
    <case>.b2c
  outputs/
    <case_name>/
      paths.json
      dsl_trace_<path>.json
      go_trace_<path>.json
      sol_trace_<path>.json
      compare_<path>.json
      report.md
    summary.json
    summary.md
```

其中：

- `paths.json`
  - 保存该 case 生成的合法/非法路径
- `dsl_trace_*`
  - DSL 模拟器轨迹
- `go_trace_*`
  - Fabric/Go 执行轨迹
- `sol_trace_*`
  - Solidity 执行轨迹
- `compare_*`
  - 单条路径的三方比较结果
- `summary.*`
  - 汇总统计


## 判定指标

建议至少定义以下指标：

### 1. 路径级一致率

- 有多少条路径在三方中结论一致
- 结论包括：
  - 接受
  - 拒绝

### 2. 步级一致率

- 对通过路径，逐步比较状态变化是否一致

### 3. guard 一致率

- 条件分支与并行汇聚中的判断结果是否一致

### 4. 终态一致率

- 最终元素状态与全局变量是否一致

### 5. 拒绝一致率

- 非法路径是否在三方中都被拒绝
- 拒绝步数与拒绝原因类别是否一致


## 与 exp2 的分工

建议将 `exp2` 与 `exp3` 明确区分：

- `exp2_semantic_fidelity`
  - 静态一致性验证
  - 验证 DSL 元素与 flow 控制逻辑是否在代码中有对应结构/证据

- `exp3`
  - 行为一致性验证
  - 验证 DSL、Go、Solidity 在相同路径输入下是否产生一致轨迹

可以在论文或报告中形成如下逻辑：

1. `exp2` 证明代码生成结果在结构和控制逻辑上覆盖了 DSL
2. `exp3` 进一步证明这些结构在执行层面表现一致


## 最小可落地方案

如果先追求最小工作量，建议按以下顺序实现：

1. 先实现 DSL 参考语义与 basic path 生成，忽略循环
2. 先选 3 到 5 个代表 case
3. 先只支持：
   - 顺序路径
   - exclusive gateway
   - parallel gateway
4. 再补：
   - businessrule
   - oracletask
5. 最后补非法路径与拒绝一致性

这样能尽快形成第一版可运行实验。


## 关键结论表达建议

如果本实验完成，最终结论建议写成：

- 同一 DSL 生成的 Go / Solidity 实现，在代表性执行路径上与 DSL 参考语义保持一致
- 在非法输入路径上，两平台实现表现出一致的拒绝行为
- 因而可以说明生成器不仅在静态结构上保留 DSL 语义，也在有界执行层面保持跨平台行为一致性

注意：

- 如果当前只做了有界深度、忽略循环，应在结论中明确这一边界
- 不建议直接宣称“完全行为等价”

