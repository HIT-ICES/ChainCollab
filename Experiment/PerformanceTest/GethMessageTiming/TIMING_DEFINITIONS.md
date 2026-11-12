# 带文件 Message 的四阶段计时方法

本文以当前自动化脚本 `run_repeat.py` 和正式100轮结果 `results-100/` 为准，说明红、黄、蓝、绿四个阶段的统计边界、时间戳来源、查询接口及关联规则。本文不修改既有测量数据。

当前使用已部署合约的实例0，连续调用 `Message_1wswgqu_Send`。每轮上传不同内容的1KiB文件，节点保持 `ENABLED`；不部署新合约、不创建新实例、不执行其他流程节点。

## 一、时间戳类型与接口地址

### 1. 时间戳类型

本实验使用两类时间戳，必须明确区分其来源：

| 类型 | 获取方式 | 用途 |
|---|---|---|
| **客户端单调时间** | Python脚本调用 `time.monotonic_ns() / 1e6`。 | 记录上传、发布及业务请求的开始时间，以及发布响应完整接收时间。它由脚本记录，不是FireFly接口返回的字段。 |
| **FireFly服务端时间戳** | 读取API返回的 `Operation.created`、业务成功事件 `created`、消息 `confirmed`、pin操作 `updated`。 | 确定业务操作创建、业务调用成功及双方消息确认等服务端事件的时间。 |

`timed_post()` 先完成JSON或multipart请求构造，再在调用 `Session.send()` 前记录开始时间；响应体完整读取后记录结束时间。JSON解析、后续状态查询及哈希核验不计入该HTTP请求耗时。

当前计时客户端是Python自动化HTTP脚本，复用页面新增上传功能的后端接口；**不是浏览器Resource Timing，也不包含人工选文件、鼠标操作或页面渲染耗时**。浏览器中的 `fetchStart/responseEnd` 仅是对应边界的类比名称。

### 2. 接口地址约定

| 记号 | 本次环境的值 |
|---|---|
| `B`：业务后端 | `http://127.0.0.1:8000/api/v1` |
| `S`：发送方FireFly命名空间 | `http://127.0.0.1:5002/api/v1/namespaces/default` |
| `R`：接收方FireFly命名空间 | `http://127.0.0.1:5001/api/v1/namespaces/default` |
| `A`：已注册业务合约API | `S/apis/SupplyChainPaper5-1f3416-f60b43-a2eb72` |
| `G`：发送方IPFS网关 | 本次为 `http://127.0.0.1:10607`，脚本从当前Docker端口映射解析，也可通过 `--ipfs-gateway` 指定。 |

下文的URL使用上述记号展开。例如 `GET S/messages/{MID}` 表示查询发送方命名空间下的一条消息。

### 3. 关联标识

| 标识 | 含义与来源 |
|---|---|
| `D`：文件dataId | 准备接口响应中的 `fileIds.orderDetails`。 |
| `MID`：FireFly MessageID | 准备接口响应中的 `messageId`，是本轮新生成的UUID。 |
| `BID`：BatchID | `GET S/messages/{MID}` 返回的 `batch`。 |
| `BTX`：批次事务ID | `GET S/batches/{BID}` 返回的 `tx.id`。 |
| `OID`：业务OperationID | 业务合约调用响应中的 `id`。 |
| `OTX`：业务事务ID | 同一业务Operation的 `tx`。 |
| `PID`：IPFS上传OperationID | 查询上传操作列表，匹配 `input.dataId == D` 后取得的 `id`。 |
| `CID`：IPFS内容地址 | 发布接口响应中的 `blob.public`，随后与上传Operation及文件资源交叉核验。 |

`BTX` 与 `OTX` 对应不同事务：前者用于消息批次存证，后者用于业务 `Message_Send` 调用。不能以其中一个的完成时间代替另一个。

## 二、文件上传与发送流程

