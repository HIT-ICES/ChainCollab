import { fireflyAPI } from './apiConfig.ts';
import axios from 'axios';
import { identity } from 'lodash';
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
    } catch (error) {
        console.error("Error occurred while making post request:", error);
        return [];
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
    } catch (error) {
        console.error("Error occurred while making post request:", error);
        return [];
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

export const getAllTokenElements = async (coreUrl: string, contractName: string, bpmnInstanceId: string) => {
    try {
        const res = await fireflyAPI.post(`${coreUrl}/api/v1/namespaces/default/apis/${contractName}/query/GetAllTokenElement`, {
            "input": {
                "InstanceID": `${bpmnInstanceId}`       //GetAllTokenElement
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
    } catch (error) {
        console.error("Error occurred while making post request:", error);
        return [];
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
    } catch (error) {
        console.error("Error occurred while making post request:", error);
        return [];
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
    } catch (error) {
        console.error("Error occurred while making post request:", error);
        return [];
    }
}

export const invokeTaskTokenAction = async(coreUrl: string, contractName: string, ruleId: any, instanceId: string,identity: string)=>{
    try {
        const res = await fireflyAPI.post(`${coreUrl}/api/v1/namespaces/default/apis/${contractName}/invoke/${ruleId}`, {
            "input": {
                "InstanceID": `${instanceId}`
            },
            "key":identity,
        });
        return res.data;
    } catch (error) {
        console.error("Error occurred while making post request:", error);
        return [];
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
    } catch (error) {
        console.error("Error occurred while making post request:", error);
        return [];
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

export const invokeCreateInstance = async (chaincodeUrl: string, data: any) => {
    console.log("chaincodeUrl", chaincodeUrl);
    console.log(data)

    // return

    try {
        const res = await fireflyAPI.post(`${chaincodeUrl.slice(0, -4)}/invoke/CreateInstance`, {
            "input": {
                "initParametersBytes": JSON.stringify(data)
            }
        });
        console.log("调用的instanceid", res.data);
        return res.data
    } catch (error) {
        console.error("Error occurred while making post request:", error);
        return [];
    }
}

export const invokeTokenInitialize = async (chaincodeUrl: string, name: string, chaincodeName: string,erc5521flag:string="false") => {
    console.log("chaincodeUrl", chaincodeUrl);
    console.log("name", name);
    console.log("chaincodeName",chaincodeName)

    try {
        const res = await fireflyAPI.post(`${chaincodeUrl.slice(0, -4)}/invoke/TokenElementInitialize`, {
            input: {
                initParametersBytes: JSON.stringify({ name, chaincodeName,erc5521flag})
            }
        });
        return res.data;
    } catch (error) {
        console.error("Error occurred while invoking TokenElementInitialize:", error);
        return [];
    }
}

export const invokeAddAuthority = async (
    chaincodeUrl: string,
    instanceId: string,
    allowedMSPs: string[],
    chaincodeName: string,
) => {
    const payload = {
        InstanceID: instanceId,
        allowedMSPs: allowedMSPs,
        chaincodeName: chaincodeName
    };
    console.log("AddAuthority payload:", payload);
    try {
        const res = await fireflyAPI.post(`${chaincodeUrl.slice(0, -4)}/invoke/AddMintAuthority`,
            {
                input: {
                    initParametersBytes: JSON.stringify(payload)
                }
            }
        );
        console.log("AddAuthority 返回结果:", res.data);
        return res.data;
    } catch (error) {
        console.error("Error occurred while invoking AddMintAuthority_nft:", error);
        return [];
    }
};

/**
 * Get registered API name from chaincode name by querying Firefly API list
 * @param fireflyUrl - Full Firefly URL (e.g., http://127.0.0.1:5002/api/v1/namespaces/default/apis/test9-bdccb7)
 * @param chaincodeName - The chaincode name to search for (e.g., "ERC721test1")
 * @returns The registered API name (e.g., "ERC721test1-5e139d") or null if not found
 */
export const getRegisteredApiName = async (fireflyUrl: string, chaincodeName: string): Promise<string | null> => {
    try {
        // Extract base APIs URL from full Firefly URL
        // Input: http://127.0.0.1:5002/api/v1/namespaces/default/apis/test9-bdccb7
        // Output: http://127.0.0.1:5002/api/v1/namespaces/default/apis
        const urlMatch = fireflyUrl.match(/^(https?:\/\/[^\/]+\/api\/v1\/namespaces\/[^\/]+\/apis)/);

        if (!urlMatch) {
            console.error(`[getRegisteredApiName] Invalid Firefly URL format: ${fireflyUrl}`);
            return null;
        }

        const baseApisUrl = urlMatch[1];
        console.log(`[getRegisteredApiName] Base APIs URL: ${baseApisUrl}`);
        console.log(`[getRegisteredApiName] Searching for chaincode: ${chaincodeName}`);

        // Query Firefly API list
        const res = await fireflyAPI.get(baseApisUrl);
        const apisList = res.data;

        console.log(`[getRegisteredApiName] Found ${Array.isArray(apisList) ? apisList.length : 0} APIs`);

        if (!Array.isArray(apisList)) {
            console.error(`[getRegisteredApiName] Unexpected response format:`, apisList);
            return null;
        }

        // Find API by chaincode name
        const matchingApi = apisList.find((api: any) =>
            api.location && api.location.chaincode === chaincodeName
        );

        if (matchingApi) {
            console.log(`[getRegisteredApiName] ✓ Found registered API name: ${matchingApi.name}`);
            console.log(`[getRegisteredApiName] ✓ API details:`, {
                id: matchingApi.id,
                name: matchingApi.name,
                chaincode: matchingApi.location.chaincode,
                channel: matchingApi.location.channel
            });
            return matchingApi.name;
        }

        console.warn(`[getRegisteredApiName] No API found for chaincode: ${chaincodeName}`);
        console.log(`[getRegisteredApiName] Available chaincodes:`,
            apisList.map((a: any) => a.location?.chaincode).filter(Boolean)
        );
        return null;

    } catch (error) {
        console.error(`[getRegisteredApiName] Error querying API list:`, error);
        return null;
    }
};

/**
 * Query data from ERC contract using registered API name
 * @param fireflyUrl - Full Firefly URL (e.g., http://127.0.0.1:5002/api/v1/namespaces/default/apis/test9-bdccb7)
 * @param chaincodeName - The chaincode name (e.g., "ERC721test1")
 * @param methodName - The query method name (e.g., "OwnerOf", "BalanceOf")
 * @param inputParams - Input parameters for the query
 * @returns Query result data
 */
export const queryERCContract = async (
    fireflyUrl: string,
    chaincodeName: string,
    methodName: string,
    inputParams: any
) => {
    try {
        // Get registered API name from chaincode name
        const registeredApiName = await getRegisteredApiName(fireflyUrl, chaincodeName);

        if (!registeredApiName) {
            console.error(`[queryERCContract] Could not find registered API for chaincode: ${chaincodeName}`);
            return null;
        }

        // Extract base APIs URL
        const urlMatch = fireflyUrl.match(/^(https?:\/\/[^\/]+\/api\/v1\/namespaces\/[^\/]+\/apis)/);
        if (!urlMatch) {
            console.error(`[queryERCContract] Invalid Firefly URL format: ${fireflyUrl}`);
            return null;
        }

        const baseApisUrl = urlMatch[1];
        const queryUrl = `${baseApisUrl}/${registeredApiName}/query/${methodName}`;

        console.log(`[queryERCContract] Query URL: ${queryUrl}`);
        console.log(`[queryERCContract] Input params:`, inputParams);

        const res = await fireflyAPI.post(queryUrl, {
            input: inputParams
        });

        console.log(`[queryERCContract] Query result:`, res.data);
        return res.data;

    } catch (error) {
        console.error(`[queryERCContract] Error querying ERC contract:`, error);
        return null;
    }
};


export const invokeFTTokenInitialize = async (chaincodeUrl: string, name: string, chaincodeName: string) => {
    console.log("chaincodeUrl", chaincodeUrl);
    console.log("name", name);
    console.log("chaincodeName",chaincodeName)

    try {
        const res = await fireflyAPI.post(`${chaincodeUrl.slice(0, -4)}/invoke/TokenElementInitializeFT`, {
            input: {
                initParametersBytes: JSON.stringify({ name, chaincodeName })
            }
        });
        return res.data;
    } catch (error) {
        console.error("Error occurred while invoking TokenElementInitialize:", error);
        return [];
    }
}

export const invokeFireflyListeners = async (coreUrl: string, contractName: string, eventName: string, interfaceId: string) => {
    try {
        const res = await fireflyAPI.post(`${coreUrl}/api/v1/namespaces/default/contracts/listeners`, {
            "interface": {
                "id": interfaceId
            },
            "location": {
                "channel": "default",
                "chaincode": contractName
            },
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


export const registerAPI = async (coreUrl: string, chaincodeName: string, channel: string, apiName: string, interfaceId: string) => {
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
