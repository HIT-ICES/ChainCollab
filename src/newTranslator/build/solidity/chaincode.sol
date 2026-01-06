// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

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
        Participant_0w6qkdf,
        Participant_19mgbdn,
        Participant_09cjol2,
        Participant_0sa2v7d,
        Participant_19j1e3o
    }

    enum MessageKey {
        Message_04wmlqe,
        Message_0cba4t6,
        Message_0d2xte5,
        Message_0hpha6h,
        Message_0pm90nx,
        Message_0ps2yzo,
        Message_0rwz1km,
        Message_196q1fj,
        Message_1ajdm9l,
        Message_1io2g9u,
        Message_1wswgqu
    }

    enum GatewayKey {
        Gateway_11hmo2k,
        Gateway_0onpe6x,
        Gateway_1fbifca
    }

    enum EventKey {
        Event_06sexe6,
        Event_13pbqdz,
        Event_0eoqvir
    }

    // ------------------------------------------------------------------
    // Structs
    // ------------------------------------------------------------------

    struct StateMemory {
        bool Self_pickup;
        int256 Amount;
        string Del_order;
        string Deliver;
        string Fwd_order;
        string Order;
        string Placed_order;
        string Pre_details;
        string Report;
        string Req_details;
        string Transport_order;
        string Waybill;
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
        address Participant_0w6qkdf_account;
        address Participant_19mgbdn_account;
        address Participant_09cjol2_account;
        address Participant_0sa2v7d_account;
        address Participant_19j1e3o_account;
        string Activity_0fbi09z_content;
        string Activity_0fbi09z_decision;
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
            ParticipantKey.Participant_0w6qkdf,
            params.Participant_0w6qkdf_account,
            false,
            0,
            0
        );
        _createParticipant(
            inst,
            ParticipantKey.Participant_19mgbdn,
            params.Participant_19mgbdn_account,
            false,
            0,
            0
        );
        _createParticipant(
            inst,
            ParticipantKey.Participant_09cjol2,
            params.Participant_09cjol2_account,
            false,
            0,
            0
        );
        _createParticipant(
            inst,
            ParticipantKey.Participant_0sa2v7d,
            params.Participant_0sa2v7d_account,
            false,
            0,
            0
        );
        _createParticipant(
            inst,
            ParticipantKey.Participant_19j1e3o,
            params.Participant_19j1e3o_account,
            false,
            0,
            0
        );

        _createActionEvent(
            inst,
            EventKey.Event_06sexe6,
            ElementState.ENABLED
        );
        _createActionEvent(
            inst,
            EventKey.Event_13pbqdz,
            ElementState.DISABLED
        );
        _createActionEvent(
            inst,
            EventKey.Event_0eoqvir,
            ElementState.DISABLED
        );

        _createMessage(
            inst,
            MessageKey.Message_04wmlqe,
            ParticipantKey.Participant_19mgbdn,
            ParticipantKey.Participant_0w6qkdf,
            ElementState.DISABLED,
            "report"
        );
        _createMessage(
            inst,
            MessageKey.Message_0cba4t6,
            ParticipantKey.Participant_0w6qkdf,
            ParticipantKey.Participant_0sa2v7d,
            ElementState.DISABLED,
            "fwd_order"
        );
        _createMessage(
            inst,
            MessageKey.Message_0d2xte5,
            ParticipantKey.Participant_19j1e3o,
            ParticipantKey.Participant_19mgbdn,
            ElementState.DISABLED,
            "del_order"
        );
        _createMessage(
            inst,
            MessageKey.Message_0hpha6h,
            ParticipantKey.Participant_0sa2v7d,
            ParticipantKey.Participant_19j1e3o,
            ElementState.DISABLED,
            "pre_details"
        );
        _createMessage(
            inst,
            MessageKey.Message_0pm90nx,
            ParticipantKey.Participant_0w6qkdf,
            ParticipantKey.Participant_19j1e3o,
            ElementState.DISABLED,
            "transport_order"
        );
        _createMessage(
            inst,
            MessageKey.Message_0ps2yzo,
            ParticipantKey.Participant_0w6qkdf,
            ParticipantKey.Participant_19mgbdn,
            ElementState.DISABLED,
            "Self_pickup"
        );
        _createMessage(
            inst,
            MessageKey.Message_0rwz1km,
            ParticipantKey.Participant_19j1e3o,
            ParticipantKey.Participant_0sa2v7d,
            ElementState.DISABLED,
            "req_details"
        );
        _createMessage(
            inst,
            MessageKey.Message_196q1fj,
            ParticipantKey.Participant_19mgbdn,
            ParticipantKey.Participant_0w6qkdf,
            ElementState.DISABLED,
            "deliver"
        );
        _createMessage(
            inst,
            MessageKey.Message_1ajdm9l,
            ParticipantKey.Participant_19mgbdn,
            ParticipantKey.Participant_09cjol2,
            ElementState.DISABLED,
            "placed_order"
        );
        _createMessage(
            inst,
            MessageKey.Message_1io2g9u,
            ParticipantKey.Participant_0sa2v7d,
            ParticipantKey.Participant_19j1e3o,
            ElementState.DISABLED,
            "waybill"
        );
        _createMessage(
            inst,
            MessageKey.Message_1wswgqu,
            ParticipantKey.Participant_0w6qkdf,
            ParticipantKey.Participant_19mgbdn,
            ElementState.DISABLED,
            "order + amount"
        );

        _createGateway(
            inst,
            GatewayKey.Gateway_11hmo2k,
            ElementState.DISABLED
        );
        _createGateway(
            inst,
            GatewayKey.Gateway_0onpe6x,
            ElementState.DISABLED
        );
        _createGateway(
            inst,
            GatewayKey.Gateway_1fbifca,
            ElementState.DISABLED
        );

        _createBusinessRule(
            inst,
            keccak256(bytes("Activity_0fbi09z")),
            params.Activity_0fbi09z_content,
            params.Activity_0fbi09z_decision
        );

        currentInstanceId += 1;
    }

    // ------------------------------------------------------------------
    // Business rule handlers
    // ------------------------------------------------------------------

    function Activity_0fbi09z(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        bytes32 ruleKey = keccak256(bytes("Activity_0fbi09z"));
        BusinessRule storage br = inst.businessRules[ruleKey];
        require(br.exists, "business rule not set");
        require(br.state == ElementState.ENABLED, "business rule not enabled");

        br.state = ElementState.WAITING_FOR_CONFIRMATION;
    }

    function Activity_0fbi09z_Continue(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        bytes32 ruleKey = keccak256(bytes("Activity_0fbi09z"));
        BusinessRule storage br = inst.businessRules[ruleKey];
        require(br.state == ElementState.WAITING_FOR_CONFIRMATION, "business rule not waiting");

        br.state = ElementState.COMPLETED;
        inst.gateways[GatewayKey.Gateway_11hmo2k].state = ElementState.ENABLED;

    }


    // ------------------------------------------------------------------
    // Workflow logic generated from DSL flows
    // ------------------------------------------------------------------

