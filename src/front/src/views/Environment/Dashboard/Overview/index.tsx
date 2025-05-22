import React, { useEffect, useState, useRef } from "react";
import {
  Card,
  Row,
  Col,
  Typography,
  Button as AntdButton,
  message,
  Modal,
  Form,
  Input,
  Spin
} from "antd";

import ClearAllIcon from "@mui/icons-material/ClearAll";
import CalendarMonthIcon from "@mui/icons-material/CalendarMonth";
import PeopleIcon from "@mui/icons-material/People";
import CalendarTodayIcon from "@mui/icons-material/CalendarToday";
import Icon from "@mdi/react";

import { mdiUngroup } from "@mdi/js";
import Button, { ButtonProps } from "@mui/material/Button";
import LoadingButton from '@mui/lab/LoadingButton';
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import { purple } from "@mui/material/colors";
import { useNavigate } from "react-router-dom";
const { Text, Title } = Typography;
import {
  InitEnv,
  JoinEnv,
  StartEnv,
  ActivateEnv,
  InstallFirefly,
  InstallOracle,
  InstallDmnEngine,
  StartFireflyForEnv,
  requestOracleFFI,
  submitSSIExpansion
} from "@/api/resourceAPI";

import {
  registerInterface,
  registerAPI
} from "@/api/executionAPI"

const systemFireflyURL = "http://127.0.0.1:5000"


import { useEnvInfo, useMembershipListData } from './hooks'
import { useAppSelector } from '@/redux/hooks'


import {
  customColStyle,
  customTextStyle,
  ColorButton,

  NaiveFabricStepBar,

  FireflyComponentCard,
  OracleComponentCard,
  DMNComponentCard,

  JoinModal
} from "./components.tsx";

import {
  DBstatus2stepandstatus
} from './utils'


