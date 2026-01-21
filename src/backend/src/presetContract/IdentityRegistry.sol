// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title IdentityRegistry
 * @dev 以太坊身份映射注册表合约
 * 用于在Geth网络中实现类似Fabric的组织和用户身份管理
 */
contract IdentityRegistry {

    // ------------------------------------------------------------------
    // 结构体定义
    // ------------------------------------------------------------------

    /// @dev 组织信息结构
    struct Organization {
        string orgName;           // 组织名称（对应FireFly org）
        address orgAdmin;         // 组织管理员地址
        bool active;              // 是否激活
        uint256 memberCount;      // 成员数量
        uint256 createdAt;        // 创建时间
    }

    /// @dev 身份信息结构
    struct Identity {
        address identityAddress;  // 用户地址
        string fireflyIdentityId; // FireFly identity ID
        string orgName;           // 所属组织
        string customKey;         // FireFly custom key
        bool registered;          // 是否已注册
        uint256 registeredAt;     // 注册时间
    }

    // ------------------------------------------------------------------
    // 存储变量
    // ------------------------------------------------------------------

    address public owner;                                    // 合约所有者
    mapping(address => bool) public authorizedCallers;       // 授权调用者（其他合约）

    mapping(string => Organization) public organizations;    // 组织名称 => 组织信息
    mapping(address => Identity) public identities;          // 地址 => 身份信息
    mapping(string => address[]) public orgMembers;          // 组织名称 => 成员地址列表
    mapping(string => bool) public orgExists;                // 组织是否存在

    string[] public orgList;                                 // 所有组织列表

    // ------------------------------------------------------------------
    // 事件定义
    // ------------------------------------------------------------------

    event OrganizationCreated(string indexed orgName, address indexed orgAdmin);
    event IdentityRegistered(address indexed identityAddress, string orgName, string fireflyIdentityId);
    event IdentityRevoked(address indexed identityAddress);
    event OrganizationDeactivated(string indexed orgName);
    event CallerAuthorized(address indexed caller);
    event CallerRevoked(address indexed caller);

    // ------------------------------------------------------------------
    // 修饰器
    // ------------------------------------------------------------------

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }

    modifier onlyOwnerOrAuthorized() {
        require(
            msg.sender == owner || authorizedCallers[msg.sender],
            "Only owner or authorized caller can call this function"
        );
        _;
    }

    modifier onlyOrgAdmin(string memory orgName) {
        require(organizations[orgName].orgAdmin == msg.sender, "Only org admin can call this function");
        _;
    }

    modifier orgMustExist(string memory orgName) {
        require(orgExists[orgName], "Organization does not exist");
        _;
    }

    // ------------------------------------------------------------------
    // 构造函数
    // ------------------------------------------------------------------

    constructor() {
        owner = msg.sender;
    }

    // ------------------------------------------------------------------
    // 组织管理功能
    // ------------------------------------------------------------------

    /**
     * @dev 创建新组织
     * @param orgName 组织名称
     * @param orgAdmin 组织管理员地址
     */
    function createOrganization(string memory orgName, address orgAdmin)
        external
        onlyOwner
    {
        require(!orgExists[orgName], "Organization already exists");
        require(orgAdmin != address(0), "Invalid admin address");

        organizations[orgName] = Organization({
            orgName: orgName,
            orgAdmin: orgAdmin,
            active: true,
            memberCount: 0,
            createdAt: block.timestamp
        });

        orgExists[orgName] = true;
        orgList.push(orgName);

        emit OrganizationCreated(orgName, orgAdmin);
    }

    /**
     * @dev 停用组织
     * @param orgName 组织名称
     */
    function deactivateOrganization(string memory orgName)
        external
        onlyOwner
        orgMustExist(orgName)
    {
        organizations[orgName].active = false;
        emit OrganizationDeactivated(orgName);
    }

    /**
     * @dev 更新组织管理员
     * @param orgName 组织名称
     * @param newAdmin 新管理员地址
     */
    function updateOrgAdmin(string memory orgName, address newAdmin)
        external
        onlyOrgAdmin(orgName)
        orgMustExist(orgName)
    {
        require(newAdmin != address(0), "Invalid admin address");
        organizations[orgName].orgAdmin = newAdmin;
    }

    // ------------------------------------------------------------------
    // 授权管理功能
    // ------------------------------------------------------------------

    /**
     * @dev 授权合约调用者（如WorkflowContract）
     * @param caller 调用者地址
     */
    function authorizeCaller(address caller)
        external
        onlyOwner
    {
        require(caller != address(0), "Invalid caller address");
        authorizedCallers[caller] = true;
        emit CallerAuthorized(caller);
    }

    /**
     * @dev 撤销合约调用授权
     * @param caller 调用者地址
     */
    function revokeCaller(address caller)
        external
        onlyOwner
    {
        authorizedCallers[caller] = false;
        emit CallerRevoked(caller);
    }

    /**
     * @dev 检查地址是否被授权
     * @param caller 调用者地址
     * @return 是否被授权
     */
    function isAuthorizedCaller(address caller)
        external
        view
        returns (bool)
    {
        return authorizedCallers[caller];
    }

    // ------------------------------------------------------------------
    // 身份注册功能
    // ------------------------------------------------------------------

    /**
     * @dev 注册新身份（可由授权合约调用）
     * @param identityAddress 身份地址
     * @param fireflyIdentityId FireFly身份ID
     * @param orgName 所属组织名称
     * @param customKey FireFly custom key
     */
    function registerIdentity(
        address identityAddress,
        string memory fireflyIdentityId,
        string memory orgName,
        string memory customKey
    )
        external
        onlyOwnerOrAuthorized
        orgMustExist(orgName)
    {
        require(identityAddress != address(0), "Invalid identity address");
        require(!identities[identityAddress].registered, "Identity already registered");
        require(organizations[orgName].active, "Organization is not active");

        identities[identityAddress] = Identity({
            identityAddress: identityAddress,
            fireflyIdentityId: fireflyIdentityId,
            orgName: orgName,
            customKey: customKey,
            registered: true,
            registeredAt: block.timestamp
        });

        orgMembers[orgName].push(identityAddress);
        organizations[orgName].memberCount += 1;

        emit IdentityRegistered(identityAddress, orgName, fireflyIdentityId);
    }

    /**
     * @dev 撤销身份
     * @param identityAddress 身份地址
     */
    function revokeIdentity(address identityAddress)
        external
        onlyOwner
    {
        require(identities[identityAddress].registered, "Identity not registered");

        string memory orgName = identities[identityAddress].orgName;
        identities[identityAddress].registered = false;

        // 减少组织成员计数
        if (organizations[orgName].memberCount > 0) {
            organizations[orgName].memberCount -= 1;
        }

        emit IdentityRevoked(identityAddress);
    }

    // ------------------------------------------------------------------
    // 查询和验证功能
    // ------------------------------------------------------------------

    /**
     * @dev 检查地址是否为某组织成员
     * @param identityAddress 身份地址
     * @param orgName 组织名称
     * @return 是否为组织成员
     */
    function isOrgMember(address identityAddress, string memory orgName)
        external
        view
        returns (bool)
    {
        Identity memory identity = identities[identityAddress];
        return identity.registered &&
               keccak256(bytes(identity.orgName)) == keccak256(bytes(orgName));
    }

    /**
     * @dev 获取地址所属组织
     * @param identityAddress 身份地址
     * @return 组织名称
     */
    function getIdentityOrg(address identityAddress)
        external
        view
        returns (string memory)
    {
        require(identities[identityAddress].registered, "Identity not registered");
        return identities[identityAddress].orgName;
    }

    /**
     * @dev 获取组织成员列表
     * @param orgName 组织名称
     * @return 成员地址列表
     */
    function getOrgMembers(string memory orgName)
        external
        view
        orgMustExist(orgName)
        returns (address[] memory)
    {
        return orgMembers[orgName];
    }

    /**
     * @dev 获取身份详细信息
     * @param identityAddress 身份地址
     * @return 身份信息
     */
    function getIdentityInfo(address identityAddress)
        external
        view
        returns (Identity memory)
    {
        require(identities[identityAddress].registered, "Identity not registered");
        return identities[identityAddress];
    }

    /**
     * @dev 获取所有组织列表
     * @return 组织名称列表
     */
    function getAllOrganizations()
        external
        view
        returns (string[] memory)
    {
        return orgList;
    }

    /**
     * @dev 检查身份是否已注册
     * @param identityAddress 身份地址
     * @return 是否已注册
     */
    function isIdentityRegistered(address identityAddress)
        external
        view
        returns (bool)
    {
        return identities[identityAddress].registered;
    }
}
