import React, { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
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
import { ApartmentOutlined, FileTextOutlined } from "@ant-design/icons";
import { useAppDispatch } from "@/redux/hooks";
import { activateConsortium } from "@/redux/slices/consortiumSlice";
import { createConsortium } from "@/api/platformAPI";

const { Title, Text } = Typography;

const CreateConsortium: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const { org_id } = useParams();

  const onFinish = async (values: { name: string; description?: string }) => {
    if (!values.name?.trim()) {
      message.error("请输入联盟名称");
      return;
    }
    try {
      setLoading(true);
      const consortium = await createConsortium(org_id, values.name.trim());
      dispatch(activateConsortium({ currentConsortiumId: consortium.id, currentConsortiumName: consortium.name }));
      message.success("Consortium created");
      navigate(`/orgs/${org_id}/consortia/${consortium.id}/dashboard`);
    } catch (error: any) {
      message.error(error?.message || "创建联盟失败");
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
            <ApartmentOutlined style={{ fontSize: 32, color: "#7dd3fc" }} />
          </Col>
          <Col flex="auto">
            <Title level={3} style={{ margin: 0, color: "#f8fafc" }}>Create Consortium</Title>
            <Text style={{ color: "#cbd5f5" }}>
              为组织创建并管理一个新的联盟。
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
            label="Consortium Name"
            name="name"
            rules={[{ required: true, message: "请输入联盟名称" }]}
          >
            <Input placeholder="例如：Consortium-A" allowClear />
          </Form.Item>
          <Form.Item label="Description" name="description">
            <Input.TextArea rows={3} placeholder="可选：描述、用途等" />
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

export default CreateConsortium;
