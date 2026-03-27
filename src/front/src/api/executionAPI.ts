import { fireflyAPI } from './apiConfig.ts';
import axios from 'axios';
// Register Interface and Contract


// DataType Annotation
export const registerDataType = async (coreUrl: string, mergedData: any) => {
    try {
        const res = await fireflyAPI.post(`${coreUrl}/api/v1/namespaces/default/datatypes`, mergedData);
        return res.data;
    } catch (error) {
        console.error("Error occurred while making post request:", error);
        return [];
    }

}


export const fireflyFileTransfer = async (coreUrl: string, uploadedFile: any) => {
    try {
        // debugger;
        const formData = new FormData();
        formData.append('autometa', 'true');
        formData.append('file', uploadedFile);
        const res = await fireflyAPI.post(`${coreUrl}/api/v1/namespaces/default/data`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        });
        return res.data;
    } catch (error: any) {
        console.error("Error occurred while making post request:", error);
        throw new Error(error?.response?.data?.message || error?.message || "Firefly file upload failed");
    }
}

export const getFireflyData = async (coreUrl: string, dataId: string) => {
    try {
        const res = await fireflyAPI.get(`${coreUrl}/api/v1/namespaces/default/data/${dataId}`);
        return res.data;
    } catch (error) {
        console.error("Error occurred while making post request:", error);
        return [];
    }
}

export const fireflyDataTransfer = async (coreUrl: string, data: any) => {
    try {
        const res = await fireflyAPI.post(`${coreUrl}/api/v1/namespaces/default/messages/private`, data);
        return res.data;
    } catch (error: any) {
        console.error("Error occurred while making post request:", error);
        throw new Error(error?.response?.data?.message || error?.message || "Firefly data transfer failed");
    }
}


// fetch SVG


//Init Ledger

export const initLedger = async (coreUrl: string, contractName: string) => {
    // coreUrl + `/api/v1/namespaces/default/apis/${name}/invoke/InitLedger
    // mediaType: "application/json"
    try {
        const res = await axios.post(`${coreUrl}/api/v1/namespaces/default/apis/${contractName}/invoke/InitLedger`, {
            "input": {}
        }
        );
        return res.data;
    } catch (error) {
        console.error("Error occurred while making post request:", error);
        return [];
    }
}

// GetAllActionEvents

export const getAllEvents = async (coreUrl: string, contractName: string, bpmnInstanceId: string) => {
    // coreUrl + "/api/v1/namespaces/default/apis/" + name + "/query/GetAllActionEvents"
    try {
        const res = await fireflyAPI.post(`${coreUrl}/api/v1/namespaces/default/apis/${contractName}/query/GetAllActionEvents`, {
            "input": {
                "InstanceID": `${bpmnInstanceId}`
            }
        });
        return res.data;
    } catch (error) {
        console.error("Error occurred while making post request:", error);
        return [];
    }
}

export const getAllGateways = async (coreUrl: string, contractName: string, bpmnInstanceId: string) => {
    try {
        const res = await fireflyAPI.post(`${coreUrl}/api/v1/namespaces/default/apis/${contractName}/query/GetAllGateways`, {
            "input": {
                "InstanceID": `${bpmnInstanceId}`
            }
        });
        return res.data;
    } catch (error) {
        console.error("Error occurred while making post request:", error);
        return [];
    }
}

export const getAllMessages = async (coreUrl: string, contractName: string, bpmnInstanceId: string) => {
    try {
        const res = await fireflyAPI.post(`${coreUrl}/api/v1/namespaces/default/apis/${contractName}/query/GetAllMessages`, {
            "input": {
                "InstanceID": `${bpmnInstanceId}`
            }
        });
        return res.data;
    } catch (error) {
        console.error("Error occurred while making post request:", error);
        return [];
    }
}

export const getAllBusinessRules = async (coreUrl: string, contractName: string, bpmnInstanceId: string) => {
    try {
        const res = await fireflyAPI.post(`${coreUrl}/api/v1/namespaces/default/apis/${contractName}/query/GetAllBusinessRules`, {
            "input": {
                "InstanceID": `${bpmnInstanceId}`
            }
        });
        return res.data;
    } catch (error) {
        console.error("Error occurred while making post request:", error);
        return [];
    }
}



// invoke

export const invokeEventAction = async (coreUrl: string, contractName: string, eventId: any, instanceId: string) => {
    try {
        const res = await fireflyAPI.post(`${coreUrl}/api/v1/namespaces/default/apis/${contractName}/invoke/${eventId}`, {
            "input": {
                "InstanceID": `${instanceId}`
            }
        });
        return res.data;
    } catch (error: any) {
        console.error("Error occurred while making post request:", error);
        throw new Error(error?.response?.data?.message || error?.message || "Invoke event failed");
    }
}

export const invokeGatewayAction = async (coreUrl: string, contractName: string, gtwId: any, instanceId: string) => {
    try {
        const res = await fireflyAPI.post(`${coreUrl}/api/v1/namespaces/default/apis/${contractName}/invoke/${gtwId}`, {
            "input": {
                "InstanceID": `${instanceId}`
            }
        });
        return res.data;
    } catch (error: any) {
        console.error("Error occurred while making post request:", error);
        throw new Error(error?.response?.data?.message || error?.message || "Invoke gateway failed");
    }
}

