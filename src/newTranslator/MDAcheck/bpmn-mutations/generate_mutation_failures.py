#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
POS_XMI_DIR = ROOT / "bpmn-positive" / "xmi"
MUT_ROOT = ROOT / "bpmn-mutations"
MUT_XMI_DIR = MUT_ROOT / "xmi"
REPORT_DIR = ROOT / "ocl-report-bpmn-mutations"
REPORT_JSON = REPORT_DIR / "report.json"
MANIFEST_PRE = MUT_ROOT / "manifest.pre-validation.json"
MANIFEST = MUT_ROOT / "manifest.json"
RUN_VALIDATE = ROOT / "run_ocl_validate_batch.sh"
ECORE = ROOT / "b2c.ecore"
OCL = ROOT / "check.ocl"

NS_B2C = "https://chaincollab/newTranslator/b2c"
NS_XSI = "http://www.w3.org/2001/XMLSchema-instance"
XSI_TYPE = f"{{{NS_XSI}}}type"
ET.register_namespace("b2c", NS_B2C)
ET.register_namespace("xmi", "http://www.omg.org/XMI")
ET.register_namespace("xsi", NS_XSI)


RULE_TARGETS = {
    "Model::AtLeastOneContract": 10,
    "Model::UniqueContractNames": 10,
    "Contract::UniqueNamesPerKind": 10,
    "Participant::MspX509Paired": 10,
    "Participant::MultiBoundsPaired": 10,
    "Participant::MultiBoundsOrder": 10,
    "Participant::AttributeKeysUnique": 10,
    "Message::SenderNotReceiver": 10,
    "BusinessRule::InputMappingParamUnique": 10,
    "BusinessRule::OutputMappingParamUnique": 10,
    "Contract::StartDoesNotEnableItself": 10,
    "GatewayFlow::CompareBranchesNoDuplicateConditions": 10,
    "SetGlobalAction::SetLiteralTypeMatchesGlobalType": 10,
    "GatewayCompareBranch::CompareLiteralTypeMatchesGlobalType": 10,
}


def local_name(tag: str) -> str:
    return tag.split("}", 1)[-1]


def children_named(parent: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in list(parent) if local_name(child.tag) == name]


def first_section(contract: ET.Element, section_type: str) -> ET.Element:
    for section in children_named(contract, "sections"):
        if (section.get(XSI_TYPE) or "").endswith(section_type):
            return section
    raise ValueError(f"missing section {section_type}")


def first_flow_item(contract: ET.Element, item_type: str | None = None) -> ET.Element:
    flow_section = first_section(contract, "FlowSection")
    items = children_named(flow_section, "flowItems")
    if item_type is None:
        if not items:
            raise ValueError("missing flowItems")
        return items[0]
    for item in items:
        if (item.get(XSI_TYPE) or "").endswith(item_type):
            return item
    raise ValueError(f"missing flow item {item_type}")


def first_gateway_compare_pair(contract: ET.Element) -> tuple[ET.Element, ET.Element, ET.Element]:
    flow_section = first_section(contract, "FlowSection")
    for flow in children_named(flow_section, "flowItems"):
        if not (flow.get(XSI_TYPE) or "").endswith("GatewayFlow"):
            continue
        branches = [
            b for b in children_named(flow, "branches")
            if (b.get(XSI_TYPE) or "").endswith("GatewayCompareBranch")
        ]
        if len(branches) >= 2:
            return flow, branches[0], branches[1]
    raise ValueError("missing gateway compare pair")


def clone_tree(path: Path) -> ET.ElementTree:
    return ET.parse(path)


def write_tree(tree: ET.ElementTree, out_path: Path) -> None:
    tree.write(out_path, encoding="utf-8", xml_declaration=True)


def replace_contract_index(elem: ET.Element, old: int, new: int) -> None:
    needle = f"//@contracts.{old}/"
    repl = f"//@contracts.{new}/"
    for node in elem.iter():
        for key, value in list(node.attrib.items()):
            if needle in value:
                node.set(key, value.replace(needle, repl))


