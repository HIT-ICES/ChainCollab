import React, { useEffect, useState } from "react";
import { Menu } from "antd";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button as MUIButton,
  Stack,
  Typography,
  FormControl,
  InputLabel,
  Select as MUISelect,
  MenuItem as MUIMenuItem,
  SelectChangeEvent
} from "@mui/material";
const { SubMenu } = Menu;
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
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

  const [consortiumName, setConsortiumName] = useState("Consortium");
  const [loading, setLoading] = useState(false);
  const dispatch = useAppDispatch();

  const currentOrgId = useAppSelector(selectOrg).currentOrgId;

  const handleClose = () => {
    if (loading) return;
    setIsModalOpen(false);
    setConsortiumName("Consortium");
  };

  const handleConfirm = async () => {
    if (!consortiumName.trim()) return;
    try {
      setLoading(true);
      const newConsortium = await createConsortium(currentOrgId, consortiumName.trim());
      dispatch(activateConsortium({ currentConsortiumId: newConsortium.id, currentConsortiumName: newConsortium.name }));
      setConsortiumName("Consortium");
      setIsModalOpen(false);
      setSync();
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog
      open={isModalOpen}
      onClose={handleClose}
      fullWidth
      maxWidth="xs"
    >
      <DialogTitle sx={{ fontWeight: 600 }}>Add Consortium</DialogTitle>
      <DialogContent dividers>
        <Stack spacing={2}>
          <TextField
            label="Consortium Name"
            value={consortiumName}
            onChange={(e) => setConsortiumName(e.target.value)}
            autoFocus
            fullWidth
          />
          <Typography variant="body2" color="text.secondary">
            创建一个新的联盟以管理多组织协作环境。
          </Typography>
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, py: 2 }}>
        <MUIButton onClick={handleClose}>Cancel</MUIButton>
        <MUIButton
          variant="contained"
          onClick={handleConfirm}
          disabled={!consortiumName.trim() || loading}
        >
          {loading ? "Creating..." : "Create"}
        </MUIButton>
      </DialogActions>
    </Dialog>
  )
}

const AddOrgModal: React.FC<{
  isModalOpen?: boolean,
  setIsModalOpen: React.Dispatch<React.SetStateAction<boolean>>,
  setSync: () => void,
}> = ({ isModalOpen = false, setIsModalOpen, setSync }) => {
  const [orgName, setOrgName] = useState("Organization");
  const [loading, setLoading] = useState(false);
  const dispatch = useAppDispatch();


  const handleClose = () => {
    if (loading) return;
    setIsModalOpen(false);
    setOrgName("Organization");
  };

  const handleConfirm = async () => {
    if (!orgName.trim()) return;
    try {
      setLoading(true);
      const Org = await createOrg(orgName.trim());
      dispatch(activateOrg({ currentOrgId: Org.id, currentOrgName: Org.name }));
      setOrgName("Organization");
      setIsModalOpen(false);
      setSync();
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog
      open={isModalOpen}
      onClose={handleClose}
      fullWidth
      maxWidth="xs"
    >
      <DialogTitle sx={{ fontWeight: 600 }}>Add Organization</DialogTitle>
      <DialogContent dividers>
        <Stack spacing={2}>
          <TextField
            label="Organization Name"
            value={orgName}
            onChange={(e) => setOrgName(e.target.value)}
            autoFocus
            fullWidth
          />
          <Typography variant="body2" color="text.secondary">
            创建一个新的组织以便在控制平面中管理资源。
          </Typography>
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, py: 2 }}>
        <MUIButton onClick={handleClose}>Cancel</MUIButton>
        <MUIButton
          variant="contained"
          onClick={handleConfirm}
          disabled={!orgName.trim() || loading}
        >
          {loading ? "Creating..." : "Create"}
        </MUIButton>
      </DialogActions>
    </Dialog>
  );
};

const AddEnvModal: React.FC<{
  isModalOpen?: boolean,
  setIsModalOpen: React.Dispatch<React.SetStateAction<boolean>>,
  setSync: () => void,
  defaultEnvType?: string,
}> = ({ isModalOpen = false, setIsModalOpen, setSync, defaultEnvType = 'Fabric' }) => {
  const [envName, setEnvName] = useState("Environment");
  const [envType, setEnvType] = useState(defaultEnvType);
  const [loading, setLoading] = useState(false);
  const dispatch = useAppDispatch();
  const currentConsortiumId = useAppSelector(selectConsortium).currentConsortiumId;

  useEffect(() => {
    if (isModalOpen) {
      setEnvName("Environment");
      setEnvType(defaultEnvType);
    }
  }, [isModalOpen, defaultEnvType]);

  const handleClose = () => {
    if (loading) return;
    setIsModalOpen(false);
    setEnvName("Environment");
    setEnvType(defaultEnvType);
  };

  const handleConfirm = async () => {
    if (!envName.trim()) return;
    try {
      setLoading(true);
      const Env = await createEnvironment(currentConsortiumId, envName.trim());
      dispatch(activateEnv({
        currentEnvId: Env.id,
        currentEnvName: Env.name,
        currentEnvType: envType || 'Fabric'
      }));
      setIsModalOpen(false);
      setSync();
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog
      open={isModalOpen}
      onClose={handleClose}
      fullWidth
      maxWidth="xs"
    >
      <DialogTitle sx={{ fontWeight: 600 }}>Add Environment</DialogTitle>
      <DialogContent dividers>
        <Stack spacing={2}>
          <TextField
            label="Environment Name"
            value={envName}
            onChange={(e) => setEnvName(e.target.value)}
            autoFocus
            fullWidth
          />
          <FormControl fullWidth>
            <InputLabel id="env-type-label">Environment Type</InputLabel>
            <MUISelect
              labelId="env-type-label"
              value={envType}
              label="Environment Type"
              onChange={(e: SelectChangeEvent<string>) => setEnvType(e.target.value as string)}
            >
              <MUIMenuItem value="Ethereum">Ethereum</MUIMenuItem>
              <MUIMenuItem value="Fabric">Fabric</MUIMenuItem>
              <MUIMenuItem value="Quorum" disabled>Quorum (coming soon)</MUIMenuItem>
            </MUISelect>
          </FormControl>
          <Typography variant="body2" color="text.secondary">
            为当前联盟创建一个新的运行环境，系统将自动完成资源准备。
          </Typography>
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, py: 2 }}>
        <MUIButton onClick={handleClose}>Cancel</MUIButton>
        <MUIButton
          variant="contained"
          onClick={handleConfirm}
          disabled={!envName.trim() || loading}
        >
          {loading ? "Creating..." : "Create"}
        </MUIButton>
      </DialogActions>
    </Dialog>
  );
}


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
          currentEnvName: matchedEnv.name
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
            () => dispatch(activateOrg({ currentOrgId: item.id, currentOrgName: item.name }))
          } >{item.name}</Menu.Item>
        ))}
        <Menu.Divider
          style={{ backgroundColor: "rgba(15, 23, 42, 0.08)" }}
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
          style={{ backgroundColor: "rgba(15, 23, 42, 0.08)" }}
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
            () => dispatch(activateConsortium({ currentConsortiumId: item.id, currentConsortiumName: item.name }))
          } >{item.name}</Menu.Item>
        ))}
        <Menu.Divider
          style={{ backgroundColor: "rgba(15, 23, 42, 0.08)" }}
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
      <Menu.Item key="/bpmn/drawing">DrawingBpmn</Menu.Item>
      <Menu.Item key="/bpmn/dmn">Dmns</Menu.Item>
      <Menu.Item key="/bpmn/translation">Deploy</Menu.Item>
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
