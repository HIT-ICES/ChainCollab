import React, { useState } from "react";
import { Card, Flex, Typography } from "antd";
import { BankOutlined, LineChartOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import DelFireflyNode from "./delete";

const { Link } = Typography

const boxStyle: React.CSSProperties = {
  width: '100%'
};

const justifyOptions = [
  'flex-start',
  'center',
  'flex-end',
  'space-between',
  'space-around',
  'space-evenly',
];

const alignOptions = ['flex-start', 'center', 'flex-end'];

const cardStyle: React.CSSProperties = {
  width: "30%",
  marginBottom: "15px"
};

const gridStyle: React.CSSProperties = {
  width: "100%",
  textAlign: "start",
};

const gridDetailStyle: React.CSSProperties = {
  width: "100%",
  height: "10px",
  display: "flex",
  alignItems: "center",
  textAlign: "start"
}

const gridDeleteStyle: React.CSSProperties = {
  width: "100%",
  height: "10px",
  display: "flex",
  alignItems: "center",
  textAlign: "start"
}

interface cardItemType {
  id: string,
  nodeName: string,
  membershipName: string,
  orgName: string,
  status: string
}
import { useAppSelector } from "@/redux/hooks.ts";
import { useFireflyListData } from './hooks.ts';

const Firefly: React.FC = () => {
  const navigate = useNavigate();

  const justify = justifyOptions[0];
  const alignItems = alignOptions[0];

  const currentOrgId = useAppSelector((state) => state.org.currentOrgId);
  const currentEnvId = useAppSelector((state) => state.env.currentEnvId);
  const [fireflyList, fireflyListStatus, syncFireflyList] = useFireflyListData(currentEnvId, currentOrgId);



  const cardItem = fireflyList.map(item => (
    <Card key={item.id} title={item.name} style={cardStyle}>
      <Card.Grid style={gridStyle}>
        <Card.Meta
          avatar={<LineChartOutlined style={{
            width: "100%",
            height: "100%",
            fontSize: "200%"
          }} />}
          title="Status"
          description={"Live"}
          style={{ margin: "10px 5px 15px 20px" }}
        />
        <Card.Meta
          avatar={<BankOutlined style={{
            width: "100%",
            height: "100%",
            fontSize: "200%"
          }} />}
          title="Owning Member"
          description={item.membershipName}
          style={{ margin: "10px 5px 15px 20px" }}
        />
      </Card.Grid>
      <Card.Grid style={gridDetailStyle}>
        <Link strong onClick={() => navigate(`./${item.id}`)}>
          VIEW DETAILS
        </Link>
      </Card.Grid>
      <Card.Grid style={gridDeleteStyle}>
        <DelFireflyNode onDelete={() => {
          console.log(
            "Delete Firefly Node"
          )
        }} />
      </Card.Grid>
    </Card>
  ))

  return (
    <Flex gap="small" align="start" vertical>
      <Flex gap="large" style={boxStyle} justify={justify} align={alignItems} wrap="wrap">
        {cardItem}
      </Flex>
    </Flex>
  );
};

export default Firefly;
