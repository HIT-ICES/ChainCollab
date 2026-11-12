from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any, Iterable

from pyecore.ecore import EClass, EEnum, EEnumLiteral, EPackage
from pyecore.resources import ResourceSet, URI
from textx import metamodel_from_file


OPTIONAL_ATTRIBUTE_KEYWORDS: dict[tuple[str, str], str] = {
    ("Participant", "msp"): r"\bmsp\b",
    ("Participant", "x509"): r"\bx509\b",
    ("Participant", "isMulti"): r"\bisMulti\b",
    ("Participant", "multiMin"): r"\bmultiMin\b",
    ("Participant", "multiMax"): r"\bmultiMax\b",
    ("Participant", "attributes"): r"\battributes\b",
    ("Message", "initialState"): r"\binitial\s+state\b",
    ("Message", "schema"): r"\bschema\b",
    ("Gateway", "gatewayType"): r"\btype\b",
    ("Gateway", "initialState"): r"\binitial\s+state\b",
    ("Event", "initialState"): r"\binitial\s+state\b",
    ("BusinessRule", "initialState"): r"\binitial\s+state\b",
}

# LiteralExpr uses mutually exclusive alternatives in grammar (stringValue | intValue | boolValue)
# Only one should be output. We detect which one by checking for non-default values.
LITERAL_EXPR_ATTRIBUTES = {"stringValue", "intValue", "boolValue"}


def _span_text(source: str, obj: Any) -> str:
    start = getattr(obj, "_tx_position", None)
    end = getattr(obj, "_tx_position_end", None)
    if isinstance(start, int) and isinstance(end, int) and 0 <= start <= end <= len(source):
        return source[start:end]
    return ""


def _iter_contained_textx_objects(root: Any) -> Iterable[Any]:
    stack = [root]
    seen: set[int] = set()
    while stack:
        obj = stack.pop()
        obj_id = id(obj)
        if obj_id in seen:
            continue
        seen.add(obj_id)
        yield obj

        tx_attrs = getattr(obj.__class__, "_tx_attrs", None)
        if not tx_attrs:
            continue
        for meta in tx_attrs.values():
            if not getattr(meta, "ref", False):
                continue
            if not getattr(meta, "cont", False):
                continue
            value = getattr(obj, meta.name, None)
            if value is None:
                continue
            if isinstance(value, list):
                stack.extend(reversed(value))
            else:
                stack.append(value)


def _load_ecore(ecore_path: Path) -> tuple[ResourceSet, EPackage]:
    rset = ResourceSet()
    resource = rset.get_resource(URI(str(ecore_path)))
    if not resource.contents:
        raise ValueError(f"No EPackage found in {ecore_path}")
    epackage = resource.contents[0]
    if not isinstance(epackage, EPackage):
        raise ValueError(f"Root of {ecore_path} is not an EPackage")
    rset.metamodel_registry[epackage.nsURI] = epackage
    return rset, epackage


def _enum_literal(enum: EEnum, value: Any) -> EEnumLiteral | None:
    if value is None:
        return None
    if isinstance(value, EEnumLiteral):
        return value
    literal_name = str(value)
    if hasattr(enum, literal_name):
        lit = getattr(enum, literal_name)
        if isinstance(lit, EEnumLiteral):
            return lit
    for lit in enum.eLiterals:
        if lit.name == literal_name:
            return lit
    return None


def _is_feature_set_in_text(source: str, obj: Any, class_name: str, feature_name: str) -> bool:
    pattern = OPTIONAL_ATTRIBUTE_KEYWORDS.get((class_name, feature_name))
    if not pattern:
        return True
    return re.search(pattern, _span_text(source, obj)) is not None


def _get_literal_expr_active_attr(tx_obj: Any, source: str) -> str | None:
    """
    Determine which attribute of a LiteralExpr was actually set in the DSL.
    The grammar uses alternatives (stringValue | intValue | boolValue), so only one is valid.
    """
    # Get the source text span for this object to determine what was actually written
    obj_span = _span_text(source, tx_obj).strip()

    # Check for string literal (quoted text)
    if obj_span.startswith('"') or obj_span.startswith("'"):
        return "stringValue"

    # Check for boolean literal
    if obj_span.lower() in ("true", "false"):
        return "boolValue"

    # Otherwise it's an integer
    try:
        int(obj_span)
        return "intValue"
    except (ValueError, TypeError):
        pass

    # Fallback: check which attribute has a non-None value
    sv = getattr(tx_obj, "stringValue", None)
    iv = getattr(tx_obj, "intValue", None)
    bv = getattr(tx_obj, "boolValue", None)

    # String is set if non-None (even empty string means it was parsed as string)
    if sv is not None:
        return "stringValue"
    # Bool is set if not None
    if bv is not None:
        return "boolValue"
    # Int is set if not None
    if iv is not None:
        return "intValue"

    return None


