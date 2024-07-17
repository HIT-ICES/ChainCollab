import React, { useEffect } from "react";
import { Card, Row, Col, Typography } from "antd";
import { useState } from "react";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import Icon from "@mdi/react";
import { mdiApps } from "@mdi/js";
const { Text } = Typography;

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

const App: React.FC = () => {
  const [apps, setApps] = useState([
    {
      name: "testApp1",
      membership: "Harbin Institute of Technology",
    },
    {
      name: "testApp2",
      membership: "Peking University",
    },
    {
      name: "testApp2",
      membership: "TsingHua University",
    },
  ]);

  useEffect(() => {
    // 首先 fetch 或者在外部使用 redux 中 orderer 节点的状态
    // setApps(updatedApps);
  }, []);
  return (
    <>
      <Col span={12}>
        <Card title="apps" style={{ width: "100%", height: "100%" }}>
          {/* 这里的 Card.Grid 用于展示每个节点的信息，点击后跳转到节点详情页 */}
          {/* 每个 app 都按照下面的模板进行渲染 */}
          {apps.map((app) => (
            <Card.Grid
              style={{ width: "100%", height: "100%", cursor: "pointer" }}
              onClick={() => console.log("clicked")}
            >
              <Row style={{ width: "100%", height: "100%" }}>
                <Col span={2} style={customColStyle}>
                  <Icon path={mdiApps} size={1} />
                </Col>
                <Col span={6} style={customColStyle}>
                  <Row>
                    <Text strong style={customTextStyle}>
                      {app.name}
                    </Text>
                  </Row>
                </Col>
                <Col span={15} style={customColStyle}>
                  <Row>
                    <Text style={customTextStyle}>{app.membership}</Text>
                  </Row>
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

export default App;
