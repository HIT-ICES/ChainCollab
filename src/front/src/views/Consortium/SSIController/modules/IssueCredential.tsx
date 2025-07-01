
import React from "react";
import { Card, Form, Input, Button, message } from "antd";
import { issueCredential } from "@/api/ssiAPI";

const IssueCredential: React.FC = () => {
  const [form] = Form.useForm();

  const handleIssue = async () => {
    const values = await form.validateFields();
    await issueCredential(values);
    message.success("Credential issued");
  };

  return (
    <Card title="Issue Credential">
      <Form form={form} layout="vertical">
        <Form.Item name="connection_id" label="Connection ID" rules={[{ required: true }]}>
          <Input />
        </Form.Item>
        <Form.Item name="credential_data" label="Credential Data" rules={[{ required: true }]}>
          <Input.TextArea />
        </Form.Item>
        <Button type="primary" onClick={handleIssue}>
          Issue
        </Button>
      </Form>
    </Card>
  );
};

export default IssueCredential;
