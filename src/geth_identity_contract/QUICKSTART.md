# 快速入门指南

本指南将帮助你快速部署和使用 IdentityRegistry 合约系统。

## 方案说明

**主流程**: 在创建EthereumIdentity时，Django API自动同步注册到IdentityRegistry合约。

**扩展功能**: 合约也支持授权其他合约（如WorkflowContract）调用注册功能。

## 📋 前置条件

- Geth 节点正在运行
- FireFly 已部署并可访问
- Python 3.8+ 环境
- Solidity 编译器 (solc >= 0.8.19)

## 🚀 快速开始（5步）

### 步骤 1: 编译合约

```bash
cd geth_identity_contract
mkdir -p build
solc --optimize --bin --abi contracts/IdentityRegistry.sol -o build/
```

验证编译结果：
```bash
ls build/
# 应该看到: IdentityRegistry.abi  IdentityRegistry.bin
```

### 步骤 2: 部署合约

```bash
cd scripts

# 设置环境变量
export WEB3_PROVIDER="http://localhost:8545"
export DEPLOYER_ADDRESS="0x你的部署者地址"
export DEPLOYER_PRIVATE_KEY="0x你的私钥"

# 执行部署
python deploy_contract.py
```

部署成功后会输出合约地址，例如：
```
✓ 合约部署成功!
✓ 合约地址: 0x1234567890abcdef...
```

**重要**: 保存这个合约地址！

### 步骤 3: 更新数据库模型

在 `backend/api/models.py` 中为 `EthEnvironment` 添加字段：

```python
class EthEnvironment(models.Model):
    # ... 现有字段 ...

    identity_registry_address = models.TextField(
        help_text="IdentityRegistry contract address",
        null=True,
        blank=True
    )
    identity_registry_owner = models.TextField(
        help_text="Owner address of IdentityRegistry contract",
        null=True,
        blank=True
    )
```

运行迁移：
```bash
cd backend
python manage.py makemigrations
python manage.py migrate
```

### 步骤 4: 在数据库中保存合约地址

通过Django admin或API，将部署的合约地址保存到对应的 `EthEnvironment` 记录中：

```python
eth_env = EthEnvironment.objects.get(id="your-env-id")
eth_env.identity_registry_address = "0x1234567890abcdef..."  # 步骤2的合约地址
eth_env.identity_registry_owner = "0x你的部署者地址"
eth_env.save()
```

### 步骤 5: 集成到API

复制工具类到项目中：

```bash
cp geth_identity_contract/scripts/identity_registry_client.py backend/api/utils/
```

在 `backend/api/routes/ethereum_identity/views.py` 中添加同步逻辑（参考 `docs/INTEGRATION.md`）。

## 🧪 测试验证

### 测试 1: 创建组织

```python
from api.utils.identity_registry_client import IdentityRegistryClient

client = IdentityRegistryClient(
    web3_provider_url="http://localhost:8545",
    contract_address="0x你的合约地址",
    abi_path="geth_identity_contract/build/IdentityRegistry.abi"
)

# 创建组织
tx_hash = client.create_organization("TestOrg", "0xAdminAddress", "0xOwnerAddress")
print(f"组织创建交易: {tx_hash}")
```

### 测试 2: 注册身份（通过API自动完成）

通过API创建 EthereumIdentity，系统会自动同步到合约：

```bash
curl -X POST http://localhost:8000/api/ethereum_identity/ \
  -H "Content-Type: application/json" \
  -d '{
    "eth_environment_id": "your-env-id",
    "name": "test_user",
    "address": "0xUserAddress"
  }'
```

### 测试 3: 验证组织成员

```python
is_member = client.is_org_member("0xUserAddress", "TestOrg")
print(f"是否为组织成员: {is_member}")
```

### 测试 4: 授权WorkflowContract（可选）

如果需要让WorkflowContract也能注册身份：

```python
# 授权WorkflowContract
tx_hash = client.authorize_caller(
    "0xWorkflowContractAddress",
    from_address="0xOwnerAddress"
)
client.wait_for_transaction(tx_hash)

# 检查授权状态
is_authorized = client.is_authorized_caller("0xWorkflowContractAddress")
print(f"是否已授权: {is_authorized}")
```

## 📝 常见场景

### 场景 1: 在工作流合约中验证权限

```solidity
// 在你的 WorkflowContract 中
import "./IdentityRegistry.sol";

contract WorkflowContract {
    IIdentityRegistry public identityRegistry;

    constructor(address _identityRegistryAddress) {
        identityRegistry = IIdentityRegistry(_identityRegistryAddress);
    }

    function sendMessage(string memory orgName) external {
        require(
            identityRegistry.isOrgMember(msg.sender, orgName),
            "Not authorized"
        );
        // 执行业务逻辑
    }
}
```

### 场景 2: API层面权限检查

```python
def check_permission(request, org_name):
    user_address = request.user.ethereum_address
    client = IdentityRegistryClient(...)

    if not client.is_org_member(user_address, org_name):
        return Response({"error": "Not authorized"}, status=403)

    # 继续处理请求
```

### 场景 3: 查询组织成员

```python
def get_org_members_view(request, org_name):
    client = IdentityRegistryClient(...)
    members = client.get_org_members(org_name)

    return Response({"members": members})
```

## 🎯 下一步

1. **阅读详细文档**
   - [设计方案](docs/DESIGN.md)
   - [部署指南](docs/DEPLOYMENT.md)
   - [集成指南](docs/INTEGRATION.md)

2. **查看示例代码**
   - `scripts/example_usage.py` - 完整的使用示例

3. **自定义和扩展**
   - 添加角色权限管理
   - 实现批量注册
   - 添加事件监听

## ❓ 遇到问题？

### 合约部署失败
- 检查 Geth 节点是否正常运行
- 确认部署账户有足够的 ETH
- 验证私钥格式是否正确

### 身份注册失败
- 确认合约地址是否正确
- 检查组织是否已创建
- 验证交易 Gas 费用是否足够

### 查询返回空结果
- 确认身份是否已成功注册到链上
- 检查交易是否已确认
- 验证查询的组织名称是否正确

## 📚 相关资源

- [Solidity 文档](https://docs.soliditylang.org/)
- [Web3.py 文档](https://web3py.readthedocs.io/)
- [FireFly 文档](https://hyperledger.github.io/firefly/)

## 🎉 完成！

现在你已经成功设置了以太坊身份映射系统，可以开始在你的区块链应用中使用组织和身份管理功能了！
