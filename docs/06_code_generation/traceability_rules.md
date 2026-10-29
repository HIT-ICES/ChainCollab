# 4.7 Traceability in Code Generation

## 1. 目标

可追踪性要求回答三个问题：

1. 某个 DSL 元素最终生成了哪段代码。
2. 某个 Go/Solidity 函数来自哪个 DSL 元素。
3. 静态验证工具如何根据这种映射检查一致性。

## 2. DSL element id 到代码命名的规则

### contract

- DSL `contract SupplyChain`
- Go：生成 `SmartContract` 主体及相关实例结构
- Solidity：生成合约名 `SupplyChain`

### participant

- DSL `participant Participant_0w6qkdf`
- Go：作为 MSP 权限检查常量和初始化字段来源
- Solidity：作为角色枚举、地址变量或参数名来源

### global

- DSL `Amount`
- Go：通常映射到 `instance.InstanceStateMemory.Amount`
- Solidity：映射到实例存储字段 `Amount`

### message

- DSL `Message_1wswgqu`
- Go：
  - `Message_1wswgqu_Send`
  - `Message_1wswgqu_Complete`
- Solidity：
  - `Message_1wswgqu_Send`
  - `Message_1wswgqu_Complete`

### gateway

- DSL `Gateway_11hmo2k`
- Go：`Gateway_11hmo2k`
- Solidity：`Gateway_11hmo2k`

### event

- DSL `Event_13pbqdz`
- Go：`Event_13pbqdz`
- Solidity：`Event_13pbqdz`

### businessrule

- DSL `Activity_0fbi09z`
- Go：
  - `CreateBusinessRule(..., "Activity_0fbi09z", ...)`
  - 规则执行相关函数
- Solidity：
  - `Activity_0fbi09z`
  - `Activity_0fbi09z_Continue`

## 3. 命名正规化规则

### Go

Go 生成器使用 `public_the_name()` 做首字母大写等正规化。

### Solidity

Solidity 生成器使用：

- `sanitize_identifier()`
- `sanitize_contract_name()`

把 DSL 标识符转成合法 Solidity 标识符。

## 4. 是否保留注释或 marker

当前实现更依赖“稳定命名”，而不是“专门的 traceability 注释 marker”。

具体表现：

- DSL 元素 ID 通常直接进入函数名、事件名、枚举名；
- `SetEvent` / Solidity `event` 里也直接保留 DSL 元素名；
- 这使静态工具无需依赖注释也能建立映射。

因此，当前 traceability 机制的核心不是 comment，而是：

- 同名映射；
- 规则化后缀；
- 稳定模板展开。

## 5. DSL 到 Go/Solidity 的主要映射模式

- `message X` -> `X_Send` / `X_Complete`
- `gateway X` -> `X`
- `event X` -> `X`
- `businessrule X` -> `X` 及 `X_Continue`
- `global V` -> 实例状态字段 `V`

## 6. 为什么这种设计有效

- 生成后代码仍保留 DSL 级术语；
- 审计者可以从代码直接回溯到源 DSL；
- 静态验证工具可以用命名匹配建立 trace graph；
- Go 与 Solidity 两个后端可以共享同一套 traceability 原则。
