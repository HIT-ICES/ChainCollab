import { env } from 'process';
import api from './apiConfig';

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
        console.log(error);
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
        return error;
    }
}

export const JoinEnv = async (envId: string, membershipId: string) => {
    const response = await api.post(`/environments/${envId}/join`, {
        membership_id: membershipId
    })
    return response.data;
}

export const StartEnv = async (envId: string) => {
    try {
        const response = await api.post(`/environments/${envId}/start`)
        return response.data;
    } catch (error) {
        return error;
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
        return error;
    }
}

export const StartFireflyForEnv = async (envId: string) => {
    try {
        const response = await api.post(`/environments/${envId}/start_firefly`)
    } catch (error) {
        return error;
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
        console.log(error)
        return {}
    }
}


// Node Related

export const getPeerList = async (resId: string) => {
    try {
        const response = await api.get(`resource_sets/${resId}/nodes`)
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
        console.log(error);
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
        console.log(error);
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

export const getFireflyList = async (envId: string, orgId: string) => {
    if (envId === "") {
        return [];
    }
    try {

        const response = await api.get(`/environments/${envId}/fireflys`, {
            params: {
                org_id: orgId ? orgId : null
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
        console.log(error);
        return [];
    }
}

export const getFireflyDetail = async (envId: string, fireflyId: string) => {
    try {
        const response = await api.get(`/environments/${envId}/fireflys/${fireflyId}`)
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
        console.log(error);
        return {};
    }
}