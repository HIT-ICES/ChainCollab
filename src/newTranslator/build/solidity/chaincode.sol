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
        Participant_1jz106x,
        Participant_0jcddbb,
        Participant_0c1qh31
    }

    enum MessageKey {
        Message_009a0bz,
        Message_02ckm6k,
        Message_06bv1qa,
        Message_0b1e9t1,
        Message_0cq2w1g,
        Message_0g4xpdf,
        Message_0hzpgno,
        Message_0is10sh,
        Message_0l75vce,
        Message_0lvlunm,
        Message_0nkjynd,
        Message_0psi2ab,
        Message_0to30q0,
        Message_1989eur,
        Message_1dp5xa4,
        Message_1ufjjj2
    }

    enum GatewayKey {
        ExclusiveGateway_0uhgcse,
        ExclusiveGateway_1e98v4d,
        ExclusiveGateway_04bkb0l,
        ExclusiveGateway_0cfvdeh,
        ExclusiveGateway_1ksw1j2,
        ExclusiveGateway_05xdg8u,
        ExclusiveGateway_0wc677m,
        ParallelGateway_0yw95j2,
        ParallelGateway_0himv1h,
        EventBasedGateway_1nphygh
    }

    enum EventKey {
        StartEvent_0gb8jks,
        EndEvent_11pwcmo
    }

    // ------------------------------------------------------------------
    // Structs
    // ------------------------------------------------------------------

    struct StateMemory {
        bool Ask;
        bool InsuranceReq;
        bool IsAvailable;
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
        address Participant_1jz106x_account;
        address Participant_0jcddbb_account;
        address Participant_0c1qh31_account;
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
            ParticipantKey.Participant_1jz106x,
            params.Participant_1jz106x_account,
            false,
            0,
            0
        );
        _createParticipant(
            inst,
            ParticipantKey.Participant_0jcddbb,
            params.Participant_0jcddbb_account,
            false,
            0,
            0
        );
        _createParticipant(
            inst,
            ParticipantKey.Participant_0c1qh31,
            params.Participant_0c1qh31_account,
            false,
            0,
            0
        );

        _createActionEvent(
            inst,
            EventKey.StartEvent_0gb8jks,
            ElementState.ENABLED
        );
        _createActionEvent(
            inst,
            EventKey.EndEvent_11pwcmo,
            ElementState.DISABLED
        );

        _createMessage(
            inst,
            MessageKey.Message_009a0bz,
            ParticipantKey.Participant_1jz106x,
            ParticipantKey.Participant_0jcddbb,
            ElementState.DISABLED,
            "{}"
        );
        _createMessage(
            inst,
            MessageKey.Message_02ckm6k,
            ParticipantKey.Participant_0jcddbb,
            ParticipantKey.Participant_1jz106x,
            ElementState.DISABLED,
            "{}"
        );
        _createMessage(
            inst,
            MessageKey.Message_06bv1qa,
            ParticipantKey.Participant_1jz106x,
            ParticipantKey.Participant_0jcddbb,
            ElementState.DISABLED,
            "{}"
        );
        _createMessage(
            inst,
            MessageKey.Message_0b1e9t1,
            ParticipantKey.Participant_1jz106x,
            ParticipantKey.Participant_0jcddbb,
            ElementState.DISABLED,
            "{}"
        );
        _createMessage(
            inst,
            MessageKey.Message_0cq2w1g,
            ParticipantKey.Participant_0jcddbb,
            ParticipantKey.Participant_1jz106x,
            ElementState.DISABLED,
            "{}"
        );
        _createMessage(
            inst,
            MessageKey.Message_0g4xpdf,
            ParticipantKey.Participant_1jz106x,
            ParticipantKey.Participant_0jcddbb,
            ElementState.DISABLED,
            "{}"
        );
        _createMessage(
            inst,
            MessageKey.Message_0hzpgno,
            ParticipantKey.Participant_1jz106x,
            ParticipantKey.Participant_0jcddbb,
            ElementState.DISABLED,
            "{}"
        );
        _createMessage(
            inst,
            MessageKey.Message_0is10sh,
            ParticipantKey.Participant_1jz106x,
            ParticipantKey.Participant_0jcddbb,
            ElementState.DISABLED,
            "{}"
        );
        _createMessage(
            inst,
            MessageKey.Message_0l75vce,
            ParticipantKey.Participant_0jcddbb,
            ParticipantKey.Participant_1jz106x,
            ElementState.DISABLED,
            "{}"
        );
        _createMessage(
            inst,
            MessageKey.Message_0lvlunm,
            ParticipantKey.Participant_0c1qh31,
            ParticipantKey.Participant_0jcddbb,
            ElementState.DISABLED,
            "{}"
        );
        _createMessage(
            inst,
            MessageKey.Message_0nkjynd,
            ParticipantKey.Participant_0jcddbb,
            ParticipantKey.Participant_1jz106x,
            ElementState.DISABLED,
            "{}"
        );
        _createMessage(
            inst,
            MessageKey.Message_0psi2ab,
            ParticipantKey.Participant_0jcddbb,
            ParticipantKey.Participant_0c1qh31,
            ElementState.DISABLED,
            "{}"
        );
        _createMessage(
            inst,
            MessageKey.Message_0to30q0,
            ParticipantKey.Participant_0jcddbb,
            ParticipantKey.Participant_1jz106x,
            ElementState.DISABLED,
            "{}"
        );
        _createMessage(
            inst,
            MessageKey.Message_1989eur,
            ParticipantKey.Participant_0jcddbb,
            ParticipantKey.Participant_1jz106x,
            ElementState.DISABLED,
            "{}"
        );
        _createMessage(
            inst,
            MessageKey.Message_1dp5xa4,
            ParticipantKey.Participant_0jcddbb,
            ParticipantKey.Participant_1jz106x,
            ElementState.DISABLED,
            "{}"
        );
        _createMessage(
            inst,
            MessageKey.Message_1ufjjj2,
            ParticipantKey.Participant_1jz106x,
            ParticipantKey.Participant_0jcddbb,
            ElementState.DISABLED,
            "{}"
        );

        _createGateway(
            inst,
            GatewayKey.ExclusiveGateway_0uhgcse,
            ElementState.DISABLED
        );
        _createGateway(
            inst,
            GatewayKey.ExclusiveGateway_1e98v4d,
            ElementState.DISABLED
        );
        _createGateway(
            inst,
            GatewayKey.ExclusiveGateway_04bkb0l,
            ElementState.DISABLED
        );
        _createGateway(
            inst,
            GatewayKey.ExclusiveGateway_0cfvdeh,
            ElementState.DISABLED
        );
        _createGateway(
            inst,
            GatewayKey.ExclusiveGateway_1ksw1j2,
            ElementState.DISABLED
        );
        _createGateway(
            inst,
            GatewayKey.ExclusiveGateway_05xdg8u,
            ElementState.DISABLED
        );
        _createGateway(
            inst,
            GatewayKey.ExclusiveGateway_0wc677m,
            ElementState.DISABLED
        );
        _createGateway(
            inst,
            GatewayKey.ParallelGateway_0yw95j2,
            ElementState.DISABLED
        );
        _createGateway(
            inst,
            GatewayKey.ParallelGateway_0himv1h,
            ElementState.DISABLED
        );
        _createGateway(
            inst,
            GatewayKey.EventBasedGateway_1nphygh,
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

function StartEvent_0gb8jks(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.StartEvent_0gb8jks];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.StartEvent_0gb8jks);
        inst.gateways[GatewayKey.ExclusiveGateway_0uhgcse].state = ElementState.ENABLED;

    }