| 步骤 | 执行操作 | 返回或完成结果 |
|---|---|---|
| **① 上传文件** | 客户端向后端 `prepare-file-message` 提交文件，后端调用FireFly `/data`。 | 获得文件 `dataId`；此时不等于IPFS发布成功或接收组织同步完成。 |
| **② 发起IPFS发布** | 客户端调用FireFly `/data/{D}/blob/publish`。 | FireFly处理发布请求并执行共享存储上传任务。 |
| **③ 完成IPFS发布** | FireFly内部调用IPFS写入文件，发布接口成功返回。 | 获得有效CID；关联上传Operation为 `Succeeded`。 |
| **④ 发送文件Message** | 后端发送私有Message，附件使用 `{id: D}`，业务文件字段也引用D。 | 返回真实FireFly MessageID，后台继续传输、组批。 |
| **⑤ 调用业务合约API** | 客户端携带MID调用 `Message_1wswgqu_Send`。 | 返回OID；其状态可能仍为 `Pending`。 |
| **⑥ 业务执行成功** | FireFly调度并提交业务交易，处理回执和成功事件。 | 同一业务Operation成功，并生成匹配的 `blockchain_invoke_op_succeeded` 事件。 |
| **⑦ 完成消息同步与确认** | 完成文件及消息传输、batch pin和双方消息确认。 | 双方消息为confirmed、关联传输及pin操作成功，接收文件内容一致。 |

**编号用于区分阶段，不表示所有步骤串行执行。** 当前后端准备接口一体化完成①和④，返回D、MID；脚本随后在后台启动②，同时立即执行⑤，不等待③完成。③与⑤、⑥可能重叠，⑦中的传输和组批从④后已经开始。

私有文件传输使用现有dataexchange路径。为了测量文件发布，实验显式调用FireFly的IPFS发布接口；不能将所有私有消息传输都视为自动使用IPFS。

## 三、四种颜色的统计公式

以下所有时间都先统一到同一单调时间轴，再进行减法和比较。`M(x)` 表示将API返回的服务端时间戳x映射到该单调轴。

定义：

- `t_upload_start`：上传准备请求的客户端发送开始时间。
- `t_publish_start`、`t_publish_end`：文件发布请求的客户端开始时间、成功响应完整读取时间。
- `t_invoke_start`：业务合约请求的客户端发送开始时间。
- `t_op_created = M(Operation.created)`。
- `t_business_success = M(匹配的业务调用成功事件.created)`。
- `t_sender_confirmed = M(发送方Message.confirmed)`。
- `t_receiver_confirmed = M(接收方Message.confirmed)`。
- `t_pin = M(关联batch pin操作.updated)`，前提是该操作已经Succeeded，并核对字段语义。

| 颜色 | 计算公式 | 统计范围 |
|---|---|---|
| **红：BPMN SC** | `t_business_success − t_op_created` | 业务Operation创建后，到FireFly报告本次业务调用成功；包括后续调度、提交、上链等待和成功事件处理。 |
| **黄：IPFS发布** | `t_publish_end − t_publish_start` | FireFly文件发布API的完整请求时延，覆盖②＋③；发布成功并取得CID才满足本次请求的完成条件。 |
| **蓝：Private Data Bus** | `max(t_publish_end, t_sender_confirmed, t_receiver_confirmed, t_pin) − t_upload_start` | 从开始上传文件，到发布、双方消息确认及pin完成的整体跨度。 |
| **绿：API Invoker** | `t_op_created − t_invoke_start` | 业务请求开始，到FireFly创建对应业务Operation。 |

绿色终点与红色起点使用**同一个换算后的Operation.created**，严格衔接、无重叠、无空隙。红色不是纯EVM执行时间。其他阶段可重叠，不能将四个阶段耗时相加作为总耗时。

## 四、黄色：时间戳如何获得

### 1. 被测接口与本地计时

```http
POST S/data/{D}/blob/publish
Content-Type: application/json

{}
```

- **开始时间**：脚本在发送该请求前调用单调时钟，保存至 `sample.ipfsPublishRequest.clock.rawStart`。
- **结束时间**：成功响应体完整读取后，脚本再次读取单调时钟，保存至 `sample.ipfsPublishRequest.clock.rawEnd`。
- **CID来源**：读取该响应的 `blob.public`，保存至 `sample.ipfsCid`。

