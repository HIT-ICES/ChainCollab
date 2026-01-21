import { Button, Table, Input, Select, Modal, Space, message, Tooltip, Card, Typography, Tag } from "antd"
import { CopyOutlined } from "@ant-design/icons"
import {
    useEthereumIdentities,
    useCreateEthereumIdentity,
    useSyncEthereumIdentity,
    useSyncAllEthereumIdentities
} from "./hooks"
import { useAPIKeyList, useRegisterAPIKey, useResourceSet } from '@/views/Consortium/FabricUsers/hooks'

import React from "react"

const { Text } = Typography

const renderCopyable = (value: string, onCopy, monospace = false) => (
    <Space size="small">
        <Text
            style={{
                fontFamily: monospace ? "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" : undefined,
                color: "rgba(0, 0, 0, 0.88)",
            }}
        >
            {value || "-"}
        </Text>
        {value ? (
            <Tooltip title="Copy">
                <Button
                    size="small"
                    type="text"
                    icon={<CopyOutlined />}
                    onClick={() => onCopy(value)}
                />
            </Tooltip>
        ) : null}
    </Space>
)

const tableSchema = (onSync, onCopy) => [
    {
        title: "ID",
        dataIndex: "Id",
        key: "Id",
        width: 220,
        render: (text: string) => renderCopyable(text, onCopy, true),
    },
    {
        title: "Name",
        dataIndex: "name",
        key: "name",
        width: 200,
        render: (text: string) => (
            <Space size="small">
                <Tag color="blue">{text || "-"}</Tag>
                {text ? (
                    <Tooltip title="Copy">
                        <Button
                            size="small"
                            type="text"
                            icon={<CopyOutlined />}
                            onClick={() => onCopy(text)}
                        />
                    </Tooltip>
                ) : null}
            </Space>
        ),
    },
    {
        title: "Address",
        dataIndex: "address",
        key: "address",
        width: 260,
        render: (text: string) => (
            renderCopyable(text, onCopy, true)
        ),
    },
    {
        title: "Private Key",
        dataIndex: "private_key",
        key: "private_key",
        width: 320,
        render: (text: string) => (
            renderCopyable(text, onCopy, true)
        ),
    },
    {
        title: "Action",
        key: "action",
        width: 160,
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
    const [messageApi, contextHolder] = message.useMessage();

    const handleCopy = async (value: string) => {
        try {
            await navigator.clipboard.writeText(value);
            messageApi.success("Copied");
        } catch (error) {
            messageApi.error("Copy failed");
        }
    };
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
                {contextHolder}
                <Card
                    size="small"
                    title="Ethereum Identities"
                    style={{ borderRadius: 8 }}
                    bodyStyle={{ background: "#fafafa" }}
                    extra={
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
                    }
                >
                    <Table
                        size="small"
                        bordered
                        columns={tableSchema((identityId) => {
                            syncIdentity(
                                { identityId },
                                {
                                    onSuccess: () => {
                                        refetch();
                                    },
                                }
                            );
                        }, handleCopy)}
                        dataSource={dataToShow}
                        loading={isLoading || syncLoading || syncAllLoading}
                        pagination={{ pageSize: 10 }}
                    />
                </Card>
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
