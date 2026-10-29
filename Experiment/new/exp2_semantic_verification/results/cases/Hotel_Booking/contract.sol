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
        Participant_1080bkg,
        Participant_0sktaei
    }

    enum MessageKey {
        Message_045i10y,
        Message_04ikf2n,
        Message_0m9p3da,
        Message_0o8eyir,
        Message_0r9lypd,
        Message_0vlxzcv,
        Message_104h2tt,
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
        Gateway_1jhfnrm,
        Gateway_1atxr3y,
        EventBasedGateway_1fxpmyn
    }

    enum EventKey {
        StartEvent_1jtgn3j,        EndEvent_0366pfz,        EndEvent_08edp7f,        EndEvent_146eii4    }

    enum BusinessRuleKey {
        Activity_0b1f7uv
    }

    struct StateMemory {
        string ID;
        int256 VIPLevel;
        string VIPcardId;
        int256 VIPpoints;
        int256 Bedrooms;
        string Booking_id;
        bool Cancel;
        bool Confirm;
        bool Confirmation;
        string Date;
        int256 Discount1;
        int256 Discount2;
        string Motivation;
        string Payableto;
        int256 Quotation;
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
        address Participant_1080bkg_account;
        string Participant_1080bkg_org;
        address Participant_0sktaei_account;
        string Participant_0sktaei_org;
        BusinessRuleInit Activity_0b1f7uv;
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
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_04ikf2n,
            ParticipantKey.Participant_0sktaei,
            ParticipantKey.Participant_1080bkg,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_0m9p3da,
            ParticipantKey.Participant_1080bkg,
            ParticipantKey.Participant_0sktaei,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_0o8eyir,
            ParticipantKey.Participant_1080bkg,
            ParticipantKey.Participant_0sktaei,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_0r9lypd,
            ParticipantKey.Participant_0sktaei,
            ParticipantKey.Participant_1080bkg,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_0vlxzcv,
            ParticipantKey.Participant_0sktaei,
            ParticipantKey.Participant_1080bkg,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_104h2tt,
            ParticipantKey.Participant_1080bkg,
            ParticipantKey.Participant_0sktaei,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_1em0ee4,
            ParticipantKey.Participant_0sktaei,
            ParticipantKey.Participant_1080bkg,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_1etcmvl,
            ParticipantKey.Participant_0sktaei,
            ParticipantKey.Participant_1080bkg,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_1joj7ca,
            ParticipantKey.Participant_1080bkg,
            ParticipantKey.Participant_0sktaei,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_1ljlm4g,
            ParticipantKey.Participant_0sktaei,
            ParticipantKey.Participant_1080bkg,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_1nlagx2,
            ParticipantKey.Participant_1080bkg,
            ParticipantKey.Participant_0sktaei,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_1xm9dxy,
            ParticipantKey.Participant_1080bkg,
            ParticipantKey.Participant_0sktaei,
            ElementState.DISABLED
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
            GatewayKey.Gateway_1jhfnrm,
            ElementState.DISABLED
        );
        _createGateway(
            inst,
            GatewayKey.Gateway_1atxr3y,
            ElementState.DISABLED
        );
        _createGateway(
            inst,
            GatewayKey.EventBasedGateway_1fxpmyn,
            ElementState.DISABLED
        );

        _createBusinessRule(
            inst,
            BusinessRuleKey.Activity_0b1f7uv,
            params.Activity_0b1f7uv
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

        messageStates = new uint8[](13);
        messageFireflyTranIds = new string[](13);
        {
            Message storage m = inst.messages[MessageKey.Message_045i10y];
            messageStates[0] = uint8(m.state);
            messageFireflyTranIds[0] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_04ikf2n];
            messageStates[1] = uint8(m.state);
            messageFireflyTranIds[1] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_0m9p3da];
            messageStates[2] = uint8(m.state);
            messageFireflyTranIds[2] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_0o8eyir];
            messageStates[3] = uint8(m.state);
            messageFireflyTranIds[3] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_0r9lypd];
            messageStates[4] = uint8(m.state);
            messageFireflyTranIds[4] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_0vlxzcv];
            messageStates[5] = uint8(m.state);
            messageFireflyTranIds[5] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_104h2tt];
            messageStates[6] = uint8(m.state);
            messageFireflyTranIds[6] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_1em0ee4];
            messageStates[7] = uint8(m.state);
            messageFireflyTranIds[7] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_1etcmvl];
            messageStates[8] = uint8(m.state);
            messageFireflyTranIds[8] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_1joj7ca];
            messageStates[9] = uint8(m.state);
            messageFireflyTranIds[9] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_1ljlm4g];
            messageStates[10] = uint8(m.state);
            messageFireflyTranIds[10] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_1nlagx2];
            messageStates[11] = uint8(m.state);
            messageFireflyTranIds[11] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_1xm9dxy];
            messageStates[12] = uint8(m.state);
            messageFireflyTranIds[12] = m.fireflyTranId;
        }

        gatewayStates = new uint8[](6);
        {
            Gateway storage g = inst.gateways[GatewayKey.ExclusiveGateway_106je4z];
            gatewayStates[0] = uint8(g.state);
        }
        {
            Gateway storage g = inst.gateways[GatewayKey.ExclusiveGateway_0hs3ztq];
            gatewayStates[1] = uint8(g.state);
        }
        {
            Gateway storage g = inst.gateways[GatewayKey.ExclusiveGateway_0nzwv7v];
            gatewayStates[2] = uint8(g.state);
        }
        {
            Gateway storage g = inst.gateways[GatewayKey.Gateway_1jhfnrm];
            gatewayStates[3] = uint8(g.state);
        }
        {
            Gateway storage g = inst.gateways[GatewayKey.Gateway_1atxr3y];
            gatewayStates[4] = uint8(g.state);
        }
        {
            Gateway storage g = inst.gateways[GatewayKey.EventBasedGateway_1fxpmyn];
            gatewayStates[5] = uint8(g.state);
        }

        eventStates = new uint8[](4);
        {
            ActionEvent storage ev = inst.events[EventKey.StartEvent_1jtgn3j];
            eventStates[0] = uint8(ev.state);
        }
        {
            ActionEvent storage ev = inst.events[EventKey.EndEvent_0366pfz];
            eventStates[1] = uint8(ev.state);
        }
        {
            ActionEvent storage ev = inst.events[EventKey.EndEvent_08edp7f];
            eventStates[2] = uint8(ev.state);
        }
        {
            ActionEvent storage ev = inst.events[EventKey.EndEvent_146eii4];
            eventStates[3] = uint8(ev.state);
        }

        businessRuleStates = new uint8[](1);
        businessRuleRequestIds = new bytes32[](1);
        {
            BusinessRule storage br = inst.businessRules[BusinessRuleKey.Activity_0b1f7uv];
            businessRuleStates[0] = uint8(br.state);
            businessRuleRequestIds[0] = br.requestId;
        }
    }

    function Activity_0b1f7uv(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        BusinessRule storage br = inst.businessRules[BusinessRuleKey.Activity_0b1f7uv];
        require(br.exists, "business rule not set");
        require(br.state == ElementState.ENABLED, "business rule not enabled");
        _checkBusinessRuleCaller(inst, br);

        string memory inputBody = "";
        inputBody = _jsonAppendField(
            inputBody,
            _jsonField(
                "VIPpoints",
            _jsonInt(inst.stateMemory.VIPpoints)
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
        emit BusinessRuleRequested(instanceId, BusinessRuleKey.Activity_0b1f7uv, requestId);
    }

    function Activity_0b1f7uv_Continue(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        BusinessRule storage br = inst.businessRules[BusinessRuleKey.Activity_0b1f7uv];
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
        inst.stateMemory.VIPLevel = _extractJsonInt(raw, "VIPLevel");
        br.state = ElementState.COMPLETED;
        inst.gateways[GatewayKey.Gateway_1jhfnrm].state = ElementState.ENABLED;


        emit BusinessRuleCompleted(instanceId, BusinessRuleKey.Activity_0b1f7uv, br.requestId);
    }


function StartEvent_1jtgn3j(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.StartEvent_1jtgn3j];
        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.StartEvent_1jtgn3j);
        inst.gateways[GatewayKey.ExclusiveGateway_0hs3ztq].state = ElementState.ENABLED;

    }