function Message_009a0bz_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_009a0bz];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_009a0bz, fireflyTranId);

    }

function Message_02ckm6k_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_02ckm6k];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_02ckm6k, fireflyTranId);

    }

function Message_06bv1qa_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_06bv1qa];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_06bv1qa, fireflyTranId);

    }

function Message_0b1e9t1_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0b1e9t1];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0b1e9t1, fireflyTranId);

    }

function Message_0cq2w1g_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0cq2w1g];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0cq2w1g, fireflyTranId);

    }

function Message_0g4xpdf_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0g4xpdf];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0g4xpdf, fireflyTranId);

    }

function Message_0hzpgno_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0hzpgno];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0hzpgno, fireflyTranId);

    }

function Message_0is10sh_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0is10sh];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0is10sh, fireflyTranId);

    }

function Message_0l75vce_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0l75vce];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0l75vce, fireflyTranId);

    }

function Message_0lvlunm_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0lvlunm];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0lvlunm, fireflyTranId);

    }

function Message_0nkjynd_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0nkjynd];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0nkjynd, fireflyTranId);

    }

function Message_0psi2ab_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0psi2ab];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0psi2ab, fireflyTranId);

    }

function Message_0to30q0_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0to30q0];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0to30q0, fireflyTranId);

    }

function Message_1989eur_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1989eur];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1989eur, fireflyTranId);

    }

