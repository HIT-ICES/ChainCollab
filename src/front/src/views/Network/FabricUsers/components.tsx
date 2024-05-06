import { Button, Table, Input, Select, Modal } from "antd"
import {
    useFabricIdentities, useCreateFabricIdentity,
    useAPIKeyList, useRegisterAPIKey,
    useResourceSet
} from "./hooks"

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
        title: "Signer",
        dataIndex: "signer",
        key: "signer",
    },
    {
        title: "Secret",
        dataIndex: "secret",
        key: "secret",
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

export const FabricUserTable = ({membershipId, envId}) => {
    const [fabricIdentities, { isLoading, isError, isSuccess }, refetch] = useFabricIdentities(envId, membershipId);
    const dataToShow = isSuccess ? fabricIdentities.map((item, index) => {
        return {
            key: index,
            Id: item.id,
            name: item.name,
            signer: item.signer,
            secret: item.secret,
        }
    }
    ) : [];
    return (
        isError ? <div>error...</div> :
            <Table columns={tableSchema} dataSource={dataToShow} loading={isLoading} />
    )
}


const paramTypes = [
    {
        value: 'boolean',
        label: 'boolean',
    },
    {
        value: 'json',
        label: 'json',
    },
    {
        value: 'string',
        label: 'string',
    },
    {
        value: 'number',
        label: 'number',
    },
    {
        value: 'file',
        label: 'file',
    },

];


export const FabricIdentityModal = ({
    envId,
    membershipId,
    visible,
    setVisible }
) => {

    const [resouceSet, { isLoading:resLoading, isError:resError, isSuccess:resSuccess }] = useResourceSet(envId, membershipId);
    const [mutate, { isLoading, isError, isSuccess }] = useCreateFabricIdentity();
    const [name, setName] = React.useState('');
    const [identityName, setIdentityName] = React.useState('');
    const [secret, setSecret] = React.useState('');
    const [dataSource, setDataSource] = React.useState([]);

    const columns = [
        {
            title: 'Name',
            dataIndex: 'name',
            key: 'name',
            render: (text, record) => (
                <Input value={record.name} onChange={(e) => {
                    const copy = [...dataSource];
                    copy[record.key].name = e.target.value;
                    setDataSource(copy);
                }
                } />
            )
        },
        {
            title: 'Value',
            dataIndex: 'value',
            key: 'value',
            render: (text, record) => (
                <Input value={record.value} onChange={(e) => {
                    const copy = [...dataSource];
                    copy[record.key].value = e.target.value;
                    setDataSource(copy);
                }
                } />
            )
        },
        {
            title: 'Action',
            dataIndex: '',
            key: 'x',
            render: (text, record) => (
                <a
                    href="#"
                    onClick={() => {
                        const copy = [...dataSource];
                        copy.splice(record.key, 1);
                        setDataSource(copy);
                    }}
                >
                    Delete
                </a>
            )
        }
    ];


    return (
        <Modal title="Add Fabric User" open={visible} onOk={() => {
            mutate({
                resourceSetId: resouceSet.id,
                nameOfFabricIdentity: name,
                nameOfIdentity: identityName,
                secretOfIdentity: secret,
                attributes: Object.fromEntries(dataSource.map((item) => [item.name, item.value])),
            });
            setVisible(false);
        }} onCancel={() => {
            // close Modal
            setVisible(false);
        }
        }>
            <div>
                Name<br />
                <Input
                    placeholder="ChangeMessageName"
                    style={{ width: '50%', }}
                    value={name}
                    onChange={
                        (e) => {
                            setName(e.target.value);
                        }
                    }
                />
                <br />
                Identity Name <br />
                <Input
                    placeholder="identityName"
                    style={{ width: '50%', }}
                    value={identityName}
                    onChange={
                        (e) => {
                            setIdentityName(e.target.value);
                        }
                    }
                />
                <br />
                Identity Secret<br />
                <Input
                    placeholder="secret"
                    style={{ width: '50%', }}
                    value={secret}
                    onChange={
                        (e) => {
                            setSecret(e.target.value);
                        }
                    }
                />
                <br />

                Attributes List
                <Table
                    dataSource={dataSource}
                    columns={columns}
                    pagination={false}
                />
                <div style={{ display: 'flex', justifyContent: "flex-end", marginTop: "10px" }} >
                    <Button type="primary" onClick={() => {
                        // ADD New ITEM INTO dataSource
                        const copy = [...dataSource];
                        copy.push({ key: copy.length, name: '', value: '' });
                        setDataSource(copy);
                    }}>Add New Field</Button>
                    {/* delete Last Line */}
                </div>
            </div>
        </Modal>)
}