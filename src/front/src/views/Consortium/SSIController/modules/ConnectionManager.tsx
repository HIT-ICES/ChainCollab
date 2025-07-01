// components/SSIController/modules/ConnectionManager.tsx
import React, { useEffect, useState } from "react";
import { Card, List, Button, Tag, message, Modal, Input, Space, Select, Collapse} from "antd";
import {
  getConnections,
  getPendingInvitations,
  sendConnectionRequest,
  acceptConnectionRequest,
} from "@/api/ssiAPI";
import { useAppSelector } from "@/redux/hooks";

const { Option } = Select;
const { Panel } = Collapse;

const ConnectionManager: React.FC = () => {
  const currentMembershipId = useAppSelector(
    (state) => state
    // ！！！
    
  );

  const [connections, setConnections] = useState<any[]>([]);
  const [pendingInvites, setPendingInvites] = useState<any[]>([]);
  const [receiverId, setReceiverId] = useState("");
  const [receiverLabel, setReceiverLabel] = useState("Membership");
  const [loading, setLoading] = useState(false);

  const fetchConnections = async () => {
    try {
      setLoading(true);
      const data = await getConnections(currentMembershipId);
      setConnections(data);
    } catch {
      message.error("Failed to fetch connections");
    } finally {
      setLoading(false);
    }
  };

  const fetchInvites = async () => {
    try {
      const data = await getPendingInvitations(currentMembershipId);
      setPendingInvites(data);
    } catch {
      message.error("Failed to fetch pending invitations");
    }
  };

  useEffect(() => {
    fetchConnections();
    fetchInvites();
  }, [currentMembershipId]);

  const handleSendRequest = async () => {
    if (!receiverId) {
      message.warning("Receiver ID is required");
      return;
    }
    try {
      await sendConnectionRequest({
        sender_id: currentMembershipId,
        sender_label: "Membership",
        receiver_id: receiverId,
        receiver_label: receiverLabel,
      });
      message.success("Invitation record created");
      setReceiverId("");
      fetchInvites(); // optional, if viewing own outgoing invites later
    } catch {
      message.error("Failed to send invitation");
    }
  };

  const handleAcceptInvite = async (invitationId: string) => {
    try {
      await acceptConnectionRequest(invitationId, currentMembershipId);
      message.success("Invitation accepted and connection established");
      fetchConnections();
      fetchInvites();
    } catch {
      message.error("Failed to accept invitation");
    }
  };

  return (
    <Card
      title="Connection Manager"
      extra={<Button onClick={fetchConnections}>Refresh</Button>}
    >
      <Space direction="vertical" style={{ width: "100%" }}>
        {/* 发送连接邀请 */}
        <Card title="Send Connection Request">
          <Space direction="vertical" style={{ width: "100%" }}>
            <Select
              value={receiverLabel}
              onChange={setReceiverLabel}
              style={{ width: 200 }}
            >
              <Option value="Membership">Membership</Option>
              <Option value="MemUser">MemUser</Option>
            </Select>
            <Input
              value={receiverId}
              onChange={(e) => setReceiverId(e.target.value)}
              placeholder="Enter receiver ID"
            />
            <Button type="primary" onClick={handleSendRequest}>
              Send Request
            </Button>
          </Space>
        </Card>

        {/* 接收连接邀请 */}
        <Card title="Pending Invitations">
          <List
            dataSource={pendingInvites}
            renderItem={(item) => (
              <List.Item
                actions={[
                  <Button
                    type="link"
                    onClick={() => handleAcceptInvite(item.id)}
                    disabled={item.status === "accepted"}
                  >
                    Accept
                  </Button>,
                ]}
              >
                <List.Item.Meta
                  title={`From: ${item.sender_label} - ${item.sender_id}`}
                  description={
                    <>
                      <p>
                        <strong>To:</strong> {item.receiver_label} -{" "}
                        {item.receiver_id}
                      </p>
                      <Tag color={item.status === "accepted" ? "green" : "orange"}>
                        {item.status}
                      </Tag>
                    </>
                  }
                />
              </List.Item>
            )}
          />
        </Card>

        {/* 显示已建立连接 */}
        <Collapse>
          <Panel header="Established Connections" key="1">
            <List
              dataSource={connections}
              renderItem={(conn) => (
                <List.Item>
                  <List.Item.Meta
                    title={<span>{conn.alias || conn.connection_id}</span>}
                    description={
                      <>
                        <p>
                          <strong>State:</strong>{" "}
                          <Tag color="blue">{conn.state}</Tag>
                        </p>
                        <p>
                          <strong>Their DID:</strong> {conn.their_did}
                        </p>
                        <p>
                          <strong>My DID:</strong> {conn.my_did}
                        </p>
                      </>
                    }
                  />
                </List.Item>
              )}
            />
          </Panel>
        </Collapse>
      </Space>
    </Card>
  );
};

export default ConnectionManager;