const Overview: React.FC = () => {
  const [isSSIModalOpen, setIsSSIModalOpen] = useState(false);
  const [ssiForm] = Form.useForm();

  const navigate = useNavigate();
  const [isJoinModelOpen, setIsJoinModelOpen] = useState(false);
  const [envInfo, setSync] = useEnvInfo()
  const currentOrgId = useAppSelector(state => state.org.currentOrgId)
  const currentConsortiumId = useAppSelector(state => state.consortium.currentConsortiumId)
  const currentEnvId = useAppSelector(state => state.env.currentEnvId)
  const [membershipList, setSyncMembershipList] = useMembershipListData()
  const stepAndStatus = DBstatus2stepandstatus(envInfo.status)


  const setupCallBackRef = useRef(null)

  const [setupFabricNetWorkLoading, setSetupFabricNetWorkLoading] = useState(false)

  const [setupComponentLoading, setSetupComponentLoading] = useState(false)

  const handleSubmitSSIExpansion = async () => {
    try {
      const values = await ssiForm.validateFields();
      const payload = membershipList.map((m) => ({
        membership_id: m.id,
        url: values[`url_${m.id}`],
        public_did: values[`did_${m.id}`],
      }));
      await submitSSIExpansion(currentEnvId, payload);
      message.success("Submitted successfully");
      setIsSSIModalOpen(false);
    } catch (err) {
      message.error("Submission failed");
    }
  };
  
  
  const handleSetUpFabricNetwork = async () => {
    // Init
    setSetupFabricNetWorkLoading(true)
    await InitEnv(currentEnvId)
    setSync()
    // will stick at join page
    await new Promise((resolve, reject) => {
      setIsJoinModelOpen(true)
      setupCallBackRef.current = resolve
    })
    setSync()
    // Start it
    await StartEnv(currentEnvId)
    setSync()
    // Activate it
    await ActivateEnv(currentEnvId, currentOrgId)
    setSetupFabricNetWorkLoading(false)
    setSync()
  }

  const handleSetUpComponent = async () => {
    setSetupComponentLoading(true)
    await InstallFirefly(currentOrgId, currentEnvId)
    setSync()
    await StartFireflyForEnv(currentEnvId)
    setSync()
    await InstallOracle(currentOrgId, currentEnvId)
    // register interface
    const oracleFFI = await requestOracleFFI()
    const res = await registerInterface(systemFireflyURL, oracleFFI.ffiContent, "Oracle")
    await new Promise((resolve, reject) => {
      setTimeout(resolve, 5000)
    })
    const res2 = await registerAPI(systemFireflyURL, "Oracle", "default", "Oracle", res.id)
    setSync()
    await InstallDmnEngine(currentOrgId, currentEnvId)
    setSync()
    setSetupComponentLoading(false)
  }

  return (
    <>
      <Col span={16}>
        <Card title="Overview" style={{ width: "100%" }}>
          {/* Naive Network */}
          <Card.Grid style={{ width: "100%", height: "100%" }}>
            <Row
              justify="space-between"
              style={{ width: "100%", height: "100%" }}
            >
              <Col span={2} style={customColStyle}>
                <ClearAllIcon style={{ fontSize: 24 }} />
              </Col>
              <Col span={8} style={customColStyle}>
                <Text strong style={customTextStyle}>
                  Naive Network
                </Text>
              </Col>
              <Col
                flex="auto"
                style={{ display: 'flex', flexDirection: 'row', justifyContent: 'flex-end' }}
              >
                <LoadingButton
                  variant="outlined"
                  onClick={() => { handleSetUpFabricNetwork() }}
                  loading={setupFabricNetWorkLoading}
                >
                  SetUp Fabric Newwork
                </LoadingButton>
              </Col>
            </Row>
            <Row>
              <Col
                style={{
                  ...customColStyle,
                  marginLeft: "40px",
                  width: "100%",
                  marginTop: "10px",
                }}
              >
                <NaiveFabricStepBar
                  stepAndStatus={stepAndStatus}
                />
              </Col>
            </Row>
          </Card.Grid>

          {/* Function Component */}
          <Card.Grid style={{ width: "100%", height: "100%" }}>
            <Row
              justify="start"
              style={{ width: "100%", height: "100%" }}
            >
              <Col span={2} style={customColStyle}>
                <ClearAllIcon style={{ fontSize: 24 }} />
              </Col>
              <Col span={8} style={customColStyle}>
                <Text strong style={customTextStyle}>
                  Function Component
                </Text>
              </Col>
              <Col
                flex="auto"
                style={{ display: 'flex', flexDirection: 'row', justifyContent: 'flex-end' }}
              >
                <LoadingButton
                  variant="outlined"
                  loading={setupComponentLoading}
                  onClick={() => { handleSetUpComponent() }}>
                  SetUp Core Component
                </LoadingButton>
              </Col>
            </Row>
            <Row style={{ display: "flex", justifyContent: "space-evenly" }}>
              <FireflyComponentCard ChaincodeStatus={envInfo.fireflyStatus !== "NO"} ClusterStatus={envInfo.fireflyStatus === "STARTED"} />
              <OracleComponentCard ChaincodeStatus={envInfo.oracleStatus === "CHAINCODEINSTALLED"} />
              <DMNComponentCard ChaincodeStatus={envInfo.dmnStatus === "CHAINCODEINSTALLED"} />
            </Row>
          </Card.Grid>

          {/* Creation Time */}
          <Card.Grid style={{ width: "100%", height: "100%" }}>
            <Row style={{ width: "100%", height: "100%" }}>
              <Col span={2} style={customColStyle}>
                <CalendarMonthIcon style={{ fontSize: 24 }} />
              </Col>
              <Col span={4} style={customColStyle}>
                <Text strong style={customTextStyle}>
                  Creation Date
                </Text>
              </Col>
              <Col span={8} style={{ ...customTextStyle, marginLeft: "10px" }}>
                <Text style={customTextStyle}>
                  {envInfo.createdAt}
                </Text>
              </Col>
            </Row>
          </Card.Grid>

          {/* Memberships */}
          <Card.Grid
            style={{ width: "100%", height: "100%", cursor: "pointer" }}
          >
            <Row justify="space-between" style={{ width: "100%", height: "100%" }}>
              <Col span={2} style={customColStyle}>
                <PeopleIcon style={{ fontSize: 24 }} />
              </Col>
              <Col span={4} style={customColStyle}>
                <Text strong style={customTextStyle}>
                  Memberships
                </Text>
              </Col>
              <Col span={8} style={{ ...customTextStyle, marginLeft: "10px" }}>
                <Text style={customTextStyle}>
                  1
                </Text>
              </Col>
              <Col
                flex="auto"
                style={{
                  display: "flex",
                  justifyContent: "flex-end",
                  alignItems: "center",
                  marginRight: "0px",
                }}
              >
                <KeyboardArrowRightIcon />
              </Col>
            </Row>
          </Card.Grid>

          {/* SSI Expansion */}
          <Card.Grid
            style={{ width: "100%", height: "100%", cursor: "pointer" }}
            onClick={() => setIsSSIModalOpen(true)}
          >
            <Row justify="space-between" style={{ width: "100%", height: "100%" }}>
              <Col span={2} style={customColStyle}>
                <PeopleIcon style={{ fontSize: 24 }} />
              </Col>
              <Col span={6} style={customColStyle}>
                <Text strong style={customTextStyle}>SSI Expansion</Text>
              </Col>
              <Col span={8} style={{ ...customTextStyle, marginLeft: "10px" }}>
                <Text style={customTextStyle}>Configure DIDs</Text>
              </Col>
              <Col
                flex="auto"
                style={{
                  display: "flex",
                  justifyContent: "flex-end",
                  alignItems: "center",
                  marginRight: "0px",
                }}
              >
                <KeyboardArrowRightIcon />
              </Col>
            </Row>
          </Card.Grid>
          {/* SSI Expansion Modal */}
          <Modal
            title="Configure SSI Expansion"
            open={isSSIModalOpen}
            onCancel={() => setIsSSIModalOpen(false)}
            onOk={handleSubmitSSIExpansion}
            okText="Submit"
            destroyOnClose
          >
            <Spin spinning={false}>
              <Form form={ssiForm} layout="vertical">
                {membershipList.map((m) => (
                  <div key={m.id} style={{ marginBottom: 16, borderBottom: "1px solid #eee", paddingBottom: 8 }}>
                    <Text strong>{m.name}</Text>
                    <Form.Item
                      name={`url_${m.id}`}
                      label="Agent URL"
                      rules={[{ required: true, message: "Please input Agent URL" }]}
                    >
                      <Input placeholder="https://..." />
                    </Form.Item>
                    <Form.Item
                      name={`did_${m.id}`}
                      label="Public DID"
                      rules={[{ required: true, message: "Please input Public DID" }]}
                    >
                      <Input placeholder="did:example:..." />
                    </Form.Item>
                  </div>
                ))}
              </Form>
            </Spin>
          </Modal>


          {/* Release Version */}
          <Card.Grid style={{ width: "100%", height: "100%" }}>
            <Row style={{ width: "100%", height: "100%" }}>
              <Col span={2} style={customColStyle}>
                <CalendarTodayIcon style={{ fontSize: 24 }} />
              </Col>
              <Col span={4} style={customColStyle}>
                <Text strong style={customTextStyle}>
                  Release Version
                </Text>
              </Col>
              <Col span={8} style={{ ...customTextStyle, marginLeft: "10px" }}>
                <Text style={customTextStyle}>
                  1.0
                </Text>
              </Col>
              <Col
                flex="auto"
                style={{ textAlign: "right", marginRight: "0px" }}
              >
                <ColorButton
                  size="small"
                  variant="contained"
                  onClick={() => { }}
                >
                  Upgrade
                </ColorButton>
              </Col>
            </Row>
          </Card.Grid>

          {/* Protocol */}
          <Card.Grid style={{ width: "100%", height: "100%" }}>
            <Row style={{ width: "100%", height: "100%" }}>
              <Col span={2} style={customColStyle}>
                <Icon path={mdiUngroup} size={1} />
              </Col>
              <Col span={4} style={customColStyle}>
                <Text strong style={customTextStyle}>
                  Protocol
                </Text>
              </Col>
              <Col span={8} style={{ ...customTextStyle, marginLeft: "10px" }}>
                <Text style={customTextStyle}>Raft</Text>
              </Col>
            </Row>
          </Card.Grid>
        </Card>
      </Col>
      <JoinModal isModalOpen={isJoinModelOpen} setIsModalOpen={setIsJoinModelOpen}
        membershipList={membershipList}
        joinFunc={
          async (membershipSelected) => {
            let requests = []
            membershipSelected.forEach((membership) => {
              requests.push(JoinEnv(currentEnvId, membership))
            }
            )
            try {
              await Promise.all(requests)
              message.success("Join Success")
              setSync()
              if (setupCallBackRef.current !== null) {
                setupCallBackRef.current()
              }

            } catch (e) {
              message.error("Join Failed")
            }
          }} />
    </>
  );
};

export default Overview;
