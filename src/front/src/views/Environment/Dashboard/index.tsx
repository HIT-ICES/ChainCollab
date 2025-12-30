import { Row, Card, Typography } from "antd";
import Overview from "./Overview";
import CA from "./CA";
import Peer from "./Peer";
import Orderer from "./Orderer";

const { Title, Text } = Typography;

const EnvDashboard = () => {

  return (
    <div style={{ padding: 8 }}>
      <Card
        bordered={false}
        style={{
          borderRadius: 18,
          boxShadow: "0 16px 46px rgba(15,23,42,0.16)",
          border: "1px solid #e2e8f0",
          marginBottom: 16,
          background: "linear-gradient(120deg, #0f172a, #1f2937 50%, #0ea5e9)",
          color: "#e2e8f0",
        }}
        title={<Title level={3} style={{ margin: 0, color: "#f8fafc" }}>Environment Dashboard</Title>}
      >
        <Text style={{ color: "#cbd5f5" }}>环境组件状态与节点概览。</Text>
      </Card>
      <Row gutter={16} style={{ marginBottom: 20 }}>
        <Overview />
        <CA></CA>
      </Row>
      <Row gutter={16}>
        <Peer></Peer>
        <Orderer></Orderer>
      </Row>
    </div>
  );
};

export default EnvDashboard;
