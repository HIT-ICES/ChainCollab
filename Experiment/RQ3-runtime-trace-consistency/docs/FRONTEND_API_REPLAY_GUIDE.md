# Exp3 Frontend API Replay Guide

## 目的

本文档记录一次已经实际跑通的“前端模拟执行”全流程，目标是让后续对话中的 Codex 能够快速接管，并在**不修改业务源码**的前提下，重新完成一轮：

1. 身份准备
2. BPMN / DMN 上传
3. Solidity 生成
4. Ethereum 合约部署
5. FireFly 注册
6. 创建实例
7. 通过 FireFly API 模拟前端执行
8. 验证最终状态


## 本次实验结论

- 当前工作区内，Ethereum / Geth / FireFly 环境可用
- 当前工作区内，没有可直接使用的 Fabric 环境，因此这次没有做 `Fabric vs Solidity` 的真实双链对比
- 已实际跑通 1 条包含 DMN 的 Ethereum 前端模拟执行路径
- 已补回 BPMN 的 `svgContent`，前端执行页现在应显示真实流程图，而不是占位名称卡片


## 使用案例

- BPMN: `/root/code/ChainCollab/Experiment/BPMNwithDMNcase/Hotel Booking.bpmn`
- DMN: `/root/code/ChainCollab/Experiment/BPMNwithDMNcase/Hotel Booking.dmn`

选这个案例的原因：

- 结构比较小
- 同时包含 choreography message、gateway、business rule
- 可以明确走到 DMN 分支


## 关键对象

以下对象是这次实际运行时生成或确认过的：

### 环境

- Ethereum environment id: `cdaaec0c-65f9-40e5-99e0-f07cc5635365`
- Ethereum environment name: `Forge-IGG`
- consortium id: `5f847a8d-a064-4c47-b54a-80b0a682151d`
- organization id: `7e533a1d-52b1-4a7c-9485-6e175fe5e9dd`

### FireFly cores

- Core: `127.0.0.1:5000`
- System/Core used for contract API: `127.0.0.1:5001`
- Aegis: `127.0.0.1:5002`
- Ops: `127.0.0.1:5003`

### 关键合约

- Identity contract address: `0x379f21788d0e647ea96b8309b3ca7b2bb1f6cee8`
- DMN Lite address: `0x9fcf193d45cde39f5054098a0c621e8881de190a`

### 参与执行的 Ethereum identities

- `user1`
  - id: `2aabf969-e939-49a9-a4c9-2ae9d92065f0`
  - address: `0x921bb41f4d8a4d98ff80889eb25d68a7e71072a2`
  - membership: `23c3bff9-11de-47e0-a957-3d8d1321b1ee`

- 本次为实验创建的 identity
  - id: `4ff8106e-ca28-4c61-9311-df3d90fe48be`
  - address: `0xec04353a836cdc0cf0fda3cc12e45b925d11aa24`
  - membership: `99a020a1-56e5-44ef-a56a-1fb2f8d3c936`

### BPMN / DMN / Contract / Instance

- BPMN id: `47b44a19-a1ba-4a93-a717-e305ad3ba61f`
- BPMN name: `exp3_hotel_20260419_211245.bpmn`
- DMN id: `86d4b763-aee8-4f17-9d52-6e80a9727dcb`
- DMN name: `exp3_hotel_20260419_211245.dmn`
- deployed Ethereum contract id: `33e2fb0d-08ed-4f9f-bf03-d4d74c3f2625`
- deployed Ethereum contract address: `0x2ab748f6b69fc529640feab3960983ad6c543fa9`
- BPMN FireFly API:
  - `http://127.0.0.1:5001/api/v1/namespaces/default/apis/exp3_hotel_20260419_211245-33e2fb-47b44a-543fa9`
- DMN FireFly data id: `b261bd45-9084-486b-ae57-ac8126094731`
- DMN CID: `QmZrVrZ9otcpdyhgFBAJFyJxavt4bS2VNdSVsfdC7pGBoa`
- local BPMN instance id: `9a776b66-d22a-4e06-9136-b2fa29abe4bf`
- on-chain instance id: `0`


## 前提检查

开始前建议确认：

1. Django backend 在 `8000` 可访问
2. FireFly core `5001` 可访问
3. `system-geth-node` 容器在运行
4. Ethereum env `cdaaec0c-65f9-40e5-99e0-f07cc5635365` 状态仍是 `ACTIVATED`

可快速检查：

