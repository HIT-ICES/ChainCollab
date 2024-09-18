from requests import post
from api.models import (
    Consortium,
    Environment,
    ResourceSet,
    Agent,
    Membership,
    FabricResourceSet,
    LoleidoOrganization,
    Node,
)
from api.config import CURRENT_IP

from api.common.enums import FabricCAOrgType, FabricNodeType


def get_all_peer_of_env(env_id: str, including_system: bool = False) -> list:
    try:
        target_env = Environment.objects.get(id=env_id)
    except Environment.DoesNotExist:
        return []

    resourceSets = target_env.resource_sets.all()
    peers = []
    for resourceSet in resourceSets:
        try:
            fabric_resource_set = FabricResourceSet.objects.get(
                resource_set=resourceSet
            )
        except FabricResourceSet.DoesNotExist:
            continue
        if (
            not including_system
            and fabric_resource_set.org_type != FabricCAOrgType.USERORG
        ):
            continue
        _peers = fabric_resource_set.node.filter(type="peer")
        peers.extend(_peers)
    return peers


def get_all_resource_set_of_env(env_id: str, including_system: bool = False) -> list:
    try:
        target_env = Environment.objects.get(id=env_id)
    except Environment.DoesNotExist:
        return []

    resourceSets = target_env.resource_sets.all()
    if not including_system:
        resourceSets = resourceSets.exclude(name="system")
    return resourceSets


def packageChaincodeForEnv(
    env_id: str,
    file_path: str,
    chaincode_name: str,
    version: str,
    org_id: str,
    auth: str,
    language: str = "golang",
) -> str:
    with open(file_path, "rb") as f:
        chaincode = f.read()
    data = {
        "name": chaincode_name,
        "version": version,
        "language": language,
        "org_id": org_id,
    }
    files = {
        "file": (
            chaincode_name + ".tar.gz",
            chaincode,
            "application/octet-stream",
        )
    }

    res = post(
        f"http://{CURRENT_IP}:8000/api/v1/environments/{env_id}/chaincodes/package",
        data=data,
        files=files,
        headers={"Authorization": auth},
    )
    return res.json()["data"]["id"]


def installChaincodeForEnv(env_id: str, chaincode_id: str, auth: str):
    peers = get_all_peer_of_env(env_id, including_system=True)
    data = {"id": chaincode_id, "peer_node_list": [str(peer.id) for peer in peers]}
    res = post(
        f"http://{CURRENT_IP}:8000/api/v1/environments/{env_id}/chaincodes/install",
        data=data,
        headers={"Authorization": auth},
    )

    return res


def approveChaincodeForEnv(env_id: str, channel_name, chaincode_name: str, auth: str):
    resourceSets = get_all_resource_set_of_env(env_id, including_system=True)
    data = {
        "channel_name": channel_name,
        "chaincode_name": chaincode_name,
        "chaincode_version": "1.0",
        "sequence": 1,
    }

    all_res = []
    for resourceSet in resourceSets:
        data["resource_set_id"] = resourceSet.id
        res = post(
            f"http://{CURRENT_IP}:8000/api/v1/environments/{env_id}/chaincodes/approve_for_my_org",
            data=data,
            headers={"Authorization": auth},
        )
        all_res.append(res)
    return all_res
