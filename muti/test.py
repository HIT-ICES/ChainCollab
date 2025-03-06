import requests
import json
import sys
import base64

import time

ContractName = "BPMN10-830efb"


def handleX509(fabric_msp_id):
    return (
        base64.encodebytes("::".join(fabric_msp_id.split("::")[1:]).encode("utf-8")).decode("utf-8").replace("\n", "")
        + "@"
        + "Mem2.org.comMSP"
    )


def invokeAPI(api, data, key=""):

    param = {}
    if data is not None:
        param["input"] = data
    if key is not None:
        param["key"] = key

    res = requests.post(f"http://127.0.0.1:5001/api/v1/namespaces/default/apis/{ContractName}/invoke/{api}", json=param)
    return res

def queryAPI(api, data, key=""):

    param = {}
    if data is not None:
        param["input"] = data
    if key is not None:
        param["key"] = key

    res = requests.post(f"http://127.0.0.1:5001/api/v1/namespaces/default/apis/{ContractName}/query/{api}", json=param)
    return res


def get_snapshot(instance_id):
    res = queryAPI("GetCurrentState", {"instanceID": str(instance_id)})
    print(res.json())


participant_map = {
    "Participant_0w6qkdf": {
        "key": "Mem2.org.comMSP::x509::CN=User1,OU=client::CN=ca.Mem2.org.com,OU=Fabric,O=Mem2.org.com,ST=North Carolina,C=US"
    },
    "Participant_19mgbdn": {
        "key": "Mem2.org.comMSP::x509::CN=User2,OU=client::CN=ca.Mem2.org.com,OU=Fabric,O=Mem2.org.com,ST=North Carolina,C=US"
    },
    "Participant_09cjol2": {
        "key": "Mem2.org.comMSP::x509::CN=User3,OU=client::CN=ca.Mem2.org.com,OU=Fabric,O=Mem2.org.com,ST=North Carolina,C=US"
    },
    "Participant_0sa2v7d": {
        "key": "Mem2.org.comMSP::x509::CN=User4,OU=client::CN=ca.Mem2.org.com,OU=Fabric,O=Mem2.org.com,ST=North Carolina,C=US"
    },
    "Participant_19j1e3o": {
        "key": "Mem2.org.comMSP::x509::CN=User5,OU=client::CN=ca.Mem2.org.com,OU=Fabric,O=Mem2.org.com,ST=North Carolina,C=US"
    },
}


