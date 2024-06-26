import React, { useEffect, useState } from "react";
import { Form, Input, Menu, Modal } from "antd";
const { SubMenu } = Menu;
import { useLocation, useNavigate } from "react-router-dom";
import { DesktopOutlined, TeamOutlined, UserOutlined } from "@ant-design/icons";

// Redux Relate
import { useAppDispatch, useAppSelector } from '@/redux/hooks'
import { selectOrg, activateOrg, deactivateOrg } from '@/redux/slices/orgSlice'
import { selectConsortium, activateConsortium, deactivateConsortium } from "@/redux/slices/consortiumSlice";
import { selectEnv, activateEnv, deactivateEnv } from '@/redux/slices/envSlice'

import { useOrgData, useConsortiaData, useEnvData } from "./hooks";

import { createConsortium, createOrg, createEnvironment } from '@/api/platformAPI'

import {
  consumeConsortiumSelectRequest,
  consumeOrgSelectRequest,
  consumeEnvSelectRequest,
  selectUI
} from '@/redux/slices/UISlice'

const AddConsortiumModal: React.FC<{
  isModalOpen?: boolean,
  setIsModalOpen: React.Dispatch<React.SetStateAction<boolean>>,
  setSync: () => void,
}> = ({ isModalOpen = false, setIsModalOpen, setSync }) => {

  type FieldType = {
    consortiumName?: string;
  };
  const [form] = Form.useForm<FieldType>();
  const dispatch = useAppDispatch();

  const currentOrgId = useAppSelector(selectOrg).currentOrgId;

  const onFinish = async (values: FieldType) => {
    const newConsortium = await createConsortium(currentOrgId, values.consortiumName);
    dispatch(activateConsortium({ currentConsortiumId: newConsortium.id, currentConsortiumName: newConsortium.name }))
    setIsModalOpen(false);
    setSync();
  }

  return (
    <Modal
      title="Add Consortium"
      open={isModalOpen}
      onOk={() => setIsModalOpen(false)}
      onCancel={() => setIsModalOpen(false)}
      destroyOnClose
      okButtonProps={{
        htmlType: "submit",
        form: "basic",
      }}
    >
      <Form
        form={form}
        name="basic"
        labelCol={{ span: 8 }}
        wrapperCol={{ span: 16 }}
        style={{ maxWidth: 600 }}
        onFinish={onFinish}
        autoComplete="off"
        preserve={false} // 在Modal关闭后，销毁Field
      >
        <Form.Item<FieldType>
          label="Consortium Name"
          name="consortiumName"
          rules={[
            { required: true, message: "Please input consortium name!" },
          ]}
        >
          <Input allowClear />
        </Form.Item>
      </Form>
    </Modal>
  )
}

const AddOrgModal: React.FC<{
  isModalOpen?: boolean,
  setIsModalOpen: React.Dispatch<React.SetStateAction<boolean>>,
  setSync: () => void,
}> = ({ isModalOpen = false, setIsModalOpen, setSync }) => {
  type FieldType = {
    orgName?: string;
  };
  const [form] = Form.useForm<FieldType>();
  const dispatch = useAppDispatch();


  const onFinish = async (values: FieldType) => {
    const Org = await createOrg(values.orgName);
    dispatch(activateOrg({ currentOrgId: Org.id, currentOrgName: Org.name }))
    setIsModalOpen(false);
    setSync();
  };

  return (
    <Modal
      title="Add Organization"
      open={isModalOpen}
      onOk={() => setIsModalOpen(false)}
      onCancel={() => setIsModalOpen(false)}
      destroyOnClose
      okButtonProps={{
        htmlType: "submit",
        form: "basic",
      }}
    >
      <Form
        form={form}
        name="basic"
        labelCol={{ span: 8 }}
        wrapperCol={{ span: 16 }}
        style={{ maxWidth: 600 }}
        onFinish={onFinish}
        autoComplete="off"
        preserve={false} // 在Modal关闭后，销毁Field
      >
        <Form.Item<FieldType>
          label="Organization Name"
          name="orgName"
          rules={[
            { required: true, message: "Please input organization name!" },
          ]}
        >
          <Input allowClear />
        </Form.Item>
      </Form>
    </Modal>
  );
};