function Message_1dp5xa4_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1dp5xa4];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1dp5xa4, fireflyTranId);

    }

function Message_1ufjjj2_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1ufjjj2];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1ufjjj2, fireflyTranId);

    }

function ExclusiveGateway_0uhgcse(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Gateway storage g = inst.gateways[GatewayKey.ExclusiveGateway_0uhgcse];
        require(g.exists, "gateway not set");
        require(g.state == ElementState.ENABLED, "gateway state not allowed");

        g.state = ElementState.COMPLETED;
        emit GatewayDone(instanceId, GatewayKey.ExclusiveGateway_0uhgcse);
        inst.messages[MessageKey.Message_02ckm6k].state = ElementState.ENABLED;

    }

function ExclusiveGateway_1e98v4d(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Gateway storage g = inst.gateways[GatewayKey.ExclusiveGateway_1e98v4d];
        require(g.exists, "gateway not set");
        require(g.state == ElementState.ENABLED, "gateway state not allowed");

        g.state = ElementState.COMPLETED;
        emit GatewayDone(instanceId, GatewayKey.ExclusiveGateway_1e98v4d);
        if (inst.stateMemory.IsAvailable == false) {
            inst.gateways[GatewayKey.ExclusiveGateway_0uhgcse].state = ElementState.ENABLED;
        }
        else if (inst.stateMemory.IsAvailable == true) {
            inst.messages[MessageKey.Message_0l75vce].state = ElementState.ENABLED;
        }

    }

function ExclusiveGateway_04bkb0l(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Gateway storage g = inst.gateways[GatewayKey.ExclusiveGateway_04bkb0l];
        require(g.exists, "gateway not set");
        require(g.state == ElementState.ENABLED, "gateway state not allowed");

        g.state = ElementState.COMPLETED;
        emit GatewayDone(instanceId, GatewayKey.ExclusiveGateway_04bkb0l);
        if (inst.stateMemory.Ask == true) {
            inst.messages[MessageKey.Message_0to30q0].state = ElementState.ENABLED;
        }
        else if (inst.stateMemory.Ask == false) {
            inst.gateways[GatewayKey.ExclusiveGateway_0cfvdeh].state = ElementState.ENABLED;
        }

    }

function ExclusiveGateway_0cfvdeh(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Gateway storage g = inst.gateways[GatewayKey.ExclusiveGateway_0cfvdeh];
        require(g.exists, "gateway not set");
        require(g.state == ElementState.ENABLED, "gateway state not allowed");

        g.state = ElementState.COMPLETED;
        emit GatewayDone(instanceId, GatewayKey.ExclusiveGateway_0cfvdeh);
        inst.gateways[GatewayKey.ExclusiveGateway_1ksw1j2].state = ElementState.ENABLED;

    }

