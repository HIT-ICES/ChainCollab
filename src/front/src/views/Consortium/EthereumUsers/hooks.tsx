import { getResourceSets } from '@/api/resourceAPI';
import { getEthereumIdentityList, createEthereumIdentity, retrieveEthereumIdentity } from '@/api/platformAPI';
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
                name
            });
        }
    );

    return [mutate, {
        isLoading, isError, isSuccess
    }];
}