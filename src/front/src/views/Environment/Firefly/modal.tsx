import React, { useState } from "react";
import { Modal, Form, Input, Button, Select, Space } from "antd";
import type { SelectProps } from "antd";
import { SmileTwoTone } from "@ant-design/icons";
interface Props {
  onSubmit: (data: { membershipName: string }) => void;
}
interface option {
  value: string;
  label: string;
}

const NewFireflyNode: React.FC<Props> = ({ onSubmit }) => {
  // Modal相关
  const [isModalOpen, setIsModalOpen] = useState(false);

  const options: SelectProps["options"] = [];
  // Select memberships
  const [memberships, setMemberships] = useState<option[]>([
    {
      value: "defaultMembership",
      label: "defaultMembership",
    },
  ]);
  //orderer nodes
  const [orderernodes, setOrderernodes] = useState<option[]>([
    {
      value: "default orderer node",
      label: "default orderer node",
    },
  ]);
  //peerer nodes
  const [peernodes, setPeernodes] = useState<option[]>([
    {
      value: "default peer node",
      label: "default peer node",
    },
  ]);
  // CA
  const [CAs, setCAs] = useState<option[]>([
    {
      value: "default CA",
      label: "default CA",
    },
  ]);
  //Channels
  const [channels, setChannels] = useState<option[]>([
    {
      value: "default channel",
      label: "default channel",
    },
  ]);

  // fetch selecteddetails from
  const getSelectedDetails = () => {
    // logic
    // setMemberships();
    // setOrderernodes();
    // setPeernodes();
    // setCAs();
    // setChannels();
  };

  const handleChange = (value: string) => {
  };

  const showModal = () => {
    setIsModalOpen(true);
  };

  const handleOk = () => {
    setIsModalOpen(false);
  };

  const handleCancel = () => {
    setIsModalOpen(false);
  };

  // Form相关
  const onFinish = (values: any) => {
    onSubmit(values);
  };

  const onFinishFailed = (errorInfo: any) => {
  };

  // type FieldType = {
  //   membershipName?: string;
  // };

  return (
    <>
      <Button type="primary" onClick={showModal}>
        ADD FIREFLY NODE
      </Button>
      <Modal
        title="Add membership"
        open={isModalOpen}
        onOk={handleOk}
        onCancel={handleCancel}
        destroyOnClose
        okButtonProps={{
          htmlType: "submit",
          form: "basic",
        }}
      >
        <Space>
          <SmileTwoTone></SmileTwoTone>
          <div
            style={{
              color: "gray", // 设置字体颜色为灰色
              fontWeight: "bold", // 应用粗体样式
              fontStyle: "italic", // 应用斜体样式
            }}
          >
            Note: Firefly should only ne deployed to given channel once per
            membership to avoid potential issues during identity registration.
          </div>{" "}
        </Space>

        <Form
          name="basic"
          labelCol={{ span: 8 }}
          wrapperCol={{ span: 16 }}
          style={{ maxWidth: 600 }}
          onFinish={onFinish}
          onFinishFailed={onFinishFailed}
          autoComplete="off"
          preserve={false} // 在Modal关闭后，销毁Field
        >
          <Form.Item
            rules={[{ required: true }]}
            label="Membership Name"
            name="membershipName"
          >
            <Select
              style={{ width: "100%" }}
              placeholder=""
              options={memberships}
            />
          </Form.Item>
          <Form.Item
            label="Node Name"
            name="nodeName"
            rules={[{ required: true, message: "Please input node name!" }]}
          >
            <Input allowClear />
          </Form.Item>
          <Form.Item
            rules={[{ required: true }]}
            label="Orderer node"
            name="ordererNode"
          >
            <Select
              style={{ width: "100%" }}
              placeholder=""
              options={orderernodes}
            />
          </Form.Item>
          <Form.Item
            rules={[{ required: true }]}
            label="Peer node"
            name="peerNode"
          >
            <Select
              style={{ width: "100%" }}
              placeholder=""
              options={peernodes}
            />
          </Form.Item>
          <Form.Item rules={[{ required: true }]} label="CA" name="CA">
            <Select style={{ width: "100%" }} placeholder="" options={CAs} />
          </Form.Item>
          <Form.Item
            rules={[{ required: true }]}
            label="Channels to deployed"
            name="channels"
          >
            <Select style={{ width: "100%" }} placeholder="" options={channels} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default NewFireflyNode;