const AddEnvModal: React.FC<{
  isModalOpen?: boolean,
  setIsModalOpen: React.Dispatch<React.SetStateAction<boolean>>,
  setSync: () => void,
}> = ({ isModalOpen = false, setIsModalOpen, setSync }) => {
  type FieldType = {
    envName?: string;
  };
  const [form] = Form.useForm<FieldType>();
  const dispatch = useAppDispatch();
  const currentConsortiumId = useAppSelector(selectConsortium).currentConsortiumId;


  const onFinish = async (values: FieldType) => {
    const Env = await createEnvironment(currentConsortiumId, values.envName);
    dispatch(activateEnv({ currentEnvId: Env.id, currentEnvName: Env.name }))
    setIsModalOpen(false);
    setSync();
  }

  return (
    <Modal
      title="Add Environment"
      open={isModalOpen}
      onOk={() => setIsModalOpen(false)}
      onCancel={() => setIsModalOpen(false)}
      destroyOnClose
      okButtonProps={{
        htmlType: "submit",
        form: "basic",
      }}
    >
      <Form
        form={form}
        name="basic"
        labelCol={{ span: 8 }}
        wrapperCol={{ span: 16 }}
        style={{ maxWidth: 600 }}
        onFinish={onFinish}
        autoComplete="off"
        preserve={false}
      >
        <Form.Item<FieldType>
          label="Environment Name"
          name="envName"
          rules={[
            { required: true, message: "Please input environment name!" },
          ]}
        >
          <Input allowClear />
        </Form.Item>
      </Form>
    </Modal>
  );
}


