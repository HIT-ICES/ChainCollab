import api from './apiConfig';

const buildApiError = (error: any, fallbackMessage: string) => {
    const message =
        error?.response?.data?.message ||
        error?.response?.data?.detail ||
        error?.message ||
        fallbackMessage;
    const wrapped: any = new Error(message);
    wrapped.status = error?.response?.status;
    wrapped.data = error?.response?.data;
    wrapped.raw = error;
    return wrapped;
};

const throwApiError = (error: any, fallbackMessage: string): never => {
    throw buildApiError(error, fallbackMessage);
};

// Agent

export const createAgent = async (agent: any) => {

    const response = {}
    return response;

};



// ResourceSet

export const createResourceSet = async (resourceSet: any) => {

}

export const getResourceSets = async (envId: string, orgId: string = null, membershipId = null) => {
    if (envId === "") {
        return [];
    }
    let params = {}

    if (orgId) {
        params["org_id"] = orgId;
    }

    if (membershipId) {
        params["membership_id"] = membershipId;
    }

    try {
        const response = await api.get(`/environments/${envId}/resource_sets`, {
            params: params
        })
        return response.data.map((item: any) => {
            return {
                id: item.id,
                name: item.name,
                agent: item.agent,
                membership: item.membership,
                membershipName: item.membership_name,
                org_type: item.org_type,
                orgId: item.org_id,
                msp: item.msp,
                environment: item.environment,
            }
        })
    } catch (error) {
        return [];
    }

}

export const getResourceSet = async (resourceSetId: string) => {

}

export const updateResourceSet = async (resourceSetId: string, resourceSet: any) => {

}

export const deleteResourceSet = async (resourceSetId: string) => {

}

// EVN API

export const InitEnv = async (envId: string) => {
    try {
        const response = await api.post(`/environments/${envId}/init`)
        return response.data;
    } catch (error) {
        throwApiError(error, "Initialize Fabric environment failed");
    }
}

export const JoinEnv = async (envId: string, membershipId: string) => {
    try {
        const response = await api.post(`/environments/${envId}/join`, {
            membership_id: membershipId
        })
        return response.data;
    } catch (error) {
        throwApiError(error, "Join Fabric environment failed");
    }
}

export const JoinEthEnv = async (envId: string, membershipId: string) => {
    try {
        const response = await api.post(`/eth-environments/${envId}/join`, {
            membership_id: membershipId
        })
        return response.data;
    } catch (error) {
        throwApiError(error, "Join Ethereum environment failed");
    }
}

export const StartEnv = async (envId: string) => {
    try {
        const response = await api.post(`/environments/${envId}/start`)
        return response.data;
    } catch (error) {
        throwApiError(error, "Start Fabric environment failed");
    }
}

export const ActivateEnv = async (envId: string, orgId: string) => {
    try {
        const response = await api.post(`/environments/${envId}/activate`,
            {
                org_id: orgId
            })
        return response.data;
    } catch (error) {
        throwApiError(error, "Activate Fabric environment failed");
    }
}

export const InstallFirefly = async (orgId: string, envId: string, force: boolean = false) => {
    try {
        const response = await api.post(`/environments/${envId}/install_firefly`, {
            org_id: orgId,
            ...(force ? { force: true } : {}),
        })
        return response.data;
    } catch (error) {
        throwApiError(error, "Install Firefly failed");
    }
}

export const InstallOracle = async (orgId: string, envId: string, force: boolean = false) => {
    try {
        const response = await api.post(`/environments/${envId}/install_oracle`, {
            org_id: orgId,
            ...(force ? { force: true } : {}),
        })
        return response.data;
    } catch (error) {
        throwApiError(error, "Install Oracle failed");
    }
}

export const InstallDmnEngine = async (orgId: string, envId: string, force: boolean = false) => {
    try {
        const response = await api.post(`/environments/${envId}/install_dmn_engine`, {
            org_id: orgId,
            ...(force ? { force: true } : {}),
        })
        return response.data;
    } catch (error) {
        throwApiError(error, "Install DMN failed");
    }
}

export const InstallChainlinkForEthEnv = async (envId: string, mode: string = "lite", force: boolean = false) => {
    try {
        const response = await api.post(`/eth-environments/${envId}/chainlink/install`, {
            mode,
            ...(force ? { force: true } : {}),
        })
        return response.data;
    } catch (error) {
        throwApiError(error, "Install Chainlink failed");
    }
}