def contract_section_index(contract: ET.Element, section: ET.Element) -> int:
    return children_named(contract, "sections").index(section)


def contract_global_ref(contract: ET.Element, global_index: int) -> str:
    global_section = first_section(contract, "GlobalSection")
    sec_idx = contract_section_index(contract, global_section)
    return f"//@contracts.0/@sections.{sec_idx}/@globals.{global_index}"


def choose_global(contract: ET.Element, preferred_type: str | None = None, variant: int = 0) -> tuple[int, ET.Element]:
    globals_ = children_named(first_section(contract, "GlobalSection"), "globals")
    candidates = [
        (idx, g) for idx, g in enumerate(globals_)
        if preferred_type is None or g.get("type", "string") == preferred_type
    ]
    if not candidates:
        candidates = list(enumerate(globals_))
    if not candidates:
        raise ValueError("missing globals")
    return candidates[variant % len(candidates)]


def choose_participant(contract: ET.Element, variant: int = 0) -> ET.Element:
    participants = children_named(first_section(contract, "ParticipantSection"), "participants")
    if not participants:
        raise ValueError("missing participants")
    return participants[variant % len(participants)]


def choose_rule(contract: ET.Element, variant: int = 0) -> ET.Element:
    rules = children_named(first_section(contract, "BusinessRuleSection"), "rules")
    if not rules:
        raise ValueError("missing rules")
    return rules[variant % len(rules)]


def choose_message(contract: ET.Element, variant: int = 0) -> ET.Element:
    messages = children_named(first_section(contract, "MessageSection"), "messages")
    if not messages:
        raise ValueError("missing messages")
    return messages[variant % len(messages)]


def mutate_at_least_one_contract(tree: ET.ElementTree, variant: int) -> None:
    root = tree.getroot()
    for contract in children_named(root, "contracts"):
        root.remove(contract)


def mutate_unique_contract_names(tree: ET.ElementTree, variant: int) -> None:
    root = tree.getroot()
    contracts = children_named(root, "contracts")
    if not contracts:
        raise ValueError("missing contracts")
    clone = copy.deepcopy(contracts[0])
    replace_contract_index(clone, 0, 1)
    root.append(clone)


def mutate_unique_names_per_kind(tree: ET.ElementTree, variant: int) -> None:
    contract = children_named(tree.getroot(), "contracts")[0]
    participants = children_named(first_section(contract, "ParticipantSection"), "participants")
    if len(participants) < 2:
        raise ValueError("need at least two participants")
    participants[1].set("name", participants[0].get("name", "dup"))


def mutate_msp_x509_paired(tree: ET.ElementTree, variant: int) -> None:
    contract = children_named(tree.getroot(), "contracts")[0]
    participant = choose_participant(contract, 0)
    participant.attrib.pop("msp", None)
    participant.set("x509", f"CERT_{variant}")


def mutate_multi_bounds_paired(tree: ET.ElementTree, variant: int) -> None:
    contract = children_named(tree.getroot(), "contracts")[0]
    participant = choose_participant(contract, 0)
    participant.attrib.pop("multiMin", None)
    participant.set("multiMax", "0")


def mutate_multi_bounds_order(tree: ET.ElementTree, variant: int) -> None:
    contract = children_named(tree.getroot(), "contracts")[0]
    participant = choose_participant(contract, 0)
    participant.set("multiMin", "2")
    participant.set("multiMax", "1")


def mutate_attribute_keys_unique(tree: ET.ElementTree, variant: int) -> None:
    contract = children_named(tree.getroot(), "contracts")[0]
    participant = choose_participant(contract, 0)
    attrs = children_named(participant, "attributes")
    if not attrs:
        raise ValueError("missing participant attributes")
    dup = copy.deepcopy(attrs[0])
    dup.set("value", f"dup_{variant}")
    participant.append(dup)


def mutate_sender_not_receiver(tree: ET.ElementTree, variant: int) -> None:
    contract = children_named(tree.getroot(), "contracts")[0]
    msg = choose_message(contract, 0)
    msg.set("receiver", msg.get("sender", ""))


