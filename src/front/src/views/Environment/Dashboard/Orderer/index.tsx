import React, {useEffect} from "react";
import { Card, Row, Col, Typography } from "antd";
import { useState } from "react";
import { DeploymentUnitOutlined } from "@ant-design/icons";
import DoneIcon from "@mui/icons-material/Done";
import Chip from "@mui/material/Chip";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import ClearIcon from '@mui/icons-material/Clear';
const { Text } = Typography;

const customColStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  marginLeft: "0px",
};

const EndColStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  marginRight: "0px",
};

const customTextStyle: React.CSSProperties = {
  fontSize: "14px",
};

let startIcon = <DoneIcon />;
let pauseIcon = <ClearIcon />;
const Overview: React.FC = () => {
  const [ordererNode, setOrdererNode] = useState({
    "Name": "Node",
    "Membership": "HIT",
    "status": "started"
  });

  const [chipProps, setChipProps] = useState({
    icon: startIcon,
    label: "started",
    sx: {
      backgroundColor: "#19c80a",
      color: "white",
      "& .MuiSvgIcon-root": { color: "white" },
    }
  });
  useEffect(() => {
    // 首先 fetch 或者在外部使用 redux 中 orderer 节点的状态
    if (ordererNode.status === "paused") {
      setChipProps({
        icon: pauseIcon,
        label: "paused",
        sx: {
          backgroundColor: "#5a5959",
          color: "white",
          "& .MuiSvgIcon-root": { color: "white" },
        }
      }
      );
    }else if (ordererNode.status === "started") {
        setChipProps({
            icon: startIcon,
            label: "started",
            sx: {
            backgroundColor: "#19c80a",
            color: "white",
            "& .MuiSvgIcon-root": { color: "white" },
            }
        }
        );
    }
  }, []);
  return (
      <>
        <Col span={12}>
          <Card title="Orderer Nodes" style={{ width: "100%", height: "100%" }}>
            <Card.Grid style={{ width: "100%", height: "100%", cursor: "pointer" }}>
              <Row style={{ width: "100%", height: "100%" }}>
                <Col span={2} style={customColStyle}>
                  <DeploymentUnitOutlined style={{ fontSize: 32 }} />
                </Col>
                <Col span={6} style={customColStyle}>
                  <Row>
                    <Text strong style={customTextStyle}>{ordererNode.Name}</Text>
                  </Row>
                </Col>
                <Col span={8} style={customColStyle}>
                  <Row>
                    <Text style={customTextStyle}>{ordererNode.Membership}</Text>
                  </Row>
                </Col>
                <Col span={7} style={customColStyle}>
                  <Chip {...chipProps} />
                </Col>
                <Col flex="auto" style={{...EndColStyle, textAlign: "right", marginRight: "0px"}}>
                  <KeyboardArrowRightIcon />
                </Col>
              </Row>
            </Card.Grid>
          </Card>
        </Col>
      </>
  );
};

export default Overview;
