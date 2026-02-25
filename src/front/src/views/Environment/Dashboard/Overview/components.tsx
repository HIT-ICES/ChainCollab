
import React, { useState } from 'react';
import { Typography, Steps, Checkbox, Modal, Button as AntdButton, Form, Table, Tag } from 'antd';
import { styled } from "@mui/material/styles";
import Button, { ButtonProps } from "@mui/material/Button";
import { purple } from "@mui/material/colors";

import BadgeIcon from "@mui/icons-material/Badge";
import AccountBalanceWalletIcon from "@mui/icons-material/AccountBalanceWallet";
import FireflyIcon from "@/assets/icons/fireflyIcon.svg"
import OracleIcon from "@/assets/icons/oracleIcon.svg"
import DmnIcon from "@/assets/icons/dmnIcon.svg"
import LinkIcon from "@mui/icons-material/Link";
import DatasetIcon from "@mui/icons-material/Dataset";
import FunctionsIcon from "@mui/icons-material/Functions";
import HubIcon from "@mui/icons-material/Hub";


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

  const { color = "#4e4d4a", logo, title, status, onSetup, onOpen, taskInfo } = props
  const taskTypeLabelMap: Record<string, string> = {
    FABRIC_FIREFLY_INSTALL: "Firefly Install",
    FABRIC_FIREFLY_START: "Firefly Start",
    ETH_FIREFLY_INSTALL: "ETH Firefly Install",
    FABRIC_ORACLE_INSTALL: "Oracle Install",
    ETH_ORACLE_INSTALL: "ETH Oracle Install",
    FABRIC_DMN_INSTALL: "DMN Install",
    ETH_DMN_INSTALL: "ETH DMN Install",
    CHAINLINK_INSTALL: "Chainlink + DMN Install",
    DMN_FIREFLY_REGISTER: "Register DMN to Firefly",
    DATA_CONTRACT_SETUP: "Data Contract Setup",
    DATA_CONTRACT_FIREFLY_REGISTER: "Register Data Contract to Firefly",
    COMPUTE_CONTRACT_SETUP: "Compute Contract Setup",
    COMPUTE_CONTRACT_FIREFLY_REGISTER: "Register Compute Contract to Firefly",
    RELAYER_CONTRACT_SETUP: "Relayer Contract Setup",
    RELAYER_CONTRACT_FIREFLY_REGISTER: "Register Relayer Contract to Firefly",
    IDENTITY_CONTRACT_INSTALL: "Identity Contract Install",
    IDENTITY_CONTRACT_REDEPLOY: "Identity Contract Redeploy",
  };
  const knownUpper = new Set(["ETH", "DMN", "OCR", "API", "URL", "FFI", "ID"]);
  const humanizeToken = (token: string) => {
    if (!token) return "";
    const upper = token.toUpperCase();
    if (knownUpper.has(upper)) return upper;
    return upper.charAt(0) + upper.slice(1).toLowerCase();
  };
  const humanizeRaw = (value: any) =>
    String(value || "")
      .split("_")
      .filter(Boolean)
      .map(humanizeToken)
      .join(" ");
  const resolveTaskLabel = (info: any) => {
    const rawType = String(info?.type || "").toUpperCase();
    const typeLabel = taskTypeLabelMap[rawType] || humanizeRaw(rawType) || "Task";
    const customLabel = String(info?.label || "").trim();
    if (!customLabel) {
      return typeLabel;
    }
    if (customLabel === rawType || customLabel === String(info?.type || "")) {
      return typeLabel;
    }
    return customLabel;
  };
  const resolveTaskStatus = (value: any) => {
    const normalized = String(value || "").toUpperCase();
    if (normalized === "RUNNING") return { label: "Running", color: "processing" as const };
    if (normalized === "PENDING") return { label: "Pending", color: "default" as const };
    if (normalized === "SUCCESS") return { label: "Success", color: "success" as const };
    if (["FAILED", "ERROR"].includes(normalized)) return { label: "Failed", color: "error" as const };
    if (normalized.startsWith("ROLLBACK")) return { label: "Rollback", color: "warning" as const };
    return { label: humanizeRaw(normalized) || "Unknown", color: "default" as const };
  };
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
  const taskStatus = resolveTaskStatus(taskInfo?.status);
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
        cursor: "default",
      }}
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
        {taskInfo ? (
          <div style={{ marginTop: 8, padding: 8, borderRadius: 8, background: "#f8fafc", border: "1px dashed #cbd5f5" }}>
            <Text strong style={{ color: "#0f172a", display: "block" }}>{resolveTaskLabel(taskInfo)}</Text>
            <div style={{ marginTop: 6, display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
              <Tag color={taskStatus.color} style={{ marginInlineEnd: 0 }}>
                {taskStatus.label}
              </Tag>
              {taskInfo.step ? <Tag style={{ marginInlineEnd: 0 }}>{humanizeRaw(taskInfo.step)}</Tag> : null}
            </div>
            {taskInfo.step ? (
              <Text type="secondary" style={{ display: "block", marginTop: 4, fontSize: 12, wordBreak: "break-word" }}>
                {taskInfo.step}
              </Text>
            ) : null}
            {taskInfo.error ? (
              <Text type="danger" style={{ display: "block", marginTop: 4, fontSize: 12, wordBreak: "break-word" }}>
                {taskInfo.error}
              </Text>
            ) : null}
            {taskInfo.updated_at || taskInfo.updatedAt ? (
              <Text type="secondary" style={{ display: "block", marginTop: 4, fontSize: 11 }}>
                {new Date(taskInfo.updated_at || taskInfo.updatedAt).toLocaleTimeString()}
              </Text>
            ) : null}
          </div>
        ) : null}
      </div>
      {onSetup || onOpen ? (
        <div
          style={{
            marginTop: "auto",
            display: "flex",
            justifyContent: "center",
            flexWrap: "wrap",
            gap: 8,
          }}
          onClick={(event) => event.stopPropagation()}
        >
          {onSetup
            ? (React.isValidElement(onSetup) ? onSetup : (
              <Button
                size="small"
                variant="outlined"
                onClick={onSetup}
                style={{ borderRadius: 8, height: 32, textTransform: "none" }}
              >
                Install
              </Button>
            ))
            : null}
          {onOpen ? (
            <Button
              size="small"
              variant="outlined"
              onClick={onOpen}
              style={{ borderRadius: 8, height: 32, textTransform: "none" }}
            >
              Check
            </Button>
          ) : null}
        </div>
      ) : null}
    </div >)
}

