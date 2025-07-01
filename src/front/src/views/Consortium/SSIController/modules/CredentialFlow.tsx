// CredentialFlow.tsx
import React, { useEffect, useState } from "react";
import { Card, Form, Input, Button, Select, message, Space } from "antd";
import { getCredentialDefinitions, issueCredential, getConnections } from "@/api/ssiAPI";
import { useAppSelector } from "@/redux/hooks";

const { Option } = Select;

const CredentialFlow: React.FC = () => {
  const [form] = Form.useForm();
  const [credentialDefs, setCredentialDefs] = useState<any[]>([]);
  const [connections, setConnections] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const currentOrgId = useAppSelector((state) => state.org.currentOrgId);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const defs = await getCredentialDefinitions(currentOrgId);
        const conns = await getConnections(currentOrgId);
        setCredentialDefs(defs);
        setConnections(conns);
      } catch (e) {
        message.error("Failed to fetch data");
      }
    };
    fetchData();
  }, [currentOrgId]);

  const onFinish = async (values: any) => {
    try {
      setLoading(true);
      const parsedAttrs = JSON.parse(values.attributes);
      await issueCredential({
        org_id: currentOrgId,
        cred_def_id: values.credDefId,
        connection_id: values.connectionId,
        attributes: parsedAttrs,
      });
      message.success("Credential issued successfully");
      form.resetFields();
    } catch (e) {
      message.error("Failed to issue credential");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card title="Issue Verifiable Credential">
      <Form
        form={form}
        layout="vertical"
        onFinish={onFinish}
        initialValues={{ attributes: "{}" }}
      >
        <Form.Item
          label="Credential Definition"
          name="credDefId"
          rules={[{ required: true, message: "Please select a credential definition" }]}
        >
          <Select placeholder="Select a definition">
            {credentialDefs.map((def) => (
              <Option key={def.id} value={def.id}>{def.name || def.id}</Option>
            ))}
          </Select>
        </Form.Item>

        <Form.Item
          label="Holder Connection"
          name="connectionId"
          rules={[{ required: true, message: "Please select a connection" }]}
        >
          <Select placeholder="Select a connection">
            {connections.map((conn) => (
              <Option key={conn.connection_id} value={conn.connection_id}>{conn.alias || conn.connection_id}</Option>
            ))}
          </Select>
        </Form.Item>

        <Form.Item
          label="Credential Attributes (JSON object)"
          name="attributes"
          rules={[{ required: true, message: "Please input attributes" }]}
        >
          <Input.TextArea rows={5} placeholder='{"name": "Alice", "email": "alice@example.com"}' />
        </Form.Item>

        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading}>Issue Credential</Button>
        </Form.Item>
      </Form>
    </Card>
  );
};

export default CredentialFlow;