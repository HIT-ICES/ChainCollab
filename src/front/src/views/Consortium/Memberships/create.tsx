import React, { useEffect, useState } from "react";
import { Modal, Form, Input, Button, Checkbox } from "antd";
import { useAppSelector } from "@/redux/hooks";
import { getMembershipList } from "@/api/platformAPI";

interface Props {
  onSubmit: (
    orgId: string,
    consortiumId: string,
    membershipName: string,
    createSSI: boolean
  ) => void;
}

const CreateMembership: React.FC<Props> = ({ onSubmit }) => {
  // Modal相关
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isValidInput, setIsValidInput] = useState(true);

  const [membershipList, setMembershipList] = useState([]);

  const orgId = useAppSelector((state) => state.org).currentOrgId;
  const consortiumId = useAppSelector(
    (state) => state.consortium
  ).currentConsortiumId;

  useEffect(() => {
    const fetchAndSetData = async (orgId: string, consortiumId: string) => {
      const data = await getMembershipList(consortiumId);
      const myMembershipList = data
        .filter(
          (item) =>
            item.consortium === consortiumId &&
            item.loleido_organization === orgId
        )
        .map(({ loleido_organization, consortium, ...rest }) => ({
          ...rest,
        }));
      setMembershipList(myMembershipList);
    };
    fetchAndSetData(orgId, consortiumId);
  }, [orgId, consortiumId]);

  const showModal = () => {
    setIsModalOpen(true);
  };

  const handleCancel = () => {
    setIsModalOpen(false);
    setIsValidInput(true);
  };

  // Form相关
  const onFinish = (values: any) => {
    const membershipName = values.membershipName;

    // 当membershipName与任一name不重复时
    if (
      membershipList.every((membership) => membership.name !== membershipName)
    ) {
      setIsValidInput(true);
      onSubmit(orgId, consortiumId, membershipName);
      setIsModalOpen(false);
    } else {
      setIsValidInput(false);
    }
  };

  const onFinishFailed = (errorInfo: any) => {
    console.log("Failed:", errorInfo);
  };

  type FieldType = {
    membershipName?: string;
    createSSI?: boolean;
  };

  return (
    <>
      <Button type="primary" onClick={showModal}>
        ADD MEMBERSHIPS
      </Button>
      <Modal
        title="Add membership"
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
          initialValues={{ createSSI: false }}
        >
          <Form.Item<FieldType>
            label="Membership Name"
            name="membershipName"
            rules={[
              { required: true, message: "Please input membership name!" },
            ]}
            validateStatus={!isValidInput ? "error" : undefined}
            help={
              !isValidInput
                ? "This ID is duplicated! Please input again."
                : undefined
            }
          >
            <Input allowClear />
          </Form.Item>
          <Form.Item<FieldType>
            name="createSSI"
            valuePropName="checked"
            wrapperCol={{ offset: 8, span: 16 }}
          >
            <Checkbox>Membership For SSI</Checkbox>
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default CreateMembership;
