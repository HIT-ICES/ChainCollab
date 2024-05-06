import React from 'react';
import { Button, Table, Select, Modal } from 'antd';
const Option = Select.Option;
import { FabricUserTable, FabricIdentityModal } from './components';
import { useLocation } from 'react-router-dom';
import { useAppSelector } from '@/redux/hooks';
import {
    useFabricIdentities
    , useCreateFabricIdentity
    , useAPIKeyList
    , useRegisterAPIKey
    , useEnvironments

} from './hooks';
import styled from 'styled-components';


const FabricUsers = () => {
    const [addFabricIdentityModalVisible, setAddFabricIdentityModalVisible] = React.useState(false);
    const [selectedEnv, setSelectedEnv] = React.useState("");
    const location = useLocation();
    const selectMembershipId = location.pathname.split('/')[6];
    const { currentConsortiumId } = useAppSelector((state) => state.consortium);
    const [environments, { isLoading: envLoading, isError: envError, isSuccess: envSuccess }, envRefetch] = useEnvironments(currentConsortiumId);

    const [apiKeyList, { isLoading: apiKeyLoading, isError: apiKeyError, isSuccess: apiKeySuccess }, apiKeyRefetch] = useAPIKeyList(selectMembershipId, selectedEnv);
    const [registerAPIKey, { isLoading: registerAPIKeyLoading, isError: registerAPIKeyError, isSuccess: registerAPIKeySuccess }] = useRegisterAPIKey();
    const [fabricIdentities, { isLoading: fabricIdentitiesLoading, isError: fabricIdentitiesError, isSuccess: fabricIdentitiesSuccess }, fabricIdentitiesRefetch] = useFabricIdentities(selectedEnv, selectMembershipId);
    const [createFabricIdentity, { isLoading: createFabricIdentityLoading, isError: createFabricIdentityError, isSuccess: createFabricIdentitySuccess }] = useCreateFabricIdentity();

    return (
        <div style={{ gap: "20px" }} >
            {/* Env Selector */}
            <div>
                <Select value={selectedEnv} loading={
                    envLoading
                }
                    onChange={(value) => {
                        setSelectedEnv(value);
                    }} style={{ width: 200 }}
                >
                    <Option value={null}>Select Environment</Option>
                    {environments.map((env) => {
                        return (
                            <Option value={env.id}
                            >{env.name}</Option>
                        )
                    })}
                </Select>
            </div>
            {/* API Key Table */}


            {/* Fabric User Table */}
            <div >
                <div style={{ display: 'flex', justifyContent: "flex-end" }} >
                    <Button
                        style={{ marginBottom: 20 }}
                        type="primary"
                        onClick={() => { setAddFabricIdentityModalVisible(true) }

                        }>Add Fabric User</Button>
                </div>


                <FabricIdentityModal visible={addFabricIdentityModalVisible}
                    setVisible={setAddFabricIdentityModalVisible}
                    envId={selectedEnv}
                    membershipId={selectMembershipId}
                />
                <FabricUserTable membershipId={selectMembershipId} envId={selectedEnv} />
            </div>
        </div>
    );
}

export default FabricUsers;