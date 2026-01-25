#!/usr/bin/env python3
"""
Visualize the execution path from config.json
"""

import json
import sys


def visualize_path(config_file="config.json"):
    """Visualize the execution path."""

    with open(config_file, 'r') as f:
        config = json.load(f)

    execution_path = config["execution_path"]
    participants = config["participants"]

    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "BPMN-NFT SUPPLY CHAIN EXECUTION PATH" + " " * 21 + "║")
    print("╚" + "═" * 78 + "╝")
    print()

    print(f"Contract: {config['contract_name']}")
    print(f"Total steps: {len(execution_path)}")
    print()

    print("Participants:")
    for pid, pdata in participants.items():
        print(f"  • {pdata['name']:20s} ({pid})")
    print()

    print("─" * 80)
    print()

    type_symbols = {
        "event": "🎯",
        "message": "📨",
        "gateway": "🔀",
        "activity": "⚙️"
    }

    for step in execution_path:
        step_num = step["step"]
        step_type = step["type"]
        step_id = step["id"]
        desc = step.get("description", "")

        symbol = type_symbols.get(step_type, "❓")

        print(f"{symbol} Step {step_num:2d}: {step_type.upper():8s} - {step_id}")

        if step_type == "message" and "invoker" in step:
            invoker_name = participants[step["invoker"]]["name"]
            print(f"   └─ Invoker: {invoker_name} ({step['invoker']})")

        if desc:
            print(f"   └─ {desc}")

        if "params" in step:
            print(f"   └─ Parameters: {step['params']}")

        if "note" in step:
            print(f"   ⚠️  Note: {step['note']}")

        print()

    print("─" * 80)
    print()
    print("Legend:")
    print(f"  {type_symbols['event']} Event    - Start/End events")
    print(f"  {type_symbols['message']} Message  - Message exchanges between participants")
    print(f"  {type_symbols['gateway']} Gateway  - Control flow gateways (split/join)")
    print(f"  {type_symbols['activity']} Activity - Token operations (mint/transfer/query)")
    print()


def main():
    """Main function."""
    config_file = "config.json"
    if len(sys.argv) > 1:
        config_file = sys.argv[1]

    try:
        visualize_path(config_file)
    except FileNotFoundError:
        print(f"Error: Configuration file '{config_file}' not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in '{config_file}'.")
        sys.exit(1)
    except KeyError as e:
        print(f"Error: Missing required field in configuration: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
