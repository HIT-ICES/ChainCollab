import React from "react";
import { Card, Typography } from "antd";
import { UserOutlined } from "@ant-design/icons";

const { Link } = Typography;

interface UserInfoCardProps {
  name: string;
  email: string;
  onDelete: () => void;
}

const UserInfoCard: React.FC<UserInfoCardProps> = ({ name, email, onDelete }) => {
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

  return (
    <Card title={name} style={cardStyle}>
      <Card.Grid style={gridStyle}>
        <Card.Meta
          avatar={
            <UserOutlined
              style={{
                width: "100%",
                height: "100%",
                fontSize: "200%",
              }}
            />
          }
          title={name}
          description={email}
        />
      </Card.Grid>
      <Card.Grid style={gridDetailStyle}>
        <Link strong disabled={true}  >
          VIEW DETAILS
        </Link>
      </Card.Grid>
      <Card.Grid style={gridDeleteStyle} >
        <Link strong onClick={onDelete} style={{ color: 'red' }}  >
          DELETE USER
        </Link>
      </Card.Grid>
    </Card>
  );
};

export default UserInfoCard;
