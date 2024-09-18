import React, { useEffect } from "react";
import { Card, Row, Col, Typography, Steps } from "antd";
import { useState } from "react";
import Icon from "@mdi/react";
import {
  mdiCardAccountDetailsOutline,
  mdiChartLine,
  mdiAccountCircleOutline,
  mdiCalendarClock,
} from "@mdi/js";
import Chip from "@mui/material/Chip";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
const { Text } = Typography;
import ClearIcon from "@mui/icons-material/Clear";
import DoneIcon from "@mui/icons-material/Done";
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

const EndColStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  marginRight: "0px",
};



interface CAProps {
  status: string;
  id: string;
  membership: string;
  creationDate: string;
}
const CA = () => {
  const [CADetails, setCADetails] = useState<CAProps[]>([]); // 用于存储CA的状态
  const [chipProps, setChipProps] = useState({
    icon: startIcon,
    label: "started",
    sx: {
      backgroundColor: "#19c80a",
      color: "white",
      "& .MuiSvgIcon-root": { color: "white" },
    },
  });

  return (
    <Col span={8}>
      <Card
        title="Certificate Authorities"
        style={{ width: "100%", height: "100%" }}
      >
        <Card.Grid
          style={{ width: "100%", height: "100%" }}
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
              <Chip {...chipProps} />
            </Col>
          </Row>
        </Card.Grid>
        <Card.Grid
          style={{ width: "100%", height: "100%" }}
        >
          <Row style={{ width: "100%", height: "100%" }}>
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
            <Col span={8} style={customColStyle}>
              <Row>
                <Text style={customTextStyle}>u1mxji3lo6</Text>
              </Row>
            </Col>
          </Row>
        </Card.Grid>
        <Card.Grid
          style={{ width: "100%", height: "100%" }}
        >
          <Row style={{ width: "100%", height: "100%" }}>
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
            <Col span={8} style={customColStyle}>
              <Row>
                <Text style={customTextStyle}>
                  Loleido
                </Text>
              </Row>
            </Col>
          </Row>
        </Card.Grid>
        <Card.Grid
          style={{ width: "100%", height: "100%" }}
        >
          <Row style={{ width: "100%", height: "100%" }}>
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
            <Col span={8} style={customColStyle}>
              <Row>
                <Text style={customTextStyle}>2024/1/24 23:49:22</Text>
              </Row>
            </Col>
          </Row>
        </Card.Grid>
      </Card>
    </Col>
  );
};
export default CA;