def mutate_input_mapping_param_unique(tree: ET.ElementTree, variant: int) -> None:
    contract = children_named(tree.getroot(), "contracts")[0]
    rule = choose_rule(contract, 0)
    inputs = children_named(rule, "inputMappings")
    if not inputs:
        raise ValueError("missing inputMappings")
    rule.append(copy.deepcopy(inputs[0]))


def mutate_output_mapping_param_unique(tree: ET.ElementTree, variant: int) -> None:
    contract = children_named(tree.getroot(), "contracts")[0]
    rule = choose_rule(contract, 0)
    outputs = children_named(rule, "outputMappings")
    if not outputs:
        raise ValueError("missing outputMappings")
    rule.append(copy.deepcopy(outputs[0]))


def mutate_start_does_not_enable_itself(tree: ET.ElementTree, variant: int) -> None:
    contract = children_named(tree.getroot(), "contracts")[0]
    start_flow = first_flow_item(contract, "StartFlow")
    target = children_named(start_flow, "target")
    if not target:
        raise ValueError("missing StartFlow target")
    target[0].set("target", start_flow.get("start", ""))


def mutate_compare_branches_no_duplicate_conditions(tree: ET.ElementTree, variant: int) -> None:
    contract = children_named(tree.getroot(), "contracts")[0]
    _, first, second = first_gateway_compare_pair(contract)
    second.set("var", first.get("var", ""))
    second.set("relation", first.get("relation", "=="))
    second_value = children_named(second, "value")
    first_value = children_named(first, "value")
    if not first_value:
        raise ValueError("missing compare branch value")
    if second_value:
        second.remove(second_value[0])
    second.insert(0, copy.deepcopy(first_value[0]))


def wrong_literal_attrs(global_type: str, variant: int) -> dict[str, str]:
    if global_type == "bool":
        return {"stringValue": f"wrong_bool_{variant}"}
    if global_type in {"int", "float"}:
        return {"boolValue": "true" if variant % 2 == 0 else "false"}
    return {"intValue": str(variant + 1)}


def mutate_set_literal_type_matches_global_type(tree: ET.ElementTree, variant: int) -> None:
    contract = children_named(tree.getroot(), "contracts")[0]
    flow_item = first_flow_item(contract, "MessageFlow")
    idx, glob = choose_global(contract, variant=0)
    action = ET.SubElement(flow_item, "actions")
    action.set(XSI_TYPE, "b2c:SetGlobalAction")
    action.set("var", contract_global_ref(contract, idx))
    expr = ET.SubElement(action, "expr")
    for key, value in wrong_literal_attrs(glob.get("type", "string"), variant).items():
        expr.set(key, value)


def mutate_compare_literal_type_matches_global_type(tree: ET.ElementTree, variant: int) -> None:
    contract = children_named(tree.getroot(), "contracts")[0]
    _, branch, _ = first_gateway_compare_pair(contract)
    var_ref = branch.get("var", "")
    global_idx = int(var_ref.rsplit(".", 1)[1]) if "." in var_ref else 0
    _, glob = choose_global(contract, variant=global_idx)
    values = children_named(branch, "value")
    if not values:
        raise ValueError("missing compare value")
    value = values[0]
    for key in ["stringValue", "intValue", "boolValue"]:
        value.attrib.pop(key, None)
    for key, literal in wrong_literal_attrs(glob.get("type", "string"), variant).items():
        value.set(key, literal)


