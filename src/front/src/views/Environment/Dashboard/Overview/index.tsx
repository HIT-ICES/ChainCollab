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
  Space,
  Tag,
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
  InitEthEnv,
  StartEthEnv,
  JoinEthEnv,
  ActivateEthEnv,
  InitFireflyForEthEnv,
  StartFireflyForEthEnv,
  InstallIdentityContract,
  getIdentityContractDetail,
  redeployIdentityContract
} from "@/api/resourceAPI";

import {
  registerInterface,
  registerAPI,
  callFireflyContract
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
  IdentityContractComponentCard,

  JoinModal,
  NaiveEthereumStepBar
} from "./components.tsx";

import {
  DBstatus2stepandstatus
} from './utils'


const Overview: React.FC = () => {
  const navigate = useNavigate();
  const [isJoinModelOpen, setIsJoinModelOpen] = useState(false);
  const [envInfo, setSync] = useEnvInfo()
  const currentOrgId = useAppSelector(state => state.org.currentOrgId)
  const currentConsortiumId = useAppSelector(state => state.consortium.currentConsortiumId)
  const currentEnvId = useAppSelector(state => state.env.currentEnvId)
  const currentEnvType = useAppSelector(state => state.env.currentEnvType)
  const [membershipList, setSyncMembershipList] = useMembershipListData()
  const stepAndStatus = DBstatus2stepandstatus(envInfo.status)

  const createdAtLabel = (() => {
    if (!envInfo.createdAt) {
      return "";
    }
    const date = new Date(envInfo.createdAt);
    if (Number.isNaN(date.getTime())) {
      return envInfo.createdAt;
    }
    return date.toLocaleString();
  })();

  const membershipCount = Array.isArray(membershipList) ? membershipList.length : 0;

  const setupCallBackRef = useRef(null)

  const [setupFabricNetWorkLoading, setSetupFabricNetWorkLoading] = useState(false)
  const [setUpEthereumNetworkLoading, setSetUpEthereumNetworkLoading] = useState(false)

  const [setupComponentLoading, setSetupComponentLoading] = useState(false)
  const [setupFireflyLoading, setSetupFireflyLoading] = useState(false)
  const [setupOracleLoading, setSetupOracleLoading] = useState(false)
  const [setupDMNLoading, setSetupDMNLoading] = useState(false)
  const [setupIdentityLoading, setSetupIdentityLoading] = useState(false)

  const [detailOpen, setDetailOpen] = useState(false)
  const [detailType, setDetailType] = useState("")
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailPayload, setDetailPayload] = useState(null)
  const [callLoading, setCallLoading] = useState(false)
  const [callResult, setCallResult] = useState<string | null>(null)
  const [callForm] = Form.useForm()
  const [identityAction, setIdentityAction] = useState(null)
  const identityQuickActions = [
    {
      label: "Check Identity Registered",
      method: "isIdentityRegistered",
      mode: "query",
      params: [{ key: "identityAddress", label: "Address", placeholder: "0x..." }],
    },
    {
      label: "Get Identity Org",
      method: "getIdentityOrg",
      mode: "query",
      params: [{ key: "identityAddress", label: "Address", placeholder: "0x..." }],
    },
    {
      label: "Check Org Member",
      method: "isOrgMember",
      mode: "query",
      params: [
        { key: "identityAddress", label: "Address", placeholder: "0x..." },
        { key: "orgName", label: "Org Name", placeholder: "OrgName" },
      ],
    },
    {
      label: "Get Identity Info",
      method: "getIdentityInfo",
      mode: "query",
      params: [{ key: "identityAddress", label: "Address", placeholder: "0x..." }],
    },
    {
      label: "Get Org Members",
      method: "getOrgMembers",
      mode: "query",
      params: [{ key: "orgName", label: "Org Name", placeholder: "OrgName" }],
    },
    {
      label: "Get All Orgs",
      method: "getAllOrganizations",
      mode: "query",
      params: [],
    },
  ]

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

  const handleSetUpEthereumNetwork = async () => {
    // Init
    setSetUpEthereumNetworkLoading(true)
    await InitEthEnv(currentEnvId)
    setSync()

    // Wait for join
    await new Promise((resolve, reject) => {
      setIsJoinModelOpen(true)
      setupCallBackRef.current = resolve
    })
    setSync()

    // Activate the environment (only changes status, no Firefly operations)
    await ActivateEthEnv(currentEnvId)
    setSync()

    // Start the environment (only changes status, no Firefly operations)
    await StartEthEnv(currentEnvId)
    setSync()

    setSetUpEthereumNetworkLoading(false)
  }

  const handleSetUpFabricComponent = async () => {
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

  const handleSetUpEthereumComponent = async () => {
    setSetupComponentLoading(true)
    await InitFireflyForEthEnv(currentEnvId)
    setSync()
    await StartFireflyForEthEnv(currentEnvId)
    setSync()
    setSetupComponentLoading(false)
  }

  const handleSetUpFireflyOnly = async () => {
    try {
      setSetupFireflyLoading(true)
      if (currentEnvType === "Fabric") {
        await InstallFirefly(currentOrgId, currentEnvId)
        setSync()
        await StartFireflyForEnv(currentEnvId)
        setSync()
      } else {
        await InitFireflyForEthEnv(currentEnvId)
        setSync()
        await StartFireflyForEthEnv(currentEnvId)
        setSync()
      }
    } finally {
      setSetupFireflyLoading(false)
    }
  }

  const handleSetUpOracleOnly = async () => {
    try {
      setSetupOracleLoading(true)
      if (currentEnvType !== "Fabric") {
        message.warning("Oracle only supports Fabric environment")
        return
      }
      await InstallOracle(currentOrgId, currentEnvId)
      setSync()
      const oracleFFI = await requestOracleFFI()
      const res = await registerInterface(systemFireflyURL, oracleFFI.ffiContent, "Oracle")
      await new Promise((resolve) => {
        setTimeout(resolve, 5000)
      })
      await registerAPI(systemFireflyURL, "Oracle", "default", "Oracle", res.id)
      setSync()
    } finally {
      setSetupOracleLoading(false)
    }
  }

  const handleSetUpDMNOnly = async () => {
    try {
      setSetupDMNLoading(true)
      if (currentEnvType !== "Fabric") {
        message.warning("DMN only supports Fabric environment")
        return
      }
      await InstallDmnEngine(currentOrgId, currentEnvId)
      setSync()
    } finally {
      setSetupDMNLoading(false)
    }
  }

  const handleSetUpIdentityContractOnly = async () => {
    try {
      setSetupIdentityLoading(true)
      if (currentEnvType !== "Ethereum") {
        message.warning("Identity contract only supports Ethereum environment")
        return
      }
      await InstallIdentityContract(currentEnvId)
      setSync()
    } finally {
      setSetupIdentityLoading(false)
    }
  }

  const openComponentDetail = async (type: string) => {
    if (type === "Firefly") {
      navigate(`/orgs/${currentOrgId}/consortia/${currentConsortiumId}/envs/${currentEnvId}/firefly`)
      return
    }
    setDetailType(type)
    setDetailOpen(true)
    setCallResult(null)
    if (type === "Identity") {
      try {
        setDetailLoading(true)
        const detail = await getIdentityContractDetail(currentEnvId, true)
        setDetailPayload(detail)
      } finally {
        setDetailLoading(false)
      }
    } else {
      setDetailPayload(null)
    }
  }

  const handleIdentityCall = async () => {
    try {
      const values = await callForm.validateFields()
      const apiBase = detailPayload?.deployment?.firefly_api_base
      if (!apiBase) {
        message.error("Firefly API base URL is not available")
        return
      }
      if (!identityAction) {
        message.error("Select a quick action first")
        return
      }
      const missingLabels: string[] = []
      const params = (identityAction.params || []).reduce((acc, param) => {
        if (!param.key) {
          return acc
        }
        const value = values[param.key]
        if (value === undefined || value === null || value === "") {
          missingLabels.push(param.label || param.key)
          return acc
        }
        acc[param.key] = value
        return acc
      }, {})
      if (missingLabels.length > 0) {
        message.error(`Missing required params: ${missingLabels.join(", ")}`)
        return
      }
      setCallLoading(true)
      const res = await callFireflyContract(
        apiBase,
        values.method,
        params,
        values.mode
      )
      setCallResult(JSON.stringify(res, null, 2))
    } catch (err) {
      if (err?.message) {
        message.error(err.message)
      }
    } finally {
      setCallLoading(false)
    }
  }

  const handleRedeployIdentity = async () => {
    if (currentEnvType !== "Ethereum") {
      message.warning("Identity contract only supports Ethereum environment")
      return
    }
    try {
      setCallLoading(true)
      await redeployIdentityContract(currentEnvId)
      message.success("Redeploy triggered. Syncing users in background.")
    } catch (err) {
      message.error("Redeploy failed to start")
    } finally {
      setCallLoading(false)
    }
  }

  const applyIdentityQuickAction = (action) => {
    setIdentityAction(action)
    const paramDefaults = {}
    action.params.forEach((param) => {
      if (!param.key) {
        return
      }
      paramDefaults[param.key] = ""
    })
    callForm.setFieldsValue({
      method: action.method,
      mode: action.mode,
      ...paramDefaults,
    })
  }

  return (
    <>
      <Col span={16}>
        <Card
          title="Environment Overview"
          style={{
            width: "100%",
            background: "linear-gradient(180deg, #ffffff, #f8fbff)",
            borderRadius: 18,
            border: "1px solid #e2e8f0",
            boxShadow: "0 16px 40px rgba(15,23,42,0.12)"
          }}
          headStyle={{ borderBottom: "1px solid #e2e8f0", fontWeight: 600 }}
          bodyStyle={{ padding: "16px 18px 8px" }}
        >
          {/* Naive Network */}
          <Card.Grid style={{ width: "100%", height: "100%" }}>
            <Row
              justify="space-between"
              style={{ width: "100%", height: "100%" }}
            >
              <Col span={2} style={customColStyle}>
                <ClearAllIcon style={{ fontSize: 24, color: "#2563eb" }} />
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
                  variant="contained"
                  color="primary"
                  onClick={() => {
                    if (currentEnvType === "Fabric") {
                      handleSetUpFabricNetwork();
                    } else  {
                      handleSetUpEthereumNetwork();
                    }
                  }}
                  loading={currentEnvType === "Fabric" ? setupFabricNetWorkLoading : setUpEthereumNetworkLoading}
                  disabled={envInfo.status === "STARTED" || envInfo.status === "ACTIVATED"}
                >
                  {currentEnvType === "Fabric" ? "SetUp Fabric Network" : "SetUp Ethereum Network"}
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
                {/* <NaiveFabricStepBar
                  stepAndStatus={stepAndStatus}
                /> */}
                {currentEnvType === "Fabric" ?
                  <NaiveFabricStepBar
                    stepAndStatus={stepAndStatus}
                  />
                  :
                  <NaiveEthereumStepBar
                    stepAndStatus={stepAndStatus}
                  />}
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
                <ClearAllIcon style={{ fontSize: 24, color: "#2563eb" }} />
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
                  onClick={() => {
                    if (currentEnvType === "Fabric") {
                      handleSetUpFabricComponent();
                    } else {
                      handleSetUpEthereumComponent();
                    }
                  }}>
                  SetUp Core Component
                </LoadingButton>
              </Col>
            </Row>
            <Row style={{ display: "flex", justifyContent: "space-evenly" }}>
              <FireflyComponentCard
                ChaincodeStatus={envInfo.fireflyStatus !== "NO"}
                ClusterStatus={envInfo.fireflyStatus === "STARTED"}
                onOpen={() => openComponentDetail("Firefly")}
                onSetup={
                  <LoadingButton
                    size="small"
                    variant="outlined"
                    loading={setupFireflyLoading}
                    onClick={handleSetUpFireflyOnly}
                  >
                    Setup
                  </LoadingButton>
                }
              />
              <OracleComponentCard
                ChaincodeStatus={envInfo.oracleStatus === "CHAINCODEINSTALLED"}
                onOpen={() => openComponentDetail("Oracle")}
                onSetup={
                  <LoadingButton
                    size="small"
                    variant="outlined"
                    loading={setupOracleLoading}
                    onClick={handleSetUpOracleOnly}
                    disabled={currentEnvType !== "Fabric"}
                  >
                    Setup
                  </LoadingButton>
                }
              />
              <DMNComponentCard
                ChaincodeStatus={envInfo.dmnStatus === "CHAINCODEINSTALLED"}
                onOpen={() => openComponentDetail("DMN")}
                onSetup={
                  <LoadingButton
                    size="small"
                    variant="outlined"
                    loading={setupDMNLoading}
                    onClick={handleSetUpDMNOnly}
                    disabled={currentEnvType !== "Fabric"}
                  >
                    Setup
                  </LoadingButton>
                }
              />
              <IdentityContractComponentCard
                ContractStatus={envInfo.identityContractStatus ?? "NO"}
                onOpen={() => openComponentDetail("Identity")}
                onSetup={
                  <LoadingButton
                    size="small"
                    variant="outlined"
                    loading={setupIdentityLoading}
                    onClick={handleSetUpIdentityContractOnly}
                    disabled={currentEnvType !== "Ethereum"}
                  >
                    Setup
                  </LoadingButton>
                }
              />
            </Row>
          </Card.Grid>

          {/* Creation Time */}
          {createdAtLabel ? (
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
                    {createdAtLabel}
                  </Text>
                </Col>
              </Row>
            </Card.Grid>
          ) : null}

          {/* Memberships */}
          {membershipCount > 0 ? (
            <Card.Grid
              style={{ width: "100%", height: "100%", cursor: "pointer" }}
            >
              <Row
                justify="space-between"
                style={{ width: "100%", height: "100%" }}
              >
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
                    {membershipCount}
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
          ) : null}


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
            if (currentEnvType === "Fabric") {
              membershipSelected.forEach((membership) => {
                requests.push(JoinEnv(currentEnvId, membership))
              }
              )
            } else {
              membershipSelected.forEach((membership) => {
                requests.push(JoinEthEnv(currentEnvId, membership))
              }
              )
            }

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
      <Modal
        open={detailOpen}
        title={`${detailType} Detail`}
        onCancel={() => setDetailOpen(false)}
        footer={null}
        destroyOnClose
      >
        {detailType === "Oracle" ? (
          <Space direction="vertical" style={{ width: "100%" }}>
            <Tag color={envInfo.oracleStatus === "CHAINCODEINSTALLED" ? "green" : "red"}>
              Status: {envInfo.oracleStatus || "NO"}
            </Tag>
            <div>Oracle 通过 Firefly 注册的 FFI/API 使用。</div>
          </Space>
        ) : null}
        {detailType === "DMN" ? (
          <Space direction="vertical" style={{ width: "100%" }}>
            <Tag color={envInfo.dmnStatus === "CHAINCODEINSTALLED" ? "green" : "red"}>
              Status: {envInfo.dmnStatus || "NO"}
            </Tag>
            <div>DMN Engine 仅支持 Fabric 环境。</div>
          </Space>
        ) : null}
        {detailType === "Identity" ? (
          <Space direction="vertical" style={{ width: "100%" }}>
            <Tag color={(envInfo.identityContractStatus === "STARTED") ? "green" : "red"}>
              Status: {envInfo.identityContractStatus || "NO"}
            </Tag>
            {detailLoading ? (
              <div>Loading...</div>
            ) : (
              <>
                <div>
                  Firefly Core: {detailPayload?.firefly_core_url || "-"}
                </div>
                <div>
                  Contract Address: {detailPayload?.deployment?.contract_address || "-"}
                </div>
                <div>
                  Firefly API Base: {detailPayload?.deployment?.firefly_api_base || "-"}
                </div>
                <Form form={callForm} layout="vertical">
                  <Form.Item label="Quick Actions">
                    <Space wrap>
                      {identityQuickActions.map((action) => (
                        <AntdButton
                          key={action.method}
                          onClick={() => applyIdentityQuickAction(action)}
                        >
                          {action.label}
                        </AntdButton>
                      ))}
                    </Space>
                  </Form.Item>
                  <Form.Item>
                    <AntdButton danger onClick={handleRedeployIdentity}>
                      Redeploy & Sync All
                    </AntdButton>
                  </Form.Item>
                  <Form.Item
                    label="Method"
                    name="method"
                    rules={[{ required: true, message: "Method is required" }]}
                  >
                    <Input placeholder="registerIdentity / isOrgMember ..." />
                  </Form.Item>
                  {identityAction ? (
                    identityAction.params.map((param, index) => (
                      <Form.Item
                        key={param.key || `${param.label}-${index}`}
                        label={param.label}
                        name={param.key}
                        rules={[{ required: true, message: `${param.label} is required` }]}
                      >
                        <Input placeholder={param.placeholder} />
                      </Form.Item>
                    ))
                  ) : (
                    <Form.Item>
                      <Input disabled placeholder="Select a quick action to auto-fill parameters." />
                    </Form.Item>
                  )}
                  <Form.Item label="Mode" name="mode" initialValue="invoke">
                    <Input placeholder="invoke / query" />
                  </Form.Item>
                  <AntdButton loading={callLoading} onClick={handleIdentityCall}>
                    Call via Firefly API
                  </AntdButton>
                </Form>
                {callResult ? (
                  <pre style={{ marginTop: 12, background: "#f8fafc", padding: 12 }}>
                    {callResult}
                  </pre>
                ) : null}
              </>
            )}
          </Space>
        ) : null}
      </Modal>
    </>
  );
};

export default Overview;
