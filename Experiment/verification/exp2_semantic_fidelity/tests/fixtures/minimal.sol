pragma solidity ^0.8.19;

contract Minimal {
    enum MessageKey { Message_A, Message_B }
    enum GatewayKey { Decision }
    enum EventKey { StartEvent_1, EndEvent_1 }
    enum BusinessRuleKey { RuleA }
    enum ElementState { DISABLED, ENABLED, WAITING_FOR_CONFIRMATION, COMPLETED }

    struct StateMemory {
        bool Approved;
        int Counter;
    }

    struct Message { ElementState state; }
    struct Gateway { ElementState state; }
    struct ActionEvent { ElementState state; }
    struct BusinessRule { ElementState state; }
    struct Instance {
        StateMemory stateMemory;
        mapping(MessageKey => Message) messages;
        mapping(GatewayKey => Gateway) gateways;
        mapping(EventKey => ActionEvent) events;
        mapping(BusinessRuleKey => BusinessRule) businessRules;
    }

    mapping(uint256 => Instance) private instances;

    function Message_A_Send(uint256 instanceId) external {
        Instance storage inst = instances[instanceId];
        inst.messages[MessageKey.Message_A].state = ElementState.COMPLETED;
        inst.gateways[GatewayKey.Decision].state = ElementState.ENABLED;
    }

    function Decision(uint256 instanceId) external {
        Instance storage inst = instances[instanceId];
        if (inst.stateMemory.Approved == true) {
            inst.messages[MessageKey.Message_B].state = ElementState.ENABLED;
        } else {
            inst.events[EventKey.EndEvent_1].state = ElementState.ENABLED;
        }
    }
}

