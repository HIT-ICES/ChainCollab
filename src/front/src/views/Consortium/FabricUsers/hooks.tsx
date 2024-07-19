import { getResourceSets } from '@/api/resourceAPI';
import { getFabricIdentityList, createFabricIdentity, getAPIKeyList, registerAPIKey, retrieveFabricIdentity } from '@/api/platformAPI';
import { useQuery, useMutation } from 'react-query';
import { getEnvironmentList } from '@/api/platformAPI';

export const useFabricIdentities = (envId, membershipId) => {
    const { data: fabricIdentities = [], isLoading, isError, isSuccess, refetch } = useQuery(['fabricIdentities'
        , envId, membershipId
    ], async () => {
        const resourceSetRes = await getResourceSets(envId, null, membershipId);
        const resourceSet = resourceSetRes.length > 0 ? resourceSetRes[0] : null;
        if (!resourceSet) {
            return [];
        }
        return await getFabricIdentityList(resourceSet.id);
    }
    );
    return [fabricIdentities, {
        isLoading, isError, isSuccess
    }, refetch];
}

export const useCreateFabricIdentity = () => {
    const { mutate, isLoading, isError, isSuccess } = useMutation(
        ({ resourceSetId, nameOfFabricIdentity, nameOfIdentity, secretOfIdentity, attributes
        }) => {
            return createFabricIdentity(resourceSetId, {
                nameOfFabricIdentity, nameOfIdentity, secretOfIdentity, attributes
            });
        }
    );
    return [mutate, {
        isLoading, isError, isSuccess
    }];
}

export const useAPIKeyList = (membershipId, envId) => {
    const { data: apiKeyList = [], isLoading, isError, isSuccess, refetch } = useQuery(['apiKeyList', membershipId], async () => {
        return await getAPIKeyList(membershipId, envId);
    });

    return [apiKeyList, {
        isLoading, isError, isSuccess
    }, refetch];
}

export const useRegisterAPIKey = () => {
    const { mutate, isLoading, isError, isSuccess } = useMutation(
        ({ membershipId, envId }) => {
            return registerAPIKey(membershipId, envId);
        }
    );
    return [mutate, {
        isLoading, isError, isSuccess
    }];
}

export const useEnvironments = (consortiumId) => {
    const { data: environments = [], isLoading, isError, isSuccess, refetch } = useQuery(['environments', consortiumId], async () => {
        return await getEnvironmentList(
            consortiumId
        );
    });

    return [environments, {
        isLoading, isError, isSuccess
    }, refetch];
}

export const useResourceSet = (envId, membershipId) => {
    const { data: resourceSet = [], isLoading, isError, isSuccess, refetch } = useQuery(['resourceSet', envId, membershipId], async () => {
        const res = await getResourceSets(envId, null, membershipId);
        return res.filter(
            (item) => item.membership === membershipId && item.environment === envId
        )[0]

    });

    return [resourceSet, {
        isLoading, isError, isSuccess
    }, refetch];
}