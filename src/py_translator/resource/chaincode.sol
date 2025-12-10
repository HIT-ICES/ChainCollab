// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IOracle {
    /// @notice 在原链码中相当于 Oracle:getDataItem(instanceID, ActivityID)
    function getDataItem(
        uint256 instanceId,
        string calldata activityId
    ) external view returns (string memory value);
}

contract WorkflowContract {
    // -------------------- 基本枚举 --------------------

    /// @dev 与 Go 代码中 ElementState 一致
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
        Message_1b1qlzd,
        Message_01jq2zl,
        Message_12n6jjk,
        Message_076ulzs,
        Message_068kmzv,
        Message_09krt7c,
        Message_1bhhp1n,
        Message_0ywghlt
    }

    enum GatewayKey {
        Gateway_0auc3he,
        Gateway_0ivv4vg,
        Gateway_0jgq0a6
    }

    enum EventKey {
        Event_0ojehz6,
        Event_0ci2gl8,
        Event_0dyp0ut
    }

    // -------------------- 结构体定义 --------------------

    /// @dev 对应 StateMemory(Type, Duration, Confirm)
    struct StateMemory {
        string typeName;
        uint256 duration;
        bool confirm;
    }

    /// @dev Participant：这里用地址代替原来的 MSP/X509 身份
    struct Participant {
        bool exists;
        address account;       // 对应谁可以发消息/操作
        bool isMulti;          // 仅保留字段，不在此示例中使用
        uint8 multiMaximum;    // 仅保留字段
        uint8 multiMinimum;    // 仅保留字段
    }

    struct Message {
        bool exists;
        ParticipantKey sendParticipant;
        ParticipantKey receiveParticipant;
        string fireflyTranId;
        ElementState state;
        string formatJson; // 原代码里的 JSON Schema 字符串
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
        bytes32 hashOfDmn;     // keccak256(DMN content)
        string decisionId;
        ElementState state;
    }

    /// @dev 合约实例，等价于原 ContractInstance
    struct Instance {
        bool exists;
        uint256 instanceId;
        StateMemory stateMemory;
        mapping(MessageKey => Message) messages;
        mapping(GatewayKey => Gateway) gateways;
        mapping(EventKey => ActionEvent) events;
        mapping(ParticipantKey => Participant) participants;
        BusinessRule businessRule; // 仅有 Activity_0tya4bp
    }

    // -------------------- 状态变量 --------------------

    address public owner;
    bool public isInited;
    uint256 public currentInstanceId; // 自增 ID，与原 "currentInstanceID" 类似
    IOracle public oracle;

    mapping(uint256 => Instance) private instances;

    // -------------------- 事件（替代 Fabric 的 stub.SetEvent） --------------------

    event InitContractEvent();
    event InstanceCreated(uint256 indexed instanceId, string activityContent);

    event MessageSent(
        uint256 indexed instanceId,
        MessageKey indexed key,
        string fireflyTranId
    );
    event GatewayDone(uint256 indexed instanceId, GatewayKey indexed key);
    event ActionEventDone(uint256 indexed instanceId, EventKey indexed key);

    /// @dev 对应 Activity_0tya4bp 中触发的 “DMNContentRequired”
    event DMNContentRequired(
        uint256 indexed instanceId,
        string funcToCall,
        string cid
    );

    /// @dev 对应 Activity_0tya4bp_Continue 中触发的 "Avtivity_continueDone"
    event ActivityContinueDone(uint256 indexed instanceId);

    // -------------------- 修饰符 --------------------

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    modifier onlyInitialized() {
        require(isInited, "contract not initialized");
        _;
    }

    // -------------------- 构造与初始化 --------------------

    constructor(address oracleAddress) {
        owner = msg.sender;
        oracle = IOracle(oracleAddress);
    }

    function setOracle(address oracleAddress) external onlyOwner {
        oracle = IOracle(oracleAddress);
    }

    /// @dev 等价于 InitLedger：只能调用一次
    function initLedger() external onlyOwner {
        require(!isInited, "already initialized");
        isInited = true;
        currentInstanceId = 0;
        emit InitContractEvent();
    }

    // -------------------- 内部工具函数 --------------------

    function _getInstance(
        uint256 instanceId
    ) internal view returns (Instance storage inst) {
        inst = instances[instanceId];
        require(inst.exists, "instance does not exist");
    }

    function _checkParticipant(
        Instance storage inst,
        ParticipantKey pk
    ) internal view {
        Participant storage p = inst.participants[pk];
        require(p.exists, "participant not set");
        require(msg.sender == p.account, "participant not allowed");
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
        string memory dmnContent,
        string memory decisionId
    ) internal {
        inst.businessRule = BusinessRule({
            exists: true,
            hashOfDmn: keccak256(bytes(dmnContent)),
            decisionId: decisionId,
            state: ElementState.DISABLED
        });
    }

    // -------------------- 创建实例（对应 CreateInstance） --------------------

    struct InitParameters {
        address participant1;
        address participant2;
        string activity_0tya4bp_Content;
        string activity_0tya4bp_DecisionID;
        // 原 ParamMapping 在 Solidity 中不再使用（反射 + JSON 不方便）
    }

    function createInstance(
        InitParameters calldata params
    ) external onlyInitialized onlyOwner returns (uint256 instanceId) {
        instanceId = currentInstanceId;

        Instance storage inst = instances[instanceId];
        require(!inst.exists, "instance already exists");

        inst.exists = true;
        inst.instanceId = instanceId;

        // Participants
        _createParticipant(
            inst,
            ParticipantKey.Participant_1p9owwo,
            params.participant1,
            false,
            0,
            0
        );
        _createParticipant(
            inst,
            ParticipantKey.Participant_12df78t,
            params.participant2,
            false,
            0,
            0
        );

        // Events
        _createActionEvent(inst, EventKey.Event_0ojehz6, ElementState.ENABLED);
        _createActionEvent(inst, EventKey.Event_0ci2gl8, ElementState.DISABLED);
        _createActionEvent(inst, EventKey.Event_0dyp0ut, ElementState.DISABLED);

        // Messages（Format JSON 与原代码保持一致）
        _createMessage(
            inst,
            MessageKey.Message_1b1qlzd,
            ParticipantKey.Participant_1p9owwo,
            ParticipantKey.Participant_12df78t,
            ElementState.DISABLED,
            '{"properties":{"reason":{"type":"string","description":""},"result":{"type":"string","description":""}},"required":["reason","result"],"files":{},"file required":[]}'
        );

        _createMessage(
            inst,
            MessageKey.Message_01jq2zl,
            ParticipantKey.Participant_1p9owwo,
            ParticipantKey.Participant_12df78t,
            ElementState.DISABLED,
            '{"properties":{"amount":{"type":"number","description":""}},"required":["amount"],"files":{},"file required":[]}'
        );

        _createMessage(
            inst,
            MessageKey.Message_12n6jjk,
            ParticipantKey.Participant_12df78t,
            ParticipantKey.Participant_1p9owwo,
            ElementState.DISABLED,
            '{"properties":{"type":{"type":"string","description":""},"duration":{"type":"number","description":""}},"required":["type","duration"],"files":{},"file required":[]}'
        );

        _createMessage(
            inst,
            MessageKey.Message_076ulzs,
            ParticipantKey.Participant_12df78t,
            ParticipantKey.Participant_1p9owwo,
            ElementState.DISABLED,
            '{"properties":{"time":{"type":"string","description":""},"description":{"type":"string","description":""},"EC2 resource ID":{"type":"string","description":""},"logs":{"type":"string","description":""},"other information":{"type":"string","description":""}},"required":["time","description","EC2 resource ID","logs"],"files":{},"file required":[]}'
        );

        _createMessage(
            inst,
            MessageKey.Message_068kmzv,
            ParticipantKey.Participant_12df78t,
            ParticipantKey.Participant_1p9owwo,
            ElementState.DISABLED,
            '{"properties":{"time":{"type":"string","description":""},"instance ID":{"type":"string","description":""},"logs":{"type":"string","description":""}},"required":["time","instance ID","logs"],"files":{},"file required":[]}'
        );

        _createMessage(
            inst,
            MessageKey.Message_09krt7c,
            ParticipantKey.Participant_1p9owwo,
            ParticipantKey.Participant_12df78t,
            ElementState.DISABLED,
            '{"properties":{"question name":{"type":"string","description":""},"description":{"type":"string","description":""}},"required":["question name","description"],"files":{},"file required":[]}'
        );

        _createMessage(
            inst,
            MessageKey.Message_1bhhp1n,
            ParticipantKey.Participant_12df78t,
            ParticipantKey.Participant_1p9owwo,
            ElementState.DISABLED,
            '{"properties":{"serviceType":{"type":"string","description":""}},"required":["serviceType"],"files":{},"file required":[]}'
        );

        _createMessage(
            inst,
            MessageKey.Message_0ywghlt,
            ParticipantKey.Participant_12df78t,
            ParticipantKey.Participant_1p9owwo,
            ElementState.DISABLED,
            '{"properties":{"serviceType":{"type":"string","description":""}},"required":["serviceType"],"files":{},"file required":[]}'
        );

        // Gateways
        _createGateway(inst, GatewayKey.Gateway_0auc3he, ElementState.DISABLED);
        _createGateway(inst, GatewayKey.Gateway_0ivv4vg, ElementState.DISABLED);
        _createGateway(inst, GatewayKey.Gateway_0jgq0a6, ElementState.DISABLED);

        // BusinessRule Activity_0tya4bp
        _createBusinessRule(
            inst,
            params.activity_0tya4bp_Content,
            params.activity_0tya4bp_DecisionID
        );

        emit InstanceCreated(instanceId, params.activity_0tya4bp_Content);

        // 自增 ID
        currentInstanceId += 1;
    }

    // -------------------- 读取全局变量（对应 ReadGlobalVariable） --------------------

    function getStateMemory(
        uint256 instanceId
    ) external view returns (string memory typeName, uint256 duration, bool confirm) {
        Instance storage inst = _getInstance(instanceId);
        StateMemory storage sm = inst.stateMemory;
        return (sm.typeName, sm.duration, sm.confirm);
    }

    // -------------------- 事件 / 消息 / 网关 流程 --------------------

    /// @dev Event_0ojehz6：启动流程，启用 Message_09krt7c
    function Event_0ojehz6(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        ActionEvent storage ev = inst.events[EventKey.Event_0ojehz6];

        require(ev.exists, "event not set");
        require(ev.state == ElementState.ENABLED, "event state not allowed");

        ev.state = ElementState.COMPLETED;
        emit ActionEventDone(instanceId, EventKey.Event_0ojehz6);

        // 启用 Message_09krt7c
        inst.messages[MessageKey.Message_09krt7c].state = ElementState.ENABLED;
    }

    /// @dev Message_09krt7c_Send：发送后启用 Gateway_0jgq0a6
    function Message_09krt7c_Send(
        uint256 instanceId,
        string calldata fireflyTranId
    ) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_09krt7c];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_09krt7c, fireflyTranId);

        inst.gateways[GatewayKey.Gateway_0jgq0a6].state = ElementState.ENABLED;
    }

    /// @dev Gateway_0jgq0a6：完成后启用两个消息
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

    function Message_0ywghlt_Send(
        uint256 instanceId,
        string calldata fireflyTranId
    ) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_0ywghlt];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_0ywghlt, fireflyTranId);

        // 禁用另一路，启用 Message_068kmzv
        inst.messages[MessageKey.Message_1bhhp1n].state = ElementState.DISABLED;
        inst.messages[MessageKey.Message_068kmzv].state = ElementState.ENABLED;
    }

    function Message_1bhhp1n_Send(
        uint256 instanceId,
        string calldata fireflyTranId
    ) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1bhhp1n];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1bhhp1n, fireflyTranId);

        inst.messages[MessageKey.Message_0ywghlt].state = ElementState.DISABLED;
        inst.messages[MessageKey.Message_076ulzs].state = ElementState.ENABLED;
    }

    function Message_068kmzv_Send(
        uint256 instanceId,
        string calldata fireflyTranId
    ) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_068kmzv];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_068kmzv, fireflyTranId);

        inst.gateways[GatewayKey.Gateway_0auc3he].state = ElementState.ENABLED;
    }

    function Message_076ulzs_Send(
        uint256 instanceId,
        string calldata fireflyTranId
    ) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_076ulzs];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_076ulzs, fireflyTranId);

        inst.gateways[GatewayKey.Gateway_0auc3he].state = ElementState.ENABLED;
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

    /// @dev Message_12n6jjk_Send：写入 StateMemory(Type, Duration)，并启用 BusinessRule
    function Message_12n6jjk_Send(
        uint256 instanceId,
        string calldata fireflyTranId,
        string calldata typeName,
        uint256 duration
    ) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_12n6jjk];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_12n6jjk, fireflyTranId);

        inst.stateMemory.typeName = typeName;
        inst.stateMemory.duration = duration;

        require(inst.businessRule.exists, "business rule not set");
        inst.businessRule.state = ElementState.ENABLED;
    }

    // -------------------- Activity_0tya4bp 业务规则 --------------------

    /// @dev 对应 Activity_0tya4bp：调用 Oracle 拿 CID，触发事件，并把 BusinessRule 置为 WAITING_FOR_CONFIRMATION
    function Activity_0tya4bp(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        BusinessRule storage br = inst.businessRule;
        require(br.exists, "business rule not set");
        require(
            br.state == ElementState.ENABLED,
            "business rule not enabled"
        );

        // 调用 Oracle 合约以获取 CID（具体实现由外部合约提供）
        string memory cid = oracle.getDataItem(instanceId, "Activity_0tya4bp");

        emit DMNContentRequired(
            instanceId,
            "Activity_0tya4bp_Continue",
            cid
        );

        br.state = ElementState.WAITING_FOR_CONFIRMATION;
    }

    /// @dev 对应 Activity_0tya4bp_Continue：
    ///      在原链码中，会：
    ///        1. 验证 DMN 内容哈希
    ///        2. 调用 DMNEngine 链码得到输出，并更新 StateMemory(Type, Duration, Confirm)
    ///
    ///      这里简化为：
    ///        - 仍然验证 DMN 内容哈希
    ///        - 假定 DMN 计算在链下完成，把新的 Type/Duration/Confirm 当作参数传入
    function Activity_0tya4bp_Continue(
        uint256 instanceId,
        string calldata dmnContent,
        string calldata newType,
        uint256 newDuration,
        bool newConfirm
    ) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        BusinessRule storage br = inst.businessRule;
        require(
            br.state == ElementState.WAITING_FOR_CONFIRMATION,
            "business rule not waiting"
        );

        // 哈希校验（Fabric 中是 SHA256，这里用 keccak256）
        bytes32 h = keccak256(bytes(dmnContent));
        require(h == br.hashOfDmn, "DMN content hash mismatch");

        // 更新全局 StateMemory
        inst.stateMemory.typeName = newType;
        inst.stateMemory.duration = newDuration;
        inst.stateMemory.confirm = newConfirm;

        // 完成规则，启用 Gateway_0ivv4vg
        br.state = ElementState.COMPLETED;
        inst.gateways[GatewayKey.Gateway_0ivv4vg].state = ElementState.ENABLED;

        emit ActivityContinueDone(instanceId);
    }

    // -------------------- Gateway_0ivv4vg & 分支消息 --------------------

    function Gateway_0ivv4vg(uint256 instanceId) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Gateway storage g = inst.gateways[GatewayKey.Gateway_0ivv4vg];
        require(g.exists, "gateway not set");
        require(g.state == ElementState.ENABLED, "gateway state not allowed");

        g.state = ElementState.COMPLETED;
        emit GatewayDone(instanceId, GatewayKey.Gateway_0ivv4vg);

        // 根据 StateMemory.confirm 选择启用哪个消息
        if (!inst.stateMemory.confirm) {
            inst.messages[MessageKey.Message_1b1qlzd].state = ElementState.ENABLED;
        } else {
            inst.messages[MessageKey.Message_01jq2zl].state = ElementState.ENABLED;
        }
    }

    function Message_1b1qlzd_Send(
        uint256 instanceId,
        string calldata fireflyTranId
    ) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_1b1qlzd];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_1b1qlzd, fireflyTranId);

        inst.events[EventKey.Event_0dyp0ut].state = ElementState.ENABLED;
    }

    function Message_01jq2zl_Send(
        uint256 instanceId,
        string calldata fireflyTranId
    ) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.Message_01jq2zl];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.Message_01jq2zl, fireflyTranId);

        inst.events[EventKey.Event_0ci2gl8].state = ElementState.ENABLED;
    }

    // -------------------- 结束事件 Event_0ci2gl8 / Event_0dyp0ut --------------------

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
