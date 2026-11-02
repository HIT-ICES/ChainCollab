# Geth BusinessRule 时间线实验

本实验创建独立 BPMN 模型，使用当前 Solidity 生成器原样生成、编译及部署合约，并复用环境中已有的 DMN Lite、Chainlink directrequest Job、CDMN 和 IPFS。实验不修改生成器、业务合约模板、Job 或服务配置。为测量新增独立且带完整参数定义的 RequestFulfilled 监听器，不修改环境原有监听器。每轮创建新的实例，按正常状态推进，不修改节点为可重复调用。

## 实际执行链路

准备阶段将与 Fabric 实验相同的 899 字节 DMN 规则文件上传并发布到 IPFS，取得 CID；把 CID、decisionId 和 DMN Lite 地址配置到新 BPMN 实例，并启动流程。这部分不计入 BRT 时间线。

| 步骤 | 调用与执行的操作 | 完成后得到什么 | 对应时间段 |
|---|---|---|---|
| ① 发起 BRT 请求 | 脚本通过 FireFly 调用 `Activity_timingbrt(instanceId)` | FireFly 创建本次 Operation | API Invoker (BRT request) |
| ② 链上请求 DMN 决策 | BPMN 合约调用 DMN Lite 的 `requestDMNDecision(url, cid, decisionId, inputData)`，经 Operator 发出 `OracleRequest` | 得到 requestId，BPMN 节点进入等待状态 | BPMN SC / DMN request |
| ③ Chainlink 接收 DMN 请求 | 已有 directrequest Job 接收事件并启动任务 | 请求关联到具体 Chainlink Run | DMN request to Chainlink job；从步骤①起计，包含前面的等待 |
| ④ 调用链下 DMN 执行器 | Chainlink 调用对应 CDMN 的 `/api/dmn/calc`，携带 requestId、CID、decisionId 和输入 | CDMN 开始处理该决策请求 | Executor / off-chain DMN evaluation |
| ⑤ 下载 DMN 规则文件 | CDMN 根据 CID 发出 `GET /ipfs/{cid}`，完整读取 DMN 文件 | 得到用于本次决策的规则内容，校验字节哈希一致 | IPFS / DMN download；嵌套在 Executor 内 |
| ⑥ 执行 DMN 并返回结果 | CDMN 调用 `dmn_engine.evaluate(...)`，计算决策并向 Chainlink 返回 JSON 结果 | 本次结果为 `approved=true` | 包含在 Executor 中；未单独测量纯 DMN 计算时间 |
| ⑦ DMN 结果上链 | Chainlink 提交 `commitBaselineFromRaw(requestId, raw)`，写入 DMN Lite，产生 `RequestFulfilled` | 链上结果可读，FireFly 接收到对应成功事件 | DMN result commit / event receipt |
| ⑧ 发起流程继续请求 | 实验脚本通过 FireFly 调用 `Activity_timingbrt_Continue(instanceId)` | 创建第二个 Operation | API Invoker2 (BPMN Continue) |
| ⑨ BPMN 读取并应用 DMN 结果 | BPMN 合约查询 DMN Lite 状态与原始结果，提取 approved，更新业务状态 | Approved 从 false 变为 true，BusinessRule 完成并启用后续节点 | BPMN SC / apply DMN result |

**DMN 的规则执行发生在步骤⑥的 CDMN 服务内。DMN Lite 是链上的请求与结果管理合约，不是链上 DMN 规则执行引擎；步骤⑨读取并应用结果，不会重新执行 DMN。当前 Continue 由实验脚本触发。**

九个流程步骤对应八条计时线：步骤④与⑥归入同一个 Executor 区间，步骤⑤同时作为其内部的 DMN 下载子区间展示。图中没有为纯 DMN 计算添加未经测量的独立时间条。

四个现有 Job 均可能执行。依据 RequestFulfilled 日志的 blockNumber/logIndex 选取最早成功回写的交易，再按交易发送地址关联 Chainlink 节点。Executor、IPFS 和结果回写均取该节点；不能拼接各节点最短时间。此环境实际走 directrequest，并非 OCR 聚合。

## 时间边界与证据

