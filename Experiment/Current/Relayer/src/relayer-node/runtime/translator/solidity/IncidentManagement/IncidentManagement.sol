// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

interface IOracle {
    function getDataItem(
        uint256 instanceId,
        string calldata activityId
    ) external view returns (string memory value);
}

interface IIdentityRegistry {
    function getIdentityOrg(address identityAddress) external view returns (string memory);
}

contract WorkflowContract {
    // ------------------------------------------------------------------
    // Enums
    // ------------------------------------------------------------------

    enum ElementState {
        DISABLED,
        ENABLED,
        WAITING_FOR_CONFIRMATION,
        COMPLETED
    }

    enum ParticipantKey {
        Participant_15d83ih,
        Participant_1yxjs7i,
        Participant_123vwrd,
        Participant_19fntjv,
        Participant_01r48ub
    }

    enum MessageKey {
        Message_05qx9bx,
        Message_0bvz0t0,
        Message_0ek1csx,
        Message_0meslzn,
        Message_0r74t0d,
        Message_0tfcf0f,
        Message_0x3m7cv,
        Message_0zg86is,
        Message_19uhzjz,
        Message_1c9wwae,
        Message_1j8ntet,
        Message_1k8bc91
    }

    enum GatewayKey {
        Gateway_0xhpdxq,
        Gateway_0a3xut0,
        Gateway_1lr7zva
    }

    enum EventKey {
        Event_026jxk6,        Event_18807k4    }

    enum BusinessRuleKey {
        PlaceholderBusinessRule
    }

    // ------------------------------------------------------------------
    // Structs
    // ------------------------------------------------------------------

    struct StateMemory {
        string Answer;
        string Dev_issue;
        string Feedback;
        string First_issue;
        bool Handle;
        string Problem;
        string Second_issue;
        string Solution;
    }

    struct Participant {
        bool exists;
        address account;
        string org;
        bool isMulti;
        uint8 multiMaximum;
        uint8 multiMinimum;
    }

    struct Message {
        bool exists;
        ParticipantKey sendParticipant;
        ParticipantKey receiveParticipant;
        string fireflyTranId;
        ElementState state;
        string formatJson;
    }

    struct Gateway {
        bool exists;
        ElementState state;
    }

    struct ActionEvent {
        bool exists;
        ElementState state;
    }

    struct BusinessRule {
        bool exists;
        address contractAddress;
        bytes32 hashOfDmn;
        string decisionId;
        ElementState state;
    }

    struct Instance {
        bool exists;
        uint256 instanceId;
        address identityContractAddress;
        StateMemory stateMemory;
        mapping(MessageKey => Message) messages;
        mapping(GatewayKey => Gateway) gateways;
        mapping(EventKey => ActionEvent) events;
        mapping(ParticipantKey => Participant) participants;
        mapping(BusinessRuleKey => BusinessRule) businessRules;
    }

    // ------------------------------------------------------------------
    // Storage
    // ------------------------------------------------------------------

    address public owner;
    bool public isInited;
    uint256 public currentInstanceId;
    IOracle public oracle;

    mapping(uint256 => Instance) private instances;

    // ------------------------------------------------------------------
    // Events
    // ------------------------------------------------------------------

    event MessageSent(uint256 instanceId, MessageKey messageKey, string fireflyTranId);
    event GatewayDone(uint256 instanceId, GatewayKey gatewayKey);
    event ActionEventDone(uint256 instanceId, EventKey eventKey);

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

    constructor(address oracleAddress) {
        owner = msg.sender;
        oracle = IOracle(oracleAddress);
    }

    function setOracle(address oracleAddress) external onlyOwner {
        oracle = IOracle(oracleAddress);
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
        if (!participant.isMulti) {
            require(msg.sender == participant.account, "participant not allowed");
            return;
        }
        require(inst.identityContractAddress != address(0), "identity contract not set");
        string memory callerOrg = IIdentityRegistry(inst.identityContractAddress).getIdentityOrg(msg.sender);
        require(
            keccak256(bytes(callerOrg)) == keccak256(bytes(participant.org)),
            "participant org not allowed"
        );
    }

    function _createParticipant(
        Instance storage inst,
        ParticipantKey key,
        address account,
        string memory org,
        bool isMulti,
        uint8 maxMulti,
        uint8 minMulti
    ) internal {
        inst.participants[key] = Participant({
            exists: true,
            account: account,
            org: org,
            isMulti: isMulti,
            multiMaximum: maxMulti,
            multiMinimum: minMulti
        });
    }

    function _createMessage(
        Instance storage inst,
        MessageKey key,
        ParticipantKey sendKey,
        ParticipantKey recvKey,
        ElementState state,
        string memory formatJson
    ) internal {
        inst.messages[key] = Message({
            exists: true,
            sendParticipant: sendKey,
            receiveParticipant: recvKey,
            fireflyTranId: "",
            state: state,
            formatJson: formatJson
        });
    }

    function _createGateway(
        Instance storage inst,
        GatewayKey key,
        ElementState state
    ) internal {
        inst.gateways[key] = Gateway({exists: true, state: state});
    }

    function _createActionEvent(
        Instance storage inst,
        EventKey key,
        ElementState state
    ) internal {
        inst.events[key] = ActionEvent({exists: true, state: state});
    }

    function _createBusinessRule(
        Instance storage inst,
        BusinessRuleKey key,
        address contractAddress,
        string memory dmnContent,
        string memory decisionId
    ) internal {
        inst.businessRules[key] = BusinessRule({
            exists: true,
            contractAddress: contractAddress,
            hashOfDmn: keccak256(bytes(dmnContent)),
            decisionId: decisionId,
            state: ElementState.DISABLED
        });
    }

    // ------------------------------------------------------------------
    // Instance creation
    // ------------------------------------------------------------------

    struct InitParameters {
        address identityContractAddress;
        address Participant_15d83ih_account;
        string Participant_15d83ih_org;
        address Participant_1yxjs7i_account;
        string Participant_1yxjs7i_org;
        address Participant_123vwrd_account;
        string Participant_123vwrd_org;
        address Participant_19fntjv_account;
        string Participant_19fntjv_org;
        address Participant_01r48ub_account;
        string Participant_01r48ub_org;
    }

    function createInstance(
        InitParameters calldata params
    ) external onlyOwner onlyInitialized returns (uint256 instanceId) {
        instanceId = currentInstanceId;
        Instance storage inst = instances[instanceId];
        require(!inst.exists, "instance already exists");

        inst.exists = true;
        inst.instanceId = instanceId;
        require(params.identityContractAddress != address(0), "identity contract not set");
        inst.identityContractAddress = params.identityContractAddress;

        _createParticipant(
            inst,
            ParticipantKey.Participant_15d83ih,
            params.Participant_15d83ih_account,
            params.Participant_15d83ih_org,
            false,
            0,
            0
        );
        _createParticipant(
            inst,
            ParticipantKey.Participant_1yxjs7i,
            params.Participant_1yxjs7i_account,
            params.Participant_1yxjs7i_org,
            false,
            0,
            0
        );
        _createParticipant(
            inst,
            ParticipantKey.Participant_123vwrd,
            params.Participant_123vwrd_account,
            params.Participant_123vwrd_org,
            false,
            0,
            0
        );
        _createParticipant(
            inst,
            ParticipantKey.Participant_19fntjv,
            params.Participant_19fntjv_account,
            params.Participant_19fntjv_org,
            false,
            0,
            0
        );
        _createParticipant(
            inst,
            ParticipantKey.Participant_01r48ub,
            params.Participant_01r48ub_account,
            params.Participant_01r48ub_org,
            false,
            0,
            0
        );

        _createActionEvent(
            inst,
            EventKey.Event_026jxk6,
            ElementState.ENABLED
        );
        _createActionEvent(
            inst,
            EventKey.Event_18807k4,
            ElementState.DISABLED
        );

        _createMessage(
            inst,
            MessageKey.Message_05qx9bx,
            ParticipantKey.Participant_1yxjs7i,
            ParticipantKey.Participant_123vwrd,
            ElementState.DISABLED,
            "first_issue"
        );
        _createMessage(
            inst,
            MessageKey.Message_0bvz0t0,
            ParticipantKey.Participant_123vwrd,
            ParticipantKey.Participant_19fntjv,
            ElementState.DISABLED,
            "second_issue"
        );
        _createMessage(
            inst,
            MessageKey.Message_0ek1csx,
            ParticipantKey.Participant_15d83ih,
            ParticipantKey.Participant_1yxjs7i,
            ElementState.DISABLED,
            "{}"
        );
        _createMessage(
            inst,
            MessageKey.Message_0meslzn,
            ParticipantKey.Participant_1yxjs7i,
            ParticipantKey.Participant_15d83ih,
            ElementState.DISABLED,
            "solution"
        );
        _createMessage(
            inst,
            MessageKey.Message_0r74t0d,
            ParticipantKey.Participant_19fntjv,
            ParticipantKey.Participant_01r48ub,
            ElementState.DISABLED,
            "dev_issue"
        );
        _createMessage(
            inst,
            MessageKey.Message_0tfcf0f,
            ParticipantKey.Participant_123vwrd,
            ParticipantKey.Participant_1yxjs7i,
            ElementState.DISABLED,
            "feedback"
        );
        _createMessage(
            inst,
            MessageKey.Message_0x3m7cv,
            ParticipantKey.Participant_19fntjv,
            ParticipantKey.Participant_123vwrd,
            ElementState.DISABLED,
            "feedback"
        );
        _createMessage(
            inst,
            MessageKey.Message_0zg86is,
            ParticipantKey.Participant_01r48ub,
            ParticipantKey.Participant_19fntjv,
            ElementState.DISABLED,
            "feedback"
        );
        _createMessage(
            inst,
            MessageKey.Message_19uhzjz,
            ParticipantKey.Participant_15d83ih,
            ParticipantKey.Participant_1yxjs7i,
            ElementState.DISABLED,
            "answer"
        );
        _createMessage(
            inst,
            MessageKey.Message_1c9wwae,
            ParticipantKey.Participant_123vwrd,
            ParticipantKey.Participant_1yxjs7i,
            ElementState.DISABLED,
            "{}"
        );
        _createMessage(
            inst,
            MessageKey.Message_1j8ntet,
            ParticipantKey.Participant_15d83ih,
            ParticipantKey.Participant_1yxjs7i,
            ElementState.DISABLED,
            "problem"
        );
        _createMessage(
            inst,
            MessageKey.Message_1k8bc91,
            ParticipantKey.Participant_1yxjs7i,
            ParticipantKey.Participant_15d83ih,
            ElementState.DISABLED,
            "{}"
        );

        _createGateway(
            inst,
            GatewayKey.Gateway_0xhpdxq,
            ElementState.DISABLED
        );
        _createGateway(
            inst,
            GatewayKey.Gateway_0a3xut0,
            ElementState.DISABLED
        );
        _createGateway(
            inst,
            GatewayKey.Gateway_1lr7zva,
            ElementState.DISABLED
        );


        currentInstanceId += 1;
    }

    // ------------------------------------------------------------------
    // Business rule handlers
    // ------------------------------------------------------------------


    // ------------------------------------------------------------------
    // Workflow logic generated from DSL flows
    // ------------------------------------------------------------------

function Event_026jxk6(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.Event_026jxk6];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.Event_026jxk6);
        inst.messages[MessageKey.Message_1j8ntet].state = ElementState.ENABLED;

    }

