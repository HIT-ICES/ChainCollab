import React, { useEffect, useState } from "react";
import { Menu } from "antd";
const { SubMenu } = Menu;
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { DesktopOutlined, TeamOutlined, UserOutlined } from "@ant-design/icons";

// Redux Relate
import { useAppDispatch, useAppSelector } from '@/redux/hooks'
import { selectOrg, activateOrg, deactivateOrg } from '@/redux/slices/orgSlice'
import { selectConsortium, activateConsortium, deactivateConsortium } from "@/redux/slices/consortiumSlice";
import { selectEnv, activateEnv, deactivateEnv } from '@/redux/slices/envSlice'

import { useOrgData, useConsortiaData, useEnvData } from "./hooks";

import {
  consumeConsortiumSelectRequest,
  consumeOrgSelectRequest,
  consumeEnvSelectRequest,
  selectUI
} from '@/redux/slices/UISlice'

const MainMenu: React.FC = () => {
  const navigateTo = useNavigate();
  const currentRoute = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const dispatch = useAppDispatch();

  const currentOrgId = useAppSelector(selectOrg).currentOrgId;
  const currentConsortiumId = useAppSelector(selectConsortium).currentConsortiumId;
  const currentEnvId = useAppSelector(selectEnv).currentEnvId;
  const currentOrgName = useAppSelector(selectOrg).currentOrgName;
  const currentConsortiumName = useAppSelector(selectConsortium).currentConsortiumName;
  const currentEnvName = useAppSelector(selectEnv).currentEnvName;
  const currentEnvType = useAppSelector(selectEnv).currentEnvType;

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
      if (!localStorage.getItem("token")) {
        return;
      }
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

  const {
    orgSelectOpenRequest
    , consortiumSelectOpenRequest
    , envSelectOpenRequest
  } = useAppSelector(selectUI);
  useEffect(() => {
    if (orgSelectOpenRequest) {
      navigateTo("/orgs/create");
      dispatch(consumeOrgSelectRequest());
    }
    if (consortiumSelectOpenRequest) {
      navigateTo(`/orgs/${currentOrgId || 'none'}/consortia/create`);
      dispatch(consumeConsortiumSelectRequest());
    }
    if (envSelectOpenRequest) {
      navigateTo(`/orgs/${currentOrgId || 'none'}/consortia/${currentConsortiumId || 'none'}/envs/create`);
      dispatch(consumeEnvSelectRequest());
    }
  }, [orgSelectOpenRequest, consortiumSelectOpenRequest, envSelectOpenRequest, navigateTo, currentOrgId, currentConsortiumId, dispatch])

  // 将 URL 中的查询参数回填到 Redux
  useEffect(() => {
    const queryOrgId = searchParams.get("orgId");
    if (queryOrgId && queryOrgId !== currentOrgId) {
      const matchedOrg = orgList.find((item) => item.id === queryOrgId);
      if (matchedOrg) {
        dispatch(activateOrg({ currentOrgId: matchedOrg.id, currentOrgName: matchedOrg.name }));
      }
    }
  }, [searchParams, orgList, currentOrgId, dispatch]);

  useEffect(() => {
    const queryConsortiumId = searchParams.get("consortiumId");
    if (queryConsortiumId && queryConsortiumId !== currentConsortiumId) {
      const matchedConsortium = consortiaList.find((item) => item.id === queryConsortiumId);
      if (matchedConsortium) {
        dispatch(activateConsortium({
          currentConsortiumId: matchedConsortium.id,
          currentConsortiumName: matchedConsortium.name
        }));
      }
    }
  }, [searchParams, consortiaList, currentConsortiumId, dispatch]);

  useEffect(() => {
    if (!envListReady) return;
    const queryEnvId = searchParams.get("envId");
    if (queryEnvId && queryEnvId !== currentEnvId) {
      const matchedEnv = envList.find((item) => item.id === queryEnvId);
      if (matchedEnv) {
        dispatch(activateEnv({
          currentEnvId: matchedEnv.id,
          currentEnvName: matchedEnv.name,
          currentEnvType: matchedEnv.type
        }));
      }
    }
  }, [searchParams, envList, envListReady, currentEnvId, dispatch]);

  // 将 Redux 选择写回 URL
  useEffect(() => {
    const nextSearch = new URLSearchParams(searchParams);
    let changed = false;
    const syncParam = (key: string, value: string) => {
      const existing = nextSearch.get(key);
      if (value && existing !== value) {
        nextSearch.set(key, value);
        changed = true;
      }
      if (!value && existing) {
        nextSearch.delete(key);
        changed = true;
      }
    };
    syncParam("orgId", currentOrgId);
    syncParam("consortiumId", currentConsortiumId);
    syncParam("envId", currentEnvId);
    if (changed) {
      setSearchParams(nextSearch, { replace: true });
    }
  }, [currentOrgId, currentConsortiumId, currentEnvId, searchParams, setSearchParams]);


  const orgItem = (
    <SubMenu key="/organization" icon={<TeamOutlined />} title="Organization">
      <SubMenu key={"ActivateOrg"} title={currentOrgName !== "" ? currentOrgName : "Select An Organization"}>
        {orgList.map((item) => (
          <Menu.Item key={item.id} onClick={
            () => {
              dispatch(activateOrg({ currentOrgId: item.id, currentOrgName: item.name }));
              navigateTo(`/orgs/${item.id}/dashboard`);
            }
          } >{item.name}</Menu.Item>
        ))}
        <Menu.Divider
          style={{ backgroundColor: "rgba(15, 23, 42, 0.08)" }}
        />
        <Menu.Item key="addOrganization" onClick={() => navigateTo("/orgs/create")}>
          Add Organization
        </Menu.Item>
      </SubMenu>
      {currentOrgId && (
        <>
          <Menu.Divider style={{ backgroundColor: "rgba(15, 23, 42, 0.08)" }} />
          <Menu.ItemGroup key="OrgActions">
            <Menu.Item key={`/orgs/${currentOrgId}/dashboard`}>Dashboard</Menu.Item>
            <Menu.Item key={`/orgs/${currentOrgId}/usersmanage`}>Manage Users</Menu.Item>
            <Menu.Item key={`/orgs/${currentOrgId}/settings`}>Settings</Menu.Item>
          </Menu.ItemGroup>
        </>
      )}
    </SubMenu>
  );

  const envItem = (
    <SubMenu key="/environment" icon={<UserOutlined />} title="Environment">
      <SubMenu key={"ActivateEnv"} title={currentEnvName !== "" ? currentEnvName : "Select One Env"}>
        {
          envListReady ?
            envList.map((item) => (
              <Menu.Item key={item.id} onClick={
                () => {
                  dispatch(activateEnv({ currentEnvId: item.id, currentEnvName: item.name, currentEnvType: item.type }));
                  navigateTo(`/orgs/${currentOrgId || 'none'}/consortia/${currentConsortiumId || 'none'}/envs/${item.id}/envdashboard`);
                }
              } >{item.name}</Menu.Item>
            )) : null
        }
        <Menu.Divider
          style={{ backgroundColor: "rgba(15, 23, 42, 0.08)" }}
        />
        <Menu.Item key="addEnvironment" onClick={() => navigateTo(`/orgs/${currentOrgId || 'none'}/consortia/${currentConsortiumId || 'none'}/envs/create`)}>
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
          {currentEnvType === 'Fabric' && (<><Menu.Item
            key={`/orgs/${currentOrgId}/consortia/${currentConsortiumId}/envs/${currentEnvId}/envdashboard`}
          >
            EnvDashboard
          </Menu.Item><SubMenu
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
            </SubMenu><Menu.Item
              key={`/orgs/${currentOrgId}/consortia/${currentConsortiumId}/envs/${currentEnvId}/firefly`}
            >
              Firefly
            </Menu.Item></>)}
            {currentEnvType === 'Ethereum' && (<><Menu.Item
        key={`/orgs/${currentOrgId}/consortia/${currentConsortiumId}/envs/${currentEnvId}/envdashboard`}
      >
        EnvDashboard
      </Menu.Item><SubMenu
        key={`/orgs/${currentOrgId}/consortia/${currentConsortiumId}/envs/${currentEnvId}/ethereum`}
        title="Ethereum"
      >
          <Menu.Item //改动存疑
            key={`/orgs/${currentOrgId}/consortia/${currentConsortiumId}/envs/${currentEnvId}/ethereum/smartcontract`}
          >
            Smart Contract
          </Menu.Item>
          <Menu.Item
            key={`/orgs/${currentOrgId}/consortia/${currentConsortiumId}/envs/${currentEnvId}/ethereum/node`}
          >
            Node
          </Menu.Item>
          <Menu.Item
            key={`/orgs/${currentOrgId}/consortia/${currentConsortiumId}/envs/${currentEnvId}/ethereum/chainlink-jobs`}
          >
            Chainlink Jobs
          </Menu.Item>
        </SubMenu></>
      )}
        </>)}
      
    </SubMenu>

  );

  const consortiumItem = (
    <SubMenu key="/network" icon={<DesktopOutlined />} title="Consortium">
      <SubMenu key={'ActivateConsortium'} title={currentConsortiumName !== "" ? currentConsortiumName : "Select A Consortium"}>
        {consortiaList.map((item) => (
          <Menu.Item key={item.id} onClick={
            () => {
              dispatch(activateConsortium({ currentConsortiumId: item.id, currentConsortiumName: item.name }));
              navigateTo(`/orgs/${currentOrgId || 'none'}/consortia/${item.id}/dashboard`);
            }
          } >{item.name}</Menu.Item>
        ))}
        <Menu.Divider
          style={{ backgroundColor: "rgba(15, 23, 42, 0.08)" }}
        />
        <Menu.Item key="addConsortium" onClick={() => navigateTo(`/orgs/${currentOrgId || 'none'}/consortia/create`)}>
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
      <Menu.Item key="/bpmn/drawing">DrawingBpmn</Menu.Item>
      <Menu.Item key="/bpmn/dmn">Dmns</Menu.Item>
      <Menu.Item key="/bpmn/translation">Deploy</Menu.Item>
      <Menu.Item key="/bpmn/execution">Execution</Menu.Item>
      <Menu.Item key="/bpmn/execution?mode=mock">Execution(Mock)</Menu.Item>
    </SubMenu>
  );

  return (
    <>
      <Menu
        theme="light"
        defaultSelectedKeys={[currentRoute.pathname]}
        selectedKeys={[current]}
        mode="inline"
        onClick={menuClick}
        openKeys={openKeys}
        onOpenChange={onOpenChange}
        className="portal-menu-list"
      >
        {orgItem}
        {consortiumItem}
        {envItem}
        {bpmnItem}
      </Menu>

    </>
  );
};

export default MainMenu;