function Event_06sexe6(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.Event_06sexe6];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.Event_06sexe6);
        inst.messages[MessageKey.Message_1wswgqu].state = ElementState.ENABLED;

    }

function Message_04wmlqe_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_04wmlqe];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_04wmlqe, fireflyTranId);

    }

function Message_0cba4t6_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0cba4t6];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0cba4t6, fireflyTranId);

    }

function Message_0d2xte5_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0d2xte5];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0d2xte5, fireflyTranId);

    }

function Message_0hpha6h_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0hpha6h];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0hpha6h, fireflyTranId);

    }

function Message_0pm90nx_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0pm90nx];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0pm90nx, fireflyTranId);

    }

function Message_0ps2yzo_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0ps2yzo];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0ps2yzo, fireflyTranId);

    }

function Message_0rwz1km_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0rwz1km];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0rwz1km, fireflyTranId);

    }

function Message_196q1fj_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_196q1fj];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_196q1fj, fireflyTranId);

    }

function Message_1ajdm9l_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1ajdm9l];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1ajdm9l, fireflyTranId);

    }

function Message_1io2g9u_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1io2g9u];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1io2g9u, fireflyTranId);

    }

function Message_1wswgqu_Send(uint256 instanceId, string calldata fireflyTranId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1wswgqu];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1wswgqu, fireflyTranId);

    }

function Gateway_11hmo2k(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Gateway storage g = inst.gateways[GatewayKey.Gateway_11hmo2k];
        require(g.exists, "gateway not set");
        require(g.state == ElementState.ENABLED, "gateway state not allowed");

        g.state = ElementState.COMPLETED;
        emit GatewayDone(instanceId, GatewayKey.Gateway_11hmo2k);
        if (keccak256(bytes(inst.stateMemory.Deliver)) == keccak256(bytes("false"))) {
            inst.messages[MessageKey.Message_196q1fj].state = ElementState.ENABLED;
        }
        else if (keccak256(bytes(inst.stateMemory.Deliver)) == keccak256(bytes("true"))) {
            inst.events[EventKey.Event_0eoqvir].state = ElementState.ENABLED;
        }

    }

function Gateway_0onpe6x(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Gateway storage g = inst.gateways[GatewayKey.Gateway_0onpe6x];
        require(g.exists, "gateway not set");
        require(g.state == ElementState.ENABLED, "gateway state not allowed");

        g.state = ElementState.COMPLETED;
        emit GatewayDone(instanceId, GatewayKey.Gateway_0onpe6x);
        inst.messages[MessageKey.Message_0cba4t6].state = ElementState.ENABLED;
        inst.messages[MessageKey.Message_0pm90nx].state = ElementState.ENABLED;

    }

function Gateway_1fbifca(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Gateway storage g = inst.gateways[GatewayKey.Gateway_1fbifca];
        require(g.exists, "gateway not set");
        require(g.state == ElementState.ENABLED, "gateway state not allowed");

        g.state = ElementState.COMPLETED;
        emit GatewayDone(instanceId, GatewayKey.Gateway_1fbifca);
        if (!(inst.messages[MessageKey.Message_0cba4t6].state == ElementState.COMPLETED && inst.messages[MessageKey.Message_0pm90nx].state == ElementState.COMPLETED)) {
                    revert("Parallel gateway prerequisites not met");
                }
        inst.messages[MessageKey.Message_0rwz1km].state = ElementState.ENABLED;

    }

function Event_13pbqdz(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.Event_13pbqdz];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.Event_13pbqdz);

    }

function Event_0eoqvir(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.Event_0eoqvir];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.Event_0eoqvir);

    }
}