```bash
docker ps --format '{{.Names}}'
curl -s http://127.0.0.1:5001/api/v1/status
curl -s http://127.0.0.1:8000/api/v1/health || true
```


## JWT 获取方式

前端接口需要 JWT。历史对话里曾为用户 `logres` 生成过 token，但下次对话时很可能已过期，因此**不要复用旧 token**，而是重新生成。

示例：

```bash
cd /root/code/ChainCollab/src/backend
. venv/bin/activate
python manage.py shell -c "
from rest_framework_simplejwt.tokens import RefreshToken
from apps.core.models import User
u = User.objects.get(username='logres')
print(str(RefreshToken.for_user(u).access_token))
"
```

后文用 `${TOKEN}` 代替新生成的 token。


## 这次实际走通的流程

### 1. 创建或确认 Ethereum identity

接口：

- `POST /api/v1/ethereum_identities`

本次成功创建出：

- `0xec04353a836cdc0cf0fda3cc12e45b925d11aa24`

如果下次要重跑，可以直接重用现有 identity，也可以重新创建一个新的。


### 2. 上传 BPMN

接口：

- `POST /api/v1/consortiums/{consortium_id}/bpmns/_upload`

关键字段：

- `name`
- `bpmnContent`
- `svgContent`
- `participants`
- `consortiumid`
- `orgid`

说明：

- `bpmnContent` 必须是真实 BPMN XML
- `svgContent` 可以先给占位 SVG，但如果要让前端执行页显示正常流程图，后续必须补成真实 SVG


### 3. 上传 DMN

接口：

- `POST /api/v1/consortiums/{consortium_id}/dmns`

关键字段：

- `name`
- `dmnContent`
- `svgContent`
- `consortiumid`
- `orgid`


### 4. 绑定 BPMN 到 Ethereum 环境

接口：

- `PUT /api/v1/consortiums/{consortium_id}/bpmns/{bpmn_id}`

关键字段：

- `envId`
- `envType=ethereum`


### 5. 生成 Solidity

接口：

- `POST /api/v1/consortiums/{consortium_id}/bpmns/{bpmn_id}/generate`

预期结果：

- 返回 `dslContent`
- 返回 `chaincodeContent`
- 返回 `ffiContent`
- 返回 `executionLayout`


### 6. 安装 Ethereum 合约

接口：

- `POST /api/v1/consortiums/{consortium_id}/bpmns/{bpmn_id}/install-eth`

本次部署结果：

- contract address: `0x2ab748f6b69fc529640feab3960983ad6c543fa9`
- deployment tx hash: `0x913215dbee24f550ecf3d6cd9bbf0044fad36add5368617a8ec0e930b6bdd71b`


### 7. 注册合约到 FireFly

接口：

- `POST /api/v1/consortiums/{consortium_id}/bpmns/{bpmn_id}/register-eth`

本次结果：

- interface id: `951b9b65-c969-47f9-a3a9-acab1107b3ad`
- api id: `6ede48d8-fe8b-40a2-a72d-8c9b9ae65e7f`
- firefly_url:
  - `http://127.0.0.1:5001/api/v1/namespaces/default/apis/exp3_hotel_20260419_211245-33e2fb-47b44a-543fa9`


### 8. 上传 DMN 到 FireFly data manager

执行页的 Ethereum create-instance 流程依赖 DMN 先被存入 FireFly，并拿到 `CID`。

关键结果：

- firefly data id: `b261bd45-9084-486b-ae57-ac8126094731`
- CID: `QmZrVrZ9otcpdyhgFBAJFyJxavt4bS2VNdSVsfdC7pGBoa`

随后需要把它回写到 DMN 记录：

- `fireflyDataId`
- `cid`


### 9. createInstance

调用接口：

- `POST {bpmn_firefly_url}/invoke/createInstance`

本次使用的核心 payload 结构如下：

```json
{
  "input": {
    "params": {
      "identityContractAddress": "0x379f21788d0e647ea96b8309b3ca7b2bb1f6cee8",
      "dmnLiteAddress": "0x9fcf193d45cde39f5054098a0c621e8881de190a",
      "dmnEvalUrl": "http://cdmn-node1:5000/api/dmn/evaluate",
      "enforceBusinessRuleCaller": false,
      "Participant_1080bkg_account": "0xec04353a836cdc0cf0fda3cc12e45b925d11aa24",
      "Participant_1080bkg_org": "Atlas-IGG-Core",
      "Participant_0sktaei_account": "0x921bb41f4d8a4d98ff80889eb25d68a7e71072a2",
      "Participant_0sktaei_org": "Atlas-IGG-Aegis-IGG",
      "Activity_0b1f7uv": {
        "dmnCid": "QmZrVrZ9otcpdyhgFBAJFyJxavt4bS2VNdSVsfdC7pGBoa",
        "dmnHash": "0x854e1554b29d1afccd4d8a2bce5a8baa9dcb7bc680b2de7bfef59ace93600559",
        "decisionId": "decision_0tybghz",
        "callerRestricted": false,
        "allowedCaller": "0x0000000000000000000000000000000000000000"
      }
    }
  }
}
```

