import { useEffect, useState } from 'react'
import { retrieveBPMNInstance, retrieveBPMN } from '@/api/externalResource'
import api from '@/api/apiConfig';
import { getResourceSets, getFireflyList } from '@/api/resourceAPI';
import { useAppSelector } from '@/redux/hooks';

export const useBPMNIntanceDetailData = (BPMNInstanceId: string) => {
    const [BPMNInstanceData, setBPMNInstanceData] = useState<any>({})
    const [syncFlag, setSyncFlag] = useState(false)
    const [ready, setReady] = useState(false)
    useEffect(() => {
        let ignore = false
        const fetchData = async () => {
            setReady(false)
            const response = await retrieveBPMNInstance(BPMNInstanceId)
            if (ignore) return
            setBPMNInstanceData(response)
            setReady(true)
        }
        fetchData()
        return () => {
            ignore = true
        }
    }, [BPMNInstanceId, syncFlag])
    return [BPMNInstanceData, ready, () => setSyncFlag(!syncFlag)]
}

export const useBPMNDetailData = (BPMNId: string) => {
    const [BPMNData, setBPMNData] = useState<any>({})
    const [syncFlag, setSyncFlag] = useState(false)
    const [ready, setReady] = useState(false)
    useEffect(() => {
        let ignore = false
        if (!BPMNId) return
        const fetchData = async () => {
            setReady(false)
            const bpmn = await retrieveBPMN(BPMNId)
            if (ignore) return
            setBPMNData(bpmn)
            setReady(true)
        }
        fetchData()
        return () => {
            ignore = true
        }
    }, [BPMNId, syncFlag])
    return [BPMNData, ready, () => setSyncFlag(!syncFlag)]
}

export const useAvailableMembers = (envId: string): [
    any[],
    () => void
] => {
    const currenOrgId = useAppSelector((state) => state.org.currentOrgId)
    const [members, setMembers] = useState<any[]>([])
    const [syncFlag, setSyncFlag] = useState(false)
    useEffect(() => {
        let ignore = false
        const fetchData = async () => {
            const response = await getResourceSets(envId, currenOrgId)
            if (ignore) return [[], () => { }]
            const data = response.map((item: any) => {
                return {
                    "membershipName": item.membershipName,
                    "membershipId": item.membership,
                }
            })
            setMembers(data)
        }
        fetchData()
        return () => {
            ignore = true
        }
    }, [envId, syncFlag])
    return [members, () => setSyncFlag(!syncFlag)]
}

export const useFireflyData = (
    envId: string,
    membershipId: string
): [
        {
            coreUrl: string,
        },
        () => void
    ] => {

    const [firefly, setFirefly] = useState({
        coreUrl: ""
    });
    const [syncFlag, setSyncFlag] = useState(false);

    useEffect(() => {
        let ignore = false;
        const fetchData = async () => {
            try {
                if (!envId ||
                    !membershipId) {
                    setFirefly({ coreUrl: "" });
                    return;
                }

                const data = await getFireflyList(envId, null);
                if (ignore) return [[], () => { }];
                const filterData = data.filter((item: any) => item.membership === membershipId);
                setFirefly(filterData[0]);
            } catch (e) {
            }
        }
        fetchData();
        return () => { ignore = true; }
    }, [syncFlag, envId, membershipId]);
    return [firefly, () => { setSyncFlag(!syncFlag) }];
}

// Firefly Hook

import {
    getAllEvents, getAllGateways, getAllMessages, getAllBusinessRules,
} from '@/api/executionAPI'

