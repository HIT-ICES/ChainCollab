// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IOracle {
    function getDataItem(
        uint256 instanceId,
        string calldata activityId
    ) external view returns (string memory value);
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
        Participant_1p9owwo,
        Participant_12df78t
    }

    enum MessageKey {
        Message_01jq2zl,
        Message_068kmzv,
        Message_076ulzs,
        Message_09krt7c,
        Message_0ywghlt,
        Message_12n6jjk,
        Message_1b1qlzd,
        Message_1bhhp1n
    }

    enum GatewayKey {
        Gateway_0auc3he,
        Gateway_0ivv4vg,
        Gateway_0jgq0a6
    }

    enum EventKey {
        Event_0ojehz6,
        Event_0ci2gl8,
        Event_0dyp0ut
    }

    // ------------------------------------------------------------------
    // Structs
    // ------------------------------------------------------------------

    struct StateMemory {
        bool Confirm;
        int256 Duration;
        string Type;
    }

    struct Participant {
        bool exists;
        address account;
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
        bytes32 hashOfDmn;
        string decisionId;
        ElementState state;
    }

    struct Instance {
        bool exists;
        uint256 instanceId;
        StateMemory stateMemory;
        mapping(MessageKey => Message) messages;
        mapping(GatewayKey => Gateway) gateways;
        mapping(EventKey => ActionEvent) events;
        mapping(ParticipantKey => Participant) participants;
        mapping(bytes32 => BusinessRule) businessRules;
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
        require(msg.sender == participant.account, "participant not allowed");
    }

    function _createParticipant(
        Instance storage inst,
        ParticipantKey key,
        address account,
        bool isMulti,
        uint8 maxMulti,
        uint8 minMulti
    ) internal {
        inst.participants[key] = Participant({
            exists: true,
            account: account,
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
        bytes32 key,
        string memory dmnContent,
        string memory decisionId
    ) internal {
        inst.businessRules[key] = BusinessRule({
            exists: true,
            hashOfDmn: keccak256(bytes(dmnContent)),
            decisionId: decisionId,
            state: ElementState.DISABLED
        });
    }

    // ------------------------------------------------------------------
    // Instance creation
    // ------------------------------------------------------------------

    struct InitParameters {
        address Participant_1p9owwo_account;
        address Participant_12df78t_account;
        string Activity_0tya4bp_content;
        string Activity_0tya4bp_decision;
    }

    function createInstance(
        InitParameters calldata params
    ) external onlyOwner onlyInitialized returns (uint256 instanceId) {
        instanceId = currentInstanceId;
        Instance storage inst = instances[instanceId];
        require(!inst.exists, "instance already exists");

        inst.exists = true;
        inst.instanceId = instanceId;

        _createParticipant(
            inst,
            ParticipantKey.Participant_1p9owwo,
            params.Participant_1p9owwo_account,
            false,
            0,
            0
        );
        _createParticipant(
            inst,
            ParticipantKey.Participant_12df78t,
            params.Participant_12df78t_account,
            false,
            0,
            0
        );

        _createActionEvent(
            inst,
            EventKey.Event_0ojehz6,
            ElementState.ENABLED
        );
        _createActionEvent(
            inst,
            EventKey.Event_0ci2gl8,
            ElementState.DISABLED
        );
        _createActionEvent(
            inst,
            EventKey.Event_0dyp0ut,
            ElementState.DISABLED
        );

        _createMessage(
            inst,
            MessageKey.Message_01jq2zl,
            ParticipantKey.Participant_1p9owwo,
            ParticipantKey.Participant_12df78t,
            ElementState.DISABLED,
            "amount"
        );
        _createMessage(
            inst,
            MessageKey.Message_068kmzv,
            ParticipantKey.Participant_12df78t,
            ParticipantKey.Participant_1p9owwo,
            ElementState.DISABLED,
            "time + instance ID + logs"
        );
        _createMessage(
            inst,
            MessageKey.Message_076ulzs,
            ParticipantKey.Participant_12df78t,
            ParticipantKey.Participant_1p9owwo,
            ElementState.DISABLED,
            "time + description + EC2 resource ID + logs + other information"
        );
        _createMessage(
            inst,
            MessageKey.Message_09krt7c,
            ParticipantKey.Participant_12df78t,
            ParticipantKey.Participant_1p9owwo,
            ElementState.DISABLED,
            "question name + description"
        );
        _createMessage(
            inst,
            MessageKey.Message_0ywghlt,
            ParticipantKey.Participant_12df78t,
            ParticipantKey.Participant_1p9owwo,
            ElementState.DISABLED,
            "serviceType"
        );
        _createMessage(
            inst,
            MessageKey.Message_12n6jjk,
            ParticipantKey.Participant_12df78t,
            ParticipantKey.Participant_1p9owwo,
            ElementState.DISABLED,
            "type + duration"
        );
        _createMessage(
            inst,
            MessageKey.Message_1b1qlzd,
            ParticipantKey.Participant_1p9owwo,
            ParticipantKey.Participant_12df78t,
            ElementState.DISABLED,
            "reason + result"
        );
        _createMessage(
            inst,
            MessageKey.Message_1bhhp1n,
            ParticipantKey.Participant_12df78t,
            ParticipantKey.Participant_1p9owwo,
            ElementState.DISABLED,
            "serviceType"
        );

        _createGateway(
            inst,
            GatewayKey.Gateway_0auc3he,
            ElementState.DISABLED
        );
        _createGateway(
            inst,
            GatewayKey.Gateway_0ivv4vg,
            ElementState.DISABLED
        );
        _createGateway(
            inst,
            GatewayKey.Gateway_0jgq0a6,
            ElementState.DISABLED
        );

        _createBusinessRule(
            inst,
            keccak256(bytes("Activity_0tya4bp")),
            params.Activity_0tya4bp_content,
            params.Activity_0tya4bp_decision
        );

        currentInstanceId += 1;
    }

    // ------------------------------------------------------------------
    // Business rule handlers
    // ------------------------------------------------------------------

    function Activity_0tya4bp(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        bytes32 ruleKey = keccak256(bytes("Activity_0tya4bp"));
        BusinessRule storage br = inst.businessRules[ruleKey];
        require(br.exists, "business rule not set");
        require(br.state == ElementState.ENABLED, "business rule not enabled");

        br.state = ElementState.WAITING_FOR_CONFIRMATION;
    }

    function Activity_0tya4bp_Continue(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        bytes32 ruleKey = keccak256(bytes("Activity_0tya4bp"));
        BusinessRule storage br = inst.businessRules[ruleKey];
        require(br.state == ElementState.WAITING_FOR_CONFIRMATION, "business rule not waiting");

        br.state = ElementState.COMPLETED;
        inst.gateways[GatewayKey.Gateway_0ivv4vg].state = ElementState.ENABLED;

    }


    // ------------------------------------------------------------------
    // Workflow logic generated from DSL flows
    // ------------------------------------------------------------------

function Event_0ojehz6(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.Event_0ojehz6];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.Event_0ojehz6);
        inst.messages[MessageKey.Message_09krt7c].state = ElementState.ENABLED;

    }

