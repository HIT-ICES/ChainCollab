// SPDX-License-Identifier: GPL-3.0
pragma solidity ^0.8.0;
pragma experimental ABIEncoderV2;
// pragma experimental SMTChecker; // SMT solver 额外的安全检查

// 定义元素状态
enum ElementState {
    DISABLED,
    ENABLED,
    WAITINGFORCONFIRMATION,
    COMPLETED
}

// 定义实例状态
enum InstanceState {
    DISABLED,
    ENABLED,
    WAITINGFORCONFIRMATION,
    COMPLETED
}

struct ActionEvent {
    string EventID;
    ElementState EventState;
}

// // 定义全局状态存储
// struct StateMemory {
//     uint NumberOfUnits;
//     bool Urgent;
//     uint SupplierReputation;
//     string FinalPriority;
// }

struct Participant {
    string ParticipantID;
    string MSP;
    mapping(string => string) Attributes;
    bool IsMulti;
    uint MultiMaximum;
    uint MultiMinimum;
    string X509;    // 加一个address
}

struct Message {
    string MessageID;
    string SendParticipantID;
    string ReceiveParticipantID;
    string FireflyTranID;
    ElementState MsgState;
    string Format;
}

struct Gateway {
    string GatewayID;
    ElementState GatewayState;
}

// 定义业务规则
// struct BusinessRule {
//     string RuleID;
//     string Description;
//     bool IsEnabled;
// }

// 定义状态内存
struct StateMemory {
    uint NumberOfUnits;
    bool Urgent;
    uint SupplierReputation;
    string FinalPriority;
}

// 定义初始化参数
struct InitParameters {
    mapping(string => Participant) Participants;
    // string ActivityDecisionID;
    // mapping(string => string) ActivityParamMapping;
    // string ActivityContent;
}

// 定义合约实例
struct ContractInstance {
    string InstanceID; // 实例ID
    StateMemory InstanceStateMemory; // 全局状态存储
    mapping(string => Message) InstanceMessages; // 消息映射
    mapping(string => Gateway) InstanceGateways; // 网关映射
    mapping(string => ActionEvent) InstanceActionEvents; // 事件映射
    // mapping(string => BusinessRule) InstanceBusinessRules; // 业务规则映射
    mapping(string => Participant) InstanceParticipants; // 参与者映射
    InstanceState InstanceState; // 实例状态
}

