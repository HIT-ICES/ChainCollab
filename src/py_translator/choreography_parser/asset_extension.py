import json
import xml.etree.ElementTree as ET

from .elements import Task


BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
ABC_NS = "http://chaincollab.assetblockcollab/schema/abc"


def _split_refs(value):
    return [item for item in (value or "").split() if item]


def _bool_attr(value):
    if isinstance(value, bool):
        return value
    return str(value or "").lower() == "true"


def _local_name(element):
    return element.tag.rsplit("}", 1)[-1]


def _namespace(element):
    if element.tag.startswith("{"):
        return element.tag[1:].split("}", 1)[0]
    return ""


def _find_children_by_local_name(element, name, namespace=None):
    return [
        child
        for child in element
        if _local_name(child).lower() == name.lower()
        and (namespace is None or _namespace(child) == namespace)
    ]


def _find_first_text(element, name):
    for child in _find_children_by_local_name(element, name):
        if child.text:
            return child.text
    return ""


def _build_parent_map(root):
    return {child: parent for parent in root.iter() for child in parent}


def _closest_parent_id(element, parent_map, names):
    expected_names = {name.lower() for name in names}
    parent = parent_map.get(element)
    while parent is not None:
        if _namespace(parent) == BPMN_NS and _local_name(parent).lower() in expected_names:
            return parent.attrib.get("id", "")
        parent = parent_map.get(parent)
    return ""


def parse_assets(root):
    assets = {}
    for asset in root.iter():
        local_name = _local_name(asset).lower()
        namespace = _namespace(asset)
        if namespace == ABC_NS and local_name == "asset":
            asset_id = asset.attrib.get("id")
            if not asset_id:
                continue

            data = {
                "assetType": asset.attrib.get("assetType", ""),
                "tokenType": asset.attrib.get("tokenType", ""),
                "tokenName": asset.attrib.get("tokenName", ""),
                "tokenId": asset.attrib.get("tokenId", ""),
                "tokenURL": asset.attrib.get("tokenURL", ""),
            }
            if "tokenHasExistInERC" in asset.attrib:
                data["tokenHasExistInERC"] = _bool_attr(asset.attrib.get("tokenHasExistInERC"))
            assets[asset_id] = {key: value for key, value in data.items() if value != ""}
            continue

        if namespace == BPMN_NS and local_name == "dataobjectreference":
            asset_id = asset.attrib.get("id")
            if not asset_id:
                continue

            doc_text = _find_first_text(asset, "documentation")
            if not doc_text:
                continue
            try:
                doc_data = json.loads(doc_text)
            except json.JSONDecodeError:
                continue

            data = {}
            for key in ["assetType", "tokenType", "tokenName", "tokenId", "tokenURL", "refTokenIds"]:
                if doc_data.get(key):
                    data[key] = doc_data[key]
            if "tokenHasExistInERC" in doc_data:
                data["tokenHasExistInERC"] = _bool_attr(doc_data.get("tokenHasExistInERC"))
            if data:
                assets[asset_id] = data
    return assets


def parse_asset_operation(choreo_task_element):
    for extension_elements in _find_children_by_local_name(choreo_task_element, "extensionElements", BPMN_NS):
        asset_operations = [
            child
            for child in extension_elements
            if _namespace(child) == ABC_NS and _local_name(child).lower() == "assetoperation"
        ]
        for asset_operation in asset_operations:
            outputs = {}
            for output in asset_operation:
                if _namespace(output) != ABC_NS or _local_name(output).lower() != "output":
                    continue
                name = output.attrib.get("name")
                if not name:
                    continue
                outputs[name] = {
                    "type": output.attrib.get("type", ""),
                    "dataType": output.attrib.get("dataType", "string"),
                }

            return {
                "operation": asset_operation.attrib.get("operation", ""),
                "inputAssetRefs": _split_refs(asset_operation.attrib.get("inputAssetRefs")),
                "outputAssetRefs": _split_refs(asset_operation.attrib.get("outputAssetRefs")),
                "recipientRefs": _split_refs(asset_operation.attrib.get("recipientRefs")),
                "tokenNumber": asset_operation.attrib.get("tokenNumber", ""),
                "outputs": outputs,
            }
    return None


