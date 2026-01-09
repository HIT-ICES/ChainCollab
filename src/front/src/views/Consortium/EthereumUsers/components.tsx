import { Button, Table, Input, Select, Modal } from "antd"
import {
    useEthereumIdentities, useCreateEthereumIdentity
} from "./hooks"
import { useAPIKeyList, useRegisterAPIKey, useResourceSet } from '@/views/Consortium/FabricUsers/hooks'

import React from "react"

const tableSchema = [
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
            </span>
        ),
    },
]

export const EthereumUserTable = ({ membershipId, envId }) => {
    const [ethereumIdentities, { isLoading, isError, isSuccess }, refetch] = useEthereumIdentities(envId, membershipId);
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
            <Table columns={tableSchema} dataSource={dataToShow} loading={isLoading} />
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