import React, { useState, useEffect } from 'react';
import { Modal, Table, Input } from 'antd';
import { forEach } from 'lodash';
import { addDmn } from '@/api/externalResource';

const UploadDmnModal = ({ dmnData, open, setOpen, consortiumId, orgId }) => {

    const [data, setData] = useState([]);
    console.log('data', data);
    useEffect(() => {
        if (dmnData !== null) {
            const formattedData = Array.from(dmnData, ([id, value]) => ({
                id,
                name: value.name,
                uploadName: value.uploadName || '',
                dmnContent: value.dmnContent,
                svgContent: value.svgContent,
            }));
            console.log('formattedData', formattedData);
            setData(formattedData);
        }
    }, [dmnData]);

    
    const handleOk = () => {
        forEach(data, async (item) => {
            await addDmn(consortiumId, item.uploadName, orgId, item.dmnContent, item.svgContent);
        });
        setOpen(false);
    }
    const handleCancel = () => setOpen(false);

    const handleInputChange = (index, event) => {
        const newData = [...data];
        newData[index].uploadName = event.target.value;
        setData(newData);
    };

    const columns = [
        {
            title: 'ID',
            dataIndex: 'id',
            key: 'id',
        },
        {
            title: 'Name',
            dataIndex: 'name',
            key: 'name',
        },
        {
            title: 'Upload Name',
            dataIndex: 'uploadName',
            key: 'uploadName',
            render: (text, record, index) => (
                <Input
                    value={text}
                    onChange={(event) => handleInputChange(index, event)}
                />
            ),
        },
    ];

    return (
        <Modal
            title="Upload Dmns"
            open={open}
            onOk={handleOk}
            onCancel={handleCancel}
        >
            <Table
                dataSource={data}
                columns={columns}
                rowKey="id"
                pagination={false}
            />
        </Modal>
    );
};

export default UploadDmnModal;