注意：

- FireFly `invoke` 返回 `202 Pending` 是正常的，不要误判为失败
- 应继续轮询 `currentInstanceId`
- 本次 `currentInstanceId` 从 `0` 变成 `1`
- 因此新的链上实例号是 `0`


### 10. 本地 BPMN instance 记录

接口：

- `POST /api/v1/bpmns/{bpmn_id}/bpmn-instances`
- `PATCH /api/v1/bpmns/{bpmn_id}/bpmn-instances/{bpmn_instance_id}`

本次最终记录：

- local instance id: `9a776b66-d22a-4e06-9136-b2fa29abe4bf`
- instance_chaincode_id: `0`


## 这次实际走的业务路径

本次不是随机执行，而是手动选了一条会经过 DMN 的成功分支：

1. `StartEvent_1jtgn3j`
2. `ExclusiveGateway_0hs3ztq`
3. `Message_045i10y_Send`
4. `Message_0r9lypd_Send`
5. `ExclusiveGateway_106je4z`
6. `Message_1em0ee4_Send`
7. `Message_1nlagx2_Send`
8. `EventBasedGateway_1fxpmyn`
9. `Message_104h2tt_Send`
10. `Activity_0b1f7uv`
11. `Activity_0b1f7uv_Continue`
12. `Gateway_1jhfnrm`
13. `Message_04ikf2n_Send`
14. `Gateway_1atxr3y`
15. `Message_0o8eyir_Send`
16. `Message_1ljlm4g_Send`
17. `Message_0m9p3da_Send`
18. `ExclusiveGateway_0nzwv7v`
19. `EndEvent_08edp7f`

关键输入选择：

- `confirm = true`
- `VIPpoints = 12001`
- DMN 输出应走 `VIPLevel == 3`
- `cancel = false`


## 最终成功判据

本次最终通过 `getExecutionSnapshot(instanceId=0)` 确认成功。

最终关键状态：

```json
{
  "businessRuleStates": ["3"],
  "eventStates": ["3", "0", "3", "0"],
  "gatewayStates": ["3", "3", "3", "3", "3", "3"]
}
```

解释：

- `businessRuleStates = ["3"]`
  - 说明 `Activity_0b1f7uv` 已完成
- `eventStates[2] = "3"`
  - 对应 `EndEvent_08edp7f`
- `gatewayStates` 全部为 `"3"`
  - 说明执行路径上的网关都已完成


## BPMN 图显示问题与修复

这次实验里，最初为了尽快打通上传-部署-执行链路，给 BPMN 上传了一个占位 `svgContent`，内容只是文件名文本，导致前端执行页虽然能执行，但“BPMN Diagram”区显示的是名字，而不是流程图。

后续已修复：

- 为 BPMN `47b44a19-a1ba-4a93-a717-e305ad3ba61f` 回写了真实 `svgContent`
- 当前 `svgContent` 长度约 `18704`
- 以 `<svg` 开头
- 包含 `data-element-id`

下次如果重新跑一轮，务必在上传后尽早补真实 SVG，避免前端只显示名字卡片。


## 下次重跑建议顺序

后续 Codex 如果要快速接管，推荐严格按下面顺序操作：

1. 检查 Docker / backend / FireFly / geth 是否活着
2. 重新生成 JWT，不要复用旧 token
3. 确认 Ethereum env、Identity contract、DMN Lite contract 仍然存在
4. 选用 `Hotel Booking.bpmn` / `Hotel Booking.dmn`
5. 创建或重用两个 Ethereum identities
6. 上传 BPMN / DMN
7. 绑定 BPMN 到 Ethereum env
8. 生成 Solidity
9. 安装合约
10. 注册 FireFly API
11. 上传 DMN 到 FireFly，拿到 CID 后回写到 DMN 记录
12. 调用 `createInstance`
13. 持续轮询 `currentInstanceId`
14. 创建本地 BPMN instance 记录，并写入 `instance_chaincode_id`
15. 用 `getExecutionSnapshot` 驱动动作
16. 验证最终状态
17. 如前端图异常，检查 `svgContent`


