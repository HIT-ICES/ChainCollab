# 合约部署指南

## 部署脚本说明

### 1. 编译合约

使用solc编译器编译IdentityRegistry合约：

```bash
solc --optimize --bin --abi contracts/IdentityRegistry.sol -o build/
```

生成文件:
- `build/IdentityRegistry.bin` - 字节码
- `build/IdentityRegistry.abi` - ABI接口定义

### 2. 部署到Geth网络

#### 方式1: 使用FireFly部署

利用现有的FireFly接口部署合约（推荐）。

#### 方式2: 使用Web3.py直接部署

```python
from web3 import Web3

# 连接到Geth节点
w3 = Web3(Web3.HTTPProvider('http://localhost:8545'))

# 解锁账户
w3.geth.personal.unlock_account(deployer_address, password)

# 读取编译后的合约
with open('build/IdentityRegistry.bin', 'r') as f:
    bytecode = f.read()

with open('build/IdentityRegistry.abi', 'r') as f:
    abi = json.load(f)

# 部署合约
IdentityRegistry = w3.eth.contract(abi=abi, bytecode=bytecode)
tx_hash = IdentityRegistry.constructor().transact({'from': deployer_address})
tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

contract_address = tx_receipt.contractAddress
print(f"Contract deployed at: {contract_address}")
```

### 3. 初始化合约

部署后需要初始化组织信息：

```python
# 创建合约实例
contract = w3.eth.contract(address=contract_address, abi=abi)

# 创建组织
for org_name, org_admin in organizations:
    tx_hash = contract.functions.createOrganization(
        org_name,
        org_admin
    ).transact({'from': owner_address})

    w3.eth.wait_for_transaction_receipt(tx_hash)
```

## 集成到现有系统

### 1. 在EthEnvironment中记录合约地址

需要在Django模型中添加字段记录部署的合约地址：

```python
class EthEnvironment(models.Model):
    # ... 现有字段 ...
    identity_registry_address = models.TextField(
        help_text="IdentityRegistry contract address",
        null=True,
        blank=True
    )
```

### 2. 在创建EthereumIdentity时同步到合约

修改`EthereumIdentityViewSet.create()`方法，在创建身份后调用合约注册。

### 3. 添加合约交互工具类

建议创建独立的工具类处理与IdentityRegistry合约的交互。
