import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Card,
  Input,
  Button,
  Typography,
  Form,
  Row,
  Col,
  message,
  Space
} from "antd";
import { RocketOutlined, FileTextOutlined } from "@ant-design/icons";
import { useAppDispatch } from "@/redux/hooks";
import { activateOrg } from "@/redux/slices/orgSlice";
import { createOrg } from "@/api/platformAPI";

const { Title, Text } = Typography;

const CreateOrganization: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const dispatch = useAppDispatch();

  const onFinish = async (values: { name: string; description?: string }) => {
    if (!values.name?.trim()) {
      message.error("请输入组织名称");
      return;
    }
    try {
      setLoading(true);
      const org = await createOrg(values.name.trim());
      dispatch(activateOrg({ currentOrgId: org.id, currentOrgName: org.name }));
      message.success("Organization created");
      navigate(`/orgs/${org.id}/dashboard`);
    } catch (error: any) {
      message.error(error?.message || "创建组织失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 960, margin: "0 auto", padding: "16px" }}>
      <Card
        bordered={false}
        style={{
          borderRadius: 18,
          boxShadow: "0 16px 46px rgba(15,23,42,0.12)",
          background: "linear-gradient(160deg, #0f172a 0%, #1f2937 50%, #0ea5e9 120%)",
          color: "#e2e8f0",
          marginBottom: 18,
        }}
      >
        <Row align="middle" gutter={16}>
          <Col flex="40px">
            <RocketOutlined style={{ fontSize: 32, color: "#7dd3fc" }} />
          </Col>
          <Col flex="auto">
            <Title level={3} style={{ margin: 0, color: "#f8fafc" }}>Create Organization</Title>
            <Text style={{ color: "#cbd5f5" }}>
              定义一个新的组织以管理联盟、环境及成员。
            </Text>
          </Col>
        </Row>
      </Card>

      <Card
        bordered={false}
        style={{
          borderRadius: 16,
          boxShadow: "0 14px 40px rgba(15,23,42,0.1)",
          border: "1px solid #e2e8f0",
          background: "#fff",
        }}
        title={
          <Row align="middle" gutter={10}>
            <Col><FileTextOutlined style={{ color: "#2563eb" }} /></Col>
            <Col><Text strong>Basic Information</Text></Col>
          </Row>
        }
      >
        <Form layout="vertical" onFinish={onFinish}>
          <Form.Item
            label="Organization Name"
            name="name"
            rules={[{ required: true, message: "请输入组织名称" }]}
          >
            <Input placeholder="例如：MyOrg1" allowClear />
          </Form.Item>
          <Form.Item label="Description" name="description">
            <Input.TextArea rows={3} placeholder="可选：组织描述、用途等" />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button onClick={() => navigate(-1)}>Cancel</Button>
              <Button type="primary" htmlType="submit" loading={loading}>
                Create
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default CreateOrganization;
