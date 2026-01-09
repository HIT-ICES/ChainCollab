# 以太坊身份映射系统设计方案（修订版）

## 1. 背景和目标

### 问题
- Geth网络中没有Fabric那种天然的组织(Organization)和用户(User)概念
- 需要在以太坊环境中实现类似Fabric的身份管理机制
- 利用FireFly的org和custom identity来建立组织与用户的映射关系

### 目标
- 设计并部署IdentityRegistry合约，维护组织和用户的映射关系
- **在创建BPMN实例时注册所有参与者身份到合约**
- **由WorkflowContract调用IdentityRegistry进行身份注册**
- 提供身份验证和权限控制能力

## 2. 架构设计

### 2.1 核心组件

1. **IdentityRegistry合约** - 链上身份映射注册表（独立部署）
2. **WorkflowContract** - 工作流合约（引用IdentityRegistry）
3. **前端应用** - 调用createInstance时传入身份信息
4. **API后端** - 提供身份数据准备和查询

### 2.2 合约关系

```
┌─────────────────────┐
│  IdentityRegistry   │ ← 独立部署，管理所有身份
│  (身份注册表)        │
└──────────▲──────────┘
           │ 调用
           │ registerIdentity()
┌──────────┴──────────┐
│  WorkflowContract   │ ← BPMN生成的合约
│  (工作流合约)        │   createInstance时注册身份
└─────────────────────┘
           ▲
           │ createInstance(params)
           │
    ┌──────┴──────┐
    │   前端调用   │
    └─────────────┘
```

### 2.3 数据模型

#### 链上数据结构（Solidity）
```solidity
Organization {
    string orgName;           // 组织名称（对应FireFly org）
    address orgAdmin;         // 组织管理员地址
    bool active;              // 是否激活
    uint256 memberCount;      // 成员数量
}

Identity {
    address identityAddress;  // 用户地址
    string fireflyIdentityId; // FireFly identity ID
    string orgName;           // 所属组织
    string customKey;         // FireFly custom key
    bool registered;          // 是否已注册
}

// WorkflowContract中增强的Participant结构
Participant {
    address account;
    string fireflyIdentityId;  // 新增
    string orgName;            // 新增
    bool isMulti;
    uint8 multiMaximum;
    uint8 multiMinimum;
}
```

#### 链下数据（Django Model）
已有的EthereumIdentity模型包含:
- firefly_identity_id
- eth_environment
- membership（对应组织）

## 3. 设计思路

### 3.1 身份注册流程

#### 方式1: 创建EthereumIdentity时同步注册（推荐）
1. 用户通过API创建EthereumIdentity
2. 系统调用FireFly API创建custom identity
3. **系统立即调用IdentityRegistry合约注册身份**
4. 保存映射关系到数据库

这是主要的身份注册方式，确保每个EthereumIdentity创建后立即在链上可验证。

#### 方式2: 其他合约调用注册（扩展）
- WorkflowContract或其他合约也可以调用IdentityRegistry
- 需要先授权：`identityRegistry.authorizeCaller(contractAddress)`
- 用于特殊场景，如批量注册或实例创建时的补充注册

### 3.2 合约授权机制

IdentityRegistry支持两种调用方式：

1. **Owner直接调用** - 通过Python客户端或后端服务调用
   ```python
   client.register_identity(address, firefly_id, org, key, from_address=owner)
   ```

2. **授权合约调用** - 其他智能合约调用
   ```solidity
   // 先授权
   identityRegistry.authorizeCaller(workflowContractAddress);

   // 然后WorkflowContract可以调用
   identityRegistry.registerIdentity(address, fireflyId, orgName, customKey);
   ```

### 3.3 组织管理

- 每个EthEnvironment对应多个ResourceSet
- 每个ResourceSet有自己的membership（组织）
- 组织信息通过IdentityRegistry合约统一管理

### 3.4 权限验证

合约提供验证函数:
- `isOrgMember(address, orgName)` - 检查是否为组织成员
- `getIdentityOrg(address)` - 获取地址所属组织
- 可在WorkflowContract中使用这些函数进行权限控制

## 4. 使用场景

### 场景1: 创建用户身份（主流程）
```
用户请求创建身份
    ↓
Django API (EthereumIdentityViewSet.create)
    ↓
1. 调用FireFly创建custom identity
    ↓
2. 保存到EthereumIdentity表
    ↓
3. 调用IdentityRegistry.registerIdentity() 同步到链上
    ↓
返回成功
```

### 场景2: WorkflowContract验证权限
```solidity
contract WorkflowContract {
    IIdentityRegistry public identityRegistry;

    function sendMessage() external {
        require(
            identityRegistry.isOrgMember(msg.sender, "RequiredOrg"),
            "Not authorized"
        );
        // 执行业务逻辑
    }
}
```

### 场景3: 其他合约注册身份（可选）
```solidity
// WorkflowContract在特殊情况下也可以注册身份
function registerParticipant(address participant, ...) external {
    if (!identityRegistry.isIdentityRegistered(participant)) {
        identityRegistry.registerIdentity(...);
    }
}
```

## 5. 下一步

- [ ] 编写IdentityRegistry智能合约
- [ ] 创建合约部署脚本
- [ ] 扩展API接口支持合约交互
- [ ] 编写集成测试
