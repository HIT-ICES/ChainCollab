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
        Participant_0ykkst0,
        Participant_1be5jmm
    }

    enum MessageKey {
        Message_03avvjh,
        Message_05o1aax,
        Message_08gg8ej,
        Message_0vzhrso,
        Message_1b9cl8r,
        Message_1br1kb3,
        Message_1f5hev8,
        Message_1nq7msq,
        Message_1vlpo12
    }

    enum GatewayKey {
        Gateway_0fkskz5
    }

    enum EventKey {
        Event_1kw6wq7,        Event_0k561h7,        Event_1tsex1f    }

    enum BusinessRuleKey {
        PlaceholderBusinessRule
    }

    // ------------------------------------------------------------------
    // Structs
    // ------------------------------------------------------------------

    struct StateMemory {
        string ConcelAck;
        string InvoiceContent;
        string OrderContent;
        string QuoteContent;
        string QuoteRequest;
        string Cancelation;
        string Confirm_message;
        string PayRecord;
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
        address Participant_0ykkst0_account;
        string Participant_0ykkst0_org;
        address Participant_1be5jmm_account;
        string Participant_1be5jmm_org;
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
            ParticipantKey.Participant_0ykkst0,
            params.Participant_0ykkst0_account,
            params.Participant_0ykkst0_org,
            false,
            0,
            0
        );
        _createParticipant(
            inst,
            ParticipantKey.Participant_1be5jmm,
            params.Participant_1be5jmm_account,
            params.Participant_1be5jmm_org,
            false,
            0,
            0
        );

        _createActionEvent(
            inst,
            EventKey.Event_1kw6wq7,
            ElementState.ENABLED
        );
        _createActionEvent(
            inst,
            EventKey.Event_0k561h7,
            ElementState.DISABLED
        );
        _createActionEvent(
            inst,
            EventKey.Event_1tsex1f,
            ElementState.DISABLED
        );

        _createMessage(
            inst,
            MessageKey.Message_03avvjh,
            ParticipantKey.Participant_0ykkst0,
            ParticipantKey.Participant_1be5jmm,
            ElementState.DISABLED,
            "cancelation"
        );
        _createMessage(
            inst,
            MessageKey.Message_05o1aax,
            ParticipantKey.Participant_0ykkst0,
            ParticipantKey.Participant_1be5jmm,
            ElementState.DISABLED,
            "payRecord"
        );
        _createMessage(
            inst,
            MessageKey.Message_08gg8ej,
            ParticipantKey.Participant_1be5jmm,
            ParticipantKey.Participant_0ykkst0,
            ElementState.DISABLED,
            "{}"
        );
        _createMessage(
            inst,
            MessageKey.Message_0vzhrso,
            ParticipantKey.Participant_0ykkst0,
            ParticipantKey.Participant_1be5jmm,
            ElementState.DISABLED,
            "OrderContent"
        );
        _createMessage(
            inst,
            MessageKey.Message_1b9cl8r,
            ParticipantKey.Participant_1be5jmm,
            ParticipantKey.Participant_0ykkst0,
            ElementState.DISABLED,
            "ConcelAck"
        );
        _createMessage(
            inst,
            MessageKey.Message_1br1kb3,
            ParticipantKey.Participant_1be5jmm,
            ParticipantKey.Participant_0ykkst0,
            ElementState.DISABLED,
            "QuoteContent"
        );
        _createMessage(
            inst,
            MessageKey.Message_1f5hev8,
            ParticipantKey.Participant_0ykkst0,
            ParticipantKey.Participant_1be5jmm,
            ElementState.DISABLED,
            "confirm message"
        );
        _createMessage(
            inst,
            MessageKey.Message_1nq7msq,
            ParticipantKey.Participant_0ykkst0,
            ParticipantKey.Participant_1be5jmm,
            ElementState.DISABLED,
            "QuoteRequest"
        );
        _createMessage(
            inst,
            MessageKey.Message_1vlpo12,
            ParticipantKey.Participant_1be5jmm,
            ParticipantKey.Participant_0ykkst0,
            ElementState.DISABLED,
            "InvoiceContent"
        );

        _createGateway(
            inst,
            GatewayKey.Gateway_0fkskz5,
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

function Event_1kw6wq7(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.Event_1kw6wq7];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.Event_1kw6wq7);
        inst.messages[MessageKey.Message_1nq7msq].state = ElementState.ENABLED;

    }

function Message_03avvjh_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_03avvjh];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_03avvjh, fireflyTranId);

    }

function Message_05o1aax_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_05o1aax];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_05o1aax, fireflyTranId);

    }

function Message_08gg8ej_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_08gg8ej];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_08gg8ej, fireflyTranId);

    }

function Message_0vzhrso_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0vzhrso];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0vzhrso, fireflyTranId);

    }

function Message_1b9cl8r_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1b9cl8r];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1b9cl8r, fireflyTranId);

    }

function Message_1br1kb3_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1br1kb3];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1br1kb3, fireflyTranId);

    }

function Message_1f5hev8_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1f5hev8];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1f5hev8, fireflyTranId);

    }

function Message_1nq7msq_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1nq7msq];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1nq7msq, fireflyTranId);

    }

function Message_1vlpo12_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1vlpo12];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1vlpo12, fireflyTranId);

    }

function Gateway_0fkskz5(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Gateway storage g = inst.gateways[GatewayKey.Gateway_0fkskz5];
        require(g.exists, "gateway not set");
        require(g.state == ElementState.ENABLED, "gateway state not allowed");

        g.state = ElementState.COMPLETED;
        emit GatewayDone(instanceId, GatewayKey.Gateway_0fkskz5);
        inst.messages[MessageKey.Message_03avvjh].state = ElementState.ENABLED;
        inst.messages[MessageKey.Message_1f5hev8].state = ElementState.ENABLED;

    }

function Event_0k561h7(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.Event_0k561h7];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.Event_0k561h7);

    }

function Event_1tsex1f(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.Event_1tsex1f];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.Event_1tsex1f);

    }
}