def convert_b2c_to_xmi(
    *,
    tx_path: Path,
    ecore_path: Path,
    b2c_path: Path,
    out_xmi: Path,
) -> None:
    mm = metamodel_from_file(str(tx_path))
    tx_model = mm.model_from_file(str(b2c_path))
    source = b2c_path.read_text(encoding="utf-8")

    rset, epackage = _load_ecore(ecore_path)
    classifiers = {c.name: c for c in epackage.eClassifiers if getattr(c, "name", None)}

    # Pass 1: create all EObjects for containment tree to preserve identity for cross-references.
    tx_to_eobj: dict[int, Any] = {}
    for tx_obj in _iter_contained_textx_objects(tx_model):
        cls_name = tx_obj.__class__.__name__
        ecls = classifiers.get(cls_name)
        if ecls is None or not isinstance(ecls, EClass):
            raise ValueError(f"Ecore missing EClass for '{cls_name}'")
        tx_to_eobj[id(tx_obj)] = ecls()

    # Pass 2: populate attributes and references.
    for tx_obj in _iter_contained_textx_objects(tx_model):
        eobj = tx_to_eobj[id(tx_obj)]
        class_name = eobj.eClass.name

        # For LiteralExpr, determine which attribute was actually set
        literal_active_attr = None
        if class_name == "LiteralExpr":
            literal_active_attr = _get_literal_expr_active_attr(tx_obj, source)

        for feature in eobj.eClass.eAllStructuralFeatures():
            fname = feature.name
            if not hasattr(tx_obj, fname):
                continue

            value = getattr(tx_obj, fname)

            # Special handling for LiteralExpr: only output the active attribute
            if class_name == "LiteralExpr" and fname in LITERAL_EXPR_ATTRIBUTES:
                if fname != literal_active_attr:
                    continue

            # Optional attributes in textX often default to ''/0/False; only set them if
            # the corresponding keyword exists in the original DSL text.
            if feature.lowerBound == 0 and not _is_feature_set_in_text(source, tx_obj, class_name, fname):
                continue

            if feature.eClass.name == "EAttribute":
                if isinstance(feature.eType, EEnum):
                    lit = _enum_literal(feature.eType, value)
                    if lit is None:
                        continue
                    setattr(eobj, fname, lit)
                else:
                    setattr(eobj, fname, value)
                continue

            # Reference
            if feature.upperBound == -1:
                if value is None:
                    continue
                if not isinstance(value, list):
                    raise TypeError(f"Expected list for multi-valued reference {class_name}.{fname}")
                setattr(eobj, fname, [tx_to_eobj[id(v)] for v in value])
            else:
                if value is None:
                    continue
                setattr(eobj, fname, tx_to_eobj[id(value)])

    # Save XMI with Model as root.
    out_xmi.parent.mkdir(parents=True, exist_ok=True)
    resource = rset.create_resource(URI(str(out_xmi)))
    resource.append(tx_to_eobj[id(tx_model)])
    resource.save()


def main() -> int:
    here = Path(__file__).resolve().parent
    default_tx = here.parent / "DSL" / "B2CDSL" / "b2cdsl" / "b2c.tx"
    default_ecore = here / "b2c.ecore"
    default_in = here.parent / "build" / "b2c" / "chaincode.b2c"
    default_out = here / "chaincode.xmi"

    parser = argparse.ArgumentParser(description="Convert B2CDSL .b2c instance model to EMF XMI (.xmi).")
    parser.add_argument("--tx", type=Path, default=default_tx, help="Path to b2c.tx grammar file.")
    parser.add_argument("--ecore", type=Path, default=default_ecore, help="Path to b2c.ecore metamodel file.")
    parser.add_argument("--in", dest="inp", type=Path, default=default_in, help="Input .b2c file.")
    parser.add_argument("--out", type=Path, default=default_out, help="Output .xmi file.")
    args = parser.parse_args()

    convert_b2c_to_xmi(tx_path=args.tx, ecore_path=args.ecore, b2c_path=args.inp, out_xmi=args.out)
    print(f"Wrote: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
