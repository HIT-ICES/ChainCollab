import React from "react";
import {Row} from "antd";
import Env from "./Env";
import App from "./App";


const Dashboard: React.FC = () => {
  return (
    <>
      <Row gutter={16} style={{ marginBottom: 20 }}>
        <Env />
        <App />
      </Row>
    </>
  );
};

export default Dashboard;
