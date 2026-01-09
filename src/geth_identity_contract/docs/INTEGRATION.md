# 集成指南

## 概述

本指南说明如何将IdentityRegistry合约集成到现有系统：
1. **主流程**: 在创建EthereumIdentity时同步注册到链上
2. **扩展功能**: 支持WorkflowContract等其他合约调用

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

## 2. 修改EthereumIdentity创建逻辑（核心）

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

            # 获取resource set和firefly
            resource_sets = eth_environment.resource_sets.all()
            if not resource_sets.exists():
                return Response(
                    {"error": "No resource sets found for this Ethereum environment"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            resource_set = resource_sets.first()
            target_firefly = resource_set.firefly.first()
            if target_firefly is None:
                return Response(
                    {"error": "firefly not found"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 注册到FireFly
            firefly_identity_id = target_firefly.register_to_firefly(serializer.data["name"])
            if not firefly_identity_id:
                return Response(
                    {"error": "register to firefly failed"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

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

            # 【核心】同步到IdentityRegistry合约
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
        web3_url = f"http://{eth_environment.geth_rpc_endpoint}"
        abi_path = os.path.join(
            os.path.dirname(__file__),
            '../../../geth_identity_contract/build/IdentityRegistry.abi'
        )

        client = IdentityRegistryClient(
            web3_provider_url=web3_url,
            contract_address=eth_environment.identity_registry_address,
            abi_path=abi_path
        )

        # 检查是否已注册
        if client.is_identity_registered(ethereum_identity.address):
            print(f"Identity {ethereum_identity.address} already registered")
            return

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

        print(f"Identity registered on-chain: {tx_hash}")
        return tx_hash
```

## 3. 在工作流合约中使用身份验证（可选）

WorkflowContract可以引用IdentityRegistry进行权限验证：

```solidity
import "./IIdentityRegistry.sol";

contract WorkflowContract {
    IIdentityRegistry public identityRegistry;

    constructor(address oracleAddress, address identityRegistryAddress) {
        owner = msg.sender;
        oracle = IOracle(oracleAddress);
        identityRegistry = IIdentityRegistry(identityRegistryAddress);
    }

    // 示例1: 消息发送前验证组织身份
    modifier onlyOrgMember(string memory orgName) {
        require(
            identityRegistry.isOrgMember(msg.sender, orgName),
            "Not a member of the organization"
        );
        _;
    }

    function Message_Send(uint256 instanceId, string calldata fireflyTranId)
        external
        onlyOrgMember("OrgA")  // 只允许OrgA的成员调用
    {
        // 执行消息发送逻辑
    }

    // 示例2: 动态验证参与者组织
    function _checkParticipant(
        Instance storage inst,
        ParticipantKey key
    ) internal view {
        Participant storage participant = inst.participants[key];
        require(participant.exists, "participant not set");

        // 验证调用者身份和组织
        require(
            msg.sender == participant.account,
            "participant not allowed"
        );

        // 可选：验证参与者仍在指定组织中
        require(
            identityRegistry.isOrgMember(msg.sender, participant.orgName),
            "participant no longer in organization"
        );
    }
}
```

**注意**: WorkflowContract**不需要**调用registerIdentity()，因为身份已经在创建EthereumIdentity时注册了。这里只用于验证。

## 4. 授权其他合约调用（可选）

如果有特殊场景需要让WorkflowContract或其他合约注册身份：

### 4.1 授权合约

```python
# 在Python中授权
client = IdentityRegistryClient(...)
tx_hash = client.authorize_caller(
    workflow_contract_address,
    from_address=owner_address
)
```

或使用Solidity：
```solidity
// 部署后授权
identityRegistry.authorizeCaller(workflowContractAddress);
```

### 4.2 合约中调用注册

```solidity
contract WorkflowContract {
    IIdentityRegistry public identityRegistry;

    // 特殊场景：在实例创建时补充注册
    function createInstance(InitParameters calldata params) external {
        // ... 创建实例逻辑 ...

        // 如果需要，可以补充注册身份
        if (!identityRegistry.isIdentityRegistered(params.participant_account)) {
            identityRegistry.registerIdentity(
                params.participant_account,
                params.firefly_identity_id,
                params.org_name,
                params.custom_key
            );
        }
    }
}
```

**推荐**: 大多数情况下不需要这样做，保持在Django层统一管理身份注册即可。

## 5. 环境初始化流程

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