def CreateInstance():
    param = {
        "Participant_0w6qkdf": {
            "ParticipantID": "X",  # no use
            "IsMulti": False,
            "MultiMaximum": 0,  # no use
            "MultiMinimum": 0,  # no use
            "MSP": "Mem2.org.comMSP",
            "Attributes": {},
            "x509": handleX509(participant_map["Participant_0w6qkdf"]["key"]),
        },
        "Participant_19mgbdn": {
            "ParticipantID": "X",  # no use
            "IsMulti": False,
            "MultiMaximum": 0,  # no use
            "MultiMinimum": 0,  # no use
            "MSP": "Mem2.org.comMSP",
            "Attributes": {},
            "x509": handleX509(participant_map["Participant_19mgbdn"]["key"]),
        },
        "Participant_09cjol2": {
            "ParticipantID": "X",  # no use
            "IsMulti": False,
            "MultiMaximum": 0,  # no use
            "MultiMinimum": 0,  # no use
            "MSP": "Mem2.org.comMSP",
            "Attributes": {},
            "x509": handleX509(participant_map["Participant_09cjol2"]["key"]),
        },
        "Participant_0sa2v7d": {
            "ParticipantID": "X",  # no use
            "IsMulti": False,
            "MultiMaximum": 0,  # no use
            "MultiMinimum": 0,  # no use
            "MSP": "Mem2.org.comMSP",
            "Attributes": {},
            "x509": handleX509(participant_map["Participant_0sa2v7d"]["key"]),
        },
        "Participant_19j1e3o": {
            "ParticipantID": "X",  # no use
            "IsMulti": True,
            "MultiMaximum": 0,  # no use
            "MultiMinimum": 0,  # no use
            "MSP": "Mem2.org.comMSP",
            "Attributes": {},
            "x509": "",
        },
        "stateMachineDescription": """{"context": {"finalPriority": null, "Participant_19j1e3o_locked": false, "Participant_19j1e3o_machine_0": false, "Participant_19j1e3o_machine_1": false, "Message_0i5t589_loop": 1, "Message_0i5t589_loopMax": 2, "Message_0d2xte5_loop": 1, "Message_0d2xte5_loopMax": 3}, "id": "NewTest_paper2", "initial": "Event_06sexe6", "states": {"Event_06sexe6": {"always": {"target": "Message_1wswgqu", "actions": []}}, "Event_13pbqdz": {"type": "final"}, "Message_1wswgqu": {"initial": "enable", "states": {"enable": {"on": {"Send_Message_1wswgqu": [{"target": "wait for confirm", "actions": []}]}}, "wait for confirm": {"on": {"Confirm_Message_1wswgqu": [{"target": "done", "actions": []}]}}, "done": {"type": "final"}}, "onDone": {"target": "Gateway_0onpe6x_TO_Gateway_1fbifca", "actions": []}}, "Message_0rwz1km": {"initial": "pending", "states": {"pending": {"always": [{"target": "Message_0rwz1km_firstTime", "guard": "Participant_19j1e3o_isNotLocked", "actions": [{"type": "lock_Participant_19j1e3o"}]}, {"target": "Message_0rwz1km", "guard": "Participant_19j1e3o_isLocked", "actions": []}]}, "done": {"type": "final"}, "Message_0rwz1km": {"initial": "machine_0", "states": {"machine_0": {"initial": "disable", "states": {"disable": {"always": [{"target": "enable", "guard": "active_Participant_19j1e3o_machine_0", "actions": []}, {"target": "locked_done", "guard": "inactive_Participant_19j1e3o_machine_0", "actions": []}]}, "enable": {"on": {"Send_Message_0rwz1km_0": [{"target": "wait for confirm", "actions": []}]}}, "locked_done": {"type": "final"}, "wait for confirm": {"on": {"Confirm_Message_0rwz1km_0": [{"target": "done", "actions": []}]}}, "done": {"type": "final"}}}, "machine_1": {"initial": "disable", "states": {"disable": {"always": [{"target": "enable", "guard": "active_Participant_19j1e3o_machine_1", "actions": []}, {"target": "locked_done", "guard": "inactive_Participant_19j1e3o_machine_1", "actions": []}]}, "enable": {"on": {"Send_Message_0rwz1km_1": [{"target": "wait for confirm", "actions": []}]}}, "locked_done": {"type": "final"}, "wait for confirm": {"on": {"Confirm_Message_0rwz1km_1": [{"target": "done", "actions": []}]}}, "done": {"type": "final"}}}}, "onDone": {"target": "done", "actions": []}, "type": "parallel"}, "Message_0rwz1km_firstTime": {"initial": "unlocked", "states": {"unlocked": {"states": {"machine_0": {"initial": "enable", "states": {"enable": {"on": {"Send_Message_0rwz1km_0": [{"target": "wait for confirm", "actions": []}]}}, "wait for confirm": {"on": {"Confirm_Message_0rwz1km_0": [{"target": "done", "actions": []}]}}, "done": {"entry": {"type": "activate_Participant_19j1e3o_machine_0"}}}}, "machine_1": {"initial": "enable", "states": {"enable": {"on": {"Send_Message_0rwz1km_1": [{"target": "wait for confirm", "actions": []}]}}, "wait for confirm": {"on": {"Confirm_Message_0rwz1km_1": [{"target": "done", "actions": []}]}}, "done": {"entry": {"type": "activate_Participant_19j1e3o_machine_1"}}}}}, "on": {"advance_Message_0rwz1km": [{"target": "locked", "actions": []}]}, "type": "parallel"}, "locked": {"type": "final"}}, "onDone": {"target": "done", "actions": []}}}, "onDone": {"target": "Message_0i5t589", "actions": []}}, "Message_0i5t589": {"initial": "Message_0i5t589", "states": {"Message_0i5t589": {"initial": "pending", "states": {"pending": {"always": [{"target": "Message_0i5t589_firstTime", "guard": "Participant_19j1e3o_isNotLocked", "actions": [{"type": "lock_Participant_19j1e3o"}]}, {"target": "Message_0i5t589", "guard": "Participant_19j1e3o_isLocked", "actions": []}]}, "done": {"type": "final"}, "Message_0i5t589": {"initial": "machine_0", "states": {"machine_0": {"initial": "disable", "states": {"disable": {"always": [{"target": "enable", "guard": "active_Participant_19j1e3o_machine_0", "actions": []}, {"target": "locked_done", "guard": "inactive_Participant_19j1e3o_machine_0", "actions": []}]}, "enable": {"on": {"Send_Message_0i5t589_0": [{"target": "wait for confirm", "actions": []}]}}, "locked_done": {"type": "final"}, "wait for confirm": {"on": {"Confirm_Message_0i5t589_0": [{"target": "done", "actions": []}]}}, "done": {"type": "final"}}}, "machine_1": {"initial": "disable", "states": {"disable": {"always": [{"target": "enable", "guard": "active_Participant_19j1e3o_machine_1", "actions": []}, {"target": "locked_done", "guard": "inactive_Participant_19j1e3o_machine_1", "actions": []}]}, "enable": {"on": {"Send_Message_0i5t589_1": [{"target": "wait for confirm", "actions": []}]}}, "locked_done": {"type": "final"}, "wait for confirm": {"on": {"Confirm_Message_0i5t589_1": [{"target": "done", "actions": []}]}}, "done": {"type": "final"}}}}, "onDone": {"target": "done", "actions": []}, "type": "parallel"}, "Message_0i5t589_firstTime": {"initial": "unlocked", "states": {"unlocked": {"states": {"machine_0": {"initial": "enable", "states": {"enable": {"on": {"Send_Message_0i5t589_0": [{"target": "wait for confirm", "actions": []}]}}, "wait for confirm": {"on": {"Confirm_Message_0i5t589_0": [{"target": "done", "actions": []}]}}, "done": {"entry": {"type": "activate_Participant_19j1e3o_machine_0"}}}}, "machine_1": {"initial": "enable", "states": {"enable": {"on": {"Send_Message_0i5t589_1": [{"target": "wait for confirm", "actions": []}]}}, "wait for confirm": {"on": {"Confirm_Message_0i5t589_1": [{"target": "done", "actions": []}]}}, "done": {"entry": {"type": "activate_Participant_19j1e3o_machine_1"}}}}}, "on": {"advance_Message_0i5t589": [{"target": "locked", "actions": []}]}, "type": "parallel"}, "locked": {"type": "final"}}, "onDone": {"target": "done", "actions": []}}}, "onDone": []}}, "onDone": [{"target": "Message_0i5t589", "guard": "Message_0i5t589_NotLoopMax", "actions": [{"type": "Message_0i5t589_LoopAdd"}]}, {"target": "Message_0oi7nug", "guard": "Message_0i5t589_LoopConditionMeet", "actions": []}, {"target": "Message_0oi7nug", "guard": "Message_0i5t589_LoopMax", "actions": []}], "type": "parallel"}, "Message_0oi7nug": {"initial": "Message_0oi7nug_0", "states": {"Message_0oi7nug_0": {"initial": "enable", "states": {"enable": {"on": {"Send_Message_0oi7nug_0": [{"target": "wait for confirm", "actions": []}]}}, "wait for confirm": {"on": {"Confirm_Message_0oi7nug_0": [{"target": "done", "actions": []}]}}, "done": {"type": "final"}}}, "Message_0oi7nug_1": {"initial": "enable", "states": {"enable": {"on": {"Send_Message_0oi7nug_1": [{"target": "wait for confirm", "actions": []}]}}, "wait for confirm": {"on": {"Confirm_Message_0oi7nug_1": [{"target": "done", "actions": []}]}}, "done": {"type": "final"}}}, "Message_0oi7nug_2": {"initial": "enable", "states": {"enable": {"on": {"Send_Message_0oi7nug_2": [{"target": "wait for confirm", "actions": []}]}}, "wait for confirm": {"on": {"Confirm_Message_0oi7nug_2": [{"target": "done", "actions": []}]}}, "done": {"type": "final"}}}}, "type": "parallel", "onDone": {"target": "Message_1io2g9u", "actions": []}}, "Message_1io2g9u": {"initial": "enable", "states": {"enable": {"on": {"Send_Message_1io2g9u": [{"target": "wait for confirm", "actions": []}]}}, "wait for confirm": {"on": {"Confirm_Message_1io2g9u": [{"target": "done", "actions": [{"type": "set_MessageGlobal_finalPriority"}]}]}}, "done": {"type": "final"}}, "onDone": {"target": "Gateway_0ep8cuh", "actions": []}}, "Gateway_0ep8cuh": {"always": [{"target": "Message_1oxmq1k", "guard": "Gateway_0ep8cuh__Message_1oxmq1k", "actions": []}, {"target": "Message_0d2xte5", "guard": "Gateway_0ep8cuh__Message_0d2xte5", "actions": []}]}, "Message_1oxmq1k": {"initial": "pending", "states": {"pending": {"always": [{"target": "Message_1oxmq1k_firstTime", "guard": "Participant_19j1e3o_isNotLocked", "actions": [{"type": "lock_Participant_19j1e3o"}]}, {"target": "Message_1oxmq1k", "guard": "Participant_19j1e3o_isLocked", "actions": []}]}, "done": {"type": "final"}, "Message_1oxmq1k": {"initial": "machine_0", "states": {"machine_0": {"initial": "disable", "states": {"disable": {"always": [{"target": "enable", "guard": "active_Participant_19j1e3o_machine_0", "actions": []}, {"target": "locked_done", "guard": "inactive_Participant_19j1e3o_machine_0", "actions": []}]}, "enable": {"on": {"Send_Message_1oxmq1k_0": [{"target": "wait for confirm", "actions": []}]}}, "locked_done": {"type": "final"}, "wait for confirm": {"on": {"Confirm_Message_1oxmq1k_0": [{"target": "done", "actions": []}]}}, "done": {"type": "final"}}}, "machine_1": {"initial": "disable", "states": {"disable": {"always": [{"target": "enable", "guard": "active_Participant_19j1e3o_machine_1", "actions": []}, {"target": "locked_done", "guard": "inactive_Participant_19j1e3o_machine_1", "actions": []}]}, "enable": {"on": {"Send_Message_1oxmq1k_1": [{"target": "wait for confirm", "actions": []}]}}, "locked_done": {"type": "final"}, "wait for confirm": {"on": {"Confirm_Message_1oxmq1k_1": [{"target": "done", "actions": []}]}}, "done": {"type": "final"}}}}, "onDone": {"target": "done", "actions": []}, "type": "parallel"}, "Message_1oxmq1k_firstTime": {"initial": "unlocked", "states": {"unlocked": {"states": {"machine_0": {"initial": "enable", "states": {"enable": {"on": {"Send_Message_1oxmq1k_0": [{"target": "wait for confirm", "actions": []}]}}, "wait for confirm": {"on": {"Confirm_Message_1oxmq1k_0": [{"target": "done", "actions": []}]}}, "done": {"entry": {"type": "activate_Participant_19j1e3o_machine_0"}}}}, "machine_1": {"initial": "enable", "states": {"enable": {"on": {"Send_Message_1oxmq1k_1": [{"target": "wait for confirm", "actions": []}]}}, "wait for confirm": {"on": {"Confirm_Message_1oxmq1k_1": [{"target": "done", "actions": []}]}}, "done": {"entry": {"type": "activate_Participant_19j1e3o_machine_1"}}}}}, "on": {"advance_Message_1oxmq1k": [{"target": "locked", "actions": []}]}, "type": "parallel"}, "locked": {"type": "final"}}, "onDone": {"target": "done", "actions": []}}}, "onDone": {"target": "Gateway_1cr0nma", "actions": []}}, "Gateway_1cr0nma": {"always": [{"target": "Event_13pbqdz", "guard": "Gateway_1cr0nma__Event_13pbqdz", "actions": []}]}, "Message_0d2xte5": {"initial": "Message_0d2xte5_", "states": {"Message_0d2xte5": {"initial": "pending", "states": {"pending": {"always": [{"target": "Message_0d2xte5_firstTime", "guard": "Participant_19j1e3o_isNotLocked", "actions": [{"type": "lock_Participant_19j1e3o"}]}, {"target": "Message_0d2xte5", "guard": "Participant_19j1e3o_isLocked", "actions": []}]}, "done": {"type": "final"}, "Message_0d2xte5": {"initial": "machine_0", "states": {"machine_0": {"initial": "disable", "states": {"disable": {"always": [{"target": "enable", "guard": "active_Participant_19j1e3o_machine_0", "actions": []}, {"target": "locked_done", "guard": "inactive_Participant_19j1e3o_machine_0", "actions": []}]}, "enable": {"on": {"Send_Message_0d2xte5_0": [{"target": "wait for confirm", "actions": []}]}}, "locked_done": {"type": "final"}, "wait for confirm": {"on": {"Confirm_Message_0d2xte5_0": [{"target": "done", "actions": []}]}}, "done": {"type": "final"}}}, "machine_1": {"initial": "disable", "states": {"disable": {"always": [{"target": "enable", "guard": "active_Participant_19j1e3o_machine_1", "actions": []}, {"target": "locked_done", "guard": "inactive_Participant_19j1e3o_machine_1", "actions": []}]}, "enable": {"on": {"Send_Message_0d2xte5_1": [{"target": "wait for confirm", "actions": []}]}}, "locked_done": {"type": "final"}, "wait for confirm": {"on": {"Confirm_Message_0d2xte5_1": [{"target": "done", "actions": []}]}}, "done": {"type": "final"}}}}, "onDone": {"target": "done", "actions": []}, "type": "parallel"}, "Message_0d2xte5_firstTime": {"initial": "unlocked", "states": {"unlocked": {"states": {"machine_0": {"initial": "enable", "states": {"enable": {"on": {"Send_Message_0d2xte5_0": [{"target": "wait for confirm", "actions": []}]}}, "wait for confirm": {"on": {"Confirm_Message_0d2xte5_0": [{"target": "done", "actions": []}]}}, "done": {"entry": {"type": "activate_Participant_19j1e3o_machine_0"}}}}, "machine_1": {"initial": "enable", "states": {"enable": {"on": {"Send_Message_0d2xte5_1": [{"target": "wait for confirm", "actions": []}]}}, "wait for confirm": {"on": {"Confirm_Message_0d2xte5_1": [{"target": "done", "actions": []}]}}, "done": {"entry": {"type": "activate_Participant_19j1e3o_machine_1"}}}}}, "on": {"advance_Message_0d2xte5": [{"target": "locked", "actions": []}]}, "type": "parallel"}, "locked": {"type": "final"}}, "onDone": {"target": "done", "actions": []}}}, "onDone": []}}, "onDone": [{"target": "Message_0d2xte5", "guard": "Message_0d2xte5_NotLoopMax", "actions": [{"type": "Message_0d2xte5_LoopAdd"}]}, {"target": "Gateway_1cr0nma", "guard": "Message_0d2xte5_LoopMax", "actions": []}], "type": "parallel"}, "Gateway_0onpe6x_TO_Gateway_1fbifca": {"initial": "", "states": {"Gateway_0onpe6x to Gateway_1fbifca path 0": {"initial": "Message_0cba4t6", "states": {"done": {"type": "final"}, "Message_0cba4t6": {"initial": "enable", "states": {"enable": {"on": {"Send_Message_0cba4t6": [{"target": "wait for confirm", "actions": []}]}}, "wait for confirm": {"on": {"Confirm_Message_0cba4t6": [{"target": "done", "actions": []}]}}, "done": {"type": "final"}}, "onDone": {"target": "Message_1ip9ryp", "actions": []}}, "Message_1ip9ryp": {"initial": "enable", "states": {"enable": {"on": {"Send_Message_1ip9ryp": [{"target": "wait for confirm", "actions": []}]}}, "wait for confirm": {"on": {"Confirm_Message_1ip9ryp": [{"target": "done", "actions": []}]}}, "done": {"type": "final"}}, "onDone": {"target": "done", "actions": []}}}, "onDone": []}, "Gateway_0onpe6x to Gateway_1fbifca path 1": {"initial": "Message_0pm90nx", "states": {"done": {"type": "final"}, "Message_0pm90nx": {"initial": "enable", "states": {"enable": {"on": {"Send_Message_0pm90nx": [{"target": "wait for confirm", "actions": []}]}}, "wait for confirm": {"on": {"Confirm_Message_0pm90nx": [{"target": "done", "actions": []}]}}, "done": {"type": "final"}}, "onDone": {"target": "done", "actions": []}}}, "onDone": []}}, "onDone": {"target": "Message_0rwz1km", "actions": []}, "type": "parallel"}}}""",
        "additionalContent": """{"actions": {"set_MessageGlobal_finalPriority": "assign({finalPriority: ({context, event}) => event.values.finalPriority})", "lock_Participant_19j1e3o": "assign({Participant_19j1e3o_locked:true})", "activate_Participant_19j1e3o_machine_0": "assign({Participant_19j1e3o_machine_0:true})", "activate_Participant_19j1e3o_machine_1": "assign({Participant_19j1e3o_machine_1:true})", "Message_0i5t589_LoopAdd": "assign({Message_0i5t589_loop: ({context}) => context.Message_0i5t589_loop + 1})", "Message_0d2xte5_LoopAdd": "assign({Message_0d2xte5_loop: ({context}) => context.Message_0d2xte5_loop + 1})"}, "services": {}, "guards": {"Participant_19j1e3o_isLocked": "({context, event},params) => {return context.Participant_19j1e3o_locked;}", "Participant_19j1e3o_isNotLocked": "({context, event},params) => {return !context.Participant_19j1e3o_locked;}", "active_Participant_19j1e3o_machine_0": "({context, event},params) => {return context.Participant_19j1e3o_machine_0;}", "inactive_Participant_19j1e3o_machine_0": "({context, event},params) => {return !context.Participant_19j1e3o_machine_0;}", "active_Participant_19j1e3o_machine_1": "({context, event},params) => {return context.Participant_19j1e3o_machine_1;}", "inactive_Participant_19j1e3o_machine_1": "({context, event},params) => {return !context.Participant_19j1e3o_machine_1;}", "Message_0i5t589_NotLoopMax": "({context, event},params) => {return context.Message_0i5t589_loop !== context.Message_0i5t589_loopMax;}", "Message_0i5t589_LoopMax": "({context, event},params) => {return context.Message_0i5t589_loop === context.Message_0i5t589_loopMax;}", "Message_0i5t589_LoopConditionMeet": "({context, event},params) => {return context.true;}", "Gateway_0ep8cuh__Message_1oxmq1k": "({context, event},params) => {return context.finalPriority=='Low';}", "Gateway_0ep8cuh__Message_0d2xte5": "({context, event},params) => {return context.finalPriority=='VeryLow';}", "Gateway_1cr0nma__Event_13pbqdz": "({context, event},params) => {return true;}", "Message_0d2xte5_NotLoopMax": "({context, event},params) => {return context.Message_0d2xte5_loop !== context.Message_0d2xte5_loopMax;}", "Message_0d2xte5_LoopMax": "({context, event},params) => {return context.Message_0d2xte5_loop === context.Message_0d2xte5_loopMax;}"}, "delays": {}}""",
    }

    data = {"initParametersBytes": json.dumps(param)}
    res = invokeAPI(api="CreateInstance", data=data)
    print(res.text)


