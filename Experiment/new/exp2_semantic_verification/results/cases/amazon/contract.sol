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
        Event_0ojehz6,        Event_0ci2gl8,        Event_0dyp0ut    }

    enum BusinessRuleKey {
        Activity_0tya4bp
    }

    struct StateMemory {
        string EC2_resource_ID;
        int256 Amount;
        bool Confirm;
        string Description;
        int256 Duration;
        string Instance_ID;
        string Logs;
        string Other_information;
        string Question_name;
        string Reason;
        string Result;
        string ServiceType;
        string Time;
        string Type;
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
        address Participant_1p9owwo_account;
        string Participant_1p9owwo_org;
        address Participant_12df78t_account;
        string Participant_12df78t_org;
        BusinessRuleInit Activity_0tya4bp;
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
            ParticipantKey.Participant_1p9owwo,
            params.Participant_1p9owwo_account,
            params.Participant_1p9owwo_org,
            false,
            0,
            0
        );
        _createParticipant(
            inst,
            ParticipantKey.Participant_12df78t,
            params.Participant_12df78t_account,
            params.Participant_12df78t_org,
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
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_068kmzv,
            ParticipantKey.Participant_12df78t,
            ParticipantKey.Participant_1p9owwo,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_076ulzs,
            ParticipantKey.Participant_12df78t,
            ParticipantKey.Participant_1p9owwo,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_09krt7c,
            ParticipantKey.Participant_12df78t,
            ParticipantKey.Participant_1p9owwo,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_0ywghlt,
            ParticipantKey.Participant_12df78t,
            ParticipantKey.Participant_1p9owwo,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_12n6jjk,
            ParticipantKey.Participant_12df78t,
            ParticipantKey.Participant_1p9owwo,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_1b1qlzd,
            ParticipantKey.Participant_1p9owwo,
            ParticipantKey.Participant_12df78t,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_1bhhp1n,
            ParticipantKey.Participant_12df78t,
            ParticipantKey.Participant_1p9owwo,
            ElementState.DISABLED
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
            BusinessRuleKey.Activity_0tya4bp,
            params.Activity_0tya4bp
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

        messageStates = new uint8[](8);
        messageFireflyTranIds = new string[](8);
        {
            Message storage m = inst.messages[MessageKey.Message_01jq2zl];
            messageStates[0] = uint8(m.state);
            messageFireflyTranIds[0] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_068kmzv];
            messageStates[1] = uint8(m.state);
            messageFireflyTranIds[1] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_076ulzs];
            messageStates[2] = uint8(m.state);
            messageFireflyTranIds[2] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_09krt7c];
            messageStates[3] = uint8(m.state);
            messageFireflyTranIds[3] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_0ywghlt];
            messageStates[4] = uint8(m.state);
            messageFireflyTranIds[4] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_12n6jjk];
            messageStates[5] = uint8(m.state);
            messageFireflyTranIds[5] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_1b1qlzd];
            messageStates[6] = uint8(m.state);
            messageFireflyTranIds[6] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_1bhhp1n];
            messageStates[7] = uint8(m.state);
            messageFireflyTranIds[7] = m.fireflyTranId;
        }

        gatewayStates = new uint8[](3);
        {
            Gateway storage g = inst.gateways[GatewayKey.Gateway_0auc3he];
            gatewayStates[0] = uint8(g.state);
        }
        {
            Gateway storage g = inst.gateways[GatewayKey.Gateway_0ivv4vg];
            gatewayStates[1] = uint8(g.state);
        }
        {
            Gateway storage g = inst.gateways[GatewayKey.Gateway_0jgq0a6];
            gatewayStates[2] = uint8(g.state);
        }

        eventStates = new uint8[](3);
        {
            ActionEvent storage ev = inst.events[EventKey.Event_0ojehz6];
            eventStates[0] = uint8(ev.state);
        }
        {
            ActionEvent storage ev = inst.events[EventKey.Event_0ci2gl8];
            eventStates[1] = uint8(ev.state);
        }
        {
            ActionEvent storage ev = inst.events[EventKey.Event_0dyp0ut];
            eventStates[2] = uint8(ev.state);
        }

        businessRuleStates = new uint8[](1);
        businessRuleRequestIds = new bytes32[](1);
        {
            BusinessRule storage br = inst.businessRules[BusinessRuleKey.Activity_0tya4bp];
            businessRuleStates[0] = uint8(br.state);
            businessRuleRequestIds[0] = br.requestId;
        }
    }

    function Activity_0tya4bp(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        BusinessRule storage br = inst.businessRules[BusinessRuleKey.Activity_0tya4bp];
        require(br.exists, "business rule not set");
        require(br.state == ElementState.ENABLED, "business rule not enabled");
        _checkBusinessRuleCaller(inst, br);

        string memory inputBody = "";
        inputBody = _jsonAppendField(
            inputBody,
            _jsonField(
                "type",
            _jsonString(inst.stateMemory.Type)
            )
        );
        inputBody = _jsonAppendField(
            inputBody,
            _jsonField(
                "duration",
            _jsonInt(inst.stateMemory.Duration)
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
        emit BusinessRuleRequested(instanceId, BusinessRuleKey.Activity_0tya4bp, requestId);
    }

    function Activity_0tya4bp_Continue(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        BusinessRule storage br = inst.businessRules[BusinessRuleKey.Activity_0tya4bp];
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
        inst.stateMemory.Confirm = _extractJsonBool(raw, "confirm");
        br.state = ElementState.COMPLETED;
        inst.gateways[GatewayKey.Gateway_0ivv4vg].state = ElementState.ENABLED;


        emit BusinessRuleCompleted(instanceId, BusinessRuleKey.Activity_0tya4bp, br.requestId);
    }


function Event_0ojehz6(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.Event_0ojehz6];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.Event_0ojehz6);
        inst.messages[MessageKey.Message_09krt7c].state = ElementState.ENABLED;

    }

