
import React, { useState } from 'react';
import { Typography, Steps, Checkbox, Modal, Button as AntdButton, Form, Table } from 'antd';
import { styled } from "@mui/material/styles";
import Button, { ButtonProps } from "@mui/material/Button";
import { purple } from "@mui/material/colors";

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

  const { color = "#4e4d4a", logo, title, status } = props
  return (
    <div
      style={{
        width: 220,
        minHeight: 220,
        background: `linear-gradient(145deg, ${color} 0%, #ffffff 80%)`,
        border: "1px solid #e2e8f0",
        borderRadius: 16,
        margin: "10px",
        padding: 16,
        display: "flex",
        flexDirection: "column",
        boxShadow: "0 12px 30px rgba(15,23,42,0.12)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center" }}>
        {logo}
      </div>
      <Title level={4} style={{ textAlign: "center", marginTop: 12, marginBottom: 8 }}>
        {title}
      </Title>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }} >
        {status.map((item) => {
          const active = item.value;
          return (
            <div key={item.key} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  backgroundColor: active ? "#22c55e" : "#f43f5e",
                  boxShadow: active ? "0 0 0 4px rgba(34,197,94,0.15)" : "0 0 0 4px rgba(244,63,94,0.12)"
                }}
              />
              <Text strong style={{ color: "#0f172a" }}>{item.key}</Text>
              <Text type="secondary">{active ? "Running" : "Pending"}</Text>
            </div>
          );
        })}
      </div>
    </div >)
}

export const FireflyComponentCard = ({
  ChaincodeStatus = false,
  ClusterStatus = false
}) => {
  return (
    <CustomCard
      color="#88c100"
      logo={<img src={FireflyIcon} alt="firefly" style={{ width: 100, height: 100 }} />} title="Firefly" status={[
        { key: "ChainCode", value: ChaincodeStatus },
        { key: "Cluster", value: ClusterStatus }
      ]} />
  );
}

export const OracleComponentCard = ({
  ChaincodeStatus = false
}) => {
  return (
    <CustomCard
      color="#2790b0"
      logo={<img src={OracleIcon} alt="firefly" style={{ width: 100, height: 100 }} />} title="Oracle" status={[
        { key: "ChainCode", value: ChaincodeStatus }
      ]} />
  );
}

export const DMNComponentCard = ({
  ChaincodeStatus = false
}) => {
  return (
    <CustomCard
      color="#ffaa00"
      logo={<img src={DmnIcon} alt="relayer" style={{ width: 100, height: 100 }} />} title="Relayer" status={[
        { key: "ChainCode", value: ChaincodeStatus }
      ]} />
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
