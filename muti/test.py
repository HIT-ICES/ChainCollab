import requests
import json
import sys
import base64
import os
import docker
import time
import re
from datetime import datetime


ContractName = "80-d37d45"


param_file_dir = "/home/logres/system/Experiment/BPMN"


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
    # print(res.json())
    return res.json()


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


def CreateInstance(id):

    # read param content form param_file_dir
    with open(os.path.join(param_file_dir,f"{id}-0.json"), "rb") as f:
        raw_string = f.read().decode("utf-8")
        stateMachineDescription = str(raw_string)

    with open(os.path.join(param_file_dir,f"{id}-1.json"), "rb") as f:
        raw_string = f.read().decode("utf-8")
        additionalContent = str(raw_string)



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
        "stateMachineDescription": stateMachineDescription,
        "additionalContent": additionalContent,
    }

    data = {"initParametersBytes": json.dumps(param)}
    res = invokeAPI(api="CreateInstance", data=data)
    print(res.text)


# Advance The Progress of BPMN


def InvokeStep(instance_id, step):

    # command_list = [
    #     # 0
    #     {
    #         "func": "Message_1wswgqu_Send",
    #         "sender": "Participant_0w6qkdf",
    #         "value": {},
    #         "type": "Send",
    #     },
    #     {
    #         "func": "Message_1wswgqu_Complete",
    #         "sender": "Participant_19mgbdn",
    #         "type": "Complete",
    #     },
    #     {
    #         "func": "Gateway_0onpe6x",
    #         "sender": "Participant_09cjol2",
    #         "type": "Gateway",
    #     },
    #     {
    #         "func": "Message_0cba4t6_Send",
    #         "sender": "Participant_09cjol2",
    #         "type": "Send"
    #     },
    #     {
    #         "func": "Message_0cba4t6_Complete",
    #         "sender": "Participant_0sa2v7d",
    #         "type": "Complete"
    #     },
    #     # 5
    #     {
    #         "func": "Message_0pm90nx_Send",
    #         "sender": "Participant_09cjol2",
    #         "type": "Send"
    #     },
    #     {
    #         "func": "Message_0pm90nx_Complete",
    #         "sender": "Participant_19mgbdn",
    #         "type": "Complete"
    #     },
    #     {
    #         "func": "Message_1ip9ryp_Send",
    #         "sender": "Participant_0w6qkdf",
    #         "type": "Send"
    #     },
    #     {
    #         "func": "Message_1ip9ryp_Complete",
    #         "sender": "Participant_19mgbdn",
    #         "type": "Complete"
    #     },
    #     {
    #         "func": "Gateway_1fbifca",
    #         "sender": "Participant_19mgbdn",
    #         "type": "Gateway"
    #     },
    #     # 10
    #     {
    #         "func": "Message_0rwz1km_Send",
    #         "sender": "Participant_19j1e3o",
    #         "type": "Send",
    #     },
    #     {
    #         "func": "Message_0rwz1km_Complete",
    #         "sender": "Participant_0sa2v7d",
    #         "confirmTargetX509": handleX509(participant_map["Participant_19j1e3o"]["key"]), 
    #         "type": "Complete"
    #     },
    #     {
    #         "func": "Message_0rwz1km_Advance",
    #         "sender": "Participant_0sa2v7d",
    #         "type": "Advance"
    #     },
    #     {
    #         "func": "Message_0i5t589_Send",
    #         "sender": "Participant_0sa2v7d",
    #         "type": "Send"
    #     },
    #     {
    #         "func": "Message_0i5t589_Complete",
    #         "sender": "Participant_19j1e3o",
    #         "type": "Complete",
    #     },
    # ]

    command_list = [
        {
            "func": "Message_1wswgqu_Advance",
            "sender": "Participant_19mgbdn",
            "type": "Advance"
        }
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
    # time.sleep(3)
    # get_snapshot(instance_id)
    return res.json()



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

def calculate_time_difference_in_ms(time1_str, time2_str):
    def parse_time_with_nanoseconds(time_str):
        time_str = time_str.rstrip("Z")
        if "." in time_str:
            seconds_str, nanoseconds_str = time_str.split(".")
            microseconds_str = nanoseconds_str[:6]
            time_str = f"{seconds_str}.{microseconds_str}"
        else:
            time_str = time_str + ".000000"
        return datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S.%f")

    time1 = parse_time_with_nanoseconds(time1_str)
    time2 = parse_time_with_nanoseconds(time2_str)

    time_difference = time2 - time1
    time_difference_ms = time_difference.total_seconds() * 1000
    return f"{time_difference_ms:.6f}"

def query_trans_handle_time(op_id):
    res = requests.get(f"http://127.0.0.1:5001/api/v1/operations/{op_id}?fetchstatus=true`)")

    print(res.json())

    op_time = res.json()['created']
    tx_id = res.json()["tx"]


    res = requests.get(f"http://127.0.0.1:5001/api/v1/events?fetchreferences=true&fetchreference=true&tx={tx_id}")

    print(res.json())

    succeed_time = res.json()[0]["created"]
    
    return calculate_time_difference_in_ms(op_time, succeed_time)


def get_golang_invoke_time_cost_from_container(container_id):
    docker_url = "unix://var/run/docker.sock"
    client = docker.DockerClient(base_url=docker_url)
    container = client.containers.get(container_id)
    
    try:
        logs = container.logs(follow=False).decode("utf-8")
    except Exception as e:
        print(e)
        return -1

    # match logs content with "Time Cost is %s 69.000492ms"
    pattern = r"Time Cost is %s (\d+\.\d+)ms"
    time_values  = re.findall(pattern, logs)
    print(time_values)
    return time_values[-1] if len(time_values) > 0 else -1


def test(instance_start_id,test_target_id,test_batch_times, chaincode_container_id):
    # create instance with instance_start_id, test_target_id
    instance_list = range(int(instance_start_id), int(instance_start_id) + int(test_batch_times))
    for i in range(0, test_batch_times):
        CreateInstance(test_target_id)
        time.sleep(3)

    results = []

    for instance_id in instance_list:
        res = InvokeStep(instance_id, 0)
        time.sleep(6)
        id = res["id"]
        trans_time_cost = query_trans_handle_time(id)

        invoke_time_cost = get_golang_invoke_time_cost_from_container(chaincode_container_id)

        results.append({
            "test_target": test_target_id,
            "gocost": invoke_time_cost,
            "trancost": trans_time_cost
        })
        
    
    with open("./result.json", "r", encoding="utf-8") as f:
        content = json.load(f)
    
    new_content = content + results

    with open("./result.json", "w", encoding="utf-8") as f:
        json.dump(new_content, f)
    print("Finished")


if "__main__" == __name__:
    _input = sys.argv[1]
    if _input == "create":
        id = sys.argv[2]
        CreateInstance(id)
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
    if _input == "test":

        with open("./instance_id.json", "r") as f:
            instance_ids = json.load(f)

        instance_id_start = instance_ids[ContractName]
        test_batch_times = int(sys.argv[2])
        chaincode_container_id = sys.argv[3]
        test_target_id = sys.argv[4]

        test(instance_id_start, test_target_id, test_batch_times, chaincode_container_id)
        
        instance_id = instance_id_start + test_batch_times
        instance_ids[ContractName] = instance_id
        with open("./instance_id.json", "w") as f:
            json.dump(instance_ids, f)

