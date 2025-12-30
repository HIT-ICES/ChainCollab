import React, { useEffect, useState } from "react";
import { Card, Row, Col, Typography, Empty } from "antd";
import Icon from "@mdi/react";
import {
  mdiCardAccountDetailsOutline,
  mdiChartLine,
  mdiAccountCircleOutline,
  mdiCalendarClock,
} from "@mdi/js";
import Chip from "@mui/material/Chip";
const { Text } = Typography;
import ClearIcon from "@mui/icons-material/Clear";
import DoneIcon from "@mui/icons-material/Done";
import { useAppSelector } from "@/redux/hooks";
import { getResourceSets, getNodeList } from "@/api/resourceAPI";
let pauseIcon = <ClearIcon />;
let startIcon = <DoneIcon />;
const customColStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  marginLeft: "0px",
};

//
const customTextStyle: React.CSSProperties = {
  fontSize: "14px", // 可以调整字体大小以适应新的行高
  display: "flex",
  alignItems: "center",
};

interface CAProps {
  status: string;
  id: string;
  membership: string;
  creationDate: string;
}
const CA = () => {
  const currentEnvId = useAppSelector((state) => state.env.currentEnvId);
  const [CADetails, setCADetails] = useState<CAProps[]>([]);

  useEffect(() => {
    const fetchCA = async () => {
      if (!currentEnvId) {
        setCADetails([]);
        return;
      }
      const resourceSets = await getResourceSets(currentEnvId);
      const caNodes = await Promise.all(
        resourceSets.map(async (resourceSet: any) => {
          const nodes = await getNodeList(resourceSet.id, "ca");
          return nodes.map((node: any) => ({
            id: node.id,
            status: node.status,
            membership: resourceSet.membershipName || resourceSet.name,
            creationDate: node.createdAt,
          }));
        })
      );
      setCADetails(caNodes.flat());
    };
    fetchCA();
  }, [currentEnvId]);

  const getChipProps = () => ({
    icon: startIcon,
    label: "Active",
    sx: {
      backgroundColor: "#19c80a",
      color: "white",
      "& .MuiSvgIcon-root": { color: "white" },
    },
  });

  const formatDate = (value?: string) => {
    if (!value) {
      return "-";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return date.toLocaleString();
  };

  return (
    <Col span={8}>
      <Card
        title="Certificate Authorities"
        style={{ width: "100%", height: "100%" }}
      >
        {CADetails.length === 0 ? (
          <Empty description="No CA nodes" />
        ) : (
          CADetails.map((ca) => (
            <div
              key={ca.id}
              style={{
                border: "1px solid #e2e8f0",
                borderRadius: 12,
                padding: "10px 12px",
                marginBottom: 12,
                background: "linear-gradient(145deg, #ffffff, #f8fafc)",
              }}
            >
              <Row style={{ width: "100%", height: "100%" }}>
                <Col span={2} style={customColStyle}>
                  <Icon path={mdiChartLine} size={1} />
                </Col>
                <Col span={6} style={customColStyle}>
                  <Row>
                    <Text strong style={customTextStyle}>
                      Status
                    </Text>
                  </Row>
                </Col>
                <Col span={8} style={customColStyle}>
                  <Chip {...getChipProps()} />
                </Col>
              </Row>
              <Row style={{ width: "100%", height: "100%", marginTop: 8 }}>
                <Col span={2} style={customColStyle}>
                  <Icon path={mdiCardAccountDetailsOutline} size={1} />
                </Col>
                <Col span={6} style={customColStyle}>
                  <Row>
                    <Text strong style={customTextStyle}>
                      ID
                    </Text>
                  </Row>
                </Col>
                <Col span={14} style={customColStyle}>
                  <Row>
                    <Text style={customTextStyle}>{ca.id}</Text>
                  </Row>
                </Col>
              </Row>
              <Row style={{ width: "100%", height: "100%", marginTop: 8 }}>
                <Col span={2} style={customColStyle}>
                  <Icon path={mdiAccountCircleOutline} size={1} />
                </Col>
                <Col span={6} style={customColStyle}>
                  <Row>
                    <Text strong style={customTextStyle}>
                      Membership
                    </Text>
                  </Row>
                </Col>
                <Col span={14} style={customColStyle}>
                  <Row>
                    <Text style={customTextStyle}>{ca.membership}</Text>
                  </Row>
                </Col>
              </Row>
              <Row style={{ width: "100%", height: "100%", marginTop: 8 }}>
                <Col span={2} style={customColStyle}>
                  <Icon path={mdiCalendarClock} size={1} />
                </Col>
                <Col span={6} style={customColStyle}>
                  <Row>
                    <Text strong style={customTextStyle}>
                      Creation Date
                    </Text>
                  </Row>
                </Col>
                <Col span={14} style={customColStyle}>
                  <Row>
                    <Text style={customTextStyle}>{formatDate(ca.creationDate)}</Text>
                  </Row>
                </Col>
              </Row>
            </div>
          ))
        )}
      </Card>
    </Col>
  );
};
export default CA;