| 阶段 | 起点 | 终点及来源 |
|---|---|---|
| API Invoker (BRT request) | 客户端发送第一次 `/invoke/Activity_timingbrt` 前的单调时钟 | 同一个 FireFly Operation 的 `created` |
| BPMN SC / DMN request | 上述 Operation.created | FireFly `/events` 中匹配 Operation/交易的 `blockchain_invoke_op_succeeded.created` |
| DMN request to Chainlink job | 第一次业务请求起点 | 获胜节点 `/v2/jobs/{id}/runs` 中对应 requestId 的 `createdAt` |
| Executor / off-chain DMN evaluation | 上述 Job.createdAt | 同一 Run 的 `call_cache` HTTP 任务 `finishedAt`，即 CDMN 响应被 Chainlink 接收完毕 |
| IPFS / DMN download | 获胜 CDMN 实际发出 `GET /ipfs/{cid}` 的首个请求数据包 | 同一请求完整 HTTP 响应到达 CDMN；校验 HTTP 200、899 字节及 SHA-256 与原 DMN 一致 |
| DMN result commit / event receipt | 上述 call_cache.finishedAt | 最早成功回写交易对应的 FireFly `blockchain_event_received.created`；其 reference 指向 RequestFulfilled 记录 |
| API Invoker2 (BPMN Continue) | 客户端发送 `/invoke/Activity_timingbrt_Continue` 前的单调时钟 | 第二次请求对应的 Operation.created |
| BPMN SC / apply DMN result | 第二次 Operation.created | 对应 `blockchain_invoke_op_succeeded.created` |

Operation 通过 `/operations/{id}` 查询；交易事件通过 `/blockchainevents?listener=...` 关联，原始链上日志和交易通过 `eth_getLogs`、`eth_getTransactionByHash` 复核。结果就绪由 DMN API 的 `getRequestStatus`（state=2）、`getRawByRequestId` 双重核验。最后验证 BPMN 状态由 Enabled 变为 Done，并利用编译器 storageLayout 和 `eth_getStorageAt` 读取原合约 Approved 字段，确认 false→true。

IPFS 时间采用只读数据包观测：`http_observer.py` 在 CDMN 容器网络空间读取真实 HTTP 流，不修改应用，不插入代理，不额外下载代替测量。容器与宿主机单调时钟在启动时校验共享同一时间轴。FireFly/Chainlink 的 UTC 时间戳通过宿主机 wall/monotonic 对照样本映射，保存 `clockPairs`，便于复核，避免直接混算时钟。最终脚本从请求返回后立即轮询成功事件，保存 `success1Bounds`、`success2Bounds`；结果回写记录 `fulfillmentBounds`。区间下界来自上一次未查到事件的查询开始时刻，上界来自首次查到事件的查询结束时刻。以此约束原始 `created` 的映射，不用轮询接收时刻替代原始时间戳。

图与结果文档使用上述明确的阶段名称；JSON/CSV 中保留原阶段键以兼容已有记录，`run_repeat.py` 的 `PHASE_LABELS` 提供一一对应关系。此命名修订不改变计时边界、原始时间戳或耗时。

## 与 Fabric 图的关系

两套实验使用相同 BPMN/DMN 和 API→Operation.created 边界，但当前生成器执行架构不同。Geth 的 DMN 在 CDMN 链下计算，另有结果回写交易，最终 Continue 只读取结果并应用流程；不能将 Continue 标成 Fabric 的链内 DMN SC。Chainlink 直接监听链上日志，其接收可能早于 FireFly 记录首笔交易成功，因此 Request-to-job 与前两条存在重叠，不能强行串接为 Fabric Event Bus。IPFS 位于 Executor 内部，不能累加各条耗时作为总延迟。

结果回写阶段的终点是 FireFly 观测到结果事件，包含连接器事件接收延迟，并非纯 EVM 执行时间。100 轮均使用相同的最终观测流程：确认结果状态与对应成功事件后，再发起 Continue。不会用 Chainlink `submit_tx.finishedAt` 作为交易成功终点，因为该任务可能额外等待多块确认。

## 最终数据与筛选规则

