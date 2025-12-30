import React, { useEffect, useState } from "react";
import { Card, Flex, Typography, Tag, Divider } from "antd";
import { BankOutlined, TeamOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";

import CreateMembership from "./create";
import DelMembership from "./delete";
import InviteMembership from "./invite";
import {
  createMembership,
  getMembershipList,
  inviteOrgJoinConsortium,
  deleteMembership,
} from "@/api/platformAPI";
import { useAppSelector } from "@/redux/hooks";

const { Link } = Typography;

const boxStyle: React.CSSProperties = {
  width: "100%",
};

const cardStyle: React.CSSProperties = {
  width: "300px",
  marginBottom: "16px",
  borderRadius: "16px",
  boxShadow: "0 12px 32px rgba(15,23,42,0.12)",
  border: "1px solid #e2e8f0",
  overflow: "hidden",
};

const gridStyle: React.CSSProperties = {
  width: "100%",
  textAlign: "start",
  background: "linear-gradient(135deg, #f8fafc, #ffffff)",
};

const gridDetailStyle: React.CSSProperties = {
  width: "100%",
  display: "flex",
  alignItems: "center",
  textAlign: "start",
  padding: "10px 16px",
};

const gridDeleteStyle: React.CSSProperties = {
  width: "100%",
  display: "flex",
  alignItems: "center",
  textAlign: "start",
  padding: "10px 16px",
};

interface membershipItemType {
  id: string;
  name: string;
  orgId: string;
  consortiumId: string;
}

const Memberships: React.FC = () => {
  const orgId = useAppSelector((state) => state.org).currentOrgId;
  const consortiumId = useAppSelector(
    (state) => state.consortium
  ).currentConsortiumId;

  const navigate = useNavigate();

  const [membershipList, setMembershipList] = useState<membershipItemType[]>(
    []
  );

  const renameMembership = ({ loleido_organization, consortium, ...rest }) => ({
    ...rest,
    orgId: loleido_organization,
    consortiumId: consortium,
  });

  useEffect(() => {
    const fetchAndSetData = async (consortiumId: string) => {
      const data = await getMembershipList(consortiumId);
      const newMembershipList = data.map(renameMembership);
      setMembershipList(newMembershipList);
    };

    fetchAndSetData(consortiumId);
  }, [consortiumId]);

  const handleCreate = async (
    orgId: string,
    consortiumId: string,
    membershipName: string
  ) => {
    await createMembership(orgId, consortiumId, membershipName);
    const data = await getMembershipList(consortiumId);
    const newMembershipList = data.map(renameMembership);
    setMembershipList(newMembershipList);
  };

  const handleInvite = async (targetOrgId: string, consortiumId: string) => {
    return await inviteOrgJoinConsortium(targetOrgId, consortiumId, orgId);

  };

  const handleDelete = async (consortiumId: string, membershipId: string) => {
    await deleteMembership(consortiumId, membershipId);
    const data = await getMembershipList(consortiumId);
    const newMembershipList = data.map(renameMembership);
    setMembershipList(newMembershipList);
  };

  const MembershipItemList: React.FC<{ orgId: string; isMine: boolean }> = ({
    orgId,
    isMine,
  }) => {
    return membershipList
      .filter((item) => (isMine ? item.orgId === orgId : item.orgId !== orgId))
      .map((item) => (
        <Card
          key={item.id}
          title={
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <TeamOutlined style={{ color: "#2563eb" }} />
              <span>{item.name}</span>
            </div>
          }
          extra={
            <Tag color={isMine ? "blue" : "gold"}>{isMine ? "My Org" : "External"}</Tag>
          }
          style={cardStyle}
          bodyStyle={{ padding: 0 }}
        >
          <Card.Grid style={gridStyle}>
            <Card.Meta
              avatar={
                <BankOutlined
                  style={{
                    width: "100%",
                    height: "100%",
                    fontSize: "200%",
                  }}
                />
              }
              title="Organization"
              description={item.orgId}
            />
          </Card.Grid>
          <Divider style={{ margin: 0 }} />
          <div style={gridDetailStyle}>
            <Link strong onClick={() => navigate(`./${item.id}`)} disabled={true}>
              VIEW DETAILS
            </Link>
          </div>
          <Divider style={{ margin: 0 }} />
          <div style={gridDetailStyle}>
            <Link strong onClick={() => navigate(`./${item.id}/fabricUsers`)} disabled={false}>
              MANAGE FABRIC USERS
            </Link>
          </div>
          <Divider style={{ margin: 0 }} />
          <div style={gridDeleteStyle}>
            <DelMembership onDelete={() => handleDelete(consortiumId, item.id)} />
          </div>
        </Card>
      ));
  };


  return (
    <Flex gap="small" align="start" vertical>
      <Card
        bordered={false}
        style={{
          width: "100%",
          borderRadius: 18,
          boxShadow: "0 14px 40px rgba(15,23,42,0.12)",
          border: "1px solid #e2e8f0",
          marginBottom: 16,
        }}
        title="Memberships"
      >
        <div style={{
          width: "100%",
          display: "flex",
          justifyContent: "flex-start",
          gap: "10px",
          flexWrap: "wrap",
        }}>
        <CreateMembership onSubmit={handleCreate} />
        <InviteMembership onSubmit={handleInvite} />
        </div>
      </Card>

      <Flex
        gap="large"
        style={boxStyle}
        justify="flex-start"
        align="flex-start"
        wrap="wrap"
      >
        <MembershipItemList orgId={orgId} isMine={true} />
      </Flex>

      <Flex
        gap="large"
        style={boxStyle}
        justify="flex-start"
        align="flex-start"
        wrap="wrap"
      >
        <MembershipItemList orgId={orgId} isMine={false} />
      </Flex>
    </Flex>
  );
};

export default Memberships;
