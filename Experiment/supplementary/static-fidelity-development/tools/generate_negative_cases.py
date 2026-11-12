#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from tools.common import EXP2_ROOT, dump_text


ASSERTIONS_PATH = EXP2_ROOT / "config" / "assertion_table.yaml"
NEGATIVE_DIR = EXP2_ROOT / "cases" / "negative"


CASE_BODIES = {
    "missing_flow_target": """contract InvalidMissingFlowTarget {
    participants {
        participant A { msp "AMSP" attributes { role = "a" } }
        participant B { msp "BMSP" attributes { role = "b" } }
    }
    globals {
        Approved: bool
    }
    messages {
        message Request from A to B { initial state INACTIVE schema "{}" }
    }
    gateways {
    }
    events {
        event StartEvent_1 { initial state READY }
        event EndEvent_1 { initial state INACTIVE }
    }
    businessrules {
    }
    oracletasks {
    }
    flows {
        start event StartEvent_1 enables MissingMessage;
        when message Request completed then enable EndEvent_1;
    }
}
""",
    "missing_set_variable": """contract InvalidMissingSetVariable {
    participants {
        participant Buyer { msp "BuyerMSP" attributes { role = "buyer" } }
        participant Seller { msp "SellerMSP" attributes { role = "seller" } }
    }
    globals {
        Counter: int
    }
    messages {
        message Offer from Seller to Buyer { initial state INACTIVE schema "{}" }
    }
    gateways {
    }
    events {
        event StartEvent_1 { initial state READY }
        event EndEvent_1 { initial state INACTIVE }
    }
    businessrules {
    }
    oracletasks {
    }
    flows {
        start event StartEvent_1 enables Offer;
        when message Offer completed then set MissingCounter = 1, enable EndEvent_1;
    }
}
""",
    "invalid_gateway_type": """contract InvalidGatewayType {
    participants {
        participant P1 { msp "P1MSP" attributes { role = "p1" } }
        participant P2 { msp "P2MSP" attributes { role = "p2" } }
    }
    globals {
        Flag: bool
    }
    messages {
        message Msg1 from P1 to P2 { initial state INACTIVE schema "{}" }
    }
    gateways {
        gateway BadGateway { type xor initial state INACTIVE }
    }
    events {
        event StartEvent_1 { initial state READY }
        event EndEvent_1 { initial state INACTIVE }
    }
    businessrules {
    }
    oracletasks {
    }
    flows {
        start event StartEvent_1 enables Msg1;
        when message Msg1 completed then enable EndEvent_1;
    }
}
""",
    "missing_message_trigger": """contract InvalidMissingMessageTrigger {
    participants {
        participant A { msp "AMSP" attributes { role = "a" } }
        participant B { msp "BMSP" attributes { role = "b" } }
    }
    globals {
        G: bool
    }
    messages {
        message KnownMsg from A to B { initial state INACTIVE schema "{}" }
    }
    gateways {
    }
    events {
        event StartEvent_1 { initial state READY }
        event EndEvent_1 { initial state INACTIVE }
    }
    businessrules {
    }
    oracletasks {
    }
    flows {
        start event StartEvent_1 enables KnownMsg;
        when message MissingMsg completed then enable EndEvent_1;
    }
}
""",
    "missing_message_sender": """contract InvalidMissingMessageSender {
    participants {
        participant Receiver { msp "ReceiverMSP" attributes { role = "receiver" } }
    }
    globals {
        G: bool
    }
    messages {
        message Msg1 from UnknownSender to Receiver { initial state INACTIVE schema "{}" }
    }
    gateways {
    }
    events {
        event StartEvent_1 { initial state READY }
        event EndEvent_1 { initial state INACTIVE }
    }
    businessrules {
    }
    oracletasks {
    }
    flows {
        start event StartEvent_1 enables Msg1;
    }
}
""",
    "missing_rule_mapping_global": """contract InvalidRuleMappingGlobal {
    participants {
        participant Clerk { msp "ClerkMSP" attributes { role = "clerk" } }
        participant Reviewer { msp "ReviewerMSP" attributes { role = "reviewer" } }
    }
    globals {
        Score: int
    }
    messages {
        message Submit from Clerk to Reviewer { initial state INACTIVE schema "{}" }
    }
    gateways {
        gateway Choice { type exclusive initial state INACTIVE }
    }
    events {
        event StartEvent_1 { initial state READY }
        event EndEvent_1 { initial state INACTIVE }
    }
    businessrules {
        businessrule Rule1 {
            dmn "rule1.dmn"
            decision "Decision1"
            input mapping {
                score -> MissingScore
            }
            initial state INACTIVE
        }
    }
    oracletasks {
    }
    flows {
        start event StartEvent_1 enables Submit;
        when message Submit completed then enable Rule1;
    }
}
""",
    "missing_parallel_source": """contract InvalidParallelSource {
    participants {
        participant A { msp "AMSP" attributes { role = "a" } }
        participant B { msp "BMSP" attributes { role = "b" } }
        participant C { msp "CMSP" attributes { role = "c" } }
    }
    globals {
        Ready: bool
    }
    messages {
        message MsgA from A to B { initial state INACTIVE schema "{}" }
        message MsgB from B to C { initial state INACTIVE schema "{}" }
    }
    gateways {
        gateway ParallelGateway_1 { type parallel initial state INACTIVE }
        gateway ParallelGateway_2 { type parallel initial state INACTIVE }
    }
    events {
        event StartEvent_1 { initial state READY }
        event EndEvent_1 { initial state INACTIVE }
    }
    businessrules {
    }
    oracletasks {
    }
    flows {
        start event StartEvent_1 enables ParallelGateway_1;
        when gateway ParallelGateway_1 completed then enable MsgA, enable MsgB;
        parallel gateway ParallelGateway_2 await MsgA, MissingMsg then enable EndEvent_1;
    }
}
""",
    "missing_start_event": """contract InvalidMissingStartEvent {
    participants {
        participant A { msp "AMSP" attributes { role = "a" } }
        participant B { msp "BMSP" attributes { role = "b" } }
    }
    globals {
        Approved: bool
    }
    messages {
        message Request from A to B { initial state INACTIVE schema "{}" }
    }
    gateways {
    }
    events {
        event EndEvent_1 { initial state INACTIVE }
    }
    businessrules {
    }
    oracletasks {
    }
    flows {
        start event MissingStart enables Request;
        when message Request completed then enable EndEvent_1;
    }
}
""",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="根据统一断言表中的负例生成器配置生成负例 DSL 样例。")
    parser.add_argument("--assertions", default=str(ASSERTIONS_PATH))
    parser.add_argument("--outdir", default=str(NEGATIVE_DIR))
    args = parser.parse_args()

    assertions_path = Path(args.assertions).resolve()
    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    config = yaml.safe_load(assertions_path.read_text(encoding="utf-8")) or {}
    for generator_id in (config.get("negative_generators") or {}).keys():
        body = CASE_BODIES.get(generator_id)
        if not body:
            continue
        filename = generator_id if generator_id.startswith("invalid_") else f"invalid_{generator_id}"
        filename = f"{filename}.b2c"
        dump_text(outdir / filename, body)


if __name__ == "__main__":
    main()