function Message_05qx9bx_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_05qx9bx];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_05qx9bx, fireflyTranId);

    }

function Message_0bvz0t0_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0bvz0t0];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0bvz0t0, fireflyTranId);

    }

function Message_0ek1csx_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0ek1csx];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0ek1csx, fireflyTranId);

    }

function Message_0meslzn_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0meslzn];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0meslzn, fireflyTranId);

    }

function Message_0r74t0d_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0r74t0d];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0r74t0d, fireflyTranId);

    }

function Message_0tfcf0f_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0tfcf0f];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0tfcf0f, fireflyTranId);

    }

function Message_0x3m7cv_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0x3m7cv];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0x3m7cv, fireflyTranId);

    }

function Message_0zg86is_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0zg86is];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0zg86is, fireflyTranId);

    }

function Message_19uhzjz_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_19uhzjz];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_19uhzjz, fireflyTranId);

    }

function Message_1c9wwae_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1c9wwae];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1c9wwae, fireflyTranId);

    }

function Message_1j8ntet_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1j8ntet];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1j8ntet, fireflyTranId);

    }

function Message_1k8bc91_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1k8bc91];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1k8bc91, fireflyTranId);

    }

function Gateway_0xhpdxq(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Gateway storage g = inst.gateways[GatewayKey.Gateway_0xhpdxq];
        require(g.exists, "gateway not set");
        require(g.state == ElementState.ENABLED, "gateway state not allowed");

        g.state = ElementState.COMPLETED;
        emit GatewayDone(instanceId, GatewayKey.Gateway_0xhpdxq);
        if (inst.stateMemory.Handle == true) {
            inst.messages[MessageKey.Message_0meslzn].state = ElementState.ENABLED;
        }
        else if (inst.stateMemory.Handle == false) {
            inst.messages[MessageKey.Message_05qx9bx].state = ElementState.ENABLED;
        }

    }

function Gateway_0a3xut0(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Gateway storage g = inst.gateways[GatewayKey.Gateway_0a3xut0];
        require(g.exists, "gateway not set");
        require(g.state == ElementState.ENABLED, "gateway state not allowed");

        g.state = ElementState.COMPLETED;
        emit GatewayDone(instanceId, GatewayKey.Gateway_0a3xut0);
        inst.messages[MessageKey.Message_0tfcf0f].state = ElementState.ENABLED;
        inst.messages[MessageKey.Message_0bvz0t0].state = ElementState.ENABLED;

    }

function Gateway_1lr7zva(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Gateway storage g = inst.gateways[GatewayKey.Gateway_1lr7zva];
        require(g.exists, "gateway not set");
        require(g.state == ElementState.ENABLED, "gateway state not allowed");

        g.state = ElementState.COMPLETED;
        emit GatewayDone(instanceId, GatewayKey.Gateway_1lr7zva);
        inst.messages[MessageKey.Message_0x3m7cv].state = ElementState.ENABLED;
        inst.messages[MessageKey.Message_0r74t0d].state = ElementState.ENABLED;

    }

function Event_18807k4(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.Event_18807k4];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.Event_18807k4);

    }
}
