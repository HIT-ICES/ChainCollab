import * as React from 'react';
import {Modal, Button, Input, Select, List, Typography, Form} from 'antd';

const participants = [
  {
    name: "Participant A",
    memberships: ["Membership 1", "Membership 2", "Membership 3"]
  },
  {
    name: "Participant B",
    memberships: ["Membership 4", "Membership 5", "Membership 6"]
  },
  {
    name: "Participant C",
    memberships: ["Membership 7", "Membership 8", "Membership 9"]
  }
];

export default function ParticipantModal({dataElementId, open: isModalOpen, onClose}) {
  const title = `Participant ID: ${dataElementId}`;

  const [form] = Form.useForm();
  const [componentSize, setComponentSize] = React.useState('default');
  const onFormLayoutChange = ({ size }) => {
    setComponentSize(size);
  };

  const [selectedData, setSelectedData] = React.useState({ participant: '', memberships: '' });

  const onParticipantChange = () => {
    form.setFieldsValue({ membership: undefined });
    setSelectedData({ ...selectedData, membership: '' }); // 清除membership数据
  };

  const onFinish = (values) => {
    setSelectedData(values); // 存储表单提交后的数据
  };

  const handleOk = () => {
    onClose && onClose(true);
  };

  const handleCancel = () => {
    onClose && onClose(false);
  };

  return (<Modal
    visible={isModalOpen}
    title={title}
    onOk={handleOk}
    onCancel={handleCancel}
    footer={[
      <Button key="back" onClick={handleCancel}>
        Return
      </Button>,
    ]}
  >
    <Form form={form} onFinish={onFinish}
               labelCol={{
                 span: 4,
               }}
               wrapperCol={{
                 span: 14,
               }}
               layout="horizontal"
               initialValues={{
                 size: componentSize,
               }}
               onValuesChange={onFormLayoutChange}
               // size={componentSize}
               style={{
                 maxWidth: 600,
               }}
    >
      <Form.Item name="participant" label="Participant" rules={[{ required: true }]}>
        <Select placeholder="Select a participant" onChange={onParticipantChange}>
          {participants.map(participant => (
            <Select.Option key={participant.name} value={participant.name}>
              {participant.name}
            </Select.Option>
          ))}
        </Select>
      </Form.Item>
      <Form.Item name="membership" label="Membership" rules={[{ required: true }]}>
        <Select placeholder="Select a membership" disabled={!form.getFieldValue('participant')}>
          {participants.find(participant => participant.name === form.getFieldValue('participant'))?.memberships.map(membership => (
            <Select.Option key={membership} value={membership}>
              {membership}
            </Select.Option>
          ))}
        </Select>
      </Form.Item>
      <Form.Item label="提交" >
        <Button type="primary" htmlType="submit">submit</Button>
      </Form.Item>
    </Form>
  </Modal>);
}