因此黄色的两个计时时间戳**均由客户端记录**。FireFly返回的CID和操作状态用于判定本次发布确实成功，不是黄色开始、结束时间戳本身。

### 2. 成功状态与文件关联核验

| 接口 | 读取字段 | 校验规则 |
|---|---|---|
| `GET S/operations?type=sharedstorage_upload_blob&limit=1000` | `id`、`input.dataId` | 唯一匹配本次文件 `input.dataId == D`，取得PID。 |
| `GET S/operations/{PID}` | `status`、`output.payloadRef` | 等待 `status == Succeeded`，并要求 `output.payloadRef == CID`。 |
| `GET S/data/{D}` | `blob.public` | 要求与发布响应中的CID一致。 |
| `GET G/ipfs/{CID}` | 文件字节 | 与本轮上传字节一致。 |

**当前采用完整发布请求耗时，并在其后核验上传Operation成功。核验请求的耗时不追加到黄色中，也不把“第一次查询到Succeeded的本地时间”当作黄色终点。**

HTTP成功状态本身不足以证明后台完成。本次必须同时取得有效CID并通过上述核验；没有CID、任务失败或关联不符的轮次不能计为成功样本。当前实测接口会在发布结果可用时返回；若未来接口改为仅返回待处理任务，该接口的第一次响应不能继续沿用为完成终点。

例如，第1轮保存的客户端时间戳为：

```text
rawStart = 88478095.705644 ms
rawEnd   = 88478246.042967 ms
黄色     = 150.337323 ms ≈ 150.34 ms
```

这些是单调时钟读数，不是Unix时间戳。当前黄色不采用内部IPFS `/add` 日志耗时，也不采用 `Operation.updated − Operation.created` 或 `Batch.created − Message.created`。

## 五、绿色与红色：时间戳如何获得

### 1. 发起业务调用，记录绿色起点

```http
POST A/invoke/Message_1wswgqu_Send
Content-Type: application/json

{
  "input": {
    "instanceId": 0,
    "fireflyTranId": "本轮真实MID",
    "orderDetails": "本轮D"
  },
  "key": "页面所选签名地址"
}
```

脚本在请求发送前读取单调时钟，保存至 `sample.invokeRequest.clock.rawStart`，作为 `t_invoke_start`。

### 2. 获取Operation.created，作为红绿共用分界点

业务调用响应包含Operation的 `id`、`tx`、`created`。脚本再查询：

```http
GET S/operations/{OID}?fetchstatus=true
```

读取该Operation的 `created`，校验它的 `id`、`created` 与最初响应一致。原始响应保存于 `sample.invokeResponse`，查询结果保存于 `sample.operation`。

使用同一时间轴上的 `M(sample.operation.created)` 作为绿色终点和红色起点。业务HTTP响应完整返回的时间仍保留在 `invokeRequest.clock.rawEnd` 中，但不参与绿色终点计算。

### 3. 查询成功事件，获取红色终点

```http
GET S/events?tx={OTX}&limit=1000
```

必须同时满足：

```text
event.type      == "blockchain_invoke_op_succeeded"
event.reference == OID
event.tx        == OTX
```

取唯一匹配事件的 `created`，换算后作为红色终点。原始事件保存在 `sample.events`，具体关联ID和时间保存在 `sample.businessTimingBoundary`。

**红色终点使用事件内部的服务端created，不使用查询响应抵达客户端的时间，也不直接取事件列表的第一条。** 本次脚本默认每250ms轮询，轮询影响何时取得记录，不把额外的查询等待直接加到红色中。

另外，脚本通过 `GET S/blockchainevents?listener={ListenerID}&limit=1000` 核验 `MessageSent` 的 `output.fireflyTranId == MID`、`output.instanceId == 0` 及目标messageKey，防止错误关联到其他轮次。

## 六、蓝色：时间戳如何获得

### 1. 上传开始时间

