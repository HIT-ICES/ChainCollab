import React, { useEffect } from "react";
import { Card, Row, Col, Typography } from "antd";
import { useState } from "react";
import { DeploymentUnitOutlined } from "@ant-design/icons";
import DoneIcon from "@mui/icons-material/Done";
import Chip from "@mui/material/Chip";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import ClearIcon from "@mui/icons-material/Clear";
import Icon from "@mdi/react";
import { mdiGamepadCircleOutline, mdiLan } from "@mdi/js";
const { Text } = Typography;

let startIcon = <DoneIcon />;
let pauseIcon = <ClearIcon />;
interface chipProps {
  icon: JSX.Element;
  label: string;
  sx: React.CSSProperties;
}

const customColStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  marginLeft: "0px",
};
const customTextStyle: React.CSSProperties = {
  fontSize: "14px", // 可以调整字体大小以适应新的行高
  display: "flex",
  alignItems: "center",
};

const EndColStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  marginRight: "0px",
};

const Env: React.FC = () => {
  const [environments, setenvironments] = useState([
    {
      name: "test1",
      type: "Hyperledger Fabric/Raft",
      status: "started",
      chipProps: {},
    },
    {
      name: "test2",
      type: "Hyperledger Fabric/Raft",
      status: "paused",
      chipProps: {},
    },
  ]);

  useEffect(() => {
    // 首先 fetch 或者在外部使用 redux 中 orderer 节点的状态
    const updatedenvironments = environments.map((environment) => {
      if (environment.status === "paused") {
        return {
          ...environment,
          chipProps: {
            icon: pauseIcon,
            label: "paused",
            sx: {
              backgroundColor: "#5a5959",
              color: "white",
              "& .MuiSvgIcon-root": { color: "white" },
            },
          },
        };
      } else if (environment.status === "started") {
        return {
          ...environment,
          chipProps: {
            icon: startIcon,
            label: "started",
            sx: {
              backgroundColor: "#19c80a",
              color: "white",
              "& .MuiSvgIcon-root": { color: "white" },
            },
          },
        };
      }
      return environment;
    });

    setenvironments(updatedenvironments);
  }, []);
  return (
    <>
      <Col span={12}>
        <Card title="Environments" style={{ width: "100%", height: "100%" }}>
          {/* 这里的 Card.Grid 用于展示每个节点的信息，点击后跳转到节点详情页 */}
          {/* 每个 environment 都按照下面的模板进行渲染 */}
          {environments.map((environment) => (
            <Card.Grid
              style={{ width: "100%", height: "100%", cursor: "pointer" }}
              onClick={() => console.log("clicked")}
            >
              <Row style={{ width: "100%", height: "100%" }}>
                <Col span={2} style={customColStyle}>
                  <Icon path={mdiLan} size={1} />
                </Col>
                <Col span={6} style={customColStyle}>
                  <Row>
                    <Text strong style={customTextStyle}>
                      {environment.name}
                    </Text>
                  </Row>
                </Col>
                <Col span={8} style={customColStyle}>
                  <Row>
                    <Text style={customTextStyle}>{environment.type}</Text>
                  </Row>
                </Col>
                <Col span={7} style={customColStyle}>
                  <Chip {...environment.chipProps} />
                </Col>
                <Col
                  flex="auto"
                  style={{
                    ...EndColStyle,
                    textAlign: "right",
                    marginRight: "0px",
                  }}
                >
                  <KeyboardArrowRightIcon />
                </Col>
              </Row>
            </Card.Grid>
          ))}
        </Card>
      </Col>
    </>
  );
};

export default Env;
