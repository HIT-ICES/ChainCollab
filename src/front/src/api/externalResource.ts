import api from "./apiConfig";
import {translatorAPI} from "./apiConfig";

export const getBPMNList = async (consortiumId: string) => {
    try {
        const response = await api.get(`/consortiums/${consortiumId}/bpmns`)
        return response.data.data;
    } catch (error) {
        console.log(error);
        return [];
    }
}

export const retrieveBPMN = async (bpmnId: string, consortiumId: string = "1") => {
    try {
        const response = await api.get(`/consortiums/${consortiumId}/bpmns/${bpmnId}`)
        return response.data;
    } catch (error) {
        console.log(error);
        return null;
    }

}


export const getBPMNInstanceList = async (BPMNId: string) => {
    try {
        const response = await api.get(`/bpmns/${BPMNId}/bpmn-instances`)
        return response.data.data;
    } catch (error) {
        console.log(error);
        return [];
    }
}

export const uploadBPMN = async (envId: string, bpmn: any) => {

}

export const addBPMNInstance = async (bpmnId: string, name: string, currentEnvId: string) => {
    try {
        const response = await api.post(`/bpmns/${bpmnId}/bpmn-instances`, {
            name: name,
            env_id: currentEnvId
        })
        return response.data;
    } catch (error) {
        console.log(error);
        return null;
    }
}

export const generateChaincode = async (bpmnContent: string, mapInfo: string) => {
    try {
        const res = await translatorAPI.post(`/chaincode/generate`, {
            bpmnContent: bpmnContent,
            participantMspMap: mapInfo
        })
        return {
            bpmnContent: res.data.bpmnContent,
            ffiContent: res.data.ffiContent,
            timeCost: res.data.timeCost
        }
    } catch (error) {
        console.log(error);
    }
}

export const retrieveBPMNInstance = async (bpmnInstanceId: string, bpmnId: string = '1') => {
    try {
        const response = await api.get(`/bpmns/${bpmnId}/bpmn-instances/${bpmnInstanceId}`)
        return response.data;
    } catch (error) {
        console.log(error);
        return null;
    }

}


export const deleteBPMNInstance = async (bpmnInstanceId: string, bpmnId: string) => {
    try {
        const response = await api.delete(`/bpmns/${bpmnId}/bpmn-instances/${bpmnInstanceId}`)
        return response.data;
    } catch (error) {
        console.log(error);
        return null;
    }
}

export const updateBPMNInstanceStatus = async (bpmnInstanceId: string, bpmnId: string, newStatus: string) => {
    try {
        const response = await api.put(`/bpmns/${bpmnId}/bpmn-instances/${bpmnInstanceId}`, { status: newStatus })
        return response.data;
    } catch (error) {
        console.log(error);
        return null;
    }
}

export const updateBPMNInstanceFireflyUrl = async (bpmnInstanceId: string, bpmnId: string, fireflyUrl: string) => {
    try {
        const response = await api.put(`/bpmns/${bpmnId}/bpmn-instances/${bpmnInstanceId}`, { firefly_url: fireflyUrl })
        return response.data;
    } catch (error) {
        console.log(error);
        return null;
    }
}



export const getParticipantsByContent = async (bpmnContent: string) => {
    try {
        const response = await translatorAPI.post(`/chaincode/getPartByBpmnC`, {
            bpmnContent: bpmnContent
        })
        return response.data;
    } catch (error) {
        console.log(error);
        return [];
    }
}

export const getBindingByBPMNInstance = async (bpmnInstanceId: string) => {
    try {
        const response = await api.get(`/bpmn-instances/${bpmnInstanceId}/binding-records`)
        return response.data.data.map(
            (item: any) => {
                return {
                    participant: item.participant_id,
                    membership: item.membership,
                    membershipName: item.membership_name
                }
            }
        )
    } catch (error) {
        console.log(error);
        return [];
    }
}

export const Binding = async (bpmnInstanceId: string, participantId: string, membershipId: string) => {
    try {
        const response = await api.post(`/bpmn-instances/${bpmnInstanceId}/binding-records`, {
            participant_id: participantId,
            membership_id: membershipId
        })
        return response.data;
    } catch (error) {
        console.log(error);
        return null;
    }
}

export const getMapInfoofBPMNInstance = async (bpmnInstanceId: string, bpmnId: string = '1') => {
    try {
        const response = await api.get(`bpmns/${bpmnId}/bpmn-instances/${bpmnInstanceId}/bindInfo`)
        return response.data.data;
    } catch (error) {
        console.log(error);
        return null;
    }
}

export const packageBPMN = async (chaincodeContent: string, ffiContent: string, bpmnInstanceId, orgId: string, bpmnId: string = '1') => {
    try {
        const response = await api.post(`bpmns/${bpmnId}/bpmn-instances/${bpmnInstanceId}/package`, {
            chaincodeContent: chaincodeContent,
            ffiContent: ffiContent,
            orgId: orgId
        })
        return response.data;
    } catch (error) {
        console.log(error);
        return null;
    }
}

export const getFireflyWithMSP = async (msp) => {
    try {
        const response = await api.get('environments/1/fireflys/get_firefly_with_msp', {
            params: {
                msp: msp
            },
        })
        return response.data;
    } catch (error) {
        console.log(error);
        return null;
    }
}