export const getTask = async (taskId: string) => {
    try {
        const response = await api.get(`/tasks/${taskId}`)
        return response.data?.data ?? response.data
    } catch (error) {
        throwApiError(error, "Get task failed");
    }
}

export const getTasks = async (targetType: string, targetId: string, limit: number = 20) => {
    try {
        const response = await api.get(`/tasks`, {
            params: { target_type: targetType, target_id: targetId, limit }
        })
        return response.data?.data ?? response.data
    } catch (error) {
        throwApiError(error, "Get tasks failed");
    }
}

export const getChainlinkDetailForEthEnv = async (envId: string, sync: boolean = false) => {
    try {
        const response = await api.get(`/eth-environments/${envId}/chainlink`, {
            params: sync ? { sync: 1 } : undefined,
        })
        return response.data;
    } catch (error) {
        throwApiError(error, "Get Chainlink detail failed");
    }
}

export const syncChainlinkForEthEnv = async (envId: string, includeJobs: boolean = true, force: boolean = false) => {
    try {
        const response = await api.post(`/eth-environments/${envId}/chainlink/sync`, {
            include_jobs: includeJobs,
            ...(force ? { force: true } : {}),
        })
        return response.data;
    } catch (error) {
        throwApiError(error, "Sync Chainlink cluster failed");
    }
}

export const getChainlinkJobsForEthEnv = async (envId: string, node?: string) => {
    try {
        const response = await api.get(`/eth-environments/${envId}/chainlink-jobs`, {
            params: node ? { node } : undefined
        })
        return response.data;
    } catch (error) {
        throwApiError(error, "Get Chainlink jobs failed");
    }
}

export const createChainlinkJobForEthEnv = async (envId: string, payload: any) => {
    try {
        const response = await api.post(`/eth-environments/${envId}/chainlink-jobs`, payload)
        return response.data;
    } catch (error) {
        throwApiError(error, "Create Chainlink job failed");
    }
}

export const createChainlinkPresetJobForEthEnv = async (envId: string, payload: any, force: boolean = false) => {
    try {
        const response = await api.post(`/eth-environments/${envId}/chainlink/create-job`, {
            ...payload,
            ...(force ? { force: true } : {}),
        })
        return response.data;
    } catch (error) {
        throwApiError(error, "Create preset Chainlink job failed");
    }
}

export const getChainlinkJobForEthEnv = async (envId: string, jobId: string, node: string) => {
    try {
        const response = await api.get(`/eth-environments/${envId}/chainlink-jobs/${jobId}`, {
            params: { node }
        })
        return response.data;
    } catch (error) {
        throwApiError(error, "Get Chainlink job failed");
    }
}

export const updateChainlinkJobForEthEnv = async (envId: string, jobId: string, payload: any) => {
    try {
        const response = await api.patch(`/eth-environments/${envId}/chainlink-jobs/${jobId}`, payload)
        return response.data;
    } catch (error) {
        throwApiError(error, "Update Chainlink job failed");
    }
}

export const deleteChainlinkJobForEthEnv = async (envId: string, jobId: string, node: string) => {
    try {
        const response = await api.delete(`/eth-environments/${envId}/chainlink-jobs/${jobId}`, {
            params: { node }
        })
        return response.data;
    } catch (error) {
        throwApiError(error, "Delete Chainlink job failed");
    }
}

export const getEthAccountCheck = async (envId: string) => {
    try {
        const response = await api.get(`/eth-environments/${envId}/account-check`)
        return response.data;
    } catch (error) {
        throwApiError(error, "Get Ethereum account check failed");
    }
}

export const getDmnContractDetailForEthEnv = async (envId: string, includeAbi: boolean = false) => {
    try {
        const response = await api.get(`/eth-environments/${envId}/dmn-contract`, {
            params: includeAbi ? { include_abi: 1 } : undefined
        })
        return response.data;
    } catch (error) {
        throwApiError(error, "Get DMN contract detail failed");
    }
}

export const redeployDmnContractForEthEnv = async (envId: string, force: boolean = false) => {
    try {
        const response = await api.post(`/eth-environments/${envId}/dmn-contract/redeploy`, {
            ...(force ? { force: true } : {}),
        })
        return response.data;
    } catch (error) {
        throwApiError(error, "Redeploy DMN contract failed");
    }
}

