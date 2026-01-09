// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title IIdentityRegistry
 * @dev IdentityRegistry合约接口，供其他合约调用
 */
interface IIdentityRegistry {
    /**
     * @dev 注册新身份
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
    ) external;

    /**
     * @dev 检查地址是否为某组织成员
     * @param identityAddress 身份地址
     * @param orgName 组织名称
     * @return 是否为组织成员
     */
    function isOrgMember(address identityAddress, string memory orgName)
        external
        view
        returns (bool);

    /**
     * @dev 获取地址所属组织
     * @param identityAddress 身份地址
     * @return 组织名称
     */
    function getIdentityOrg(address identityAddress)
        external
        view
        returns (string memory);

    /**
     * @dev 检查身份是否已注册
     * @param identityAddress 身份地址
     * @return 是否已注册
     */
    function isIdentityRegistered(address identityAddress)
        external
        view
        returns (bool);
}