export const invokeBusinessRuleAction = async (coreUrl: string, contractName: string, ruleId: any, instanceId: string) => {
    try {
        const res = await fireflyAPI.post(`${coreUrl}/api/v1/namespaces/default/apis/${contractName}/invoke/${ruleId}`, {
            "input": {
                "InstanceID": `${instanceId}`
            }
        });
        return res.data;
    } catch (error: any) {
        console.error("Error occurred while making post request:", error);
        throw new Error(error?.response?.data?.message || error?.message || "Invoke business rule failed");
    }
}

export const invokeMessageAction = async (coreUrl: string, contractName: string, methodName: any, data: any, instanceId: string, identity: string) => {
    // debugger
    try {
        const res = await fireflyAPI.post(`${coreUrl}/api/v1/namespaces/default/apis/${contractName}/invoke/${methodName}`, {
            "input": {
                ...data.input,
                "InstanceID": `${instanceId}`,
            },
            "key": identity,
        });
        return res.data;
    } catch (error: any) {
        console.error("Error occurred while making post request:", error);
        throw new Error(error?.response?.data?.message || error?.message || "Invoke message failed");
    }
}


export const getFireflyVerify = async (coreUrl: string, fireflyIdentityId: string) => {
    try {
        const res = await fireflyAPI.get(`http://${coreUrl}/api/v1/namespaces/default/identities/${fireflyIdentityId}/verifiers`);
        return res.data;
    } catch (error) {
        console.error("Error occurred while making post request:", error);
        return [];
    }
}

export const callFireflyContract = async (
    contractBaseUrl: string,
    method: string,
    params: Record<string, any> = {},
    mode: "invoke" | "query" = "invoke"
) => {
    const payload = {
        input: params,
    };
    const res = await fireflyAPI.post(`${contractBaseUrl}/${mode}/${method}`, payload);
    return res.data;
}

export const invokeCreateInstance = async (chaincodeUrl: string, data: any) => {
    try {
        const res = await fireflyAPI.post(`${chaincodeUrl.slice(0, -4)}/invoke/CreateInstance`, {
            "input": {
                "initParametersBytes": JSON.stringify(data)
            }
        });
        return res.data
    } catch (error) {
        console.error("Error occurred while making post request:", error);
        return [];
    }
}
export const invokeFireflyListeners = async (
    coreUrl: string,
    contractName: string,
    eventName: string,
    interfaceId: string,
    contractAddress?: string  // 新增可选参数：Ethereum 合约地址
) => {
    try {
        // 根据是否提供 contractAddress 决定使用 Fabric 还是 Ethereum location
        const location = contractAddress
            ? { address: contractAddress }  // Ethereum: 使用 address
            : {  // Fabric: 使用 channel + chaincode
                channel: "default",
                chaincode: contractName
            };

        const res = await fireflyAPI.post(`${coreUrl}/api/v1/namespaces/default/contracts/listeners`, {
            "interface": {
                "id": interfaceId
            },
            "location": location,
            "event": {
                "name": eventName
            },
            "options": {
                "firstEvent": "oldest"
            },
            "topic": eventName
        });
        return res.data;
    } catch (error) {
        console.error("Error occurred while making post request:", error);
        return [];
    }
}

export const invokeFireflySubscriptions = async (coreUrl: string, eventName: string, listenerId: string) => {
    try {
        const res = await fireflyAPI.post(`${coreUrl}/api/v1/namespaces/default/subscriptions`, {
            "namespace": "default",
            "name": eventName,
            "transport": "websockets",
            "filter": {
                "events": "blockchain_event_received",
                "blockchainevent": {
                    "listener": listenerId
                }
            },
            "options": {
                "firstEvent": "oldest"
            }
        });
        return res.data;
    } catch (error) {
        console.error("Error occurred while making post request:", error);
        return [];
    }
}

// Register Interface

export const registerInterface = async (coreUrl: string, ffiConetnt: string, interfaceName: string) => {
    try {
        let parsedData = JSON.parse(ffiConetnt);
        parsedData.name = interfaceName;
        const res = await fireflyAPI.post(`${coreUrl}/api/v1/namespaces/default/contracts/interfaces`, 
            parsedData
        );
        return res.data;
    } catch (error) {
        console.error("Error occurred while making post request:", error);
        return [];
    }
}


export const registerAPI = async (coreUrl: string, chaincodeName:string, channel:string, apiName: string, interfaceId: string) => {
    try {
        const res = await fireflyAPI.post(`${coreUrl}/api/v1/namespaces/default/apis`, {
            "name": apiName,
            "interface": {
                "id": interfaceId
            },
            "location": {
                "channel": channel,
                "chaincode": chaincodeName
            }
        });
        return res.data;
    } catch (error) {
        console.error("Error occurred while making post request:", error);
        return [];
    }
}
