from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Optional

from pyecore.ecore import (
    EAttribute,
    EBoolean,
    EBooleanObject,
    EClass,
    EEnum,
    EInt,
    EIntegerObject,
    EPackage,
    EReference,
    EString,
)
from pyecore.resources import ResourceSet, URI
from textx import metamodel_from_file


ENUM_RULES = {
    "ScalarType",
    "ElementState",
    "GatewayType",
    "MessageCondition",
    "RuleCondition",
    # RelationOperator contains non-identifier literals like '==' and '!=';
    # keep it as EString to avoid tooling issues.
}


OPTIONAL_BOUNDS: dict[tuple[str, str], tuple[int, int]] = {
    ("Contract", "sections"): (0, -1),
    ("ParticipantSection", "participants"): (0, -1),
    ("GlobalSection", "globals"): (0, -1),
    ("MessageSection", "messages"): (0, -1),
    ("GatewaySection", "gateways"): (0, -1),
    ("EventSection", "events"): (0, -1),
    ("BusinessRuleSection", "rules"): (0, -1),
    ("FlowSection", "flowItems"): (0, -1),
    ("Participant", "attributes"): (0, -1),
    ("BusinessRule", "inputMappings"): (0, -1),
    ("BusinessRule", "outputMappings"): (0, -1),
    ("GatewayFlow", "actions"): (0, -1),
    ("GatewayFlow", "branches"): (0, -1),
    ("MessageFlow", "actions"): (1, -1),
    ("GatewayCompareBranch", "actions"): (1, -1),
    ("GatewayExpressionBranch", "actions"): (1, -1),
    ("GatewayElseBranch", "actions"): (1, -1),
    ("RuleFlow", "actions"): (1, -1),
    ("EventFlow", "actions"): (1, -1),
    ("ParallelJoin", "sources"): (1, -1),
    ("ParallelJoin", "actions"): (1, -1),
    ("Model", "contracts"): (1, -1),
    ("LiteralExpr", "stringValue"): (0, 1),
    ("LiteralExpr", "intValue"): (0, 1),
    ("LiteralExpr", "boolValue"): (0, 1),
    ("Participant", "msp"): (0, 1),
    ("Participant", "x509"): (0, 1),
    ("Participant", "multiMin"): (0, 1),
    ("Participant", "multiMax"): (0, 1),
    ("Message", "initialState"): (0, 1),
    ("Message", "schema"): (0, 1),
    ("Gateway", "gatewayType"): (0, 1),
    ("Gateway", "initialState"): (0, 1),
    ("Event", "initialState"): (0, 1),
    ("BusinessRule", "initialState"): (0, 1),
    ("GatewayFlow", "actions"): (0, -1),
    ("GatewayFlow", "branches"): (0, -1),
}


def _extract_enum_literals(grammar_text: str, rule_name: str) -> list[str]:
    lines = grammar_text.splitlines()
    start: Optional[int] = None
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{rule_name}:"):
            start = i
            break
    if start is None:
        raise ValueError(f"Rule '{rule_name}' not found in grammar.")

    literals: list[str] = []
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if stripped == ";":
            break
        literals.extend(re.findall(r"'([^']+)'", stripped))
    # Preserve order while de-duping.
    seen: set[str] = set()
    result: list[str] = []
    for lit in literals:
        if lit not in seen:
            seen.add(lit)
            result.append(lit)
    return result


def _bounds_for(class_name: str, attr_name: str, mult: str) -> tuple[int, int]:
    override = OPTIONAL_BOUNDS.get((class_name, attr_name))
    if override is not None:
        return override
    if mult == "1..*":
        return (0, -1)
    return (1, 1)


def _is_optional(class_name: str, attr_name: str) -> bool:
    lower, _upper = _bounds_for(class_name, attr_name, "1")
    return lower == 0


def build_b2c_epackage(tx_path: Path) -> EPackage:
    mm = metamodel_from_file(str(tx_path))
    namespace = mm.namespaces.get("b2c")
    if not namespace:
        raise ValueError("textX namespace 'b2c' not found. Did you load the correct b2c.tx?")

    grammar_text = tx_path.read_text(encoding="utf-8")

    epackage = EPackage("b2c", nsURI="https://chaincollab/newTranslator/b2c", nsPrefix="b2c")

    enums: dict[str, EEnum] = {}
    for enum_name in sorted(ENUM_RULES):
        literals = _extract_enum_literals(grammar_text, enum_name)
        enums[enum_name] = EEnum(enum_name, literals=literals)
        epackage.eClassifiers.append(enums[enum_name])

    eclasses: dict[str, EClass] = {}
    for name, tx_cls in namespace.items():
        tx_type = getattr(tx_cls, "_tx_type", None)
        if tx_type == "match":
            continue
        if not hasattr(tx_cls, "_tx_attrs"):
            continue
        abstract = tx_type == "abstract"
        eclasses[name] = EClass(name, abstract=abstract)

    for name in sorted(eclasses):
        epackage.eClassifiers.append(eclasses[name])

    # Inheritance: wire abstract bases to their children
    for name, tx_cls in namespace.items():
        base = eclasses.get(name)
        if base is None:
            continue
        children = getattr(tx_cls, "_tx_inh_by", []) or []
        for child in children:
            child_ec = eclasses.get(child.__name__)
            if child_ec is not None:
                child_ec.eSuperTypes.append(base)

    def datatype_for(class_name: str, attr_name: str, type_name: str):
        if type_name in enums:
            return enums[type_name]
        if type_name in ("ID", "STRING"):
            return EString
        if type_name == "INT":
            return EIntegerObject if _is_optional(class_name, attr_name) else EInt
        if type_name == "BOOL":
            # Keep primitive bool for isMulti-like flags to avoid OCL 'undefined' pitfalls.
            return EBooleanObject if _is_optional(class_name, attr_name) else EBoolean
        # Fallback: treat as string.
        return EString

    # Features
    for class_name, tx_cls in namespace.items():
        ecls = eclasses.get(class_name)
        if ecls is None:
            continue

        for attr in tx_cls._tx_attrs.values():
            attr_name = attr.name
            attr_type_name = attr.cls.__name__
            lower, upper = _bounds_for(class_name, attr_name, str(attr.mult))

            if attr.ref:
                target = eclasses.get(attr_type_name)
                if target is None:
                    raise ValueError(
                        f"Reference {class_name}.{attr_name} points to unknown class '{attr_type_name}'."
                    )
                feature = EReference(
                    attr_name,
                    target,
                    containment=bool(attr.cont),
                    upper=upper,
                    lower=lower,
                )
            else:
                dtype = datatype_for(class_name, attr_name, attr_type_name)
                feature = EAttribute(attr_name, dtype, upper=upper, lower=lower)

            ecls.eStructuralFeatures.append(feature)

    return epackage


def main() -> int:
    here = Path(__file__).resolve().parent
    default_tx = here.parent / "DSL" / "B2CDSL" / "b2cdsl" / "b2c.tx"
    default_out = here / "b2c.ecore"

    parser = argparse.ArgumentParser(description="Export B2CDSL textX metamodel to EMF Ecore (.ecore).")
    parser.add_argument("--tx", type=Path, default=default_tx, help="Path to b2c.tx grammar file.")
    parser.add_argument("--out", type=Path, default=default_out, help="Output .ecore path.")
    args = parser.parse_args()

    epackage = build_b2c_epackage(args.tx)
    rset = ResourceSet()
    resource = rset.create_resource(URI(str(args.out)))
    resource.append(epackage)
    resource.save()

    print(f"Wrote: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

