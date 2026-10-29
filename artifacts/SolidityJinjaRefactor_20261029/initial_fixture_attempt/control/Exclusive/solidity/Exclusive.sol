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

interface IDmnLite {
    function requestDMNDecision(
        string calldata url,
        string calldata dmnCid,
        string calldata decisionId,
        string calldata inputData
    ) external returns (bytes32 requestId);

    function getRequestStatus(bytes32 requestId)
        external
        view
        returns (
            uint8 state,
            address requester,
            uint256 createdAt,
            uint256 fulfilledAt,
            bool exists
        );

    function getRawByRequestId(bytes32 requestId) external view returns (string memory);
}

interface IIdentityRegistry {
    function getIdentityOrg(address identityAddress) external view returns (string memory);
}

contract Exclusive {
    enum ElementState {
        DISABLED,
        ENABLED,
        WAITING_FOR_CONFIRMATION,
        COMPLETED
    }

    enum ParticipantKey {
        Participant_127fmp5,
        Participant_1i0wkot
    }

    enum MessageKey {
        Message_1kt861j
    }

    enum GatewayKey {
        Gateway_1309cek
    }

    enum EventKey {
        Event_1ex6tww,        Event_1w9hecu,        Event_0azwphb,        Event_13dkewm,        Event_0if27w4,        Event_1tsrojw,        Event_0ox11yo,        Event_00uq91w,        Event_1eluy7v,        Event_0a9rmyh    }

    enum BusinessRuleKey {
        PlaceholderBusinessRule
    }

    struct StateMemory {
        int256 Condition;
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
    }

    struct Gateway {
        bool exists;
        ElementState state;
    }

    struct ActionEvent {
        bool exists;
        ElementState state;
    }

    struct BusinessRuleInit {
        string dmnCid;
        bytes32 dmnHash;
        string decisionId;
        bool callerRestricted;
        address allowedCaller;
    }

    struct BusinessRule {
        bool exists;
        string dmnCid;
        bytes32 hashOfDmn;
        string decisionId;
        bool callerRestricted;
        address allowedCaller;
        ElementState state;
        bytes32 requestId;
        uint256 requestedAt;
        uint256 fulfilledAt;
        string lastRawResult;
    }

    struct Instance {
        bool exists;
        uint256 instanceId;
        address identityContractAddress;
        address dmnLiteAddress;
        string dmnEvalUrl;
        bool enforceBusinessRuleCaller;
        StateMemory stateMemory;
        mapping(MessageKey => Message) messages;
        mapping(GatewayKey => Gateway) gateways;
        mapping(EventKey => ActionEvent) events;
        mapping(ParticipantKey => Participant) participants;
        mapping(BusinessRuleKey => BusinessRule) businessRules;
    }

    struct InitParameters {
        address identityContractAddress;
        address dmnLiteAddress;
        string dmnEvalUrl;
        bool enforceBusinessRuleCaller;
        address Participant_127fmp5_account;
        string Participant_127fmp5_org;
        address Participant_1i0wkot_account;
        string Participant_1i0wkot_org;
    }

    address public owner;
    bool public isInited;
    uint256 public currentInstanceId;
    IOracle public oracle;

    mapping(uint256 => Instance) private instances;

    uint8 private constant DMN_REQUEST_FULFILLED = 2;

    event MessageSent(uint256 instanceId, MessageKey messageKey, string fireflyTranId);
    event GatewayDone(uint256 instanceId, GatewayKey gatewayKey);
    event ActionEventDone(uint256 instanceId, EventKey eventKey);
    event BusinessRuleRequested(
        uint256 indexed instanceId,
        BusinessRuleKey indexed ruleKey,
        bytes32 indexed requestId
    );
    event BusinessRuleCompleted(
        uint256 indexed instanceId,
        BusinessRuleKey indexed ruleKey,
        bytes32 indexed requestId
    );

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

    function initLedger() external onlyOwner {
        require(!isInited, "already initialized");
        isInited = true;
        currentInstanceId = 0;
    }

    function _getInstance(uint256 instanceId) internal view returns (Instance storage inst) {
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

    function _checkBusinessRuleCaller(
        Instance storage inst,
        BusinessRule storage br
    ) internal view {
        if (!(inst.enforceBusinessRuleCaller || br.callerRestricted)) {
            return;
        }
        require(br.allowedCaller != address(0), "business rule caller not configured");
        require(msg.sender == br.allowedCaller, "business rule caller not allowed");
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
        ElementState state
    ) internal {
        inst.messages[key] = Message({
            exists: true,
            sendParticipant: sendKey,
            receiveParticipant: recvKey,
            fireflyTranId: "",
            state: state
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
        BusinessRuleInit calldata config
    ) internal {
        inst.businessRules[key] = BusinessRule({
            exists: true,
            dmnCid: config.dmnCid,
            hashOfDmn: config.dmnHash,
            decisionId: config.decisionId,
            callerRestricted: config.callerRestricted,
            allowedCaller: config.allowedCaller,
            state: ElementState.DISABLED,
            requestId: bytes32(0),
            requestedAt: 0,
            fulfilledAt: 0,
            lastRawResult: ""
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

    function _jsonString(string memory value) internal pure returns (string memory) {
        return string.concat("\"", value, "\"");
    }

    function _jsonBool(bool value) internal pure returns (string memory) {
        return value ? "true" : "false";
    }

    function _jsonInt(int256 value) internal pure returns (string memory) {
        if (value == 0) {
            return "0";
        }

        bool negative = value < 0;
        uint256 temp = uint256(negative ? -value : value);
        uint256 digits;
        uint256 cursor = temp;
        while (cursor != 0) {
            digits++;
            cursor /= 10;
        }

        uint256 totalLength = digits + (negative ? 1 : 0);
        bytes memory buffer = new bytes(totalLength);
        uint256 index = totalLength;
        while (temp != 0) {
            index--;
            buffer[index] = bytes1(uint8(48 + (temp % 10)));
            temp /= 10;
        }
        if (negative) {
            buffer[0] = bytes1("-");
        }
        return string(buffer);
    }

    function _jsonField(
        string memory key,
        string memory encodedValue
    ) internal pure returns (string memory) {
        return string.concat(_jsonString(key), ":", encodedValue);
    }

    function _jsonAppendField(
        string memory body,
        string memory field
    ) internal pure returns (string memory) {
        if (bytes(body).length == 0) {
            return field;
        }
        return string.concat(body, ",", field);
    }

    function _jsonObject(string memory body) internal pure returns (string memory) {
        return string.concat("{", body, "}");
    }

    function _skipWhitespace(bytes memory data, uint256 index) internal pure returns (uint256) {
        while (index < data.length) {
            bytes1 ch = data[index];
            if (ch != 0x20 && ch != 0x09 && ch != 0x0A && ch != 0x0D) {
                break;
            }
            unchecked {
                index++;
            }
        }
        return index;
    }

    function _sliceBytes(
        bytes memory data,
        uint256 start,
        uint256 end
    ) internal pure returns (string memory) {
        require(end >= start, "invalid slice");
        bytes memory out = new bytes(end - start);
        for (uint256 i = start; i < end; i++) {
            out[i - start] = data[i];
        }
        return string(out);
    }

    function _findJsonValue(
        string memory raw,
        string memory key
    ) internal pure returns (uint256 start, uint256 end, uint8 kind, bool found) {
        bytes memory data = bytes(raw);
        bytes memory keyBytes = bytes(key);
        if (data.length == 0 || keyBytes.length == 0) {
            return (0, 0, 0, false);
        }

        for (uint256 i = 0; i + keyBytes.length + 2 <= data.length; i++) {
            if (data[i] != bytes1("\"")) {
                continue;
            }

            bool matches = true;
            for (uint256 j = 0; j < keyBytes.length; j++) {
                if (data[i + 1 + j] != keyBytes[j]) {
                    matches = false;
                    break;
                }
            }
            if (!matches || data[i + 1 + keyBytes.length] != bytes1("\"")) {
                continue;
            }

            uint256 cursor = _skipWhitespace(data, i + keyBytes.length + 2);
            if (cursor >= data.length || data[cursor] != bytes1(":")) {
                continue;
            }
            cursor = _skipWhitespace(data, cursor + 1);
            if (cursor >= data.length) {
                return (0, 0, 0, false);
            }

            bytes1 ch = data[cursor];
            if (ch == bytes1("\"")) {
                uint256 valueStart = cursor + 1;
                uint256 valueEnd = valueStart;
                while (valueEnd < data.length) {
                    if (data[valueEnd] == bytes1("\"") && (valueEnd == valueStart || data[valueEnd - 1] != bytes1("\\"))) {
                        return (valueStart, valueEnd, 1, true);
                    }
                    unchecked {
                        valueEnd++;
                    }
                }
                revert("unterminated json string");
            }

            if (ch == bytes1("t") || ch == bytes1("f")) {
                uint256 valueEnd = cursor;
                while (valueEnd < data.length) {
                    bytes1 c = data[valueEnd];
                    if ((c < bytes1("a") || c > bytes1("z")) && (c < bytes1("A") || c > bytes1("Z"))) {
                        break;
                    }
                    unchecked {
                        valueEnd++;
                    }
                }
                return (cursor, valueEnd, 2, true);
            }

            if (
                ch == bytes1("-") ||
                (ch >= bytes1("0") && ch <= bytes1("9"))
            ) {
                uint256 valueEnd = cursor;
                while (valueEnd < data.length) {
                    bytes1 c = data[valueEnd];
                    if (
                        c != bytes1("-") &&
                        c != bytes1(".") &&
                        (c < bytes1("0") || c > bytes1("9"))
                    ) {
                        break;
                    }
                    unchecked {
                        valueEnd++;
                    }
                }
                return (cursor, valueEnd, 3, true);
            }
        }

        return (0, 0, 0, false);
    }

    function _extractJsonString(
        string memory raw,
        string memory key
    ) internal pure returns (string memory) {
        (uint256 start, uint256 end, uint8 kind, bool found) = _findJsonValue(raw, key);
        require(found && kind == 1, "json string not found");
        return _sliceBytes(bytes(raw), start, end);
    }

    function _extractJsonBool(
        string memory raw,
        string memory key
    ) internal pure returns (bool) {
        (uint256 start, uint256 end, uint8 kind, bool found) = _findJsonValue(raw, key);
        require(found && kind == 2, "json bool not found");
        bytes32 hashed = keccak256(bytes(_sliceBytes(bytes(raw), start, end)));
        if (hashed == keccak256(bytes("true"))) {
            return true;
        }
        if (hashed == keccak256(bytes("false"))) {
            return false;
        }
        revert("invalid json bool");
    }

    function _extractJsonInt(
        string memory raw,
        string memory key
    ) internal pure returns (int256) {
        (uint256 start, uint256 end, uint8 kind, bool found) = _findJsonValue(raw, key);
        require(found && kind == 3, "json number not found");
        return _stringToInt(_sliceBytes(bytes(raw), start, end));
    }

    function createInstance(
        InitParameters calldata params
    ) external onlyOwner onlyInitialized returns (uint256 instanceId) {
        instanceId = currentInstanceId;
        Instance storage inst = instances[instanceId];
        require(!inst.exists, "instance already exists");

        inst.exists = true;
        inst.instanceId = instanceId;
        inst.identityContractAddress = params.identityContractAddress;
        inst.dmnLiteAddress = params.dmnLiteAddress;
        inst.dmnEvalUrl = params.dmnEvalUrl;
        inst.enforceBusinessRuleCaller = params.enforceBusinessRuleCaller;


        _createParticipant(
            inst,
            ParticipantKey.Participant_127fmp5,
            params.Participant_127fmp5_account,
            params.Participant_127fmp5_org,
            false,
            0,
            0
        );
        _createParticipant(
            inst,
            ParticipantKey.Participant_1i0wkot,
            params.Participant_1i0wkot_account,
            params.Participant_1i0wkot_org,
            false,
            0,
            0
        );

        _createActionEvent(
            inst,
            EventKey.Event_1ex6tww,
            ElementState.ENABLED
        );
        _createActionEvent(
            inst,
            EventKey.Event_1w9hecu,
            ElementState.DISABLED
        );
        _createActionEvent(
            inst,
            EventKey.Event_0azwphb,
            ElementState.DISABLED
        );
        _createActionEvent(
            inst,
            EventKey.Event_13dkewm,
            ElementState.DISABLED
        );
        _createActionEvent(
            inst,
            EventKey.Event_0if27w4,
            ElementState.DISABLED
        );
        _createActionEvent(
            inst,
            EventKey.Event_1tsrojw,
            ElementState.DISABLED
        );
        _createActionEvent(
            inst,
            EventKey.Event_0ox11yo,
            ElementState.DISABLED
        );
        _createActionEvent(
            inst,
            EventKey.Event_00uq91w,
            ElementState.DISABLED
        );
        _createActionEvent(
            inst,
            EventKey.Event_1eluy7v,
            ElementState.DISABLED
        );
        _createActionEvent(
            inst,
            EventKey.Event_0a9rmyh,
            ElementState.DISABLED
        );

        _createMessage(
            inst,
            MessageKey.Message_1kt861j,
            ParticipantKey.Participant_127fmp5,
            ParticipantKey.Participant_1i0wkot,
            ElementState.DISABLED
        );

        _createGateway(
            inst,
            GatewayKey.Gateway_1309cek,
            ElementState.DISABLED
        );


        currentInstanceId += 1;
    }

    function getExecutionSnapshot(uint256 instanceId)
        external
        view
        returns (
            uint8[] memory messageStates,
            string[] memory messageFireflyTranIds,
            uint8[] memory gatewayStates,
            uint8[] memory eventStates,
            uint8[] memory businessRuleStates,
            bytes32[] memory businessRuleRequestIds
        )
    {
        Instance storage inst = _getInstance(instanceId);

        messageStates = new uint8[](1);
        messageFireflyTranIds = new string[](1);
        {
            Message storage m = inst.messages[MessageKey.Message_1kt861j];
            messageStates[0] = uint8(m.state);
            messageFireflyTranIds[0] = m.fireflyTranId;
        }

        gatewayStates = new uint8[](1);
        {
            Gateway storage g = inst.gateways[GatewayKey.Gateway_1309cek];
            gatewayStates[0] = uint8(g.state);
        }

        eventStates = new uint8[](10);
        {
            ActionEvent storage ev = inst.events[EventKey.Event_1ex6tww];
            eventStates[0] = uint8(ev.state);
        }
        {
            ActionEvent storage ev = inst.events[EventKey.Event_1w9hecu];
            eventStates[1] = uint8(ev.state);
        }
        {
            ActionEvent storage ev = inst.events[EventKey.Event_0azwphb];
            eventStates[2] = uint8(ev.state);
        }
        {
            ActionEvent storage ev = inst.events[EventKey.Event_13dkewm];
            eventStates[3] = uint8(ev.state);
        }
        {
            ActionEvent storage ev = inst.events[EventKey.Event_0if27w4];
            eventStates[4] = uint8(ev.state);
        }
        {
            ActionEvent storage ev = inst.events[EventKey.Event_1tsrojw];
            eventStates[5] = uint8(ev.state);
        }
        {
            ActionEvent storage ev = inst.events[EventKey.Event_0ox11yo];
            eventStates[6] = uint8(ev.state);
        }
        {
            ActionEvent storage ev = inst.events[EventKey.Event_00uq91w];
            eventStates[7] = uint8(ev.state);
        }
        {
            ActionEvent storage ev = inst.events[EventKey.Event_1eluy7v];
            eventStates[8] = uint8(ev.state);
        }
        {
            ActionEvent storage ev = inst.events[EventKey.Event_0a9rmyh];
            eventStates[9] = uint8(ev.state);
        }

        businessRuleStates = new uint8[](0);
        businessRuleRequestIds = new bytes32[](0);
    }


function Event_1ex6tww(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.Event_1ex6tww];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.Event_1ex6tww);
        inst.messages[MessageKey.Message_1kt861j].state = ElementState.ENABLED;

    }

function Message_1kt861j_Send(uint256 instanceId, string calldata fireflyTranId, int256 condition) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1kt861j];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        inst.stateMemory.Condition = condition;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1kt861j, fireflyTranId);
        inst.gateways[GatewayKey.Gateway_1309cek].state = ElementState.ENABLED;

    }

function Gateway_1309cek(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Gateway storage g = inst.gateways[GatewayKey.Gateway_1309cek];
        require(g.exists, "gateway not set");
        require(g.state == ElementState.ENABLED, "gateway state not allowed");

        g.state = ElementState.COMPLETED;
        emit GatewayDone(instanceId, GatewayKey.Gateway_1309cek);
        if (inst.stateMemory.Condition == 1) {
            inst.events[EventKey.Event_1w9hecu].state = ElementState.ENABLED;
        }
        else if (inst.stateMemory.Condition == 2) {
            inst.events[EventKey.Event_0azwphb].state = ElementState.ENABLED;
        }
        else if (inst.stateMemory.Condition == 3) {
            inst.events[EventKey.Event_13dkewm].state = ElementState.ENABLED;
        }
        else if (inst.stateMemory.Condition == 4) {
            inst.events[EventKey.Event_0if27w4].state = ElementState.ENABLED;
        }
        else if (inst.stateMemory.Condition == 5) {
            inst.events[EventKey.Event_1tsrojw].state = ElementState.ENABLED;
        }
        else if (inst.stateMemory.Condition == 7) {
            inst.events[EventKey.Event_0ox11yo].state = ElementState.ENABLED;
        }
        else if (inst.stateMemory.Condition == 8) {
            inst.events[EventKey.Event_00uq91w].state = ElementState.ENABLED;
        }
        else if (inst.stateMemory.Condition == 9) {
            inst.events[EventKey.Event_1eluy7v].state = ElementState.ENABLED;
        }
        else if (inst.stateMemory.Condition == 10) {
            inst.events[EventKey.Event_0a9rmyh].state = ElementState.ENABLED;
        }

    }

function Event_1w9hecu(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.Event_1w9hecu];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.Event_1w9hecu);

    }

function Event_0azwphb(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.Event_0azwphb];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.Event_0azwphb);

    }

function Event_13dkewm(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.Event_13dkewm];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.Event_13dkewm);

    }

function Event_0if27w4(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.Event_0if27w4];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.Event_0if27w4);

    }

function Event_1tsrojw(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.Event_1tsrojw];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.Event_1tsrojw);

    }

function Event_0ox11yo(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.Event_0ox11yo];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.Event_0ox11yo);

    }

function Event_00uq91w(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.Event_00uq91w];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.Event_00uq91w);

    }

function Event_1eluy7v(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.Event_1eluy7v];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.Event_1eluy7v);

    }

function Event_0a9rmyh(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.Event_0a9rmyh];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.Event_0a9rmyh);

    }
}
