import React, { useEffect, useMemo, useState } from "react";
import { Card, Row, Col, Typography, Tag, Empty, Tooltip } from "antd";
import DoneIcon from "@mui/icons-material/Done";
import Chip from "@mui/material/Chip";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import ClearIcon from "@mui/icons-material/Clear";
import Icon from "@mdi/react";
import { mdiLan } from "@mdi/js";
import { useNavigate } from "react-router-dom";
import { getEnvironmentList } from "@/api/platformAPI";
import { useAppSelector } from "@/redux/hooks";
import { selectConsortium } from "@/redux/slices/consortiumSlice";
import { selectOrg } from "@/redux/slices/orgSlice";
const { Text } = Typography;

const statusStyles: Record<string, { label: string; color: string; bg: string; icon?: JSX.Element }> = {
  CREATED: { label: "Created", color: "#475569", bg: "#e2e8f0" },
  INITIALIZED: { label: "Initialized", color: "#1e40af", bg: "#dbeafe" },
  STARTED: { label: "Started", color: "#0f766e", bg: "#ccfbf1", icon: <DoneIcon /> },
  ACTIVATED: { label: "Activated", color: "#047857", bg: "#d1fae5", icon: <DoneIcon /> },
  PAUSED: { label: "Paused", color: "#7c2d12", bg: "#ffedd5", icon: <ClearIcon /> },
};

const summaryCardStyle: React.CSSProperties = {
  borderRadius: 14,
  padding: "10px 14px",
  border: "1px solid #e2e8f0",
  background: "linear-gradient(145deg, #ffffff, #f8fafc)",
};

const envCardStyle: React.CSSProperties = {
  borderRadius: 14,
  padding: "14px 16px",
  border: "1px solid #e2e8f0",
  background: "linear-gradient(145deg, #ffffff, #f8fafc)",
  cursor: "pointer",
  transition: "transform 0.2s ease, box-shadow 0.2s ease",
};

const Env: React.FC = () => {
  const navigate = useNavigate();
  const currentConsortiumId = useAppSelector(selectConsortium).currentConsortiumId;
  const currentOrgId = useAppSelector(selectOrg).currentOrgId;
  const [environments, setenvironments] = useState<any[]>([]);

  useEffect(() => {
    let mounted = true;
    const fetchEnvs = async () => {
      if (!currentConsortiumId) {
        if (mounted) {
          setenvironments([]);
        }
        return;
      }
      const data = await getEnvironmentList(currentConsortiumId);
      if (mounted) {
        setenvironments(Array.isArray(data) ? data : []);
      }
    };
    fetchEnvs();
    return () => {
      mounted = false;
    };
  }, [currentConsortiumId]);

  const summary = useMemo(() => {
    const total = environments.length;
    const running = environments.filter((env) =>
      ["STARTED", "ACTIVATED"].includes((env.status || "").toUpperCase())
    ).length;
    const preparing = environments.filter((env) =>
      ["CREATED", "INITIALIZED"].includes((env.status || "").toUpperCase())
    ).length;
    const paused = environments.filter((env) =>
      ["PAUSED"].includes((env.status || "").toUpperCase())
    ).length;
    return { total, running, preparing, paused };
  }, [environments]);

  const getStatusChip = (status?: string) => {
    const key = (status || "CREATED").toUpperCase();
    const meta = statusStyles[key] || statusStyles.CREATED;
    return (
      <Chip
        icon={meta.icon}
        label={meta.label}
        sx={{
          backgroundColor: meta.bg,
          color: meta.color,
          fontWeight: 600,
          "& .MuiSvgIcon-root": { color: meta.color },
        }}
      />
    );
  };

  const formatDate = (value?: string) => {
    if (!value) {
      return "-";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return date.toLocaleDateString();
  };

  return (
    <Card
      title="Environments"
      style={{ width: "100%", height: "100%" }}
      headStyle={{ borderBottom: "1px solid #e2e8f0", fontWeight: 600 }}
    >
      <Row gutter={[12, 12]} style={{ marginBottom: 12 }}>
        <Col span={6}>
          <div style={summaryCardStyle}>
            <Text type="secondary">Total</Text>
            <div style={{ fontSize: 22, fontWeight: 700 }}>{summary.total}</div>
          </div>
        </Col>
        <Col span={6}>
          <div style={summaryCardStyle}>
            <Text type="secondary">Running</Text>
            <div style={{ fontSize: 22, fontWeight: 700 }}>{summary.running}</div>
          </div>
        </Col>
        <Col span={6}>
          <div style={summaryCardStyle}>
            <Text type="secondary">Preparing</Text>
            <div style={{ fontSize: 22, fontWeight: 700 }}>{summary.preparing}</div>
          </div>
        </Col>
        <Col span={6}>
          <div style={summaryCardStyle}>
            <Text type="secondary">Paused</Text>
            <div style={{ fontSize: 22, fontWeight: 700 }}>{summary.paused}</div>
          </div>
        </Col>
      </Row>

      {environments.length === 0 ? (
        <Empty description="No environments yet" />
      ) : (
        <Row gutter={[12, 12]}>
          {environments.map((environment) => (
            <Col span={24} key={environment.id}>
              <div
                style={envCardStyle}
                onClick={() =>
                  navigate(
                    `/orgs/${currentOrgId}/consortia/${currentConsortiumId}/envs/${environment.id}/envdashboard`
                  )
                }
                onMouseEnter={(event) => {
                  (event.currentTarget as HTMLDivElement).style.boxShadow =
                    "0 12px 30px rgba(15,23,42,0.12)";
                  (event.currentTarget as HTMLDivElement).style.transform = "translateY(-2px)";
                }}
                onMouseLeave={(event) => {
                  (event.currentTarget as HTMLDivElement).style.boxShadow = "none";
                  (event.currentTarget as HTMLDivElement).style.transform = "translateY(0)";
                }}
              >
                <Row align="middle" gutter={12}>
                  <Col flex="32px">
                    <Icon path={mdiLan} size={1} />
                  </Col>
                  <Col flex="auto">
                    <Row justify="space-between" align="middle">
                      <Col>
                        <Text strong style={{ fontSize: 15 }}>
                          {environment.name}
                        </Text>
                        <div style={{ marginTop: 4 }}>
                          <Text type="secondary">Created: {formatDate(environment.createdAt)}</Text>
                        </div>
                      </Col>
                      <Col>
                        {getStatusChip(environment.status)}
                      </Col>
                    </Row>
                    <Row style={{ marginTop: 10 }} gutter={[8, 8]}>
                      <Col>
                        <Tooltip title="Firefly status">
                          <Tag color={environment.fireflyStatus === "STARTED" ? "green" : "default"}>
                            Firefly {environment.fireflyStatus || "NO"}
                          </Tag>
                        </Tooltip>
                      </Col>
                      <Col>
                        <Tooltip title="Oracle status">
                          <Tag color={environment.oracleStatus === "CHAINCODEINSTALLED" ? "blue" : "default"}>
                            Oracle {environment.oracleStatus || "NO"}
                          </Tag>
                        </Tooltip>
                      </Col>
                      <Col>
                        <Tooltip title="DMN status">
                          <Tag color={environment.dmnStatus === "CHAINCODEINSTALLED" ? "purple" : "default"}>
                            DMN {environment.dmnStatus || "NO"}
                          </Tag>
                        </Tooltip>
                      </Col>
                    </Row>
                  </Col>
                  <Col>
                    <KeyboardArrowRightIcon />
                  </Col>
                </Row>
              </div>
            </Col>
          ))}
        </Row>
      )}
    </Card>
  );
};

export default Env;
