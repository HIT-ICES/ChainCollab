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

contract GeneratedContract {
    enum ElementState {
        DISABLED,
        ENABLED,
        WAITING_FOR_CONFIRMATION,
        COMPLETED
    }

    enum ParticipantKey {
        Participant_1xq1vsc,
        Participant_05g5xih
    }

    enum MessageKey {
        Message_00wpjke,
        Message_03was4c,
        Message_05uqcn2,
        Message_0z8kf0j,
        Message_0zt8q9t,
        Message_13l7271,
        Message_1i5n14f,
        Message_1kazup6,
        Message_1y5d31x,
        Message_1yln43l
    }

    enum GatewayKey {
        Gateway_19zzj3s,
        Gateway_085e7pr
    }

    enum EventKey {
        Event_0okhbce,        Event_0th6os0,        Event_0awuo5v,        Event_0zsq5na    }

    enum BusinessRuleKey {
        Activity_1uktp5z
    }

    struct StateMemory {
        bool CancelFee;
        string ConcelAck;
        string Fee;
        string InvoiceContent;
        int256 OrderAmount;
        string OrderContent;
        string QuoteContent;
        string QuoteRequest;
        string Cancelation;
        string Confirm_message;
        string PayMethod;
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
        address Participant_1xq1vsc_account;
        string Participant_1xq1vsc_org;
        address Participant_05g5xih_account;
        string Participant_05g5xih_org;
        BusinessRuleInit Activity_1uktp5z;
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

        require(inst.dmnLiteAddress != address(0), "dmn lite not set");
        require(bytes(inst.dmnEvalUrl).length != 0, "dmn eval url not set");

        _createParticipant(
            inst,
            ParticipantKey.Participant_1xq1vsc,
            params.Participant_1xq1vsc_account,
            params.Participant_1xq1vsc_org,
            false,
            0,
            0
        );
        _createParticipant(
            inst,
            ParticipantKey.Participant_05g5xih,
            params.Participant_05g5xih_account,
            params.Participant_05g5xih_org,
            false,
            0,
            0
        );

        _createActionEvent(
            inst,
            EventKey.Event_0okhbce,
            ElementState.ENABLED
        );
        _createActionEvent(
            inst,
            EventKey.Event_0th6os0,
            ElementState.DISABLED
        );
        _createActionEvent(
            inst,
            EventKey.Event_0awuo5v,
            ElementState.DISABLED
        );
        _createActionEvent(
            inst,
            EventKey.Event_0zsq5na,
            ElementState.DISABLED
        );

        _createMessage(
            inst,
            MessageKey.Message_00wpjke,
            ParticipantKey.Participant_1xq1vsc,
            ParticipantKey.Participant_05g5xih,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_03was4c,
            ParticipantKey.Participant_1xq1vsc,
            ParticipantKey.Participant_05g5xih,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_05uqcn2,
            ParticipantKey.Participant_1xq1vsc,
            ParticipantKey.Participant_05g5xih,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_0z8kf0j,
            ParticipantKey.Participant_1xq1vsc,
            ParticipantKey.Participant_05g5xih,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_0zt8q9t,
            ParticipantKey.Participant_05g5xih,
            ParticipantKey.Participant_1xq1vsc,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_13l7271,
            ParticipantKey.Participant_1xq1vsc,
            ParticipantKey.Participant_05g5xih,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_1i5n14f,
            ParticipantKey.Participant_05g5xih,
            ParticipantKey.Participant_1xq1vsc,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_1kazup6,
            ParticipantKey.Participant_05g5xih,
            ParticipantKey.Participant_1xq1vsc,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_1y5d31x,
            ParticipantKey.Participant_05g5xih,
            ParticipantKey.Participant_1xq1vsc,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_1yln43l,
            ParticipantKey.Participant_05g5xih,
            ParticipantKey.Participant_1xq1vsc,
            ElementState.DISABLED
        );

        _createGateway(
            inst,
            GatewayKey.Gateway_19zzj3s,
            ElementState.DISABLED
        );
        _createGateway(
            inst,
            GatewayKey.Gateway_085e7pr,
            ElementState.DISABLED
        );

        _createBusinessRule(
            inst,
            BusinessRuleKey.Activity_1uktp5z,
            params.Activity_1uktp5z
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

        messageStates = new uint8[](10);
        messageFireflyTranIds = new string[](10);
        {
            Message storage m = inst.messages[MessageKey.Message_00wpjke];
            messageStates[0] = uint8(m.state);
            messageFireflyTranIds[0] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_03was4c];
            messageStates[1] = uint8(m.state);
            messageFireflyTranIds[1] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_05uqcn2];
            messageStates[2] = uint8(m.state);
            messageFireflyTranIds[2] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_0z8kf0j];
            messageStates[3] = uint8(m.state);
            messageFireflyTranIds[3] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_0zt8q9t];
            messageStates[4] = uint8(m.state);
            messageFireflyTranIds[4] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_13l7271];
            messageStates[5] = uint8(m.state);
            messageFireflyTranIds[5] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_1i5n14f];
            messageStates[6] = uint8(m.state);
            messageFireflyTranIds[6] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_1kazup6];
            messageStates[7] = uint8(m.state);
            messageFireflyTranIds[7] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_1y5d31x];
            messageStates[8] = uint8(m.state);
            messageFireflyTranIds[8] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_1yln43l];
            messageStates[9] = uint8(m.state);
            messageFireflyTranIds[9] = m.fireflyTranId;
        }

        gatewayStates = new uint8[](2);
        {
            Gateway storage g = inst.gateways[GatewayKey.Gateway_19zzj3s];
            gatewayStates[0] = uint8(g.state);
        }
        {
            Gateway storage g = inst.gateways[GatewayKey.Gateway_085e7pr];
            gatewayStates[1] = uint8(g.state);
        }

        eventStates = new uint8[](4);
        {
            ActionEvent storage ev = inst.events[EventKey.Event_0okhbce];
            eventStates[0] = uint8(ev.state);
        }
        {
            ActionEvent storage ev = inst.events[EventKey.Event_0th6os0];
            eventStates[1] = uint8(ev.state);
        }
        {
            ActionEvent storage ev = inst.events[EventKey.Event_0awuo5v];
            eventStates[2] = uint8(ev.state);
        }
        {
            ActionEvent storage ev = inst.events[EventKey.Event_0zsq5na];
            eventStates[3] = uint8(ev.state);
        }

        businessRuleStates = new uint8[](1);
        businessRuleRequestIds = new bytes32[](1);
        {
            BusinessRule storage br = inst.businessRules[BusinessRuleKey.Activity_1uktp5z];
            businessRuleStates[0] = uint8(br.state);
            businessRuleRequestIds[0] = br.requestId;
        }
    }

    function Activity_1uktp5z(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        BusinessRule storage br = inst.businessRules[BusinessRuleKey.Activity_1uktp5z];
        require(br.exists, "business rule not set");
        require(br.state == ElementState.ENABLED, "business rule not enabled");
        _checkBusinessRuleCaller(inst, br);

        string memory inputBody = "";
        inputBody = _jsonAppendField(
            inputBody,
            _jsonField(
                "OrderAmount",
            _jsonInt(inst.stateMemory.OrderAmount)
            )
        );
        string memory inputData = _jsonObject(inputBody);
        IDmnLite dmnLite = IDmnLite(inst.dmnLiteAddress);
        require(bytes(br.dmnCid).length != 0, "dmn cid not set");
        bytes32 requestId = dmnLite.requestDMNDecision(
            inst.dmnEvalUrl,
            br.dmnCid,
            br.decisionId,
            inputData
        );
        require(requestId != bytes32(0), "dmn request failed");
        br.requestId = requestId;
        br.requestedAt = block.timestamp;
        br.fulfilledAt = 0;
        br.lastRawResult = "";
        br.state = ElementState.WAITING_FOR_CONFIRMATION;
        emit BusinessRuleRequested(instanceId, BusinessRuleKey.Activity_1uktp5z, requestId);
    }

    function Activity_1uktp5z_Continue(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        BusinessRule storage br = inst.businessRules[BusinessRuleKey.Activity_1uktp5z];
        require(br.exists, "business rule not set");
        require(br.state == ElementState.WAITING_FOR_CONFIRMATION, "business rule not waiting");
        require(br.requestId != bytes32(0), "business rule not requested");
        _checkBusinessRuleCaller(inst, br);

        IDmnLite dmnLite = IDmnLite(inst.dmnLiteAddress);
        (
            uint8 requestState,
            address requester,
            ,
            uint256 fulfilledAt,
            bool exists
        ) = dmnLite.getRequestStatus(br.requestId);
        require(exists, "dmn request missing");
        require(requester == address(this), "unexpected dmn requester");
        require(requestState == DMN_REQUEST_FULFILLED, "dmn result not ready");

        string memory raw = dmnLite.getRawByRequestId(br.requestId);
        br.lastRawResult = raw;
        br.fulfilledAt = fulfilledAt;
        inst.stateMemory.CancelFee = _extractJsonBool(raw, "CancelFee");
        br.state = ElementState.COMPLETED;
        inst.gateways[GatewayKey.Gateway_19zzj3s].state = ElementState.ENABLED;


        emit BusinessRuleCompleted(instanceId, BusinessRuleKey.Activity_1uktp5z, br.requestId);
    }


