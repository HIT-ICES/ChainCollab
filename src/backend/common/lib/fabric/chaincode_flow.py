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
    chaincode_id = packageChaincodeForEnv(
        env_id=env.id,
        file_path=file_path,
        chaincode_name=chaincode_name,
        version=version,
        org_id=org_id,
        auth=auth,
        language=language,
    )

    installChaincodeForEnv(
        env_id=env.id,
        chaincode_id=chaincode_id,
        auth=auth,
    )

    approveChaincodeForEnv(
        env_id=env.id,
        channel_name=channel_name,
        chaincode_name=chaincode_name,
        auth=auth,
    )

    commmitChaincodeForEnv(
        env_id=env.id,
        channel_name=channel_name,
        chaincode_name=chaincode_name,
        auth=auth,
    )

    if status_field:
        setattr(env, status_field, "CHAINCODEINSTALLED")
        env.save(update_fields=[status_field])

    return chaincode_id
