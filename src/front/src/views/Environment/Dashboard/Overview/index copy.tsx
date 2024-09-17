import React, { useEffect, useState } from "react";
import {
  Card,
  Row,
  Col,
  Typography,
  Steps,
  Modal,
  Button as AntdButton,
  Form,
  Select,
  message,
} from "antd";
import ClearAllIcon from "@mui/icons-material/ClearAll";
import CalendarMonthIcon from "@mui/icons-material/CalendarMonth";
import PeopleIcon from "@mui/icons-material/People";
import CalendarTodayIcon from "@mui/icons-material/CalendarToday";
import Icon from "@mdi/react";
import { styled } from "@mui/material/styles";
import { mdiUngroup } from "@mdi/js";
import Button, { ButtonProps } from "@mui/material/Button";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import { purple } from "@mui/material/colors";
import { useNavigate } from "react-router-dom";
const { Text } = Typography;
import {
  InitEnv,
  JoinEnv,
  StartEnv,
  ActivateEnv,
  StartFireflyForEnv
} from "@/api/resourceAPI";

import { useEnvInfo, useMembershipListData } from './hooks'
import { useAppSelector } from '@/redux/hooks'
import { set } from "lodash";


const ColorButton = styled(Button)<ButtonProps>(({ theme }) => ({
  color: theme.palette.getContrastText(purple[500]),
  backgroundColor: purple[500],
  "&:hover": {
    backgroundColor: purple[700],
  },
}));

const customColStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  marginLeft: "0px",
};

//
const customTextStyle: React.CSSProperties = {
  fontSize: "14px",
  display: "flex",
  alignItems: "center",
};

const JoinModel = ({
  isModalOpen,
  setIsModalOpen
}) => {
  const [membershipList, setSync] = useMembershipListData()
  const currentEnvId = useAppSelector(state => state.env.currentEnvId)
  const onFinish = async (values: any) => {
    try {
      const response = await JoinEnv(currentEnvId, values.membership);
      message.success("Join Success", 2.5)
    } catch (err) {
      console.error("Error:", err);
    }
    setSync()
  }

  return (
    <Modal
      open={isModalOpen}
      onCancel={() => setIsModalOpen(false)}
      title="Activate Membership"
      footer={[
        <AntdButton
          key="submit"
          type="primary"
          form="membershipForm"
          htmlType="submit"
        >
          {"提交"}
        </AntdButton>,
      ]}
    >
      <Form id="membershipForm" onFinish={onFinish}>
        <Form.Item
          name="membership"
          rules={[{ required: true, message: "Please select a membership!" }]}
        >
          <Select placeholder="Select a membership">
            {membershipList.map((membership) => {
              return (
                <Select.Option value={membership.id}>
                  {membership.name}
                </Select.Option>
              );
            })}
          </Select>
        </Form.Item>
      </Form>
    </Modal>
  );
}



const items: Array<{
  title: string;
}> = [
    {
      title: "Created",
    },
    {
      title: "Initialized",
    },
    {
      title: "Started",
    },
    {
      title: "Active",
    },
    {
      title: "Firefly",
    }
  ];


