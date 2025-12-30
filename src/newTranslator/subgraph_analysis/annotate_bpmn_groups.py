from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple
import xml.etree.ElementTree as ET


NS = {
    "bpmn2": "http://www.omg.org/spec/BPMN/20100524/MODEL",
    "bpmndi": "http://www.omg.org/spec/BPMN/20100524/DI",
    "dc": "http://www.omg.org/spec/DD/20100524/DC",
    "di": "http://www.omg.org/spec/DD/20100524/DI",
}


def _register_namespaces() -> None:
    for prefix, uri in NS.items():
        ET.register_namespace(prefix, uri)


def _load_regions(region_json: Path) -> List[Dict[str, object]]:
    data = json.loads(region_json.read_text(encoding="utf8"))
    return data.get("regions", [])


def _region_score(region: Dict[str, object], type_map: Dict[str, str]) -> float:
    nodes = region.get("nodes", [])
    size = len(nodes)
    gateways = sum(1 for n in nodes if type_map.get(n, "").endswith("GATEWAY"))
    events = sum(1 for n in nodes if "EVENT" in type_map.get(n, ""))
    tasks = sum(1 for n in nodes if "TASK" in type_map.get(n, ""))
    # emphasize control-heavy subgraphs
    return size + 3 * gateways + 2 * events + 1 * tasks


def _select_regions(
    regions: List[Dict[str, object]],
    type_map: Dict[str, str],
    top_k: int,
) -> List[Dict[str, object]]:
    ranked = sorted(regions, key=lambda r: _region_score(r, type_map), reverse=True)
    return ranked[:top_k]


def _find_choreography(root: ET.Element) -> ET.Element:
    choreography = root.find(".//bpmn2:choreography", NS)
    if choreography is None:
        raise ValueError("No bpmn2:choreography found.")
    return choreography


def _find_bpmn_plane(root: ET.Element) -> ET.Element:
    plane = root.find(".//bpmndi:BPMNPlane", NS)
    if plane is None:
        raise ValueError("No bpmndi:BPMNPlane found.")
    return plane


def _collect_shape_bounds(plane: ET.Element) -> Dict[str, Tuple[float, float, float, float]]:
    bounds_map: Dict[str, Tuple[float, float, float, float]] = {}
    for shape in plane.findall("bpmndi:BPMNShape", NS):
        element_id = shape.attrib.get("bpmnElement")
        bounds = shape.find("dc:Bounds", NS)
        if not element_id or bounds is None:
            continue
        x = float(bounds.attrib.get("x", "0"))
        y = float(bounds.attrib.get("y", "0"))
        width = float(bounds.attrib.get("width", "0"))
        height = float(bounds.attrib.get("height", "0"))
        bounds_map[element_id] = (x, y, width, height)
    return bounds_map


def _ensure_category(root: ET.Element, group_id: str, label: str) -> str:
    category = root.find("bpmn2:category", NS)
    if category is None:
        category = ET.SubElement(root, f"{{{NS['bpmn2']}}}category", {"id": "Category_1"})
    value_id = f"CategoryValue_{group_id}"
    ET.SubElement(
        category,
        f"{{{NS['bpmn2']}}}categoryValue",
        {"id": value_id, "value": label},
    )
    return value_id


def _compute_bounds(
    nodes: List[str],
    bounds_map: Dict[str, Tuple[float, float, float, float]],
    padding: float,
) -> Tuple[float, float, float, float]:
    xs: List[float] = []
    ys: List[float] = []
    x2s: List[float] = []
    y2s: List[float] = []
    for node in nodes:
        if node not in bounds_map:
            continue
        x, y, w, h = bounds_map[node]
        xs.append(x)
        ys.append(y)
        x2s.append(x + w)
        y2s.append(y + h)
    if not xs:
        return 0.0, 0.0, 0.0, 0.0
    min_x = min(xs) - padding
    min_y = min(ys) - padding
    max_x = max(x2s) + padding
    max_y = max(y2s) + padding
    return min_x, min_y, max_x - min_x, max_y - min_y


def annotate_groups(
    bpmn_path: Path,
    regions_json: Path,
    output_path: Path,
    top_k: int,
    padding: float,
) -> None:
    _register_namespaces()
    tree = ET.parse(bpmn_path)
    root = tree.getroot()
    choreography = _find_choreography(root)
    plane = _find_bpmn_plane(root)
    bounds_map = _collect_shape_bounds(plane)

    from generator.parser.choreography_parser.parser import Choreography

    choreography_parser = Choreography()
    choreography_parser.load_diagram_from_xml_file(str(bpmn_path))
    type_map = {
        node.id: node.type.name for node in choreography_parser.nodes if hasattr(node, "type")
    }

    regions = _load_regions(regions_json)
    regions = _select_regions(regions, type_map, top_k)
    for idx, region in enumerate(regions, start=1):
        group_id = f"Group_SESE_{idx}"
        label = f"SESE_{idx}"
        category_value = _ensure_category(root, group_id, label)
        group = ET.SubElement(
            choreography,
            f"{{{NS['bpmn2']}}}group",
            {"id": group_id, "categoryValueRef": category_value},
        )
        group.set("name", label)

        nodes = region.get("nodes", [])
        x, y, w, h = _compute_bounds(nodes, bounds_map, padding)
        if w == 0 and h == 0:
            continue
        shape = ET.SubElement(
            plane,
            f"{{{NS['bpmndi']}}}BPMNShape",
            {"id": f"{group_id}_di", "bpmnElement": group_id},
        )
        ET.SubElement(
            shape,
            f"{{{NS['dc']}}}Bounds",
            {"x": str(x), "y": str(y), "width": str(w), "height": str(h)},
        )

    tree.write(output_path, encoding="utf-8", xml_declaration=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Annotate BPMN with Group elements for SESE subgraphs."
    )
    parser.add_argument("bpmn", type=Path, help="Path to BPMN XML file")
    parser.add_argument("regions", type=Path, help="Path to SESE JSON output")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output BPMN path (default: subgraph_analysis/output/<name>.grouped.bpmn)",
    )
    parser.add_argument("--top-k", type=int, default=5, help="Top-k regions to group")
    parser.add_argument("--padding", type=float, default=20.0, help="Padding in pixels")
    args = parser.parse_args()

    bpmn_path = args.bpmn.resolve()
    regions_path = args.regions.resolve()
    if args.output is None:
        out_dir = Path(__file__).resolve().parent / "output"
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / f"{bpmn_path.stem}.grouped.bpmn"
    else:
        output_path = args.output.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

    annotate_groups(bpmn_path, regions_path, output_path, args.top_k, args.padding)
    print(f"Grouped BPMN written to: {output_path}")


if __name__ == "__main__":
    main()