当前调用的是页面新增上传功能所用的业务后端接口：

```http
POST B/bpmns/{BPMN记录ID}/bpmn-instances/{实例记录ID}/prepare-file-message
Content-Type: multipart/form-data

messageId: Message_1wswgqu
values: {}
orderDetails: 本轮文件
```

脚本在该请求发送前记录单调时间，保存至 `sample.fileUpload.clock.rawStart`，作为蓝色起点。这里的两个路径ID是业务数据库UUID，不是链上实例编号0。

该接口内部先调用 `POST S/data` 上传文件，再调用 `POST S/messages/private` 发送文件Message，最终返回 `fileIds.orderDetails` 和FireFly `messageId`。请求中的 `messageId=Message_1wswgqu` 是BPMN元素标识；响应中的messageId则是本轮FireFly消息UUID，两者含义不同。

蓝色覆盖这次准备请求中上传、消息发送以及必要的后端处理开销；没有在后端内部另设一个更晚的FireFly `/data` 请求起点。

### 2. 查询双方消息确认时间

| 接口 | 读取字段 | 用途 |
|---|---|---|
| `GET S/messages/{MID}` | `state`、`confirmed`、`batch` | 等待发送方 `state == confirmed` 且confirmed非空；confirmed换算为发送方确认时间，batch取得BID。 |
| `GET R/messages/{MID}` | `state`、`confirmed` | 等待接收方消息确认，confirmed换算为接收方确认时间。 |

两个confirmed均是API返回的服务端字段。脚本晚一些才查询到记录，不等于把查询时刻当作确认时间。记录分别保存在 `sample.messageFinal` 和 `sample.receiverMessage`。

### 3. 查询关联批次与pin操作

```http
GET S/batches/{BID}
GET S/operations?tx={BTX}&limit=1000
```

先读取Batch的 `tx.id` 得到BTX，再查询该批次事务下的操作，要求存在 `type == blockchain_pin_batch`，且所有关联操作均为 `Succeeded`。记录保存在 `sample.batch` 与 `sample.transportOperations`。

当前实现取已成功pin操作的 `updated`，换算后作为pin时间候选。**它是当前实现采用的完成时间代理，不是所有Operation通用的成功时间字段。** 必须结合pin成功状态、双方confirmed和相关记录核对；当updated未随完成更新时，不能将其解释成精确的实际完成时刻。

蓝色终点取发布响应完成、双方confirmed、pin时间四类候选中的最大值。因此，蓝色包含pin所需的链上存证等待；它不是仅测网络发送或文件传输。

### 4. 文件与链上状态核验

| 接口 | 校验内容 |
|---|---|
| `GET R/messages/{MID}/data` | 消息附件包含D，业务文件字段orderDetails也引用D。 |
| `GET R/data/{D}/blob` | 接收文件字节与本轮上传文件一致。 |
| `GET G/ipfs/{CID}` | IPFS文件字节与上传、接收端文件一致。 |
| `POST A/query/getExecutionSnapshot`，输入 `instanceId=0` | Message仍为ENABLED，最新 `messageFireflyTranIds` 为MID，其他状态数组不变。 |
| `POST A/query/currentInstanceId`，输入空对象 | 整次实验前后计数器相同，证明未创建新实例。 |

这些核验用于判定每轮是否有效。**接收文件读取和SHA-256核验的结束时间不另计入蓝色。** 蓝色使用消息确认和pin相关时间表示同步完成，不是网络抓包测得的“最后一个文件字节到达时刻”。

两个合约查询的完整请求体分别为：

```text
POST A/query/getExecutionSnapshot
{"input": {"instanceId": 0}}

POST A/query/currentInstanceId
{"input": {}}
```

## 七、时钟统一与结果保存

### 1. 服务端时间戳的换算

当前环境存在系统时间跳变，不能将FireFly ISO时间戳直接与客户端单调时钟相减。脚本每约5ms配对记录 `time.time_ns()` 与 `time.monotonic_ns()`，建立wall/monotonic对应关系。

