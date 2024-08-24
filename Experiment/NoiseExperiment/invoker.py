from loader import STEP, CHECK_CONDITION, BoolWithMessage, ElementTypes
import requests
import json
import websocket
import time
import re
import select


def extract_url_port(chaincode_url):
    pattern = r"(http:\/\/[\w\.]+):(\d+)"
    match = re.search(pattern, chaincode_url)

    if match:
        invoker_firefly_url = match.group(1)
        invoker_firefly_port = match.group(2)
        # print(f"invoker_firefly_url: {invoker_firefly_url}:{invoker_firefly_port}")
    else:
        print("No match found.")
    return invoker_firefly_url, invoker_firefly_port


def websocket_listen_get_result(subscription_name: str, timeout: int = 20):
    ws_uri = "ws://localhost:5001/ws"
    ws = websocket.WebSocket()
    ws.connect(ws_uri)
    message_to_send = {
        "type": "start",
        "name": subscription_name,
        "namespace": "default",
        "autoack": True,
    }
    ws.send(json.dumps(message_to_send))
    print(f"Sent: {message_to_send}")
    ws_fd = ws.sock.fileno()  # Get the file descriptor of the WebSocket socket
    poll = select.poll()
    poll.register(ws_fd, select.POLLIN)  # Register to poll for incoming data

    start_time = time.time()

    while True:
        elapsed_time = time.time() - start_time
        if elapsed_time >= timeout:
            print("Timeout reached. Closing connection.")
            ws.close()
            return False, {"error": "Timeout after {} seconds".format(timeout)}

        events = poll.poll(
            (timeout - elapsed_time) * 1000
        )  # Poll remaining time in milliseconds

        if events:
            message = ws.recv()
            print(f"Received: {message}")
            ws.close()
            return True, json.loads(message)

        time.sleep(1)  # Optional: to avoid busy waiting


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


def pre_check(
    url: str, instance_id, conditions: list[CHECK_CONDITION]
) -> BoolWithMessage:
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


def post_check(
    url: str, instance_id, conditions: list[CHECK_CONDITION]
) -> BoolWithMessage:
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


def parse_meta(step_meta):
    if isinstance(step_meta, str):
        # 如果是字符串格式，先尝试将其转换为字典
        try:
            step_meta = json.loads(step_meta)
        except json.JSONDecodeError:
            raise ValueError("The string could not be parsed as JSON.")
    elif not isinstance(step_meta, dict):
        raise TypeError("The input should be either a string or a dictionary.")

    # 如果已经是字典格式，直接返回
    return step_meta


def invoke_api(
    chaincode_url: str, instance_id: str, step: STEP, invoker_map, contract_name
) -> bool:

    # Execute
    is_message = True if step.type == ElementTypes.MESSAGE else False
    is_activity = True if step.type == ElementTypes.ACTIVITY else False
    method_name = step.element

    if is_message:
        method_name = f"{step.element}_Send"
        meta = parse_meta(step.meta)
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
    print(f"invoke method {method_name}", res.text)
    operation_id = res.json()["id"]
    # Wait Return Value and Event
    invoker_firefly_url, invoker_firefly_port = extract_url_port(chaincode_url)

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
    # if is activity, waiting for Activity_continueDone event
    if is_activity:
        # Check if invoke is Success
        if invoke_status == "Failed":
            return False, res.json()["output"]["errorMessage"]
        is_success, msg = websocket_listen_get_result(
            "Avtivity_continueDone-" + contract_name
        )
        if not is_success:
            return False, f"{step.element} failed,Reason:[{msg}]"
        blockchain_instance_id = msg["blockchainEvent"]["output"]["InstanceID"]
        if blockchain_instance_id == instance_id:
            return True, "Activity passed"
        else:
            return (
                False,
                "Activity intanceID not equal, received InstanceId:"
                + blockchain_instance_id
                + "expected InstanceId:"
                + instance_id,
            )

    else:
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

    if not (res := invoke_api(url, instance_id, step, invoker_map)):
        return BoolWithMessage(False, f"Invoke failed:{res.message}")

    is_success, msg = post_check(url, instance_id, step.check_conditions)
    if not is_success:
        return BoolWithMessage(False, "Post-check failed")
    return BoolWithMessage(True, "Step passed")


def invoke_choreograph_path_step(
    url, instance_id: str, step: STEP | None, invoker_map, contract_name
) -> BoolWithMessage:
    is_success, msg = invoke_api(url, instance_id, step, invoker_map, contract_name)
    if not is_success:
        return BoolWithMessage(False, f"Invoke failed,Reason:[{msg}]")
    return BoolWithMessage(True, "Step passed")


def invoke_task(
    path_indexes,
    steps: list[STEP],
    url,
    create_instance_param,
    invoker_map,
    contract_name,
) -> BoolWithMessage:
    # Create A New Instance of Task

    res = requests.post(
        f"{url}/invoke/CreateInstance",
        json=create_instance_param,
    )
    print("create instance response:", res.text)
    # create contract listener and subscribe to the event
    subscription_name = "InstanceCreated-" + contract_name

    is_success, message = websocket_listen_get_result(subscription_name)
    if not is_success:
        return BoolWithMessage(False, f"Instance creation failed,Reason:[{message}]")
    blockchain_instance_id = message["blockchainEvent"]["output"]["InstanceID"]
    print(f"blockchain_instance_id: {blockchain_instance_id}")

    # return BoolWithMessage(True, "Instance created")

    for index, path_index in enumerate(path_indexes):
        if not (
            res := invoke_choreograph_path_step(
                url,
                blockchain_instance_id,
                steps[path_index],
                invoker_map,
                contract_name,
            )
        ):
            return BoolWithMessage(False, f"Step {index} failed for reason:{res}")
    return BoolWithMessage(True, "All steps passed")
