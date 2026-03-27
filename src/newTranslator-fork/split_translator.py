#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional


def _localname(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _detect_split_points_from_bpmn(
    bpmn_path: Path, marker_key: str = "splitPoint"
) -> List[str]:
    tree = ET.parse(str(bpmn_path))
    root = tree.getroot()
    points: List[str] = []

    for elem in root.iter():
        elem_id = elem.attrib.get("id")
        if not elem_id:
            continue

        docs = [
            x
            for x in elem
            if _localname(x.tag).lower() == "documentation" and (x.text or "").strip()
        ]
        if not docs:
            continue

        found = False
        for doc in docs:
            text = (doc.text or "").strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
                if isinstance(payload, dict) and payload.get(marker_key):
                    found = True
                    break
            except Exception:
                lowered = text.lower()
                if (
                    f"{marker_key.lower()}=true" in lowered
                    or "#split" in lowered
                    or "split-point" in lowered
                ):
                    found = True
                    break
        if found:
            points.append(elem_id)

    return points


def _ensure_pythonpath(translator_root: Path) -> None:
    if str(translator_root) not in sys.path:
        sys.path.insert(0, str(translator_root))


def _run(cmd: List[str], cwd: Optional[Path] = None, env: Optional[Dict[str, str]] = None) -> None:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"command failed: {' '.join(cmd)}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )


def _select_regions(
    regions: List[Dict[str, Any]],
    split_points: List[str],
    top_k: int = 2,
) -> List[Dict[str, Any]]:
    ranked = sorted(regions, key=lambda x: int(x.get("size", 0)), reverse=True)
    if not ranked:
        return []
    if not split_points:
        return ranked[:top_k]

    primary = split_points[0]
    with_primary = [r for r in ranked if primary in (r.get("nodes") or [])]
    if len(with_primary) >= top_k:
        return with_primary[:top_k]
    if len(with_primary) == 1:
        first = with_primary[0]
        for r in ranked:
            if r is not first:
                return [first, r]
        return [first]
    return ranked[:top_k]


def _safe_name(path: Path) -> str:
    return path.stem.replace(" ", "_")


def _safe_contract_prefix(raw: str) -> str:
    out = "".join(c if (c.isalnum() or c == "_") else "_" for c in raw)
    if not out or not (out[0].isalpha() or out[0] == "_"):
        out = f"Wf_{out}"
    return out


def _build_split_dsl(
    case_id: str, split_point: str, sub_a: Dict[str, Any], sub_b: Dict[str, Any]
) -> str:
    return "\n".join(
        [
            f"split_workflow {case_id} {{",
            f"  main_contract {case_id}Main;",
            "  split_point SP1 {",
            f"    from_submodel {sub_a['submodelId']};",
            f"    to_submodel {sub_b['submodelId']};",
            f"    marker_node \"{split_point}\";",
            "    handoff_event HandoffRequested;",
            "  }",
            f"  submodel {sub_a['submodelId']} {{",
            f"    start_node \"{sub_a['entryNodes'][0] if sub_a['entryNodes'] else 'UNKNOWN'}\";",
            f"    end_node \"{sub_a['exitNodes'][0] if sub_a['exitNodes'] else 'UNKNOWN'}\";",
            f"    node_count {sub_a['nodeCount']};",
            "  }",
            f"  submodel {sub_b['submodelId']} {{",
            f"    start_node \"{sub_b['entryNodes'][0] if sub_b['entryNodes'] else 'UNKNOWN'}\";",
            f"    end_node \"{sub_b['exitNodes'][0] if sub_b['exitNodes'] else 'UNKNOWN'}\";",
            f"    node_count {sub_b['nodeCount']};",
            "  }",
            "}",
        ]
    )


def _build_source_contract(contract_name: str) -> str:
    return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract {contract_name} {{
    struct HandoffTask {{
        address requester;
        bytes32 payloadHash;
        uint256 nonce;
        uint256 createdAt;
    }}

    uint256 public nextNonce;
    mapping(bytes32 => bool) public taskExists;
    mapping(bytes32 => HandoffTask) private tasks;

    event HandoffRequested(
        bytes32 indexed taskId,
        address indexed requester,
        bytes32 payloadHash,
        uint256 nonce,
        uint256 sourceChainId
    );

    function startAndRequestHandoff(bytes32 payloadHash) external returns (bytes32 taskId) {{
        require(payloadHash != bytes32(0), "empty payload hash");
        uint256 nonce = nextNonce;
        unchecked {{
            nextNonce = nonce + 1;
        }}
        taskId = keccak256(
            abi.encodePacked(block.chainid, address(this), msg.sender, nonce, payloadHash)
        );
        require(!taskExists[taskId], "task already exists");
        taskExists[taskId] = true;
        tasks[taskId] = HandoffTask({{
            requester: msg.sender,
            payloadHash: payloadHash,
            nonce: nonce,
            createdAt: block.timestamp
        }});
        emit HandoffRequested(taskId, msg.sender, payloadHash, nonce, block.chainid);
    }}

    function getTask(bytes32 taskId) external view returns (bool exists, HandoffTask memory task) {{
        exists = taskExists[taskId];
        task = tasks[taskId];
    }}
}}
"""


def _build_target_contract(contract_name: str) -> str:
    return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract {contract_name} {{
    struct Delivery {{
        bool processed;
        bytes32 payloadHash;
        address relayer;
        uint256 sourceChainId;
        address sourceContract;
        uint256 processedAt;
    }}

    address public owner;
    uint256 public processedCount;
    mapping(address => bool) public allowedRelayers;
    mapping(bytes32 => Delivery) private deliveries;
    bytes32 private constant RELAY_DOMAIN = keccak256("BPMN_SPLIT_RELAY_V1");

    event RelayerUpdated(address indexed relayer, bool allowed);
    event HandoffAccepted(
        bytes32 indexed taskId,
        bytes32 payloadHash,
        address indexed relayer,
        uint256 sourceChainId,
        address indexed sourceContract
    );

    modifier onlyOwner() {{
        require(msg.sender == owner, "not owner");
        _;
    }}

    constructor() {{
        owner = msg.sender;
    }}

    function setRelayer(address relayer, bool allowed) external onlyOwner {{
        require(relayer != address(0), "zero relayer");
        allowedRelayers[relayer] = allowed;
        emit RelayerUpdated(relayer, allowed);
    }}

    function acceptHandoff(
        bytes32 taskId,
        bytes32 payloadHash,
        uint256 sourceChainId,
        address sourceContract,
        bytes calldata signature
    ) external {{
        require(taskId != bytes32(0), "empty taskId");
        require(payloadHash != bytes32(0), "empty payloadHash");
        require(sourceContract != address(0), "empty sourceContract");
        require(allowedRelayers[msg.sender], "relayer not allowed");
        require(!deliveries[taskId].processed, "task already processed");

        bytes32 digest = keccak256(
            abi.encodePacked(
                RELAY_DOMAIN,
                address(this),
                block.chainid,
                sourceChainId,
                sourceContract,
                taskId,
                payloadHash
            )
        );

        address signer = _recoverSigner(_toEthSignedMessageHash(digest), signature);
        require(signer == msg.sender, "invalid relay signature");

        deliveries[taskId] = Delivery({{
            processed: true,
            payloadHash: payloadHash,
            relayer: msg.sender,
            sourceChainId: sourceChainId,
            sourceContract: sourceContract,
            processedAt: block.timestamp
        }});
        unchecked {{
            processedCount += 1;
        }}

        emit HandoffAccepted(taskId, payloadHash, msg.sender, sourceChainId, sourceContract);
    }}

    function isProcessed(bytes32 taskId) external view returns (bool) {{
        return deliveries[taskId].processed;
    }}

    function getDelivery(bytes32 taskId) external view returns (Delivery memory) {{
        return deliveries[taskId];
    }}

    function _toEthSignedMessageHash(bytes32 hash) internal pure returns (bytes32) {{
        return keccak256(abi.encodePacked("\\x19Ethereum Signed Message:\\n32", hash));
    }}

    function _recoverSigner(bytes32 digest, bytes memory signature) internal pure returns (address) {{
        require(signature.length == 65, "invalid signature length");
        bytes32 r;
        bytes32 s;
        uint8 v;
        assembly {{
            r := mload(add(signature, 0x20))
            s := mload(add(signature, 0x40))
            v := byte(0, mload(add(signature, 0x60)))
        }}
        if (v < 27) {{
            v += 27;
        }}
        require(v == 27 || v == 28, "invalid signature v");
        address recovered = ecrecover(digest, v, r, s);
        require(recovered != address(0), "ecrecover failed");
        return recovered;
    }}
}}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Translator fork for BPMN split contracts: BPMN -> full artifacts + split DSL + split contracts."
        )
    )
    parser.add_argument("bpmn", type=Path, help="Input BPMN file")
    parser.add_argument(
        "--translator-root",
        type=Path,
        default=Path("/home/logres/system/src/newTranslator"),
        help="Path to base newTranslator project",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("/home/logres/system/src/newTranslator-fork/build_split"),
        help="Output directory root",
    )
    parser.add_argument(
        "--split-point-id",
        action="append",
        default=[],
        help="Manual split marker node id (repeatable)",
    )
    parser.add_argument(
        "--marker-key",
        default="splitPoint",
        help="BPMN documentation json key for split markers",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bpmn_path = args.bpmn.resolve()
    translator_root = args.translator_root.resolve()
    out_root = args.out_dir.resolve()

    if not bpmn_path.exists():
        raise SystemExit(f"bpmn not found: {bpmn_path}")
    if not translator_root.exists():
        raise SystemExit(f"translator root not found: {translator_root}")

    _ensure_pythonpath(translator_root)
    from subgraph_analysis.analyze_bpmn_sese import analyze_bpmn  # type: ignore

    case_id = _safe_name(bpmn_path)
    case_dir = out_root / case_id
    full_dir = case_dir / "full"
    split_dir = case_dir / "split"
    split_contract_dir = split_dir / "contracts"

    full_dir.mkdir(parents=True, exist_ok=True)
    split_contract_dir.mkdir(parents=True, exist_ok=True)

    sese_path = split_dir / f"{case_id}.sese.json"
    analyze_result = analyze_bpmn(bpmn_path, sese_path)

    auto_markers = _detect_split_points_from_bpmn(bpmn_path, marker_key=args.marker_key)
    split_points = [*args.split_point_id, *[x for x in auto_markers if x not in args.split_point_id]]
    selected = _select_regions(analyze_result.get("regions", []), split_points, top_k=2)
    if len(selected) < 2:
        if len(selected) == 1:
            first = selected[0]
            selected = [
                first,
                {
                    "entry_nodes": first.get("exit_nodes", []) or first.get("entry_nodes", []) or ["UNKNOWN"],
                    "exit_nodes": first.get("exit_nodes", []) or ["UNKNOWN"],
                    "size": max(1, int(first.get("size", 2)) // 2),
                    "condensed_size": max(1, int(first.get("condensed_size", 1))),
                },
            ]
            print(
                "[split_translator] warning: only one SESE region found, generated fallback submodel B",
                file=sys.stderr,
            )
        else:
            total_nodes = int(analyze_result.get("nodes", 2))
            half = max(1, total_nodes // 2)
            selected = [
                {
                    "entry_nodes": ["AUTO_ENTRY_A"],
                    "exit_nodes": ["AUTO_EXIT_A"],
                    "size": half,
                    "condensed_size": 1,
                },
                {
                    "entry_nodes": ["AUTO_ENTRY_B"],
                    "exit_nodes": ["AUTO_EXIT_B"],
                    "size": max(1, total_nodes - half),
                    "condensed_size": 1,
                },
            ]
            print(
                "[split_translator] warning: no SESE region found, generated two fallback submodels",
                file=sys.stderr,
            )

    submodels: List[Dict[str, Any]] = []
    for idx, region in enumerate(selected, start=1):
        submodels.append(
            {
                "submodelId": f"{case_id}_sub_{idx}",
                "entryNodes": region.get("entry_nodes", []),
                "exitNodes": region.get("exit_nodes", []),
                "nodeCount": int(region.get("size", 0)),
                "condensedSize": int(region.get("condensed_size", 0)),
            }
        )

    split_point = split_points[0] if split_points else (
        submodels[0]["exitNodes"][0] if submodels[0]["exitNodes"] else "UNKNOWN"
    )

    b2c_path = full_dir / f"{case_id}.b2c"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(translator_root)
    _run(
        ["python3", "-m", "generator.bpmn_to_dsl", str(bpmn_path), "-o", str(b2c_path)],
        cwd=translator_root,
        env=env,
    )

    textx_bin = translator_root / ".venv" / "bin" / "textx"
    full_sol_dir = full_dir / "solidity"
    full_sol_dir.mkdir(parents=True, exist_ok=True)
    _run(
        [
            str(textx_bin),
            "generate",
            str(b2c_path),
            "--target",
            "solidity",
            "--overwrite",
            "-o",
            str(full_sol_dir),
        ],
        cwd=translator_root,
        env=os.environ.copy(),
    )

    split_dsl_path = split_dir / f"{case_id}.split.dsl"
    split_dsl_text = _build_split_dsl(case_id, split_point, submodels[0], submodels[1])
    split_dsl_path.write_text(split_dsl_text, encoding="utf8")

    contract_prefix = _safe_contract_prefix(case_id)
    source_contract_name = f"{contract_prefix}SubmodelA"
    target_contract_name = f"{contract_prefix}SubmodelB"
    source_contract_path = split_contract_dir / f"{source_contract_name}.sol"
    target_contract_path = split_contract_dir / f"{target_contract_name}.sol"
    source_contract_path.write_text(_build_source_contract(source_contract_name), encoding="utf8")
    target_contract_path.write_text(_build_target_contract(target_contract_name), encoding="utf8")

    out = {
        "generatedAt": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "input": {"bpmn": str(bpmn_path)},
        "splitMarkers": {
            "manual": args.split_point_id,
            "autoDetected": auto_markers,
            "selected": split_point,
            "markerKey": args.marker_key,
        },
        "fullArtifacts": {
            "b2cPath": str(b2c_path),
            "solidityDir": str(full_sol_dir),
            "solidityPath": str(full_sol_dir / f"{case_id}.sol"),
        },
        "splitArtifacts": {
            "sesePath": str(sese_path),
            "splitDslPath": str(split_dsl_path),
            "submodels": submodels,
            "contracts": {
                "sourceContractName": source_contract_name,
                "sourceContractPath": str(source_contract_path),
                "targetContractName": target_contract_name,
                "targetContractPath": str(target_contract_path),
            },
        },
    }

    plan_path = case_dir / "split-plan.json"
    plan_path.write_text(json.dumps(out, indent=2), encoding="utf8")
    print(f"split plan written to: {plan_path}")
    print(f"full solidity contract: {out['fullArtifacts']['solidityPath']}")
    print(f"split contracts: {source_contract_path}, {target_contract_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
