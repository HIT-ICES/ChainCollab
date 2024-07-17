import api from '@/api/apiConfig';
import { useState, useEffect } from 'react';

import { retrieveBPMNInstance } from '@/api/externalResource';
import { getResourceSets } from '@/api/resourceAPI';
import { useAppSelector } from '@/redux/hooks';
import { useQuery } from 'react-query';

export const useBPMNIntanceDetailData = (BPMNInstanceId: string) => {
    const [BPMNInstanceData, setBPMNInstanceData] = useState<any>({})
    const [syncFlag, setSyncFlag] = useState(false)
    useEffect(() => {
        let ignore = false
        const fetchData = async () => {
            const response = await retrieveBPMNInstance(BPMNInstanceId)
            if (ignore) return [[], () => { }]
            setBPMNInstanceData(response)
        }
        fetchData()
        return () => {
            ignore = true
        }
    }, [BPMNInstanceId, syncFlag])
    return [BPMNInstanceData, () => setSyncFlag(!syncFlag)]

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
        if (!envId) return;
        const fetchData = async () => {
            const response = await getResourceSets(envId, currenOrgId)
            if (ignore) return
            const data = response.map((item: any) => {
                return {
                    "membershipName": item.membershipName,
                    "membershipId": item.membership,
                    "resourceSetId": item.id,
                    "msp": item.msp,
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

import { retrieveBPMN } from '@/api/externalResource'

export const useParticipantsData = (bpmnId: string): [
    any[], () => void
] => {
    const [participants, setParticipants] = useState<any[]>([])
    const [syncFlag, setSyncFlag] = useState(false)
    useEffect(() => {
        let ignore = false
        const fetchData = async () => {
            // const response = await getParticipantsByContent(bpmnContent)
            const response = await retrieveBPMN(bpmnId)
            if (ignore) return [[], () => { }]
            setParticipants(JSON.parse(response.participants))
        }
        fetchData()
        return () => {
            ignore = true
        }
    }, [bpmnId, syncFlag])
    return [participants, () => setSyncFlag(!syncFlag)]
}

export const useBusinessRulesDataByBpmn = (bpmnId: string) => {
    const { data: dmns = [], isLoading, isError, isSuccess, refetch } = useQuery(['dmns', bpmnId], async () => {
        const response = await retrieveBPMN(bpmnId)
        const bpmnContent = response.bpmnContent
        return await getBusinessRulesByContent(
            bpmnContent
        );
    });
    return [dmns, { isLoading, isError, isSuccess }, refetch]
}



import { getBindingByBPMNInstance } from '@/api/externalResource'

export const useBPMNBindingData = (bpmnInstanceId: string): [
    {}, () => void
] => {
    const [bindings, setBindings] = useState<{}>({})
    const [syncFlag, setSyncFlag] = useState(false)
    useEffect(() => {
        let ignore = false
        const fetchData = async () => {
            const response = await getBindingByBPMNInstance(bpmnInstanceId)
            if (ignore) return [{}, () => { }]
            let data = {}
            response.forEach((item: any) => {
                data[item.participant] = item.membershipName
            })
            setBindings(data)
        }
        fetchData()
        return () => {
            ignore = true
        }
    }, [bpmnInstanceId, syncFlag])
    return [bindings, () => setSyncFlag(!syncFlag)]
}

export const useBPMNBindingDataReverse = (bpmnInstanceId: string): [
    {}, () => void
] => {
    const [bindings, setBindings] = useState<{}>({})
    const [syncFlag, setSyncFlag] = useState(false)
    useEffect(() => {
        let ignore = false
        const fetchData = async () => {
            const response = await getBindingByBPMNInstance(bpmnInstanceId)
            if (ignore) return [{}, () => { }]
            let data = {}
            response.forEach((item: any) => {
                data[item.membershipName] = item.participant
            })
            setBindings(data)
        }
        fetchData()
        return () => {
            ignore = true
        }
    }, [bpmnInstanceId, syncFlag])
    return [bindings, () => setSyncFlag(!syncFlag)]
}


import { getFireflyList } from '@/api/resourceAPI.ts';
import { useDmnListData } from '../../Dmn/hooks';
import { getBusinessRulesByContent } from '@/api/translator';
export const useFireflyData = (
    envId: string,
    orgId: string,
    membershipId: string
): [
        {
            "coreURL": string,
            "orgName": string,
        },
        () => void
    ] => {

    const [firefly, setFirefly] = useState({
        coreURL: "",
        orgName: "",
    });
    const [syncFlag, setSyncFlag] = useState(false);

    useEffect(() => {
        let ignore = false;
        const fetchData = async () => {
            try {
                const data = await getFireflyList(envId, orgId);
                const finalData = data.find((item: any) => item.membershipId === membershipId);
                if (ignore) return
                setFirefly(finalData);
            } catch (e) {
                console.log(e);
            }
        }
        fetchData();
        return () => { ignore = true; }
    }, [syncFlag, envId, orgId, membershipId]);
    return [firefly, () => { setSyncFlag(!syncFlag) }];
}