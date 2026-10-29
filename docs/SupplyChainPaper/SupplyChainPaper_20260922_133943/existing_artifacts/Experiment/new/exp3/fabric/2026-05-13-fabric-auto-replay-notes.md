# 2026-05-13 Fabric 自动执行与 BPMN 链码问题排查记录

## 背景

本次工作的目标是在 `Experiment/new/exp3` 实验中补齐 Fabric 环境下的自动执行能力。此前实验里已经有 DSL 和 Geth/Solidity 路径执行逻辑，但 Fabric 侧还缺少一个可以自动创建实例、按已有路径输入逐步调用链码、等待链上状态变化并生成执行报告的脚本。

用户已经完成了 Fabric 环境启动，并在前端手动创建身份、跑通过一个案例，说明基础 Fabric/FireFly 环境本身可用。因此本次工作重点不是搭环境，而是识别当前 Fabric 环境、参考已有 Geth 自动执行逻辑，实现 Fabric 自动执行脚本，并验证它是否能复用已有路径文件中的输入。

约束如下：

- 不修改 `dsl` 内容。
- 不修改 `geth` / Solidity 自动执行逻辑。
- 最初只希望添加 Fabric 自动执行脚本和配置。
- 后续排查发现问题根因在 Fabric BPMN 链码生成逻辑，因此补了 Fabric Go 链码生成/后处理逻辑。

## 新增的 Fabric 自动执行文件

新增脚本：

```text
/root/code/ChainCollab/Experiment/new/exp3/scripts/replay_fabric_instance.py
```

新增配置：

```text
/root/code/ChainCollab/Experiment/new/exp3/fabric/fabric_replay_config.from_frontend_param.json
```

当前配置默认指向 VeryLow 路径：

```json
"execution_sequence_file": "/root/code/ChainCollab/Experiment/new/exp3/solidity/SupplyChainPaper/paths/SupplyChainPaper_auto_path_004/execution_sequence.json"
```

直接执行方式：

```bash
cd /root/code/ChainCollab/Experiment/new/exp3
python3 scripts/replay_fabric_instance.py --config fabric/fabric_replay_config.from_frontend_param.json
```

也可以临时指定其他路径：

```bash
python3 scripts/replay_fabric_instance.py \
  --config fabric/fabric_replay_config.from_frontend_param.json \
  --sequence-file /root/code/ChainCollab/Experiment/new/exp3/solidity/SupplyChainPaper/paths/SupplyChainPaper_auto_path_001/execution_sequence.json
```

## Fabric 配置文件字段说明

当前 Fabric 配置的关键字段包括：

```json
{
  "firefly_core_url": "http://127.0.0.1:5001",
  "event_core_urls": [
    "http://127.0.0.1:5000",
    "http://127.0.0.1:5001"
  ],
  "namespace": "default",
  "api_name": "SupplyChainPaper-45a262",
  "chaincode": "SupplyChainPaper",
  "default_signer": "...",
  "create_instance_signer": "",
  "participant_signers": {
    "Participant_09cjol2": "",
    "Participant_0sa2v7d": "",
    "Participant_0w6qkdf": "",
    "Participant_19j1e3o": "",
    "Participant_19mgbdn": ""
  },
  "create_instance_params": {},
  "execution_sequence_file": "..."
}
```

含义：

- `firefly_core_url`：实际发起 Fabric invoke/query 的 FireFly Core 地址。
- `event_core_urls`：监听 `InstanceCreated` 等 Fabric 事件的 FireFly Core 地址列表。实际测试时，调用 core 和接收事件的 core 不一定是同一个，因此这里支持多个 core。
- `api_name`：FireFly 中注册的 Fabric 合约 API 名称。
- `chaincode`：Fabric 链码名。
- `default_signer`：默认签名身份。
- `participant_signers`：按参与者配置 signer。当前可以留空，脚本会从 `create_instance_params` 中的 participant `x509` 字段推导 signer。
- `create_instance_params`：前端 CreateInstance 使用的初始化参数，也就是 `initParametersBytes` 中 JSON 反序列化后的对象。
- `execution_sequence_file`：已有路径中的执行序列文件。脚本会自动从这里读取每一步 message 的 payload。

## create_instance_params 的来源

用户从前端拿到了如下结构：

