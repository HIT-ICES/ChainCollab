import api from './apiConfig.ts';

export const generateChaincode = async (bpmnContent: string, target: "go" | "solidity" = "go") => {
    try {
        const response = await api.post(`/translator/chaincode/generate`, {
            bpmnContent,
            target,
        });
        return response.data;
    } catch (error) {
    }
}

export const getParticipantsByContent = async (bpmnContent: string) => {
    try {
        const response = await api.post(`/translator/chaincode/participants`, {
            bpmnContent: bpmnContent
        })
        return response.data;
    } catch (error) {
        return [];
    }
}

export const getBusinessRulesByContent = async (bpmnContent: string) => {
    try {
        const response = await api.post('/translator/chaincode/business-rules', {
            bpmnContent: bpmnContent
        })
        return response.data;
    }
    catch (error) {
        return [];
    }
}

export const getMessagesByBpmnContent = async (bpmnContent: string) => {
    try {
        const response = await api.post('/translator/chaincode/messages', {
            bpmnContent: bpmnContent
        })
        return response.data;
    }
    catch (error) {
        return [];
    }
}

export const getDecisions = async (dmnContent: string) => {
    try {
        const response = await api.post(`/translator/dmn/decisions`,{
            dmnContent: dmnContent
        })
        return response.data;
    } catch (error) {
        return [];
    }
}
