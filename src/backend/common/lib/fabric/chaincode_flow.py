import logging

from apps.api.config import DEFAULT_CHANNEL_NAME
from apps.environment.routes.environment.utils import (
    approveChaincodeForEnv,
    commmitChaincodeForEnv,
    installChaincodeForEnv,
    packageChaincodeForEnv,
)


def install_fabric_chaincode_flow(
    env,
    file_path: str,
    chaincode_name: str,
    auth: str,
    org_id: str,
    version: str = "1.0",
    language: str = "golang",
    channel_name: str = DEFAULT_CHANNEL_NAME,
    status_field: str | None = None,
) -> str:
    LOG = logging.getLogger("api")
    LOG.info(
        "Chaincode flow start env=%s name=%s version=%s lang=%s channel=%s file=%s org=%s",
        env.id,
        chaincode_name,
        version,
        language,
        channel_name,
        file_path,
        org_id,
    )
    chaincode_id = packageChaincodeForEnv(
        env_id=env.id,
        file_path=file_path,
        chaincode_name=chaincode_name,
        version=version,
        org_id=org_id,
        auth=auth,
        language=language,
    )
    LOG.info("Chaincode flow package done env=%s name=%s id=%s", env.id, chaincode_name, chaincode_id)

    installChaincodeForEnv(
        env_id=env.id,
        chaincode_id=chaincode_id,
        auth=auth,
    )
    LOG.info("Chaincode flow install done env=%s name=%s id=%s", env.id, chaincode_name, chaincode_id)

    approveChaincodeForEnv(
        env_id=env.id,
        channel_name=channel_name,
        chaincode_name=chaincode_name,
        auth=auth,
    )
    LOG.info("Chaincode flow approve done env=%s name=%s channel=%s", env.id, chaincode_name, channel_name)

    commmitChaincodeForEnv(
        env_id=env.id,
        channel_name=channel_name,
        chaincode_name=chaincode_name,
        auth=auth,
    )
    LOG.info("Chaincode flow commit done env=%s name=%s channel=%s", env.id, chaincode_name, channel_name)

    if status_field:
        setattr(env, status_field, "CHAINCODEINSTALLED")
        env.save(update_fields=[status_field])
        LOG.info("Chaincode flow status updated env=%s field=%s", env.id, status_field)

    LOG.info("Chaincode flow complete env=%s name=%s id=%s", env.id, chaincode_name, chaincode_id)
    return chaincode_id
