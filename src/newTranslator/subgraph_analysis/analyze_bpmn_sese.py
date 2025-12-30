from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple

import networkx as nx

from generator.parser.choreography_parser.parser import Choreography


def _load_graph(bpmn_path: Path) -> nx.DiGraph:
    choreography = Choreography()
    choreography.load_diagram_from_xml_file(str(bpmn_path))
    return choreography.topology_graph_without_message


def _is_sese_region(
    graph: nx.DiGraph,
    region: Set[str],
    entry: str,
    exit: str,
) -> bool:
    entry_nodes = set()
    exit_nodes = set()
    for node in region:
        if any(pred not in region for pred in graph.predecessors(node)):
            entry_nodes.add(node)
        if any(succ not in region for succ in graph.successors(node)):
            exit_nodes.add(node)
    if entry_nodes != {entry} or exit_nodes != {exit}:
        return False
    if entry == exit:
        return False
    if not any(succ in region for succ in graph.successors(entry)):
        return False
    if not any(pred in region for pred in graph.predecessors(exit)):
        return False
    return True


def _collect_sese_regions(graph: nx.DiGraph) -> List[Dict[str, object]]:
    nodes = list(graph.nodes)
    descendants = {n: nx.descendants(graph, n) for n in nodes}
    ancestors = {n: nx.ancestors(graph, n) for n in nodes}
    regions: List[Dict[str, object]] = []

    for entry in nodes:
        reachable = descendants[entry]
        if not reachable:
            continue
        for exit in reachable:
            region = (reachable | {entry}) & (ancestors[exit] | {exit})
            if len(region) < 2:
                continue
            if not _is_sese_region(graph, region, entry, exit):
                continue
            subgraph = graph.subgraph(region)
            regions.append(
                {
                    "entry": entry,
                    "exit": exit,
                    "nodes": sorted(region),
                    "size": len(region),
                    "edges": subgraph.number_of_edges(),
                }
            )
    return regions


def _condense_graph(graph: nx.DiGraph) -> Dict[str, object]:
    sccs = list(nx.strongly_connected_components(graph))
    comp_index: Dict[str, int] = {}
    for idx, comp in enumerate(sccs):
        for node in comp:
            comp_index[node] = idx

    condensed = nx.DiGraph()
    for idx, comp in enumerate(sccs):
        condensed.add_node(idx, nodes=sorted(comp))
    for u, v in graph.edges():
        cu = comp_index[u]
        cv = comp_index[v]
        if cu != cv:
            condensed.add_edge(cu, cv)
    return {
        "graph": condensed,
        "components": {str(i): sorted(comp) for i, comp in enumerate(sccs)},
    }


def _select_top_regions(regions: List[Dict[str, object]], k: int) -> List[Dict[str, object]]:
    return sorted(regions, key=lambda r: r.get("size", 0), reverse=True)[:k]


def _color_palette() -> List[str]:
    return [
        "#3B82F6",
        "#10B981",
        "#F59E0B",
        "#EF4444",
        "#8B5CF6",
        "#06B6D4",
        "#F97316",
        "#22C55E",
        "#E11D48",
        "#A855F7",
    ]


def _build_region_color_map(
    regions: List[Dict[str, object]],
    top_k: int,
) -> Tuple[Dict[str, str], List[Dict[str, object]]]:
    selected = _select_top_regions(regions, top_k)
    colors = _color_palette()
    color_map: Dict[str, str] = {}
    for idx, region in enumerate(selected):
        color = colors[idx % len(colors)]
        for node in region.get("nodes", []):
            color_map[node] = color
    return color_map, selected


def analyze_bpmn(bpmn_path: Path, output_path: Path) -> Dict[str, object]:
    graph = _load_graph(bpmn_path)
    condensed_info = _condense_graph(graph)
    condensed_graph: nx.DiGraph = condensed_info["graph"]
    result: Dict[str, object] = {
        "bpmn": str(bpmn_path),
        "dag": nx.is_directed_acyclic_graph(graph),
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "condensed_nodes": condensed_graph.number_of_nodes(),
        "condensed_edges": condensed_graph.number_of_edges(),
        "components": condensed_info["components"],
        "regions": [],
    }

    condensed_regions = _collect_sese_regions(condensed_graph)
    regions: List[Dict[str, object]] = []
    for region in condensed_regions:
        comp_nodes = region["nodes"]
        entry_comp = region["entry"]
        exit_comp = region["exit"]
        region_components = [str(node) for node in comp_nodes]
        region_nodes: Set[str] = set()
        for comp_id in region_components:
            region_nodes.update(result["components"][comp_id])
        regions.append(
            {
                "entry_component": entry_comp,
                "exit_component": exit_comp,
                "entry_nodes": result["components"][str(entry_comp)],
                "exit_nodes": result["components"][str(exit_comp)],
                "components": region_components,
                "nodes": sorted(region_nodes),
                "size": len(region_nodes),
                "condensed_size": len(comp_nodes),
                "edges": region["edges"],
            }
        )

    result["regions"] = regions
    output_path.write_text(json.dumps(result, indent=2), encoding="utf8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze BPMN as DAG and extract single-entry/single-exit subgraphs."
        )
    )
    parser.add_argument("bpmn", type=Path, help="Path to BPMN XML file")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON path (default: subgraph_analysis/output/<name>.sese.json)",
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="Generate interactive HTML visualization (pyvis required).",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Highlight top-k largest SESE regions in visualization.",
    )
    args = parser.parse_args()

    bpmn_path = args.bpmn.resolve()
    if args.output is None:
        out_dir = Path(__file__).resolve().parent / "output"
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / f"{bpmn_path.stem}.sese.json"
    else:
        output_path = args.output.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

    result = analyze_bpmn(bpmn_path, output_path)
    if args.html:
        try:
            from pyvis.network import Network
        except ImportError as exc:
            raise SystemExit(
                "pyvis is required for --html. Install with: pip install pyvis"
            ) from exc

        graph = _load_graph(bpmn_path)
        color_map, selected = _build_region_color_map(result["regions"], args.top_k)
        net = Network(height="800px", width="100%", directed=True)
        net.barnes_hut()

        for node in graph.nodes():
            label = node
            color = color_map.get(node, "#CBD5E1")
            net.add_node(node, label=label, color=color)
        for u, v in graph.edges():
            net.add_edge(u, v)

        html_path = output_path.with_suffix(".html")
        net.write_html(str(html_path))
        result["html"] = str(html_path)
        result["highlighted_regions"] = selected
        output_path.write_text(json.dumps(result, indent=2), encoding="utf8")
        print(f"HTML visualization written to: {html_path}")

    print(f"SESE regions written to: {output_path}")


if __name__ == "__main__":
    main()
