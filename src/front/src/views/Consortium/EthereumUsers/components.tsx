import { Button, Table, Input, Select, Modal, Space } from "antd"
import {
    useEthereumIdentities,
    useCreateEthereumIdentity,
    useSyncEthereumIdentity,
    useSyncAllEthereumIdentities
} from "./hooks"
import { useAPIKeyList, useRegisterAPIKey, useResourceSet } from '@/views/Consortium/FabricUsers/hooks'

import React from "react"

const tableSchema = (onSync) => [
    {
        title: "ID",
        dataIndex: "Id",
        key: "Id",
    },
    {
        title: "Name",
        dataIndex: "name",
        key: "name",
    },
    {
        title: "Address",
        dataIndex: "address",
        key: "address",
    },
    {
        title: "Private Key",
        dataIndex: "private_key",
        key: "private_key",
    },
    {
        title: "Action",
        key: "action",
        render: (text: any, record: any) => (
            <span>
                <Button type="link">Edit</Button>
                <Button type="link">Delete</Button>
                <Button type="link" onClick={() => onSync(record.Id)}>Sync</Button>
            </span>
        ),
    },
]

export const EthereumUserTable = ({ membershipId, envId }) => {
    const [ethereumIdentities, { isLoading, isError, isSuccess }, refetch] = useEthereumIdentities(envId, membershipId);
    const [syncIdentity, { isLoading: syncLoading }] = useSyncEthereumIdentity();
    const [syncAll, { isLoading: syncAllLoading }] = useSyncAllEthereumIdentities();
    const dataToShow = isSuccess ? ethereumIdentities.map((item, index) => {
        return {
            key: index,
            Id: item.id,
            name: item.name,
            address: item.address,
            private_key: item.private_key,
        }
    }
    ) : [];
    return (
        isError ? <div>error...</div> :
            <>
                <Space style={{ marginBottom: 12 }}>
                    <Button
                        onClick={() => {
                            syncAll(
                                { ethEnvironmentId: envId, membershipId },
                                { onSuccess: () => refetch() }
                            );
                        }}
                        loading={syncAllLoading}
                    >
                        Sync All
                    </Button>
                </Space>
                <Table
                    columns={tableSchema((identityId) => {
                        syncIdentity(
                            { identityId },
                            {
                                onSuccess: () => {
                                    refetch();
                                },
                            }
                        );
                    })}
                    dataSource={dataToShow}
                    loading={isLoading || syncLoading || syncAllLoading}
                />
            </>
    )
}

export const EthereumIdentityModal = ({
    envId,
    membershipId,
    visible,
    setVisible
}) => {
    const [mutate, { isLoading, isError, isSuccess }] = useCreateEthereumIdentity();
    const [name, setName] = React.useState('');

    return (
        <Modal
            title="Add Ethereum User"
            open={visible}
            onOk={() => {
                mutate({
                    ethEnvironmentId: envId,
                    membershipId: membershipId,
                    name: name,
                }, {
                    onSuccess: () => {
                        setVisible(false);
                        setName('');
                    },
                    onError: (error) => {
                        console.error("Failed to create Ethereum identity:", error);
                    }
                });
            }}
            onCancel={() => {
                setVisible(false);
                setName('');
            }}
            confirmLoading={isLoading}
        >
            <div>
                Name<br />
                <Input
                    placeholder="Ethereum User Name"
                    style={{ width: '50%', }}
                    value={name}
                    onChange={(e) => {
                        setName(e.target.value);
                    }}
                />
            </div>
            {isError && (
                <div style={{ color: 'red', marginTop: '10px' }}>
                    Failed to create Ethereum identity. Please try again.
                </div>
            )}
        </Modal>
    )
}
