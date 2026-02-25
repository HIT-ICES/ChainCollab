import { translatorAPI } from './apiConfig.ts';

export const generateChaincode = async (bpmnContent: string, target: "go" | "solidity" = "go") => {
    try {
        if (target === "solidity") {
            // Ethereum环境：生成Solidity合约
            const res = await translatorAPI.post(`/chaincode/generate-eth`, {
                bpmnContent: bpmnContent,
            })
            return {
                bpmnContent: res.data.contractContent, // Solidity合约内容
                dslContent: res.data.dslContent || "",
                ffiContent: res.data.ffiContent || "{}",
                timeCost: res.data.timeCost || res.data.timecost
            }
        } else {
            // Fabric环境：生成Go链码
            const dslRes = await translatorAPI.post(`/chaincode/generate`, {
                bpmnContent: bpmnContent,
            })
            const dslContent = dslRes.data.bpmnContent;
            const timeCost = dslRes.data.timeCost || dslRes.data.timecost;
            const compileRes = await translatorAPI.post(`/chaincode/compile`, {
                dslContent,
                target: "go"
            })
            const compileFFI = compileRes.data.ffiContent;
            const fallbackFFI = dslRes.data.ffiContent;
            const ffiContent =
                compileFFI && compileFFI !== "{}" ? compileFFI : fallbackFFI;
            return {
                bpmnContent: compileRes.data.chaincodeContent,
                dslContent: dslContent,
                ffiContent: ffiContent,
                timeCost: timeCost
            }
        }
    } catch (error) {
    }
}

export const getParticipantsByContent = async (bpmnContent: string) => {
    try {
        const response = await translatorAPI.post(`/chaincode/getPartByBpmnC`, {
            bpmnContent: bpmnContent
        })
        return response.data;
    } catch (error) {
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
        return [];
    }
}

export const getMessagesByBpmnContent = async (bpmnContent: string) => {
    try {
        const response = await translatorAPI.post('/chaincode/getMessagesByBpmnC', {
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
        const response = await translatorAPI.post(`/chaincode/getDecisions`,{
            dmnContent: dmnContent
        })
        return response.data;
    } catch (error) {
        return [];
    }
}