对API返回的created、confirmed、updated等字段，脚本解析其UTC时间，在本轮采样范围内换算到单调时间轴。跨越时钟跳变的片段不用于插值；无法唯一确定映射时，校验失败，不对负值取绝对值或人为移动图形。

绿色终点和红色起点只换算一次并复用。所有图以本轮 `t_upload_start` 为0显示相对位置，再对各轮相对起止点计算均值。

### 2. 可复核的数据字段

| 保存位置 | 内容 |
|---|---|
| `sample.fileUpload.clock` | 蓝色客户端起点及准备请求完整结束时间。 |
| `sample.ipfsPublishRequest.clock` | 黄色客户端起止时间。 |
| `sample.ipfsUploadOperation`、`senderPublishedData`、`ipfsCid` | 黄色发布成功与CID关联核验依据。 |
| `sample.invokeRequest.clock` | 绿色客户端起点及完整HTTP响应时间。 |
| `sample.invokeResponse`、`operation`、`events` | 业务Operation创建时间与匹配成功事件的原始API记录。 |
| `sample.businessTimingBoundary` | 红绿共用分界点、成功事件ID及服务端原始时间。 |
| `sample.messageFinal`、`receiverMessage`、`transportOperations` | 蓝色服务端完成时间与成功状态依据。 |
| `sample.clockNormalization.clockPairs`、`events` | 时钟对应样本与各服务端时间戳的映射结果。 |
| `sample.stages` | 校准后的四阶段起止点和最终耗时；这是正式统计输入。 |

完整100轮记录位于 `results-100/results.json` 和各轮 `round-N/result.json`；`timings.csv` 保存逐段相对起止点，`summary.json` 保存均值、中位数及范围，`verification.json` 保存核验摘要。

## 八、与旧实验口径的区别

当前黄色保持完整FireFly发布请求口径，**不使用**以下替代区间：

- 内部IPFS `/add` 请求的单独耗时；
- `Operation.created → Operation.updated`；
- 首次轮询观察到Succeeded的时间；
- 旧脚本的 `Message.created → Batch.created`。

已找到的旧Fabric脚本虽然也通过FireFly API读取记录，但黄色使用的是最后一种区间，与当前口径不同。不能仅因都从FireFly取得信息，就认为统计边界相同。后续Fabric与Geth对比应统一使用本文的请求边界、成功判定和客户端实现。

## 九、100轮实验的纳入阈值与补测规则

按用户指定，正式数据集需包含100个核验成功且红色耗时不超过25秒的样本：

```text
先完整执行首批100轮，不在批内按红色阈值筛选。
批次结束后统一判断：红色 duration_ms <= 25000 纳入，>25000 整轮四阶段排除。
缺少N轮，则再完整执行N轮，批后统一筛选。
按批次循环，直到正式样本达到100轮。
```

判断对象是时钟校准后的红色阶段，即Operation.created到匹配业务成功事件之间的耗时；不对蓝、黄、绿另设筛除阈值，不将25秒以上的数值截断为25秒，也不只删除红色而保留同轮其他颜色。执行前后仍需验证节点可重复及文件、CID、事件一致。

样本筛选只在完成本次调用和全部核验后进行，超阈值也等待原交易、同步完成，不在旧事务尚未处理完时开始补测。若计时因系统时钟无法唯一映射而无效，则单列为无效计时、保存原始记录并补测；文件或业务核验失败则停止并保留故障信息，不自动当作成功样本。

`results.json`的samples及正式summary、timings.csv、均值图只包含纳入的100轮。按用户要求，现已删除attempts.json、attempts.csv、attempts目录及summary-all-attempts.json，仅保留有效轮次的完整数据与核验信息。报告需同时注明筛选条件、总尝试次数及各类排除数量。**正式结果是阈值筛选后的条件统计，不应描述为全部请求的未经筛选性能。**

本次通过run_batches.py自动完成“整批执行→统一筛选→计算缺额→整批补测”，没有人工逐轮决定。批次原始输出曾保存在batches/batch-NNN，现已按用户要求删除；最终统计只使用纳入样本。