MUTATORS = {
    "Model::AtLeastOneContract": ("mut_model_no_contract", mutate_at_least_one_contract),
    "Model::UniqueContractNames": ("mut_duplicate_contract_name", mutate_unique_contract_names),
    "Contract::UniqueNamesPerKind": ("mut_duplicate_participant_name", mutate_unique_names_per_kind),
    "Participant::MspX509Paired": ("mut_msp_x509_unpaired", mutate_msp_x509_paired),
    "Participant::MultiBoundsPaired": ("mut_multi_bounds_unpaired", mutate_multi_bounds_paired),
    "Participant::MultiBoundsOrder": ("mut_multi_bounds_order", mutate_multi_bounds_order),
    "Participant::AttributeKeysUnique": ("mut_duplicate_attribute_key", mutate_attribute_keys_unique),
    "Message::SenderNotReceiver": ("mut_sender_equals_receiver", mutate_sender_not_receiver),
    "BusinessRule::InputMappingParamUnique": ("mut_duplicate_input_mapping_param", mutate_input_mapping_param_unique),
    "BusinessRule::OutputMappingParamUnique": ("mut_duplicate_output_mapping_param", mutate_output_mapping_param_unique),
    "Contract::StartDoesNotEnableItself": ("mut_start_targets_itself", mutate_start_does_not_enable_itself),
    "GatewayFlow::CompareBranchesNoDuplicateConditions": ("mut_duplicate_compare_condition", mutate_compare_branches_no_duplicate_conditions),
    "SetGlobalAction::SetLiteralTypeMatchesGlobalType": ("mut_setglobal_literal_type_mismatch", mutate_set_literal_type_matches_global_type),
    "GatewayCompareBranch::CompareLiteralTypeMatchesGlobalType": ("mut_compare_literal_type_mismatch", mutate_compare_literal_type_matches_global_type),
}


def collect_actual_rules(report_json: Path) -> dict[str, list[str]]:
    data = json.loads(report_json.read_text(encoding="utf-8"))
    out: dict[str, list[str]] = {}
    for model in data.get("models", []):
        rel = model.get("relativePath")
        rules = sorted({v.get("code") for v in model.get("violations", []) if v.get("code")})
        if rel:
            out[Path(rel).name] = rules
    return out


def build_mutations() -> list[dict]:
    template = POS_XMI_DIR / "Blood_analysis.xmi"
    if not template.exists():
        raise SystemExit(f"no positives under {POS_XMI_DIR}")

    if MUT_XMI_DIR.exists():
        shutil.rmtree(MUT_XMI_DIR)
    MUT_XMI_DIR.mkdir(parents=True, exist_ok=True)

    entries: list[dict] = []
    for rule, quota in RULE_TARGETS.items():
        label, mutator = MUTATORS[rule]
        for i in range(quota):
            src = template
            variant = i
            tree = clone_tree(src)
            mutator(tree, variant)
            out_name = f"{src.stem}__{label}_{i:02d}.xmi"
            out_path = MUT_XMI_DIR / out_name
            write_tree(tree, out_path)
            entries.append(
                {
                    "sourcePositive": src.name,
                    "mutantName": out_name,
                    "path": f"xmi/{out_name}",
                    "intendedRule": rule,
                    "mutation": label,
                    "variant": i,
                }
            )
    MANIFEST_PRE.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")
    return entries


def validate_mutations() -> None:
    if REPORT_DIR.exists():
        shutil.rmtree(REPORT_DIR)
    subprocess.run(
        [
            "bash",
            str(RUN_VALIDATE),
            str(MUT_XMI_DIR),
            str(ECORE),
            str(OCL),
            str(REPORT_DIR),
        ],
        check=True,
    )


def enrich_manifest(entries: list[dict]) -> None:
    actual_map = collect_actual_rules(REPORT_JSON)
    enriched = []
    for entry in entries:
        actual_rules = actual_map.get(entry["mutantName"], [])
        enriched.append(
            {
                **entry,
                "ok": len(actual_rules) == 0,
                "actualRules": actual_rules,
            }
        )
    MANIFEST.write_text(json.dumps(enriched, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    entries = build_mutations()
    validate_mutations()
    enrich_manifest(entries)

    by_rule = defaultdict(int)
    for item in json.loads(MANIFEST.read_text(encoding="utf-8")):
        by_rule[item["intendedRule"]] += 1

    print("Generated coverage mutation set:")
    for rule in sorted(by_rule):
        print(f"  {rule}: {by_rule[rule]}")
    print(f"Manifest: {MANIFEST}")
    print(f"Report:   {REPORT_JSON}")


if __name__ == "__main__":
    main()
