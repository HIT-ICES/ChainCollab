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

contract BikeRental {
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
        StartEvent_0gb8jks,        EndEvent_11pwcmo    }

    enum BusinessRuleKey {
        PlaceholderBusinessRule
    }

    struct StateMemory {
        bool Ask;
        bool InsuranceReq;
        bool IsAvailable;
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
        address Participant_1jz106x_account;
        string Participant_1jz106x_org;
        address Participant_0jcddbb_account;
        string Participant_0jcddbb_org;
        address Participant_0c1qh31_account;
        string Participant_0c1qh31_org;
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
            ParticipantKey.Participant_1jz106x,
            params.Participant_1jz106x_account,
            params.Participant_1jz106x_org,
            false,
            0,
            0
        );
        _createParticipant(
            inst,
            ParticipantKey.Participant_0jcddbb,
            params.Participant_0jcddbb_account,
            params.Participant_0jcddbb_org,
            false,
            0,
            0
        );
        _createParticipant(
            inst,
            ParticipantKey.Participant_0c1qh31,
            params.Participant_0c1qh31_account,
            params.Participant_0c1qh31_org,
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
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_02ckm6k,
            ParticipantKey.Participant_0jcddbb,
            ParticipantKey.Participant_1jz106x,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_06bv1qa,
            ParticipantKey.Participant_1jz106x,
            ParticipantKey.Participant_0jcddbb,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_0b1e9t1,
            ParticipantKey.Participant_1jz106x,
            ParticipantKey.Participant_0jcddbb,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_0cq2w1g,
            ParticipantKey.Participant_0jcddbb,
            ParticipantKey.Participant_1jz106x,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_0g4xpdf,
            ParticipantKey.Participant_1jz106x,
            ParticipantKey.Participant_0jcddbb,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_0hzpgno,
            ParticipantKey.Participant_1jz106x,
            ParticipantKey.Participant_0jcddbb,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_0is10sh,
            ParticipantKey.Participant_1jz106x,
            ParticipantKey.Participant_0jcddbb,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_0l75vce,
            ParticipantKey.Participant_0jcddbb,
            ParticipantKey.Participant_1jz106x,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_0lvlunm,
            ParticipantKey.Participant_0c1qh31,
            ParticipantKey.Participant_0jcddbb,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_0nkjynd,
            ParticipantKey.Participant_0jcddbb,
            ParticipantKey.Participant_1jz106x,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_0psi2ab,
            ParticipantKey.Participant_0jcddbb,
            ParticipantKey.Participant_0c1qh31,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_0to30q0,
            ParticipantKey.Participant_0jcddbb,
            ParticipantKey.Participant_1jz106x,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_1989eur,
            ParticipantKey.Participant_0jcddbb,
            ParticipantKey.Participant_1jz106x,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_1dp5xa4,
            ParticipantKey.Participant_0jcddbb,
            ParticipantKey.Participant_1jz106x,
            ElementState.DISABLED
        );
        _createMessage(
            inst,
            MessageKey.Message_1ufjjj2,
            ParticipantKey.Participant_1jz106x,
            ParticipantKey.Participant_0jcddbb,
            ElementState.DISABLED
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

        messageStates = new uint8[](16);
        messageFireflyTranIds = new string[](16);
        {
            Message storage m = inst.messages[MessageKey.Message_009a0bz];
            messageStates[0] = uint8(m.state);
            messageFireflyTranIds[0] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_02ckm6k];
            messageStates[1] = uint8(m.state);
            messageFireflyTranIds[1] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_06bv1qa];
            messageStates[2] = uint8(m.state);
            messageFireflyTranIds[2] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_0b1e9t1];
            messageStates[3] = uint8(m.state);
            messageFireflyTranIds[3] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_0cq2w1g];
            messageStates[4] = uint8(m.state);
            messageFireflyTranIds[4] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_0g4xpdf];
            messageStates[5] = uint8(m.state);
            messageFireflyTranIds[5] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_0hzpgno];
            messageStates[6] = uint8(m.state);
            messageFireflyTranIds[6] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_0is10sh];
            messageStates[7] = uint8(m.state);
            messageFireflyTranIds[7] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_0l75vce];
            messageStates[8] = uint8(m.state);
            messageFireflyTranIds[8] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_0lvlunm];
            messageStates[9] = uint8(m.state);
            messageFireflyTranIds[9] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_0nkjynd];
            messageStates[10] = uint8(m.state);
            messageFireflyTranIds[10] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_0psi2ab];
            messageStates[11] = uint8(m.state);
            messageFireflyTranIds[11] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_0to30q0];
            messageStates[12] = uint8(m.state);
            messageFireflyTranIds[12] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_1989eur];
            messageStates[13] = uint8(m.state);
            messageFireflyTranIds[13] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_1dp5xa4];
            messageStates[14] = uint8(m.state);
            messageFireflyTranIds[14] = m.fireflyTranId;
        }
        {
            Message storage m = inst.messages[MessageKey.Message_1ufjjj2];
            messageStates[15] = uint8(m.state);
            messageFireflyTranIds[15] = m.fireflyTranId;
        }

        gatewayStates = new uint8[](10);
        {
            Gateway storage g = inst.gateways[GatewayKey.ExclusiveGateway_0uhgcse];
            gatewayStates[0] = uint8(g.state);
        }
        {
            Gateway storage g = inst.gateways[GatewayKey.ExclusiveGateway_1e98v4d];
            gatewayStates[1] = uint8(g.state);
        }
        {
            Gateway storage g = inst.gateways[GatewayKey.ExclusiveGateway_04bkb0l];
            gatewayStates[2] = uint8(g.state);
        }
        {
            Gateway storage g = inst.gateways[GatewayKey.ExclusiveGateway_0cfvdeh];
            gatewayStates[3] = uint8(g.state);
        }
        {
            Gateway storage g = inst.gateways[GatewayKey.ExclusiveGateway_1ksw1j2];
            gatewayStates[4] = uint8(g.state);
        }
        {
            Gateway storage g = inst.gateways[GatewayKey.ExclusiveGateway_05xdg8u];
            gatewayStates[5] = uint8(g.state);
        }
        {
            Gateway storage g = inst.gateways[GatewayKey.ExclusiveGateway_0wc677m];
            gatewayStates[6] = uint8(g.state);
        }
        {
            Gateway storage g = inst.gateways[GatewayKey.ParallelGateway_0yw95j2];
            gatewayStates[7] = uint8(g.state);
        }
        {
            Gateway storage g = inst.gateways[GatewayKey.ParallelGateway_0himv1h];
            gatewayStates[8] = uint8(g.state);
        }
        {
            Gateway storage g = inst.gateways[GatewayKey.EventBasedGateway_1nphygh];
            gatewayStates[9] = uint8(g.state);
        }

        eventStates = new uint8[](2);
        {
            ActionEvent storage ev = inst.events[EventKey.StartEvent_0gb8jks];
            eventStates[0] = uint8(ev.state);
        }
        {
            ActionEvent storage ev = inst.events[EventKey.EndEvent_11pwcmo];
            eventStates[1] = uint8(ev.state);
        }

        businessRuleStates = new uint8[](0);
        businessRuleRequestIds = new bytes32[](0);
    }


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
        inst.messages[MessageKey.Message_0psi2ab].state = ElementState.ENABLED;

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
        inst.messages[MessageKey.Message_06bv1qa].state = ElementState.ENABLED;

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
        inst.gateways[GatewayKey.ExclusiveGateway_1e98v4d].state = ElementState.ENABLED;

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
        inst.messages[MessageKey.Message_0hzpgno].state = ElementState.ENABLED;

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
        inst.messages[MessageKey.Message_1989eur].state = ElementState.DISABLED;
        inst.messages[MessageKey.Message_1ufjjj2].state = ElementState.ENABLED;

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
        inst.gateways[GatewayKey.ParallelGateway_0himv1h].state = ElementState.ENABLED;

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
        inst.gateways[GatewayKey.EventBasedGateway_1nphygh].state = ElementState.ENABLED;

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
        inst.gateways[GatewayKey.ParallelGateway_0himv1h].state = ElementState.ENABLED;

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
        inst.gateways[GatewayKey.ExclusiveGateway_05xdg8u].state = ElementState.ENABLED;

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
        inst.gateways[GatewayKey.ExclusiveGateway_0wc677m].state = ElementState.ENABLED;

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
        inst.messages[MessageKey.Message_0b1e9t1].state = ElementState.ENABLED;

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
        inst.messages[MessageKey.Message_0lvlunm].state = ElementState.ENABLED;

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
        inst.gateways[GatewayKey.ExclusiveGateway_0cfvdeh].state = ElementState.ENABLED;

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
        inst.messages[MessageKey.Message_0cq2w1g].state = ElementState.DISABLED;
        inst.gateways[GatewayKey.ExclusiveGateway_1ksw1j2].state = ElementState.ENABLED;

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
        inst.gateways[GatewayKey.ParallelGateway_0yw95j2].state = ElementState.ENABLED;

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
        inst.gateways[GatewayKey.ExclusiveGateway_04bkb0l].state = ElementState.ENABLED;

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
