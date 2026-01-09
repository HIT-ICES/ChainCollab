# 集成指南

## 1. 修改Django模型

在 `backend/api/models.py` 中添加字段：

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

## 2. 修改EthereumIdentity创建逻辑

在 `backend/api/routes/ethereum_identity/views.py` 中集成合约调用：

```python
from geth_identity_contract.scripts.identity_registry_client import IdentityRegistryClient
import os

class EthereumIdentityViewSet(viewsets.ViewSet):

    def create(self, request):
        serializer = EthereumIdentityCreateSerializer(data=request.data)
        if serializer.is_valid():
            eth_environment_id = serializer.data["eth_environment_id"]
            eth_environment = EthEnvironment.objects.get(id=eth_environment_id)

            # ... 现有的FireFly注册逻辑 ...

            # 创建EthereumIdentity实例
            ethereum_identity = EthereumIdentity(
                name=serializer.data["name"],
                address=serializer.data.get("address", ""),
                private_key=serializer.data.get("private_key", ""),
                firefly_identity_id=firefly_identity_id,
                eth_environment=eth_environment,
                membership=resource_set.membership,
            )
            ethereum_identity.save()

            # 【新增】同步到IdentityRegistry合约
            if eth_environment.identity_registry_address:
                try:
                    self._sync_to_contract(
                        eth_environment,
                        ethereum_identity,
                        resource_set.membership.name
                    )
                except Exception as e:
                    # 记录错误但不影响创建流程
                    print(f"Failed to sync to contract: {e}")

            return Response(
                {"id": ethereum_identity.id},
                status=status.HTTP_201_CREATED,
            )

    def _sync_to_contract(self, eth_environment, ethereum_identity, org_name):
        """同步身份到IdentityRegistry合约"""

        # 初始化合约客户端
        web3_url = f"http://{eth_environment.geth_rpc_endpoint}"  # 需要根据实际情况调整
        abi_path = os.path.join(
            os.path.dirname(__file__),
            '../../../geth_identity_contract/build/IdentityRegistry.abi'
        )

        client = IdentityRegistryClient(
            web3_provider_url=web3_url,
            contract_address=eth_environment.identity_registry_address,
            abi_path=abi_path
        )

        # 注册身份到合约
        tx_hash = client.register_identity(
            identity_address=ethereum_identity.address,
            firefly_identity_id=ethereum_identity.firefly_identity_id,
            org_name=org_name,
            custom_key=ethereum_identity.name,
            from_address=eth_environment.identity_registry_owner
        )

        # 等待交易确认
        receipt = client.wait_for_transaction(tx_hash)

        if receipt['status'] != 1:
            raise Exception(f"Transaction failed: {tx_hash}")

        return tx_hash
```

## 3. 在工作流合约中使用身份验证

在 `WorkflowContract` 或其他业务合约中引用IdentityRegistry：

```solidity
import "./IdentityRegistry.sol";

contract WorkflowContract {
    IIdentityRegistry public identityRegistry;

    constructor(address _identityRegistryAddress) {
        identityRegistry = IIdentityRegistry(_identityRegistryAddress);
    }

    modifier onlyOrgMember(string memory orgName) {
        require(
            identityRegistry.isOrgMember(msg.sender, orgName),
            "Not a member of the organization"
        );
        _;
    }

    function someRestrictedFunction() external onlyOrgMember("OrgA") {
        // 只有OrgA的成员可以调用
    }
}

interface IIdentityRegistry {
    function isOrgMember(address identityAddress, string memory orgName) external view returns (bool);
}
```

## 4. 环境初始化流程

创建新的EthEnvironment时：

1. 部署IdentityRegistry合约
2. 保存合约地址到`identity_registry_address`字段
3. 为每个ResourceSet的membership创建组织
4. 后续创建EthereumIdentity时自动注册到合约

## 5. 权限验证场景

### 场景1: 检查用户是否属于某组织

```python
def check_user_org(user_address, org_name, eth_environment):
    client = IdentityRegistryClient(...)
    return client.is_org_member(user_address, org_name)
```

### 场景2: 获取组织所有成员

```python
def get_org_users(org_name, eth_environment):
    client = IdentityRegistryClient(...)
    return client.get_org_members(org_name)
```

### 场景3: 链上验证（在智能合约中）

```solidity
function sendMessage(MessageKey messageKey) external {
    Message storage m = messages[messageKey];

    // 验证发送者是否属于正确的组织
    require(
        identityRegistry.isOrgMember(msg.sender, "RequiredOrg"),
        "Sender not in required organization"
    );

    // 执行消息发送逻辑
    // ...
}
```
