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
        Participant_1080bkg,
        Participant_0sktaei
    }

    enum MessageKey {
        Message_045i10y,
        Message_0m9p3da,
        Message_0o8eyir,
        Message_0r9lypd,
        Message_1em0ee4,
        Message_1etcmvl,
        Message_1joj7ca,
        Message_1ljlm4g,
        Message_1nlagx2,
        Message_1xm9dxy
    }

    enum GatewayKey {
        ExclusiveGateway_106je4z,
        ExclusiveGateway_0hs3ztq,
        ExclusiveGateway_0nzwv7v,
        EventBasedGateway_1fxpmyn
    }

    enum EventKey {
        StartEvent_1jtgn3j,        EndEvent_0366pfz,        EndEvent_08edp7f,        EndEvent_146eii4    }

    enum BusinessRuleKey {
        PlaceholderBusinessRule
    }

    // ------------------------------------------------------------------
    // Structs
    // ------------------------------------------------------------------

    struct StateMemory {
        bool Cancel;
        bool Confirm;
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
        address Participant_1080bkg_account;
        string Participant_1080bkg_org;
        address Participant_0sktaei_account;
        string Participant_0sktaei_org;
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
            ParticipantKey.Participant_1080bkg,
            params.Participant_1080bkg_account,
            params.Participant_1080bkg_org,
            false,
            0,
            0
        );
        _createParticipant(
            inst,
            ParticipantKey.Participant_0sktaei,
            params.Participant_0sktaei_account,
            params.Participant_0sktaei_org,
            false,
            0,
            0
        );

        _createActionEvent(
            inst,
            EventKey.StartEvent_1jtgn3j,
            ElementState.ENABLED
        );
        _createActionEvent(
            inst,
            EventKey.EndEvent_0366pfz,
            ElementState.DISABLED
        );
        _createActionEvent(
            inst,
            EventKey.EndEvent_08edp7f,
            ElementState.DISABLED
        );
        _createActionEvent(
            inst,
            EventKey.EndEvent_146eii4,
            ElementState.DISABLED
        );

        _createMessage(
            inst,
            MessageKey.Message_045i10y,
            ParticipantKey.Participant_1080bkg,
            ParticipantKey.Participant_0sktaei,
            ElementState.DISABLED,
            "{}"
        );
        _createMessage(
            inst,
            MessageKey.Message_0m9p3da,
            ParticipantKey.Participant_1080bkg,
            ParticipantKey.Participant_0sktaei,
            ElementState.DISABLED,
            "{}"
        );
        _createMessage(
            inst,
            MessageKey.Message_0o8eyir,
            ParticipantKey.Participant_1080bkg,
            ParticipantKey.Participant_0sktaei,
            ElementState.DISABLED,
            "{}"
        );
        _createMessage(
            inst,
            MessageKey.Message_0r9lypd,
            ParticipantKey.Participant_0sktaei,
            ParticipantKey.Participant_1080bkg,
            ElementState.DISABLED,
            "{}"
        );
        _createMessage(
            inst,
            MessageKey.Message_1em0ee4,
            ParticipantKey.Participant_0sktaei,
            ParticipantKey.Participant_1080bkg,
            ElementState.DISABLED,
            "{}"
        );
        _createMessage(
            inst,
            MessageKey.Message_1etcmvl,
            ParticipantKey.Participant_0sktaei,
            ParticipantKey.Participant_1080bkg,
            ElementState.DISABLED,
            "{}"
        );
        _createMessage(
            inst,
            MessageKey.Message_1joj7ca,
            ParticipantKey.Participant_1080bkg,
            ParticipantKey.Participant_0sktaei,
            ElementState.DISABLED,
            "{}"
        );
        _createMessage(
            inst,
            MessageKey.Message_1ljlm4g,
            ParticipantKey.Participant_0sktaei,
            ParticipantKey.Participant_1080bkg,
            ElementState.DISABLED,
            "{}"
        );
        _createMessage(
            inst,
            MessageKey.Message_1nlagx2,
            ParticipantKey.Participant_1080bkg,
            ParticipantKey.Participant_0sktaei,
            ElementState.DISABLED,
            "{}"
        );
        _createMessage(
            inst,
            MessageKey.Message_1xm9dxy,
            ParticipantKey.Participant_1080bkg,
            ParticipantKey.Participant_0sktaei,
            ElementState.DISABLED,
            "{}"
        );

        _createGateway(
            inst,
            GatewayKey.ExclusiveGateway_106je4z,
            ElementState.DISABLED
        );
        _createGateway(
            inst,
            GatewayKey.ExclusiveGateway_0hs3ztq,
            ElementState.DISABLED
        );
        _createGateway(
            inst,
            GatewayKey.ExclusiveGateway_0nzwv7v,
            ElementState.DISABLED
        );
        _createGateway(
            inst,
            GatewayKey.EventBasedGateway_1fxpmyn,
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

function StartEvent_1jtgn3j(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.StartEvent_1jtgn3j];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.StartEvent_1jtgn3j);
        inst.gateways[GatewayKey.ExclusiveGateway_0hs3ztq].state = ElementState.ENABLED;

    }