独立完成 145 次测量尝试，获得 100 轮有效样本。17 次因时钟映射无解或不唯一排除，28 次因超出约定阈值排除。此次清理删除了排除样本明细、旧三轮验证、调试目录、运行日志以及重复数据；保留分类计数和全部 100 轮有效原始证据。

| 阶段原始键 | 上限 | 排除条件 |
|---|---:|---|
| Result commit on chain | 25000 ms | 严格大于 25000 ms |
| Request to Chainlink job | 60000 ms | 严格大于 60000 ms |

其余阶段不进行延迟阈值筛选，即使耗时较长也保留。等于上限的样本有效。任一约定阶段超限则整轮排除，并创建新实例补测。批量脚本最多尝试 300 次，遇到未预期业务错误时停止并保存状态。

最终结果均值是**通过上述筛选后的 100 轮均值**，不表示全部 145 次尝试的无条件均值。

| 文件或目录 | 内容 |
|---|---|
| `results-100/RESULTS.md` | 八阶段均值、中位数、范围及统计口径 |
| `results-100/timings.csv` | 100 轮 × 8 阶段，共 800 条明细 |
| `results-100/geth_businessrule_timeline_mean.*` | 平均时间线 PNG、PDF、SVG 和绘图数据 |
| `results-100/round-1/` … `round-100/` | 每轮完整原始记录，含 API、Operation、事件、Chainlink、IPFS、状态与时钟样本 |
| `results-100/results.json` | 紧凑汇总索引，以 sampleFiles 引用每轮原始记录，不重复内嵌数据 |
| `results-100/sample-sha256.json` | 100 份原始记录的 SHA-256，校验清理前后数据未改变 |
| `results-100/run-metadata.json` | 已完成批次的起止时间、筛选阈值、原运行脚本哈希与分类计数 |
| `deployment/` | 原生成 Solidity、BPMN、DMN、ABI、编译结果、部署与字节码核验记录、开发 LINK 补充交易 |

`run_repeat.load_report(path)` 同时支持历史内嵌格式与上述按轮归档格式。绘图和验证脚本默认读取最终 100 轮。有效记录中的 API/交易/请求 ID 用于关联真实证据，予以保留；原网络观测日志中的有效请求已经包含在每轮记录内，无需重复保留日志。

## 复核与复现

以下离线命令不提交任何新交易：

```bash
src/backend/venv/bin/python -B Experiment/PerformanceTest/GethBusinessRuleTiming/verify_results.py
PYTHONPATH=/tmp/geth-timing-plot-libs src/backend/venv/bin/python -B Experiment/PerformanceTest/GethBusinessRuleTiming/draw.py
```

验证脚本核对 100 份文件哈希、DMN 内容、规则输出、业务状态、筛选阈值，并用保存的 clockPairs 重算全部 800 个阶段区间。绘图需要 matplotlib；示例 PYTHONPATH 指向本机已安装目录，可替换为自己的安装位置。

重新采集须确保环境与 `config.live.json` 匹配，已有 Chainlink Job/CDMN 正常运行，并为 DMN Lite 提供足够的开发 LINK（每次请求 0.1 LINK；原批次补足到 30 LINK 供最多 300 次尝试，交易已留存）。环境重新部署后需重新生成对应部署配置，不能沿用失效地址。

```bash
# 需要重新部署测试模型时使用；当前环境可直接复用现有部署
src/backend/venv/bin/python -B Experiment/PerformanceTest/GethBusinessRuleTiming/prepare_fixture.py

# 指定新的空目录，避免覆盖最终归档
src/backend/venv/bin/python -B Experiment/PerformanceTest/GethBusinessRuleTiming/run_batch.py --rounds 100 --output /absolute/path/to/new-results
```

批量任务可脱离终端运行，完成后自动离线复核和绘图。运行时会生成 `batch-100/status.json` 与脚本快照；日志可由启动者重定向。临时目录已加入本实验的 `.gitignore`。需要恢复中断任务时，对相同输出目录加 `--resume`，并先确认旧进程已退出；不要同时运行两份采样。

Chainlink 登录凭据可通过 CHAINLINK_EMAIL/CHAINLINK_PASSWORD 覆盖，仅用于内存会话；不保存 Cookie。业务代码、生成器、现有 Chainlink Job 及服务配置均未因本实验修改。
