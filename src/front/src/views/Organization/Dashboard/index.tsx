import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Row, Col, Typography, Space, Card, Divider, Tag, List, Badge } from "antd";
import { InfoCircleOutlined, TeamOutlined, SettingOutlined, ApartmentOutlined, UserOutlined, ThunderboltOutlined, CloudServerOutlined } from '@ant-design/icons';
import { useAppDispatch, useAppSelector } from "@/redux/hooks";
import { openOrgSelectRequest } from "@/redux/slices/UISlice";
import { selectConsortium } from "@/redux/slices/consortiumSlice";
import { selectOrg } from "@/redux/slices/orgSlice";
import { useOrgInfo } from './hooks.ts';
import { getUserList } from "@/api/platformAPI";

const { Title, Text } = Typography;

const emptyStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  justifyContent: "center",
  alignItems: "center",
  height: "60vh",
  gap: 16,
};

const Dashboard = () => {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const currOrgId = useAppSelector(selectOrg).currentOrgId;
  const currentConsortiumName = useAppSelector(selectConsortium).currentConsortiumName;
  const [orgInfo] = useOrgInfo(currOrgId);
  const [userList, setUserList] = useState<any[]>([]);
  const [userLoading, setUserLoading] = useState(false);

  useEffect(() => {
    if (!currOrgId) {
      setUserList([]);
      return;
    }
    let mounted = true;
    const fetchUsers = async () => {
      try {
        setUserLoading(true);
        const res = await getUserList(currOrgId);
        if (mounted) {
          setUserList(Array.isArray(res) ? res : []);
        }
      } finally {
        if (mounted) {
          setUserLoading(false);
        }
      }
    };
    fetchUsers();
    return () => {
      mounted = false;
    };
  }, [currOrgId]);

  if (!currOrgId) {
    return (
      <div style={emptyStyle}>
        <Title level={3}>Haven't activated an organization?</Title>
        <Text type="secondary">请选择或创建一个组织以查看组织仪表盘。</Text>
        <Button type="primary" size="large" onClick={() => dispatch(openOrgSelectRequest())}>
          Create / Activate
        </Button>
      </div>
    );
  }

  const users = userList;
  const consortiums = (orgInfo as any)?.consortiums ?? [];
  const envs = (orgInfo as any)?.envs ?? [];

  return (
    <div style={{ padding: 8 }}>
      <div
        style={{
          borderRadius: 18,
          padding: "18px 20px",
          marginBottom: 16,
          background: "linear-gradient(120deg, #111827, #1f2937 45%, #0ea5e9)",
          color: "#e2e8f0",
          boxShadow: "0 16px 46px rgba(0,0,0,0.22)",
        }}
      >
        <Row justify="space-between" align="middle">
          <Col>
            <Space direction="vertical" size={4}>
              <Title level={3} style={{ margin: 0, color: "#f8fafc" }}>
                Organization Dashboard
              </Title>
              <Space>
                <Tag color="geekblue">{orgInfo?.name ?? "Org"}</Tag>
                <Text style={{ color: "#cbd5f5" }}>ID: {orgInfo?.id}</Text>
                <Text style={{ color: "#cbd5f5" }}>Consortium: {currentConsortiumName || (consortiums[0]?.name ?? "未选择")}</Text>
              </Space>
            </Space>
          </Col>
          <Col>
            <Space>
              <Button
                icon={<TeamOutlined />}
                onClick={() => navigate(`/orgs/${currOrgId}/usersmanage`)}
                style={{ borderRadius: 10 }}
              >
                Manage Users
              </Button>
              <Button
                icon={<SettingOutlined />}
                onClick={() => navigate(`/orgs/${currOrgId}/settings`)}
                style={{ borderRadius: 10 }}
              >
                Settings
              </Button>
            </Space>
          </Col>
        </Row>
      </div>

      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Row gutter={[12, 12]}>
            <Col span={6}>
              <Card bordered={false} style={{ borderRadius: 14, boxShadow: "0 10px 30px rgba(15,23,42,0.1)", border: "1px solid #e2e8f0" }}>
                <Space direction="vertical" size={4}>
                  <Text type="secondary">Consortiums</Text>
                  <Title level={3} style={{ margin: 0 }}>{consortiums.length || 1}</Title>
                  <Tag color="geekblue">Active</Tag>
                </Space>
              </Card>
            </Col>
            <Col span={6}>
              <Card bordered={false} style={{ borderRadius: 14, boxShadow: "0 10px 30px rgba(15,23,42,0.1)", border: "1px solid #e2e8f0" }}>
                <Space direction="vertical" size={4}>
                  <Text type="secondary">Users</Text>
                  <Title level={3} style={{ margin: 0 }}>{Array.isArray(users) ? users.length : 0}</Title>
                  <Text type="secondary">{userLoading ? "Loading..." : "Members in org"}</Text>
                </Space>
              </Card>
            </Col>
            <Col span={6}>
              <Card bordered={false} style={{ borderRadius: 14, boxShadow: "0 10px 30px rgba(15,23,42,0.1)", border: "1px solid #e2e8f0" }}>
                <Space direction="vertical" size={4}>
                  <Text type="secondary">Environments</Text>
                  <Title level={3} style={{ margin: 0 }}>{Array.isArray(envs) ? envs.length : 0}</Title>
                  <Text type="secondary">Fabric / Ethereum</Text>
                </Space>
              </Card>
            </Col>
            <Col span={6}>
              <Card bordered={false} style={{ borderRadius: 14, boxShadow: "0 10px 30px rgba(15,23,42,0.1)", border: "1px solid #e2e8f0" }}>
                <Space direction="vertical" size={4}>
                  <Text type="secondary">Status</Text>
                  <Space align="center">
                    <Badge status="success" />
                    <Text strong>Healthy</Text>
                  </Space>
                  <Text type="secondary">Last check passed</Text>
                </Space>
              </Card>
            </Col>
          </Row>
        </Col>

        <Col span={12}>
          <Card
            title="Org & Consortium"
            extra={<ApartmentOutlined style={{ color: "#2563eb" }} />}
            bordered={false}
            style={{
              borderRadius: 16,
              boxShadow: "0 14px 40px rgba(15,23,42,0.12)",
              border: "1px solid #e2e8f0",
            }}
          >
            <Space direction="vertical" size="small">
              <Text strong>Organization</Text>
              <Text>{orgInfo?.name ?? "--"}</Text>
              <Text type="secondary">ID: {orgInfo?.id ?? "--"}</Text>
              <Divider style={{ margin: "12px 0" }} />
              <Text strong>Consortium</Text>
              <Text>{currentConsortiumName || (consortiums[0]?.name ?? "未选择")}</Text>
              <Text type="secondary">已关联 {consortiums.length || 1} 个联盟</Text>
            </Space>
          </Card>
        </Col>

        <Col span={12}>
          <Card
            title="Users"
            extra={<UserOutlined style={{ color: "#2563eb" }} />}
            bordered={false}
            style={{
              borderRadius: 16,
              boxShadow: "0 14px 40px rgba(15,23,42,0.12)",
              border: "1px solid #e2e8f0",
            }}
          >
            <Space direction="vertical" style={{ width: "100%" }}>
              <Space align="center" style={{ justifyContent: "space-between", width: "100%" }}>
                <Text strong>成员总数</Text>
                <Tag color="blue">{Array.isArray(users) ? users.length : "N/A"}</Tag>
              </Space>
              <List
                size="small"
                dataSource={(users || []).slice(0, 5)}
                locale={{ emptyText: "暂无用户" }}
                renderItem={(item: any) => (
                  <List.Item>
                    <Space direction="vertical" size={0}>
                      <Text>{item?.name ?? item?.username ?? "User"}</Text>
                      <Text type="secondary">{item?.email ?? item?.role ?? ""}</Text>
                    </Space>
                  </List.Item>
                )}
              />
              <Button type="link" onClick={() => navigate(`/orgs/${currOrgId}/usersmanage`)}>前往用户管理</Button>
            </Space>
          </Card>
        </Col>

        <Col span={24}>
          <Card
            title="Organization Details"
            bordered={false}
            style={{
              borderRadius: 16,
              boxShadow: "0 14px 40px rgba(15,23,42,0.12)",
              border: "1px solid #e2e8f0",
            }}
          >
            <Row gutter={[16, 12]}>
              <Col span={12}>
                <Text strong>Display Name</Text>
                <div><Text>{orgInfo?.name ?? "--"}</Text></div>
              </Col>
              <Col span={12}>
                <Text strong>Organization ID</Text>
                <div><Text>{orgInfo?.id ?? "--"}</Text></div>
              </Col>
              <Col span={12}>
                <Text strong>Created At</Text>
                <div><Text>{orgInfo?.created_at ?? orgInfo?.createdAt ?? "N/A"}</Text></div>
              </Col>
              <Col span={12}>
                <Text strong>Updated At</Text>
                <div><Text>{orgInfo?.updated_at ?? orgInfo?.updatedAt ?? "N/A"}</Text></div>
              </Col>
            </Row>
          </Card>
        </Col>

        <Col span={24}>
          <Card
            title="Quick Actions"
            bordered={false}
            style={{
              borderRadius: 16,
              boxShadow: "0 14px 40px rgba(15,23,42,0.12)",
              border: "1px solid #e2e8f0",
            }}
          >
            <Space wrap>
              <Button icon={<ApartmentOutlined />} onClick={() => navigate("/network")}>View Consortiums</Button>
              <Button icon={<CloudServerOutlined />} onClick={() => navigate("/environment")}>Manage Environments</Button>
              <Button icon={<TeamOutlined />} onClick={() => navigate(`/orgs/${currOrgId}/usersmanage`)}>Add User</Button>
              <Button icon={<ThunderboltOutlined />} onClick={() => navigate("/bpmn/drawing")}>Open BPMN Modeler</Button>
            </Space>
          </Card>
        </Col>

        <Col span={24}>
          <Card
            title="Recent Activity"
            bordered={false}
            style={{
              borderRadius: 16,
              boxShadow: "0 14px 40px rgba(15,23,42,0.12)",
              border: "1px solid #e2e8f0",
            }}
          >
            <List
              size="small"
              dataSource={[
                { title: "用户管理", desc: "更新了组织成员与角色。" },
                { title: "环境检查", desc: "最近一次健康检查通过。" },
                { title: "联盟关联", desc: `关联联盟：${currentConsortiumName || "未选择"}` },
              ]}
              renderItem={(item) => (
                <List.Item>
                  <List.Item.Meta
                    title={<Text strong>{item.title}</Text>}
                    description={<Text type="secondary">{item.desc}</Text>}
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
