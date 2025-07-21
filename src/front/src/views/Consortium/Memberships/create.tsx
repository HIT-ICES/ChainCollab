import React, { useEffect, useState } from "react";
import { Modal, Form, Input, Button, Checkbox } from "antd";
import { useAppSelector } from "@/redux/hooks";
import { getMembershipList } from "@/api/platformAPI";
import { set } from "lodash";

interface Props {
  onSubmit: (
    orgId: string,
    consortiumId: string,
    membershipName: string,
    createSSI: boolean,
    is_ssi_agent: boolean,
    url: string,
    public_did: string,
  ) => void;
}

const CreateMembership: React.FC<Props> = ({ onSubmit }) => {
  // Modal相关
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isValidInput, setIsValidInput] = useState(true);

  const [membershipList, setMembershipList] = useState([]);

  const orgId = useAppSelector((state) => state.org).currentOrgId;
  const consortiumId = useAppSelector( (state) => state.consortium ).currentConsortiumId;
  const currentConsortiumType = useAppSelector( (state) => state.consortium.currentConsortiumType );
  const [showSSIFields, setShowSSIFields] = useState(false);
  const [is_ssi_agent, setIsSsiAgent] = useState(true); 

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

  const handleSSICheckboxChange = (e: any) => {
    const checked = e.target.checked;
    setShowSSIFields(checked);
    setIsSsiAgent(!checked); // 勾选时 is_ssi_agent = false，取消勾选时 = true
  };

  // Form相关
  const onFinish = (values: any) => {
    const membershipName = values.membershipName;
    const createSSI = values.creatSSI;
    const url = values.ssiUrl;
    const public_did = values.ssiDID;
    setShowSSIFields(values.createSSI);
    // 当membershipName与任一name不重复时
    if (
      membershipList.every((membership) => membership.name !== membershipName)
    ) {
      setIsValidInput(true);
      onSubmit(orgId, consortiumId, membershipName, createSSI,is_ssi_agent, url, public_did);
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
    ssiUrl?: string;
    ssiDID?: string;
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
          {currentConsortiumType === "ssi" && (
            <Form.Item<FieldType>
              name="createSSI"
              valuePropName="checked"
              wrapperCol={{ offset: 8, span: 16 }}
            >
              <Checkbox onChange={handleSSICheckboxChange}>
                External SSI Agent
              </Checkbox>
            </Form.Item>
          )}
          {showSSIFields && (
          <>
            <Form.Item<FieldType>
              label="Agent URL"
              name="ssiUrl"
              rules={[{ required: true, message: "Please input Agent URL!" }]}
            >
              <Input placeholder="http://agent.example.com" />
            </Form.Item>
            <Form.Item<FieldType>
              label="Public DID"
              name="ssiDID"
              rules={[{ required: true, message: "Please input Public DID!" }]}
            >
              <Input placeholder="did:example:12345" />
            </Form.Item>
          </>
        )}
        </Form>
      </Modal>
    </>
  );
};

export default CreateMembership;
