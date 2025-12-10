import React, { useState, useEffect, useRef } from 'react';
import type { ChangeEvent } from 'react';
import { Modal, Table, Input } from 'antd';
import type { DmnDefinition, UploadableDmn } from '@/types/modeler';
import type { ColumnsType } from 'antd/es/table';
import Draggable from 'react-draggable';
import type { DraggableEvent, DraggableData } from 'react-draggable';

interface UploadDmnModalProps {
  dmnData: Map<string, DmnDefinition>;
  open: boolean;
  setOpen: (open: boolean) => void;
  onUpload: (items: UploadableDmn[]) => Promise<void> | void;
}

const UploadDmnModal: React.FC<UploadDmnModalProps> = ({
  dmnData,
  open,
  setOpen,
  onUpload
}) => {

  const [data, setData] = useState<UploadableDmn[]>([]);
  const draggleRef = useRef<HTMLDivElement | null>(null);
  const [dragDisabled, setDragDisabled] = useState(true);
  const [bounds, setBounds] = useState({ left: 0, top: 0, bottom: 0, right: 0 });

  useEffect(() => {
    if (!dmnData) {
      setData([]);
      return;
    }
    const formattedData: UploadableDmn[] = Array.from(dmnData.entries()).map(([id, value]) => ({
      id,
      name: value.name ?? id,
      uploadName: value.name ?? id,
      dmnContent: value.dmnContent,
      svgContent: value.svgContent
    }));
    setData(formattedData);
  }, [dmnData]);

  const handleOk = async () => {
    const validItems = data.filter((item) => item.uploadName?.trim().length);
    if (validItems.length) {
      await onUpload(validItems);
    }
    setOpen(false);
  };

  const onStart = (_event: DraggableEvent, uiData: DraggableData) => {
    const { clientWidth, clientHeight } = document.documentElement;
    const targetRect = draggleRef.current?.getBoundingClientRect();
    if (!targetRect) {
      return;
    }
    setBounds({
      left: -targetRect.left + uiData.x,
      right: clientWidth - (targetRect.right - uiData.x),
      top: -targetRect.top + uiData.y,
      bottom: clientHeight - (targetRect.bottom - uiData.y),
    });
  };

  const handleCancel = () => setOpen(false);

  const handleInputChange = (index: number, event: ChangeEvent<HTMLInputElement>) => {
    const newData = [...data];
    newData[index] = {
      ...newData[index],
      uploadName: event.target.value
    };
    setData(newData);
  };

  const columns: ColumnsType<UploadableDmn> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id'
    },
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name'
    },
    {
      title: 'Upload Name',
      dataIndex: 'uploadName',
      key: 'uploadName',
      render: (_text: string, _record: UploadableDmn, index: number) => (
        <Input
          value={data[index]?.uploadName}
          onChange={(event) => handleInputChange(index, event)}
        />
      )
    }
  ];

  return (
    <Modal
      title="Upload Dmns"
      open={open}
      onOk={handleOk}
      okButtonProps={{ disabled: !data.length }}
      onCancel={handleCancel}
      destroyOnClose
      centered
      width={720}
      styles={{
        header: {
          borderBottom: 'none',
          padding: '24px 32px',
          fontSize: 18,
          fontWeight: 600
        },
        body: {
          padding: '0 32px 24px',
          background: '#f8fafc'
        },
        footer: {
          borderTop: 'none',
          padding: '16px 32px 32px'
        }
      }}
      centered
      width={640}
      styles={{
        header: {
          borderBottom: '1px solid #e2e8f0',
          padding: '16px 24px'
        },
        body: {
          padding: '0 24px 24px',
          background: '#f8fafc',
          maxHeight: '60vh',
          overflowY: 'auto'
        },
        footer: {
          borderTop: 'none',
          padding: '16px 24px 24px'
        }
      }}
      modalRender={(modal) => (
        <Draggable
          nodeRef={draggleRef}
          disabled={dragDisabled}
          bounds={bounds}
          onStart={onStart}
        >
          <div
            ref={draggleRef}
            onMouseOver={() => dragDisabled && setDragDisabled(false)}
            onMouseOut={() => setDragDisabled(true)}
          >
            {modal}
          </div>
        </Draggable>
      )}
    >
      <Table<UploadableDmn>
        dataSource={data}
        columns={columns}
        rowKey="id"
        pagination={false}
        size="small"
        bordered
        style={{ background: '#fff', borderRadius: 12, overflow: 'hidden' }}
      />
    </Modal>
  );
};

export default UploadDmnModal;