# Advance The Progress of BPMN


def InvokeStep(instance_id, step):

    command_list = [
        # 0
        {
            "func": "Message_1wswgqu_Send",
            "sender": "Participant_0w6qkdf",
            "value": {},
            "type": "Send",
        },
        {
            "func": "Message_1wswgqu_Complete",
            "sender": "Participant_19mgbdn",
            "type": "Complete",
        },
        {
            "func": "Gateway_0onpe6x",
            "sender": "Participant_09cjol2",
            "type": "Gateway",
        },
        {
            "func": "Message_0cba4t6_Send",
            "sender": "Participant_09cjol2",
            "type": "Send"
        },
        {
            "func": "Message_0cba4t6_Complete",
            "sender": "Participant_0sa2v7d",
            "type": "Complete"
        },
        # 5
        {
            "func": "Message_0pm90nx_Send",
            "sender": "Participant_09cjol2",
            "type": "Send"
        },
        {
            "func": "Message_0pm90nx_Complete",
            "sender": "Participant_19mgbdn",
            "type": "Complete"
        },
        {
            "func": "Message_1ip9ryp_Send",
            "sender": "Participant_0w6qkdf",
            "type": "Send"
        },
        {
            "func": "Message_1ip9ryp_Complete",
            "sender": "Participant_19mgbdn",
            "type": "Complete"
        },
        {
            "func": "Gateway_1fbifca",
            "sender": "Participant_19mgbdn",
            "type": "Gateway"
        },
        # 10
        {
            "func": "Message_0rwz1km_Send",
            "sender": "Participant_19j1e3o",
            "type": "Send",
        },
        {
            "func": "Message_0rwz1km_Complete",
            "sender": "Participant_0sa2v7d",
            "confirmTargetX509": handleX509(participant_map["Participant_19j1e3o"]["key"]), 
            "type": "Complete"
        },
        {
            "func": "Message_0rwz1km_Advance",
            "sender": "Participant_0sa2v7d",
            "type": "Advance"
        },
        {
            "func": "Message_0i5t589_Send",
            "sender": "Participant_0sa2v7d",
            "type": "Send"
        },
        {
            "func": "Message_0i5t589_Complete",
            "sender": "Participant_19j1e3o",
            "type": "Complete",
        },
    ]

    command = command_list[int(step)]
    print("Command: ", command)

    if command["type"] == "Send":
        data = {"fireFlyTran": "default", "instanceID": str(instance_id), "targetTaskID": 0}
    if command["type"] == "Complete":
        data = {"instanceID": str(instance_id), "targetTaskID": 0 if  "targetTaskID" not in command else command["targetTaskID"], "confirmTargetX509": "XXXX" if "confirmTargetX509" not in command else command["confirmTargetX509"]}
    if command["type"] == "Gateway":
        data = {"instanceID": str(instance_id)}
    if command["type"] == "Advance":
        data = {"instanceID": str(instance_id), "targetTaskID": 0 if "targetTaskID" not in command else command["targetTaskID"]}

    participant = command["sender"]
    key = participant_map[participant]["key"]

    # key = handleX509(participant_map[participant]["key"]) + "@" + "Mem2.org.comMSP"

    res = invokeAPI(api=command["func"], data=data, key=key)
    print(res.text)
    time.sleep(3)
    get_snapshot(instance_id)



def recongnize_all_element_mapping(machine_description, snapshot):

    # Gateway
    # [
    #     {
    #         name: Gateway_xxxx
    #         status: disable|enable| waitforconfirm| done
    #     },
    #     {
    #     }
    # ]
    # # Message
    # [
    #     status: 
    # ]
    # [
    #
    # ]
    pass


if "__main__" == __name__:
    _input = sys.argv[1]
    if _input == "create":
        CreateInstance()
    if _input == "invoke":
        instance_id = sys.argv[2]
        step = sys.argv[3]
        InvokeStep(instance_id, step)
    if _input == "snapshot":
        instance_id = sys.argv[2]
        get_snapshot(instance_id)
    if _input == "invokes":
        instance_id = sys.argv[2]
        if_auto = sys.argv[3]
        if if_auto == "auto":
            for i in range(0, 11):
                InvokeStep(instance_id, i)
        command = ""
        while True:
            command = input("Enter Command: ")
            if command == "exit":
                break
            InvokeStep(instance_id, command)
