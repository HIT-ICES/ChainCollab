// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "./IIdentityRegistry.sol";

interface IOracle {
    function getDataItem(
        uint256 instanceId,
        string calldata activityId
    ) external view returns (string memory value);
}

/**
 * @title WorkflowContract with IdentityRegistry Integration
 * @dev 集成身份映射功能的工作流合约模板
 */
contract WorkflowContract {
    // ------------------------------------------------------------------
    // Enums (根据BPMN生成)
    // ------------------------------------------------------------------

    enum ElementState {
        DISABLED,
        ENABLED,
        WAITING_FOR_CONFIRMATION,
        COMPLETED
    }

    // 参与者枚举（由BPMN生成）
    enum ParticipantKey {
        Participant_0w6qkdf,
        Participant_19mgbdn
        // ... 更多参与者
    }

    // ------------------------------------------------------------------
    // Structs
    // ------------------------------------------------------------------

    struct Participant {
        bool exists;
        address account;
        string fireflyIdentityId;  // 新增：FireFly身份ID
        string orgName;            // 新增：所属组织
        bool isMulti;
        uint8 multiMaximum;
        uint8 multiMinimum;
    }

    struct Instance {
        bool exists;
        uint256 instanceId;
        mapping(ParticipantKey => Participant) participants;
        // ... 其他结构
    }

    // ------------------------------------------------------------------
    // Storage
    // ------------------------------------------------------------------

    address public owner;
    bool public isInited;
    uint256 public currentInstanceId;
    IOracle public oracle;
    IIdentityRegistry public identityRegistry;  // 新增：身份注册表引用

    mapping(uint256 => Instance) private instances;

    // ------------------------------------------------------------------
    // Events
    // ------------------------------------------------------------------

    event InstanceCreated(uint256 indexed instanceId);
    event IdentitiesRegistered(uint256 indexed instanceId, uint256 count);

    // ------------------------------------------------------------------
    // Modifiers
    // ------------------------------------------------------------------

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    modifier onlyInitialized() {
        require(isInited, "contract not initialized");
        _;
    }

    // ------------------------------------------------------------------
    // Constructor
    // ------------------------------------------------------------------

    constructor(address oracleAddress, address identityRegistryAddress) {
        owner = msg.sender;
        oracle = IOracle(oracleAddress);
        identityRegistry = IIdentityRegistry(identityRegistryAddress);
    }

    function setOracle(address oracleAddress) external onlyOwner {
        oracle = IOracle(oracleAddress);
    }

    function setIdentityRegistry(address identityRegistryAddress) external onlyOwner {
        identityRegistry = IIdentityRegistry(identityRegistryAddress);
    }

    // ------------------------------------------------------------------
    // Initialization
    // ------------------------------------------------------------------

    function initLedger() external onlyOwner {
        require(!isInited, "already initialized");
        isInited = true;
        currentInstanceId = 0;
    }

    // ------------------------------------------------------------------
    // Internal helpers
    // ------------------------------------------------------------------

    function _getInstance(
        uint256 instanceId
    ) internal view returns (Instance storage inst) {
        inst = instances[instanceId];
        require(inst.exists, "instance not found");
    }

    function _checkParticipant(
        Instance storage inst,
        ParticipantKey key
    ) internal view {
        Participant storage participant = inst.participants[key];
        require(participant.exists, "participant not set");
        require(msg.sender == participant.account, "participant not allowed");
    }

    function _createParticipant(
        Instance storage inst,
        ParticipantKey key,
        address account,
        string memory fireflyIdentityId,
        string memory orgName,
        bool isMulti,
        uint8 maxMulti,
        uint8 minMulti
    ) internal {
        inst.participants[key] = Participant({
            exists: true,
            account: account,
            fireflyIdentityId: fireflyIdentityId,
            orgName: orgName,
            isMulti: isMulti,
            multiMaximum: maxMulti,
            multiMinimum: minMulti
        });
    }

    // ------------------------------------------------------------------
    // Instance creation with Identity Registration
    // ------------------------------------------------------------------

    struct ParticipantData {
        address account;
        string fireflyIdentityId;
        string orgName;
        string customKey;
    }

    struct InitParameters {
        ParticipantData participant_0w6qkdf;
        ParticipantData participant_19mgbdn;
        // ... 其他参与者
        // 其他初始化参数
    }

    /**
     * @dev 创建实例并注册所有参与者身份到IdentityRegistry
     * @param params 初始化参数，包含所有参与者的身份信息
     * @return instanceId 创建的实例ID
     */
    function createInstance(
        InitParameters calldata params
    ) external onlyOwner onlyInitialized returns (uint256 instanceId) {
        instanceId = currentInstanceId;
        Instance storage inst = instances[instanceId];
        require(!inst.exists, "instance already exists");

        inst.exists = true;
        inst.instanceId = instanceId;

        // 创建参与者并注册身份
        _createParticipant(
            inst,
            ParticipantKey.Participant_0w6qkdf,
            params.participant_0w6qkdf.account,
            params.participant_0w6qkdf.fireflyIdentityId,
            params.participant_0w6qkdf.orgName,
            false,
            0,
            0
        );

        // 注册身份到IdentityRegistry（如果尚未注册）
        if (!identityRegistry.isIdentityRegistered(params.participant_0w6qkdf.account)) {
            identityRegistry.registerIdentity(
                params.participant_0w6qkdf.account,
                params.participant_0w6qkdf.fireflyIdentityId,
                params.participant_0w6qkdf.orgName,
                params.participant_0w6qkdf.customKey
            );
        }

        _createParticipant(
            inst,
            ParticipantKey.Participant_19mgbdn,
            params.participant_19mgbdn.account,
            params.participant_19mgbdn.fireflyIdentityId,
            params.participant_19mgbdn.orgName,
            false,
            0,
            0
        );

        // 注册身份到IdentityRegistry（如果尚未注册）
        if (!identityRegistry.isIdentityRegistered(params.participant_19mgbdn.account)) {
            identityRegistry.registerIdentity(
                params.participant_19mgbdn.account,
                params.participant_19mgbdn.fireflyIdentityId,
                params.participant_19mgbdn.orgName,
                params.participant_19mgbdn.customKey
            );
        }

        // ... 更多参与者

        // 初始化其他元素（消息、网关、事件等）
        // ...

        currentInstanceId += 1;

        emit InstanceCreated(instanceId);
        emit IdentitiesRegistered(instanceId, 2); // 根据实际参与者数量

        return instanceId;
    }

    // ------------------------------------------------------------------
    // Workflow logic with identity verification
    // ------------------------------------------------------------------

    /**
     * @dev 示例：发送消息前验证发送者身份
     */
    function Message_Send_WithIdentityCheck(
        uint256 instanceId,
        string calldata fireflyTranId,
        string calldata requiredOrg
    ) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);

        // 验证调用者是否属于要求的组织
        require(
            identityRegistry.isOrgMember(msg.sender, requiredOrg),
            "sender not in required organization"
        );

        // 执行消息发送逻辑
        // ...
    }
}
