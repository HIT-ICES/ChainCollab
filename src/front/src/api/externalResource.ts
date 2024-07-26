import api from "./apiConfig";
import { translatorAPI } from "./apiConfig";

export const getBPMNList = async (consortiumId: string = '1') => {
    try {
        const response = await api.get(`/consortiums/${consortiumId}/bpmns/_list`)
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

export const addBPMN = async (consortiumId: string, name: string, orgId: string, bpmnContent: string, svgContent: string, participants: string) => {
    try {
        const response = await api.post(`/consortiums/${consortiumId}/bpmns/_upload`, {
            bpmnContent: bpmnContent,
            consortiumid: consortiumId,
            orgid: orgId,
            name: name,
            svgContent: svgContent,
            participants: participants
        })
        return response.data;
    } catch (error) {
        console.log(error);
        return null;
    }
}

export const addDmn = async (consortiumId: string, name: string, orgId: string, dmnContent: string, svgContent: string) => {
    try {
        const response = await api.post(`/consortiums/${consortiumId}/dmns`, {
            dmnContent: dmnContent,
            consortiumid: consortiumId,
            orgid: orgId,
            name: name,
            svgContent: svgContent
        })
        return response.data;
    } catch (error) {
        console.log(error);
        return null;
    }
}

export const getDmnList = async (consortiumId: string) => {
    try {
        const response = await api.get(`/consortiums/${consortiumId}/dmns`)
        return response.data.data;
    } catch (error) {
        console.log(error);
        return [];
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

export const updateBPMNStatus = async (bpmnId: string, newStatus: string, consortiumId: string = '1') => {
    try {
        const response = await api.put(`/consortiums/${consortiumId}/bpmns/${bpmnId}`, { status: newStatus })
        return response.data;
    } catch (error) {
        console.log(error);
        return null;
    }
}

export const updateBpmnEnv = async (bpmnId: string, envId: string, consortiumId: string = '1') => {
    try {
        const response = await api.put(`/consortiums/${consortiumId}/bpmns/${bpmnId}`, { envId: envId })
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

export const updateBPMNFireflyUrl = async (bpmnId: string, fireflyUrl: string, consortiumId: string = '1') => {
    try {
        const response = await api.put(`/consortiums/${consortiumId}/bpmns/${bpmnId}`, { firefly_url: fireflyUrl })
        return response.data;
    } catch (error) {
        console.log(error);
        return null;
    }
}

export const updateBpmnEvents = async (bpmnId: string, events: string, consortiumId: string = '1') => {
    try {
        const response = await api.put(`/consortiums/${consortiumId}/bpmns/${bpmnId}`, { events: events })
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

export const packageBpmn = async (chaincodeContent: string, ffiContent: string, orgId: string, bpmnId: string, consortiumId: string = '1') => {
    try {
        const response = await api.post(`/consortiums/${consortiumId}/bpmns/${bpmnId}/package`, {
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

export const packageBpmnToInstance = async (chaincodeContent: string, ffiContent: string, bpmnInstanceId, orgId: string, bpmnId: string = '1') => {
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

import axios from 'axios'

export const getFireflyIdentity = async (coreUrl:string, idInFirefly:string) =>{
    const res = await axios.get(`${coreUrl}/api/v1/identities/${idInFirefly}/verifiers`)
    return res
}