#!/usr/bin/env python3

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Callable
import xml.etree.ElementTree as ET


ROOT = Path("/root/code/ChainCollab/src/newTranslator")
MDA = ROOT / "MDAcheck"
MUT_ROOT = Path(__file__).resolve().parent
POSITIVE_XMI = MDA / "bpmn-positive" / "xmi"
MUT_XMI = MUT_ROOT / "xmi"
REPORT_DIR = MDA / "ocl-report-bpmn-mutations"

NS = {
    "b2c": "https://chaincollab/newTranslator/b2c",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
}
XSI_TYPE = "{http://www.w3.org/2001/XMLSchema-instance}type"


def get_sections(root: ET.Element) -> list[ET.Element]:
    contract = root.find("contracts")
    if contract is None:
        raise ValueError("No contract found")
    return contract.findall("sections")


def section_by_type(root: ET.Element, section_type: str) -> ET.Element:
    for section in get_sections(root):
        if section.get(XSI_TYPE) == f"b2c:{section_type}":
            return section
    raise ValueError(f"Missing section {section_type}")


def flow_items_by_type(root: ET.Element, item_type: str) -> list[ET.Element]:
    flow = section_by_type(root, "FlowSection")
    return [item for item in flow.findall("flowItems") if item.get(XSI_TYPE) == f"b2c:{item_type}"]


def write_tree(tree: ET.ElementTree, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(path, encoding="utf-8", xml_declaration=True)


def load_tree(name: str) -> ET.ElementTree:
    return ET.parse(POSITIVE_XMI / name)


def mutate_sender_equals_receiver(tree: ET.ElementTree) -> str:
    root = tree.getroot()
    msg_section = section_by_type(root, "MessageSection")
    msg = msg_section.findall("messages")[0]
    msg.set("receiver", msg.get("sender"))
    return "Set first message receiver equal to sender"


def mutate_multi_bounds_order(tree: ET.ElementTree) -> str:
    root = tree.getroot()
    participants = section_by_type(root, "ParticipantSection").findall("participants")
    p = participants[0]
    p.set("multiMin", "2")
    p.set("multiMax", "1")
    return "Set first participant multiMin=2 and multiMax=1"


def mutate_duplicate_participant_name(tree: ET.ElementTree) -> str:
    root = tree.getroot()
    participants = section_by_type(root, "ParticipantSection").findall("participants")
    if len(participants) < 2:
        raise ValueError("Need at least two participants")
    participants[1].set("name", participants[0].get("name"))
    return "Set second participant name equal to first participant"


def main() -> int:
    ET.register_namespace("b2c", NS["b2c"])
    ET.register_namespace("xmi", "http://www.omg.org/XMI")
    ET.register_namespace("xsi", NS["xsi"])

    mutation_kinds: list[tuple[str, str, Callable[[ET.ElementTree], str]]] = [
        ("mut_sender_equals_receiver", "Message::SenderNotReceiver", mutate_sender_equals_receiver),
        ("mut_duplicate_participant_name", "Contract::UniqueNamesPerKind", mutate_duplicate_participant_name),
        ("mut_multi_bounds_order", "Participant::MultiBoundsOrder", mutate_multi_bounds_order),
    ]

    plans: list[tuple[str, str, str, Callable[[ET.ElementTree], str]]] = []
    for source in sorted(POSITIVE_XMI.glob("*.xmi")):
        for mutant_name, intended_rule, func in mutation_kinds:
            plans.append((source.name, mutant_name, intended_rule, func))

    if MUT_ROOT.exists():
        shutil.rmtree(MUT_ROOT)
    MUT_XMI.mkdir(parents=True, exist_ok=True)

    manifest: list[dict[str, str]] = []
    for source_name, mutant_name, intended_rule, func in plans:
        tree = load_tree(source_name)
        description = func(tree)
        out = MUT_XMI / f"{Path(source_name).stem}__{mutant_name}.xmi"
        write_tree(tree, out)
        manifest.append(
            {
                "sourceXmi": str(POSITIVE_XMI / source_name),
                "mutantXmi": str(out),
                "mutantName": mutant_name,
                "intendedRule": intended_rule,
                "mutation": description,
            }
        )

    (MUT_ROOT / "manifest.pre-validation.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if REPORT_DIR.exists():
        shutil.rmtree(REPORT_DIR)

    subprocess.run(
        [
            "bash",
            str(MDA / "run_ocl_validate_batch.sh"),
            str(MUT_XMI),
            str(MDA / "b2c.ecore"),
            str(MDA / "check.ocl"),
            str(REPORT_DIR),
        ],
        cwd=ROOT,
        check=True,
    )

    report = json.loads((REPORT_DIR / "report.json").read_text(encoding="utf-8"))
    report_by_name = {
        Path(model["absolutePath"]).name: model
        for model in report["models"]
    }

    final_manifest = []
    for item in manifest:
        name = Path(item["mutantXmi"]).name
        model = report_by_name[name]
        final_manifest.append(
            {
                **item,
                "ok": model["ok"],
                "violationCount": model["violationCount"],
                "actualRules": [v.get("code") for v in model.get("violations", [])],
            }
        )

    (MUT_ROOT / "manifest.json").write_text(
        json.dumps(final_manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Generated {len(final_manifest)} mutated XMI files in {MUT_XMI}")
    print(f"Validation report: {REPORT_DIR / 'report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