export const registerDmnContractToFireflyForEthEnv = async (envId: string, force: boolean = false) => {
    try {
        const response = await api.post(`/eth-environments/${envId}/dmn-contract/register-firefly`, {
            ...(force ? { force: true } : {}),
        })
        return response.data;
    } catch (error) {
        throwApiError(error, "Register DMN contract to Firefly failed");
    }
}

export const getDataContractDetailForEthEnv = async (envId: string, includeAbi: boolean = false) => {
    try {
        const response = await api.get(`/eth-environments/${envId}/data-contract`, {
            params: includeAbi ? { include_abi: 1 } : undefined
        })
        return response.data;
    } catch (error) {
        throwApiError(error, "Get data contract detail failed");
    }
}

export const setupDataContractForEthEnv = async (envId: string, force: boolean = false) => {
    try {
        const response = await api.post(`/eth-environments/${envId}/data-contract/setup`, {
            ...(force ? { force: true } : {}),
        })
        return response.data;
    } catch (error) {
        throwApiError(error, "Setup data contract failed");
    }
}

export const registerDataContractToFireflyForEthEnv = async (envId: string, force: boolean = false) => {
    try {
        const response = await api.post(`/eth-environments/${envId}/data-contract/register-firefly`, {
            ...(force ? { force: true } : {}),
        })
        return response.data;
    } catch (error) {
        throwApiError(error, "Register data contract to Firefly failed");
    }
}

export const getComputeContractDetailForEthEnv = async (envId: string, includeAbi: boolean = false) => {
    try {
        const response = await api.get(`/eth-environments/${envId}/compute-contract`, {
            params: includeAbi ? { include_abi: 1 } : undefined
        })
        return response.data;
    } catch (error) {
        throwApiError(error, "Get compute contract detail failed");
    }
}

export const setupComputeContractForEthEnv = async (envId: string, force: boolean = false) => {
    try {
        const response = await api.post(`/eth-environments/${envId}/compute-contract/setup`, {
            ...(force ? { force: true } : {}),
        })
        return response.data;
    } catch (error) {
        throwApiError(error, "Setup compute contract failed");
    }
}

export const registerComputeContractToFireflyForEthEnv = async (envId: string, force: boolean = false) => {
    try {
        const response = await api.post(`/eth-environments/${envId}/compute-contract/register-firefly`, {
            ...(force ? { force: true } : {}),
        })
        return response.data;
    } catch (error) {
        throwApiError(error, "Register compute contract to Firefly failed");
    }
}

export const getRelayerContractDetailForEthEnv = async (envId: string, includeAbi: boolean = false) => {
    try {
        const response = await api.get(`/eth-environments/${envId}/relayer-contract`, {
            params: includeAbi ? { include_abi: 1 } : undefined
        })
        return response.data;
    } catch (error) {
        throwApiError(error, "Get relayer contract detail failed");
    }
}

export const setupRelayerContractForEthEnv = async (envId: string, force: boolean = false) => {
    try {
        const response = await api.post(`/eth-environments/${envId}/relayer-contract/setup`, {
            ...(force ? { force: true } : {}),
        })
        return response.data;
    } catch (error) {
        throwApiError(error, "Setup relayer contract failed");
    }
}

export const registerRelayerContractToFireflyForEthEnv = async (envId: string, force: boolean = false) => {
    try {
        const response = await api.post(`/eth-environments/${envId}/relayer-contract/register-firefly`, {
            ...(force ? { force: true } : {}),
        })
        return response.data;
    } catch (error) {
        throwApiError(error, "Register relayer contract to Firefly failed");
    }
}

export const getRelayerNodeStatusForEthEnv = async (envId: string) => {
    try {
        const response = await api.get(`/eth-environments/${envId}/relayer-node`)
        return response.data;
    } catch (error) {
        throwApiError(error, "Get relayer node status failed");
    }
}

export const controlRelayerNodeForEthEnv = async (envId: string, action: "start" | "stop") => {
    try {
        const response = await api.post(`/eth-environments/${envId}/relayer-node/${action}`)
        return response.data;
    } catch (error) {
        throwApiError(error, `Relayer node ${action} failed`);
    }
}