export const FireflyComponentCard = ({
  ChaincodeStatus = false,
  ClusterStatus = false,
  taskInfo,
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
      taskInfo={taskInfo}
      onSetup={onSetup}
      onOpen={onOpen}
    />
  );
}

export const OracleComponentCard = ({
  ChaincodeStatus = false,
  statusKey = "ChainCode",
  taskInfo,
  onSetup,
  onOpen
}) => {
  return (
    <CustomCard
      color="#2790b0"
      logo={<img src={OracleIcon} alt="firefly" style={{ width: 100, height: 100 }} />}
      title="Oracle"
      status={[
        { key: statusKey, value: ChaincodeStatus }
      ]}
      taskInfo={taskInfo}
      onSetup={onSetup}
      onOpen={onOpen}
    />
  );
}

export const DMNComponentCard = ({
  ChaincodeStatus = false,
  statusKey = "ChainCode",
  FireflyStatus = null,
  taskInfo,
  onSetup,
  onOpen
}) => {
  const statusItems = [{ key: statusKey, value: ChaincodeStatus }];
  if (FireflyStatus !== null && FireflyStatus !== undefined) {
    statusItems.push({ key: "FireFly", value: FireflyStatus });
  }
  return (
    <CustomCard
      color="#ffaa00"
      logo={<img src={DmnIcon} alt="dmn" style={{ width: 100, height: 100 }} />}
      title="DMN"
      status={statusItems}
      taskInfo={taskInfo}
      onSetup={onSetup}
      onOpen={onOpen}
    />
  );
}

