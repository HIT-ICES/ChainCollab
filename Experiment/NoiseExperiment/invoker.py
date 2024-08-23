from loader import STEP, CHECK_CONDITION, BoolWithMessage, ElementTypes
import requests
import json
import websocket
import time
import re


def subsribe_and_get_result(subscription_name: str):
    ws_uri = "ws://localhost:5000/ws"
    ws = websocket.WebSocket()
    ws.connect(ws_uri)
    message_to_send = {
        "type": "start",
        "name": subscription_name,
        "namespace": "default",
        "autoack": True,
    }
    ws.send(json.dumps(message_to_send))

    message = ws.recv()
    ws.close()
    return json.loads(message)


def from_num_to_state(num: int) -> str:
    match num:
        case 0:
            return "DISABLED"
        case 1:
            return "ENABLED"
        case 2:
            return "WAITINGFORCONFIRMATION"
        case 3:
            return "COMPLETED"
        case _:
            return "UNKNOWN"


def get_all_state_of_instance(url: str, instance_id: str) -> dict:
    state = {}
    res = requests.post(
        f"{url}/query/GetAllMessages",
        json={"input": {"InstanceID": instance_id}},
    )
    state["messages"] = {
        item["MessageID"]: from_num_to_state(item["MsgState"]) for item in res.json()
    }
    res = requests.post(
        f"{url}/query/GetAllActionEvents",
        json={"input": {"InstanceID": instance_id}},
    )
    state["events"] = {
        item["EventID"]: from_num_to_state(item["EventState"]) for item in res.json()
    }
    res = requests.post(
        f"{url}/query/GetAllGateways",
        json={"input": {"InstanceID": instance_id}},
    )
    state["gateways"] = {
        item["GatewayID"]: from_num_to_state(item["GatewayState"])
        for item in res.json()
    }
    res = requests.post(
        f"{url}/query/GetAllBusinessRules",
        json={"input": {"InstanceID": instance_id}},
    )
    state["business_rules"] = {
        item["BusinessRuleID"]: from_num_to_state(item["State"]) for item in res.json()
    }
    return state


def pre_check(url: str, instance_id, conditions: list[CHECK_CONDITION]) -> bool:
    print("PRE CHECK")
    state = get_all_state_of_instance(url, instance_id)
    for condition in conditions:
        element = condition.element
        element_type = condition.element_type
        match element_type:
            case ElementTypes.MESSAGE:
                if state["messages"][element] != condition.pre_state:
                    err_msg = f"Message {element} is not {condition.pre_state}"
                    print(err_msg)
                    return False, err_msg
            case ElementTypes.EVENT:
                if state["events"][element] != condition.pre_state:
                    err_msg = f"Event {element} is not {condition.pre_state}"
                    print(err_msg)
                    return False, err_msg
            case ElementTypes.GATEWAY:
                if state["gateways"][element] != condition.pre_state:
                    err_msg = f"Gateway {element} is not {condition.pre_state}"
                    print(err_msg)
                    return False, err_msg
            case _:
                return False, "Unknown Element Type"
    return True, ""


def post_check(url: str, instance_id, conditions: list[CHECK_CONDITION]) -> bool:
    print("POST CHECK")
    state = get_all_state_of_instance(url, instance_id)
    for condition in conditions:
        element = condition.element
        element_type = condition.element_type
        match element_type:
            case ElementTypes.MESSAGE:
                if state["messages"][element] != condition.post_state:
                    err_msg = f"Message {element} is not {condition.post_state}"
                    print(err_msg)
                    return False, err_msg
            case ElementTypes.EVENT:
                if state["events"][element] != condition.post_state:
                    err_msg = f"Event {element} is not {condition.post_state}"
                    print(err_msg)
                    return False, err_msg
            case ElementTypes.GATEWAY:
                if state["gateways"][element] != condition.post_state:
                    err_msg = f"Gateway {element} is not {condition.post_state}"
                    print(err_msg)
                    return False, err_msg
            case _:
                return False, "Unknown Element Type"
    return True, ""


def get_real_invoker(invoker: str) -> str:

    return invoker


