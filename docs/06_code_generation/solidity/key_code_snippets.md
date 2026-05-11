# 4.6 B2CDSL to Solidity/Geth Contract

完整生成结果见 [generated_contract_example.sol](/home/shenxz-lab/code/ChainCollab/docs/06_code_generation/solidity/generated_contract_example.sol)。

## 1. storage variable

Solidity 版本将 DSL `globals` 和元素状态映射为合约存储。  
例如，全局变量会进入实例状态结构，消息/网关/事件/规则也会各自对应状态槽位。

语义：

- DSL 中的共享业务状态在 Geth/EVM 上表现为持久化 storage。
- 后续所有 `require`、分支判断和回调处理都基于这些状态槽位。

## 2. role / address

参与方在 Solidity 中映射为地址和组织标识，而不是 MSP：

- DSL `participant` -> 地址参数 / 角色枚举 / 角色槽位
- 调用时通过 `msg.sender` 等信息进行校验

这与 Fabric 的最大差异之一，就是身份模型从 “证书组织” 转为 “地址账户”。

## 3. public function

生成器会为消息和规则生成公开方法，例如：

- `Message_1wswgqu_Send`
- `Message_1wswgqu_Complete`
- `Activity_0fbi09z`
- `Activity_0fbi09z_Continue`

语义：

- `Send` / `Complete` 落地消息双阶段推进。
- 规则节点拆成“发起请求”和“回调继续”两个阶段。

## 4. require

Solidity 使用 `require(...)` 做权限与状态检查，例如：

- 调用者是否是正确参与方；
- 当前元素是否处于可执行状态；
- 并行 join 的前驱是否均已完成。

语义：

- DSL 的身份约束和状态可执行性，在 EVM 上以 `require` 落地。

## 5. event

合约生成中保留了大量事件，例如：

- `BusinessRuleRequested`
- `BusinessRuleCompleted`
- 各类 message/gateway/event 完成事件

语义：

- 它们替代 Fabric 的 `SetEvent`；
- 也是 traceability 和链外监听的重要机制。

## 6. state update

Solidity 版本同样把 flow 语义翻译为状态更新：

- 当前元素完成；
- 后继元素启用；
- 必要时写回全局变量；
- 必要时发出事件。

## 7. businessrule 外部调用

Solidity 模板中保留了 DMN 外部调用接口：

```solidity
function requestDMNDecision(...)
```

并在规则函数中发起请求：

```solidity
bytes32 requestId = dmnLite.requestDMNDecision(...);
emit BusinessRuleRequested(instanceId, BusinessRuleKey.Activity_0fbi09z, requestId);
```

语义：

- EVM 版本不直接本地执行 DMN；
- 而是通过外部适配层/Oracle 式接口发起决策请求。

## 8. callback / fulfill

规则节点的第二阶段通常由回调方法完成，例如：

- `Activity_0fbi09z_Continue`

语义：

1. 外部系统完成 DMN 求值；
2. 回调继续方法写回输出变量；
3. 规则节点置为完成；
4. 启动下游 gateway 或消息。

这正是 Solidity 版本与 Fabric 版本在决策执行形态上的显著差异。

## 9. Solidity 生成器与模板位置

- 生成器代码：`solidity_generator_code/__init__.py`
- 模板目录：`solidity_templates/`
- 主模板：`solidity_templates/contract.sol.jinja`

## 10. Solidity 合约如何部署和调用

### 部署

1. 由 B2CDSL 生成 `generated_contract_example.sol`。
2. 在 Solidity 工程中编译。
3. 部署到 Geth/兼容 EVM 网络。
4. 初始化参与方地址、DMN/Oracle 适配合约地址等配置。

### 调用

1. 参与方按流程调用 `*_Send` / `*_Complete`。
2. BusinessRule 节点先发出请求，再由外部回调 `*_Continue`。
3. 链外监听事件，以获得执行轨迹和回调时机。

这说明 Solidity 版本更偏“合约状态机 + 链外异步回调协同”。