export const requestOracleFFI = async () => {
    try {
        const response = await api.get(`/environments/requestOracleFFI`)
        return response.data;
    } catch (error) {
        throwApiError(error, "Get Oracle FFI failed");
    }
}

export const StartFireflyForEnv = async (envId: string, force: boolean = false) => {
    try {
        const response = await api.post(`/environments/${envId}/start_firefly`, {
            ...(force ? { force: true } : {}),
        })
        return response.data;
    } catch (error) {
        throwApiError(error, "Start Firefly failed");
    }
}

// ChainCode Related
//             name = serializer.validated_data.get("name")
// version = serializer.validated_data.get("version")
// language = serializer.validated_data.get("language")
// file = serializer.validated_data.get("file")
// env_id = request.parser_context["kwargs"].get("environment_id")
// env = Environment.objects.get(id=env_id)
// env_resource_set = env.resource_sets.all().first()
// org_id = serializer.validated_data.get("org_id")

export const packageChaincode = async ({
    name,
    version,
    language,
    file,
    env_id,
    org_id
}: any) => {

    const formData = new FormData();
    formData.append("file", file);
    formData.append("name", name);
    formData.append("version", version);
    formData.append("language", language);
    formData.append("org_id", org_id);

    try {
        const response = await api.post(`/environments/${env_id}/chaincodes/package`, formData, {
            headers: {
                "Content-Type": "multipart/form-data"
            }
        })
        return response.data;
    } catch (error) {
        return error;
    }
}


export const getChainCodeList = async (envId: string) => {
    try {
        const response = await api.get(`/environments/${envId}/chaincodes`)
        return response.data.map((item: any) => {
            return {
                key: item.id,
                name: item.name,
                version: item.version,
                language: item.language,
                creator: item.creator,
                create_time: item.create_ts,
            }
        })
    } catch (error) {
        return {}
    }
}

export const getEthContractList = async (envId: string) => {
    try {
        const response = await api.get(`/eth-environments/${envId}/contracts`)
        const items = response.data?.data ?? response.data ?? []
        return items.map((item: any) => {
            return {
                key: item.id,
                id: item.id,
                name: item.name,
                version: item.version,
                language: item.language,
                creator: item.creator,
                filename: item.filename,
                status: item.status,
                contract_address: item.contract_address,
                deployment_tx_hash: item.deployment_tx_hash,
                create_time: item.create_ts,
            }
        })
    } catch (error) {
        throwApiError(error, "Get ethereum contract list failed");
    }
}

export const getEthContractDetail = async (envId: string, contractId: string) => {
    try {
        const response = await api.get(`/eth-environments/${envId}/contracts/${contractId}`)
        return response.data?.data ?? response.data
    } catch (error) {
        throwApiError(error, "Get ethereum contract detail failed");
    }
}

export const installEthContract = async ({
    envId,
    name,
    version,
    language = "solidity",
    file,
    orgId,
    compilerVersion,
    contractName,
    namespace = "default",
    constructorArgs = [],
}: any) => {
    const formData = new FormData();
    formData.append("name", name);
    formData.append("version", version);
    formData.append("language", language);
    formData.append("file", file);
    formData.append("org_id", orgId);
    formData.append("namespace", namespace);
    formData.append("constructor_args", JSON.stringify(constructorArgs));
    if (compilerVersion) {
        formData.append("compiler_version", compilerVersion);
    }
    if (contractName) {
        formData.append("contract_name", contractName);
    }
    try {
        const response = await api.post(`/eth-environments/${envId}/contracts/install`, formData, {
            headers: {
                "Content-Type": "multipart/form-data"
            }
        })
        return response.data?.data ?? response.data;
    } catch (error) {
        throwApiError(error, "Install ethereum contract failed");
    }
}

// ETH ENV API

export const InitEthEnv = async (envId: string) => {
    try {
        const response = await api.post(`/eth-environments/${envId}/init`)
        return response.data;
    } catch (error) {
        throwApiError(error, "Initialize Ethereum environment failed");
    }
}

export const StartEthEnv = async (envId: string) => {
    try {
        const response = await api.post(`/eth-environments/${envId}/start`)
        return response.data;
    } catch (error) {
        throwApiError(error, "Start Ethereum environment failed");
    }
}