def invoke_api(chaincode_url: str, instance_id: str, step: STEP, invoker_map) -> bool:
    # Execute
    is_message = True if step.type == ElementTypes.MESSAGE else False

    method_name = step.element if not is_message else f"{step.element}_Send"

    if is_message:
        meta = json.loads(step.meta)
        params = {}
        idx = 0
        for key in meta["properties"].keys():
            params[key] = step.param[idx]
            idx += 1

        full_param = {
            "input": {
                **params,
                "InstanceID": instance_id,
                "FireFlyTran": "123",
            },
            "key": invoker_map[step.invoker]["key"],
        }
        chaincode_url = invoker_map[step.invoker]["fireflyUrl"]
    else:
        full_param = {
            "input": {
                "InstanceID": instance_id,
            },
        }

    res = requests.post(
        f"{chaincode_url}/invoke/{method_name}",
        json=full_param,
    )
    # time.sleep(5)
    print(res.text)

    operation_id = res.json()["id"]
    # Wait Return Value and Event
    pattern = r"(http:\/\/[\w\.]+):(\d+)"
    match = re.search(pattern, chaincode_url)

    if match:
        invoker_firefly_url = match.group(1)
        invoker_firefly_port = match.group(2)
        print(f"invoker_firefly_url: {invoker_firefly_url}:{invoker_firefly_port}")
    else:
        print("No match found.")

    # Wait for the operation to complete
    while True:
        time.sleep(1)
        res = requests.get(
            f"{invoker_firefly_url}:{invoker_firefly_port}/api/v1/namespaces/default/operations/{operation_id}?fetchstatus=true"
        )
        invoke_status = res.json()["status"]
        print(f"Invoke Status: {invoke_status}")
        if invoke_status == "Pending":
            continue
        else:
            break
    # Check if invoke is Success
    if invoke_status == "Succeeded":
        return True, res.json()["output"]
    elif invoke_status == "Failed":
        return False, res.json()["output"]["errorMessage"]


def invoke_step(
    url, instance_id: str, step: STEP | None, invoker_map
) -> BoolWithMessage:
    get_all_state_of_instance(url, instance_id)

    if not step:
        return BoolWithMessage(False, "Step not found")

    is_success, msg = pre_check(url, instance_id, step.check_conditions)
    if not is_success:
        return BoolWithMessage(False, f"Pre-check failed, reason:[{msg}]")

    if not invoke_api(url, instance_id, step, invoker_map):
        return BoolWithMessage(False, "Invoke failed")

    is_success, msg = post_check(url, instance_id, step.check_conditions)
    if not is_success:
        return BoolWithMessage(False, "Post-check failed")
    return BoolWithMessage(True, "Step passed")


def invoke_choreograph_path_step(
    url, instance_id: str, step: STEP | None, invoker_map
) -> BoolWithMessage:
    is_success, msg = invoke_api(url, instance_id, step, invoker_map)
    if not is_success:
        return BoolWithMessage(False, f"Invoke failed,Reason:[{msg}]")
    return BoolWithMessage(True, "Step passed")


def invoke_task(
    path, steps: list[STEP], url, create_instance_param, invoker_map
) -> BoolWithMessage:

    # Create A New Instance of Task

    res = requests.post(
        f"{url}/invoke/CreateInstance",
        json=create_instance_param,
    )
    subscription_name = "InstanceCreated-Customer"

    message = subsribe_and_get_result(subscription_name)
    blockchain_instance_id = message["blockchainEvent"]["output"]["InstanceID"]
    print(f"blockchain_instance_id: {blockchain_instance_id}")

    # return BoolWithMessage(True, "Instance created")

    # TODO : maintain a map of step name to step object
    def get_step_with_name(name: str) -> STEP:
        for step in steps:
            if step.element == name:
                return step
        return None

    for index, step in enumerate(path):
        if not (
            res := invoke_choreograph_path_step(
                url, blockchain_instance_id, get_step_with_name(step), invoker_map
            )
        ):
            return BoolWithMessage(False, f"Step {index} failed for reason:{res}")
    return BoolWithMessage(True, "All steps passed")