const Overview: React.FC = () => {
  const navigate = useNavigate();
  const [form] = Form.useForm(); // 获取 form 实例
  const [isJoinModelOpen, setIsJoinModelOpen] = useState(false);
  const [envInfo, setSync] = useEnvInfo()
  const [buttonEnable, setButtonEnable] = useState(true);
  const [subButtonEnable, setSubButtonEnable] = useState(true);
  const currentOrgId = useAppSelector(state => state.org.currentOrgId)
  const currentConsortiumId = useAppSelector(state => state.consortium.currentConsortiumId)
  const currentEnvId = useAppSelector(state => state.env.currentEnvId)
  const [membershipList, setSyncMembershipList] = useMembershipListData()
  // number?


  const status = (() => {
    if (envInfo.status === "CREATED") {
      return 0
    } else if (envInfo.status === "INITIALIZED") {
      return 1
    } else if (envInfo.status === "STARTED") {
      return 2
    } else if (envInfo.status === "ACTIVATED") {
      return 3
    } else if (envInfo.status === "FIREFLY") {
      return 4
    }
  })()


  const subButton = () => {

    const buttonName = (() => {
      if (envInfo.status === "INITIALIZED")
        return "Join"
      else if (envInfo.status === "ACTIVATED")
        return "Install"
    })()

    const buttonFunction = (() => {
      if (envInfo.status === "INITIALIZED")
        return () => {
          setIsJoinModelOpen(true)
        }
      else if (envInfo.status === "ACTIVATED")
        return () => {
          navigate("/orgs/" + currentOrgId + "/consortia/" + currentConsortiumId + "/envs/" + currentEnvId + "/fabric/chaincode")
        }
    })()

    return (<Button
      variant="outlined"
      disabled={subButtonEnable === false}
      onClick={buttonFunction}
    >{buttonName}</Button>)

  }

  const mainButton = () => {
    const buttonName = (() => {
      if (envInfo.status === "CREATED") {
        return "Init"
      } else if (envInfo.status === "INITIALIZED") {
        return "Start"
      } else if (envInfo.status === "STARTED") {
        return "Activate"
      } else if (envInfo.status === "ACTIVATED") {
        return "START FIREFLY"
      }
      return ""
    })()

    const buttonFunction = (() => {
      if (envInfo.status === "CREATED") {
        return async () => {
          setButtonEnable(false)
          const response = await InitEnv(envInfo.id);
          setTimeout(() => {
            setButtonEnable(true)
          }
            , 3000)
          setSync()
        }
      } else if (envInfo.status === "INITIALIZED") {
        return async () => {
          setButtonEnable(false)
          const response = await StartEnv(envInfo.id);
          setTimeout(() => {
            setButtonEnable(true)
          }
            , 3000)
          setSync()
        }
      } else if (envInfo.status === "STARTED") {
        return async () => {
          setButtonEnable(false)
          const response = await ActivateEnv(envInfo.id, currentOrgId);
          setTimeout(() => {
            setButtonEnable(true)
          }
            , 3000)
          setSync()
        }
      } else if (envInfo.status === "ACTIVATED") {
        return async () => {
          setButtonEnable(false)
          const response = await StartFireflyForEnv(envInfo.id);
          setTimeout(() => {
            setButtonEnable(true)
          }
            , 3000)
          setSync()
        }
      }
    })()

    return (<Button
      variant="outlined"
      disabled={buttonEnable === false}
      onClick={buttonFunction}
    >{buttonName}</Button>)
  }

  const allInOneFunction = async () => {
    // Init, join all membership, start, activate
    await InitEnv(envInfo.id)
    // get all memberships

    for (let i = 0; i < membershipList.length; i++) {
      await JoinEnv(envInfo.id, membershipList[i].id)
    }
    await StartEnv(envInfo.id)
    await ActivateEnv(envInfo.id, currentOrgId)
    setSync()
  }

  return (
    <>
      <Col span={12}>
        <Card title="Overview" style={{ width: "100%" }}>
          <Card.Grid style={{ width: "100%", height: "100%" }}>
            <Row
              justify="space-between"
              style={{ width: "100%", height: "100%" }}
            >
              <Col span={2} style={customColStyle}>
                <ClearAllIcon style={{ fontSize: 24 }} />
              </Col>
              <Col span={2} style={customColStyle}>
                <Text strong style={customTextStyle}>
                  Status
                </Text>
              </Col>
              <Col
                flex="auto"
                style={{ display: 'flex', flexDirection: 'row', justifyContent: 'flex-end' }}
              >
                {(status !== 1 && status !== 3) ? null : (
                  subButton()
                )}
                <div style={{ width: '10px' }} />
                {status === 4 ? null : (
                  mainButton()
                )}
                <div style={{ width: '10px' }} />
                <Button
                  variant="outlined"
                  onClick={allInOneFunction}
                >
                  All In One
                </Button>
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
                <Steps
                  current={status}
                  items={items}
                />
              </Col>
            </Row>
          </Card.Grid>


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
          {/* Membership */}
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
      <JoinModel isModalOpen={isJoinModelOpen} setIsModalOpen={setIsJoinModelOpen} />
    </>
  );
};

export default Overview;
