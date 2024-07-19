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

export const getAllEvents = async (coreUrl: string, contractName: string) => {
    // coreUrl + "/api/v1/namespaces/default/apis/" + name + "/query/GetAllActionEvents"
    try {
        const res = await fireflyAPI.post(`${coreUrl}/api/v1/namespaces/default/apis/${contractName}/query/GetAllActionEvents`, {});
        return res.data;
    } catch (error) {
        console.error("Error occurred while making post request:", error);
        return [];
    }
}

export const getAllGateways = async (coreUrl: string, contractName: string) => {
    try {
        const res = await fireflyAPI.post(`${coreUrl}/api/v1/namespaces/default/apis/${contractName}/query/GetAllGateways`, {});
        return res.data;
    } catch (error) {
        console.error("Error occurred while making post request:", error);
        return [];
    }
}

export const getAllMessages = async (coreUrl: string, contractName: string) => {
    try {
        const res = await fireflyAPI.post(`${coreUrl}/api/v1/namespaces/default/apis/${contractName}/query/GetAllMessages`, {});
        return res.data;
    } catch (error) {
        console.error("Error occurred while making post request:", error);
        return [];
    }
}

// invoke

export const invokeEventAction = async (coreUrl: string, contractName: string, eventId: any) => {
    try {
        const res = await fireflyAPI.post(`${coreUrl}/api/v1/namespaces/default/apis/${contractName}/invoke/${eventId}`, {});
        return res.data;
    } catch (error) {
        console.error("Error occurred while making post request:", error);
        return [];
    }
}

export const invokeGatewayAction = async (coreUrl: string, contractName: string, gtwId: any) => {
    try {
        const res = await fireflyAPI.post(`${coreUrl}/api/v1/namespaces/default/apis/${contractName}/invoke/${gtwId}`, {});
        return res.data;
    } catch (error) {
        console.error("Error occurred while making post request:", error);
        return [];
    }
}

export const invokeMessageAction = async (coreUrl: string, contractName: string, methodName: any, data: any) => {
    try {
        const res = await fireflyAPI.post(`http://${coreUrl}/api/v1/namespaces/default/apis/${contractName}/invoke/${methodName}`, data);
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