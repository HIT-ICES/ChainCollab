import React from "react";
import { Card, Row, Col, Typography, Divider } from "antd";
import { useParams } from "react-router-dom";

const { Text } = Typography;

const gridDetailStyle: React.CSSProperties = {
  width: "100%",
  // height: "20px"
}

const Detail: React.FC = () => {
  const params = useParams();

  const detailList = {
    "Membership Name": "待获取1",
    "Membership ID": params.id,
    "Organization Name": "待获取2",
    "Organization ID": "待获取3",
    "Primary Contact Email": "待获取4",
    "Join Date": "待获取5"
  };

  const detailItem = Object.entries(detailList).map(([key, value], index) => {
    return (
      // <React.Fragment key={key}>
      <Card.Grid key={key} style={gridDetailStyle}>
        <Row>
          <Col span={12}>
            <Text strong>{key}</Text>
          </Col>
          <Col span={12}>
            <Text>{value}</Text>
          </Col>
        </Row>
        {/* {index !== Object.keys(detailList).length - 1 && <Divider />}
      </React.Fragment> */}
      </Card.Grid>
    )
  })

  return (
    <Card title="Membership Detail" style={{ width: 500 }}>
      {detailItem}
    </Card>
  )
};

export default Detail;