function Event_0okhbce(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.Event_0okhbce];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.Event_0okhbce);
        inst.messages[MessageKey.Message_00wpjke].state = ElementState.ENABLED;

    }

function Message_00wpjke_Send(uint256 instanceId, string calldata fireflyTranId, string calldata QuoteRequest) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_00wpjke];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        inst.stateMemory.QuoteRequest = QuoteRequest;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_00wpjke, fireflyTranId);
        inst.messages[MessageKey.Message_1kazup6].state = ElementState.ENABLED;

    }

function Message_03was4c_Send(uint256 instanceId, string calldata fireflyTranId, string calldata confirm_message) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_03was4c];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        inst.stateMemory.Confirm_message = confirm_message;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_03was4c, fireflyTranId);
        inst.messages[MessageKey.Message_0z8kf0j].state = ElementState.DISABLED;
        inst.messages[MessageKey.Message_1yln43l].state = ElementState.ENABLED;

    }

function Message_05uqcn2_Send(uint256 instanceId, string calldata fireflyTranId, string calldata payMethod) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_05uqcn2];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        inst.stateMemory.PayMethod = payMethod;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_05uqcn2, fireflyTranId);
        inst.events[EventKey.Event_0zsq5na].state = ElementState.ENABLED;

    }

function Message_0z8kf0j_Send(uint256 instanceId, string calldata fireflyTranId, string calldata cancelation) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0z8kf0j];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        inst.stateMemory.Cancelation = cancelation;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0z8kf0j, fireflyTranId);
        inst.messages[MessageKey.Message_03was4c].state = ElementState.DISABLED;
        inst.messages[MessageKey.Message_0zt8q9t].state = ElementState.ENABLED;

    }