export const useAllFireflyData = (
    coreUrl: string, contractName: string, bpmnInstanceId: string
): [
        any[],
        any[],
        any[],
        any[],
        boolean,
        () => void,
        {
            connected: boolean,
            lastSyncAt: string | null,
            error: string | null,
        }
    ] => {
    const [events, setEvents] = useState<any[]>([]);
    const [gateways, setGateways] = useState<any[]>([]);
    const [messages, setMessages] = useState<any[]>([]);
    const [businessRules, setBusinessRules] = useState<any[]>([]);
    const [syncFlag, setSyncFlag] = useState(false);
    const [ready, setReady] = useState(false);
    const [meta, setMeta] = useState({
        connected: false,
        lastSyncAt: null as string | null,
        error: null as string | null,
    });

    const normalizeState = (item: any, keys: string[]) => {
        for (const key of keys) {
            if (typeof item?.[key] === "number") {
                return item[key];
            }
        }
        if (typeof item?.state === "number") {
            return item.state;
        }
        return 0;
    };

    useEffect(() => {
        let ignore = false;
        const fetchData = async () => {
            setReady(false);
            if (!coreUrl || !contractName || !bpmnInstanceId || coreUrl === "http://") {
                if (!ignore) {
                    setEvents([]);
                    setGateways([]);
                    setMessages([]);
                    setBusinessRules([]);
                    setMeta({
                        connected: false,
                        lastSyncAt: null,
                        error: "Execution context not ready",
                    });
                    setReady(true);
                }
                return;
            }
            try {
                const [healthRes, eventsRes, gatewaysRes, messagesRes, businessRulesRes] = await Promise.allSettled([
                    axios.get(`${coreUrl}/api/v1/status`, { timeout: 4000 }),
                    getAllEvents(coreUrl, contractName, bpmnInstanceId),
                    getAllGateways(coreUrl, contractName, bpmnInstanceId),
                    getAllMessages(coreUrl, contractName, bpmnInstanceId),
                    getAllBusinessRules(coreUrl, contractName, bpmnInstanceId),
                ]);
                if (ignore) return;

                const eventsRaw = eventsRes.status === "fulfilled" && Array.isArray(eventsRes.value)
                    ? eventsRes.value
                    : [];
                const gatewaysRaw = gatewaysRes.status === "fulfilled" && Array.isArray(gatewaysRes.value)
                    ? gatewaysRes.value
                    : [];
                const messagesRaw = messagesRes.status === "fulfilled" && Array.isArray(messagesRes.value)
                    ? messagesRes.value
                    : [];
                const businessRulesRaw = businessRulesRes.status === "fulfilled" && Array.isArray(businessRulesRes.value)
                    ? businessRulesRes.value
                    : [];

                setEvents(eventsRaw.map((item: any) => ({
                    ...item,
                    type: "event",
                    state: normalizeState(item, ["EventState", "eventState"]),
                })));
                setGateways(gatewaysRaw.map((item: any) => ({
                    ...item,
                    type: "gateway",
                    state: normalizeState(item, ["GatewayState", "gatewayState"]),
                })));
                setMessages(messagesRaw.map((item: any) => ({
                    ...item,
                    type: "message",
                    state: normalizeState(item, ["MsgState", "msgState"]),
                })));
                setBusinessRules(businessRulesRaw.map((item: any) => ({
                    ...item,
                    type: "businessRule",
                    state: normalizeState(item, ["State", "state"]),
                })));

                const connected = healthRes.status === "fulfilled";
                const firstError = [
                    healthRes,
                    eventsRes,
                    gatewaysRes,
                    messagesRes,
                    businessRulesRes,
                ].find((res: any) => res.status === "rejected") as PromiseRejectedResult | undefined;

                setMeta({
                    connected,
                    lastSyncAt: new Date().toISOString(),
                    error: firstError ? String(firstError.reason || "Unknown error") : null,
                });
            } catch (error: any) {
                if (ignore) return;
                setEvents([]);
                setGateways([]);
                setMessages([]);
                setBusinessRules([]);
                setMeta({
                    connected: false,
                    lastSyncAt: new Date().toISOString(),
                    error: String(error?.message || error || "Sync failed"),
                });
            } finally {
                if (!ignore) {
                    setReady(true);
                }
            }
        }
        fetchData();
        return () => { ignore = true; }
    }, [syncFlag, coreUrl, contractName, bpmnInstanceId]);
    return [
        events,
        gateways,
        messages,
        businessRules,
        ready,
        () => { setSyncFlag(syncFlag => !syncFlag); },
        meta,
    ];
}

import { useQuery } from 'react-query'
import { getFireflyIdentity } from "@/api/platformAPI"
import axios from 'axios';

export const useAvailableIdentity = () => {
    const currenOrgId = useAppSelector((state) => state.org.currentOrgId)
    const currenEnvId = useAppSelector((state) => state.env.currentEnvId)
    const { data, isLoading, isError, isSuccess, refetch } = useQuery(['availableIdentity', currenOrgId, currenEnvId], async () => {
        const res = await getFireflyIdentity(currenEnvId, currenOrgId)
        return res
    })
    return [data, isLoading, refetch]
}

export const useFireflyIdentity = (coreUrl: string, idInFirefly: string) => {
    const { data, isLoading } = useQuery([' fireflyIdentity', idInFirefly], async () => {
        const res = await axios.get(`${coreUrl}/api/v1/identities/${idInFirefly}/verifiers`)
        return res.data
    })
    return [data, isLoading]
}
