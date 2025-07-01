// components/SSIController/index.tsx
import React from "react";
import AgentInfo from "./modules/AgentInfo";
import IssueCredential from "./modules/IssueCredential";
import VerifyCredential from "./modules/VerifyCredential";
import { Row } from "antd";

const SSIController: React.FC = () => {
  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 20 }}>
        <AgentInfo />  
        <ConnectionManager />
        <CredentialDefinition />
      </Row>
      <Row gutter={16} >
        <IssueCredential />
        <VerifyCredential />
      </Row>
    </div>
  );
};

export default SSIController;