function Message_01jq2zl_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_01jq2zl];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_01jq2zl, fireflyTranId);
        inst.events[EventKey.Event_0ci2gl8].state = ElementState.ENABLED;

    }

function Message_068kmzv_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_068kmzv];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_068kmzv, fireflyTranId);
        inst.gateways[GatewayKey.Gateway_0auc3he].state = ElementState.ENABLED;

    }

function Message_076ulzs_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_076ulzs];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_076ulzs, fireflyTranId);
        inst.gateways[GatewayKey.Gateway_0auc3he].state = ElementState.ENABLED;

    }

function Message_09krt7c_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_09krt7c];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_09krt7c, fireflyTranId);
        inst.gateways[GatewayKey.Gateway_0jgq0a6].state = ElementState.ENABLED;

    }

function Message_0ywghlt_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0ywghlt];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0ywghlt, fireflyTranId);
        inst.messages[MessageKey.Message_1bhhp1n].state = ElementState.DISABLED;
        inst.messages[MessageKey.Message_068kmzv].state = ElementState.ENABLED;

    }

function Message_12n6jjk_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_12n6jjk];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_12n6jjk, fireflyTranId);
        bytes32 brKey_Activity_0tya4bp = keccak256(bytes("Activity_0tya4bp"));
        inst.businessRules[brKey_Activity_0tya4bp].state = ElementState.ENABLED;

    }

function Message_1b1qlzd_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1b1qlzd];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1b1qlzd, fireflyTranId);
        inst.events[EventKey.Event_0dyp0ut].state = ElementState.ENABLED;

    }

function Message_1bhhp1n_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1bhhp1n];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1bhhp1n, fireflyTranId);
        inst.messages[MessageKey.Message_0ywghlt].state = ElementState.DISABLED;
        inst.messages[MessageKey.Message_076ulzs].state = ElementState.ENABLED;

    }

function Gateway_0auc3he(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Gateway storage g = inst.gateways[GatewayKey.Gateway_0auc3he];
        require(g.exists, "gateway not set");
        require(g.state == ElementState.ENABLED, "gateway state not allowed");

        g.state = ElementState.COMPLETED;
        emit GatewayDone(instanceId, GatewayKey.Gateway_0auc3he);
        inst.messages[MessageKey.Message_12n6jjk].state = ElementState.ENABLED;

    }

function Gateway_0ivv4vg(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Gateway storage g = inst.gateways[GatewayKey.Gateway_0ivv4vg];
        require(g.exists, "gateway not set");
        require(g.state == ElementState.ENABLED, "gateway state not allowed");

        g.state = ElementState.COMPLETED;
        emit GatewayDone(instanceId, GatewayKey.Gateway_0ivv4vg);
        inst.messages[MessageKey.Message_1b1qlzd].state = ElementState.ENABLED;
        inst.messages[MessageKey.Message_01jq2zl].state = ElementState.ENABLED;

    }

function Gateway_0jgq0a6(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Gateway storage g = inst.gateways[GatewayKey.Gateway_0jgq0a6];
        require(g.exists, "gateway not set");
        require(g.state == ElementState.ENABLED, "gateway state not allowed");

        g.state = ElementState.COMPLETED;
        emit GatewayDone(instanceId, GatewayKey.Gateway_0jgq0a6);
        inst.messages[MessageKey.Message_0ywghlt].state = ElementState.ENABLED;
        inst.messages[MessageKey.Message_1bhhp1n].state = ElementState.ENABLED;

    }

function Event_0ci2gl8(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.Event_0ci2gl8];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.Event_0ci2gl8);

    }

function Event_0dyp0ut(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.Event_0dyp0ut];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.Event_0dyp0ut);

    }
}
