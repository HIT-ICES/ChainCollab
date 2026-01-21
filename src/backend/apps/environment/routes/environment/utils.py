import logging

from requests import post
from apps.infra.models import Agent
from apps.fabric.models import ResourceSet, FabricResourceSet, Node
from apps.environment.models import Environment
from apps.core.models import Consortium, Membership, LoleidoOrganization
from apps.api.config import CURRENT_IP

from common.enums import FabricCAOrgType, FabricNodeType

LOG = logging.getLogger(__name__)


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

    url = f"http://{CURRENT_IP}:8000/api/v1/environments/{env_id}/chaincodes/package"
    LOG.info("Chaincode action=package env=%s name=%s", env_id, chaincode_name)
    res = post(
        url,
        data=data,
        files=files,
        headers={"Authorization": auth},
    )
    if not str(res.status_code).startswith("2"):
        LOG.warning(
            "Chaincode action=package failed env=%s status=%s", env_id, res.status_code
        )
        raise Exception(f"Package chaincode failed: {res.status_code} {res.text}")
    try:
        payload = res.json()
    except Exception:
        raise Exception(f"Package chaincode failed: invalid JSON {res.text}")
    chaincode_id = payload.get("data", {}).get("id") if isinstance(payload, dict) else None
    if not chaincode_id:
        raise Exception(f"Package chaincode failed: missing id in response {payload}")
    return chaincode_id


def installChaincodeForEnv(env_id: str, chaincode_id: str, auth: str):
    peers = get_all_peer_of_env(env_id, including_system=True)
    data = {"id": chaincode_id, "peer_node_list": [str(peer.id) for peer in peers]}
    url = f"http://{CURRENT_IP}:8000/api/v1/environments/{env_id}/chaincodes/install"
    LOG.info("Chaincode action=install env=%s chaincode_id=%s peers=%s", env_id, chaincode_id, len(peers))
    res = post(
        url,
        json=data,
        headers={"Authorization": auth, "Content-Type": "application/json"},
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
        url = f"http://{CURRENT_IP}:8000/api/v1/environments/{env_id}/chaincodes/approve_for_my_org"
        LOG.info("Chaincode action=approve env=%s resource_set=%s", env_id, resourceSet.id)
        res = post(
            url,
            data=data,
            headers={"Authorization": auth},
        )
        all_res.append(res)
    return all_res


def commmitChaincodeForEnv(
    env_id: str, channel_name: str, chaincode_name: str, auth: str
):
    resourceSets = get_all_resource_set_of_env(env_id, including_system=True)
    if not resourceSets:
        return None
    chosen_resource_set = resourceSets[0]
    data = {
        "chaincode_name": chaincode_name,
        "chaincode_version": "1.0",
        "channel_name": channel_name,
        "resource_set_id": chosen_resource_set.id,
        "sequence": 1,
    }
    url = f"http://{CURRENT_IP}:8000/api/v1/environments/{env_id}/chaincodes/commit"
    LOG.info("Chaincode action=commit env=%s resource_set=%s", env_id, chosen_resource_set.id)
    res = post(
        url,
        data=data,
        headers={"Authorization": auth},
    )
    return res
