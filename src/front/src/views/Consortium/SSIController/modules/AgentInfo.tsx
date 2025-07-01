import React, { useEffect, useState } from "react";
import { Card, Form, Input, Button, message } from "antd";
import { getAgentInfo, bindAgent } from "@/api/ssiAPI";
import { useAppSelector } from "@/redux/hooks";

const AgentInfo: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const currentOrgId = useAppSelector((state) => state.org.currentOrgId);

  useEffect(() => {
    const fetch = async () => {
      try {
        const data = await getAgentInfo(currentOrgId);
        form.setFieldsValue(data);
      } catch (e) {
        console.warn("No agent info bound");
      } finally {
        setInitialLoading(false);
      }
    };
    fetch();
  }, [currentOrgId]);

  const onFinish = async (values: any) => {
    try {
      setLoading(true);
      await bindAgent(currentOrgId, values);
      message.success("Agent info saved");
    } catch (e) {
      message.error("Failed to save agent info");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card title="My Agent Info" loading={initialLoading}>
      <Form form={form} layout="vertical" onFinish={onFinish}>
        <Form.Item label="Agent URL" name="agent_url" rules={[{ required: true }]}> <Input /> </Form.Item>
        <Form.Item label="Public DID" name="public_did" rules={[{ required: true }]}> <Input /> </Form.Item>
        <Form.Item label="Label (optional)" name="label"> <Input /> </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading}> Save </Button>
        </Form.Item>
      </Form>
    </Card>
  );
};

export default AgentInfo;