```python
param = {
  "Participant_0w6qkdf": {
    "msp": "...",
    "attributes": {},
    "isMulti": False,
    "multiMaximum": 0,
    "multiMinimum": 0,
    "x509": "..."
  },
  "...": {},
  "Activity_0rm8bkp_DecisionID": "Decision_0zwjfyy",
  "Activity_0rm8bkp_ParamMapping": {
    "numberOfUnits": "numberOfUnits",
    "urgent": "urgent",
    "supplierReputation": "supplierReputation",
    "finalPriority": "finalPriority"
  },
  "Activity_0rm8bkp_Content": "<DMN XML>"
}
```

这部分被整理到了配置文件的：

```json
"create_instance_params": { ... }
```

注意 JSON 中布尔值必须是小写：

```json
true
false
```

不能写 Python 风格：

```python
True
False
```

`create_instance_params` 的作用只是创建 BPMN 实例，包括参与者身份绑定、DMN 内容、DMN 参数映射等。它不是每一步业务 message 的输入来源。

## 执行路径输入的来源

Fabric 自动执行脚本当前不是从 `dsl` 目录实时读取输入，而是从已有路径的：

```text
solidity/.../execution_sequence.json
```

读取每一步 message 的 payload。

例如当前默认路径：

```text
/root/code/ChainCollab/Experiment/new/exp3/solidity/SupplyChainPaper/paths/SupplyChainPaper_auto_path_004/execution_sequence.json
```

其中关键输入是：

```json
{
  "Message_0rwz1km": {
    "requestId": 1,
    "numberOfUnits": 99,
    "urgent": true
  },
  "Message_0hpha6h": {
    "requestId": 1,
    "supplierReputation": 2
  }
}
```

对应业务结果：

```text
numberOfUnits = 99
urgent = true
supplierReputation = 2
=> finalPriority = VeryLow
=> Message_0d2xte5
```

另一个路径 `SupplyChainPaper_auto_path_001` 的关键输入是：

```json
{
  "Message_0rwz1km": {
    "requestId": 1,
    "numberOfUnits": 99,
    "urgent": true
  },
  "Message_0hpha6h": {
    "requestId": 1,
    "supplierReputation": 3
  }
}
```

对应业务结果应该是：

```text
numberOfUnits = 99
urgent = true
supplierReputation = 3
=> finalPriority = Low
=> Message_1oxmq1k
```

因此脚本是否走 VeryLow 或 Low，不是脚本自己猜，而是由 `execution_sequence_file` 指向的已有路径输入决定。

## Fabric 自动执行脚本的执行逻辑

`replay_fabric_instance.py` 的核心流程如下：

1. 读取 Fabric 配置。
2. 发现 FireFly 中注册的 Fabric 合约 API。
3. 获取 Fabric FFI/interface，构建方法表。
4. 使用 `create_instance_params` 调用：

   ```text
   CreateInstance(initParametersBytes)
   ```

5. 等待 `InstanceCreated` 链上事件，并取得 `InstanceID`。
6. 读取 `execution_sequence_file`。
7. 对每一步执行：

   - 等待目标 element 变成 READY。
   - 根据 Fabric FFI 构造 invoke payload。
   - 合并 execution sequence 中的 payload。
   - 选择 signer。
   - 调用 FireFly invoke API。
   - 等待 FireFly operation 成功。
   - 查询链上 snapshot。

8. 对 `businessRule` 做特殊处理：

   - 先调用 `Activity_xxx`。
   - 如果环境中的 DMN listener 自动执行了 `Activity_xxx_Continue`，脚本检测到 DONE 后不再重复调用。
   - 如果没有自动 Continue，则脚本手动调用 `Activity_xxx_Continue`，并传入 DMN XML。

9. 成功后输出 JSON 和 Markdown 报告。

## 已验证成功的 Fabric 自动执行

使用 `SupplyChainPaper_auto_path_004` 路径执行成功：

```bash
python3 scripts/replay_fabric_instance.py \
  --config fabric/fabric_replay_config.from_frontend_param.json \
  --sequence-file /root/code/ChainCollab/Experiment/new/exp3/solidity/SupplyChainPaper/paths/SupplyChainPaper_auto_path_004/execution_sequence.json
```

结果：

```text
Replay succeeded.
Fabric instance id: 6
```

报告文件：

```text
/root/code/ChainCollab/Experiment/new/exp3/solidity/SupplyChainPaper/paths/SupplyChainPaper_auto_path_004/fabric_replays/replay_20260513_214424.json
/root/code/ChainCollab/Experiment/new/exp3/solidity/SupplyChainPaper/paths/SupplyChainPaper_auto_path_004/fabric_replays/replay_20260513_214424.md
```

