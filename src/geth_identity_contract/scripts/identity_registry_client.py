"""
IdentityRegistry合约交互工具类
提供与IdentityRegistry智能合约交互的Python接口
"""

from web3 import Web3
import json
from typing import List, Dict, Optional


class IdentityRegistryClient:
    """IdentityRegistry合约客户端"""

    def __init__(self, web3_provider_url: str, contract_address: str, abi_path: str):
        """
        初始化客户端

        Args:
            web3_provider_url: Web3 provider URL (e.g., http://localhost:8545)
            contract_address: 已部署的合约地址
            abi_path: 合约ABI文件路径
        """
        self.w3 = Web3(Web3.HTTPProvider(web3_provider_url))
        self.contract_address = contract_address

        # 加载ABI
        with open(abi_path, 'r') as f:
            abi = json.load(f)

        self.contract = self.w3.eth.contract(address=contract_address, abi=abi)

    def create_organization(self, org_name: str, org_admin: str, from_address: str) -> str:
        """
        创建组织

        Args:
            org_name: 组织名称
            org_admin: 组织管理员地址
            from_address: 交易发起者地址（必须是合约owner）

        Returns:
            交易哈希
        """
        tx_hash = self.contract.functions.createOrganization(
            org_name,
            org_admin
        ).transact({'from': from_address})

        return tx_hash.hex()

    def register_identity(
        self,
        identity_address: str,
        firefly_identity_id: str,
        org_name: str,
        custom_key: str,
        from_address: str
    ) -> str:
        """
        注册身份到合约

        Args:
            identity_address: 身份地址
            firefly_identity_id: FireFly身份ID
            org_name: 所属组织
            custom_key: FireFly custom key
            from_address: 交易发起者地址（必须是合约owner）

        Returns:
            交易哈希
        """
        tx_hash = self.contract.functions.registerIdentity(
            identity_address,
            firefly_identity_id,
            org_name,
            custom_key
        ).transact({'from': from_address})

        return tx_hash.hex()

    def is_org_member(self, identity_address: str, org_name: str) -> bool:
        """
        检查地址是否为组织成员

        Args:
            identity_address: 身份地址
            org_name: 组织名称

        Returns:
            是否为组织成员
        """
        return self.contract.functions.isOrgMember(identity_address, org_name).call()

    def get_identity_org(self, identity_address: str) -> str:
        """
        获取地址所属组织

        Args:
            identity_address: 身份地址

        Returns:
            组织名称
        """
        return self.contract.functions.getIdentityOrg(identity_address).call()

    def get_org_members(self, org_name: str) -> List[str]:
        """
        获取组织成员列表

        Args:
            org_name: 组织名称

        Returns:
            成员地址列表
        """
        return self.contract.functions.getOrgMembers(org_name).call()

    def get_identity_info(self, identity_address: str) -> Dict:
        """
        获取身份详细信息

        Args:
            identity_address: 身份地址

        Returns:
            身份信息字典
        """
        info = self.contract.functions.getIdentityInfo(identity_address).call()
        return {
            'identityAddress': info[0],
            'fireflyIdentityId': info[1],
            'orgName': info[2],
            'customKey': info[3],
            'registered': info[4],
            'registeredAt': info[5]
        }

    def is_identity_registered(self, identity_address: str) -> bool:
        """
        检查身份是否已注册

        Args:
            identity_address: 身份地址

        Returns:
            是否已注册
        """
        return self.contract.functions.isIdentityRegistered(identity_address).call()

    def get_all_organizations(self) -> List[str]:
        """
        获取所有组织列表

        Returns:
            组织名称列表
        """
        return self.contract.functions.getAllOrganizations().call()

    def authorize_caller(self, caller_address: str, from_address: str) -> str:
        """
        授权合约调用者（如WorkflowContract）

        Args:
            caller_address: 被授权的合约地址
            from_address: 交易发起者地址（必须是合约owner）

        Returns:
            交易哈希
        """
        tx_hash = self.contract.functions.authorizeCaller(
            caller_address
        ).transact({'from': from_address})

        return tx_hash.hex()

    def revoke_caller(self, caller_address: str, from_address: str) -> str:
        """
        撤销合约调用授权

        Args:
            caller_address: 被撤销授权的合约地址
            from_address: 交易发起者地址（必须是合约owner）

        Returns:
            交易哈希
        """
        tx_hash = self.contract.functions.revokeCaller(
            caller_address
        ).transact({'from': from_address})

        return tx_hash.hex()

    def is_authorized_caller(self, caller_address: str) -> bool:
        """
        检查地址是否被授权

        Args:
            caller_address: 调用者地址

        Returns:
            是否被授权
        """
        return self.contract.functions.isAuthorizedCaller(caller_address).call()

    def wait_for_transaction(self, tx_hash: str, timeout: int = 120):
        """
        等待交易确认

        Args:
            tx_hash: 交易哈希
            timeout: 超时时间（秒）

        Returns:
            交易收据
        """
        return self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
