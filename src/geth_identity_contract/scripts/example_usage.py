"""
IdentityRegistry 使用示例

演示如何使用 IdentityRegistryClient 进行各种操作
"""

from identity_registry_client import IdentityRegistryClient


def main():
    # 配置参数（需要根据实际环境修改）
    WEB3_PROVIDER = "http://localhost:8545"
    CONTRACT_ADDRESS = "0x..."  # 部署后的合约地址
    ABI_PATH = "../build/IdentityRegistry.abi"
    OWNER_ADDRESS = "0x..."  # 合约owner地址

    # 初始化客户端
    client = IdentityRegistryClient(
        web3_provider_url=WEB3_PROVIDER,
        contract_address=CONTRACT_ADDRESS,
        abi_path=ABI_PATH
    )

    print("=" * 60)
    print("IdentityRegistry 使用示例")
    print("=" * 60)

    # 1. 创建组织
    print("\n1. 创建组织...")
    org_configs = [
        ("OrgA", "0xOrgAAdminAddress"),
        ("OrgB", "0xOrgBAdminAddress"),
    ]

    for org_name, org_admin in org_configs:
        try:
            tx_hash = client.create_organization(org_name, org_admin, OWNER_ADDRESS)
            print(f"   创建组织 {org_name}: {tx_hash}")
            client.wait_for_transaction(tx_hash)
            print(f"   ✓ {org_name} 创建成功")
        except Exception as e:
            print(f"   ✗ {org_name} 创建失败: {e}")

    # 2. 注册身份
    print("\n2. 注册身份...")
    identities = [
        {
            "address": "0xUser1Address",
            "firefly_id": "ff-identity-001",
            "org": "OrgA",
            "custom_key": "user1@orgA"
        },
        {
            "address": "0xUser2Address",
            "firefly_id": "ff-identity-002",
            "org": "OrgB",
            "custom_key": "user2@orgB"
        }
    ]

    for identity in identities:
        try:
            tx_hash = client.register_identity(
                identity_address=identity["address"],
                firefly_identity_id=identity["firefly_id"],
                org_name=identity["org"],
                custom_key=identity["custom_key"],
                from_address=OWNER_ADDRESS
            )
            print(f"   注册身份 {identity['custom_key']}: {tx_hash}")
            client.wait_for_transaction(tx_hash)
            print(f"   ✓ {identity['custom_key']} 注册成功")
        except Exception as e:
            print(f"   ✗ {identity['custom_key']} 注册失败: {e}")

    # 3. 查询组织列表
    print("\n3. 查询所有组织...")
    try:
        orgs = client.get_all_organizations()
        print(f"   找到 {len(orgs)} 个组织:")
        for org in orgs:
            print(f"   - {org}")
    except Exception as e:
        print(f"   ✗ 查询失败: {e}")

    # 4. 验证组织成员
    print("\n4. 验证组织成员...")
    for identity in identities:
        try:
            is_member = client.is_org_member(identity["address"], identity["org"])
            status = "✓" if is_member else "✗"
            print(f"   {status} {identity['custom_key']} 是否属于 {identity['org']}: {is_member}")
        except Exception as e:
            print(f"   ✗ 验证失败: {e}")

    # 5. 获取组织成员列表
    print("\n5. 获取组织成员列表...")
    for org_name, _ in org_configs:
        try:
            members = client.get_org_members(org_name)
            print(f"   {org_name} 有 {len(members)} 个成员:")
            for member in members:
                print(f"   - {member}")
        except Exception as e:
            print(f"   ✗ 查询失败: {e}")

    # 6. 获取身份详细信息
    print("\n6. 获取身份详细信息...")
    for identity in identities:
        try:
            info = client.get_identity_info(identity["address"])
            print(f"   身份: {info['customKey']}")
            print(f"   - FireFly ID: {info['fireflyIdentityId']}")
            print(f"   - 组织: {info['orgName']}")
            print(f"   - 已注册: {info['registered']}")
            print(f"   - 注册时间: {info['registeredAt']}")
        except Exception as e:
            print(f"   ✗ 查询失败: {e}")

    # 7. 检查身份是否已注册
    print("\n7. 检查身份注册状态...")
    test_addresses = [
        identities[0]["address"],
        "0xUnregisteredAddress"
    ]

    for addr in test_addresses:
        try:
            is_registered = client.is_identity_registered(addr)
            status = "✓ 已注册" if is_registered else "✗ 未注册"
            print(f"   {addr}: {status}")
        except Exception as e:
            print(f"   ✗ 查询失败: {e}")

    print("\n" + "=" * 60)
    print("示例执行完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