export const ActivateEthEnv = async (envId: string) => {
    try {
        const response = await api.post(`/eth-environments/${envId}/activate`)
        return response.data;
    } catch (error) {
        throwApiError(error, "Activate Ethereum environment failed");
    }
}

// Firefly for Ethereum
export const InitFireflyForEthEnv = async (envId: string) => {
    try {
        const response = await api.post(`/eth-environments/${envId}/fireflys/init_eth`)
        return response.data;
    } catch (error) {
        throwApiError(error, "Initialize Ethereum Firefly failed");
    }
}

export const StartFireflyForEthEnv = async (envId: string) => {
    try {
        const response = await api.post(`/eth-environments/${envId}/fireflys/start_eth`)
        return response.data;
    } catch (error) {
        throwApiError(error, "Start Ethereum Firefly failed");
    }
}

export const InstallIdentityContract = async (
    envId: string,
    options: {
        force?: boolean,
        compilerVersion?: string | null,
        archive?: File | null,
        contractName?: string | null,
    } = {}
) => {
    try {
        const { force = false, compilerVersion = null, archive = null, contractName = null } = options;
        const hasArchive = archive instanceof File;
        if (hasArchive) {
            const payload = new FormData();
            if (archive) {
                payload.append("archive", archive);
            }
            if (force) {
                payload.append("force", "true");
            }
            if (compilerVersion) {
                payload.append("compiler_version", compilerVersion);
            }
            if (contractName) {
                payload.append("contract_name", contractName);
            }
            const response = await api.post(
                `/eth-environments/${envId}/identity-contract/install`,
                payload,
                {
                    headers: {
                        "Content-Type": "multipart/form-data"
                    }
                }
            )
            return response.data;
        }
        const payload = {
            ...(force ? { force: true } : {}),
            ...(compilerVersion ? { compiler_version: compilerVersion } : {}),
            ...(contractName ? { contract_name: contractName } : {}),
        };
        const response = await api.post(
            `/eth-environments/${envId}/identity-contract/install`,
            payload
        )
        return response.data;
    } catch (error) {
        throwApiError(error, "Install identity contract failed");
    }
}

export const getIdentityContractDetail = async (envId: string, includeAbi: boolean = false) => {
    try {
        const response = await api.get(
            `/eth-environments/${envId}/identity-contract`,
            {
                params: { include_abi: includeAbi ? 1 : 0 }
            }
        )
        return response.data;
    } catch (error) {
        throwApiError(error, "Get identity contract detail failed");
    }
}

export const redeployIdentityContract = async (envId: string, force: boolean = false) => {
    try {
        const response = await api.post(`/eth-environments/${envId}/identity-contract/redeploy`, {
            ...(force ? { force: true } : {}),
        })
        return response.data;
    } catch (error) {
        throwApiError(error, "Redeploy identity contract failed");
    }
}


// Node Related

export const getPeerList = async (resId: string) => {
    try {
        const response = await api.get(`resource_sets/${resId}/nodes`, {
            params: {
                page: 1,
                per_page: 100,
            }
        })
        return response.data.filter(
            (item: any) => { return item.type === "peer" })
            .map((item: any) => {
                return {
                    id: item.id,
                    name: item.name,
                    owner: item.owner,
                    orgId: item.org_id,
                }
            })
    } catch (error) {
    }
}

export const getNodeList = async (resId: string, type?: string) => {
    try {
        const response = await api.get(`resource_sets/${resId}/nodes`, {
            params: {
                page: 1,
                per_page: 100,
                ...(type ? { type } : {}),
            }
        })
        return response.data.map((item: any) => ({
            id: item.id,
            name: item.name,
            type: item.type,
            owner: item.owner,
            orgId: item.org_id,
            status: item.status,
            createdAt: item.created_at,
        }))
    } catch (error) {
        return [];
    }
}

export const installChaincode = async (envId: string, nodeId: string, chaincodeId: string) => {
    try {
        const response = await api.post(`/environments/${envId}/chaincodes/install`, {
            peer_node_list: [nodeId],
            id: chaincodeId
        })
        return response.data;
    } catch (error) {
        return error;
    }
}

