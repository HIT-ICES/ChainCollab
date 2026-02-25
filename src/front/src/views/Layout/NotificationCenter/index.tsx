import { Button, Col, Dropdown, Row, Space, Typography, Menu, Tabs } from "antd";
const { TabPane } = Tabs;
import type { MenuProps } from "antd";
import React, { useEffect, useState } from "react";
import { BellOutlined } from "@ant-design/icons";
import { useAppSelector } from "@/redux/hooks";

const { Text } = Typography;

import { invitationMsgType } from './types'
import { useOrgInvitionData, useUserInvitationList, useAcceptUserInvitation, useDeclineUserInvitation } from './hooks'
import { acceptOrgInvitation, rejectOrgInvitation } from '@/api/platformAPI'

const NotificationCenter: React.FC = () => {
  const orgID = useAppSelector((state) => state.org).currentOrgId;
  const [msgList, setSync] = useOrgInvitionData(orgID);

  useEffect(() => {
    const task = setInterval(() => {
      if (!localStorage.getItem("token")) {
        return;
      }
      setSync();
    }, 5000);
    return () => {
      clearInterval(task);
    }
  }
    , []);

  const MenuItemLabel: React.FC<invitationMsgType> = (invitationMsg) => {
    const onAccept = async (id: string) => {
      await acceptOrgInvitation(id);
      setSync();
    };

    const onReject = async (id: string) => {
      await rejectOrgInvitation(id);
      setSync();
    };

    return (
      <Row style={{
        width: "500px", padding: "10px", marginBottom: "10px",
        border: "1px solid #f0f0f0", borderRadius: "5px"
      }} justify="space-between" align="middle">
        <Col span={21}>
          <Text>The organization </Text>
          <Text strong>{invitationMsg.invitorName} </Text>
          <Text>has invited you to join the consortium </Text>
          <Text strong>{invitationMsg.consortiumName} </Text>
          <Text>at </Text>
          <Text strong>{invitationMsg.date}</Text>
          <Text>.</Text>
        </Col>
        {
          invitationMsg.status === 'pending' ? (
            <Col span={3}>
              <Space direction="vertical">
                <Button
                  size="small"
                  type="primary"
                  block
                  onClick={() => onAccept(invitationMsg.id)}
                >
                  Accept
                </Button>
                <Button
                  size="small"
                  danger
                  block
                  onClick={() => onReject(invitationMsg.id)}
                >
                  Reject
                </Button>
              </Space>
            </Col>
          ) : (
            <Col span={3} >
              <Typography.Text type={invitationMsg.status === 'accept' ? 'success' : 'danger'}
                style={{
                  fontSize: "18px",
                  fontWeight: "bold"
                }}
              > {invitationMsg.status} </Typography.Text>
            </Col>
          )
        }
      </Row>
    );
  };



  const getItemList: (
    invitationMsgList: invitationMsgType[]
  ) => MenuProps["items"] = (invitationMsgList) =>
      invitationMsgList.map((item, index) => ({
        label: <MenuItemLabel {...item} />,
        key: item.id,
      }));

  const items: MenuProps["items"] = getItemList(msgList);
  const notItems = [{ label: <Text>There is no new message</Text>, key: "0" }];
  const ItemsToShow = items.length === 0 ? notItems : items;


  // const userMessage
  const [acceptUserInvitation, acceptUserInvitationStatus] = useAcceptUserInvitation();
  const [declineUserInvitation, declineUserInvitationStatus] = useDeclineUserInvitation();
  const [userInvitations, userInvitationStatus, refetch] = useUserInvitationList();

  const UserMenuItemLabel = (userInvitations) => {
    const onAccept = async (id: string) => {
      await acceptUserInvitation(id);
      refetch();
    };

    const onReject = async (id: string) => {
      await declineUserInvitation(id);
      refetch();
    };

    return (
      <Row style={{
        width: "500px", padding: "10px", marginBottom: "10px",
        border: "1px solid #f0f0f0", borderRadius: "5px"
      }} justify="space-between" align="middle">
        <Col span={21}>
          <Text>You have been invited to join the organization </Text>
          <Text strong>{userInvitations.loleido_organization.name} </Text>
          <Text>at </Text>
          <Text strong>{userInvitations.date}</Text>
          <Text>.</Text>
        </Col>
        {
          userInvitations.status === 'pending' ? (
            <Col span={3}>
              <Space direction="vertical">
                <Button
                  size="small"
                  type="primary"
                  block
                  onClick={() => onAccept(userInvitations.id)}
                >
                  Accept
                </Button>
                <Button
                  size="small"
                  danger
                  block
                  onClick={() => onReject(userInvitations.id)}
                >
                  Reject
                </Button>
              </Space>
            </Col>
          ) : (
            <Col span={3} >
              <Typography.Text type={userInvitations.status === 'accept' ? 'success' : 'danger'}
                style={{
                  fontSize: "18px",
                  fontWeight: "bold"
                }}
              > {userInvitations.status} </Typography.Text>
            </Col>
          )
        }
      </Row>
    );
  }
  const getUserItemList = (userInvitations: invitationMsgType[]) =>
    userInvitations.map((item, index) => ({
      label: <UserMenuItemLabel {...item} />,
      key: item.id,
    }));
  const userItems = getUserItemList(userInvitations);
  const userNotItems = [{ label: <Text>There is no new message</Text>, key: "0" }];
  const userItemsToShow = userItems.length === 0 ? userNotItems : userItems;

  return (
    <Dropdown dropdownRender={() =>
      <Menu >
        <Tabs defaultActiveKey="1" style={{
          width: "500px",
          display: "flex",
        }}>
          <TabPane tab="Organization Messages" key="1"  >
            {ItemsToShow.map((item) => (
              <Menu.Item key={item.key}>{item.label}</Menu.Item>
            ))}
          </TabPane>
          <TabPane tab="User Messages" key="2"  >
            {
              userItemsToShow.map((item) => (
                <Menu.Item key={item.key}>{item.label}</Menu.Item>
              ))
            }
          </TabPane>
        </Tabs>
      </Menu>
    } trigger={["click"]} arrow={true} >
      <BellOutlined style={{ fontSize: "24px" }} />
    </Dropdown >
  );
};

export default NotificationCenter;