function ExclusiveGateway_1ksw1j2(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Gateway storage g = inst.gateways[GatewayKey.ExclusiveGateway_1ksw1j2];
        require(g.exists, "gateway not set");
        require(g.state == ElementState.ENABLED, "gateway state not allowed");

        g.state = ElementState.COMPLETED;
        emit GatewayDone(instanceId, GatewayKey.ExclusiveGateway_1ksw1j2);
        inst.messages[MessageKey.Message_1dp5xa4].state = ElementState.ENABLED;

    }

function ExclusiveGateway_05xdg8u(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Gateway storage g = inst.gateways[GatewayKey.ExclusiveGateway_05xdg8u];
        require(g.exists, "gateway not set");
        require(g.state == ElementState.ENABLED, "gateway state not allowed");

        g.state = ElementState.COMPLETED;
        emit GatewayDone(instanceId, GatewayKey.ExclusiveGateway_05xdg8u);
        if (inst.stateMemory.InsuranceReq == false) {
            inst.gateways[GatewayKey.ExclusiveGateway_0wc677m].state = ElementState.ENABLED;
        }
        else if (inst.stateMemory.InsuranceReq == true) {
            inst.messages[MessageKey.Message_009a0bz].state = ElementState.ENABLED;
        }

    }

function ExclusiveGateway_0wc677m(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Gateway storage g = inst.gateways[GatewayKey.ExclusiveGateway_0wc677m];
        require(g.exists, "gateway not set");
        require(g.state == ElementState.ENABLED, "gateway state not allowed");

        g.state = ElementState.COMPLETED;
        emit GatewayDone(instanceId, GatewayKey.ExclusiveGateway_0wc677m);
        inst.messages[MessageKey.Message_0nkjynd].state = ElementState.ENABLED;

    }

function ParallelGateway_0yw95j2(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Gateway storage g = inst.gateways[GatewayKey.ParallelGateway_0yw95j2];
        require(g.exists, "gateway not set");
        require(g.state == ElementState.ENABLED, "gateway state not allowed");

        g.state = ElementState.COMPLETED;
        emit GatewayDone(instanceId, GatewayKey.ParallelGateway_0yw95j2);
        inst.messages[MessageKey.Message_0g4xpdf].state = ElementState.ENABLED;
        inst.messages[MessageKey.Message_0is10sh].state = ElementState.ENABLED;

    }

function ParallelGateway_0himv1h(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Gateway storage g = inst.gateways[GatewayKey.ParallelGateway_0himv1h];
        require(g.exists, "gateway not set");
        require(g.state == ElementState.ENABLED, "gateway state not allowed");

        g.state = ElementState.COMPLETED;
        emit GatewayDone(instanceId, GatewayKey.ParallelGateway_0himv1h);
        if (!(inst.messages[MessageKey.Message_0is10sh].state == ElementState.COMPLETED && inst.messages[MessageKey.Message_0g4xpdf].state == ElementState.COMPLETED)) {
                    revert("Parallel gateway prerequisites not met");
                }
        inst.events[EventKey.EndEvent_11pwcmo].state = ElementState.ENABLED;

    }

function EventBasedGateway_1nphygh(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Gateway storage g = inst.gateways[GatewayKey.EventBasedGateway_1nphygh];
        require(g.exists, "gateway not set");
        require(g.state == ElementState.ENABLED, "gateway state not allowed");

        g.state = ElementState.COMPLETED;
        emit GatewayDone(instanceId, GatewayKey.EventBasedGateway_1nphygh);
        inst.messages[MessageKey.Message_0cq2w1g].state = ElementState.ENABLED;
        inst.messages[MessageKey.Message_1989eur].state = ElementState.ENABLED;

    }

function EndEvent_11pwcmo(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.EndEvent_11pwcmo];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.EndEvent_11pwcmo);

    }
}
