
import React, { useState } from 'react';
import { Typography, Steps, Checkbox, Modal, Button as AntdButton, Form, Table } from 'antd';
import { styled } from "@mui/material/styles";
import Button, { ButtonProps } from "@mui/material/Button";
import { purple } from "@mui/material/colors";

import BadgeIcon from "@mui/icons-material/Badge";
import FireflyIcon from "@/assets/icons/fireflyIcon.svg"
import OracleIcon from "@/assets/icons/oracleIcon.svg"
import DmnIcon from "@/assets/icons/dmnIcon.svg"


const { Title, Text } = Typography;

// CustomStyle

export const ColorButton = styled(Button)<ButtonProps>(({ theme }) => ({
  color: theme.palette.getContrastText(purple[500]),
  backgroundColor: purple[500],
  "&:hover": {
    backgroundColor: purple[700],
  },
}));

export const customColStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  marginLeft: "0px",
};

export const customTextStyle: React.CSSProperties = {
  fontSize: "14px",
  display: "flex",
  alignItems: "center",
};


// Step Bar

export const NaiveFabricStepBar = (props) => {

  const { step = 1, status = "wait" } = props.stepAndStatus;
  // status wait process finish error

  const items: Array<{
    title: string;
    description?: string;
  }> = [
      {
        title: "Created",
        description: "DB Record",
      },
      {
        title: "Initialized",
        description: "CA & Orderer Node",
      },
      {
        title: "Started",
        description: "Peer Nodes",
      },
      {
        title: "Active",
        description: "Channel been Setup",
      }
    ];

  return <Steps
    current={step}
    status={status}
    items={items}
  />

}

export const NaiveEthereumStepBar = (props) => {

  const { step = 1, status = "wait" } = props.stepAndStatus;
  // status wait process finish error

  const items: Array<{
    title: string;
    description?: string;
  }> = [
    // {
    //   title: "System Created",
    //   description: "DB Record",
    // },
      {
        title: "System Node Created",
        description: "System go-client node",
      },
      {
        title: "Membership Node Initialized",
        description: "Membership go-client node",
      }
    ];

  return <Steps
    current={step}
    status={status}
    items={items}
  />

}


// Function Cards
export const CustomCard = (props) => {

  const { color = "#4e4d4a", logo, title, status, action, onOpen } = props
  const resolveStatus = (value) => {
    if (typeof value === "string") {
      const normalized = value.toUpperCase();
      if (["STARTED", "RUNNING", "SUCCESS"].includes(normalized)) {
        return { label: "Running", color: "#22c55e", shadow: "0 0 0 4px rgba(34,197,94,0.15)" };
      }
      if (["SETTINGUP", "INITIALIZING"].includes(normalized)) {
        return { label: "SettingUp", color: "#f59e0b", shadow: "0 0 0 4px rgba(245,158,11,0.15)" };
      }
      if (["FAILED", "ERROR"].includes(normalized)) {
        return { label: "Failed", color: "#f43f5e", shadow: "0 0 0 4px rgba(244,63,94,0.12)" };
      }
      return { label: "Pending", color: "#94a3b8", shadow: "0 0 0 4px rgba(148,163,184,0.15)" };
    }
    if (value) {
      return { label: "Running", color: "#22c55e", shadow: "0 0 0 4px rgba(34,197,94,0.15)" };
    }
    return { label: "Pending", color: "#f43f5e", shadow: "0 0 0 4px rgba(244,63,94,0.12)" };
  };
  return (
    <div
      style={{
        width: 220,
        minHeight: 240,
        background: `linear-gradient(145deg, ${color} 0%, #ffffff 80%)`,
        border: "1px solid #e2e8f0",
        borderRadius: 16,
        margin: "10px",
        padding: 16,
        display: "flex",
        flexDirection: "column",
        boxShadow: "0 12px 30px rgba(15,23,42,0.12)",
        cursor: onOpen ? "pointer" : "default",
      }}
      onClick={onOpen}
    >
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center" }}>
        {logo}
      </div>
      <Title level={4} style={{ textAlign: "center", marginTop: 12, marginBottom: 8 }}>
        {title}
      </Title>
      <div style={{ display: "flex", flexDirection: "column", gap: 8, flex: 1 }} >
        {status.map((item) => {
          const resolved = resolveStatus(item.value);
          return (
            <div key={item.key} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  backgroundColor: resolved.color,
                  boxShadow: resolved.shadow,
                }}
              />
              <Text strong style={{ color: "#0f172a" }}>{item.key}</Text>
              <Text type="secondary">{resolved.label}</Text>
            </div>
          );
        })}
      </div>
      {action ? (
        <div
          style={{
            marginTop: "auto",
            display: "flex",
            justifyContent: "center",
            flexWrap: "wrap",
          }}
          onClick={(event) => event.stopPropagation()}
        >
          {action}
        </div>
      ) : null}
    </div >)
}

