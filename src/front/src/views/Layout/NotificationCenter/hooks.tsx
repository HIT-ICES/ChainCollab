import { useState, useEffect } from 'react';
import { getOrgInvitationList } from '@/api/platformAPI';
import { invitationMsgType } from './types'

export const useOrgInvitionData = (orgId: string): [invitationMsgType[], () => void] => {
    const [invitations, setInvitations] = useState<invitationMsgType[]>([]);
    const [syncFlag, setSyncFlag] = useState<boolean>(false);
    useEffect(() => {
        let ignore = false;
        const fetchData = async (orgId: string) => {
            if (!localStorage.getItem("token")) {
                if (!ignore) setInvitations([]);
                return;
            }
            if (!orgId) {
                if (!ignore) setInvitations([]);
                return;
            }
            try {
                const res = await getOrgInvitationList(orgId);
                if (ignore) return;
                setInvitations(res);
            } catch (err) {
                console.error("获取邀请列表失败", err);
            }
        };
        fetchData(orgId);
        return () => { ignore = true; };
    }, [orgId, syncFlag]);
    const setSync = () => setSyncFlag(!syncFlag);
    return [invitations, setSync];
}

import { useQuery, useMutation } from 'react-query'
import { getUserInvitationList } from '@/api/platformAPI'

export const useUserInvitationList = () => {
    const hasToken = Boolean(localStorage.getItem("token"));
    const { data: invitations = [], isSuccess, isLoading, isError, refetch } = useQuery(['userInvitationData'], async () => {
        return await getUserInvitationList()
    }, {
        enabled: hasToken,
        retry: false,
    })
    return [invitations, {
        isSuccess, isLoading, isError
    }, refetch]
}

import { acceptUserInvitation, declineUserInvitation } from '@/api/platformAPI'

export const useAcceptUserInvitation = () => {
    const { mutate, isLoading, isError, isSuccess } = useMutation((invitationId: string) => {
        return acceptUserInvitation(invitationId)
    })
    return [mutate, {
        isLoading, isError, isSuccess
    }]
}

export const useDeclineUserInvitation = () => {
    const { mutate, isLoading, isError, isSuccess } = useMutation((invitationId: string) => {
        return declineUserInvitation(invitationId)
    })
    return [mutate, {
        isLoading, isError, isSuccess
    }]
}
