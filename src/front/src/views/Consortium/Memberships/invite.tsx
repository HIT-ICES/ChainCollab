import React, { useEffect, useState } from "react";
import { Modal, Form, Input, Button } from "antd";
import { useAppSelector } from "@/redux/hooks";
import { getOrgList } from "@/api/platformAPI";

interface Props {
  onSubmit: (orgId: string, consortiumId: string) => Promise<boolean>;
}

const InviteMembership: React.FC<Props> = ({ onSubmit }) => {
  // Modal相关
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isValidInput, setIsValidInput] = useState(true);

  const orgId = useAppSelector((state) => state.org).currentOrgId;
  const consortiumId = useAppSelector(
    (state) => state.consortium
  ).currentConsortiumId;

  const showModal = () => {
    setIsModalOpen(true);
  };

  const handleCancel = () => {
    setIsModalOpen(false);
    setIsValidInput(true);
  };

  // Form相关
  const onFinish = async (values: any) => {
    const invitedOrgId = values.orgId;
    const res = await onSubmit(invitedOrgId, consortiumId);
    if (res) {
      setIsModalOpen(false);
    } else {
      setIsValidInput(false);
    }
  };

  const onFinishFailed = (errorInfo: any) => {
    console.log("Failed:", errorInfo);
  };

  type FieldType = {
    orgId: string;
  };

  return (
    <>
      <Button type="primary" onClick={showModal}>
        INVITE ORGANIZATIONS
      </Button>
      <Modal
        title="Invite Organizations"
        open={isModalOpen}
        // onOk={handleOk}
        onCancel={handleCancel}
        destroyOnClose
        okButtonProps={{
          htmlType: "submit",
          form: "basic",
        }}
      >
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
          <Form.Item<FieldType>
            label="Org ID"
            name="orgId"
            rules={[
              { required: true, message: "Please input organization's ID!" },
            ]}
            validateStatus={!isValidInput ? "error" : undefined}
            help={
              !isValidInput
                ? "This ID is invalid! Please input again."
                : undefined
            }
          >
            <Input allowClear />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default InviteMembership;