## 风险与注意事项

### 1. Token 过期

JWT 很容易失效。每次新对话都应现生成。

### 2. FireFly invoke 是异步的

`invoke` 的 `202 Pending` 是正常的，不是失败。要继续轮询链上状态。

### 3. 不要重复触发同一步

若后台自动脚本已经推进状态，再次调用同一步通常会收到：

- `message state not allowed`
- `gateway state not allowed`
- `business rule not waiting`

这通常不是系统坏了，而是状态已经前进。

### 4. Fabric 目前不可用

如果目标是做 `Fabric vs Solidity` 真正对比，必须先补可运行的 Fabric 环境。

### 5. 当前文档记录的是一次成功样本

对象 ID、地址、FireFly API 名称都可能在下次重跑时变化。真正重要的是：

- 调用顺序
- payload 结构
- 成功判据


## 建议保留的最小交接信息

如果下一次只想快速接管，至少先读取本文档中的这些部分：

1. `关键对象`
2. `JWT 获取方式`
3. `createInstance`
4. `这次实际走的业务路径`
5. `最终成功判据`
6. `BPMN 图显示问题与修复`


## 已提供的自动化脚本

如果你的前提是：

- BPMN 已经上传并部署完成
- FireFly API 已注册完成
- Ethereum identities 已手工创建完成

那么可以直接使用下面这个脚本自动完成：

- 绑定 participant / business rule
- `createInstance`
- 创建本地 BPMN instance 记录
- 轮询 `getExecutionSnapshot`
- 自动执行直到结束

脚本路径：

- `/root/code/ChainCollab/Experiment/new/exp3/scripts/replay_bound_eth_instance.py`

参数模板：

- `/root/code/ChainCollab/Experiment/new/exp3/replay_bound_eth_instance.template.json`

推荐用法：

1. 复制模板

```bash
cp /root/code/ChainCollab/Experiment/new/exp3/replay_bound_eth_instance.template.json \
   /root/code/ChainCollab/Experiment/new/exp3/replay_supplychain.json
```

2. 手工填写你自己的：

- `token`
- `consortium_id`
- `eth_environment_id`
- `bpmn_id`
- `default_signer`
- `create_instance_params`

执行阶段说明：

- 当前脚本已按“单一身份执行”方式调整
- 所有 message / event / gateway / business rule 的调用都会统一使用 `default_signer`
- `execution_signers` 可以留空，不再需要按节点分别配置 signer
- 如果你已经能从前端或抓包中直接拿到 `createInstance` 的 `params`，优先直接填到 `create_instance_params`
- 只有在拿不到完整 `params` 时，才需要改回脚本里原来的 `participant_bindings` / `business_rule_bindings` 组装模式
- 如果你已经有实验三 DSL 的步骤顺序，优先单独放到路径文件里
- 推荐把环境/实例配置和执行路径拆成两个文件：
  - 主配置：`replay_bound_eth_instance.template.json`
  - 路径文件：`shared/execution_sequence.template.json`
- 路径文件中的 `steps` 格式可直接沿用 DSL case 的 `steps`
- 这时脚本会只轮询当前目标节点，而不是扫描所有节点里谁先 ready
- `businessrule` 步骤会先执行 request，再等待同一节点进入 continue 阶段并自动调用 `_Continue`

3. 执行脚本

```bash
python /root/code/ChainCollab/Experiment/new/exp3/scripts/replay_bound_eth_instance.py \
  --config /root/code/ChainCollab/Experiment/new/exp3/replay_supplychain.json \
  --sequence-file /root/code/ChainCollab/Experiment/new/exp3/shared/execution_sequence.template.json
```

也可以把 token 放到命令行，覆盖配置里的 `token`：

```bash
python /root/code/ChainCollab/Experiment/new/exp3/scripts/replay_bound_eth_instance.py \
  --config /root/code/ChainCollab/Experiment/new/exp3/replay_supplychain.json \
  --sequence-file /root/code/ChainCollab/Experiment/new/exp3/shared/execution_sequence.template.json \
  --token "YOUR_JWT"
```

输出：

- 默认生成到 `exp3/outputs/eth_instance_replay/`
- 会产出一份 `.json` 报告和一份 `.md` 报告

注意：

- 这个脚本是“参数由你手工填”的模式，不会自动猜测你的业务绑定
- 更适合你现在说的目标：部署手工做，身份手工建，脚本只负责实例创建与执行自动化
