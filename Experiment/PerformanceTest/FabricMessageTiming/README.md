# Fabric 文件 Message 时间线实验脚本

实验代码与结果集中在本目录，不修改项目业务代码或现有链码模板。采集脚本不负责部署；`generate_fixture.py`、`deploy_fixture.py` 用于明确授权后的独立测试模型生成和部署。

当前 Fabric 环境已部署独立测试模型并完成采集：正式结果为 [100轮报告](results-100/RESULTS.md) 和 [100轮均值图](results-100/fabric_message_timeline_mean.png)。正式任务共108次尝试，保留100轮；8次时间戳映射无效，红色超过25秒的样本为0。未使用先前Geth的数据，也未混入三轮预验证。按用户要求，现已删除三轮预验证、失败与排除记录、重复尝试副本、部署失败材料及过程日志；仅保留最终有效100轮数据和成功部署所需材料。筛选条件与数量保留作汇总说明。

[源码与实际安装包核验](deployment/source-verification.json)确认仅有允许重复调用的单行差异；[最终独立核验](results-100/final-verification.json)覆盖文件哈希、双方消息确认、节点状态、红绿边界、时钟离线重放、CSV与图表均值。

## 当前测试模型

测试 BPMN 为 `deployment/FabricFileTiming.bpmn`，包含 `Message_1wswgqu`，其中 `orderDetails` 为必填 file 字段，另有固定的 `requestId=1`。该标量避免当前 Fabric contract-api 对生成器空 StateMemory 的元数据校验错误，不增加流程节点。

`deployment/generated.go` 是当前生成器原始输出；`deployment/smartcontract.go` 是部署的实验副本，唯一逻辑差异是删除 Send 中将目标状态改为 WAITINGFORCONFIRMATION 的一行，保留真实 MessageID 写入、身份校验、事件及持久化操作。补丁保存于 `deployment/repeatable-message.patch`。未调用 Complete，后续节点不推进。生成器本身没有修改。

固定requestId字段用于避免纯文件模型产生空StateMemory的兼容问题。早期失败部署记录已清理，不计入任何时延样本。

```bash
# 从现有 BPMN 的文件 Message 构造独立模型，并调用当前生成器。
src/backend/venv/bin/python Experiment/PerformanceTest/FabricMessageTiming/generate_fixture.py \
  --owner-bpmn 实际源BPMN_UUID

# 使用部署清单按步骤继续，不覆盖现有 BPMN 或已完成生命周期步骤。
src/backend/venv/bin/python Experiment/PerformanceTest/FabricMessageTiming/deploy_fixture.py --stage all
```

部署在 `deployment/deployment.json` 留存环境、独立链码、FireFly API 与初始化 Operation ID。生成脚本拒绝覆盖已经部署的模型。部署脚本默认发送端5002、接收端5001，实际配置写入 `config.live.json`；采集脚本仍支持任意环境配置。

## 配置

复制 `config.example.json` 为自己的配置文件，替换所有 `REPLACE_WITH_*` 字段：

- `source_core`、`receiver_core`：发送方与接收方 FireFly namespace 完整URL，例如以 `/api/v1/namespaces/default` 结尾；必须属于不同组织。
- `api`：发送方已注册的 Fabric 链码 API 完整URL，末尾为 `/apis/实际API名`。
- `ipfs_gateway`：发送方 IPFS HTTP 网关根地址，不含 `/ipfs`。
- `instance_id`、`message_id`：已有实例编号及可重复执行的文件 Message ID。脚本不会创建、重置或推进节点来准备实验。
- `recipient`：绑定接收方的 FireFly 身份 DID；`key` 为现有 Fabric 签名标识，格式与页面链码调用相同。
- `file_field`：Message Format 中声明的文件字段，例如 `orderDetails`。
- `values`：其余 Message 业务字段；`contract_input`：Send 方法的其余链码参数。脚本根据实际接口填入实例ID、真实 FireFly Message ID，以及存在对应参数时的文件 dataId。
- `parameters`：默认从接口自动识别参数名，兼容 `InstanceID`、`instanceID`、`FireFlyTran`、`fireflyTranID` 等。若有歧义，填入 `{"instance":"实际实例参数名","firefly":"实际MessageID参数名","file":"实际文件参数名"}`；没有链上文件参数时不要设置 `file`。
- `header_env`：可选 HTTP 认证头与环境变量名的映射，例如 `{"Authorization":"FABRIC_TIMING_AUTH"}`。环境变量值包含完整认证头内容；脚本不保存头部凭据。不要将密钥或令牌写入提交中的配置。

链码必须已提供 `GetAllMessages`、`GetAllGateways`、`GetAllActionEvents`、`GetAllBusinessRules` 查询。它们的实例参数同样从接口识别。脚本比较前后完整节点查询结果，只允许目标 Message 的 `FireflyTranID` 更新；目标 `MsgState` 必须始终为1。若普通链码在调用后推进状态，脚本停止并保存失败记录，不自动改链码或回滚。

## 执行命令（环境就绪后）

从项目根目录运行。采集依赖 `requests`，可用已有后端虚拟环境；绘图另需 `matplotlib`。

