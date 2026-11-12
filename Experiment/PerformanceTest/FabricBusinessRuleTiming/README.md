# Fabric BusinessRule 七阶段时间线

当前环境 Forge-962 中已部署独立 `FabricBrtTiming` 链码，源模型为 `deployment/BusinessRuleTiming.bpmn`，BusinessRule 为 `Activity_timingbrt`。链码由当前生成器生成，业务代码没有手工修改；没有改生成器、项目执行器、业务页面或旧实验数据。

正式100轮结果位于 [results-100/RESULTS.md](results-100/RESULTS.md)，均值图为 [fabric_businessrule_timeline_mean.png](results-100/fabric_businessrule_timeline_mean.png)。100次尝试全部有效，没有排除样本，没有按耗时筛选。按用户要求已删除三轮预验证、调试失败记录、重复attempts及过程日志；保留100轮完整原始证据、统计与成功部署材料。

## 模型与真实执行路径

模型为 Start → Score Decision → End。输入 `score` 为字符串，实例初始值为空字符串；DMN 决策 `Decision_timing` 规定空字符串输入返回 `approved=true`，非空返回 false。输出在链上 `StateMemory.Approved` 中核验，从 false 变为 true；BusinessRule 状态从 ENABLED 变为 COMPLETED，遵循原始生成器逻辑。

每轮分别准备新实例，实例创建、Start、DMN文件上传与IPFS发布、Oracle CID绑定均在计时外。由生成器产生的 BusinessRule 发出真实 `DMNContentRequired` 事件，实验 WebSocket 执行器接收后按 CID 下载文件，并调用原始 `_Continue` 方法。Continue 内部校验DMN哈希并调用环境中现有 DMNEngine，返回结果写回BPMN链码。

这条链路使用 Fabric 的链内 DMNEngine，没有 Chainlink 阶段。实验执行器与旧执行器承担同样的下载和Continue调用职责，增加独立的逐请求记录；没有调用旧Redis固定键，也没有另外启动旧oracle进程，避免重复消费。

## 时间边界与时间戳来源

| 阶段 | 开始 → 结束 | 数据来源 |
|---|---|---|
| API Invoker | 第一次请求开始 → Operation1.created | 客户端monotonic_ns起点；第一次调用响应及GET /operations/{id}的created |
| BPMN SC | 同一Operation1.created → 匹配调用成功事件.created | GET /events?tx=Operation1.tx，匹配type=blockchain_invoke_op_succeeded、reference=Operation1.id、tx一致 |
| Event Bus | BPMN SC结束的同一个业务成功事件.created → WebSocket客户端收到对应DMNContentRequired完整消息 | 起点复用第一次Operation的匹配成功事件；终点由执行器monotonic_ns记录。消息id/reference、InstanceID、rule ID、CID及链上transactionId核验关联 |
| Executor | 执行器收到事件 → Continue请求完整响应结束 | 同一执行器进程的monotonic_ns；包含下载、内容校验、构造请求及第二次请求 |
| IPFS | GET /ipfs/{CID}开始 → 完整读取成功响应内容 | 同一HTTP客户端单调时钟；校验状态、完整字节和DMN哈希，哈希计算在下载时延外 |
| API Invoker2 | 实际发起Continue请求 → Operation2.created | 客户端单调时钟起点、第二次Operation.created；不以IPFS结束替代请求开始 |
| DMN SC | 同一Operation2.created → 匹配调用成功事件.created | 第二次Operation.id、tx严格匹配的blockchain_invoke_op_succeeded.created |

两个API阶段均与对应链上阶段共享同一换算后的Operation.created边界。BPMN SC与Event Bus也共用同一次换算后的业务成功事件边界，Event Bus与Executor共用执行器接收时刻。Executor与其内部IPFS、API Invoker2以及DMN SC起始部分可重叠，不能将七段相加。

Event Bus采用与旧七段图相同的完整区间，包含“业务成功通知→FireFly记录DMNContentRequired”和“FireFly记录→执行器收到”两段。当前100轮Event Bus均值为413.92ms，两部分原始明细保存在各轮eventBusBreakdown中。源事件created仍由GET /events/{id}核验，保存在eventBusBreakdown供细分审计，不额外增加图中的阶段。timingDefinitionVersion=2用于区分已修正的区间；该定义直接用于100轮采集，亦支持用已保存的时间戳和clockPairs离线复算，无需重发交易。

DMN SC测量的是整个Continue交易，其中包含链内DMNEngine调用、共识及FireFly成功通知，不是DMN引擎纯CPU时间。IPFS测量的是规则下载，和文件Message实验中的IPFS上传发布指标不同。

服务端时间通过原Message实验同样的5ms wall/monotonic采样映射到客户端轴；不跨系统时钟跳变插值，拒绝没有唯一映射的样本，原始字段与clockPairs完整保存。采集客户端与FireFly运行在同一宿主机时间基准下。若出现无效计时，保留原尝试并用新实例补测；业务失败立即停止，不伪造数据。

## 脚本

从项目根目录使用后端虚拟环境运行。环境编号、API、监听器、CID网关等由 `config.live.json` 保存。

```bash
# 新建独立模型；生命周期步骤写入deployment.json，重复调用跳过已完成步骤。
src/backend/venv/bin/python Experiment/PerformanceTest/FabricBusinessRuleTiming/prepare_fixture.py --stage all

# 测量三次；输出目录必须为空。
src/backend/venv/bin/python Experiment/PerformanceTest/FabricBusinessRuleTiming/run_repeat.py \
  --config Experiment/PerformanceTest/FabricBusinessRuleTiming/config.live.json \
  --rounds 3 --output Experiment/PerformanceTest/FabricBusinessRuleTiming/results-new

# 仅根据保存的结果离线画图，需matplotlib。
python3 Experiment/PerformanceTest/FabricBusinessRuleTiming/draw.py \
  --input Experiment/PerformanceTest/FabricBusinessRuleTiming/results-100/results.json

# 对已有数据离线重放校准时间戳并更新边界，不请求环境、不发送交易。
src/backend/venv/bin/python Experiment/PerformanceTest/FabricBusinessRuleTiming/recalculate.py \
  --input Experiment/PerformanceTest/FabricBusinessRuleTiming/results-100/results.json
```

采集脚本通过只读查询寻找本独立链码的下一个未使用实例ID，创建后核验BRT初始状态；不会从其他模型推断实例ID，也不读取固定Redis键。每轮使用独立订阅并在结束后删除订阅。

旧版WebSocket适配记录与三轮预验证结果已清理，不参与正式100轮均值。当前只保留有效100轮及其核验信息，sampleCounts保存总次数与无筛选说明。
