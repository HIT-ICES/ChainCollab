import { getBusinessRulesByContent,getDecisions, getTasksByContent } from '@/api/translator';
import { retrieveBPMN } from '@/api/externalResource'
import { useQuery } from 'react-query';

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

export const useTaskDataByBpmn = (bpmnId: string) => {
    const { data: taskMap = new Map(), isLoading, isError, isSuccess, refetch } = useQuery(
        ['tasks', bpmnId],
        async () => {
            const response = await retrieveBPMN(bpmnId);
            const bpmnContent = response.bpmnContent;
            const raw = await getTasksByContent(bpmnContent);
            const taskMap = new Map<string, { name: string; documentation?: string }>();
            Object.entries(raw).forEach(([id, info]: any) => {
                taskMap.set(id, {
                    name: info.name,
                    documentation: info.documentation,
                });
            });
            return taskMap;
        }
    );

    return [taskMap, { isLoading, isError, isSuccess }, refetch] as const;
};


export const useBpmnSvg = (bpmnId: string) => {
    const { data: bpmnSvg = '', isLoading, isError, isSuccess, refetch } = useQuery(['bpmnSvg', bpmnId], async () => {
        const response = await retrieveBPMN(bpmnId)
        return response.svgContent
    });
    return [bpmnSvg, { isLoading, isError, isSuccess }, refetch]
}

export const useDecisions = (dmnContent: string) => {
    const { data: decisions = [], isLoading, isError, isSuccess, refetch } = useQuery(['dmnList', dmnContent], async () => {
        if (dmnContent === "") return []
        return await getDecisions(dmnContent)
    });
    return [decisions, { isLoading, isError, isSuccess }, refetch]
}
