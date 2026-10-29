# Solidity 消息发送与接收确认

Solidity 的 BusinessRule 原已支持 request → WAITING_FOR_CONFIRMATION → Continue → COMPLETED。此前消息使用单次 Send → COMPLETED，没有用于启用两阶段消息确认的开关。

当前消息生成器默认与 Fabric 使用相同的两阶段思路：

| 调用 | 权限 | 前置状态 | 结果 |
| --- | --- | --- | --- |
| `<MessageID>_Send(instanceId, fireflyTranId, ...payload)` | 发送方身份 | ENABLED | 保存交易标识和消息参数，进入 WAITING_FOR_CONFIRMATION，发出 MessageSent；执行 DSL `sent` 动作 |
| `<MessageID>_Complete(instanceId)` | 接收方身份 | WAITING_FOR_CONFIRMATION | 进入 COMPLETED，发出 MessageCompleted，执行 DSL `completed` 动作 |

多实例参与方使用原有 identity registry 的组织鉴权；单实例参与方使用原有 account 地址鉴权。等待时重发、发送前确认、完成后再次发送/确认均被拒绝。Complete 不再次接收参数，也不改写 Send 保存的 fireflyTranId。

DSL 中 `sent` 与 `completed` 是不同触发条件，分别在 Send 和 Complete 阶段执行，与 Fabric 一致。现有 BPMN→B2CDSL 转换仍可能把普通后继写作 `when message ... sent`，这些后继仍在 Send 阶段启用；不能把新实现描述为所有后继都自动推迟到确认之后。并行汇合仍要求其消息前驱为 COMPLETED。

真实模板：

- `src/newTranslator/CodeGenerator/b2cdsl-solidity/templates/actions/message_send.sol.jinja`
- `src/newTranslator/CodeGenerator/b2cdsl-solidity/templates/actions/message_complete.sol.jinja`
- `templates/contract.sol.jinja` 新增 MessageCompleted 事件，其余 BusinessRule 逻辑保持原样。

execution layout 保留 `<MessageID>` → `_Send` 映射，并新增 `<MessageID>#complete` → `_Complete` 以及消息的 sendMethod/completeMethod 字段。前端 Ethereum 执行页在状态 2 且 ABI 存在 Complete 时显示 “Confirm receipt”；状态 1 仍调用 Send。接收权限由合约检查。

这是新生成合约的默认行为，无单阶段兼容开关。已部署合约不会自动更新；要使用新流程，需要重新生成 Solidity/ABI、重新部署或按既有部署流程更新合约，再建立使用新代码的实例。原合约 ABI 没有 Complete 时，前端不会显示无效确认入口。

生成器验证与本地 EVM 运行证据：`artifacts/SolidityMessageConfirmation_20261029/README.md`。没有对线上网络或既有实验部署进行修改。
