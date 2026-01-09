# Geth Identity Contract - 以太坊身份映射系统

## 概述

该项目实现了一个以太坊身份映射合约系统，用于在Geth网络中模拟类似Hyperledger Fabric的组织和用户身份管理机制。

通过结合FireFly的org和custom identity功能，在链上维护组织与用户的映射关系，为跨链协作场景提供统一的身份管理方案。

### 核心特性

- **组织管理**: 创建、管理和停用组织
- **身份注册**: 将以太坊地址与FireFly identity关联
- **权限验证**: 链上验证用户是否属于特定组织
- **成员管理**: 查询组织成员列表和身份信息
- **合约调用支持**: 允许授权的合约（如WorkflowContract）调用身份注册功能
- **集成友好**: 提供Python客户端，易于集成到Django后端

## 使用模式

### 模式1: API层面同步注册（推荐，主流程）

创建EthereumIdentity时，Django API自动同步注册到链上：

```
用户创建身份请求
    ↓
Django API
    ↓
1. 调用FireFly创建identity
2. 保存到数据库
3. 同步注册到IdentityRegistry合约 ← 主要方式
    ↓
返回成功
```

**优点**:
- 集中管理，逻辑清晰
- 每个用户身份创建后立即在链上可验证
- 便于审计和追踪

### 模式2: 合约间调用（扩展功能）

授权后，WorkflowContract等其他合约也可以注册身份：

```
WorkflowContract
    ↓
调用 identityRegistry.registerIdentity()
    ↓
注册参与者身份
```

**使用场景**:
- 批量注册
- 特殊的业务逻辑需要
- 实例创建时的补充注册

**注意**: 需要先调用 `authorizeCaller(contractAddress)` 授权。

## 项目结构

```
geth_identity_contract/
├── contracts/
│   └── IdentityRegistry.sol        # 核心身份映射合约
├── scripts/
│   └── identity_registry_client.py # Python客户端工具类
├── docs/
│   ├── DESIGN.md                   # 设计方案文档
│   ├── DEPLOYMENT.md               # 部署指南
│   └── INTEGRATION.md              # 集成指南
└── build/                          # 编译输出目录（需手动创建）
```

## 快速开始

### 1. 编译合约

```bash
cd geth_identity_contract
mkdir -p build
solc --optimize --bin --abi contracts/IdentityRegistry.sol -o build/
```

### 2. 部署合约

使用FireFly或Web3.py部署合约到Geth网络。详见 [DEPLOYMENT.md](docs/DEPLOYMENT.md)

### 3. 集成到项目

按照 [INTEGRATION.md](docs/INTEGRATION.md) 修改Django后端代码，实现自动同步。

## 核心合约功能

### 组织管理
- `createOrganization(orgName, orgAdmin)` - 创建组织
- `deactivateOrganization(orgName)` - 停用组织
- `updateOrgAdmin(orgName, newAdmin)` - 更新管理员

### 授权管理（新增）
- `authorizeCaller(callerAddress)` - 授权其他合约调用
- `revokeCaller(callerAddress)` - 撤销授权
- `isAuthorizedCaller(callerAddress)` - 检查是否被授权

### 身份注册
- `registerIdentity(address, fireflyId, orgName, customKey)` - 注册身份
  - Owner可以直接调用
  - 授权的合约（如WorkflowContract）也可以调用
- `revokeIdentity(address)` - 撤销身份

### 查询验证
- `isOrgMember(address, orgName)` - 检查组织成员
- `getIdentityOrg(address)` - 获取所属组织
- `getOrgMembers(orgName)` - 获取成员列表
- `getIdentityInfo(address)` - 获取身份详情
- `isIdentityRegistered(address)` - 检查是否已注册

## 使用场景

### 场景1: 创建EthereumIdentity时自动注册（主流程）

```python
# 在views.py中
ethereum_identity.save()
self._sync_to_contract(eth_environment, ethereum_identity, org_name)
```

身份创建后立即在链上注册，确保一致性。

### 场景2: WorkflowContract中验证权限

```solidity
modifier onlyOrgMember(string memory orgName) {
    require(
        identityRegistry.isOrgMember(msg.sender, orgName),
        "Not authorized"
    );
    _;
}

function sendMessage() external onlyOrgMember("OrgA") {
    // 只有OrgA成员可以调用
}
```

### 场景3: 授权WorkflowContract调用（可选）

```python
# 如果需要让WorkflowContract也能注册身份
client = IdentityRegistryClient(...)
client.authorize_caller(workflow_contract_address, from_address=owner)
```

然后在WorkflowContract中：
```solidity
// 可以补充注册身份（如果需要）
if (!identityRegistry.isIdentityRegistered(participant)) {
    identityRegistry.registerIdentity(...);
}
```

### 场景4: API层面验证身份

```python
client = IdentityRegistryClient(...)
is_member = client.is_org_member(user_address, "OrgA")
if not is_member:
    return Response({"error": "Not authorized"}, status=403)
```

## 与FireFly集成

1. **创建Custom Identity**: 通过FireFly API创建带有custom key的identity
2. **同步注册到合约**: 调用IdentityRegistry.registerIdentity()将身份信息上链
3. **双重记录**: 数据库(EthereumIdentity) + 合约(IdentityRegistry)同时维护

## 数据流图

```
用户请求创建身份
    ↓
Django API接收
    ↓
1. 调用FireFly创建custom identity → 获取firefly_identity_id
    ↓
2. 保存到EthereumIdentity表
    ↓
3. 调用IdentityRegistry.registerIdentity() → 上链（主流程）
    ↓
返回成功

---

可选扩展流程：

WorkflowContract需要注册身份
    ↓
检查是否已授权
    ↓
调用 identityRegistry.registerIdentity()
    ↓
身份上链
```

## 技术栈

- **智能合约**: Solidity ^0.8.19
- **区块链**: Geth/Ethereum
- **中间件**: FireFly
- **后端**: Django + Web3.py
- **部署**: solc编译器

## 相关文档

- [设计方案](docs/DESIGN.md) - 详细的架构设计和数据模型
- [部署指南](docs/DEPLOYMENT.md) - 合约编译和部署步骤
- [集成指南](docs/INTEGRATION.md) - 与现有系统集成的详细说明

## 注意事项

1. **私钥管理**: 合约owner的私钥需要妥善保管
2. **Gas费用**: 注册身份需要消耗Gas，建议批量操作
3. **错误处理**: 合约调用失败不应影响数据库记录
4. **同步策略**: 建议异步同步到合约，避免阻塞API响应

## 下一步计划

- [ ] 添加角色权限管理（Role-Based Access Control）
- [ ] 支持批量注册身份
- [ ] 添加事件监听和同步机制
- [ ] 编写单元测试和集成测试
- [ ] 提供合约升级方案（使用代理模式）

## 贡献

欢迎提交Issue和Pull Request。

## 许可证

MIT License