contract BpmnSupply {
    // enum State {DISABLED, ENABLED, WAITINGFORCONFIRMATION, COMPLETED} State s;

    // 合约初始化状态
    string public contractState;

    // 合约所有者
    address public owner;

    // 事件日志
    event ContractInitialized(string state, address owner);
    event ParticipantAdded(string participantID, string msp);

    // 构造函数
    constructor() {
        owner = msg.sender;
        contractState = "Initialized";
        emit ContractInitialized(contractState, owner);

        //enable the start process
        initLedger();
    }

    // 事件定义
    event InitContractEvent(string message);

    // 存储状态
    bool private isInited = false; // 用于标识合约是否已初始化
    string private currentInstanceID = "0"; // 存储当前实例ID

    function initLedger() public {
        // 如果合约已经初始化，抛出错误
        require(!isInited, "Contract has already been initialized");

        // 执行初始化操作
        currentInstanceID = "0"; // 初始化当前实例ID
        isInited = true; // 标记合约已经初始化

        // 触发事件，通知初始化成功
        emit InitContractEvent("Contract has been initialized successfully");
    }

    // 获取当前实例ID
    function getCurrentInstanceID() public view returns (string memory) {
        return currentInstanceID;
    }

    // 获取合约初始化状态
    function getIsInited() public view returns (bool) {
        return isInited;
    }

    // 事件定义
    event CreateInstanceEvent(string instanceID, string message);

    // 状态变量
    uint private instanceCount = 0; // 用于生成唯一实例ID的计数器
    mapping(string => ContractInstance) private instances; // 存储所有实例的映射

    // // 定义实例结构体
    // struct Instance {
    //     string instanceID;    // 实例ID
    //     string creator;       // 实例创建者
    //     uint creationTime;    // 创建时间戳
    //     bool isActive;        // 实例是否激活
    // }

    // 创建实例方法
    function createInstance(
        string memory creator
    ) public returns (string memory) {
        instanceCount++; // 增加实例计数器
        string memory newInstanceID = string(
            abi.encodePacked("instance_", uint2str(instanceCount))
        ); // 生成新的实例ID

        // 创建实例并存储
        Instance memory newInstance = Instance({
            instanceID: newInstanceID,
            creator: creator,
            creationTime: block.timestamp,
            isActive: true
        });
        instances[newInstanceID] = newInstance; // 存储实例数据

        // 触发事件，通知实例创建
        emit CreateInstanceEvent(
            newInstanceID,
            "New instance created successfully"
        );

        return newInstanceID; // 返回新的实例ID
    }

    // 获取实例信息
    function getInstance(
        string memory instanceID
    ) public view returns (Instance memory) {
        return instances[instanceID]; // 返回指定实例的数据
    }

    // 辅助函数：将 uint 转换为 string
    function uint2str(uint _i) internal pure returns (string memory str) {
        if (_i == 0) {
            return "0";
        }
        uint j = _i;
        uint length;
        while (j != 0) {
            length++;
            j /= 10;
        }
        bytes memory bstr = new bytes(length);
        uint k = length;
        while (_i != 0) {
            bstr[--k] = bytes1(uint8(48 + (_i % 10)));
            _i /= 10;
        }
        str = string(bstr);
    }

    // 创建参与者
    function createParticipant(
        string memory participantID,
        string memory msp,
        bool isMulti,
        uint multiMaximum,
        uint multiMinimum,
        string memory x509
    ) public {
        // 获取当前实例
        ContractInstance storage currentInstance = instances[currentInstanceID];

        // 创建并存储参与者
        Participant storage newParticipant = currentInstance
            .InstanceParticipants[participantID];
        newParticipant.ParticipantID = participantID;
        newParticipant.MSP = msp;
        newParticipant.IsMulti = isMulti;
        newParticipant.MultiMaximum = multiMaximum;
        newParticipant.MultiMinimum = multiMinimum;
        newParticipant.X509 = x509;

        emit ParticipantAdded(participantID, msp);
    }

    // 创建消息
function createMessage(
    string memory messageID,
    string memory sendParticipantID,
    string memory receiveParticipantID,
    string memory fireflyTranID,
    ElementState msgState,
    string memory format
) public {
    // 获取当前实例
    ContractInstance storage currentInstance = instances[currentInstanceID];
    
    // 创建并存储消息
    Message storage newMessage = currentInstance.InstanceMessages[messageID];
    newMessage.MessageID = messageID;
    newMessage.SendParticipantID = sendParticipantID;
    newMessage.ReceiveParticipantID = receiveParticipantID;
    newMessage.FireflyTranID = fireflyTranID;
    newMessage.MsgState = msgState;
    newMessage.Format = format;

    emit CreateMessageEvent(messageID, "Message created successfully");
}

// 消息创建事件
event CreateMessageEvent(string messageID, string message);

// 创建网关
function createGateway(
    string memory gatewayID,
    ElementState gatewayState
) public {
    // 获取当前实例
    ContractInstance storage currentInstance = instances[currentInstanceID];
    
    // 创建并存储网关
    Gateway storage newGateway = currentInstance.InstanceGateways[gatewayID];
    newGateway.GatewayID = gatewayID;
    newGateway.GatewayState = gatewayState;

    emit CreateGatewayEvent(gatewayID, "Gateway created successfully");
}

// 网关创建事件
event CreateGatewayEvent(string gatewayID, string message);


// 创建操作事件
function createActionEvent(
    string memory eventID,
    ElementState eventState
) public {
    // 获取当前实例
    ContractInstance storage currentInstance = instances[currentInstanceID];
    
    // 创建并存储操作事件
    ActionEvent storage newActionEvent = currentInstance.InstanceActionEvents[eventID];
    newActionEvent.EventID = eventID;
    newActionEvent.EventState = eventState;

    emit CreateActionEventEvent(eventID, "ActionEvent created successfully");
}

// 操作事件创建事件
event CreateActionEventEvent(string eventID, string message);


// 获取实例信息
function getInstance(string memory instanceID) public view returns (
    string memory instanceID_,
    string memory creator,
    uint creationTime,
    bool isActive,
    StateMemory memory stateMemory,
    InstanceState instanceState
) {
    // 获取当前实例
    ContractInstance storage currentInstance = instances[instanceID];
    
    instanceID_ = currentInstance.InstanceID;
    creator = currentInstance.InstanceParticipants[creator].ParticipantID;
    creationTime = currentInstance.creationTime;
    isActive = currentInstance.isActive;
    stateMemory = currentInstance.InstanceStateMemory;
    instanceState = currentInstance.InstanceState;
}

// 设置实例信息
function setInstance(
    string memory instanceID,
    string memory creator,
    uint creationTime,
    bool isActive
) public {
    // 创建并存储实例
    ContractInstance storage newInstance = instances[instanceID];
    newInstance.InstanceID = instanceID;
    newInstance.creator = creator;
    newInstance.creationTime = creationTime;
    newInstance.isActive = isActive;

    emit SetInstanceEvent(instanceID, "Instance set successfully");
}

// 实例设置事件
event SetInstanceEvent(string instanceID, string message);

// 读取消息
function readMsg(string memory instanceID, string memory messageID) public view returns (
    string memory messageID_,
    string memory sendParticipantID,
    string memory receiveParticipantID,
    string memory fireflyTranID,
    ElementState msgState,
    string memory format
) {
    // 获取当前实例
    ContractInstance storage currentInstance = instances[instanceID];
    
    // 获取消息
    Message storage msg = currentInstance.InstanceMessages[messageID];
    
    messageID_ = msg.MessageID;
    sendParticipantID = msg.SendParticipantID;
    receiveParticipantID = msg.ReceiveParticipantID;
    fireflyTranID = msg.FireflyTranID;
    msgState = msg.MsgState;
    format = msg.Format;
}

// 读取网关
function readGtw(string memory instanceID, string memory gatewayID) public view returns (
    string memory gatewayID_,
    ElementState gatewayState
) {
    // 获取当前实例
    ContractInstance storage currentInstance = instances[instanceID];
    
    // 获取网关
    Gateway storage gtw = currentInstance.InstanceGateways[gatewayID];
    
    gatewayID_ = gtw.GatewayID;
    gatewayState = gtw.GatewayState;
}

// 读取操作事件
function readEvent(string memory instanceID, string memory eventID) public view returns (
    string memory eventID_,
    ElementState eventState
) {
    // 获取当前实例
    ContractInstance storage currentInstance = instances[instanceID];
    
    // 获取操作事件
    ActionEvent storage event_ = currentInstance.InstanceActionEvents[eventID];
    
    eventID_ = event_.EventID;
    eventState = event_.EventState;
}

// 更新消息状态
function changeMsgState(
    string memory instanceID,
    string memory messageID,
    ElementState newState
) public {
    // 获取当前实例
    ContractInstance storage currentInstance = instances[instanceID];
    
    // 获取消息
    Message storage msg = currentInstance.InstanceMessages[messageID];
    
    // 更新消息状态
    msg.MsgState = newState;
    
    emit MsgStateChanged(instanceID, messageID, newState);
}

// 消息状态变化事件
event MsgStateChanged(string instanceID, string messageID, ElementState newState);

// 更新消息的 FireflyTranID
function changeMsgFireflyTranID(
    string memory instanceID,
    string memory messageID,
    string memory newFireflyTranID
) public {
    // 获取当前实例
    ContractInstance storage currentInstance = instances[instanceID];
    
    // 获取消息
    Message storage msg = currentInstance.InstanceMessages[messageID];
    
    // 更新 FireflyTranID
    msg.FireflyTranID = newFireflyTranID;
    
    emit MsgFireflyTranIDChanged(instanceID, messageID, newFireflyTranID);
}

// 消息 FireflyTranID 变化事件
event MsgFireflyTranIDChanged(string instanceID, string messageID, string newFireflyTranID);

// 更新网关状态
function changeGtwState(
    string memory instanceID,
    string memory gatewayID,
    ElementState newState
) public {
    // 获取当前实例
    ContractInstance storage currentInstance = instances[instanceID];
    
    // 获取网关
    Gateway storage gtw = currentInstance.InstanceGateways[gatewayID];
    
    // 更新网关状态
    gtw.GatewayState = newState;
    
    emit GtwStateChanged(instanceID, gatewayID, newState);
}

// 网关状态变化事件
event GtwStateChanged(string instanceID, string gatewayID, ElementState newState);

// 更新事件状态
function changeEventState(
    string memory instanceID,
    string memory eventID,
    ElementState newState
) public {
    // 获取当前实例
    ContractInstance storage currentInstance = instances[instanceID];
    
    // 获取事件
    ActionEvent storage event = currentInstance.InstanceActionEvents[eventID];
    
    // 更新事件状态
    event.EventState = newState;
    
    emit EventStateChanged(instanceID, eventID, newState);
}

// 事件状态变化事件
event EventStateChanged(string instanceID, string eventID, ElementState newState);

// 获取所有消息
function getAllMessages(string memory instanceID) public view returns (Message[] memory) {
    // 获取当前实例
    ContractInstance storage currentInstance = instances[instanceID];
    
    // 计算消息数量
    uint messageCount = 0;
    for (uint i = 0; i < 1000; i++) {  // 假设最多有1000条消息，实际情况可以根据需求调整
        string memory msgID = uint2str(i);
        if (bytes(currentInstance.InstanceMessages[msgID].MessageID).length != 0) {
            messageCount++;
        }
    }

    // 创建一个数组并填充数据
    Message[] memory messages = new Message[](messageCount);
    uint index = 0;
    for (uint i = 0; i < 1000; i++) {
        string memory msgID = uint2str(i);
        if (bytes(currentInstance.InstanceMessages[msgID].MessageID).length != 0) {
            messages[index] = currentInstance.InstanceMessages[msgID];
            index++;
        }
    }

    return messages;
}

// 辅助函数：将 uint 转换为 string
function uint2str(uint _i) internal pure returns (string memory str) {
    if (_i == 0) {
        return "0";
    }
    uint j = _i;
    uint length;
    while (j != 0) {
        length++;
        j /= 10;
    }
    bytes memory bstr = new bytes(length);
    uint k = length;
    while (_i != 0) {
        bstr[--k] = bytes1(uint8(48 + _i % 10));
        _i /= 10;
    }
    str = string(bstr);
}

// 获取所有网关
function getAllGateways(string memory instanceID) public view returns (Gateway[] memory) {
    // 获取当前实例
    ContractInstance storage currentInstance = instances[instanceID];
    
    // 计算网关数量
    uint gatewayCount = 0;
    for (uint i = 0; i < 1000; i++) {  // 假设最多有1000个网关，实际情况可以根据需求调整
        string memory gtwID = uint2str(i);
        if (bytes(currentInstance.InstanceGateways[gtwID].GatewayID).length != 0) {
            gatewayCount++;
        }
    }

    // 创建一个数组并填充数据
    Gateway[] memory gateways = new Gateway[](gatewayCount);
    uint index = 0;
    for (uint i = 0; i < 1000; i++) {
        string memory gtwID = uint2str(i);
        if (bytes(currentInstance.InstanceGateways[gtwID].GatewayID).length != 0) {
            gateways[index] = currentInstance.InstanceGateways[gtwID];
            index++;
        }
    }

    return gateways;
}

// 获取所有操作事件
function getAllActionEvents(string memory instanceID) public view returns (ActionEvent[] memory) {
    // 获取当前实例
    ContractInstance storage currentInstance = instances[instanceID];
    
    // 计算操作事件数量
    uint eventCount = 0;
    for (uint i = 0; i < 1000; i++) {  // 假设最多有1000个事件，实际情况可以根据需求调整
        string memory eventID = uint2str(i);
        if (bytes(currentInstance.InstanceActionEvents[eventID].EventID).length != 0) {
            eventCount++;
        }
    }

    // 创建一个数组并填充数据
    ActionEvent[] memory events = new ActionEvent[](eventCount);
    uint index = 0;
    for (uint i = 0; i < 1000; i++) {
        string memory eventID = uint2str(i);
        if (bytes(currentInstance.InstanceActionEvents[eventID].EventID).length != 0) {
            events[index] = currentInstance.InstanceActionEvents[eventID];
            index++;
        }
    }

    return events;
}

// 获取所有参与者
function getAllParticipants(string memory instanceID) public view returns (Participant[] memory) {
    // 获取当前实例
    ContractInstance storage currentInstance = instances[instanceID];
    
    // 计算参与者数量
    uint participantCount = 0;
    for (uint i = 0; i < 1000; i++) {  // 假设最多有1000个参与者，实际情况可以根据需求调整
        string memory participantID = uint2str(i);
        if (bytes(currentInstance.InstanceParticipants[participantID].ParticipantID).length != 0) {
            participantCount++;
        }
    }

    // 创建一个数组并填充数据
    Participant[] memory participants = new Participant[](participantCount);
    uint index = 0;
    for (uint i = 0; i < 1000; i++) {
        string memory participantID = uint2str(i);
        if (bytes(currentInstance.InstanceParticipants[participantID].ParticipantID).length != 0) {
            participants[index] = currentInstance.InstanceParticipants[participantID];
            index++;
        }
    }

    return participants;
}

// 读取全局变量（实例的StateMemory）
function readGlobalVariable(string memory instanceID) public view returns (
    uint numberOfUnits,
    bool urgent,
    uint supplierReputation,
    string memory finalPriority
) {
    // 获取当前实例
    ContractInstance storage currentInstance = instances[instanceID];
    
    // 返回实例的StateMemory（全局状态存储）
    StateMemory memory stateMemory = currentInstance.InstanceStateMemory;

    numberOfUnits = stateMemory.NumberOfUnits;
    urgent = stateMemory.Urgent;
    supplierReputation = stateMemory.SupplierReputation;
    finalPriority = stateMemory.FinalPriority;
}

// 设置全局变量（更新指定实例的StateMemory）
function setGlobalVariable(
    string memory instanceID,
    uint numberOfUnits,
    bool urgent,
    uint supplierReputation,
    string memory finalPriority
) public {
    // 获取当前实例
    ContractInstance storage currentInstance = instances[instanceID];

    // 更新StateMemory
    currentInstance.InstanceStateMemory.NumberOfUnits = numberOfUnits;
    currentInstance.InstanceStateMemory.Urgent = urgent;
    currentInstance.InstanceStateMemory.SupplierReputation = supplierReputation;
    currentInstance.InstanceStateMemory.FinalPriority = finalPriority;

    // 触发事件通知
    emit GlobalVariableUpdated(instanceID, numberOfUnits, urgent, supplierReputation, finalPriority);
}

// 更新全局变量的事件
event GlobalVariableUpdated(
    string instanceID,
    uint numberOfUnits,
    bool urgent,
    uint supplierReputation,
    string finalPriority
);

// 读取参与者信息
function readParticipant(
    string memory instanceID,
    string memory participantID
) public view returns (
    string memory participantID_,
    string memory msp,
    bool isMulti,
    uint multiMaximum,
    uint multiMinimum,
    string memory x509
) {
    // 获取当前实例
    ContractInstance storage currentInstance = instances[instanceID];

    // 获取指定参与者
    Participant storage participant = currentInstance.InstanceParticipants[participantID];

    // 返回参与者的各个字段
    participantID_ = participant.ParticipantID;
    msp = participant.MSP;
    isMulti = participant.IsMulti;
    multiMaximum = participant.MultiMaximum;
    multiMinimum = participant.MultiMinimum;
    x509 = participant.X509;
}

// 更新参与者信息
function writeParticipant(
    string memory instanceID,
    string memory participantID,
    string memory msp,
    bool isMulti,
    uint multiMaximum,
    uint multiMinimum,
    string memory x509
) public {
    // 获取当前实例
    ContractInstance storage currentInstance = instances[instanceID];

    // 更新指定参与者的信息
    Participant storage participant = currentInstance.InstanceParticipants[participantID];
    participant.MSP = msp;
    participant.IsMulti = isMulti;
    participant.MultiMaximum = multiMaximum;
    participant.MultiMinimum = multiMinimum;
    participant.X509 = x509;

    // 触发事件通知参与者信息已更新
    emit ParticipantUpdated(instanceID, participantID);
}

// 更新参与者信息的事件
event ParticipantUpdated(string instanceID, string participantID);

// 验证参与者的MSP
function check_msp(string memory instanceID, string memory participantID, string memory expectedMSP) public view returns (bool) {
    // 获取当前实例
    ContractInstance storage currentInstance = instances[instanceID];
    
    // 获取指定参与者
    Participant storage participant = currentInstance.InstanceParticipants[participantID];

    // 比较参与者的MSP与期望的MSP
    if (keccak256(bytes(participant.MSP)) == keccak256(bytes(expectedMSP))) {
        return true; // 如果匹配，返回true
    } else {
        return false; // 如果不匹配，返回false
    }
}

// 验证参与者是否具有特定属性
function check_attribute(
    string memory instanceID,
    string memory participantID,
    string memory attributeKey,
    string memory expectedValue
) public view returns (bool) {
    // 获取当前实例
    ContractInstance storage currentInstance = instances[instanceID];
    
    // 获取指定参与者
    Participant storage participant = currentInstance.InstanceParticipants[participantID];

    // 获取参与者的属性值
    string memory attributeValue = participant.Attributes[attributeKey];

    // 检查属性值是否匹配
    if (keccak256(bytes(attributeValue)) == keccak256(bytes(expectedValue))) {
        return true; // 属性匹配，返回true
    } else {
        return false; // 属性不匹配，返回false
    }
}

// 验证参与者是否存在
function check_participant(string memory instanceID, string memory participantID) public view returns (bool) {
    // 获取当前实例
    ContractInstance storage currentInstance = instances[instanceID];

    // 检查指定参与者是否存在
    if (bytes(currentInstance.InstanceParticipants[participantID].ParticipantID).length != 0) {
        return true; // 如果参与者存在，返回true
    } else {
        return false; // 如果参与者不存在，返回false
    }
}

function hashXML(string memory xmlContent) public pure returns (bytes32) {
    return keccak256(abi.encodePacked(xmlContent));
}

function Event_06sexe6(string memory instanceID) public {
        ContractInstance storage instance = getInstance(instanceID);
        ActionEvent storage actionEvent = readEvent(instanceID, "Event_06sexe6");

        require(actionEvent.EventState == ElementState.ENABLED, "Event is not enabled");

        changeEventState(instanceID, "Event_06sexe6", ElementState.COMPLETED);
        emit Event_06sexe6("Contract has been started successfully");

        changeMsgState(instanceID, "Message_1wswgqu", ElementState.ENABLED);
    }

    // 消息发送成功事件，可根据实际需求调整事件内容
    event Message1wswgquSent(string instanceID, string messageID, string fireflyTranID);

    function Message_1wswgqu_Send(
        string memory instanceID,
        string memory fireflyTranID
    ) public {
        ContractInstance storage currentInstance = instances[instanceID];
        
        Message storage msg = currentInstance.InstanceMessages["Message_1wswgqu"];

        if (!check_participant(instanceID, msg.SendParticipantID)) {
            revert("Participant is not allowed to send the message");
        }

        if (msg.MsgState!= ElementState.ENABLED) {
            revert("Message state is not allowed");
        }

        msg.FireflyTranID = fireflyTranID;
        msg.MsgState = ElementState.COMPLETED;

        emit Message1wswgquSent(instanceID, msg.MessageID, fireflyTranID);

        currentInstance.InstanceMessages["Message_1ajdm9l"].MsgState = ElementState.ENABLED;
    }  
    
event Message1ajdm9lSent(string instanceID, string messageID, string fireflyTranID);

    function Message_1ajdm9l_Send(
        string memory instanceID,
        string memory fireflyTranID
    ) public {
        ContractInstance storage currentInstance = instances[instanceID];
        
        Message storage msg = currentInstance.InstanceMessages["Message_1ajdm9l"];

        if (!check_participant(instanceID, msg.SendParticipantID)) {
            revert("Participant is not allowed to send the message");
        }

        if (msg.MsgState!= ElementState.ENABLED) {
            revert("Message state is not allowed");
        }

        msg.FireflyTranID = fireflyTranID;
        msg.MsgState = ElementState.COMPLETED;

        emit Message1ajdm9lSent(instanceID, msg.MessageID, fireflyTranID);

        currentInstance.InstanceGateways["Gateway_0onpe6x"].GatewayState = ElementState.ENABLED;
    }

event Gateway0onpe6xCompleted(string instanceID);

    function Gateway_0onpe6x(
        string memory instanceID
    ) public {
        ContractInstance storage currentInstance = instances[instanceID];

        Gateway storage gtw = currentInstance.InstanceGateways["Gateway_0onpe6x"];
        
        if (gtw.GatewayState!= ElementState.ENABLED) {
            revert("Gateway state is not allowed");
        }
        
        gtw.GatewayState = ElementState.COMPLETED;
    
        emit Gateway0onpe6xCompleted(instanceID);
        
        currentInstance.InstanceMessages["Message_0cba4t6"].MsgState = ElementState.ENABLED;
        currentInstance.InstanceMessages["Message_0pm90nx"].MsgState = ElementState.ENABLED;
    }

    event Message0cba4t6Sent(string instanceID, string messageID, string fireflyTranID);

    function Message_0cba4t6_Send(
        string memory instanceID,
        string memory fireflyTranID
    ) public {
        // 获取当前实例
        ContractInstance storage currentInstance = instances[instanceID];
        
        // 获取对应消息
        Message storage msg = currentInstance.InstanceMessages["Message_0cba4t6"];
        
        // 检查参与者是否允许发送此消息
        if (!check_participant(instanceID, msg.SendParticipantID)) {
            revert("Participant is not allowed to send the message");
        }
        
        // 检查消息当前状态是否符合发送要求
        if (msg.MsgState!= ElementState.ENABLED) {
            revert("Message state is not allowed");
        }
        
        // 更新消息的FireflyTranID
        msg.FireflyTranID = fireflyTranID;
        // 将消息状态更新为已完成（COMPLETED）
        msg.MsgState = ElementState.COMPLETED;
        
        // 触发消息发送成功事件
        emit Message0cba4t6Sent(instanceID, msg.MessageID, fireflyTranID);
        
        Message storage otherMsg = currentInstance.InstanceMessages["Message_0pm90nx"];
        if (otherMsg.MsgState == ElementState.COMPLETED) {
            currentInstance.InstanceGateways["Gateway_1fbifca"].GatewayState = ElementState.ENABLED;
        }
    }

    event Message0pm90nxSent(string instanceID, string messageID, string fireflyTranID);

    function Message_0pm90nx_Send(
        string memory instanceID,
        string memory fireflyTranID
    ) public {
        // 获取当前实例
        ContractInstance storage currentInstance = instances[instanceID];
        
        // 获取对应消息
        Message storage msg = currentInstance.InstanceMessages["Message_0pm90nx"];
        
        // 检查参与者是否允许发送此消息
        if (!check_participant(instanceID, msg.SendParticipantID)) {
            revert("Participant is not allowed to send the message");
        }
        
        // 检查消息当前状态是否符合发送要求
        if (msg.MsgState!= ElementState.ENABLED) {
            revert("Message state is not allowed");
        }
        
        // 更新消息的FireflyTranID
        msg.FireflyTranID = fireflyTranID;
        // 将消息状态更新为已完成（COMPLETED）
        msg.MsgState = ElementState.COMPLETED;
        
        // 触发消息发送成功事件
        emit Message0pm90nxSent(instanceID, msg.MessageID, fireflyTranID);
        
        Message storage otherMsg = currentInstance.InstanceMessages["Message_0cba4t6"];
        if (otherMsg.MsgState == ElementState.COMPLETED) {
            currentInstance.InstanceGateways["Gateway_1fbifca"].GatewayState = ElementState.ENABLED;
        }
    }

    event Gateway1fbifcaCompleted(string instanceID);

    function Gateway_1fbifca(
        string memory instanceID
    ) public {
        ContractInstance storage currentInstance = instances[instanceID];

        Gateway storage gtw = currentInstance.InstanceGateways["Gateway_1fbifca"];

        if (gtw.GatewayState!= ElementState.ENABLED) {
            revert("Gateway state is not allowed");
        }

        gtw.GatewayState = ElementState.COMPLETED;

        emit Gateway1fbifcaCompleted(instanceID);

        currentInstance.InstanceMessages["Message_0rwz1km"].MsgState = ElementState.ENABLED;
    }

    event Message0rwz1kmSent(string instanceID, string messageID, string fireflyTranID);

    function Message_0rwz1km_Send(
        string memory instanceID,
        string memory fireflyTranID,
        uint numberOfUnits,
        bool urgent
    ) public {
        ContractInstance storage currentInstance = instances[instanceID];

        Message storage msg = currentInstance.InstanceMessages["Message_0rwz1km"];
      
        if (!check_participant(instanceID, msg.SendParticipantID)) {
            revert("Participant is not allowed to send the message");
        }
        
        if (msg.MsgState!= ElementState.ENABLED) {
            revert("Message state is not allowed");
        }
        
        msg.FireflyTranID = fireflyTranID;
        msg.MsgState = ElementState.COMPLETED;
       
        StateMemory storage globalMemory = currentInstance.InstanceStateMemory;
        globalMemory.NumberOfUnits = numberOfUnits;
        globalMemory.Urgent = urgent;

        emit Message0rwz1kmSent(instanceID, msg.MessageID, fireflyTranID);
        
        currentInstance.InstanceMessages["Message_0hpha6h"].MsgState = ElementState.ENABLED;
    }

    event Message0hpha6hSent(string instanceID, string messageID, string fireflyTranID);

    function Message_0hpha6h_Send(
        string memory instanceID,
        string memory fireflyTranID,
        uint supplierReputation
    ) public {
        ContractInstance storage currentInstance = instances[instanceID];
        
        Message storage msg = currentInstance.InstanceMessages["Message_0hpha6h"];
        
        if (!check_participant(instanceID, msg.SendParticipantID)) {
            revert("Participant is not allowed to send the message");
        }
        
        if (msg.MsgState!= ElementState.ENABLED) {
            revert("Message state is not allowed");
        }

        msg.FireflyTranID = fireflyTranID;
        msg.MsgState = ElementState.COMPLETED;

        StateMemory storage globalMemory = currentInstance.InstanceStateMemory;
        globalMemory.SupplierReputation = supplierReputation;
  
        emit Message0hpha6hSent(instanceID, msg.MessageID, fireflyTranID);

        currentInstance.InstanceMessages["Message_1io2g9u"].MsgState = ElementState.ENABLED;
    }

    event Message1io2g9uSent(string instanceID, string messageID, string fireflyTranID);

    function Message_1io2g9u_Send(
        string memory instanceID,
        string memory fireflyTranID
    ) public {
        ContractInstance storage currentInstance = instances[instanceID];

        Message storage msg = currentInstance.InstanceMessages["Message_1io2g9u"];

        if (!check_participant(instanceID, msg.SendParticipantID)) {
            revert("Participant is not allowed to send the message");
        }

        if (msg.MsgState!= ElementState.ENABLED) {
            revert("Message state is not allowed");
        }

        msg.FireflyTranID = fireflyTranID;
        msg.MsgState = ElementState.COMPLETED;

        emit Message1io2g9uSent(instanceID, msg.MessageID, fireflyTranID);
        
       
    }

    event Message0d2xte5Sent(string instanceID, string messageID, string fireflyTranID);

    function Message_0d2xte5_Send(
        string memory instanceID,
        string memory fireflyTranID
    ) public {
        ContractInstance storage currentInstance = instances[instanceID];
        
        Message storage msg = currentInstance.InstanceMessages["Message_0d2xte5"];
        
        if (!check_participant(instanceID, msg.SendParticipantID)) {
            revert("Participant is not allowed to send the message");
        }
        
        if (msg.MsgState!= ElementState.ENABLED) {
            revert("Message state is not allowed");
        }
        
        msg.FireflyTranID = fireflyTranID;
        msg.MsgState = ElementState.COMPLETED;
      
        emit Message0d2xte5Sent(instanceID, msg.MessageID, fireflyTranID);
     
        currentInstance.InstanceMessages["Message_04wmlqe"].MsgState = ElementState.ENABLED;
    }

    event Message04wmlqeSent(string instanceID, string messageID, string fireflyTranID);

    function Message_04wmlqe_Send(
        string memory instanceID,
        string memory fireflyTranID
    ) public {
        ContractInstance storage currentInstance = instances[instanceID];

        Message storage msg = currentInstance.InstanceMessages["Message_04wmlqe"];
        
        if (!check_participant(instanceID, msg.SendParticipantID)) {
            revert("Participant is not allowed to send the message");
        }

        if (msg.MsgState!= ElementState.ENABLED) {
            revert("Message state is not allowed");
        }

        msg.FireflyTranID = fireflyTranID;
        msg.MsgState = ElementState.COMPLETED;

        emit Message04wmlqeSent(instanceID, msg.MessageID, fireflyTranID);

        currentInstance.InstanceMessages["Message_196q1fj"].MsgState = ElementState.ENABLED;
    }

    event Message196q1fjSent(string instanceID, string messageID, string fireflyTranID);

    function Message_196q1fj_Send(
        string memory instanceID,
        string memory fireflyTranID
    ) public {
        ContractInstance storage currentInstance = instances[instanceID];

        Message storage msg = currentInstance.InstanceMessages["Message_196q1fj"];

        if (!check_participant(instanceID, msg.SendParticipantID)) {
            revert("Participant is not allowed to send the message");
        }

        if (msg.MsgState!= ElementState.ENABLED) {
            revert("Message state is not allowed");
        }

        msg.FireflyTranID = fireflyTranID;
        msg.MsgState = ElementState.COMPLETED;
        
        emit Message196q1fjSent(instanceID, msg.MessageID, fireflyTranID);
        
        currentInstance.InstanceGateways["Gateway_1cr0nma"].GatewayState = ElementState.ENABLED;
    }

    event Event13pbqdzCompleted(string instanceID);

    function Event_13pbqdz(
        string memory instanceID
    ) public {
        ContractInstance storage currentInstance = instances[instanceID];
        
        ActionEvent storage actionEvent = currentInstance.InstanceActionEvents["Event_13pbqdz"];
        
        if (actionEvent.EventState!= ElementState.ENABLED) {
            revert("Event state is not allowed");
        }
        
        actionEvent.EventState = ElementState.COMPLETED;

        emit Event13pbqdzCompleted(instanceID);
        
    }

    event Message1oxmq1kSent(string instanceID, string messageID, string fireflyTranID);

    function Message_1oxmq1k_Send(
        string memory instanceID,
        string memory fireflyTranID
    ) public {
        ContractInstance storage currentInstance = instances[instanceID];
        
        Message storage msg = currentInstance.InstanceMessages["Message_1oxmq1k"];
        
        if (!check_participant(instanceID, msg.SendParticipantID)) {
            revert("Participant is not allowed to send the message");
        }

        if (msg.MsgState!= ElementState.ENABLED) {
            revert("Message state is not allowed");
        }
        
        msg.FireflyTranID = fireflyTranID;
        msg.MsgState = ElementState.COMPLETED;
        
        emit Message1oxmq1kSent(instanceID, msg.MessageID, fireflyTranID);
        
        currentInstance.InstanceMessages["Message_04wmlqe"].MsgState = ElementState.ENABLED;
    }

    event Message1dzkcn0Sent(string instanceID, string messageID, string fireflyTranID);

    function Message_1dzkcn0_Send(
        string memory instanceID,
        string memory fireflyTranID
    ) public {
        ContractInstance storage currentInstance = instances[instanceID];
        
        Message storage msg = currentInstance.InstanceMessages["Message_1dzkcn0"];

        if (!check_participant(instanceID, msg.SendParticipantID)) {
            revert("Participant is not allowed to send the message");
        }

        if (msg.MsgState!= ElementState.ENABLED) {
            revert("Message state is not allowed");
        }
        
        msg.FireflyTranID = fireflyTranID;
        msg.MsgState = ElementState.COMPLETED;
        
        emit Message1dzkcn0Sent(instanceID, msg.MessageID, fireflyTranID);
        
        currentInstance.InstanceMessages["Message_04wmlqe"].MsgState = ElementState.ENABLED;
    }

    event Message1dmeexgSent(string instanceID, string messageID, string fireflyTranID);

    function Message_1dmeexg_Send(
        string memory instanceID,
        string memory fireflyTranID
    ) public {
        ContractInstance storage currentInstance = instances[instanceID];
        
        Message storage msg = currentInstance.InstanceMessages["Message_1dmeexg"];
        
        if (!check_participant(instanceID, msg.SendParticipantID)) {
            revert("Participant is not allowed to send the message");
        }

        if (msg.MsgState!= ElementState.ENABLED) {
            revert("Message state is not allowed");
        }
        
        msg.FireflyTranID = fireflyTranID;
        msg.MsgState = ElementState.COMPLETED;
        
        emit Message1dmeexgSent(instanceID, msg.MessageID, fireflyTranID);
        
        currentInstance.InstanceGateways["Gateway_1cr0nma"].GatewayState = ElementState.ENABLED;
    }

    event Gateway1cr0nmaCompleted(string instanceID);

    function Gateway_1cr0nma(
        string memory instanceID
    ) public {
        ContractInstance storage currentInstance = instances[instanceID];
        
        Gateway storage gtw = currentInstance.InstanceGateways["Gateway_1cr0nma"];
        

        if (gtw.GatewayState!= ElementState.ENABLED) {
            revert("Gateway state is not allowed");
        }

        gtw.GatewayState = ElementState.COMPLETED;
        
        emit Gateway1cr0nmaCompleted(instanceID);

        currentInstance.InstanceMessages["Message_04wmlqe"].MsgState = ElementState.ENABLED;
    }

    event Gateway0ep8cuhCompleted(string instanceID);

    function Gateway_0ep8cuh(
        string memory instanceID
    ) public {
        ContractInstance storage currentInstance = instances[instanceID];

        Gateway storage gtw = currentInstance.InstanceGateways["Gateway_0ep8cuh"];
        
        if (gtw.GatewayState!= ElementState.ENABLED) {
            revert("Gateway state is not allowed");
        }

        gtw.GatewayState = ElementState.COMPLETED;

        emit Gateway0ep8cuhCompleted(instanceID);

        currentInstance.InstanceMessages["Message_1dmeexg"].MsgState = ElementState.ENABLED;
    }

}
