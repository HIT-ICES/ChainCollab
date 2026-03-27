// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

interface IOracle {
    function getExternalData(
        uint256 instanceId,
        string calldata activityId,
        string calldata dataSource,
        string calldata outputKey
    ) external view returns (string memory value);

    function runComputeTask(
        uint256 instanceId,
        string calldata activityId,
        string calldata computeScript,
        string calldata outputKey
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
        Participant_0oa2za9,
        Participant_0jwk4tk,
        Participant_0cb2p7d
    }

    enum MessageKey {
        Message_01kcpmi,
        Message_02q44he,
        Message_05gz8u0,
        Message_0g7m9tf,
        Message_0mcktm6,
        Message_0q9hvem,
        Message_14wu8ts,
        Message_15pehvh,
        Message_1f0gefc,
        Message_1ieb8wn
    }

    enum GatewayKey {
        Gateway_1ltys0e,
        Gateway_025uwvp
    }

    enum EventKey {
        Event_0ehnwwz,        Event_0e3j88g,        Event_1o9guxu,        Event_194zr5n    }

    enum BusinessRuleKey {
        PlaceholderBusinessRule
    }

    // ------------------------------------------------------------------
    // Structs
    // ------------------------------------------------------------------

    struct StateMemory {
        string MessageContent;
        string Price;
        string Time;
        string Num;
        string OrderContent;
        string Time;
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

    function _stringToInt(string memory value) internal pure returns (int256) {
        bytes memory data = bytes(value);
        if (data.length == 0) {
            return 0;
        }

        bool negative = false;
        uint256 index = 0;
        if (data[0] == bytes1("-")) {
            negative = true;
            index = 1;
        }

        int256 result = 0;
        for (; index < data.length; index++) {
            uint8 c = uint8(data[index]);
            require(c >= 48 && c <= 57, "invalid int string");
            result = (result * 10) + int256(uint256(c - 48));
        }

        return negative ? -result : result;
    }

    function _stringToBool(string memory value) internal pure returns (bool) {
        bytes32 hashValue = keccak256(bytes(value));
        return (
            hashValue == keccak256(bytes("true")) ||
            hashValue == keccak256(bytes("TRUE")) ||
            hashValue == keccak256(bytes("1"))
        );
    }

    // ------------------------------------------------------------------
    // Instance creation
    // ------------------------------------------------------------------

    struct InitParameters {
        address identityContractAddress;
        address Participant_0oa2za9_account;
        string Participant_0oa2za9_org;
        address Participant_0jwk4tk_account;
        string Participant_0jwk4tk_org;
        address Participant_0cb2p7d_account;
        string Participant_0cb2p7d_org;
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
            ParticipantKey.Participant_0oa2za9,
            params.Participant_0oa2za9_account,
            params.Participant_0oa2za9_org,
            false,
            0,
            0
        );
        _createParticipant(
            inst,
            ParticipantKey.Participant_0jwk4tk,
            params.Participant_0jwk4tk_account,
            params.Participant_0jwk4tk_org,
            false,
            0,
            0
        );
        _createParticipant(
            inst,
            ParticipantKey.Participant_0cb2p7d,
            params.Participant_0cb2p7d_account,
            params.Participant_0cb2p7d_org,
            false,
            0,
            0
        );

        _createActionEvent(
            inst,
            EventKey.Event_0ehnwwz,
            ElementState.ENABLED
        );
        _createActionEvent(
            inst,
            EventKey.Event_0e3j88g,
            ElementState.DISABLED
        );
        _createActionEvent(
            inst,
            EventKey.Event_1o9guxu,
            ElementState.DISABLED
        );
        _createActionEvent(
            inst,
            EventKey.Event_194zr5n,
            ElementState.DISABLED
        );

