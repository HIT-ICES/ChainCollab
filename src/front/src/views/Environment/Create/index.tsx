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
  Select,
  Space
} from "antd";
import { CloudServerOutlined, FileTextOutlined } from "@ant-design/icons";
import { useAppDispatch } from "@/redux/hooks";
import { activateEnv } from "@/redux/slices/envSlice";
import { createEnvironment } from "@/api/platformAPI";

const { Title, Text } = Typography;
const { Option } = Select;

const CreateEnvironment: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const { org_id, consortium_id } = useParams();

  const onFinish = async (values: { name: string; envType: string; description?: string }) => {
    if (!values.name?.trim()) {
      message.error("请输入环境名称");
      return;
    }
    try {
      setLoading(true);
      const env = await createEnvironment(consortium_id, values.name.trim());
      dispatch(activateEnv({ currentEnvId: env.id, currentEnvName: env.name, currentEnvType: values.envType || "Fabric" }));
      message.success("Environment created");
      navigate(`/orgs/${org_id}/consortia/${consortium_id}/envs/${env.id}/envdashboard`);
    } catch (error: any) {
      message.error(error?.message || "创建环境失败");
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
            <CloudServerOutlined style={{ fontSize: 32, color: "#7dd3fc" }} />
          </Col>
          <Col flex="auto">
            <Title level={3} style={{ margin: 0, color: "#f8fafc" }}>Create Environment</Title>
            <Text style={{ color: "#cbd5f5" }}>
              为联盟创建运行环境，选择适合的网络类型。
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
        <Form layout="vertical" onFinish={onFinish} initialValues={{ envType: "Fabric" }}>
          <Form.Item
            label="Environment Name"
            name="name"
            rules={[{ required: true, message: "请输入环境名称" }]}
          >
            <Input placeholder="例如：Env-Fabric-01" allowClear />
          </Form.Item>
          <Form.Item
            label="Environment Type"
            name="envType"
            rules={[{ required: true, message: "请选择环境类型" }]}
          >
            <Select>
              <Option value="Fabric">Fabric</Option>
              <Option value="Ethereum">Ethereum</Option>
              <Option value="Quorum" disabled>Quorum（即将支持）</Option>
            </Select>
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

export default CreateEnvironment;
