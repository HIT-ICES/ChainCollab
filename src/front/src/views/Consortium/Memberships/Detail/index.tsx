import React, { useEffect, useState } from "react";
import { Card, Typography, Descriptions, Tag, Space, Button, Skeleton, Empty } from "antd";
import { useNavigate, useParams } from "react-router-dom";
import { getMembership } from "@/api/platformAPI";
import { useAppSelector } from "@/redux/hooks";

const { Title, Text } = Typography;

const Detail: React.FC = () => {
  const params = useParams();
  const navigate = useNavigate();
  const { currentConsortiumId } = useAppSelector((state) => state.consortium);
  const { currentOrgId } = useAppSelector((state) => state.org);
  const [loading, setLoading] = useState(true);
  const [membership, setMembership] = useState<any | null>(null);

  useEffect(() => {
    const fetchMembership = async () => {
      if (!params.id) {
        setLoading(false);
        return;
      }
      try {
        const data = await getMembership(params.id, currentConsortiumId);
        setMembership(data);
      } catch (error) {
        setMembership(null);
      } finally {
        setLoading(false);
      }
    };
    fetchMembership();
  }, [params.id, currentConsortiumId]);

  if (loading) {
    return (
      <Card style={{ borderRadius: 14 }}>
        <Skeleton active />
      </Card>
    );
  }

  if (!membership) {
    return (
      <Card style={{ borderRadius: 14 }}>
        <Empty description="Membership not found" />
      </Card>
    );
  }

  const orgId = membership.loleido_organization || membership.orgId;
  const isMine = orgId && currentOrgId && orgId === currentOrgId;
  const createdAt = membership.created_at || membership.createdAt;

  return (
    <Card
      style={{ borderRadius: 16, boxShadow: "0 12px 32px rgba(15, 23, 42, 0.12)", border: "1px solid #e5e7eb" }}
      title={
        <Space direction="vertical" size={0}>
          <Title level={4} style={{ margin: 0 }}>
            {membership.name || "Membership"}
          </Title>
          <Text type="secondary">{membership.id}</Text>
        </Space>
      }
      extra={
        <Space>
          <Tag color={isMine ? "blue" : "gold"}>{isMine ? "My Org" : "External"}</Tag>
          <Button onClick={() => navigate(`../${membership.id}/fabricUsers`)}>Manage Users</Button>
        </Space>
      }
    >
      <Descriptions
        bordered
        size="middle"
        column={1}
        labelStyle={{ width: 220, background: "#f8fafc" }}
        contentStyle={{ background: "#ffffff" }}
      >
        <Descriptions.Item label="Membership Name">{membership.name || "-"}</Descriptions.Item>
        <Descriptions.Item label="Membership ID">{membership.id || "-"}</Descriptions.Item>
        <Descriptions.Item label="Organization ID">{orgId || "-"}</Descriptions.Item>
        <Descriptions.Item label="Consortium ID">{membership.consortium || membership.consortiumId || "-"}</Descriptions.Item>
        <Descriptions.Item label="Join Date">{createdAt || "-"}</Descriptions.Item>
      </Descriptions>
    </Card>
  )
};

export default Detail;
