#!/usr/bin/env python3
"""
BPMN-NFT Supply Chain Clean Path Execution Script (Enhanced with Result Output)
This version collects execution results and outputs them to JSON file.
"""

import json
import time
import sys
import os
import requests
import websocket
import select
from datetime import datetime


def load_config(config_file="config_runtime.json"):
    """Load configuration from JSON file."""
    if not os.path.exists(config_file):
        print(f"Configuration file '{config_file}' not found!")
        print("Please create it based on config.json template.")
        sys.exit(1)

    with open(config_file, 'r') as f:
        return json.load(f)


def extract_url_port(chaincode_url):
    """Extract URL and port from chaincode URL."""
    import re
    pattern = r"(http:\/\/[\w\.]+):(\d+)"
    match = re.search(pattern, chaincode_url)

    if match:
        return match.group(1), match.group(2)
    else:
        raise ValueError(f"Invalid URL format: {chaincode_url}")


def build_ws_uri_from_api_url(api_url: str) -> tuple[str, str, str]:
    """Return (ws_uri, firefly_url, firefly_port) from a FireFly API URL."""
    firefly_url, firefly_port = extract_url_port(api_url)
    ws_uri = firefly_url.replace("http://", "ws://") + f":{firefly_port}/ws"
    return ws_uri, firefly_url, firefly_port