export const queryInstalledChaincode = async (envId: string, nodeId: string) => {
    try {
        const response = await api.get(`/environments/${envId}/chaincodes/query_installed`, {
            params: {
                peer_id: nodeId
            }
        })
        return response.data;
    } catch (error) {
        return error;
    }
}

export const getChannelList = async (envId: string) => {
    try {
        const response = await api.get(`/environments/${envId}/channels`)
        // if (response.data.status!=="success") {
        //     return [];
        // }
        return response.data.data.map((item: any) => {
            return {
                id: item.id,
                name: item.name,
            }
        })
    } catch (error) {
        return [];
    }
}

export const retriveChaincode = async (envId: string, chaincodeId: string) => {
    try {
        const response = await api.get(`/environments/${envId}/chaincodes/${chaincodeId}`)
        return response.data;
    } catch (error) {
        return error;
    }
}

export const queryChaincodeApprove = async (channelName: string, chaincodeName: string, resourceSetId: string, envId: string) => {

    try {
        const response = await api.get(`/environments/${envId}/chaincodes/query_approved`, {
            params: {
                channel_name: channelName,
                chaincode_name: chaincodeName,
                resource_set_id: resourceSetId
            }
        })
        return response.data.data.approved;
    } catch (error) {
        return error;
    }
}

export const approveChaincode = async (chaincodeName: string, chaincodeVersion: string, channelName: string, envId: string, resourceSetId: string) => {
    try {
        const response = await api.post(`/environments/${envId}/chaincodes/approve_for_my_org`, {
            chaincode_name: chaincodeName,
            chaincode_version: chaincodeVersion,
            channel_name: channelName,
            resource_set_id: resourceSetId,
            sequence: 1
        })
        return response.data;
    } catch (error) {
        return error;
    }
}

export const queryCommitChaincode = async (channelName: string, chaincodeName: string, envId: string) => {
    try {
        const response = await api.get(`/environments/${envId}/chaincodes/query_committed`, {
            params: {
                channel_name: channelName,
                chaincode_name: chaincodeName
            }
        })
        return response.data.data.committed;
    } catch (error) {
        return error;
    }
}

export const commitChaincode = async (chaincodeName: string, chaincodeVersion: string, channelName: string, envId: string, resource_set_id: string) => {
    try {
        const response = await api.post(`/environments/${envId}/chaincodes/commit`, {
            chaincode_name: chaincodeName,
            chaincode_version: chaincodeVersion,
            channel_name: channelName,
            resource_set_id: resource_set_id,
            sequence: 1,
        })
        return response.data;
    } catch (error) {
        return error;
    }
}

export const getFireflyList = async (
    envId: string,
    orgId: string,
    membershipId: string = null,
    envType: string = "Fabric",
) => {
    if (envId === "") {
        return [];
    }
    try {
        const basePath =
            envType === "Ethereum"
                ? `/eth-environments/${envId}/fireflys`
                : `/environments/${envId}/fireflys`;

        const response = await api.get(basePath, {
            params: {
                org_id: orgId ? orgId : null,
                membership_id: membershipId ? membershipId : null
            }
        })
        return response.data.data.map((item: any) => {
            return {
                id: item.id,
                name: item.org_name,
                // membershipName: item.membership_name,
                orgName: item.org_name,
                // status: item.status
                coreURL: item.core_url,
                sandboxURL: item.sandbox_url,
                membershipName: item.membership_name,
                membershipId: item.membership_id,
            }
        })
    } catch (error) {
        return [];
    }
}

export const getFireflyDetail = async (envId: string, fireflyId: string) => {
    return getFireflyDetailByEnvType(envId, fireflyId, "Fabric");
}

export const getFireflyDetailByEnvType = async (
    envId: string,
    fireflyId: string,
    envType: string = "Fabric",
) => {
    try {
        const basePath =
            envType === "Ethereum"
                ? `/eth-environments/${envId}/fireflys/${fireflyId}`
                : `/environments/${envId}/fireflys/${fireflyId}`;
        const response = await api.get(basePath)
        const item = response.data.data;
        return {
            id: item.id,
            name: item.org_name,
            // membershipName: item.membership_name,
            // orgName: item.org_name,
            // status: item.status
            coreURL: item.core_url,
            sandboxURL: item.sandbox_url,
            membershipName: item.membership_name,
            membershipId: item.membership_id,
        }
    } catch (error) {
        return {};
    }
}