function Message_045i10y_Send(uint256 instanceId, string calldata fireflyTranId, string calldata date, int256 bedrooms) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_045i10y];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        inst.stateMemory.Date = date;
        inst.stateMemory.Bedrooms = bedrooms;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_045i10y, fireflyTranId);
        inst.messages[MessageKey.Message_0r9lypd].state = ElementState.ENABLED;

    }

function Message_04ikf2n_Send(uint256 instanceId, string calldata fireflyTranId, int256 discount2) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_04ikf2n];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        inst.stateMemory.Discount2 = discount2;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_04ikf2n, fireflyTranId);
        inst.gateways[GatewayKey.Gateway_1atxr3y].state = ElementState.ENABLED;

    }

function Message_0m9p3da_Send(uint256 instanceId, string calldata fireflyTranId, bool cancel) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0m9p3da];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        inst.stateMemory.Cancel = cancel;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0m9p3da, fireflyTranId);
        inst.gateways[GatewayKey.ExclusiveGateway_0nzwv7v].state = ElementState.ENABLED;

    }

function Message_0o8eyir_Send(uint256 instanceId, string calldata fireflyTranId, string calldata payableto) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0o8eyir];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        inst.stateMemory.Payableto = payableto;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0o8eyir, fireflyTranId);
        inst.messages[MessageKey.Message_1xm9dxy].state = ElementState.DISABLED;
        inst.messages[MessageKey.Message_104h2tt].state = ElementState.DISABLED;
        inst.messages[MessageKey.Message_1ljlm4g].state = ElementState.ENABLED;

    }