这条路径预期就是 VeryLow：

```text
supplierReputation = 2
=> finalPriority = VeryLow
=> Message_0d2xte5
```

## 发现的问题：auto_path_001 输入与 Fabric 实际分支不一致

测试 `SupplyChainPaper_auto_path_001` 时，路径输入是：

```json
{
  "numberOfUnits": 99,
  "urgent": true,
  "supplierReputation": 3
}
```

根据 DSL/Geth 语义，这应该得到：

```text
finalPriority = Low
=> Message_1oxmq1k
```

但 Fabric 实际执行后，链上激活的是：

```text
Message_0d2xte5 READY
Message_1oxmq1k INACTIVE
```

也就是 Fabric 实际走了：

```text
finalPriority = VeryLow
=> Message_0d2xte5
```

当时脚本报错：

```text
ReplayError: execution_sequence[12] target Message_1oxmq1k did not become READY
```

这个错误不是脚本随机失败，而是脚本发现：

```text
路径期待 Message_1oxmq1k READY
链上实际 Message_0d2xte5 READY
```

即路径语义与 Fabric 链上语义不一致。

## DMN 规则本身的预期

用户提供的 DMN 中，业务规则大致是：

第一层决策：

```text
numberOfUnits < 100
=> initialPriority = Low
```

第二层决策：

```text
initialPriority = Low 且 supplierReputation < 3
=> finalPriority = VeryLow

initialPriority = Low 且 supplierReputation >= 3
=> finalPriority = Low
```

因此：

```text
numberOfUnits = 99
urgent = true
supplierReputation = 2
=> VeryLow
```

而：

```text
numberOfUnits = 99
urgent = true
supplierReputation = 3
=> Low
```

所以 `auto_path_001` 走到 VeryLow 是不正常的。

## 根因定位

排查 Fabric 参考链码后发现，原本生成出来的 BPMN Fabric Go 链码存在问题。

FireFly FFI/interface 中 `Message_0hpha6h_Send` 确实声明了业务参数：

```json
{
  "name": "Message_0hpha6h_Send",
  "params": [
    { "name": "InstanceID", "schema": { "type": "string" } },
    { "name": "FireFlyTran", "schema": { "type": "string" } },
    { "name": "requestId", "schema": { "type": "number" } },
    { "name": "supplierReputation", "schema": { "type": "number" } }
  ]
}
```

但旧的 Go 链码 Send 方法实际类似：

```go
func (cc *SmartContract) Message_0hpha6h_Send(
    ctx contractapi.TransactionContextInterface,
    instanceID string,
    fireflyTranID string,
) error {
    ...
    cc.ChangeMsgFireflyTranID(ctx, instance, fireflyTranID, msg.MessageID)
    cc.ChangeMsgState(ctx, instance, "Message_0hpha6h", COMPLETED)
    ...
}
```

它没有接收：

```go
requestId int
supplierReputation int
```

也没有写入：

```go
globalMemory.RequestId = requestId
globalMemory.SupplierReputation = supplierReputation
```

同样，`Message_0rwz1km_Send` 也没有把：

```text
numberOfUnits
requestId
urgent
```

写入 `StateMemory`。

而业务规则 Continue 的逻辑是从 `StateMemory` 中读取参数：

```go
globalVariable, _err := cc.ReadGlobalVariable(ctx, instanceID)
...
realParamMapping[key] = field.Interface()
```

因此问题链条是：

```text
execution_sequence.json 里有 supplierReputation = 3
-> 自动脚本把 supplierReputation = 3 传给 FireFly invoke
-> BPMN Fabric 链码没有把 supplierReputation 写入 StateMemory
-> Activity_0rm8bkp_Continue 从 StateMemory 读到默认值 0
-> DMNEngine 收到 supplierReputation = 0
-> DMN 正常计算出 VeryLow
-> Gateway_0ep8cuh 激活 Message_0d2xte5
-> 与 auto_path_001 预期 Message_1oxmq1k 不一致
```

结论：

```text
不是 DMN 链码的问题。
不是 Fabric 自动脚本读取路径的问题。
根因是 BPMN Fabric 链码生成逻辑没有把 message payload 写入 StateMemory。
```

DMN 链码只是按 BPMN 链码传给它的参数计算。

## 正确的 Fabric BPMN + DMN 调用链