def parse_asset_associations(root, assets_by_id):
    references_by_task = {}
    parent_map = _build_parent_map(root)
    for association in root.iter():
        if _namespace(association) != BPMN_NS:
            continue
        association_type = _local_name(association).lower()
        if association_type not in [
            "association",
            "datainputassociation",
            "dataoutputassociation",
            "sequenceflow",
        ]:
            continue

        target_ref = association.attrib.get("targetRef", "") or _find_first_text(association, "targetRef")
        source_refs = _split_refs(association.attrib.get("sourceRef", ""))
        if not source_refs:
            source_refs = [
                source_ref.text
                for source_ref in _find_children_by_local_name(association, "sourceRef")
                if source_ref.text
            ]

        for source_ref in source_refs:
            if source_ref in assets_by_id and target_ref:
                references_by_task.setdefault(target_ref, {"inputAssetRefs": [], "outputAssetRefs": []})
                references_by_task[target_ref]["inputAssetRefs"].append(source_ref)
            if target_ref in assets_by_id and source_ref:
                references_by_task.setdefault(source_ref, {"inputAssetRefs": [], "outputAssetRefs": []})
                references_by_task[source_ref]["outputAssetRefs"].append(target_ref)

        parent_task_id = _closest_parent_id(association, parent_map, ["task", "choreographyTask"])
        if not parent_task_id:
            continue

        if association_type == "datainputassociation":
            for source_ref in source_refs:
                if source_ref in assets_by_id:
                    references_by_task.setdefault(parent_task_id, {"inputAssetRefs": [], "outputAssetRefs": []})
                    references_by_task[parent_task_id]["inputAssetRefs"].append(source_ref)
        elif association_type == "dataoutputassociation" and target_ref in assets_by_id:
            references_by_task.setdefault(parent_task_id, {"inputAssetRefs": [], "outputAssetRefs": []})
            references_by_task[parent_task_id]["outputAssetRefs"].append(target_ref)
    return references_by_task


def apply_association_fallback(asset_operation, association_refs):
    if not association_refs:
        return asset_operation

    merged = dict(asset_operation)
    if not merged.get("inputAssetRefs"):
        merged["inputAssetRefs"] = association_refs.get("inputAssetRefs", [])
    if not merged.get("outputAssetRefs"):
        merged["outputAssetRefs"] = association_refs.get("outputAssetRefs", [])
    return merged


def derive_caller_and_callee(choreo_task_element, asset_operation):
    caller = choreo_task_element.attrib.get("initiatingParticipantRef", "")
    operation = asset_operation.get("operation", "")

    if operation in ["mint", "burn", "query", "branch", "merge"]:
        return caller, []

    if operation in ["grant usage rights", "revoke usage rights"]:
        return caller, asset_operation.get("recipientRefs", [])

    if operation in ["Transfer", "transfer"]:
        participants = [
            participant_ref.text
            for participant_ref in choreo_task_element.findall(f"./{{{BPMN_NS}}}participantRef")
            if participant_ref.text
        ]
        return caller, [participant for participant in participants if participant != caller]

    return caller, []


def build_legacy_asset_doc(choreo_task_element, asset_operation, assets_by_id):
    operation = asset_operation.get("operation", "")
    create_operations = ["mint", "branch", "merge"]
    refs = (
        asset_operation.get("outputAssetRefs", [])
        if operation in create_operations
        else asset_operation.get("inputAssetRefs", [])
    )
    if not refs:
        return None

    main_asset = assets_by_id.get(refs[0])
    if not main_asset:
        return None

    result = {}
    for key in ["assetType", "tokenType", "tokenName", "tokenId", "tokenURL", "tokenHasExistInERC"]:
        if key in main_asset and main_asset[key] not in ["", None]:
            result[key] = main_asset[key]

    result["operation"] = operation
    caller, callee = derive_caller_and_callee(choreo_task_element, asset_operation)
    result["caller"] = caller
    result["callee"] = callee

    if asset_operation.get("tokenNumber"):
        result["tokenNumber"] = asset_operation["tokenNumber"]

    if asset_operation.get("outputs"):
        result["outputs"] = asset_operation["outputs"]

    if operation in ["branch", "merge"]:
        ref_token_ids = []
        for asset_id in asset_operation.get("inputAssetRefs", []):
            token_id = assets_by_id.get(asset_id, {}).get("tokenId")
            if token_id:
                ref_token_ids.append(token_id)
        if ref_token_ids:
            result["refTokenIds"] = ref_token_ids

    return result


def create_asset_task_projections(graph, root):
    assets_by_id = parse_assets(root)
    asset_refs_by_task = parse_asset_associations(root, assets_by_id)
    projections = []

    for choreo_task_element in root.findall(f".//{{{BPMN_NS}}}choreographyTask"):
        asset_operation = parse_asset_operation(choreo_task_element)
        if not asset_operation or not asset_operation.get("operation"):
            continue

        original_task = graph.get_element_with_id(choreo_task_element.attrib["id"])
        if original_task is not None:
            original_task.is_asset_task = True
            original_task.asset_operation = asset_operation

        asset_operation = apply_association_fallback(
            asset_operation,
            asset_refs_by_task.get(choreo_task_element.attrib["id"]),
        )

        legacy_doc = build_legacy_asset_doc(choreo_task_element, asset_operation, assets_by_id)
        if legacy_doc is None:
            continue

        incoming = choreo_task_element.find(f"./{{{BPMN_NS}}}incoming")
        outgoing = choreo_task_element.find(f"./{{{BPMN_NS}}}outgoing")
        projection = Task(
            graph,
            choreo_task_element.attrib["id"],
            choreo_task_element.attrib.get("name", ""),
            incoming=incoming.text if incoming is not None and incoming.text else "",
            outgoing=outgoing.text if outgoing is not None and outgoing.text else "",
            documentation=json.dumps(legacy_doc),
        )
        projection.is_asset_projection = True
        projections.append(projection)

    return projections