function Message_045i10y_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_045i10y];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_045i10y, fireflyTranId);

    }

function Message_0m9p3da_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0m9p3da];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0m9p3da, fireflyTranId);

    }

function Message_0o8eyir_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0o8eyir];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0o8eyir, fireflyTranId);

    }

function Message_0r9lypd_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0r9lypd];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0r9lypd, fireflyTranId);

    }

function Message_1em0ee4_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1em0ee4];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1em0ee4, fireflyTranId);

    }

function Message_1etcmvl_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1etcmvl];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1etcmvl, fireflyTranId);

    }

function Message_1joj7ca_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1joj7ca];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1joj7ca, fireflyTranId);

    }

function Message_1ljlm4g_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1ljlm4g];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1ljlm4g, fireflyTranId);

    }

function Message_1nlagx2_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1nlagx2];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1nlagx2, fireflyTranId);

    }

function Message_1xm9dxy_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1xm9dxy];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1xm9dxy, fireflyTranId);

    }

function ExclusiveGateway_106je4z(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Gateway storage g = inst.gateways[GatewayKey.ExclusiveGateway_106je4z];
        require(g.exists, "gateway not set");
        require(g.state == ElementState.ENABLED, "gateway state not allowed");

        g.state = ElementState.COMPLETED;
        emit GatewayDone(instanceId, GatewayKey.ExclusiveGateway_106je4z);
        if (inst.stateMemory.Confirm == true) {
            inst.messages[MessageKey.Message_1em0ee4].state = ElementState.ENABLED;
        }
        else if (inst.stateMemory.Confirm == false) {
            inst.gateways[GatewayKey.ExclusiveGateway_0hs3ztq].state = ElementState.ENABLED;
        }

    }

function ExclusiveGateway_0hs3ztq(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Gateway storage g = inst.gateways[GatewayKey.ExclusiveGateway_0hs3ztq];
        require(g.exists, "gateway not set");
        require(g.state == ElementState.ENABLED, "gateway state not allowed");

        g.state = ElementState.COMPLETED;
        emit GatewayDone(instanceId, GatewayKey.ExclusiveGateway_0hs3ztq);
        inst.messages[MessageKey.Message_045i10y].state = ElementState.ENABLED;

    }

function ExclusiveGateway_0nzwv7v(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Gateway storage g = inst.gateways[GatewayKey.ExclusiveGateway_0nzwv7v];
        require(g.exists, "gateway not set");
        require(g.state == ElementState.ENABLED, "gateway state not allowed");

        g.state = ElementState.COMPLETED;
        emit GatewayDone(instanceId, GatewayKey.ExclusiveGateway_0nzwv7v);
        if (inst.stateMemory.Cancel == false) {
            inst.events[EventKey.EndEvent_08edp7f].state = ElementState.ENABLED;
        }
        else if (inst.stateMemory.Cancel == true) {
            inst.messages[MessageKey.Message_1joj7ca].state = ElementState.ENABLED;
        }

    }

function EventBasedGateway_1fxpmyn(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Gateway storage g = inst.gateways[GatewayKey.EventBasedGateway_1fxpmyn];
        require(g.exists, "gateway not set");
        require(g.state == ElementState.ENABLED, "gateway state not allowed");

        g.state = ElementState.COMPLETED;
        emit GatewayDone(instanceId, GatewayKey.EventBasedGateway_1fxpmyn);
        inst.messages[MessageKey.Message_0o8eyir].state = ElementState.ENABLED;
        inst.messages[MessageKey.Message_1xm9dxy].state = ElementState.ENABLED;

    }

function EndEvent_0366pfz(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.EndEvent_0366pfz];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.EndEvent_0366pfz);

    }

function EndEvent_08edp7f(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.EndEvent_08edp7f];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.EndEvent_08edp7f);

    }

function EndEvent_146eii4(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.EndEvent_146eii4];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.EndEvent_146eii4);

    }
}
