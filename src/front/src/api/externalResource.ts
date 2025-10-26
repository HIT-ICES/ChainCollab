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

export const updateERCChaincodeFireflyUrl = async (ercId: string, fireflyUrl: string, consortiumId: string = '1') => {
    try {
        const response = await api.put(`/consortiums/${consortiumId}/ercchaincodes/${ercId}`, { firefly_url: fireflyUrl })
        return response.data;
    } catch (error) {
        console.log(error);
        return null;
    }
}


export const updateERCChaincodebindToken = async (
    ercId: string,
    token: string,
    consortiumId: string = "1"
) => {
    try {
        const response = await api.put(
            `/consortiums/${consortiumId}/ercchaincodes/${ercId}`,
            { token: token }
        );
        return response.data;
    } catch (error) {
        console.log(error);
        return null;
    }
};

export const bindTokensToERCs = async (
    ercIdTokenMap: Record<string, string>,
    chaincodeUrl: string,
    consortiumId: string,
) => {
    for (const [ercId, token] of Object.entries(ercIdTokenMap)) {
        try {
            const erc = await retrieveERCChaincode(ercId, consortiumId);

            if (!erc) {
                console.log(` 无法获取 ERC 对象: ${ercId}`);
                continue;
            }

            if (erc.installed === true && (!erc.token || erc.token === "")) {
                console.log(`更新 ERC ${ercId} 绑定 Token: ${token}`);
                if (erc.token_type == "ERC721") {
                    invokeTokenInitialize(chaincodeUrl, token, erc.name);
                }
                else if (erc.token_type == "ERC20") {
                    invokeFTTokenInitialize(chaincodeUrl, token, erc.name);
                }
                else if(erc.token_type == "ERC1155"){
                    invokeTokenInitialize(chaincodeUrl, token, erc.name);
                }
                await updateERCChaincodebindToken(ercId, token, consortiumId);
            } else {
                console.log(`初始化失败，链码未安装或者链码已初始化`);
            }
        } catch (err) {
            console.error(` ERC ${ercId} 出错:`, err);
        }
    }
}

export const ERCAddMintAuthority = async (
    ercIdTokenMap: Record<string, string>,
    chaincodeUrl: string,
    consortiumId: string,
    instanceId: string,
    msps: string[],
) => {
    for (const [ercId, token] of Object.entries(ercIdTokenMap)) {
        try {
            const erc = await retrieveERCChaincode(ercId, consortiumId);

            if (!erc) {
                console.log(` 无法获取 ERC 对象: ${ercId}`);
                continue;
            }
            invokeAddAuthority(chaincodeUrl, instanceId, msps, erc.name)

        } catch (err) {
            console.error(` ERC ${ercId} 出错:`, err);
        }
    }
}

export const getERCList = async (consortiumId: string) => {
    try {
        const response = await api.get(`/consortiums/${consortiumId}/ercchaincodes`)
        return response.data;
    } catch (error) {
        console.log(error);
        return [];
    }
}



export const retrieveERCChaincode = async (ercId: string, consortiumId: string = "1") => {
    try {
        const response = await api.get(`/consortiums/${consortiumId}/ercchaincodes/${ercId}`)
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


export const getMaxInstanceChaincodeId = async (bpmnId: string) => {
    try {
        const response = await api.get(`/bpmns/${bpmnId}/bpmn-instances`);
        const instances = response.data?.data || [];

        if (instances.length === 0) {
            return 0; // 没有实例
        }

        const maxId = Math.max(
            ...instances
                .map((item: any) => item.instance_chaincode_id)
                .filter((id: number | null) => id !== null) // 过滤掉 null
        );

        return maxId + 1;
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

export const packageERC = async (
    tokens: { name: string; type: string; chainCode: string; ffi: string; installed: boolean }[],
    envId: string,
    orgId: string,
    consortiumId: string = '1',
    onProgress?: (progress: {
        index: number;
        total: number;
        name: string;
        status: "packaging" | "success" | "failed";
        message?: string;
    }) => void
) => {
    try {
        const notInstalledTokens = tokens.filter(token => !token.installed);
        const resulttokens: {
            name: string;
            type: string;
            chainCode: string;
            ffi: string;
            installed: boolean;
            ercId: string | null;
        }[] = [];
        // 准备一个结果数组，保存每个token的执行情况
        const results: {
            name: string;
            status: "success" | "failed";
            message?: string;
        }[] = [];

        for (let i = 0; i < notInstalledTokens.length; i++) {
            const token = notInstalledTokens[i];
            onProgress?.({
                index: i + 1,
                total: notInstalledTokens.length,
                name: token.name,
                status: "packaging",
                message: "Packaging..."
            });
            try {
                const response = await api.post(
                    `/consortiums/${consortiumId}/ercchaincodes/packageERC`,
                    {
                        name: token.name,
                        ERCChaincode: token.chainCode,
                        ERCType: token.type,
                        ERCffi: token.ffi,
                        envId,
                        orgId,
                    }
                );
                const ercId = response.data?.ercId;
                resulttokens.push({ ...token, ercId });
                const result = {
                    name: token.name,
                    status: "success" as const,
                    message: response.data?.message || "Success",
                };
                results.push(result);

                // 通知前端进度
                onProgress?.({
                    index: i + 1,
                    total: notInstalledTokens.length,
                    name: token.name,
                    status: "success",
                    message: response.data?.message || "Success"
                });

            } catch (err: any) {
                const result = {
                    name: token.name,
                    status: "failed" as const,
                    message: err?.message || "Failed",
                };
                results.push(result);
                onProgress?.({
                    index: i + 1,
                    total: notInstalledTokens.length,
                    name: token.name,
                    status: "failed",
                    message: err?.message || "Failed"
                });
            }
        }

        return { results, resulttokens };
    } catch (error) {
        console.log(error);
        return { results: [], resulttokens: [] };
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
import { invokeAddAuthority, invokeFTTokenInitialize, invokeTokenInitialize } from "./executionAPI";

export const getFireflyIdentity = async (coreUrl: string, idInFirefly: string) => {
    const res = await axios.get(`${coreUrl}/api/v1/identities/${idInFirefly}/verifiers`)
    return res
}