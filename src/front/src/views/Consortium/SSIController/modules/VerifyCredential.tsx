// components/SSIController/modules/VerifyCredential.tsx
import React from "react";
import { Card, Form, Input, Button, message } from "antd";
// import { verifyCredential } from "@/api/ssiAPI";

const VerifyCredential: React.FC = () => {
  const [form] = Form.useForm();

  const handleVerify = async () => {
    // const values = await form.validateFields();
    // const res = await verifyCredential(values);
    // if (res.data.valid) {
    //   message.success("Credential is valid");
    // } else {
    //   message.error("Credential verification failed");
    // }
    message.info("Verify function not implemented yet");
  };

  return (
    <Card title="Verify Credential">
      <Form form={form} layout="vertical">
        <Form.Item name="credential_json" label="Credential JSON" rules={[{ required: true }]}>
          <Input.TextArea />
        </Form.Item>
        <Button type="primary" onClick={handleVerify}>
          Verify
        </Button>
      </Form>
    </Card>
  );
};

export default VerifyCredential;