function Message_0zt8q9t_Send(uint256 instanceId, string calldata fireflyTranId, string calldata ConcelAck) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0zt8q9t];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        inst.stateMemory.ConcelAck = ConcelAck;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0zt8q9t, fireflyTranId);
        inst.businessRules[BusinessRuleKey.Activity_1uktp5z].state = ElementState.ENABLED;

    }

function Message_13l7271_Send(uint256 instanceId, string calldata fireflyTranId, string calldata payRecord) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_13l7271];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        inst.stateMemory.PayRecord = payRecord;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_13l7271, fireflyTranId);
        inst.events[EventKey.Event_0th6os0].state = ElementState.ENABLED;

    }

function Message_1i5n14f_Send(uint256 instanceId, string calldata fireflyTranId, string calldata Fee) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1i5n14f];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        inst.stateMemory.Fee = Fee;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1i5n14f, fireflyTranId);
        inst.messages[MessageKey.Message_05uqcn2].state = ElementState.ENABLED;

    }

function Message_1kazup6_Send(uint256 instanceId, string calldata fireflyTranId, string calldata QuoteContent) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1kazup6];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        inst.stateMemory.QuoteContent = QuoteContent;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1kazup6, fireflyTranId);
        inst.messages[MessageKey.Message_1y5d31x].state = ElementState.ENABLED;

    }

function Message_1y5d31x_Send(uint256 instanceId, string calldata fireflyTranId, string calldata OrderContent, int256 OrderAmount) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1y5d31x];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        inst.stateMemory.OrderContent = OrderContent;
        inst.stateMemory.OrderAmount = OrderAmount;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1y5d31x, fireflyTranId);
        inst.gateways[GatewayKey.Gateway_085e7pr].state = ElementState.ENABLED;

    }

function Message_1yln43l_Send(uint256 instanceId, string calldata fireflyTranId, string calldata InvoiceContent) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1yln43l];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        inst.stateMemory.InvoiceContent = InvoiceContent;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1yln43l, fireflyTranId);
        inst.messages[MessageKey.Message_13l7271].state = ElementState.ENABLED;

    }

function Gateway_19zzj3s(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Gateway storage g = inst.gateways[GatewayKey.Gateway_19zzj3s];
        require(g.exists, "gateway not set");
        require(g.state == ElementState.ENABLED, "gateway state not allowed");

        g.state = ElementState.COMPLETED;
        emit GatewayDone(instanceId, GatewayKey.Gateway_19zzj3s);
        if (inst.stateMemory.CancelFee == false) {
            inst.events[EventKey.Event_0awuo5v].state = ElementState.ENABLED;
        }
        else if (inst.stateMemory.CancelFee == true) {
            inst.messages[MessageKey.Message_1i5n14f].state = ElementState.ENABLED;
        }

    }

function Gateway_085e7pr(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Gateway storage g = inst.gateways[GatewayKey.Gateway_085e7pr];
        require(g.exists, "gateway not set");
        require(g.state == ElementState.ENABLED, "gateway state not allowed");

        g.state = ElementState.COMPLETED;
        emit GatewayDone(instanceId, GatewayKey.Gateway_085e7pr);
        inst.messages[MessageKey.Message_0z8kf0j].state = ElementState.ENABLED;
        inst.messages[MessageKey.Message_03was4c].state = ElementState.ENABLED;

    }

function Event_0th6os0(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.Event_0th6os0];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.Event_0th6os0);

    }

function Event_0awuo5v(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.Event_0awuo5v];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.Event_0awuo5v);

    }

function Event_0zsq5na(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.Event_0zsq5na];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.Event_0zsq5na);

    }
}
