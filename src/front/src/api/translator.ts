import api from './apiConfig.ts';
import axios from 'axios';
import { translatorAPI } from './apiConfig.ts';

export const generateChaincode = async (bpmnContent: string) => {
    try {
        const res = await translatorAPI.post(`/chaincode/generate`, {
            bpmnContent: bpmnContent,
            // participantMspMap: mapInfo
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

export const getBusinessRulesByContent = async (bpmnContent: string) => {
    try {
        const response = await translatorAPI.post('/chaincode/getBusinessRulesByBpmnC', {
            bpmnContent: bpmnContent
        })
        return response.data;
    }
    catch (error) {
        console.log(error);
        return [];
    }
}

export const getDecisions = async (dmnContent: string) => {
    try {
        const response = await translatorAPI.post(`/chaincode/getDecisions`,{
            dmnContent: dmnContent
        })
        return response.data;
    } catch (error) {
        console.log(error);
        return [];
    }
}
