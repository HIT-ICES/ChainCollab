import { useEffect, useState } from 'react';
import { useAppDispatch, useAppSelector } from '@/redux/hooks'
import { useQuery } from 'react-query'
import { getEnvironment } from '@/api/platformAPI'

export const useEnvInfo = () => {
    const currentConsortiumId = useAppSelector(state => state.consortium.currentConsortiumId)
    const currentEnvId = useAppSelector(state => state.env.currentEnvId)
    const { data: envInfo = {}, isLoading, isError, isSuccess, refetch } = useQuery(['envInfo', currentEnvId, currentConsortiumId], async () => {
        return await getEnvironment(currentEnvId, currentConsortiumId)
    }
    );
    return [envInfo, refetch]
}

import { getMembershipList } from '@/api/platformAPI'

export const useMembershipListData = () => {
    const currentConsortiumId = useAppSelector(state => state.consortium.currentConsortiumId)
    const currentOrgId = useAppSelector(state => state.org.currentOrgId)

    const { data: membershipList = [], isLoading, isError, isSuccess, refetch } = useQuery(['membershipList', currentConsortiumId], async () => {
        return await getMembershipList(currentConsortiumId)
    });

    return [membershipList, refetch]
}