        _createMessage(
            inst,
            MessageKey.Message_01kcpmi,
            ParticipantKey.Participant_0oa2za9,
            ParticipantKey.Participant_0jwk4tk,
            ElementState.DISABLED,
            "{}"
        );
        _createMessage(
            inst,
            MessageKey.Message_02q44he,
            ParticipantKey.Participant_0oa2za9,
            ParticipantKey.Participant_0jwk4tk,
            ElementState.DISABLED,
            "{}"
        );
        _createMessage(
            inst,
            MessageKey.Message_05gz8u0,
            ParticipantKey.Participant_0jwk4tk,
            ParticipantKey.Participant_0oa2za9,
            ElementState.DISABLED,
            "MessageContent"
        );
        _createMessage(
            inst,
            MessageKey.Message_0g7m9tf,
            ParticipantKey.Participant_0oa2za9,
            ParticipantKey.Participant_0jwk4tk,
            ElementState.DISABLED,
            "num + time"
        );
        _createMessage(
            inst,
            MessageKey.Message_0mcktm6,
            ParticipantKey.Participant_0jwk4tk,
            ParticipantKey.Participant_0oa2za9,
            ElementState.DISABLED,
            "Price + Time"
        );
        _createMessage(
            inst,
            MessageKey.Message_0q9hvem,
            ParticipantKey.Participant_0jwk4tk,
            ParticipantKey.Participant_0oa2za9,
            ElementState.DISABLED,
            "orderContent"
        );
        _createMessage(
            inst,
            MessageKey.Message_14wu8ts,
            ParticipantKey.Participant_0oa2za9,
            ParticipantKey.Participant_0jwk4tk,
            ElementState.DISABLED,
            "MessageContent"
        );
        _createMessage(
            inst,
            MessageKey.Message_15pehvh,
            ParticipantKey.Participant_0jwk4tk,
            ParticipantKey.Participant_0oa2za9,
            ElementState.DISABLED,
            "{}"
        );
        _createMessage(
            inst,
            MessageKey.Message_1f0gefc,
            ParticipantKey.Participant_0oa2za9,
            ParticipantKey.Participant_0jwk4tk,
            ElementState.DISABLED,
            "MessageContent"
        );
        _createMessage(
            inst,
            MessageKey.Message_1ieb8wn,
            ParticipantKey.Participant_0oa2za9,
            ParticipantKey.Participant_0jwk4tk,
            ElementState.DISABLED,
            "{}"
        );

        _createGateway(
            inst,
            GatewayKey.Gateway_1ltys0e,
            ElementState.DISABLED
        );
        _createGateway(
            inst,
            GatewayKey.Gateway_025uwvp,
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

function Event_0ehnwwz(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.Event_0ehnwwz];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.Event_0ehnwwz);
        inst.messages[MessageKey.Message_0q9hvem].state = ElementState.ENABLED;

    }

function Message_01kcpmi_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_01kcpmi];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_01kcpmi, fireflyTranId);

    }

function Message_02q44he_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_02q44he];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_02q44he, fireflyTranId);

    }

function Message_05gz8u0_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_05gz8u0];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_05gz8u0, fireflyTranId);

    }

function Message_0g7m9tf_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0g7m9tf];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0g7m9tf, fireflyTranId);

    }

function Message_0mcktm6_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0mcktm6];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0mcktm6, fireflyTranId);

    }

function Message_0q9hvem_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0q9hvem];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0q9hvem, fireflyTranId);

    }

function Message_14wu8ts_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_14wu8ts];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_14wu8ts, fireflyTranId);

    }

function Message_15pehvh_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_15pehvh];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_15pehvh, fireflyTranId);

    }

function Message_1f0gefc_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1f0gefc];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1f0gefc, fireflyTranId);

    }

function Message_1ieb8wn_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1ieb8wn];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1ieb8wn, fireflyTranId);

    }

function Gateway_1ltys0e(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Gateway storage g = inst.gateways[GatewayKey.Gateway_1ltys0e];
        require(g.exists, "gateway not set");
        require(g.state == ElementState.ENABLED, "gateway state not allowed");

        g.state = ElementState.COMPLETED;
        emit GatewayDone(instanceId, GatewayKey.Gateway_1ltys0e);
        inst.messages[MessageKey.Message_1f0gefc].state = ElementState.ENABLED;
        inst.messages[MessageKey.Message_14wu8ts].state = ElementState.ENABLED;

    }

function Gateway_025uwvp(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Gateway storage g = inst.gateways[GatewayKey.Gateway_025uwvp];
        require(g.exists, "gateway not set");
        require(g.state == ElementState.ENABLED, "gateway state not allowed");

        g.state = ElementState.COMPLETED;
        emit GatewayDone(instanceId, GatewayKey.Gateway_025uwvp);
        inst.messages[MessageKey.Message_0mcktm6].state = ElementState.ENABLED;
        inst.messages[MessageKey.Message_05gz8u0].state = ElementState.ENABLED;

    }

function Event_0e3j88g(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.Event_0e3j88g];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.Event_0e3j88g);

    }

function Event_1o9guxu(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.Event_1o9guxu];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.Event_1o9guxu);

    }

function Event_194zr5n(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.Event_194zr5n];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.Event_194zr5n);

    }
}
