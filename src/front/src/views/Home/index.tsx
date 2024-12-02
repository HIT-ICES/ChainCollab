import styled from 'styled-components';
import { Typography, Button } from 'antd';

const { Title, Paragraph } = Typography;

const HomePageContainer = styled.div`
  max-width: 800px;
  margin: 0 auto;
  padding: 40px;
  text-align: center;
`;

const DocumentLink = styled(Button)`
  margin-right: 10px;
  background-color: #1890ff;
  border-color: #1890ff;
  &:hover {
    background-color: #40a9ff;
    border-color: #40a9ff;
  }
  &:active {
    background-color: #096dd9;
    border-color: #096dd9;
  }
`;

const StyledParagraph = styled.p`
  font-size: 16px;
  line-height: 1.8;
  margin: 20px 0;
  padding: 16px;
  background: linear-gradient(135deg, #f9f9f9, #f1f1f1);
  border-left: 4px solid #1bb6fe;
  border-radius: 8px;
  color: #333;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  text-align: justify;
`;

function HomePage() {
  return (
    <HomePageContainer>
      <Title level={1}>BlockCollab</Title>
      <StyledParagraph>
        Welcome to the enterprise multi-party collaboration platform. We are committed to providing secure, transparent, and efficient collaboration solutions based on blockchain technology.
      </StyledParagraph>
      <StyledParagraph>
        Using blockchain technology, we ensure data immutability and traceability, establishing a foundation of trust for enterprise cooperation.
      </StyledParagraph>
      <StyledParagraph>
        To learn more about how we leverage blockchain technology for collaboration, please choose from the following options:
      </StyledParagraph>
      <DocumentLink type="primary" href="/quickstart">Quick Start</DocumentLink>
      <DocumentLink type="primary" href="/platform-introduction">Platform Introduction</DocumentLink>
      <DocumentLink type="primary" href="/team-introduction">Team Introduction</DocumentLink>
    </HomePageContainer>
  );
}



export default HomePage;