export const FireflyComponentCard = ({
  ChaincodeStatus = false,
  ClusterStatus = false,
  onSetup,
  onOpen
}) => {
  return (
    <CustomCard
      color="#88c100"
      logo={<img src={FireflyIcon} alt="firefly" style={{ width: 100, height: 100 }} />}
      title="Firefly"
      status={[
        { key: "ChainCode", value: ChaincodeStatus },
        { key: "Cluster", value: ClusterStatus }
      ]}
      action={onSetup}
      onOpen={onOpen}
    />
  );
}

export const OracleComponentCard = ({
  ChaincodeStatus = false,
  onSetup,
  onOpen
}) => {
  return (
    <CustomCard
      color="#2790b0"
      logo={<img src={OracleIcon} alt="firefly" style={{ width: 100, height: 100 }} />}
      title="Oracle"
      status={[
        { key: "ChainCode", value: ChaincodeStatus }
      ]}
      action={onSetup}
      onOpen={onOpen}
    />
  );
}

export const DMNComponentCard = ({
  ChaincodeStatus = false,
  onSetup,
  onOpen
}) => {
  return (
    <CustomCard
      color="#ffaa00"
      logo={<img src={DmnIcon} alt="dmn" style={{ width: 100, height: 100 }} />}
      title="DMN"
      status={[
        { key: "ChainCode", value: ChaincodeStatus }
      ]}
      action={onSetup}
      onOpen={onOpen}
    />
  );
}

export const IdentityContractComponentCard = ({
  ContractStatus = "NO",
  onSetup,
  onOpen
}) => {
  return (
    <CustomCard
      color="#8b5cf6"
      logo={<BadgeIcon style={{ fontSize: 80, color: "#1e293b" }} />}
      title="Identity Contract"
      status={[
        { key: "Contract", value: ContractStatus }
      ]}
      action={onSetup}
      onOpen={onOpen}
    />
  );
}


// Join Modal

export const JoinModal = ({
  isModalOpen,
  setIsModalOpen,
  membershipList,
  joinFunc,
}) => {

  const [membershipSelected, setMembershipSelected] = useState([]);


  const columns = [
    {
      title: 'Membership Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Select',
      dataIndex: 'id',
      key: 'id',
      render: (id) => (
        <Checkbox value={id} onChange={
          (e) => {
            if (e.target.checked) {
              setMembershipSelected([...membershipSelected, id])
            } else {
              setMembershipSelected(membershipSelected.filter((item) => item !== id))
            }
          }
        } />
      ),
    }
  ];

  const onFinish = async () => {
    setIsModalOpen(false)
    try {
      const response = await joinFunc(membershipSelected);
    } catch (err) {
      console.error("Error:", err);
    }
  }

  return (
    <Modal
      open={isModalOpen}
      onCancel={() => setIsModalOpen(false)}
      title="Activate Membership"
      footer={[
        <AntdButton
          key="submit"
          type="primary"
          form="membershipForm"
          htmlType="submit"
        >
          {"提交"}
        </AntdButton>,
      ]}
    >
      <Form id="membershipForm" onFinish={onFinish}>
        <Table
          dataSource={membershipList}
          columns={columns}
          rowKey="id"
          pagination={false}
        />
      </Form>
    </Modal>
  );
}  