def get_contract_interface_id(api_url: str) -> str | None:
    """Try to resolve the contract interface ID from the /apis/{id} endpoint."""
    try:
        r = requests.get(api_url, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        iface = data.get("interface")
        if isinstance(iface, dict):
            return iface.get("id") or iface.get("interface")
        if isinstance(iface, str):
            return iface
    except Exception:
        return None
    return None


def create_listener_and_subscribe(event_name: str, subscription_name: str, contract_name: str,
                                 api_url: str, contract_interface_id: str) -> tuple[bool, str]:
    """Create a listener+subscription like the reference main.py does (firstEvent=oldest)."""
    ws_uri, firefly_url, firefly_port = build_ws_uri_from_api_url(api_url)

    listeners_url = f"{firefly_url}:{firefly_port}/api/v1/namespaces/default/contracts/listeners"
    subs_url = f"{firefly_url}:{firefly_port}/api/v1/namespaces/default/subscriptions"

    # 1) listener
    res = requests.post(
        listeners_url,
        json={
            "interface": {"id": contract_interface_id},
            "location": {"channel": "default", "chaincode": contract_name},
            "event": {"name": event_name},
            "options": {"firstEvent": "oldest"},
            "topic": subscription_name,
        },
        timeout=15,
    )
    if res.status_code not in (200, 201, 202):
        # If the listener/subscription already exists (common when rerunning), just reuse it (Scheme A)
        if "already exists" in res.text.lower() or "same channel id" in res.text.lower():
            return True, ws_uri
        return False, f"Create listener failed: HTTP {res.status_code}: {res.text}"
    listener_id = res.json().get("id")
    if not listener_id:
        return False, f"Create listener returned no id: {res.text}"

    # 2) subscription
    res = requests.post(
        subs_url,
        json={
            "namespace": "default",
            "name": subscription_name,
            "transport": "websockets",
            "filter": {
                "events": "blockchain_event_received",
                "blockchainevent": {"listener": listener_id},
            },
            "options": {"firstEvent": "oldest"},
        },
        headers={"Content-Type": "application/json"},
        timeout=15,
    )
    if res.status_code not in (200, 201, 202):
        # If it already exists, reuse it (Scheme A)
        if "already exists" in res.text.lower() or "same channel id" in res.text.lower():
            return True, ws_uri
        return False, f"Create subscription failed: HTTP {res.status_code}: {res.text}"

    return True, ws_uri


def wait_operation_done(api_url: str, operation_id: str, max_attempts: int = 60) -> tuple[bool, dict]:
    """Poll /operations/{id}?fetchstatus=true until Succeeded/Failed."""
    firefly_url, firefly_port = extract_url_port(api_url)
    op_url = f"{firefly_url}:{firefly_port}/api/v1/namespaces/default/operations/{operation_id}?fetchstatus=true"

    last = {}
    for _ in range(max_attempts):
        time.sleep(1)
        r = requests.get(op_url)
        if r.status_code != 200:
            last = {"error": f"HTTP {r.status_code}: {r.text}"}
            continue
        last = r.json()
        st = last.get("status")
        if st == "Pending":
            continue
        return (st == "Succeeded"), last
    return False, last


def get_instance_id_by_tx(api_url: str, tx_id: str, timeout: int = 60) -> str | None:
    """Resolve InstanceID by querying /blockchainevents filtered by tx (stable, avoids websocket replay issues)."""
    firefly_url, firefly_port = extract_url_port(api_url)
    events_url = (
        f"{firefly_url}:{firefly_port}/api/v1/namespaces/default/blockchainevents"
        f"?name=InstanceCreated&tx={tx_id}"
    )
    for _ in range(timeout):
        time.sleep(1)
        try:
            r = requests.get(events_url, timeout=10)
            if r.status_code != 200:
                continue
            events = r.json()
            if isinstance(events, list) and len(events) > 0:
                output = events[0].get("output") or {}
                inst = output.get("InstanceID")
                if inst is not None:
                    return str(inst)
        except Exception:
            continue
    return None

def websocket_listen_get_result(subscription_name: str, timeout: int = 30, ws_uri: str | None = None):
    """Listen for websocket events with timeout."""
    if ws_uri is None:
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
    print(f"WebSocket sent: {message_to_send} (uri={ws_uri})")

    ws_fd = ws.sock.fileno()
    poll = select.poll()
    poll.register(ws_fd, select.POLLIN)

    start_time = time.time()

    while True:
        elapsed_time = time.time() - start_time
        if elapsed_time >= timeout:
            print(f"Timeout reached after {timeout} seconds")
            ws.close()
            return False, {"error": f"Timeout after {timeout} seconds"}

        events = poll.poll(int((timeout - elapsed_time) * 1000))

        if events:
            message = ws.recv()
            ws.close()
            return True, json.loads(message)

        time.sleep(0.2)
def invoke_message(url, instance_id, message_id, invoker_key, params=None):
    """Invoke a message send operation."""
    method_name = f"{message_id}_Send"

    full_param = {
        "input": {
            **(params or {}),
            "InstanceID": instance_id,
            "FireFlyTran": "123",
        },
        "key": invoker_key,
    }

    print(f"\n=== Invoking {method_name} ===")
    print(f"Parameters: {json.dumps(full_param, indent=2)}")

    res = requests.post(f"{url}/invoke/{method_name}", json=full_param)
    print(f"Response: {res.text}")

    if res.status_code not in (200, 202):
        return False, f"HTTP {res.status_code}: {res.text}"

    operation_id = res.json()["id"]

    # Wait for operation to complete
    firefly_url, firefly_port = extract_url_port(url)

    max_attempts = 30
    for attempt in range(max_attempts):
        time.sleep(1)
        status_res = requests.get(
            f"{firefly_url}:{firefly_port}/api/v1/namespaces/default/operations/{operation_id}?fetchstatus=true"
        )
        invoke_status = status_res.json()["status"]
        print(f"Operation status: {invoke_status} (attempt {attempt+1}/{max_attempts})")

        if invoke_status == "Succeeded":
            return True, status_res.json().get("output", "Success")
        elif invoke_status == "Failed":
            error_msg = status_res.json().get("output", {}).get("errorMessage", "Unknown error")
            return False, error_msg
        elif invoke_status != "Pending":
            break

    return False, "Operation timeout"


def invoke_event(url, instance_id, event_id):
    """Invoke an event."""
    full_param = {
        "input": {
            "InstanceID": instance_id
        }
    }

    print(f"\n=== Invoking {event_id} ===")

    res = requests.post(f"{url}/invoke/{event_id}", json=full_param)
    print(f"Response: {res.text}")

    if res.status_code not in (200, 202):
        return False, f"HTTP {res.status_code}: {res.text}"

    operation_id = res.json()["id"]

    # Wait for operation to complete
    firefly_url, firefly_port = extract_url_port(url)

    for _ in range(30):
        time.sleep(1)
        status_res = requests.get(
            f"{firefly_url}:{firefly_port}/api/v1/namespaces/default/operations/{operation_id}?fetchstatus=true"
        )
        invoke_status = status_res.json()["status"]
        print(f"Operation status: {invoke_status}")

        if invoke_status == "Succeeded":
            return True, status_res.json().get("output", "Success")
        elif invoke_status == "Failed":
            error_msg = status_res.json().get("output", {}).get("errorMessage", "Unknown error")
            return False, error_msg

    return False, "Operation timeout"


def invoke_gateway(url, instance_id, gateway_id):
    """Invoke a gateway."""
    return invoke_event(url, instance_id, gateway_id)


def invoke_activity(url, instance_id, activity_id,  invoker_key,contract_name):
    """Invoke an activity."""
    full_param = {
        "input": {
            "InstanceID": instance_id
        },
        "key": invoker_key
    }

    print(f"\n=== Invoking {activity_id} ===")

    res = requests.post(f"{url}/invoke/{activity_id}", json=full_param)
    print(f"Response: {res.text}")

    if res.status_code not in (200, 202):
        return False, f"HTTP {res.status_code}: {res.text}"

    operation_id = res.json()["id"]

    # Wait for operation to complete
    firefly_url, firefly_port = extract_url_port(url)

    for _ in range(30):
        time.sleep(1)
        status_res = requests.get(
            f"{firefly_url}:{firefly_port}/api/v1/namespaces/default/operations/{operation_id}?fetchstatus=true"
        )
        invoke_status = status_res.json()["status"]
        print(f"Operation status: {invoke_status}")

        if invoke_status == "Failed":
            error_msg = status_res.json().get("output", {}).get("errorMessage", "Unknown error")
            return False, error_msg
        elif invoke_status == "Succeeded":
            return True, status_res.json().get("output", "Success")

    return False, "Operation timeout"


def create_instance(url, participants, erc_chaincodes, bpmn_id, contract_name):
    """Create a new contract instance. The returned CreateInstance 'id' is an operation id, NOT the instance id.
    We must read InstanceID from the InstanceCreated event (reference invoker.py does this).
    """
    print("\n=== Creating Instance ===")

    # Build initParametersBytes
    init_params = {}
    for pid, pdata in participants.items():
        init_params[pid] = {
            "msp": pdata["msp"],
            "attributes": {},
            "isMulti": False,
            "multiMaximum": 0,
            "multiMinimum": 0,
            "x509": pdata["x509"]
        }

    init_params["ERCChaincodeNames"] = erc_chaincodes
    init_params["BpmnId"] = bpmn_id

    create_instance_params = {
        "input": {
            "initParametersBytes": json.dumps(init_params)
        }
    }

    print(f"Parameters: {json.dumps(create_instance_params, indent=2)}")

    # Resolve interface id to create a listener/subscription BEFORE invoking, to avoid missing the event
    contract_interface_id = get_contract_interface_id(url)

    # Scheme A: reuse the existing (stable) subscription name
    subscription_name = f"InstanceCreated-{contract_name}"

    # If we can resolve interface id, create listener+subscription now
    ws_uri = None
    if contract_interface_id:
        ok, ws_or_err = create_listener_and_subscribe(
            "InstanceCreated", subscription_name, contract_name, url, contract_interface_id
        )
        if not ok:
            print(f"⚠️  {ws_or_err} (will still try to listen if subscription already exists)")
        else:
            ws_uri = ws_or_err

    # Invoke CreateInstance
    res = requests.post(f"{url}/invoke/CreateInstance", json=create_instance_params)
    print(f"Response: {res.text}")

    if res.status_code not in (200, 202):
        return None, f"HTTP {res.status_code}: {res.text}"

    # If interface id was not resolvable earlier, try to pull it from the operation response (best-effort)
    try:
        if not contract_interface_id:
            contract_interface_id = res.json().get("input", {}).get("interface")
            if contract_interface_id:
                ok, ws_or_err = create_listener_and_subscribe(
                    "InstanceCreated", subscription_name, contract_name, url, contract_interface_id
                )
                if ok:
                    ws_uri = ws_or_err
    except Exception:
        pass

    # If ws_uri still missing, at least use url-derived ws endpoint
    if ws_uri is None:
        ws_uri, _, _ = build_ws_uri_from_api_url(url)

    # IMPORTANT (reference behavior): listen for InstanceCreated immediately (do NOT wait for operation first)
    is_success, message = websocket_listen_get_result(subscription_name, timeout=90, ws_uri=ws_uri)
    if not is_success:
        # also poll the operation for better diagnostics
        op_id = None
        try:
            op_id = res.json().get("id")
        except Exception:
            op_id = None
        if op_id:
            ok, op = wait_operation_done(url, op_id, max_attempts=30)
            st = op.get("status")
            print(f"CreateInstance operation finished: {st}. Full={op}")
        return None, f"Instance creation failed,Reason:[{message}]"

    # Extract real InstanceID from event
    try:
        instance_id = message["blockchainEvent"]["output"]["InstanceID"]
    except Exception:
        return None, f"InstanceCreated event format unexpected: {message}"

    print(f"✓ Instance created with ID: {instance_id}")

    # Finally, ensure operation itself is succeeded (optional but helpful)
    try:
        op_id = res.json().get("id")
        if op_id:
            ok, op = wait_operation_done(url, op_id, max_attempts=30)
            if not ok:
                return None, f"CreateInstance operation failed: {op.get('output', op)}"
    except Exception:
        pass

    return instance_id, None
def run_clean_path(config):
    """Execute the clean path through the BPMN contract and collect results."""

    url = config["url"]
    contract_name = config["contract_name"]
    participants = config["participants"]
    erc_chaincodes = config["erc_chaincodes"]
    execution_path = config["execution_path"]
    bpmn_id = config.get("bpmn_id", contract_name)

    # Result collection
    result = {
        "task_name": f"{contract_name}_clean_path",
        "timestamp": datetime.now().isoformat(),
        "instance_id": None,
        "steps_executed": [],
        "status": "running",
        "error_message": None
    }

    # Create instance
    instance_id, error = create_instance(url, participants, erc_chaincodes, bpmn_id, contract_name)
    if error:
        print(f"✗ Failed to create instance: {error}")
        result["status"] = "error"
        result["error_message"] = f"Instance creation failed: {error}"
        return result

    result["instance_id"] = instance_id
    time.sleep(3)

    print(f"\n{'='*60}")
    print(f"Executing {len(execution_path)} steps in clean path")
    print(f"{'='*60}")

    # Execute each step
    for i, step in enumerate(execution_path):
        step_result = {
            "step_number": i + 1,
            "step_id": step["id"],
            "step_type": step["type"],
            "description": step.get("description", ""),
            "status": "pending",
            "result": None,
            "error": None,
            "timestamp": datetime.now().isoformat()
        }

        print(f"\n[{i+1}/{len(execution_path)}] Step: {step['type']} - {step['id']}")
        if 'description' in step:
            print(f"Description: {step['description']}")

        success = False
        result_data = None

        try:
            if step["type"] == "message":
                invoker_key = participants[step["invoker"]]["key"]
                success, result_data = invoke_message(
                    url, instance_id, step["id"], invoker_key, step.get("params")
                )

            elif step["type"] == "event":
                success, result_data = invoke_event(url, instance_id, step["id"])

            elif step["type"] == "gateway":
                success, result_data = invoke_gateway(url, instance_id, step["id"])

            elif step["type"] == "activity":
                invoker_key = participants[step["invoker"]]["key"]
                success, result_data = invoke_activity(url, instance_id, step["id"], invoker_key, contract_name)

            if success:
                step_result["status"] = "success"
                step_result["result"] = str(result_data)
                print(f"✓ Step {i+1} succeeded")
            else:
                step_result["status"] = "failed"
                step_result["error"] = str(result_data)
                print(f"✗ Step {i+1} FAILED: {result_data}")
                result["steps_executed"].append(step_result)
                result["status"] = "failed"
                result["error_message"] = f"Step {i+1} ({step['id']}) failed: {result_data}"
                return result

        except Exception as e:
            step_result["status"] = "error"
            step_result["error"] = str(e)
            print(f"✗ Step {i+1} ERROR: {e}")
            result["steps_executed"].append(step_result)
            result["status"] = "error"
            result["error_message"] = f"Step {i+1} ({step['id']}) error: {e}"
            return result

        result["steps_executed"].append(step_result)
        time.sleep(2)

    print(f"\n{'='*60}")
    print(f"✓ All {len(execution_path)} steps completed successfully!")
    print(f"{'='*60}")

    result["status"] = "success"
    return result


def main():
    """Main execution function."""

    print("""
╔══════════════════════════════════════════════════════════════╗
║  BPMN-NFT Supply Chain Clean Path Execution Script          ║
║  Enhanced version with result output                         ║
╚══════════════════════════════════════════════════════════════╝
""")

    # Check for config file argument
    config_file = "config_runtime.json"
    output_file = "execution_result.json"

    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]

    print(f"Configuration file: {config_file}")
    print(f"Output file: {output_file}")

    config = load_config(config_file)

    print("\nConfiguration loaded:")
    print(f"  Contract: {config['contract_name']}")
    print(f"  URL: {config['url']}")
    print(f"  Participants: {len(config['participants'])}")
    print(f"  Execution steps: {len(config['execution_path'])}")

    print("\nPress Enter to start execution, or Ctrl+C to cancel...")
    try:
        input()
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        sys.exit(0)

    # Run the clean path and collect results
    result = run_clean_path(config)

    # Save results to JSON file
    print(f"\n{'='*60}")
    print(f"Saving results to {output_file}...")

    # Load existing results if file exists
    existing_results = []
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r') as f:
                existing_results = json.load(f)
        except:
            existing_results = []

    # Append new result
    if isinstance(existing_results, list):
        existing_results.append(result)
    else:
        existing_results = [result]

    # Save to file
    with open(output_file, 'w') as f:
        json.dump(existing_results, f, indent=2)

    print(f"✓ Results saved to {output_file}")

    # Print summary
    print(f"\n{'='*60}")
    print("EXECUTION SUMMARY")
    print(f"{'='*60}")
    print(f"Status: {result['status'].upper()}")
    print(f"Instance ID: {result['instance_id']}")
    print(f"Total steps: {len(result['steps_executed'])}")

    success_count = sum(1 for s in result['steps_executed'] if s['status'] == 'success')
    failed_count = sum(1 for s in result['steps_executed'] if s['status'] == 'failed')
    error_count = sum(1 for s in result['steps_executed'] if s['status'] == 'error')

    print(f"  ✓ Successful: {success_count}")
    print(f"  ✗ Failed: {failed_count}")
    print(f"  ⚠ Errors: {error_count}")

    if result['error_message']:
        print(f"\nError: {result['error_message']}")

    print(f"{'='*60}")

    if result['status'] == 'success':
        print("\n✓ Clean path execution completed successfully!")
        sys.exit(0)
    else:
        print(f"\n✗ Clean path execution failed: {result['status']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