export const IdentityContractComponentCard = ({
  ContractStatus = "NO",
  taskInfo,
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
      taskInfo={taskInfo}
      onSetup={onSetup}
      onOpen={onOpen}
    />
  );
}

export const DataContractComponentCard = ({
  ContractStatus = "NO",
  FireflyStatus = null,
  taskInfo,
  onSetup,
  onOpen
}) => {
  const statusItems = [{ key: "Contract", value: ContractStatus }];
  if (FireflyStatus !== null && FireflyStatus !== undefined) {
    statusItems.push({ key: "FireFly", value: FireflyStatus });
  }
  return (
    <CustomCard
      color="#14b8a6"
      logo={<DatasetIcon style={{ fontSize: 80, color: "#1e293b" }} />}
      title="Data Contract"
      status={statusItems}
      taskInfo={taskInfo}
      onSetup={onSetup}
      onOpen={onOpen}
    />
  );
}

export const ComputeContractComponentCard = ({
  ContractStatus = "NO",
  FireflyStatus = null,
  taskInfo,
  onSetup,
  onOpen
}) => {
  const statusItems = [{ key: "Contract", value: ContractStatus }];
  if (FireflyStatus !== null && FireflyStatus !== undefined) {
    statusItems.push({ key: "FireFly", value: FireflyStatus });
  }
  return (
    <CustomCard
      color="#f97316"
      logo={<FunctionsIcon style={{ fontSize: 80, color: "#1e293b" }} />}
      title="Compute Contract"
      status={statusItems}
      taskInfo={taskInfo}
      onSetup={onSetup}
      onOpen={onOpen}
    />
  );
}

export const RelayerComponentCard = ({
  ContractStatus = "NO",
  NodeStatus = "NO",
  FireflyStatus = null,
  taskInfo,
  onSetup,
  onOpen
}) => {
  const statusItems = [
    { key: "Contract", value: ContractStatus },
    { key: "Node", value: NodeStatus },
  ];
  if (FireflyStatus !== null && FireflyStatus !== undefined) {
    statusItems.push({ key: "FireFly", value: FireflyStatus });
  }
  return (
    <CustomCard
      color="#6366f1"
      logo={<HubIcon style={{ fontSize: 80, color: "#1e293b" }} />}
      title="Relayer"
      status={statusItems}
      taskInfo={taskInfo}
      onSetup={onSetup}
      onOpen={onOpen}
    />
  );
}

export const ChainlinkComponentCard = ({
  ClusterStatus = "NO",
  onSetup,
  onOpen
}) => {
  return (
    <CustomCard
      color="#0ea5e9"
      logo={<LinkIcon style={{ fontSize: 80, color: "#1e293b" }} />}
      title="Chainlink"
      status={[
        { key: "Cluster", value: ClusterStatus }
      ]}
      onSetup={onSetup}
      onOpen={onOpen}
    />
  );
}

export const SystemAccountComponentCard = ({
  AccountStatus = "NO",
  onOpen
}) => {
  return (
    <CustomCard
      color="#16a34a"
      logo={<AccountBalanceWalletIcon style={{ fontSize: 80, color: "#1e293b" }} />}
      title="System Account"
      status={[
        { key: "Account", value: AccountStatus }
      ]}
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

  React.useEffect(() => {
    if (!isModalOpen) {
      return;
    }
    const allIds = Array.isArray(membershipList)
      ? membershipList.map((item) => item.id)
      : [];
    setMembershipSelected(allIds);
  }, [isModalOpen, membershipList]);


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
        <Checkbox
          value={id}
          checked={membershipSelected.includes(id)}
          onChange={(e) => {
            if (e.target.checked) {
              setMembershipSelected([...membershipSelected, id])
            } else {
              setMembershipSelected(membershipSelected.filter((item) => item !== id))
            }
          }}
        />
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