修复后，正确逻辑应该是：

```text
1. 自动脚本读取 execution_sequence.json
2. 调用 Fabric/FireFly 的 Message_xxx_Send
3. Message_xxx_Send 接收 message payload 参数
4. BPMN Fabric 链码把这些参数写入 StateMemory
5. 执行业务规则 Activity_xxx
6. Activity_xxx_Continue 从 StateMemory 取 DMN 输入
7. 调用 DMNEngine 链码
8. DMNEngine 返回 output
9. BPMN Fabric 链码把 DMN output 写回 StateMemory
10. Gateway 根据 StateMemory 里的结果选择分支
```

以本案例为例：

```text
Message_0rwz1km_Send 接收:
  numberOfUnits = 99
  requestId = 1
  urgent = true

写入:
  StateMemory.NumberOfUnits = 99
  StateMemory.RequestId = 1
  StateMemory.Urgent = true
```

然后：

```text
Message_0hpha6h_Send 接收:
  requestId = 1
  supplierReputation = 3

写入:
  StateMemory.RequestId = 1
  StateMemory.SupplierReputation = 3
```

之后：

```text
Activity_0rm8bkp_Continue
```

从 `StateMemory` 取到：

```json
{
  "numberOfUnits": 99,
  "urgent": true,
  "supplierReputation": 3
}
```

调用：

```text
DMNEngine:v1
```

得到：

```text
finalPriority = Low
```

最后：

```text
Gateway_0ep8cuh
=> Message_1oxmq1k
```

## 已完成的修复

修复 1：Go 链码生成器

文件：

```text
/root/code/ChainCollab/src/newTranslator/CodeGenerator/b2cdsl-go/b2cdsl_go/__init__.py
```

新增逻辑：

- 解析 message schema。
- 找到 schema 字段和全局变量 `StateMemory` 字段之间的对应关系。
- 为 `Message_xxx_Send` 生成业务参数。
- 在 Send 方法中把参数写入 `StateMemory`。

生成后的 `Message_0hpha6h_Send` 应类似：

```go
func (cc *SmartContract) Message_0hpha6h_Send(
    ctx contractapi.TransactionContextInterface,
    instanceID string,
    fireflyTranID string,
    requestId int,
    supplierReputation int,
) error {
    ...
    cc.ChangeMsgFireflyTranID(ctx, instance, fireflyTranID, msg.MessageID)
    cc.ChangeMsgState(ctx, instance, "Message_0hpha6h", COMPLETED)

    globalMemory, readGlobalError := cc.ReadGlobalVariable(ctx, instanceID)
    if readGlobalError != nil {
        fmt.Println(readGlobalError.Error())
        return readGlobalError
    }
    globalMemory.RequestId = requestId
    globalMemory.SupplierReputation = supplierReputation
    setGlobalError := cc.SetGlobalVariable(ctx, instance, globalMemory)
    if setGlobalError != nil {
        fmt.Println(setGlobalError.Error())
        return setGlobalError
    }
    ...
}
```

生成后的 `Message_0rwz1km_Send` 应类似：

```go
func (cc *SmartContract) Message_0rwz1km_Send(
    ctx contractapi.TransactionContextInterface,
    instanceID string,
    fireflyTranID string,
    numberOfUnits int,
    requestId int,
    urgent bool,
) error {
    ...
    globalMemory.NumberOfUnits = numberOfUnits
    globalMemory.RequestId = requestId
    globalMemory.Urgent = urgent
    ...
}
```

修复 2：全局变量赋值模板缩进

文件：

```text
/root/code/ChainCollab/src/newTranslator/CodeGenerator/b2cdsl-go/templates/actions/set_global_variable.go.jinja
```

作用：

- 让生成出来的 Go 代码缩进更正常。
- 方便 `gofmt` 后保持一致。

修复 3：旧链码 package 时的后处理兼容

文件：

```text
/root/code/ChainCollab/src/backend/apps/core/services/chaincode_postprocess.py
```

新增逻辑：

- 从 FFI 中读取 `Message_xxx_Send` 的参数。
- 对旧的 Go 链码 Send 方法补参数签名。
- 在 Send 方法状态变更后插入 `StateMemory` 写入逻辑。

这样即使 BPMN 记录里已经存着旧的 `chaincodeContent`，只要重新 package，也可以通过 FFI 后处理补上 message payload 写入逻辑。

修复 4：调用后处理时传入 FFI