```bash
# 只验证配置字段，不请求环境，不执行实验。
src/backend/venv/bin/python Experiment/PerformanceTest/FabricMessageTiming/run_repeat.py \
  --config /path/to/fabric-timing.json --check-config

# 先验证3轮。
src/backend/venv/bin/python Experiment/PerformanceTest/FabricMessageTiming/run_repeat.py \
  --config /path/to/fabric-timing.json --rounds 3 \
  --output Experiment/PerformanceTest/FabricMessageTiming/results-3

# 再运行100轮：整批完成后排除红色>25秒，按缺额整批补测。
src/backend/venv/bin/python Experiment/PerformanceTest/FabricMessageTiming/run_repeat.py \
  --config /path/to/fabric-timing.json --rounds 100 --max-red-seconds 25 \
  --output Experiment/PerformanceTest/FabricMessageTiming/results-100

# 离线绘制均值图，不产生交易。
python3 Experiment/PerformanceTest/FabricMessageTiming/draw.py \
  --input Experiment/PerformanceTest/FabricMessageTiming/results-100/results.json
```

默认每次生成内容不同的1KiB文件，避免 CID 缓存复用。`--file` 可指定原样文件，但重复上传命中已发布数据将停止，不作为新的上传样本。`--max-red-seconds 0` 取消红色阈值；`--max-attempts` 默认1000，避免无限补测。红色恰为25000ms可纳入，不筛蓝、黄、绿。时钟映射无效单列排除；业务、文件或状态核验失败立即停止。未完成请求不盲目重试，非空结果目录禁止覆盖。

## 流程和四色边界

1. 直接调用发送方 `POST /data`，multipart字段为 `autometa=true` 和 `file`，取得 dataId。
2. `POST /messages/private` 发送业务字段及真实文件附件，取得 MessageID。文件字段保存 dataId；不使用 CID 替代附件引用。
3. 后台发起 `POST /data/{dataId}/blob/publish`，请求已开始后立即调用 `POST /apis/{api}/invoke/{MessageID}_Send`，两者不等待对方响应完成。
4. 等待业务 Operation 成功、匹配成功事件、双方消息确认及 batch pin 成功；从接收方和 IPFS 网关读取文件核验字节。随后查询链码确认节点仍可重复，且目标保存的 FireflyTranID 与本轮真实 MessageID 一致。

| 颜色 | 开始 | 结束与数据来源 |
|---|---|---|
| 蓝色 Private Data Bus | 客户端发送文件上传HTTP请求 | 取发布响应结束、发送方和接收方 Message.confirmed、成功 blockchain_pin_batch Operation.updated 的最晚时间。消息通过双方 `GET /messages/{MessageID}` 查询；pin经 `GET /batches/{batchID}` 的 tx.id 关联 `GET /operations?tx=...`，所有相关操作须成功。 |
| 黄色 IPFS | 客户端发送 `POST /data/{dataId}/blob/publish` | 完整成功响应返回 CID。另查 `GET /operations?type=sharedstorage_upload_blob`，按 input.dataId 匹配，核验 Succeeded、output.payloadRef、`GET /data/{dataId}` 的 blob.public 与 CID 一致。查询核验耗时不加进黄色。 |
| 绿色 API Invoker | 客户端发送业务链码请求 | 本次业务 Operation.created，由调用响应及 `GET /operations/{operationID}?fetchstatus=true` 核对。 |
| 红色 BPMN SC | 同一业务 Operation.created | `GET /events?tx={业务Operation.tx}` 返回的 blockchain_invoke_op_succeeded.created，同时匹配 reference=Operation.id、tx=Operation.tx。包含 Fabric 调度、提交、确认及 FireFly 事件处理，并非纯链码CPU执行时间。 |

红绿共享一次换算后的边界，统计上严格衔接；黄绿可以重叠。蓝色不强行延长到红色结束，按真实同步/pin事件计算；哈希核验的客户端处理时间不额外计入蓝色。

客户端请求起止使用 `time.monotonic_ns()`，记录 rawStart/rawEnd。服务端 created/confirmed/updated 是 FireFly 时间戳；复用 Geth 实验的5ms wall/monotonic采样桥接，将其映射到客户端同一时间轴，保存原始时间与采样证据。系统时间跳变不跨段插值，无法唯一映射的样本排除。要求客户端与 FireFly 共享宿主机时间基准；跨机器未校时部署不能直接套用该计时方法。

Fabric 上传准备直接使用现有 FireFly 接口，Geth 原实验使用其后端 prepare-file-message 接口。四色事件边界保持一致，但上传入口的服务开销存在差异；不把两者描述为完全相同的端到端入口。

脚本运行时输出 results.json、每轮 round-N/result.json、summary.json、timings.csv、verification.json、RESULTS.md 和 attempts/原始尝试。本次整理后已删除attempts及results.json内的尝试明细，保留有效100轮；绘图生成PNG、PDF、SVG及均值区间JSON。筛选后均值须标明阈值及排除数量，不能当作未经筛选的全体延迟。以实际输出目录中的 status 与样本数判断完成情况。
