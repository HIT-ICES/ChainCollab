from __future__ import annotations

import json
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


def _localname(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def detect_split_points_from_bpmn(
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


def _select_regions(
    regions: List[Dict[str, Any]], split_points: List[str], top_k: int = 2
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


def _extract_flow_node_ids(bpmn_path: Path) -> List[str]:
    tree = ET.parse(str(bpmn_path))
    root = tree.getroot()
    allowed = {
        "choreographytask",
        "subchoreography",
        "task",
        "scripttask",
        "servicetask",
        "businesstask",
        "businessruletask",
        "manualtask",
        "usertask",
        "receivetask",
        "sendtask",
        "callactivity",
        "exclusivegateway",
        "parallelgateway",
        "inclusivegateway",
        "eventbasedgateway",
        "startEvent".lower(),
        "endEvent".lower(),
        "intermediatecatchevent",
        "intermediatethrowevent",
    }
    out: List[str] = []
    seen = set()
    for elem in root.iter():
        elem_id = elem.attrib.get("id")
        if not elem_id:
            continue
        ln = _localname(elem.tag).lower()
        if ln not in allowed:
            continue
        if elem_id in seen:
            continue
        seen.add(elem_id)
        out.append(elem_id)
    return out


def _select_closed_interval_region(
    regions: List[Dict[str, Any]],
    split_point: str,
    merge_point: Optional[str],
) -> Optional[Dict[str, Any]]:
    ranked_small = sorted(
        regions,
        key=lambda x: (
            int(x.get("size", 0)),
            int(x.get("condensed_size", 0)),
        ),
    )
    if merge_point and merge_point == split_point:
        return {
            "entry_nodes": [split_point],
            "exit_nodes": [split_point],
            "nodes": [split_point],
            "size": 1,
            "condensed_size": 1,
        }
    if merge_point:
        candidates = [
            r
            for r in ranked_small
            if split_point in (r.get("nodes") or [])
            and merge_point in (r.get("nodes") or [])
        ]
        if candidates:
            return candidates[0]
    candidates = [r for r in ranked_small if split_point in (r.get("nodes") or [])]
    if candidates:
        return candidates[0]
    return None


def _build_closed_interval_submodels(
    case_id: str,
    bpmn_path: Path,
    analyze_result: Dict[str, Any],
    split_point: str,
    merge_point: Optional[str],
) -> List[Dict[str, Any]]:
    all_nodes = _extract_flow_node_ids(bpmn_path)
    region = _select_closed_interval_region(
        analyze_result.get("regions", []), split_point, merge_point
    )
    if region:
        target_nodes = _dedupe_nodes(list(region.get("nodes", [])))
    else:
        target_nodes = [split_point]
    if not target_nodes:
        target_nodes = [split_point]
    source_nodes = [n for n in all_nodes if n not in set(target_nodes)]
    if not source_nodes:
        source_nodes = [split_point]

    source_sub = {
        "submodelId": f"{case_id}_sub_1",
        "entryNodes": [source_nodes[0]],
        "exitNodes": [source_nodes[-1]],
        "nodeIds": source_nodes,
        "nodeCount": len(source_nodes),
        "condensedSize": max(1, len(source_nodes)),
    }
    target_sub = {
        "submodelId": f"{case_id}_sub_2",
        "entryNodes": [split_point],
        "exitNodes": [merge_point or split_point],
        "nodeIds": target_nodes,
        "nodeCount": len(target_nodes),
        "condensedSize": max(1, len(target_nodes)),
    }
    return [source_sub, target_sub]


def _safe_case_id(path: Path) -> str:
    return path.stem.replace(" ", "_")


def _safe_contract_prefix(raw: str) -> str:
    out = "".join(c if (c.isalnum() or c == "_") else "_" for c in raw)
    if not out or not (out[0].isalpha() or out[0] == "_"):
        out = f"Wf_{out}"
    return out


def _safe_identifier(raw: str, fallback: str = "Node") -> str:
    out = "".join(c if (c.isalnum() or c == "_") else "_" for c in raw)
    if not out:
        out = fallback
    if not (out[0].isalpha() or out[0] == "_"):
        out = f"N_{out}"
    return out


def _dedupe_nodes(nodes: List[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for n in nodes:
        s = str(n or "").strip()
        if not s or s in seen:
            continue
        seen.add(s)
        ordered.append(s)
    return ordered


def _render_node_order_function(node_ids: List[str]) -> str:
    ordered = _dedupe_nodes(node_ids)
    lines: List[str] = [
        "    function _nodeOrder(string memory nodeId) internal pure returns (uint256) {"
    ]
    for idx, node_id in enumerate(ordered):
        lines.append(
            f'        if (keccak256(bytes(nodeId)) == keccak256(bytes("{node_id}"))) return {idx};'
        )
    lines.append('        revert("unknown node id");')
    lines.append("    }")
    return "\n".join(lines)


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


def _render_source_node_methods(node_ids: List[str]) -> str:
    methods: List[str] = []
    for idx, node_id in enumerate(_dedupe_nodes(node_ids), start=1):
        fn_name = _safe_identifier(node_id, fallback=f"Node_{idx}")
        methods.append(
            f"""
    function {fn_name}(bytes32 taskId, bytes32 payloadHash) external {{
        require(taskExists[taskId], "unknown taskId");
        _markNodeExecuted(taskId, "{node_id}", payloadHash);
    }}"""
        )
    return "".join(methods)


def _build_source_contract(contract_name: str, node_ids: List[str]) -> str:
    node_methods = _render_source_node_methods(node_ids)
    node_order_fn = _render_node_order_function(node_ids)
    return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract {contract_name} {{
    struct HandoffTask {{
        address requester;
        bytes32 payloadHash;
        uint256 nonce;
        uint256 createdAt;
    }}

    struct TaskRuntime {{
        uint256 nextOrder;
        uint256 executedCount;
        bytes32 lastPayloadHash;
        address lastCaller;
        uint256 updatedAt;
    }}

    uint256 public nextNonce;
    mapping(bytes32 => bool) public taskExists;
    mapping(bytes32 => HandoffTask) private tasks;
    mapping(bytes32 => TaskRuntime) private taskRuntime;
    mapping(bytes32 => mapping(bytes32 => bool)) private nodeExecuted;

    event HandoffRequested(
        bytes32 indexed taskId,
        address indexed requester,
        bytes32 payloadHash,
        uint256 nonce,
        uint256 sourceChainId
    );
    event NodeExecuted(
        bytes32 indexed taskId,
        string nodeId,
        bytes32 payloadHash,
        address indexed caller,
        uint256 at
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
        taskRuntime[taskId] = TaskRuntime({{
            nextOrder: 0,
            executedCount: 0,
            lastPayloadHash: payloadHash,
            lastCaller: msg.sender,
            updatedAt: block.timestamp
        }});
        emit HandoffRequested(taskId, msg.sender, payloadHash, nonce, block.chainid);
    }}

    function getTask(bytes32 taskId) external view returns (bool exists, HandoffTask memory task) {{
        exists = taskExists[taskId];
        task = tasks[taskId];
    }}

    function getTaskRuntime(bytes32 taskId) external view returns (TaskRuntime memory runtime) {{
        runtime = taskRuntime[taskId];
    }}

    function isNodeExecuted(bytes32 taskId, string calldata nodeId) external view returns (bool) {{
        bytes32 key = keccak256(bytes(nodeId));
        return nodeExecuted[taskId][key];
    }}

    function executeBatch(
        bytes32 taskId,
        bytes32 payloadHash,
        string[] calldata nodeIds
    ) external {{
        require(taskExists[taskId], "unknown taskId");
        require(nodeIds.length > 0, "empty node batch");
        for (uint256 i = 0; i < nodeIds.length; i++) {{
            _markNodeExecuted(taskId, nodeIds[i], payloadHash);
        }}
    }}

    function _markNodeExecuted(bytes32 taskId, string memory nodeId, bytes32 payloadHash) internal {{
        require(payloadHash == tasks[taskId].payloadHash, "payload hash mismatch");
        bytes32 key = keccak256(bytes(nodeId));
        require(!nodeExecuted[taskId][key], "node already executed");

        TaskRuntime storage rt = taskRuntime[taskId];
        uint256 expectedOrder = _nodeOrder(nodeId);

        nodeExecuted[taskId][key] = true;
        if (expectedOrder >= rt.nextOrder) {{
            rt.nextOrder = expectedOrder + 1;
        }}
        unchecked {{
            rt.executedCount += 1;
        }}
        rt.lastPayloadHash = payloadHash;
        rt.lastCaller = msg.sender;
        rt.updatedAt = block.timestamp;
        emit NodeExecuted(taskId, nodeId, payloadHash, msg.sender, block.timestamp);
    }}
{node_order_fn}
{node_methods}
}}
"""


def _render_target_node_methods(node_ids: List[str]) -> str:
    methods: List[str] = []
    for idx, node_id in enumerate(_dedupe_nodes(node_ids), start=1):
        fn_name = _safe_identifier(node_id, fallback=f"Node_{idx}")
        methods.append(
            f"""
    function {fn_name}(bytes32 taskId) external {{
        require(deliveries[taskId].processed, "handoff not accepted");
        _markNodeExecuted(taskId, "{node_id}", deliveries[taskId].payloadHash);
    }}"""
        )
    return "".join(methods)


def _build_target_contract(contract_name: str, node_ids: List[str]) -> str:
    node_methods = _render_target_node_methods(node_ids)
    node_order_fn = _render_node_order_function(node_ids)
    return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract {contract_name} {{
    enum RelayStatus {{
        Rejected,
        Pending,
        Accepted,
        AlreadyProcessed
    }}

    struct Delivery {{
        bool processed;
        bytes32 msgId;
        bytes32 payloadHash;
        address relayer;
        uint256 sourceChainId;
        uint256 targetChainId;
        address sourceContract;
        uint256 confirmations;
        uint256 firstSeenAt;
        uint256 processedAt;
    }}

    struct TaskRuntime {{
        uint256 nextOrder;
        uint256 executedCount;
        bytes32 lastPayloadHash;
        address lastCaller;
        uint256 updatedAt;
    }}

    address public owner;
    uint256 public processedCount;
    uint256 public confirmationThreshold = 1;
    mapping(address => bool) public allowedRelayers;
    mapping(bytes32 => Delivery) private deliveries;
    mapping(bytes32 => bool) private processedMsgIds;
    mapping(bytes32 => TaskRuntime) private taskRuntime;
    mapping(bytes32 => mapping(bytes32 => bool)) private nodeExecuted;
    mapping(bytes32 => mapping(address => bool)) private confirmedBy;
    bytes32 private constant RELAY_DOMAIN = keccak256("BPMN_SPLIT_RELAY_V1");

    event RelayerUpdated(address indexed relayer, bool allowed);
    event ConfirmationThresholdUpdated(uint256 threshold);
    event ConfirmationAdded(
        bytes32 indexed taskId,
        bytes32 indexed msgId,
        address indexed signer,
        uint256 confirmations
    );
    event ConfirmationPending(
        bytes32 indexed taskId,
        bytes32 indexed msgId,
        uint256 confirmations,
        uint256 threshold
    );
    event HandoffAlreadyProcessed(bytes32 indexed taskId, bytes32 indexed msgId);
    event HandoffAccepted(
        bytes32 indexed taskId,
        bytes32 indexed msgId,
        bytes32 payloadHash,
        address indexed relayer,
        uint256 sourceChainId,
        address sourceContract,
        uint256 confirmations
    );
    event NodeExecuted(
        bytes32 indexed taskId,
        string nodeId,
        bytes32 payloadHash,
        address indexed caller,
        uint256 at
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

    function setConfirmationThreshold(uint256 threshold) external onlyOwner {{
        require(threshold > 0, "threshold must be > 0");
        confirmationThreshold = threshold;
        emit ConfirmationThresholdUpdated(threshold);
    }}

    function acceptHandoff(
        bytes32 taskId,
        bytes32 payloadHash,
        uint256 sourceChainId,
        address sourceContract,
        bytes calldata signature
    ) external returns (RelayStatus status) {{
        bytes[] memory signatures = new bytes[](1);
        signatures[0] = signature;
        (status,,) = acceptHandoffWithSignatures(
            taskId,
            payloadHash,
            sourceChainId,
            sourceContract,
            block.chainid,
            signatures
        );
    }}

    function acceptHandoff(
        bytes32 taskId,
        bytes32 payloadHash,
        uint256 sourceChainId,
        address sourceContract,
        uint256 targetChainId,
        bytes[] calldata signatures
    ) external returns (RelayStatus status, bytes32 msgId, uint256 confirmations) {{
        return acceptHandoffWithSignatures(
            taskId,
            payloadHash,
            sourceChainId,
            sourceContract,
            targetChainId,
            signatures
        );
    }}

    function acceptHandoffWithSignatures(
        bytes32 taskId,
        bytes32 payloadHash,
        uint256 sourceChainId,
        address sourceContract,
        uint256 targetChainId,
        bytes[] memory signatures
    ) public returns (RelayStatus status, bytes32 msgId, uint256 confirmations) {{
        if (taskId == bytes32(0) || payloadHash == bytes32(0) || sourceContract == address(0)) {{
            return (RelayStatus.Rejected, bytes32(0), 0);
        }}
        if (targetChainId != block.chainid) {{
            return (RelayStatus.Rejected, bytes32(0), 0);
        }}
        if (!allowedRelayers[msg.sender]) {{
            return (RelayStatus.Rejected, bytes32(0), 0);
        }}

        msgId = _buildMessageId(taskId, payloadHash, sourceChainId, sourceContract, targetChainId);
        if (processedMsgIds[msgId]) {{
            emit HandoffAlreadyProcessed(taskId, msgId);
            return (RelayStatus.AlreadyProcessed, msgId, deliveries[taskId].confirmations);
        }}
        Delivery storage d = deliveries[taskId];
        if (d.firstSeenAt == 0) {{
            deliveries[taskId] = Delivery({{
                processed: false,
                msgId: msgId,
                payloadHash: payloadHash,
                relayer: address(0),
                sourceChainId: sourceChainId,
                targetChainId: targetChainId,
                sourceContract: sourceContract,
                confirmations: 0,
                firstSeenAt: block.timestamp,
                processedAt: 0
            }});
            d = deliveries[taskId];
        }} else {{
            if (
                d.msgId != msgId ||
                d.payloadHash != payloadHash ||
                d.sourceChainId != sourceChainId ||
                d.targetChainId != targetChainId ||
                d.sourceContract != sourceContract
            ) {{
                return (RelayStatus.Rejected, msgId, d.confirmations);
            }}
        }}

        if (d.processed) {{
            emit HandoffAlreadyProcessed(taskId, d.msgId);
            return (RelayStatus.AlreadyProcessed, d.msgId, d.confirmations);
        }}

        bytes32 digest = _toEthSignedMessageHash(
            _relayDigest(taskId, payloadHash, sourceChainId, sourceContract, targetChainId)
        );
        uint256 added = _collectValidConfirmations(
            taskId,
            d.msgId,
            digest,
            d.confirmations,
            signatures
        );
        if (added > 0) {{
            d.confirmations += added;
        }}
        confirmations = d.confirmations;
        if (confirmations < confirmationThreshold) {{
            emit ConfirmationPending(taskId, d.msgId, confirmations, confirmationThreshold);
            return (RelayStatus.Pending, d.msgId, confirmations);
        }}

        d.processed = true;
        processedMsgIds[d.msgId] = true;
        d.relayer = msg.sender;
        d.processedAt = block.timestamp;
        taskRuntime[taskId] = TaskRuntime({{
            nextOrder: 0,
            executedCount: 0,
            lastPayloadHash: payloadHash,
            lastCaller: msg.sender,
            updatedAt: block.timestamp
        }});
        unchecked {{
            processedCount += 1;
        }}
        emit HandoffAccepted(
            taskId,
            d.msgId,
            payloadHash,
            msg.sender,
            sourceChainId,
            sourceContract,
            confirmations
        );
        return (RelayStatus.Accepted, d.msgId, confirmations);
    }}

    function isProcessed(bytes32 taskId) external view returns (bool) {{
        return deliveries[taskId].processed;
    }}

    function isMessageProcessed(bytes32 msgId) external view returns (bool) {{
        return processedMsgIds[msgId];
    }}

    function getDelivery(bytes32 taskId) external view returns (Delivery memory) {{
        return deliveries[taskId];
    }}

    function getTaskRuntime(bytes32 taskId) external view returns (TaskRuntime memory runtime) {{
        runtime = taskRuntime[taskId];
    }}

    function isNodeExecuted(bytes32 taskId, string calldata nodeId) external view returns (bool) {{
        bytes32 key = keccak256(bytes(nodeId));
        return nodeExecuted[taskId][key];
    }}

    function executeBatch(bytes32 taskId, string[] calldata nodeIds) external {{
        require(deliveries[taskId].processed, "handoff not accepted");
        require(nodeIds.length > 0, "empty node batch");
        bytes32 payloadHash = deliveries[taskId].payloadHash;
        for (uint256 i = 0; i < nodeIds.length; i++) {{
            _markNodeExecuted(taskId, nodeIds[i], payloadHash);
        }}
    }}

    function isConfirmedBy(bytes32 taskId, address signer) external view returns (bool) {{
        return confirmedBy[taskId][signer];
    }}

    function _markNodeExecuted(bytes32 taskId, string memory nodeId, bytes32 payloadHash) internal {{
        require(payloadHash == deliveries[taskId].payloadHash, "payload hash mismatch");
        bytes32 key = keccak256(bytes(nodeId));
        require(!nodeExecuted[taskId][key], "node already executed");

        TaskRuntime storage rt = taskRuntime[taskId];
        uint256 expectedOrder = _nodeOrder(nodeId);

        nodeExecuted[taskId][key] = true;
        if (expectedOrder >= rt.nextOrder) {{
            rt.nextOrder = expectedOrder + 1;
        }}
        unchecked {{
            rt.executedCount += 1;
        }}
        rt.lastPayloadHash = payloadHash;
        rt.lastCaller = msg.sender;
        rt.updatedAt = block.timestamp;
        emit NodeExecuted(taskId, nodeId, payloadHash, msg.sender, block.timestamp);
    }}

    function _buildMessageId(
        bytes32 taskId,
        bytes32 payloadHash,
        uint256 sourceChainId,
        address sourceContract,
        uint256 targetChainId
    ) internal view returns (bytes32) {{
        return keccak256(
            abi.encodePacked(
                RELAY_DOMAIN,
                address(this),
                targetChainId,
                sourceChainId,
                sourceContract,
                taskId,
                payloadHash
            )
        );
    }}

    function _relayDigest(
        bytes32 taskId,
        bytes32 payloadHash,
        uint256 sourceChainId,
        address sourceContract,
        uint256 targetChainId
    ) internal view returns (bytes32) {{
        return _buildMessageId(taskId, payloadHash, sourceChainId, sourceContract, targetChainId);
    }}

    function _collectValidConfirmations(
        bytes32 taskId,
        bytes32 msgId,
        bytes32 digest,
        uint256 baseConfirmations,
        bytes[] memory signatures
    ) internal returns (uint256 added) {{
        if (signatures.length == 0) {{
            return 0;
        }}
        for (uint256 i = 0; i < signatures.length; i++) {{
            address signer = _tryRecoverSigner(digest, signatures[i]);
            if (signer == address(0)) {{
                continue;
            }}
            if (!allowedRelayers[signer]) {{
                continue;
            }}
            if (confirmedBy[taskId][signer]) {{
                continue;
            }}
            confirmedBy[taskId][signer] = true;
            unchecked {{
                added += 1;
            }}
            emit ConfirmationAdded(taskId, msgId, signer, baseConfirmations + added);
        }}
    }}

    function _toEthSignedMessageHash(bytes32 hash) internal pure returns (bytes32) {{
        return keccak256(abi.encodePacked("\\x19Ethereum Signed Message:\\n32", hash));
    }}

    function _tryRecoverSigner(bytes32 digest, bytes memory signature) internal pure returns (address) {{
        if (signature.length != 65) {{
            return address(0);
        }}
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
        if (!(v == 27 || v == 28)) {{
            return address(0);
        }}
        address recovered = ecrecover(digest, v, r, s);
        return recovered;
    }}
{node_order_fn}
{node_methods}
}}
"""


def _resolve_textx_bin(translator_root: Path) -> Optional[Path]:
    venv_bin = translator_root / ".venv" / "bin" / "textx"
    if venv_bin.exists():
        return venv_bin
    found = shutil.which("textx")
    if found:
        return Path(found)
    return None


@dataclass
class SplitModeConfig:
    bpmn_path: Path
    b2c_output_path: Path
    translator_root: Path
    split_output_dir: Path
    split_contract_dir: Optional[Path]
    split_point_ids: List[str]
    merge_point_id: Optional[str]
    split_marker_key: str
    contract_name: Optional[str]


def generate_split_mode_artifacts(config: SplitModeConfig) -> Dict[str, Any]:
    from subgraph_analysis.analyze_bpmn_sese import analyze_bpmn  # type: ignore

    case_id = config.contract_name or _safe_case_id(config.bpmn_path)
    case_id = case_id.replace(" ", "_")

    case_dir = config.split_output_dir / case_id
    split_dir = case_dir / "split"
    split_dir.mkdir(parents=True, exist_ok=True)
    if config.split_contract_dir:
        contract_dir = config.split_contract_dir
    else:
        contract_dir = split_dir / "contracts"
    contract_dir.mkdir(parents=True, exist_ok=True)

    sese_path = split_dir / f"{case_id}.sese.json"
    analyze_result = analyze_bpmn(config.bpmn_path, sese_path)

    auto_markers = detect_split_points_from_bpmn(
        config.bpmn_path, marker_key=config.split_marker_key
    )
    split_points = [
        *config.split_point_ids,
        *[x for x in auto_markers if x not in config.split_point_ids],
    ]

    split_point = (
        split_points[0]
        if split_points
        else "UNKNOWN"
    )
    merge_point = (
        config.merge_point_id.strip() if config.merge_point_id else None
    ) or split_point

    submodels = _build_closed_interval_submodels(
        case_id=case_id,
        bpmn_path=config.bpmn_path,
        analyze_result=analyze_result,
        split_point=split_point,
        merge_point=merge_point,
    )

    split_dsl_path = split_dir / f"{case_id}.split.dsl"
    split_dsl_path.write_text(
        _build_split_dsl(case_id, split_point, submodels[0], submodels[1]),
        encoding="utf8",
    )

    contract_prefix = _safe_contract_prefix(case_id)
    source_contract_name = f"{contract_prefix}SubmodelA"
    target_contract_name = f"{contract_prefix}SubmodelB"
    source_contract_path = contract_dir / f"{source_contract_name}.sol"
    target_contract_path = contract_dir / f"{target_contract_name}.sol"
    source_contract_path.write_text(
        _build_source_contract(source_contract_name, submodels[0].get("nodeIds", [])),
        encoding="utf8",
    )
    target_contract_path.write_text(
        _build_target_contract(target_contract_name, submodels[1].get("nodeIds", [])),
        encoding="utf8",
    )

    full_sol_dir = case_dir / "full_solidity"
    full_sol_dir.mkdir(parents=True, exist_ok=True)
    full_sol_path = full_sol_dir / f"{case_id}.sol"
    textx_bin = _resolve_textx_bin(config.translator_root)
    if textx_bin:
        proc = subprocess.run(
            [
                str(textx_bin),
                "generate",
                str(config.b2c_output_path),
                "--target",
                "solidity",
                "--overwrite",
                "-o",
                str(full_sol_dir),
            ],
            cwd=str(config.translator_root),
            env=os.environ.copy(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            full_sol_path = Path("")
    else:
        full_sol_path = Path("")

    out: Dict[str, Any] = {
        "generatedAt": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "input": {"bpmn": str(config.bpmn_path)},
        "splitMarkers": {
            "manual": config.split_point_ids,
            "autoDetected": auto_markers,
            "selected": split_point,
            "mergeSelected": merge_point,
            "markerKey": config.split_marker_key,
        },
        "fullArtifacts": {
            "b2cPath": str(config.b2c_output_path),
            "solidityDir": str(full_sol_dir),
            "solidityPath": str(full_sol_path) if full_sol_path else "",
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
    out["planPath"] = str(plan_path)
    return out
