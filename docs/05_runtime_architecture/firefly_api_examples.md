# 5.2 FireFly API Examples

## 1. 操作映射表

| B2CDSL operation | FireFly-level operation | Fabric invocation | Geth transaction |
| --- | --- | --- | --- |
| `CreateInstance` | `CreateInstance` | chaincode invoke | contract function |
| `Message_1wswgqu_Send` | `Message_1wswgqu_Send` | chaincode invoke | contract transaction |
| `Gateway_11hmo2k` | `Gateway_11hmo2k` | chaincode invoke | contract transaction |
| `Activity_0fbi09z` | `Activity_0fbi09z` | chaincode invoke / rule trigger | contract transaction |
| `Activity_0fbi09z_Continue` | `Activity_0fbi09z_Continue` | continuation invoke | callback continuation transaction |

## 2. Fabric 侧实际调用样例

以下调用形态来自 `Experiment/NoiseExperiment/invoker.py` 和保存的实验日志。

### 2.1 FireFly invoke 请求

```http
POST /api/v1/namespaces/default/apis/purcha/invoke/Message_0q9hvem_Send
Content-Type: application/json
```

```json
{
  "input": {
    "InstanceID": "31",
    "FireFlyTran": "123",
    "orderContent": "Sample Order Content",
    "productAvalibale": false
  },
  "key": "Mem2.org.comMSP::x509::CN=user2,OU=client::CN=ca.mem2.org.com,OU=Fabric,O=mem2.org.com,ST=North Carolina,C=US"
}
```

### 2.2 FireFly 返回结果

```json
{
  "id": "aeb8db6c-ee50-4a42-ae70-ee83f9a9619d",
  "namespace": "default",
  "tx": "58330b4f-0bbc-4e99-a0cc-ae32d6e46f5f",
  "type": "blockchain_invoke",
  "status": "Pending",
  "plugin": "fabric"
}
```

### 2.3 含义

- 上层只指定 `methodName` 和 `input`。
- `key` 标识 Fabric 侧调用身份。
- FireFly 再把它路由到具体 `channel + chaincode`。

## 3. Geth 侧统一调用样例

仓库中对 Ethereum/Geth 的 FireFly API 注册逻辑已实现于：

- `src/front/src/views/BPMN/Translation/BpmnDetail/index.tsx`
- `src/front/src/api/executionAPI.ts`

### 3.1 注册后的统一调用路径

```http
POST /api/v1/namespaces/default/apis/SupplyChain-eth123/invoke/Message_1wswgqu_Send
Content-Type: application/json
```

### 3.2 代表性请求体

```json
{
  "input": {
    "instanceId": 1,
    "fireflyTranId": "ff-tx-001",
    "order": "PO-001",
    "amount": 320
  }
}
```

说明：

- 这里的结构是代表性示例，依据来源是统一 invoke API 设计和 Solidity 生成函数签名。
- 实际 signer/identity 绑定由 FireFly Ethereum 连接配置决定。

## 4. Fabric/Geth 参数转换

### Fabric

- 多用 `InstanceID`
- 身份通常经 `key` 指定
- 后端落到 chaincode 参数和 MSP 身份

### Geth

- 多用 `instanceId`
- 身份通常依赖链上账户 / FireFly signer
- 后端落到 Solidity 函数参数与 `msg.sender`

因此统一层做的不是“参数完全相同”，而是：

- 操作名对齐
- 语义字段对齐
- 平台特定字段在注册/路由层吸收

## 5. 论文里建议怎么写

可以把 FireFly 的作用概括为：

> FireFly 为生成应用暴露统一业务操作接口。上层执行器只需调用同一套 operation 名称，FireFly 再依据注册时的 `location` 将其路由到 Fabric chaincode 或 Geth contract。
