"""
IdentityRegistry 合约部署脚本

自动化部署 IdentityRegistry 合约到 Geth 网络
"""

from web3 import Web3
import json
import os
import sys


class ContractDeployer:
    """合约部署器"""

    def __init__(self, web3_provider_url: str, deployer_address: str, deployer_private_key: str):
        """
        初始化部署器

        Args:
            web3_provider_url: Web3 provider URL
            deployer_address: 部署者地址
            deployer_private_key: 部署者私钥
        """
        self.w3 = Web3(Web3.HTTPProvider(web3_provider_url))
        self.deployer_address = Web3.to_checksum_address(deployer_address)
        self.deployer_private_key = deployer_private_key

        # 检查连接
        if not self.w3.is_connected():
            raise Exception("无法连接到Web3 provider")

        print(f"✓ 已连接到 {web3_provider_url}")
        print(f"✓ 部署者地址: {self.deployer_address}")

    def deploy_contract(self, bin_path: str, abi_path: str):
        """
        部署合约

        Args:
            bin_path: 编译后的字节码文件路径
            abi_path: ABI文件路径

        Returns:
            (contract_address, tx_hash)
        """
        # 读取字节码和ABI
        with open(bin_path, 'r') as f:
            bytecode = '0x' + f.read().strip()

        with open(abi_path, 'r') as f:
            abi = json.load(f)

        print("\n开始部署 IdentityRegistry 合约...")
        print(f"字节码长度: {len(bytecode)} 字符")

        # 创建合约对象
        Contract = self.w3.eth.contract(abi=abi, bytecode=bytecode)

        # 构建交易
        construct_txn = Contract.constructor().build_transaction({
            'from': self.deployer_address,
            'nonce': self.w3.eth.get_transaction_count(self.deployer_address),
            'gas': 3000000,
            'gasPrice': self.w3.eth.gas_price
        })

        # 签名交易
        signed_txn = self.w3.eth.account.sign_transaction(
            construct_txn,
            private_key=self.deployer_private_key
        )

        # 发送交易
        print("发送部署交易...")
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        print(f"交易哈希: {tx_hash.hex()}")

        # 等待交易确认
        print("等待交易确认...")
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)

        if tx_receipt['status'] != 1:
            raise Exception("合约部署失败")

        contract_address = tx_receipt['contractAddress']
        print(f"\n✓ 合约部署成功!")
        print(f"✓ 合约地址: {contract_address}")
        print(f"✓ Gas使用: {tx_receipt['gasUsed']}")

        return contract_address, tx_hash.hex()

    def initialize_organizations(self, contract_address: str, abi_path: str, org_configs: list):
        """
        初始化组织

        Args:
            contract_address: 合约地址
            abi_path: ABI文件路径
            org_configs: 组织配置列表 [(org_name, org_admin), ...]
        """
        with open(abi_path, 'r') as f:
            abi = json.load(f)

        contract = self.w3.eth.contract(address=contract_address, abi=abi)

        print(f"\n初始化 {len(org_configs)} 个组织...")

        for org_name, org_admin in org_configs:
            print(f"\n创建组织: {org_name}")
            print(f"  管理员: {org_admin}")

            # 构建交易
            txn = contract.functions.createOrganization(
                org_name,
                Web3.to_checksum_address(org_admin)
            ).build_transaction({
                'from': self.deployer_address,
                'nonce': self.w3.eth.get_transaction_count(self.deployer_address),
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price
            })

            # 签名并发送
            signed_txn = self.w3.eth.account.sign_transaction(txn, self.deployer_private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)

            # 等待确认
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

            if tx_receipt['status'] == 1:
                print(f"  ✓ {org_name} 创建成功")
            else:
                print(f"  ✗ {org_name} 创建失败")


def main():
    """主函数"""
    print("=" * 60)
    print("IdentityRegistry 合约部署脚本")
    print("=" * 60)

    # 配置参数（需要根据实际情况修改）
    WEB3_PROVIDER = os.getenv("WEB3_PROVIDER", "http://localhost:8545")
    DEPLOYER_ADDRESS = os.getenv("DEPLOYER_ADDRESS", "")
    DEPLOYER_PRIVATE_KEY = os.getenv("DEPLOYER_PRIVATE_KEY", "")

    if not DEPLOYER_ADDRESS or not DEPLOYER_PRIVATE_KEY:
        print("\n错误: 请设置环境变量 DEPLOYER_ADDRESS 和 DEPLOYER_PRIVATE_KEY")
        print("\n使用方法:")
        print("  export DEPLOYER_ADDRESS=0x...")
        print("  export DEPLOYER_PRIVATE_KEY=0x...")
        print("  python deploy_contract.py")
        sys.exit(1)

    # 文件路径
    base_dir = os.path.dirname(os.path.abspath(__file__))
    bin_path = os.path.join(base_dir, "../build/IdentityRegistry.bin")
    abi_path = os.path.join(base_dir, "../build/IdentityRegistry.abi")

    # 检查文件是否存在
    if not os.path.exists(bin_path) or not os.path.exists(abi_path):
        print("\n错误: 合约文件不存在，请先编译合约")
        print("\n编译命令:")
        print("  solc --optimize --bin --abi contracts/IdentityRegistry.sol -o build/")
        sys.exit(1)

    try:
        # 初始化部署器
        deployer = ContractDeployer(WEB3_PROVIDER, DEPLOYER_ADDRESS, DEPLOYER_PRIVATE_KEY)

        # 部署合约
        contract_address, tx_hash = deployer.deploy_contract(bin_path, abi_path)

        # 组织配置（示例，需要根据实际情况修改）
        org_configs = [
            # ("OrgA", "0xOrgAAdminAddress"),
            # ("OrgB", "0xOrgBAdminAddress"),
        ]

        # 如果有组织配置，则初始化
        if org_configs:
            deployer.initialize_organizations(contract_address, abi_path, org_configs)

        # 保存部署信息
        deployment_info = {
            "contract_address": contract_address,
            "tx_hash": tx_hash,
            "deployer": DEPLOYER_ADDRESS,
            "network": WEB3_PROVIDER
        }

        output_path = os.path.join(base_dir, "../build/deployment.json")
        with open(output_path, 'w') as f:
            json.dump(deployment_info, f, indent=2)

        print(f"\n✓ 部署信息已保存到: {output_path}")

        print("\n" + "=" * 60)
        print("部署完成!")
        print("=" * 60)
        print(f"\n合约地址: {contract_address}")
        print("\n请将此地址保存到 EthEnvironment.identity_registry_address 字段中")

    except Exception as e:
        print(f"\n✗ 部署失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