文件：

```text
/root/code/ChainCollab/src/backend/apps/core/services/new_translator.py
/root/code/ChainCollab/src/backend/apps/core/routes/bpmn/views.py
```

作用：

- 新生成链码时，把 `ffi_content` 传给后处理。
- 重新 package 旧 BPMN 链码时，也把 `ffiContent` 传给后处理。

## 验证情况

Python 编译检查已通过：

```bash
python3 -m py_compile \
  /root/code/ChainCollab/src/backend/apps/core/services/chaincode_postprocess.py \
  /root/code/ChainCollab/src/backend/apps/core/services/new_translator.py \
  /root/code/ChainCollab/src/backend/apps/core/routes/bpmn/views.py \
  /root/code/ChainCollab/src/newTranslator/CodeGenerator/b2cdsl-go/b2cdsl_go/__init__.py
```

使用 `SupplyChainPaper.b2c` 本地生成临时代码，并用 `gofmt` 验证关键输出：

```bash
gofmt -w /tmp/supplychainpaper_smartcontract.go
```

确认生成代码包含：

```text
Message_0hpha6h_Send(..., requestId int, supplierReputation int)
globalMemory.RequestId = requestId
globalMemory.SupplierReputation = supplierReputation
```

以及：

```text
Message_0rwz1km_Send(..., numberOfUnits int, requestId int, urgent bool)
globalMemory.NumberOfUnits = numberOfUnits
globalMemory.RequestId = requestId
globalMemory.Urgent = urgent
```

## 重要注意事项

已经部署到 Fabric 上的旧链码不会自动变化。

本次修复改的是：

```text
链码生成逻辑
链码 package 前的后处理逻辑
```

因此必须重新生成或重新 package/deploy BPMN Fabric 链码后，链上行为才会改变。

如果继续使用已经部署的旧链码，`auto_path_001` 仍可能继续走 VeryLow，因为链上旧代码仍不会保存 message payload。

## 建议的后续验证步骤

1. 重新生成或重新 package/deploy `SupplyChainPaper` 的 Fabric BPMN 链码。

2. 确认 FireFly interface 中 `Message_0hpha6h_Send` 仍包含：

   ```text
   requestId
   supplierReputation
   ```

3. 跑 VeryLow 路径：

   ```bash
   cd /root/code/ChainCollab/Experiment/new/exp3
   python3 scripts/replay_fabric_instance.py \
     --config fabric/fabric_replay_config.from_frontend_param.json \
     --sequence-file /root/code/ChainCollab/Experiment/new/exp3/solidity/SupplyChainPaper/paths/SupplyChainPaper_auto_path_004/execution_sequence.json
   ```

   预期：

   ```text
   supplierReputation = 2
   => finalPriority = VeryLow
   => Message_0d2xte5
   => replay succeeded
   ```

4. 跑 Low 路径：

   ```bash
   python3 scripts/replay_fabric_instance.py \
     --config fabric/fabric_replay_config.from_frontend_param.json \
     --sequence-file /root/code/ChainCollab/Experiment/new/exp3/solidity/SupplyChainPaper/paths/SupplyChainPaper_auto_path_001/execution_sequence.json
   ```

   预期：

   ```text
   supplierReputation = 3
   => finalPriority = Low
   => Message_1oxmq1k
   => replay succeeded
   ```

5. 如果 `auto_path_001` 仍走 VeryLow，则继续检查：

   - 实际部署的链码是否已经是新生成版本。
   - FireFly API 是否仍绑定旧链码版本。
   - `Message_0hpha6h_Send` 链码方法签名是否真正包含 `supplierReputation`。
   - `Activity_0rm8bkp_Continue` 调 DMN 前读取的 `StateMemory.SupplierReputation` 是否为 3。

## 当前结论

Fabric 自动执行脚本本身已经可以使用，并且已经验证过 `auto_path_004` 可以完整执行成功。

今天发现的分支不一致问题，核心原因是：

```text
原本生成的 BPMN Fabric 链码没有把 message payload 写入 StateMemory。
```

因此：

```text
不是 DMN 链码问题。
不是路径文件没有参数。
不是自动执行脚本没有读取路径输入。
```

正确修复方向是：

```text
修复 BPMN Fabric 链码生成/后处理逻辑，
使 Message_xxx_Send 接收并保存业务输入，
然后 Activity_xxx_Continue 才能把正确参数传给 DMNEngine。
```

