import React, { useEffect, useState } from "react";
import { Card, Flex, Typography } from "antd";
import { BankOutlined } from "@ant-design/icons";
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
  width: "30%",
  marginBottom: "15px",
};

const gridStyle: React.CSSProperties = {
  width: "100%",
  textAlign: "start",
};

const gridDetailStyle: React.CSSProperties = {
  width: "100%",
  height: "10px",
  display: "flex",
  alignItems: "center",
  textAlign: "start",
};

const gridDeleteStyle: React.CSSProperties = {
  width: "100%",
  height: "10px",
  display: "flex",
  alignItems: "center",
  textAlign: "start",
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
        <Card key={item.id} title={item.name} style={cardStyle}>
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
          <Card.Grid style={gridDetailStyle}>
            <Link strong onClick={() => navigate(`./${item.id}`)} disabled={true}>
              VIEW DETAILS
            </Link>
          </Card.Grid>
          <Card.Grid style={gridDetailStyle}>
            <Link strong onClick={() => navigate(`./${item.id}/fabricUsers`)} disabled={false}>
              MANAGE FABRIC USERS
            </Link>
          </Card.Grid>
          <Card.Grid style={gridDeleteStyle}>
            <DelMembership
              onDelete={() => handleDelete(consortiumId, item.id)}
            />
          </Card.Grid>
        </Card>
      ));
  };


  return (
    <Flex gap="small" align="start" vertical>
      <div style={{
        width: "100%",
        display: "flex",
        justifyContent: "flex-start",
        marginBottom: "10px",
        gap: "10px",
      }}>
        <CreateMembership onSubmit={handleCreate} />
        <InviteMembership onSubmit={handleInvite} />
      </div>

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
