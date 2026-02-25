import { getResourceSets } from '@/api/resourceAPI';
import {
    getEthereumIdentityList,
    createEthereumIdentity,
    retrieveEthereumIdentity,
    syncEthereumIdentity,
    syncAllEthereumIdentities
} from '@/api/platformAPI';
import { useQuery, useMutation } from 'react-query';

export const useEthereumIdentities = (ethEnvironmentId, membershipId) => {
    const { data: ethereumIdentities = [], isLoading, isError, isSuccess, refetch } = useQuery(['ethereumIdentities', ethEnvironmentId, membershipId], async () => {
        if (ethEnvironmentId && membershipId) {
            return await getEthereumIdentityList(ethEnvironmentId, membershipId);
        } else if (ethEnvironmentId) {
            return await getEthereumIdentityList(ethEnvironmentId);
        }
        return [];
    });

    return [ethereumIdentities, {
        isLoading, isError, isSuccess
    }, refetch];
}

export const useCreateEthereumIdentity = () => {
    const { mutate, isLoading, isError, isSuccess } = useMutation(
        ({ ethEnvironmentId, membershipId, name }) => {
            return createEthereumIdentity(ethEnvironmentId, {
                membership_id: membershipId,
                name,
                address: "",
                private_key: "",
            });
        }
    );

    return [mutate, {
        isLoading, isError, isSuccess
    }];
}

export const useSyncEthereumIdentity = () => {
    const { mutate, isLoading, isError, isSuccess } = useMutation(
        ({ identityId }) => {
            return syncEthereumIdentity(identityId);
        }
    );

    return [mutate, {
        isLoading, isError, isSuccess
    }];
}

export const useSyncAllEthereumIdentities = () => {
    const { mutate, isLoading, isError, isSuccess } = useMutation(
        ({ ethEnvironmentId, membershipId }) => {
            return syncAllEthereumIdentities(ethEnvironmentId, membershipId);
        }
    );

    return [mutate, {
        isLoading, isError, isSuccess
    }];
}
