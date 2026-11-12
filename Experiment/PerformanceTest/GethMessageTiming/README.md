# Geth 文件 Message：同一实例自动重复实验

当前正式结果为 [results-100/RESULTS.md](results-100/RESULTS.md)：按整批执行、批后筛选及缺额补测，最终保留100轮红色≤25秒的有效样本。共134次尝试，排除21次红色超阈值和13次无效计时。测量已完成，不需要继续运行。

- [100轮完整数据](results-100/results.json)
- [100轮均值图](results-100/geth_message_timeline_mean.png)
- [100轮逐段CSV](results-100/timings.csv)
- [核验摘要](results-100/verification.json)
- [四颜色统计公式、时间戳字段与查询接口](TIMING_DEFINITIONS.md)

同一已有合约、实例0、Message_1wswgqu连续发送，Message每轮保持ENABLED，其他节点状态不变，未创建新实例。正式均值是阈值筛选后的条件统计；按用户要求，目前仅保留有效100轮数据、统计表、图表及核验信息；失败记录、批次中间产物和此前实验结果已删除。总尝试次数与排除数量仅作为汇总说明保留。

## 自动执行3轮或100轮

在项目根目录运行，使用项目已有后端Python环境：

```bash
# 先验证3轮；默认自动生成一个新时间戳目录。
src/backend/venv/bin/python Experiment/PerformanceTest/GethMessageTiming/run_repeat.py --rounds 3

# 后续100轮：整批执行、批后筛选、按缺额整批补测。
src/backend/venv/bin/python Experiment/PerformanceTest/GethMessageTiming/run_batches.py \
  --rounds 100 \
  --max-red-seconds 25 \
  --output Experiment/PerformanceTest/GethMessageTiming/results-100
```

本次100轮采用 `run_batches.py`：先调用底层脚本一次完成100轮，不在批内按红色筛选；整批完成后统一排除红色>25000ms的样本，再按缺额执行下一整批，直至保留100轮。红色恰为25000ms仍纳入，同轮四种颜色一起保留或排除。脚本运行时会生成batches目录；本次已按要求清理批次数据及日志，最终纳入结果位于results-100的results.json、summary.json与timings.csv中。

脚本运行时会生成attempts目录与attempts.csv；本次已按要求删除这些原始尝试记录。报告保留总尝试次数、红色超阈值次数和无效计时次数；正式均值为筛选后的条件统计，不是原始全体请求的平均延迟。子批次日志中的passed/accepted只表示该轮核验和计时成功，是否满足25秒纳入条件由整批结束后的上层筛选决定。

`run_repeat.py --max-red-seconds` 仍支持逐次自动筛选，但本次100轮不使用该模式。

脚本默认使用截图中已部署的API `SupplyChainPaper5-1f3416-f60b43-a2eb72` 对应的BPMN和现有实例。支持 `--bpmn`、`--instance`、`--message`、`--signer` 指定其他目标，详见 `--help`。当前针对可重复的单Message文件模型，必须预先为ENABLED；脚本不部署合约、不创建实例、不执行其他节点。

默认每轮生成不同内容的1KiB文件，避免相同文件/CID导致IPFS缓存复用。`--file /path/to/file` 可以指定文件，但不改动文件内容；重复发布命中缓存会明确失败，不混入实际上传样本。100轮正式测量建议使用默认的新文件策略。

输出目录非空时会拒绝覆盖。已完整验证并保存的轮次可以使用 `--resume --output 原输出目录` 继续，`--rounds` 和 `--max-red-seconds` 保持该次任务原计划的值。未完成或失败的轮次不会自动忽略或计为成功；需要先检查失败原因。

脚本自动写出results.json、逐轮round-N/result.json、summary.json、timings.csv、verification.json和RESULTS.md。每轮保存检查点，认证令牌每轮在内存中重新生成，不写入文件，不需要把账号密码放入脚本。后端API、FireFly、IPFS和已部署合约需保持运行。

## 文件路径与计时

脚本通过与你新增上传按钮相同的认证后端 `prepare-file-message` 接口上传文件、发送真实私有Message，返回文件dataId和MessageID；随后在后台发起FireFly IPFS发布，同时立即调用业务合约。等待双方消息确认、pin成功、业务成功事件，并从接收方和IPFS按CID读回文件核验原始字节。

- 蓝：自动化客户端发起上传请求至双方消息确认、pin完成和IPFS发布完成的最晚时间。
- 黄：发起FireFly文件发布请求至成功返回CID，验证关联IPFS Operation为Succeeded，覆盖发布排队、上传与发布处理。
- 绿：业务请求开始至对应Operation.created。
- 红：同一Operation.created至匹配Operation ID、事务ID的业务调用成功事件。

红绿严格衔接。计时使用Python HTTP客户端单调时钟，服务端时间通过每5ms的wall/monotonic采样统一到同一轴，原始样本保留以便离线复核。它测量API请求流程，不包含人工选文件、鼠标操作或浏览器渲染时间。Fabric对比时应使用相同客户端和边界。

本次发送端为5002，接收组织为5001；接收方从现有执行绑定和FireFly身份父组织解析，未手动改变绑定或业务代码。实验显式发布IPFS，原私有传输仍使用dataexchange。

## 离线核验及绘图

```bash
# 只读取本次保存的数据、重放时钟换算，不发送交易。
src/backend/venv/bin/python Experiment/PerformanceTest/GethMessageTiming/summarize.py

# 绘制均值图；需要matplotlib。
python3 Experiment/PerformanceTest/GethMessageTiming/draw.py

# 对100轮输出绘图。
python3 Experiment/PerformanceTest/GethMessageTiming/draw.py \
  --input Experiment/PerformanceTest/GethMessageTiming/results-100/results.json \
  --output-dir Experiment/PerformanceTest/GethMessageTiming/results-100
```

此前的results/、results-repeat/实验结果目录已删除。当前实验使用run_repeat.py，批量筛选使用run_batches.py。