const MainMenu: React.FC = () => {
  const navigateTo = useNavigate();
  const currentRoute = useLocation();
  const dispatch = useAppDispatch();

  const currentOrgId = useAppSelector(selectOrg).currentOrgId;
  const currentConsortiumId = useAppSelector(selectConsortium).currentConsortiumId;
  const currentEnvId = useAppSelector(selectEnv).currentEnvId;
  const currentOrgName = useAppSelector(selectOrg).currentOrgName;
  const currentConsortiumName = useAppSelector(selectConsortium).currentConsortiumName;
  const currentEnvName = useAppSelector(selectEnv).currentEnvName;

  const [orgList, syncOrgList] = useOrgData();
  const [consortiaList, syncConsortiaList] = useConsortiaData(currentOrgId);
  const [envList, envListReady, syncEnvList] = useEnvData(currentConsortiumId);

  const syncAll = () => {
    syncOrgList();
    syncConsortiaList();
    syncEnvList();
  }


  useEffect(() => {
    const task = setInterval(() => {
      syncOrgList();
      syncConsortiaList();
      syncEnvList();
    }, 5000);
    return () => {
      clearInterval(task);
    }
  }
    , []);

  const [openKeys, setOpenKeys] = useState<string[]>([]);
  const onOpenChange = (keys: string[]) => {
    setOpenKeys(keys);
  };

  const current = currentRoute.pathname;

  const menuClick = (e: any) => {
    const key = e.key;
    if (key[0] === "/") {
      navigateTo(key);
      return;
    }
  };

  const [isAddConsortiumModalOpen, setIsAddConsortiumModalOpen] = useState(false);
  const [isAddOrgModalOpen, setIsAddOrgModalOpen] = useState(false);
  const [isAddEnvModalOpen, setIsAddEnvModalOpen] = useState(false);

  const {
    orgSelectOpenRequest
    , consortiumSelectOpenRequest
    , envSelectOpenRequest
  } = useAppSelector(selectUI);
  useEffect(() => {
    if (orgSelectOpenRequest) {
      setIsAddOrgModalOpen(true);
      dispatch(consumeOrgSelectRequest());
    }
    if (consortiumSelectOpenRequest) {
      setIsAddConsortiumModalOpen(true);
      dispatch(consumeConsortiumSelectRequest());
    }
    if (envSelectOpenRequest) {
      setIsAddEnvModalOpen(true);
      dispatch(consumeEnvSelectRequest());
    }
  }, [orgSelectOpenRequest, consortiumSelectOpenRequest, envSelectOpenRequest])

  console.log(envList)


  const orgItem = (
    <SubMenu key="/organization" icon={<TeamOutlined />} title="Organization">
      <SubMenu key={"ActivateOrg"} title={currentOrgName !== "" ? currentOrgName : "Select An Organization"}>
        {orgList.map((item) => (
          <Menu.Item key={item.id} onClick={
            () => dispatch(activateOrg({ currentOrgId: item.id, currentOrgName: item.name }))
          } >{item.name}</Menu.Item>
        ))}
        <Menu.Divider
          style={{ backgroundColor: "rgba(255, 255, 255, 0.2)" }} // 使分割线在dark主题下可见
        />
        <Menu.Item key="addOrganization" onClick={() => setIsAddOrgModalOpen(true)}>
          Add Organization
        </Menu.Item>
      </SubMenu>
      <Menu.Item key={`/orgs/${currentOrgId ? currentOrgId : 'none'}/dashboard`}>Dashboard</Menu.Item>
      {currentOrgId === '' ? null : (
        <>
          <Menu.Item key={`/orgs/${currentOrgId}/usersmanage`}>Manage Users</Menu.Item>
          <Menu.Item key={`/orgs/${currentOrgId}/settings`}>Settings</Menu.Item>
        </>)}
    </SubMenu>
  );

  const envItem = (
    <SubMenu key="/environment" icon={<UserOutlined />} title="Environment">
      <SubMenu key={"ActivateEnv"} title={currentEnvName !== "" ? currentEnvName : "Select One Env"}>
        {
          envListReady ?
            envList.map((item) => (
              <Menu.Item key={item.id} onClick={
                () => dispatch(activateEnv({ currentEnvId: item.id, currentEnvName: item.name }))
              } >{item.name}</Menu.Item>
            )) : null
        }
        <Menu.Divider
          style={{ backgroundColor: "rgba(255, 255, 255, 0.2)" }} // 使分割线在dark主题下可见
        />
        <Menu.Item key="addEnvironment" onClick={() => setIsAddEnvModalOpen(true)}>
          Add Environment
        </Menu.Item>
      </SubMenu>
      {currentEnvId === '' ? null : (
        <>
          {/* <Menu.Item
            key={`/orgs/${currentOrgId}/consortia/${currentConsortiumId}/envs/${currentEnvId}/app`}
          >
            App
          </Menu.Item> */}
          <Menu.Item
            key={`/orgs/${currentOrgId}/consortia/${currentConsortiumId}/envs/${currentEnvId}/envdashboard`}
          >
            EnvDashboard
          </Menu.Item>
          <SubMenu
            key={`/orgs/${currentOrgId}/consortia/${currentConsortiumId}/envs/${currentEnvId}/fabric`}
            title="Fabric"
          >
            <Menu.Item
              key={`/orgs/${currentOrgId}/consortia/${currentConsortiumId}/envs/${currentEnvId}/fabric/chaincode`}
            >
              Chaincode
            </Menu.Item>
            <Menu.Item
              key={`/orgs/${currentOrgId}/consortia/${currentConsortiumId}/envs/${currentEnvId}/fabric/channel`}
            >
              Channel
            </Menu.Item>
            <Menu.Item
              key={`/orgs/${currentOrgId}/consortia/${currentConsortiumId}/envs/${currentEnvId}/fabric/node`}
            >
              Node
            </Menu.Item>
          </SubMenu>
          <Menu.Item
            key={`/orgs/${currentOrgId}/consortia/${currentConsortiumId}/envs/${currentEnvId}/firefly`}
          >
            Firefly
          </Menu.Item>
        </>)}
    </SubMenu>

  );

  const consortiumItem = (
    <SubMenu key="/network" icon={<DesktopOutlined />} title="Consortium">
      <SubMenu key={'ActivateConsortium'} title={currentConsortiumName !== "" ? currentConsortiumName : "Select A Consortium"}>
        {consortiaList.map((item) => (
          <Menu.Item key={item.id} onClick={
            () => dispatch(activateConsortium({ currentConsortiumId: item.id, currentConsortiumName: item.name }))
          } >{item.name}</Menu.Item>
        ))}
        <Menu.Divider
          style={{ backgroundColor: "rgba(255, 255, 255, 0.2)" }} // 使分割线在dark主题下可见
        />
        <Menu.Item key="addConsortium" onClick={() => setIsAddConsortiumModalOpen(true)}>
          Add Consortium
        </Menu.Item>
      </SubMenu>
      {currentConsortiumId === '' ? null : (
        <>
          <Menu.Item key={`/orgs/${currentOrgId}/consortia/${currentConsortiumId}/dashboard`}>
            Dashboard
          </Menu.Item>
          <Menu.Item key={`/orgs/${currentOrgId}/consortia/${currentConsortiumId}/memberships`}>
            Memberships
          </Menu.Item>
          <Menu.Item key={`/orgs/${currentOrgId}/consortia/${currentConsortiumId}/settings`}>
            Settings
          </Menu.Item>
        </>)}
    </SubMenu>
  );

  const bpmnItem = (
    <SubMenu key="/bpmn" icon={<DesktopOutlined />} title="BPMN">
      <Menu.Item key="/bpmn/drawing">Drawing</Menu.Item>
      <Menu.Item key="/bpmn/translation">Deploy</Menu.Item>
      <Menu.Item key="/bpmn/chor-js">Chor-js</Menu.Item>
    </SubMenu>
  );

  return (
    <>
      <Menu
        theme="dark"
        defaultSelectedKeys={[currentRoute.pathname]}
        selectedKeys={[current]}
        mode="inline"
        onClick={menuClick}
        openKeys={openKeys}
        onOpenChange={onOpenChange}
      >
        {orgItem}
        {consortiumItem}
        {envItem}
        {bpmnItem}
      </Menu>

      <AddConsortiumModal
        isModalOpen={isAddConsortiumModalOpen}
        setIsModalOpen={setIsAddConsortiumModalOpen}
        setSync={syncAll}
      />
      <AddOrgModal
        isModalOpen={isAddOrgModalOpen}
        setIsModalOpen={setIsAddOrgModalOpen}
        setSync={syncAll}
      />
      <AddEnvModal
        isModalOpen={isAddEnvModalOpen}
        setIsModalOpen={setIsAddEnvModalOpen}
        setSync={syncAll}
      />
    </>
  );
};

export default MainMenu;
