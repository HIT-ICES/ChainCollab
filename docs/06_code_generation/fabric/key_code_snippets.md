# 4.5 B2CDSL to Fabric Go Chaincode

完整生成结果见 [generated_chaincode_example.go](/home/shenxz-lab/code/ChainCollab/docs/06_code_generation/fabric/generated_chaincode_example.go)。

## 1. participant 权限检查

当前生成链码通过 Fabric 客户端身份信息检查调用者组织，例如：

```go
clientMSPID, err := ctx.GetClientIdentity().GetMSPID()
if err != nil {
    return fmt.Errorf("failed to get client MSPID: %v", err)
}
if clientMSPID != "Bulk_buyerMSP" {
    return fmt.Errorf("only Bulk_buyerMSP can invoke this method")
}
```

语义：

- DSL `participant.msp` 映射为链码运行时的组织身份约束。
- 这使 BPMN 中的参与方在链上落成“谁有权触发哪条消息”。

## 2. ledger state 读写

链码通过 `GetState` / `PutState` 维护流程实例：

```go
instanceAsBytes, err := ctx.GetStub().GetState(instanceID)
if err != nil {
    return err
}
err = ctx.GetStub().PutState(instanceID, instanceAsBytes)
if err != nil {
    return err
}
```

语义：

- DSL `globals`、元素状态和实例结构被固化到 ledger。
- 每次消息、网关、规则推进，都会更新实例状态。

## 3. message handler

生成器会为每个消息生成一对方法，例如：

- `Message_1wswgqu_Send`
- `Message_1wswgqu_Complete`

典型作用：

- `Send`：把消息置为待确认状态，并写入消息参数。
- `Complete`：把消息置为完成状态，并触发后续 flow。

## 4. gateway 分支

Exclusive gateway 的生成代码会读取全局变量并执行条件分支。  
其来源是 DSL 中类似下面的 flow：

```dsl
when gateway Gateway_11hmo2k completed
choose {
    if Deliver == true
    then enable Message_196q1fj;
    if Deliver == false
    then enable Event_0eoqvir;
}
```

语义：

- `Deliver` 来自 DSL `globals`。
- gateway 完成函数把条件判断落成 Go `if` 语句，并启用对应后继元素。

## 5. event emit

链码广泛使用 `stub.SetEvent(...)` 把状态推进暴露出去，例如：

```go
stub.SetEvent("Message_1wswgqu", []byte("Message has been done"))
stub.SetEvent("Gateway_11hmo2k", []byte("Gateway has been completed"))
stub.SetEvent("Event_13pbqdz", []byte("Event has been completed"))
```

语义：

- DSL 元素 ID 直接成为事件名。
- 这为链外监听、可视化和 traceability 提供了天然锚点。

## 6. businessrule 处理

BusinessRule 在 Fabric 版本中生成了显式构造与执行逻辑，例如：

```go
func (cc *SmartContract) CreateBusinessRule(ctx contractapi.TransactionContextInterface, instance *ContractInstance, BusinessRuleID string, DMNContent string, DecisionID string, ParamMapping map[string]string) (*BusinessRule, error)
```

以及对外部组件的调用：

```go
resJson, err = cc.Invoke_Other_chaincode(ctx, "DMNEngine:v1", "default", _args)
```

语义：

- DSL `businessrule` 被翻译为一个可持久化、可调用的规则实体。
- 决策执行并不内嵌在链码里，而是通过外部 `DMNEngine` 链码完成。

## 7. flow 状态更新

flow 语义在链码中表现为“完成当前元素后，更新后继元素状态”。  
例如，某消息完成后启用下一消息或网关。

这对应了 DSL 中的：

```dsl
when message Message_1wswgqu completed
then enable Message_1ajdm9l;
```

## 8. Go 生成器与模板位置

- 生成器代码：`go_generator_code/__init__.py`
- 模板目录：`go_templates/`
- 主模板：`go_templates/contract.go.jinja`

## 9. Go 链码如何部署和调用

当前文档建议按两层理解：

### 部署

1. 由 B2CDSL 生成 `generated_chaincode_example.go`。
2. 将其纳入 Fabric chaincode 工程。
3. 按 Fabric 常规流程完成打包、安装、审批、提交。

### 调用

1. 初始化合约实例。
2. 按消息顺序调用 `*_Send` / `*_Complete`。
3. 遇到 BusinessRule 时，调用对应规则函数并由 DMN 引擎返回结果。
4. 监听 `SetEvent` 事件，观察流程推进。

这说明 Fabric 版本更偏“链码编排 + 外部链码协同”。