function Message_01jq2zl_Send(uint256 instanceId, string calldata fireflyTranId, int256 amount) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_01jq2zl];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        inst.stateMemory.Amount = amount;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_01jq2zl, fireflyTranId);
        inst.events[EventKey.Event_0ci2gl8].state = ElementState.ENABLED;

    }

function Message_068kmzv_Send(uint256 instanceId, string calldata fireflyTranId, string calldata time, string calldata instance_ID, string calldata logs) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_068kmzv];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        inst.stateMemory.Time = time;
        inst.stateMemory.Instance_ID = instance_ID;
        inst.stateMemory.Logs = logs;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_068kmzv, fireflyTranId);
        inst.gateways[GatewayKey.Gateway_0auc3he].state = ElementState.ENABLED;

    }

function Message_076ulzs_Send(uint256 instanceId, string calldata fireflyTranId, string calldata time, string calldata description, string calldata EC2_resource_ID, string calldata logs, string calldata other_information) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_076ulzs];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        inst.stateMemory.Time = time;
        inst.stateMemory.Description = description;
        inst.stateMemory.EC2_resource_ID = EC2_resource_ID;
        inst.stateMemory.Logs = logs;
        inst.stateMemory.Other_information = other_information;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_076ulzs, fireflyTranId);
        inst.gateways[GatewayKey.Gateway_0auc3he].state = ElementState.ENABLED;

    }

function Message_09krt7c_Send(uint256 instanceId, string calldata fireflyTranId, string calldata question_name, string calldata description) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_09krt7c];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        inst.stateMemory.Question_name = question_name;
        inst.stateMemory.Description = description;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_09krt7c, fireflyTranId);
        inst.gateways[GatewayKey.Gateway_0jgq0a6].state = ElementState.ENABLED;

    }

function Message_0ywghlt_Send(uint256 instanceId, string calldata fireflyTranId, string calldata serviceType) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0ywghlt];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        inst.stateMemory.ServiceType = serviceType;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0ywghlt, fireflyTranId);
        inst.messages[MessageKey.Message_1bhhp1n].state = ElementState.DISABLED;
        inst.messages[MessageKey.Message_068kmzv].state = ElementState.ENABLED;

    }

function Message_12n6jjk_Send(uint256 instanceId, string calldata fireflyTranId, string calldata type, int256 duration) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_12n6jjk];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        inst.stateMemory.Type = type;
        inst.stateMemory.Duration = duration;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_12n6jjk, fireflyTranId);
        inst.businessRules[BusinessRuleKey.Activity_0tya4bp].state = ElementState.ENABLED;

    }

function Message_1b1qlzd_Send(uint256 instanceId, string calldata fireflyTranId, string calldata reason, string calldata result) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1b1qlzd];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        inst.stateMemory.Reason = reason;
        inst.stateMemory.Result = result;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1b1qlzd, fireflyTranId);
        inst.events[EventKey.Event_0dyp0ut].state = ElementState.ENABLED;

    }

function Message_1bhhp1n_Send(uint256 instanceId, string calldata fireflyTranId, string calldata serviceType) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1bhhp1n];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        inst.stateMemory.ServiceType = serviceType;
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
        if (inst.stateMemory.Confirm == false) {
            inst.messages[MessageKey.Message_1b1qlzd].state = ElementState.ENABLED;
        }
        else if (inst.stateMemory.Confirm == true) {
            inst.messages[MessageKey.Message_01jq2zl].state = ElementState.ENABLED;
        }

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