function Message_0r9lypd_Send(uint256 instanceId, string calldata fireflyTranId, bool confirm) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0r9lypd];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        inst.stateMemory.Confirm = confirm;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0r9lypd, fireflyTranId);
        inst.gateways[GatewayKey.ExclusiveGateway_106je4z].state = ElementState.ENABLED;

    }

function Message_0vlxzcv_Send(uint256 instanceId, string calldata fireflyTranId, int256 discount1) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0vlxzcv];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        inst.stateMemory.Discount1 = discount1;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0vlxzcv, fireflyTranId);
        inst.gateways[GatewayKey.Gateway_1atxr3y].state = ElementState.ENABLED;

    }

function Message_104h2tt_Send(uint256 instanceId, string calldata fireflyTranId, int256 VIPpoints, string calldata VIPcardId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_104h2tt];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        inst.stateMemory.VIPpoints = VIPpoints;
        inst.stateMemory.VIPcardId = VIPcardId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_104h2tt, fireflyTranId);
        inst.messages[MessageKey.Message_0o8eyir].state = ElementState.DISABLED;
        inst.messages[MessageKey.Message_1xm9dxy].state = ElementState.DISABLED;
        inst.businessRules[BusinessRuleKey.Activity_0b1f7uv].state = ElementState.ENABLED;

    }

function Message_1em0ee4_Send(uint256 instanceId, string calldata fireflyTranId, int256 quotation) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1em0ee4];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        inst.stateMemory.Quotation = quotation;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1em0ee4, fireflyTranId);
        inst.messages[MessageKey.Message_1nlagx2].state = ElementState.ENABLED;

    }

function Message_1etcmvl_Send(uint256 instanceId, string calldata fireflyTranId, string calldata payableto) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1etcmvl];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        inst.stateMemory.Payableto = payableto;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1etcmvl, fireflyTranId);
        inst.events[EventKey.EndEvent_146eii4].state = ElementState.ENABLED;

    }

function Message_1joj7ca_Send(uint256 instanceId, string calldata fireflyTranId, string calldata ID) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1joj7ca];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        inst.stateMemory.ID = ID;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1joj7ca, fireflyTranId);
        inst.messages[MessageKey.Message_1etcmvl].state = ElementState.ENABLED;

    }

function Message_1ljlm4g_Send(uint256 instanceId, string calldata fireflyTranId, string calldata booking_id) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1ljlm4g];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        inst.stateMemory.Booking_id = booking_id;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1ljlm4g, fireflyTranId);
        inst.messages[MessageKey.Message_0m9p3da].state = ElementState.ENABLED;

    }

function Message_1nlagx2_Send(uint256 instanceId, string calldata fireflyTranId, bool confirmation) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1nlagx2];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        inst.stateMemory.Confirmation = confirmation;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1nlagx2, fireflyTranId);
        inst.gateways[GatewayKey.EventBasedGateway_1fxpmyn].state = ElementState.ENABLED;

    }

function Message_1xm9dxy_Send(uint256 instanceId, string calldata fireflyTranId, string calldata motivation) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1xm9dxy];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        inst.stateMemory.Motivation = motivation;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1xm9dxy, fireflyTranId);
        inst.messages[MessageKey.Message_0o8eyir].state = ElementState.DISABLED;
        inst.messages[MessageKey.Message_104h2tt].state = ElementState.DISABLED;
        inst.events[EventKey.EndEvent_0366pfz].state = ElementState.ENABLED;

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

function Gateway_1jhfnrm(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Gateway storage g = inst.gateways[GatewayKey.Gateway_1jhfnrm];
        require(g.exists, "gateway not set");
        require(g.state == ElementState.ENABLED, "gateway state not allowed");

        g.state = ElementState.COMPLETED;
        emit GatewayDone(instanceId, GatewayKey.Gateway_1jhfnrm);
        if (inst.stateMemory.VIPLevel < 3) {
            inst.messages[MessageKey.Message_0vlxzcv].state = ElementState.ENABLED;
        }
        else if (inst.stateMemory.VIPLevel == 3) {
            inst.messages[MessageKey.Message_04ikf2n].state = ElementState.ENABLED;
        }

    }

function Gateway_1atxr3y(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Gateway storage g = inst.gateways[GatewayKey.Gateway_1atxr3y];
        require(g.exists, "gateway not set");
        require(g.state == ElementState.ENABLED, "gateway state not allowed");

        g.state = ElementState.COMPLETED;
        emit GatewayDone(instanceId, GatewayKey.Gateway_1atxr3y);
        inst.messages[MessageKey.Message_0o8eyir].state = ElementState.ENABLED;

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
        inst.messages[MessageKey.Message_104h2tt].state = ElementState.ENABLED;

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
