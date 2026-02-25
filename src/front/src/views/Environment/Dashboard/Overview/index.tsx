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
  InstallChainlinkForEthEnv,
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
  redeployIdentityContract,
  getChainlinkDetailForEthEnv,
  syncChainlinkForEthEnv,
  getEthAccountCheck,
  getDmnContractDetailForEthEnv,
  registerDmnContractToFireflyForEthEnv,
  callDmnContractForEthEnv,
  getDataContractDetailForEthEnv,
  setupDataContractForEthEnv,
  registerDataContractToFireflyForEthEnv,
  getComputeContractDetailForEthEnv,
  setupComputeContractForEthEnv,
  registerComputeContractToFireflyForEthEnv,
  getRelayerContractDetailForEthEnv,
  setupRelayerContractForEthEnv,
  registerRelayerContractToFireflyForEthEnv,
  getRelayerNodeStatusForEthEnv,
  controlRelayerNodeForEthEnv,
  getTask,
  getTasks,
} from "@/api/resourceAPI";

import {
  registerInterface,
  registerAPI,
  callFireflyContract
} from "@/api/executionAPI"

const systemFireflyURL = (import.meta.env.VITE_FIREFLY_URL as string) || "http://127.0.0.1:5000"
const fireflyBaseUrl = systemFireflyURL.replace(/\/$/, "")
const fireflyUiUrl = `${fireflyBaseUrl}/ui`
const fireflyApiDocUrl = `${fireflyBaseUrl}/api`


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
  DataContractComponentCard,
  ComputeContractComponentCard,
  RelayerComponentCard,
  IdentityContractComponentCard,
  SystemAccountComponentCard,

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
  const isEthereumEnv = currentEnvType === "Ethereum";
  const ethChainlinkStatus = envInfo.chainlinkStatus ?? "NO";
  const ethDmnContractAddress = envInfo.dmnContractAddress || "";
  const ethDmnContractStatus = ethDmnContractAddress ? "STARTED" : ethChainlinkStatus;
  const ethDmnFireflyStatus = envInfo.dmnFireflyRegistered ? "STARTED" : "NO";
  const ethDataContractAddress = envInfo.dataContractAddress || "";
  const ethDataContractStatus = ethDataContractAddress ? "STARTED" : "NO";
  const ethDataFireflyStatus = envInfo.dataFireflyRegistered ? "STARTED" : "NO";
  const ethComputeContractAddress = envInfo.computeContractAddress || "";
  const ethComputeContractStatus = ethComputeContractAddress ? "STARTED" : "NO";
  const ethComputeFireflyStatus = envInfo.computeFireflyRegistered ? "STARTED" : "NO";
  const ethRelayerContractAddress = envInfo.relayerContractAddress || "";
  const ethRelayerContractStatus = ethRelayerContractAddress ? "STARTED" : "NO";
  const ethRelayerFireflyStatus = envInfo.relayerFireflyRegistered ? "STARTED" : "NO";

  const setupCallBackRef = useRef(null)

  const [setupFabricNetWorkLoading, setSetupFabricNetWorkLoading] = useState(false)
  const [setUpEthereumNetworkLoading, setSetUpEthereumNetworkLoading] = useState(false)

  const [setupComponentLoading, setSetupComponentLoading] = useState(false)
  const [setupFireflyLoading, setSetupFireflyLoading] = useState(false)
  const [setupOracleLoading, setSetupOracleLoading] = useState(false)
  const [setupDMNLoading, setSetupDMNLoading] = useState(false)
  const [setupDmnFireflyLoading, setSetupDmnFireflyLoading] = useState(false)
  const [setupDataContractLoading, setSetupDataContractLoading] = useState(false)
  const [setupDataFireflyLoading, setSetupDataFireflyLoading] = useState(false)
  const [setupComputeContractLoading, setSetupComputeContractLoading] = useState(false)
  const [setupComputeFireflyLoading, setSetupComputeFireflyLoading] = useState(false)
  const [setupRelayerContractLoading, setSetupRelayerContractLoading] = useState(false)
  const [setupRelayerFireflyLoading, setSetupRelayerFireflyLoading] = useState(false)
  const [relayerNodeActionLoading, setRelayerNodeActionLoading] = useState(false)
  const [setupIdentityLoading, setSetupIdentityLoading] = useState(false)

  const [detailOpen, setDetailOpen] = useState(false)
  const [detailType, setDetailType] = useState("")
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailPayload, setDetailPayload] = useState(null)
  const [chainlinkDetail, setChainlinkDetail] = useState(null)
  const [chainlinkSyncLoading, setChainlinkSyncLoading] = useState(false)
  const [dmnDetail, setDmnDetail] = useState(null)
  const [dataDetail, setDataDetail] = useState(null)
  const [computeDetail, setComputeDetail] = useState(null)
  const [relayerDetail, setRelayerDetail] = useState<any>(null)
  const [relayerNodeStatus, setRelayerNodeStatus] = useState<any>(null)
  const [ethAccountCheck, setEthAccountCheck] = useState<any>(null)
  const [ethAccountCheckLoading, setEthAccountCheckLoading] = useState(false)
  const [callLoading, setCallLoading] = useState(false)
  const [callResult, setCallResult] = useState<string | null>(null)
  const [callForm] = Form.useForm()
  const [identityAction, setIdentityAction] = useState(null)
  const [dmnAction, setDmnAction] = useState(null)
  const [dmnCallLoading, setDmnCallLoading] = useState(false)
  const [dmnCallResult, setDmnCallResult] = useState<string | null>(null)
  const [dmnForm] = Form.useForm()
  const [taskItems, setTaskItems] = useState<any[]>([])
  const [taskMap, setTaskMap] = useState<Record<string, any>>({})
  const taskTimerRef = useRef<number | null>(null)
  const taskItemsRef = useRef<any[]>([])
  const hadRunningTasksRef = useRef<boolean>(false)
  const lastTerminalTaskKeyRef = useRef<string>("")
  const authWarningShownRef = useRef<boolean>(false)
  const taskTypeLabelMap: Record<string, string> = {
    FABRIC_FIREFLY_INSTALL: "Firefly Install",
    FABRIC_FIREFLY_START: "Firefly Start",
    ETH_FIREFLY_INSTALL: "ETH Firefly Install",
    FABRIC_ORACLE_INSTALL: "Oracle Install",
    ETH_ORACLE_INSTALL: "ETH Oracle Install",
    FABRIC_DMN_INSTALL: "DMN Install",
    ETH_DMN_INSTALL: "ETH DMN Install",
    CHAINLINK_INSTALL: "Chainlink + DMN Install",
    CHAINLINK_JOB_CREATE: "Chainlink Job Create",
    DMN_FIREFLY_REGISTER: "Register DMN to FireFly",
    DATA_CONTRACT_SETUP: "Data Contract Setup",
    DATA_CONTRACT_FIREFLY_REGISTER: "Register Data Contract to FireFly",
    COMPUTE_CONTRACT_SETUP: "Compute Contract Setup",
    COMPUTE_CONTRACT_FIREFLY_REGISTER: "Register Compute Contract to FireFly",
    RELAYER_CONTRACT_SETUP: "Relayer Contract Setup",
    RELAYER_CONTRACT_FIREFLY_REGISTER: "Register Relayer Contract to FireFly",
    IDENTITY_CONTRACT_INSTALL: "Identity Contract Install",
    IDENTITY_CONTRACT_REDEPLOY: "Identity Contract Redeploy",
  }
  const extractErrorMessage = (error: any, fallback: string = "Request failed") => {
    return (
      error?.data?.message ||
      error?.data?.detail ||
      error?.response?.data?.message ||
      error?.response?.data?.detail ||
      error?.message ||
      fallback
    )
  }
  const isUnauthorizedError = (error: any) => {
    return (
      error?.status === 401 ||
      error?.response?.status === 401 ||
      error?.data?.detail === "Authentication credentials were not provided." ||
      error?.response?.data?.detail === "Authentication credentials were not provided."
    )
  }
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

  const dmnQuickActions = [
    {
      label: "requestDMNDecision",
      method: "requestDMNDecision",
      mode: "invoke",
      params: [
        { key: "url", label: "DMN URL", placeholder: "http://cdmn-node1:5000/api/dmn/evaluate" },
        { key: "dmnContent", label: "DMN Content", placeholder: "<DMN XML>" },
        { key: "decisionId", label: "Decision ID", placeholder: "decision" },
        { key: "inputData", label: "Input JSON", placeholder: "{\"temperature\":20}" },
      ],
    },
    {
      label: "getRawByRequestId",
      method: "getRawByRequestId",
      mode: "call",
      params: [{ key: "requestId", label: "Request ID", placeholder: "0x..." }],
    },
    {
      label: "getDMNResult",
      method: "getDMNResult",
      mode: "call",
      params: [],
    },
    {
      label: "rawResultCount",
      method: "rawResultCount",
      mode: "call",
      params: [],
    },
    {
      label: "rawResultHashAt",
      method: "rawResultHashAt",
      mode: "call",
      params: [{ key: "index", label: "Index", placeholder: "0" }],
    },
    {
      label: "getAllRawResults",
      method: "getAllRawResults",
      mode: "call",
      params: [],
    },
  ]

  const handleSetUpFabricNetwork = async () => {
    try {
      setSetupFabricNetWorkLoading(true)
      await InitEnv(currentEnvId)
      setSync()
      await new Promise((resolve, reject) => {
        setIsJoinModelOpen(true)
        setupCallBackRef.current = resolve
      })
      setSync()
      await StartEnv(currentEnvId)
      setSync()
      await ActivateEnv(currentEnvId, currentOrgId)
      setSync()
    } catch (error: any) {
      message.error(extractErrorMessage(error, "Setup Fabric network failed"))
    } finally {
      setSetupFabricNetWorkLoading(false)
    }
  }

  const handleSetUpEthereumNetwork = async () => {
    try {
      setSetUpEthereumNetworkLoading(true)
      await InitEthEnv(currentEnvId)
      setSync()
      await new Promise((resolve, reject) => {
        setIsJoinModelOpen(true)
        setupCallBackRef.current = resolve
      })
      setSync()
      await StartEthEnv(currentEnvId)
      setSync()
      await ActivateEthEnv(currentEnvId)
      setSync()
    } catch (error: any) {
      message.error(extractErrorMessage(error, "Setup Ethereum network failed"))
    } finally {
      setSetUpEthereumNetworkLoading(false)
    }
  }

  const upsertTaskItem = (item: any) => {
    setTaskItems((prev) => {
      const idx = prev.findIndex((t) => t.id === item.id)
      if (idx >= 0) {
        const next = [...prev]
        next[idx] = { ...next[idx], ...item }
        return next
      }
      return [...prev, item]
    })
  }

  const parseTaskTime = (item: any): number => {
    const raw = item?.updated_at || item?.updatedAt || item?.created_at || item?.createdAt
    if (!raw) {
      return 0
    }
    const value = new Date(raw).getTime()
    return Number.isNaN(value) ? 0 : value
  }

  const mergeTaskItems = (localItems: any[], remoteItems: any[]) => {
    const byId = new Map<string, any>()
    remoteItems.forEach((item) => {
      if (!item?.id) return
      byId.set(String(item.id), { ...item })
    })
    localItems.forEach((item) => {
      if (!item?.id) return
      const id = String(item.id)
      const remote = byId.get(id)
      if (!remote) {
        byId.set(id, { ...item })
        return
      }
      byId.set(id, {
        ...item,
        ...remote,
        label: remote.label || item.label,
      })
    })
    return Array.from(byId.values()).sort((a, b) => parseTaskTime(b) - parseTaskTime(a))
  }

  const humanizeTaskType = (rawType: string) => {
    if (!rawType) return "Task"
    const upper = String(rawType).toUpperCase()
    if (taskTypeLabelMap[upper]) {
      return taskTypeLabelMap[upper]
    }
    return upper
      .split("_")
      .filter(Boolean)
      .map((token) => token.charAt(0) + token.slice(1).toLowerCase())
      .join(" ")
  }

  const taskStatusColor = (statusValue: string) => {
    const normalized = String(statusValue || "").toUpperCase()
    if (normalized === "SUCCESS") return "green"
    if (normalized === "RUNNING") return "blue"
    if (normalized === "PENDING") return "default"
    if (normalized === "FAILED") return "red"
    return "default"
  }

  const pollTasksOnce = async (seedItems: any[] = []) => {
    const pendingMap = new Map<string, any>()
    const candidates = [...seedItems, ...taskItemsRef.current]
    candidates
      .filter((t) => t && (t.status === "PENDING" || t.status === "RUNNING"))
      .forEach((t) => pendingMap.set(String(t.id), t))
    const pending = Array.from(pendingMap.values())
    if (pending.length === 0) {
      return
    }
    await Promise.all(
      pending.map(async (t) => {
        try {
          const res = await getTask(t.id)
          if (res && res.id) {
            upsertTaskItem(res)
          }
        } catch (error) {
          // keep polling resilient for per-task failures
        }
      })
    )
  }

  const refreshTasks = async () => {
    if (!currentEnvId || !currentEnvType) {
      return
    }
    const token = localStorage.getItem("token")
    if (!token) {
      if (taskTimerRef.current) {
        window.clearTimeout(taskTimerRef.current)
        taskTimerRef.current = null
      }
      return
    }
    const targetType = currentEnvType === "Ethereum" ? "EthEnvironment" : "Environment"
    try {
      const res = await getTasks(targetType, currentEnvId, 50)
      authWarningShownRef.current = false
      if (Array.isArray(res)) {
      const mergedItems = mergeTaskItems(taskItemsRef.current, res)
      setTaskItems(mergedItems)
      setTaskMap(buildTaskMap(mergedItems))
      const relatedTaskTypes = new Set([
        "FABRIC_FIREFLY_INSTALL",
        "FABRIC_FIREFLY_START",
        "ETH_FIREFLY_INSTALL",
        "FABRIC_ORACLE_INSTALL",
        "ETH_ORACLE_INSTALL",
        "FABRIC_DMN_INSTALL",
        "ETH_DMN_INSTALL",
        "CHAINLINK_INSTALL",
        "CHAINLINK_JOB_CREATE",
        "DMN_FIREFLY_REGISTER",
        "DATA_CONTRACT_SETUP",
        "DATA_CONTRACT_FIREFLY_REGISTER",
        "COMPUTE_CONTRACT_SETUP",
        "COMPUTE_CONTRACT_FIREFLY_REGISTER",
        "RELAYER_CONTRACT_SETUP",
        "RELAYER_CONTRACT_FIREFLY_REGISTER",
        "IDENTITY_CONTRACT_INSTALL",
        "IDENTITY_CONTRACT_REDEPLOY",
      ])
      const terminalTask = mergedItems.find(
        (t) =>
          relatedTaskTypes.has(t.type) &&
          (String(t.status || "").toUpperCase() === "SUCCESS" ||
            String(t.status || "").toUpperCase() === "FAILED")
      )
      if (terminalTask) {
        const terminalKey = `${terminalTask.id}:${terminalTask.status}:${terminalTask.updated_at || terminalTask.updatedAt || ""}`
        if (terminalKey !== lastTerminalTaskKeyRef.current) {
          lastTerminalTaskKeyRef.current = terminalKey
          await setSync()
          if (currentEnvType === "Ethereum") {
            await loadEthAccountCheck(true)
          }
        }
      }
      const running = mergedItems.some(
        (t) =>
          relatedTaskTypes.has(t.type) &&
          (t.status === "PENDING" || t.status === "RUNNING")
      )
      if (running) {
        hadRunningTasksRef.current = true
        await setSync()
      } else if (hadRunningTasksRef.current) {
        hadRunningTasksRef.current = false
        await setSync()
      }
      }
    } catch (error: any) {
      if (isUnauthorizedError(error)) {
        if (taskTimerRef.current) {
          window.clearTimeout(taskTimerRef.current)
          taskTimerRef.current = null
        }
        if (!authWarningShownRef.current) {
          authWarningShownRef.current = true
          message.warning("Login expired, task polling stopped. Please login again.")
        }
        return
      }
      message.error(extractErrorMessage(error, "Refresh tasks failed"))
    }
  }

  const loadEthAccountCheck = async (silent = false) => {
    if (!currentEnvId || currentEnvType !== "Ethereum") {
      setEthAccountCheck(null)
      return
    }
    if (!silent) {
      setEthAccountCheckLoading(true)
    }
    try {
      const res = await getEthAccountCheck(currentEnvId)
      if (res && typeof res === "object" && (res.expected_account || res.rpc_url)) {
        setEthAccountCheck(res)
      } else {
        setEthAccountCheck(null)
      }
    } catch (error: any) {
      setEthAccountCheck(null)
      if (!silent) {
        message.error(extractErrorMessage(error, "Get account check failed"))
      }
    } finally {
      if (!silent) {
        setEthAccountCheckLoading(false)
      }
    }
  }

  const loadChainlinkDetail = async (silent = false, sync = false) => {
    if (!currentEnvId || currentEnvType !== "Ethereum") {
      setChainlinkDetail(null)
      return null
    }
    if (!silent) {
      setDetailLoading(true)
    }
    try {
      const detail = await getChainlinkDetailForEthEnv(currentEnvId, sync)
      setChainlinkDetail(detail)
      return detail
    } catch (error: any) {
      if (!silent) {
        message.error(extractErrorMessage(error, "Failed to load Chainlink detail"))
      }
      return null
    } finally {
      if (!silent) {
        setDetailLoading(false)
      }
    }
  }

  const loadDataContractDetail = async (silent = false) => {
    if (!currentEnvId || currentEnvType !== "Ethereum") {
      setDataDetail(null)
      return null
    }
    if (!silent) {
      setDetailLoading(true)
    }
    try {
      const detail = await getDataContractDetailForEthEnv(currentEnvId, true)
      setDataDetail(detail)
      return detail
    } catch (error: any) {
      if (!silent) {
        message.error(extractErrorMessage(error, "Load data contract detail failed"))
      }
      return null
    } finally {
      if (!silent) {
        setDetailLoading(false)
      }
    }
  }

  const loadComputeContractDetail = async (silent = false) => {
    if (!currentEnvId || currentEnvType !== "Ethereum") {
      setComputeDetail(null)
      return null
    }
    if (!silent) {
      setDetailLoading(true)
    }
    try {
      const detail = await getComputeContractDetailForEthEnv(currentEnvId, true)
      setComputeDetail(detail)
      return detail
    } catch (error: any) {
      if (!silent) {
        message.error(extractErrorMessage(error, "Load compute contract detail failed"))
      }
      return null
    } finally {
      if (!silent) {
        setDetailLoading(false)
      }
    }
  }

  const loadRelayerContractDetail = async (silent = false) => {
    if (!currentEnvId || currentEnvType !== "Ethereum") {
      setRelayerDetail(null)
      return null
    }
    if (!silent) {
      setDetailLoading(true)
    }
    try {
      const detail = await getRelayerContractDetailForEthEnv(currentEnvId, true)
      setRelayerDetail(detail)
      if (detail?.node) {
        setRelayerNodeStatus(detail.node)
      }
      return detail
    } catch (error: any) {
      if (!silent) {
        message.error(extractErrorMessage(error, "Load relayer contract detail failed"))
      }
      return null
    } finally {
      if (!silent) {
        setDetailLoading(false)
      }
    }
  }

  const loadRelayerNodeStatus = async (silent = false) => {
    if (!currentEnvId || currentEnvType !== "Ethereum") {
      setRelayerNodeStatus(null)
      return null
    }
    if (!silent) {
      setRelayerNodeActionLoading(true)
    }
    try {
      const status = await getRelayerNodeStatusForEthEnv(currentEnvId)
      setRelayerNodeStatus(status)
      return status
    } catch (error: any) {
      if (!silent) {
        message.error(extractErrorMessage(error, "Load relayer node status failed"))
      }
      return null
    } finally {
      if (!silent) {
        setRelayerNodeActionLoading(false)
      }
    }
  }

  const handleSyncChainlinkCluster = async (silent = false) => {
    if (!currentEnvId || currentEnvType !== "Ethereum") {
      return
    }
    if (!silent) {
      setChainlinkSyncLoading(true)
    }
    try {
      await syncChainlinkForEthEnv(currentEnvId, true)
      await Promise.all([loadChainlinkDetail(true, false), setSync()])
      if (!silent) {
        message.success("Chainlink cluster synced")
      }
    } catch (error: any) {
      if (!silent) {
        message.error(extractErrorMessage(error, "Sync Chainlink cluster failed"))
      }
    } finally {
      if (!silent) {
        setChainlinkSyncLoading(false)
      }
    }
  }

  const startTaskPolling = async (taskId: string, label: string) => {
    const seed = { id: taskId, label, status: "PENDING" }
    upsertTaskItem(seed)
    await pollTasksOnce([seed])
  }

  const buildTaskMap = (tasks: any[]) => {
    const pickLatest = (types: string[]) => {
      const candidates = tasks.filter((t) => types.includes(t.type))
      if (candidates.length === 0) return null
      const running = candidates.find((t) => t.status === "RUNNING" || t.status === "PENDING")
      return running || candidates[0]
    }
    const map: Record<string, any> = {}
    map.firefly = pickLatest(["FABRIC_FIREFLY_INSTALL", "FABRIC_FIREFLY_START", "ETH_FIREFLY_INSTALL"])
    map.oracle = pickLatest([
      "FABRIC_ORACLE_INSTALL",
      "ETH_ORACLE_INSTALL",
      "CHAINLINK_INSTALL",
      "CHAINLINK_JOB_CREATE",
    ])
    map.dmn = pickLatest(["FABRIC_DMN_INSTALL", "ETH_DMN_INSTALL", "CHAINLINK_INSTALL", "DMN_FIREFLY_REGISTER"])
    map.data = pickLatest(["DATA_CONTRACT_SETUP", "DATA_CONTRACT_FIREFLY_REGISTER"])
    map.compute = pickLatest(["COMPUTE_CONTRACT_SETUP", "COMPUTE_CONTRACT_FIREFLY_REGISTER"])
    map.relayer = pickLatest(["RELAYER_CONTRACT_SETUP", "RELAYER_CONTRACT_FIREFLY_REGISTER"])
    map.identity = pickLatest(["IDENTITY_CONTRACT_INSTALL", "IDENTITY_CONTRACT_REDEPLOY"])
    return map
  }

  const applyTaskOverlay = (value: any, taskInfo: any) => {
    if (!taskInfo) {
      return value
    }
    const status = String(taskInfo.status || "").toUpperCase()
    if (status === "PENDING" || status === "RUNNING") {
      return "SETTINGUP"
    }
    if (status === "FAILED") {
      return "FAILED"
    }
    return value
  }

  useEffect(() => {
    if (!currentEnvId || !currentEnvType) {
      return
    }
    let stopped = false
    const stopTimer = () => {
      if (taskTimerRef.current) {
        window.clearTimeout(taskTimerRef.current)
        taskTimerRef.current = null
      }
    }
    const scheduleNext = (delay: number) => {
      stopTimer()
      taskTimerRef.current = window.setTimeout(runPolling, delay)
    }
    const runPolling = async () => {
      if (stopped) {
        return
      }
      await refreshTasks()
      if (stopped) {
        return
      }
      const token = localStorage.getItem("token")
      if (!token) {
        stopTimer()
        return
      }
      scheduleNext(hadRunningTasksRef.current ? 2000 : 10000)
    }
    runPolling()
    if (currentEnvType === "Ethereum") {
      loadEthAccountCheck(true)
      loadRelayerNodeStatus(true)
    } else {
      setEthAccountCheck(null)
      setRelayerNodeStatus(null)
    }
    return () => {
      stopped = true
      stopTimer()
    }
  }, [currentEnvId, currentEnvType])

  useEffect(() => {
    if (
      !detailOpen ||
      detailType !== "Oracle" ||
      currentEnvType !== "Ethereum" ||
      !currentEnvId
    ) {
      return
    }
    const timer = window.setInterval(() => {
      loadChainlinkDetail(true, true)
    }, 10000)
    return () => {
      window.clearInterval(timer)
    }
  }, [detailOpen, detailType, currentEnvType, currentEnvId])

  const handleSetUpFabricComponent = async () => {
    try {
      setSetupComponentLoading(true)
      const fireflyRes = await InstallFirefly(currentOrgId, currentEnvId)
      if (fireflyRes?.task_id) {
        await startTaskPolling(fireflyRes.task_id, "Fabric Firefly Install")
      }
      setSync()
      const startRes = await StartFireflyForEnv(currentEnvId)
      if (startRes?.task_id) {
        await startTaskPolling(startRes.task_id, "Fabric Firefly Start")
      }
      setSync()
      const oracleRes = await InstallOracle(currentOrgId, currentEnvId)
      if (oracleRes?.task_id) {
        await startTaskPolling(oracleRes.task_id, "Fabric Oracle Install")
      }
      const oracleFFI = await requestOracleFFI()
      const res = await registerInterface(systemFireflyURL, oracleFFI.ffiContent, "Oracle")
      await new Promise((resolve, reject) => {
        setTimeout(resolve, 5000)
      })
      await registerAPI(systemFireflyURL, "Oracle", "default", "Oracle", res.id)
      setSync()
      const dmnRes = await InstallDmnEngine(currentOrgId, currentEnvId)
      if (dmnRes?.task_id) {
        await startTaskPolling(dmnRes.task_id, "Fabric DMN Install")
      }
      setSync()
    } catch (error: any) {
      message.error(extractErrorMessage(error, "Setup Fabric components failed"))
    } finally {
      setSetupComponentLoading(false)
    }
  }

  const handleSetUpEthereumComponent = async () => {
    try {
      setSetupComponentLoading(true)
      await InitFireflyForEthEnv(currentEnvId)
      setSync()
      await StartFireflyForEthEnv(currentEnvId)
      setSync()
    } catch (error: any) {
      message.error(extractErrorMessage(error, "Setup Ethereum components failed"))
    } finally {
      setSetupComponentLoading(false)
    }
  }

  const handleSetUpFireflyOnly = async () => {
    try {
      setSetupFireflyLoading(true)
      if (currentEnvType === "Fabric") {
        const installRes = await InstallFirefly(currentOrgId, currentEnvId)
        if (installRes?.task_id) {
          await startTaskPolling(installRes.task_id, "Fabric Firefly Install")
        }
        setSync()
        const startRes = await StartFireflyForEnv(currentEnvId)
        if (startRes?.task_id) {
          await startTaskPolling(startRes.task_id, "Fabric Firefly Start")
        }
        setSync()
      } else {
        await InitFireflyForEthEnv(currentEnvId)
        setSync()
        await StartFireflyForEthEnv(currentEnvId)
        setSync()
      }
    } catch (error: any) {
      message.error(extractErrorMessage(error, "Setup Firefly failed"))
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
      const oracleRes = await InstallOracle(currentOrgId, currentEnvId)
      if (oracleRes?.task_id) {
        await startTaskPolling(oracleRes.task_id, "Fabric Oracle Install")
      }
      setSync()
      const oracleFFI = await requestOracleFFI()
      const res = await registerInterface(systemFireflyURL, oracleFFI.ffiContent, "Oracle")
      await new Promise((resolve) => {
        setTimeout(resolve, 5000)
      })
      await registerAPI(systemFireflyURL, "Oracle", "default", "Oracle", res.id)
      setSync()
    } catch (error: any) {
      message.error(extractErrorMessage(error, "Setup Oracle failed"))
    } finally {
      setSetupOracleLoading(false)
    }
  }

  const handleSetUpDMNOnly = async () => {
    try {
      setSetupDMNLoading(true)
      if (currentEnvType === "Fabric") {
        const dmnRes = await InstallDmnEngine(currentOrgId, currentEnvId)
        if (dmnRes?.task_id) {
          await startTaskPolling(dmnRes.task_id, "Fabric DMN Install")
        }
        setSync()
        return
      }
      if (currentEnvType === "Ethereum") {
        const chainlinkRes = await InstallChainlinkForEthEnv(currentEnvId, "lite")
        if (chainlinkRes?.task_id) {
          await startTaskPolling(chainlinkRes.task_id, "Ethereum Chainlink Lite Install")
        }
        setSync()
        return
      }
      message.warning("DMN only supports Fabric/Ethereum environment")
    } catch (error: any) {
      message.error(extractErrorMessage(error, "Setup DMN failed"))
    } finally {
      setSetupDMNLoading(false)
    }
  }

  const handleRegisterDmnToFirefly = async () => {
    try {
      setSetupDmnFireflyLoading(true)
      if (currentEnvType !== "Ethereum") {
        message.warning("DMN FireFly registration only supports Ethereum environment")
        return
      }
      if (envInfo.chainlinkStatus !== "STARTED") {
        message.warning("DMN contract is not deployed yet")
        return
      }
      if (envInfo.fireflyStatus !== "STARTED") {
        message.warning("FireFly cluster is not started")
        return
      }
      if (envInfo.dmnFireflyRegistered) {
        message.info("DMN contract is already registered to FireFly")
        return
      }
      if (!envInfo.dmnContractAddress && !dmnDetail?.contract?.address) {
        message.warning("DMN contract address is missing, please run DMN setup first")
        return
      }
      const res = await registerDmnContractToFireflyForEthEnv(currentEnvId)
      if (res?.task_id) {
        await startTaskPolling(res.task_id, "Ethereum DMN FireFly Register")
        message.success("DMN register task started")
      } else if (res?.status === "STARTED" && res?.dmn_detail) {
        message.success("DMN contract already registered to FireFly")
      } else if (res?.message) {
        message.info(res.message)
      } else {
        message.success("DMN contract registered to FireFly")
      }
      setSync()
      if (detailType === "DMN") {
        const detail = await getDmnContractDetailForEthEnv(currentEnvId, true)
        setDmnDetail(detail)
      }
    } catch (error: any) {
      message.error(extractErrorMessage(error, "Failed to register DMN contract to FireFly"))
    } finally {
      setSetupDmnFireflyLoading(false)
    }
  }

  const handleSetUpDataContractOnly = async () => {
    try {
      setSetupDataContractLoading(true)
      if (currentEnvType !== "Ethereum") {
        message.warning("Data contract only supports Ethereum environment")
        return
      }
      if (envInfo.chainlinkStatus !== "STARTED") {
        message.warning("Please setup Chainlink + DMN first")
        return
      }
      const res = await setupDataContractForEthEnv(currentEnvId)
      if (res?.task_id) {
        await startTaskPolling(res.task_id, "Data Contract Setup")
        message.success("Data contract setup task started")
      } else if (res?.status === "STARTED") {
        message.success(res?.message || "Data contract already deployed")
      } else if (res?.message) {
        message.info(res.message)
      }
      setSync()
      if (detailType === "Data") {
        await loadDataContractDetail(true)
      }
    } catch (error: any) {
      message.error(extractErrorMessage(error, "Failed to setup data contract"))
    } finally {
      setSetupDataContractLoading(false)
    }
  }

  const handleRegisterDataToFirefly = async () => {
    try {
      setSetupDataFireflyLoading(true)
      if (currentEnvType !== "Ethereum") {
        message.warning("Data contract only supports Ethereum environment")
        return
      }
      if (envInfo.fireflyStatus !== "STARTED") {
        message.warning("Please setup Firefly first")
        return
      }
      if (!envInfo.dataContractAddress && !dataDetail?.contract?.address) {
        message.warning("Data contract address is missing, please run setup first")
        return
      }
      if (envInfo.dataFireflyRegistered) {
        message.info("Data contract already registered to FireFly")
        return
      }
      const res = await registerDataContractToFireflyForEthEnv(currentEnvId)
      if (res?.task_id) {
        await startTaskPolling(res.task_id, "Data Contract FireFly Register")
        message.success("Data contract register task started")
      } else if (res?.status === "STARTED") {
        message.success(res?.message || "Data contract already registered to FireFly")
      } else if (res?.message) {
        message.info(res.message)
      }
      setSync()
      if (detailType === "Data") {
        await loadDataContractDetail(true)
      }
    } catch (error: any) {
      message.error(extractErrorMessage(error, "Failed to register data contract to FireFly"))
    } finally {
      setSetupDataFireflyLoading(false)
    }
  }

  const handleSetUpComputeContractOnly = async () => {
    try {
      setSetupComputeContractLoading(true)
      if (currentEnvType !== "Ethereum") {
        message.warning("Compute contract only supports Ethereum environment")
        return
      }
      if (envInfo.chainlinkStatus !== "STARTED") {
        message.warning("Please setup Chainlink + DMN first")
        return
      }
      const res = await setupComputeContractForEthEnv(currentEnvId)
      if (res?.task_id) {
        await startTaskPolling(res.task_id, "Compute Contract Setup")
        message.success("Compute contract setup task started")
      } else if (res?.status === "STARTED") {
        message.success(res?.message || "Compute contract already deployed")
      } else if (res?.message) {
        message.info(res.message)
      }
      setSync()
      if (detailType === "Compute") {
        await loadComputeContractDetail(true)
      }
    } catch (error: any) {
      message.error(extractErrorMessage(error, "Failed to setup compute contract"))
    } finally {
      setSetupComputeContractLoading(false)
    }
  }

  const handleRegisterComputeToFirefly = async () => {
    try {
      setSetupComputeFireflyLoading(true)
      if (currentEnvType !== "Ethereum") {
        message.warning("Compute contract only supports Ethereum environment")
        return
      }
      if (envInfo.fireflyStatus !== "STARTED") {
        message.warning("Please setup Firefly first")
        return
      }
      if (!envInfo.computeContractAddress && !computeDetail?.contract?.address) {
        message.warning("Compute contract address is missing, please run setup first")
        return
      }
      if (envInfo.computeFireflyRegistered) {
        message.info("Compute contract already registered to FireFly")
        return
      }
      const res = await registerComputeContractToFireflyForEthEnv(currentEnvId)
      if (res?.task_id) {
        await startTaskPolling(res.task_id, "Compute Contract FireFly Register")
        message.success("Compute contract register task started")
      } else if (res?.status === "STARTED") {
        message.success(res?.message || "Compute contract already registered to FireFly")
      } else if (res?.message) {
        message.info(res.message)
      }
      setSync()
      if (detailType === "Compute") {
        await loadComputeContractDetail(true)
      }
    } catch (error: any) {
      message.error(extractErrorMessage(error, "Failed to register compute contract to FireFly"))
    } finally {
      setSetupComputeFireflyLoading(false)
    }
  }

  const handleSetUpRelayerContractOnly = async () => {
    try {
      setSetupRelayerContractLoading(true)
      if (currentEnvType !== "Ethereum") {
        message.warning("Relayer contract only supports Ethereum environment")
        return
      }
      if (envInfo.chainlinkStatus !== "STARTED") {
        message.warning("Please setup Chainlink first")
        return
      }
      if (ethRelayerContractAddress || relayerDetail?.contract?.address) {
        message.info("Relayer contract already deployed")
        return
      }
      const res = await setupRelayerContractForEthEnv(currentEnvId)
      if (res?.task_id) {
        await startTaskPolling(res.task_id, "Relayer Contract Setup")
      } else if (res?.status === "STARTED") {
        message.success(res?.message || "Relayer contract already deployed")
      } else if (res?.message) {
        message.info(res.message)
      }
      setSync()
      if (detailType === "Relayer") {
        await loadRelayerContractDetail(true)
      }
    } catch (error: any) {
      message.error(extractErrorMessage(error, "Failed to setup relayer contract"))
    } finally {
      setSetupRelayerContractLoading(false)
    }
  }

  const handleRegisterRelayerToFirefly = async () => {
    try {
      setSetupRelayerFireflyLoading(true)
      if (currentEnvType !== "Ethereum") {
        message.warning("Relayer contract only supports Ethereum environment")
        return
      }
      if (envInfo.fireflyStatus !== "STARTED") {
        message.warning("Please setup Firefly first")
        return
      }
      if (!ethRelayerContractAddress && !relayerDetail?.contract?.address) {
        message.warning("Relayer contract address is missing, please run setup first")
        return
      }
      if (envInfo.relayerFireflyRegistered) {
        message.info("Relayer contract already registered to FireFly")
        return
      }
      const res = await registerRelayerContractToFireflyForEthEnv(currentEnvId)
      if (res?.task_id) {
        await startTaskPolling(res.task_id, "Relayer Contract FireFly Register")
        message.success("Relayer contract register task started")
      } else if (res?.status === "STARTED") {
        message.success(res?.message || "Relayer contract already registered to FireFly")
      } else if (res?.message) {
        message.info(res.message)
      }
      setSync()
      if (detailType === "Relayer") {
        await loadRelayerContractDetail(true)
      }
    } catch (error: any) {
      message.error(extractErrorMessage(error, "Failed to register relayer contract to FireFly"))
    } finally {
      setSetupRelayerFireflyLoading(false)
    }
  }

  const handleRelayerNodeControl = async (action: "start" | "stop") => {
    if (!currentEnvId || currentEnvType !== "Ethereum") {
      return
    }
    try {
      setRelayerNodeActionLoading(true)
      const res = await controlRelayerNodeForEthEnv(currentEnvId, action)
      setRelayerNodeStatus(res?.status || null)
      message.success(`Relayer node ${action} command sent`)
    } catch (error: any) {
      message.error(extractErrorMessage(error, `Relayer node ${action} failed`))
    } finally {
      setRelayerNodeActionLoading(false)
    }
  }

  const handleSetUpIdentityContractOnly = async () => {
    try {
      setSetupIdentityLoading(true)
      if (currentEnvType !== "Ethereum") {
        message.warning("Identity contract only supports Ethereum environment")
        return
      }
      const identityRes = await InstallIdentityContract(currentEnvId)
      if (identityRes?.task_id) {
        await startTaskPolling(identityRes.task_id, "Ethereum Identity Contract Install")
      }
      setSync()
    } catch (error: any) {
      message.error(extractErrorMessage(error, "Setup identity contract failed"))
    } finally {
      setSetupIdentityLoading(false)
    }
  }

  const formatWei = (wei: string | null | undefined) => {
    if (!wei || typeof wei !== "string") {
      return "-"
    }
    try {
      const base = BigInt(wei)
      const whole = base / BigInt("1000000000000000000")
      const fraction = base % BigInt("1000000000000000000")
      const fractionText = fraction.toString().padStart(18, "0").replace(/0+$/, "").slice(0, 6)
      return fractionText ? `${whole.toString()}.${fractionText} ETH` : `${whole.toString()} ETH`
    } catch (error) {
      return wei
    }
  }

  useEffect(() => {
    taskItemsRef.current = taskItems
  }, [taskItems])

  useEffect(() => {
    return () => {
      if (taskTimerRef.current) {
        window.clearTimeout(taskTimerRef.current)
      }
    }
  }, [])


  const openComponentDetail = async (type: string) => {
    if (type === "Firefly") {
      if (currentEnvType === "Ethereum") {
        setDetailType(type)
        setDetailOpen(true)
        return
      }
      navigate(`/orgs/${currentOrgId}/consortia/${currentConsortiumId}/envs/${currentEnvId}/firefly`)
      return
    }
    setDetailType(type)
    setDetailOpen(true)
    setCallResult(null)
    setDmnCallResult(null)
    setDataDetail(null)
    setComputeDetail(null)
    setRelayerDetail(null)
    setRelayerNodeStatus(null)
    if (type === "Identity") {
      try {
        setDetailLoading(true)
        const detail = await getIdentityContractDetail(currentEnvId, true)
        setDetailPayload(detail)
      } finally {
        setDetailLoading(false)
      }
    } else if (type === "Oracle" && currentEnvType === "Ethereum") {
      try {
        setDetailLoading(true)
        const [detail] = await Promise.all([
          getChainlinkDetailForEthEnv(currentEnvId, true),
          loadEthAccountCheck(true),
        ])
        setChainlinkDetail(detail)
      } catch (error: any) {
        message.error(extractErrorMessage(error, "Load Chainlink detail failed"))
      } finally {
        setDetailLoading(false)
      }
    } else if (type === "DMN" && currentEnvType === "Ethereum") {
      try {
        setDetailLoading(true)
        const [detail] = await Promise.all([
          getDmnContractDetailForEthEnv(currentEnvId, true),
          loadEthAccountCheck(true),
        ])
        setDmnDetail(detail)
      } catch (error: any) {
        message.error(extractErrorMessage(error, "Load DMN detail failed"))
      } finally {
        setDetailLoading(false)
      }
    } else if (type === "Data" && currentEnvType === "Ethereum") {
      try {
        setDetailLoading(true)
        const [detail] = await Promise.all([
          getDataContractDetailForEthEnv(currentEnvId, true),
          loadEthAccountCheck(true),
        ])
        setDataDetail(detail)
      } catch (error: any) {
        message.error(extractErrorMessage(error, "Load data contract detail failed"))
      } finally {
        setDetailLoading(false)
      }
    } else if (type === "Compute" && currentEnvType === "Ethereum") {
      try {
        setDetailLoading(true)
        const [detail] = await Promise.all([
          getComputeContractDetailForEthEnv(currentEnvId, true),
          loadEthAccountCheck(true),
        ])
        setComputeDetail(detail)
      } catch (error: any) {
        message.error(extractErrorMessage(error, "Load compute contract detail failed"))
      } finally {
        setDetailLoading(false)
      }
    } else if (type === "Relayer" && currentEnvType === "Ethereum") {
      try {
        setDetailLoading(true)
        const [detail] = await Promise.all([
          getRelayerContractDetailForEthEnv(currentEnvId, true),
          loadEthAccountCheck(true),
        ])
        setRelayerDetail(detail)
        if (detail?.node) {
          setRelayerNodeStatus(detail.node)
        } else {
          await loadRelayerNodeStatus(true)
        }
      } catch (error: any) {
        message.error(extractErrorMessage(error, "Load relayer detail failed"))
      } finally {
        setDetailLoading(false)
      }
    } else if (type === "Account" && currentEnvType === "Ethereum") {
      try {
        setDetailLoading(true)
        await loadEthAccountCheck(false)
      } finally {
        setDetailLoading(false)
      }
    } else {
      setDetailPayload(null)
      setChainlinkDetail(null)
      setDmnDetail(null)
      setDataDetail(null)
      setComputeDetail(null)
      setRelayerDetail(null)
      setRelayerNodeStatus(null)
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

  const applyDmnQuickAction = (action) => {
    setDmnAction(action)
    dmnForm.setFieldsValue({
      method: action.method,
      mode: action.mode,
    })
  }

  const handleDmnCall = async () => {
    try {
      const values = await dmnForm.validateFields()
      setDmnCallLoading(true)
      const method = values.method
      const mode = values.mode || "call"
      const args = (dmnAction?.params || []).map((param) => values[param.key])
      const res = await callDmnContractForEthEnv(currentEnvId, { method, mode, args })
      setDmnCallResult(JSON.stringify(res, null, 2))
    } catch (err) {
      message.error("DMN call failed")
    } finally {
      setDmnCallLoading(false)
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
                ChaincodeStatus={applyTaskOverlay(envInfo.fireflyStatus !== "NO", taskMap.firefly)}
                ClusterStatus={applyTaskOverlay(envInfo.fireflyStatus === "STARTED", taskMap.firefly)}
                taskInfo={taskMap.firefly}
                onOpen={() => openComponentDetail("Firefly")}
                onSetup={
                  <LoadingButton
                    size="small"
                    variant="outlined"
                    loading={setupFireflyLoading}
                    onClick={handleSetUpFireflyOnly}
                    disabled={envInfo.fireflyStatus && envInfo.fireflyStatus !== "NO" && envInfo.fireflyStatus !== "FAILED"}
                  >
                    Setup
                  </LoadingButton>
                }
              />
              <OracleComponentCard
                ChaincodeStatus={
                  currentEnvType === "Ethereum"
                    ? applyTaskOverlay(envInfo.chainlinkStatus ?? "NO", taskMap.oracle)
                    : applyTaskOverlay(envInfo.oracleStatus === "CHAINCODEINSTALLED", taskMap.oracle)
                }
                statusKey={isEthereumEnv ? "Cluster" : "ChainCode"}
                taskInfo={taskMap.oracle}
                onOpen={() => openComponentDetail("Oracle")}
                onSetup={
                  currentEnvType === "Fabric" ? (
                    <LoadingButton
                      size="small"
                      variant="outlined"
                      loading={setupOracleLoading}
                      onClick={handleSetUpOracleOnly}
                      disabled={envInfo.oracleStatus && envInfo.oracleStatus !== "NO" && envInfo.oracleStatus !== "FAILED"}
                    >
                      Setup
                    </LoadingButton>
                  ) : null
                }
              />
              <DMNComponentCard
                ChaincodeStatus={
                  currentEnvType === "Ethereum"
                    ? applyTaskOverlay(ethDmnContractStatus, taskMap.dmn)
                    : applyTaskOverlay(envInfo.dmnStatus === "CHAINCODEINSTALLED", taskMap.dmn)
                }
                FireflyStatus={
                  isEthereumEnv
                    ? applyTaskOverlay(
                        ethDmnFireflyStatus,
                        String(taskMap.dmn?.type || "").toUpperCase() === "DMN_FIREFLY_REGISTER"
                          ? taskMap.dmn
                          : null
                      )
                    : null
                }
                statusKey={isEthereumEnv ? "Contract" : "ChainCode"}
                taskInfo={taskMap.dmn}
                onOpen={() => openComponentDetail("DMN")}
                onSetup={
                  currentEnvType === "Ethereum" ? (
                    <>
                      <LoadingButton
                        size="small"
                        variant="outlined"
                        loading={setupDMNLoading}
                        onClick={handleSetUpDMNOnly}
                        disabled={envInfo.chainlinkStatus && envInfo.chainlinkStatus !== "NO" && envInfo.chainlinkStatus !== "FAILED"}
                      >
                        Setup
                      </LoadingButton>
                      <LoadingButton
                        size="small"
                        variant="outlined"
                        loading={setupDmnFireflyLoading}
                        onClick={handleRegisterDmnToFirefly}
                        disabled={
                          envInfo.fireflyStatus !== "STARTED" ||
                          envInfo.chainlinkStatus !== "STARTED" ||
                          !ethDmnContractAddress ||
                          envInfo.dmnFireflyRegistered
                        }
                      >
                        Register FireFly
                      </LoadingButton>
                    </>
                  ) : (
                    <LoadingButton
                      size="small"
                      variant="outlined"
                      loading={setupDMNLoading}
                      onClick={handleSetUpDMNOnly}
                      disabled={
                        (currentEnvType !== "Fabric" && currentEnvType !== "Ethereum") ||
                        (currentEnvType === "Fabric" && envInfo.dmnStatus && envInfo.dmnStatus !== "NO" && envInfo.dmnStatus !== "FAILED")
                      }
                    >
                      Setup
                    </LoadingButton>
                  )
                }
              />
              {currentEnvType === "Ethereum" ? (
                <DataContractComponentCard
                  ContractStatus={applyTaskOverlay(ethDataContractStatus, taskMap.data)}
                  FireflyStatus={applyTaskOverlay(
                    ethDataFireflyStatus,
                    String(taskMap.data?.type || "").toUpperCase() === "DATA_CONTRACT_FIREFLY_REGISTER"
                      ? taskMap.data
                      : null
                  )}
                  taskInfo={taskMap.data}
                  onOpen={() => openComponentDetail("Data")}
                  onSetup={
                    <>
                      <LoadingButton
                        size="small"
                        variant="outlined"
                        loading={setupDataContractLoading}
                        onClick={handleSetUpDataContractOnly}
                        disabled={envInfo.chainlinkStatus !== "STARTED" || !!ethDataContractAddress}
                      >
                        Setup
                      </LoadingButton>
                      <LoadingButton
                        size="small"
                        variant="outlined"
                        loading={setupDataFireflyLoading}
                        onClick={handleRegisterDataToFirefly}
                        disabled={
                          envInfo.fireflyStatus !== "STARTED" ||
                          !ethDataContractAddress ||
                          envInfo.dataFireflyRegistered
                        }
                      >
                        Register FireFly
                      </LoadingButton>
                    </>
                  }
                />
              ) : null}
              {currentEnvType === "Ethereum" ? (
                <ComputeContractComponentCard
                  ContractStatus={applyTaskOverlay(ethComputeContractStatus, taskMap.compute)}
                  FireflyStatus={applyTaskOverlay(
                    ethComputeFireflyStatus,
                    String(taskMap.compute?.type || "").toUpperCase() === "COMPUTE_CONTRACT_FIREFLY_REGISTER"
                      ? taskMap.compute
                      : null
                  )}
                  taskInfo={taskMap.compute}
                  onOpen={() => openComponentDetail("Compute")}
                  onSetup={
                    <>
                      <LoadingButton
                        size="small"
                        variant="outlined"
                        loading={setupComputeContractLoading}
                        onClick={handleSetUpComputeContractOnly}
                        disabled={envInfo.chainlinkStatus !== "STARTED" || !!ethComputeContractAddress}
                      >
                        Setup
                      </LoadingButton>
                      <LoadingButton
                        size="small"
                        variant="outlined"
                        loading={setupComputeFireflyLoading}
                        onClick={handleRegisterComputeToFirefly}
                        disabled={
                          envInfo.fireflyStatus !== "STARTED" ||
                          !ethComputeContractAddress ||
                          envInfo.computeFireflyRegistered
                        }
                      >
                        Register FireFly
                      </LoadingButton>
                    </>
                  }
                />
              ) : null}
              {currentEnvType === "Ethereum" ? (
                <RelayerComponentCard
                  ContractStatus={applyTaskOverlay(ethRelayerContractStatus, taskMap.relayer)}
                  NodeStatus={(relayerNodeStatus?.running ? "STARTED" : "NO")}
                  FireflyStatus={applyTaskOverlay(
                    ethRelayerFireflyStatus,
                    String(taskMap.relayer?.type || "").toUpperCase() === "RELAYER_CONTRACT_FIREFLY_REGISTER"
                      ? taskMap.relayer
                      : null
                  )}
                  taskInfo={taskMap.relayer}
                  onOpen={() => openComponentDetail("Relayer")}
                  onSetup={
                    <>
                      <LoadingButton
                        size="small"
                        variant="outlined"
                        loading={setupRelayerContractLoading}
                        onClick={handleSetUpRelayerContractOnly}
                        disabled={envInfo.chainlinkStatus !== "STARTED" || !!ethRelayerContractAddress}
                      >
                        Setup
                      </LoadingButton>
                      <LoadingButton
                        size="small"
                        variant="outlined"
                        loading={setupRelayerFireflyLoading}
                        onClick={handleRegisterRelayerToFirefly}
                        disabled={
                          envInfo.fireflyStatus !== "STARTED" ||
                          !ethRelayerContractAddress ||
                          envInfo.relayerFireflyRegistered
                        }
                      >
                        Register FireFly
                      </LoadingButton>
                    </>
                  }
                />
              ) : null}
              <IdentityContractComponentCard
                ContractStatus={applyTaskOverlay(envInfo.identityContractStatus ?? "NO", taskMap.identity)}
                taskInfo={taskMap.identity}
                onOpen={() => openComponentDetail("Identity")}
                onSetup={
                  <LoadingButton
                    size="small"
                    variant="outlined"
                    loading={setupIdentityLoading}
                    onClick={handleSetUpIdentityContractOnly}
                    disabled={currentEnvType !== "Ethereum" || (envInfo.identityContractStatus && envInfo.identityContractStatus !== "NO" && envInfo.identityContractStatus !== "FAILED")}
                  >
                    Setup
                  </LoadingButton>
                }
              />
              {currentEnvType === "Ethereum" ? (
                <SystemAccountComponentCard
                  AccountStatus={ethAccountCheck?.has_expected_account && ethAccountCheck?.unlock_ok ? "STARTED" : "NO"}
                  onOpen={() => openComponentDetail("Account")}
                />
              ) : null}
            </Row>
            <Row style={{ width: "100%", marginTop: 12 }}>
              <Col span={24}>
                <div
                  style={{
                    border: "1px solid #e2e8f0",
                    borderRadius: 12,
                    padding: 12,
                    background: "#f8fafc",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                    <Text strong>Recent Tasks</Text>
                    <Space size={8}>
                      <Tag color="blue">Total: {taskItems.length}</Tag>
                      <AntdButton size="small" onClick={refreshTasks}>
                        Refresh
                      </AntdButton>
                    </Space>
                  </div>
                  <div style={{ maxHeight: 260, overflowY: "auto", paddingRight: 4 }}>
                    {taskItems.length === 0 ? (
                      <Text type="secondary">No recent tasks</Text>
                    ) : (
                      taskItems.slice(0, 12).map((task) => (
                        <div
                          key={task.id}
                          style={{
                            borderBottom: "1px dashed #dbeafe",
                            padding: "8px 0",
                          }}
                        >
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
                            <Space size={8} wrap>
                              <Tag color={taskStatusColor(task.status)}>
                                {String(task.status || "UNKNOWN").toUpperCase()}
                              </Tag>
                              <Text strong>{task.label || humanizeTaskType(task.type)}</Text>
                              {task.step ? <Tag>{String(task.step)}</Tag> : null}
                            </Space>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              {task.updated_at || task.updatedAt
                                ? new Date(task.updated_at || task.updatedAt).toLocaleTimeString()
                                : "-"}
                            </Text>
                          </div>
                          {task.error ? (
                            <Text type="danger" style={{ display: "block", marginTop: 4, fontSize: 12 }}>
                              {String(task.error)}
                            </Text>
                          ) : null}
                          {task?.result?.log_path ? (
                            <Text type="secondary" style={{ display: "block", marginTop: 2, fontSize: 12 }}>
                              log: {task.result.log_path}
                            </Text>
                          ) : null}
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </Col>
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
        {detailType === "Firefly" ? (
          <Space direction="vertical" style={{ width: "100%" }}>
            <Tag color={(envInfo.fireflyStatus === "STARTED") ? "green" : "red"}>
              Status: {envInfo.fireflyStatus || "NO"}
            </Tag>
            {currentEnvType === "Ethereum" ? (
              <Space direction="vertical">
                <div>Ethereum 环境不使用 Firefly 列表页。</div>
                <Space>
                  <AntdButton
                    type="link"
                    onClick={() => window.open(fireflyUiUrl, "_blank")}
                  >
                    Open Firefly UI
                  </AntdButton>
                  <AntdButton
                    type="link"
                    onClick={() => window.open(fireflyApiDocUrl, "_blank")}
                  >
                    Open Firefly API
                  </AntdButton>
                </Space>
              </Space>
            ) : (
              <Space direction="vertical">
                <div>Firefly 详情请通过 Firefly 页面查看。</div>
                <AntdButton
                  type="link"
                  onClick={() => window.open(fireflyUiUrl, "_blank")}
                >
                  Open Firefly UI
                </AntdButton>
              </Space>
            )}
          </Space>
        ) : null}
        {detailType === "Oracle" ? (
          <Space direction="vertical" style={{ width: "100%" }}>
            <Tag color={(currentEnvType === "Ethereum" ? (envInfo.chainlinkStatus === "STARTED") : (envInfo.oracleStatus === "CHAINCODEINSTALLED")) ? "green" : "red"}>
              Status: {currentEnvType === "Ethereum" ? (envInfo.chainlinkStatus || "NO") : (envInfo.oracleStatus || "NO")}
            </Tag>
            {currentEnvType === "Ethereum" ? (
              <>
                <div>Oracle 卡片在以太坊环境下展示 Chainlink 集群信息。</div>
                <Space>
                  <Tag color={ethAccountCheck?.has_expected_account && ethAccountCheck?.unlock_ok ? "green" : "orange"}>
                    Account Ready: {ethAccountCheck?.has_expected_account && ethAccountCheck?.unlock_ok ? "YES" : "NO"}
                  </Tag>
                  <AntdButton size="small" loading={ethAccountCheckLoading} onClick={() => loadEthAccountCheck(false)}>
                    Refresh Account Check
                  </AntdButton>
                  <AntdButton
                    size="small"
                    loading={chainlinkSyncLoading}
                    onClick={() => handleSyncChainlinkCluster(false)}
                  >
                    Sync Chainlink Cluster
                  </AntdButton>
                </Space>
                {detailLoading ? (
                  <div>Loading...</div>
                ) : (
                  <>
                    <div>LinkToken: {chainlinkDetail?.link_token || "-"}</div>
                    <div>Operator: {chainlinkDetail?.operator || "-"}</div>
                    <div>DMN Job ID: {chainlinkDetail?.dmn_job_id || "-"}</div>
                    <div>DMN Contract: {chainlinkDetail?.dmn_contract?.address || "-"}</div>
                    <div>System Account: {ethAccountCheck?.expected_account || "-"}</div>
                    <div>RPC URL: {ethAccountCheck?.rpc_url || "-"}</div>
                    <div>
                      Cluster Sync: {chainlinkDetail?.cluster_sync?.synced_at || "never"}
                    </div>
                    <div>
                      Healthy Nodes: {chainlinkDetail?.cluster_sync?.healthy_count ?? 0}/{chainlinkDetail?.cluster_sync?.node_count ?? 0}
                    </div>
                    {Array.isArray(chainlinkDetail?.cluster_sync?.nodes) && chainlinkDetail.cluster_sync.nodes.length > 0 ? (
                      <Space wrap>
                        {chainlinkDetail.cluster_sync.nodes.map((node: any) => (
                          <Tag key={node?.name || node?.url} color={node?.healthy ? "green" : "red"}>
                            {node?.name}: {node?.healthy ? `UP (${node?.job_count || 0} jobs)` : "DOWN"}
                          </Tag>
                        ))}
                      </Space>
                    ) : null}
                    <AntdButton
                      type="link"
                      onClick={() => {
                        const url = chainlinkDetail?.chainlink_ui
                        if (url) {
                          window.open(url, "_blank")
                        } else {
                          message.error("Chainlink UI not configured")
                        }
                      }}
                    >
                      Open Chainlink UI
                    </AntdButton>
                    <AntdButton
                      type="link"
                      onClick={() =>
                        navigate(
                          `/orgs/${currentOrgId}/consortia/${currentConsortiumId}/envs/${currentEnvId}/ethereum/chainlink-jobs`
                        )
                      }
                    >
                      Open Chainlink Jobs
                    </AntdButton>
                  </>
                )}
              </>
            ) : (
              <div>Oracle 通过 Firefly 注册的 FFI/API 使用。</div>
            )}
          </Space>
        ) : null}
        {detailType === "DMN" ? (
          <Space direction="vertical" style={{ width: "100%" }}>
            <Tag
              color={
                currentEnvType === "Ethereum"
                  ? ((dmnDetail?.contract?.address || ethDmnContractAddress) ? "green" : "red")
                  : (envInfo.dmnStatus === "CHAINCODEINSTALLED" ? "green" : "red")
              }
            >
              Status: {currentEnvType === "Ethereum"
                ? ((dmnDetail?.contract?.address || ethDmnContractAddress) ? "STARTED" : "NO")
                : (envInfo.dmnStatus || "NO")}
            </Tag>
            {currentEnvType === "Ethereum" ? (
              <>
                <div>DMN 通过 Chainlink lite 提供结果（与 Oracle 卡片共享安装流程）。</div>
                <Space>
                  <Tag color={ethAccountCheck?.has_expected_account && ethAccountCheck?.unlock_ok ? "green" : "orange"}>
                    Account Ready: {ethAccountCheck?.has_expected_account && ethAccountCheck?.unlock_ok ? "YES" : "NO"}
                  </Tag>
                  <AntdButton size="small" loading={ethAccountCheckLoading} onClick={() => loadEthAccountCheck(false)}>
                    Refresh Account Check
                  </AntdButton>
                </Space>
                {detailLoading ? (
                  <div>Loading...</div>
                ) : (
                  <>
                    <div>Install Pipeline: {envInfo.chainlinkStatus || "-"}</div>
                    <div>Contract Address: {dmnDetail?.contract?.address || "-"}</div>
                    <div>Operator: {dmnDetail?.operator || "-"}</div>
                    <div>LinkToken: {dmnDetail?.link_token || "-"}</div>
                    <div>DMN Job ID: {dmnDetail?.dmn_job_id || "-"}</div>
                    <div>
                      FireFly Registered: {dmnDetail?.firefly?.registered ? "YES" : "NO"}
                    </div>
                    <div>FireFly API: {dmnDetail?.firefly?.api_name || "-"}</div>
                    <div>FireFly Interface: {dmnDetail?.firefly?.interface_id || "-"}</div>
                    <div>FireFly Core: {dmnDetail?.firefly?.core_url || "-"}</div>
                    <AntdButton
                      size="small"
                      loading={setupDmnFireflyLoading}
                      onClick={handleRegisterDmnToFirefly}
                      disabled={envInfo.fireflyStatus !== "STARTED" || !dmnDetail?.contract?.address || !!dmnDetail?.firefly?.registered}
                    >
                      Register DMN To FireFly
                    </AntdButton>
                    <Form form={dmnForm} layout="vertical">
                      <Form.Item label="Quick Actions">
                        <Space wrap>
                          {dmnQuickActions.map((action) => (
                            <AntdButton
                              key={action.method}
                              onClick={() => applyDmnQuickAction(action)}
                            >
                              {action.label}
                            </AntdButton>
                          ))}
                        </Space>
                      </Form.Item>
                      <Form.Item
                        label="Method"
                        name="method"
                        rules={[{ required: true, message: "Method is required" }]}
                      >
                        <Input placeholder="requestDMNDecision / getRawByRequestId ..." />
                      </Form.Item>
                      {dmnAction ? (
                        dmnAction.params.map((param, index) => (
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
                      <Form.Item label="Mode" name="mode" initialValue="call">
                        <Input placeholder="call / invoke" />
                      </Form.Item>
                      <AntdButton loading={dmnCallLoading} onClick={handleDmnCall}>
                        Call DMN Contract
                      </AntdButton>
                    </Form>
                    {dmnCallResult ? (
                      <pre style={{ marginTop: 12, background: "#f8fafc", padding: 12 }}>
                        {dmnCallResult}
                      </pre>
                    ) : null}
                  </>
                )}
              </>
            ) : (
              <div>DMN Engine 仅支持 Fabric 环境。</div>
            )}
          </Space>
        ) : null}
        {detailType === "Data" ? (
          <Space direction="vertical" style={{ width: "100%" }}>
            <Tag color={(dataDetail?.contract?.address || ethDataContractAddress) ? "green" : "red"}>
              Status: {(dataDetail?.contract?.address || ethDataContractAddress) ? "STARTED" : "NO"}
            </Tag>
            <div>Data Contract 负责链外数据请求与结果回写。</div>
            <Space>
              <Tag color={ethAccountCheck?.has_expected_account && ethAccountCheck?.unlock_ok ? "green" : "orange"}>
                Account Ready: {ethAccountCheck?.has_expected_account && ethAccountCheck?.unlock_ok ? "YES" : "NO"}
              </Tag>
              <AntdButton size="small" loading={ethAccountCheckLoading} onClick={() => loadEthAccountCheck(false)}>
                Refresh Account Check
              </AntdButton>
            </Space>
            {detailLoading ? (
              <div>Loading...</div>
            ) : (
              <>
                <div>Contract Address: {dataDetail?.contract?.address || "-"}</div>
                <div>Main Router: {dataDetail?.main_router || "-"}</div>
                <div>Operator: {dataDetail?.operator || "-"}</div>
                <div>LinkToken: {dataDetail?.link_token || "-"}</div>
                <div>Job ID: {dataDetail?.job_id || "-"}</div>
                <div>FireFly Registered: {dataDetail?.firefly?.registered ? "YES" : "NO"}</div>
                <div>FireFly API: {dataDetail?.firefly?.api_name || "-"}</div>
                <div>FireFly Interface: {dataDetail?.firefly?.interface_id || "-"}</div>
                <div>FireFly Core: {dataDetail?.firefly?.core_url || "-"}</div>
                <Space>
                  <AntdButton
                    size="small"
                    loading={setupDataContractLoading}
                    onClick={handleSetUpDataContractOnly}
                    disabled={envInfo.chainlinkStatus !== "STARTED" || !!(dataDetail?.contract?.address || ethDataContractAddress)}
                  >
                    Setup Data Contract
                  </AntdButton>
                  <AntdButton
                    size="small"
                    loading={setupDataFireflyLoading}
                    onClick={handleRegisterDataToFirefly}
                    disabled={envInfo.fireflyStatus !== "STARTED" || !(dataDetail?.contract?.address || ethDataContractAddress) || !!dataDetail?.firefly?.registered}
                  >
                    Register Data To FireFly
                  </AntdButton>
                </Space>
              </>
            )}
          </Space>
        ) : null}
        {detailType === "Compute" ? (
          <Space direction="vertical" style={{ width: "100%" }}>
            <Tag color={(computeDetail?.contract?.address || ethComputeContractAddress) ? "green" : "red"}>
              Status: {(computeDetail?.contract?.address || ethComputeContractAddress) ? "STARTED" : "NO"}
            </Tag>
            <div>Compute Contract 负责链外计算任务请求与结果回写。</div>
            <Space>
              <Tag color={ethAccountCheck?.has_expected_account && ethAccountCheck?.unlock_ok ? "green" : "orange"}>
                Account Ready: {ethAccountCheck?.has_expected_account && ethAccountCheck?.unlock_ok ? "YES" : "NO"}
              </Tag>
              <AntdButton size="small" loading={ethAccountCheckLoading} onClick={() => loadEthAccountCheck(false)}>
                Refresh Account Check
              </AntdButton>
            </Space>
            {detailLoading ? (
              <div>Loading...</div>
            ) : (
              <>
                <div>Contract Address: {computeDetail?.contract?.address || "-"}</div>
                <div>Main Router: {computeDetail?.main_router || "-"}</div>
                <div>Operator: {computeDetail?.operator || "-"}</div>
                <div>LinkToken: {computeDetail?.link_token || "-"}</div>
                <div>Job ID: {computeDetail?.job_id || "-"}</div>
                <div>FireFly Registered: {computeDetail?.firefly?.registered ? "YES" : "NO"}</div>
                <div>FireFly API: {computeDetail?.firefly?.api_name || "-"}</div>
                <div>FireFly Interface: {computeDetail?.firefly?.interface_id || "-"}</div>
                <div>FireFly Core: {computeDetail?.firefly?.core_url || "-"}</div>
                <Space>
                  <AntdButton
                    size="small"
                    loading={setupComputeContractLoading}
                    onClick={handleSetUpComputeContractOnly}
                    disabled={envInfo.chainlinkStatus !== "STARTED" || !!(computeDetail?.contract?.address || ethComputeContractAddress)}
                  >
                    Setup Compute Contract
                  </AntdButton>
                  <AntdButton
                    size="small"
                    loading={setupComputeFireflyLoading}
                    onClick={handleRegisterComputeToFirefly}
                    disabled={envInfo.fireflyStatus !== "STARTED" || !(computeDetail?.contract?.address || ethComputeContractAddress) || !!computeDetail?.firefly?.registered}
                  >
                    Register Compute To FireFly
                  </AntdButton>
                </Space>
              </>
            )}
          </Space>
        ) : null}
        {detailType === "Relayer" ? (
          <Space direction="vertical" style={{ width: "100%" }}>
            <Tag color={(relayerDetail?.contract?.address || ethRelayerContractAddress) ? "green" : "red"}>
              Status: {(relayerDetail?.contract?.address || ethRelayerContractAddress) ? "STARTED" : "NO"}
            </Tag>
            <div>Relayer Contract 用于跨链请求中继验证与执行。</div>
            <Space>
              <Tag color={relayerNodeStatus?.running ? "green" : "orange"}>
                Relayer Node: {relayerNodeStatus?.running ? "RUNNING" : "NOT_READY"}
              </Tag>
              <Tag color={ethAccountCheck?.has_expected_account && ethAccountCheck?.unlock_ok ? "green" : "orange"}>
                Account Ready: {ethAccountCheck?.has_expected_account && ethAccountCheck?.unlock_ok ? "YES" : "NO"}
              </Tag>
            </Space>
            {detailLoading ? (
              <div>Loading...</div>
            ) : (
              <>
                <div>Contract Address: {relayerDetail?.contract?.address || "-"}</div>
                <div>Threshold: {relayerDetail?.threshold ?? "-"}</div>
                <div>Relayers: {(relayerDetail?.relayers || []).join(", ") || "-"}</div>
                <div>FireFly Registered: {relayerDetail?.firefly?.registered ? "YES" : "NO"}</div>
                <div>FireFly API: {relayerDetail?.firefly?.api_name || "-"}</div>
                <div>FireFly Interface: {relayerDetail?.firefly?.interface_id || "-"}</div>
                <div>Relayer Node URL: {relayerNodeStatus?.node_url || relayerDetail?.node?.node_url || "-"}</div>
                <div>Relayer Node UI: {relayerNodeStatus?.ui_url || relayerDetail?.node?.ui_url || "-"}</div>
                <Space wrap>
                  <AntdButton
                    size="small"
                    loading={setupRelayerContractLoading}
                    onClick={handleSetUpRelayerContractOnly}
                    disabled={envInfo.chainlinkStatus !== "STARTED" || !!(relayerDetail?.contract?.address || ethRelayerContractAddress)}
                  >
                    Setup Relayer Contract
                  </AntdButton>
                  <AntdButton
                    size="small"
                    loading={setupRelayerFireflyLoading}
                    onClick={handleRegisterRelayerToFirefly}
                    disabled={envInfo.fireflyStatus !== "STARTED" || !(relayerDetail?.contract?.address || ethRelayerContractAddress) || !!relayerDetail?.firefly?.registered}
                  >
                    Register Relayer To FireFly
                  </AntdButton>
                  <AntdButton
                    size="small"
                    loading={relayerNodeActionLoading}
                    onClick={() => loadRelayerNodeStatus(false)}
                  >
                    Refresh Node
                  </AntdButton>
                  <AntdButton
                    size="small"
                    loading={relayerNodeActionLoading}
                    onClick={() => handleRelayerNodeControl("start")}
                  >
                    Start Node
                  </AntdButton>
                  <AntdButton
                    size="small"
                    loading={relayerNodeActionLoading}
                    onClick={() => handleRelayerNodeControl("stop")}
                  >
                    Stop Node
                  </AntdButton>
                </Space>
              </>
            )}
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
        {detailType === "Chainlink" ? (
          <Space direction="vertical" style={{ width: "100%" }}>
            <Tag color={(envInfo.chainlinkStatus === "STARTED") ? "green" : "red"}>
              Status: {envInfo.chainlinkStatus || "NO"}
            </Tag>
            <div>Chainlink 通过 directrequest Job 监听 Operator 合约并写回 DMN 请求合约。</div>
            <div>安装使用 lite 模式（无 OCR 聚合）。</div>
          </Space>
        ) : null}
        {detailType === "Account" ? (
          <Space direction="vertical" style={{ width: "100%" }}>
            <Tag color={ethAccountCheck?.has_expected_account && ethAccountCheck?.unlock_ok ? "green" : "orange"}>
              Status: {ethAccountCheck?.has_expected_account && ethAccountCheck?.unlock_ok ? "READY" : "NOT_READY"}
            </Tag>
            {detailLoading ? (
              <div>Loading...</div>
            ) : (
              <>
                <div>System Account: {ethAccountCheck?.expected_account || "-"}</div>
                <div>RPC URL: {ethAccountCheck?.rpc_url || "-"}</div>
                <div>Balance(wei): {ethAccountCheck?.balance_wei || "-"}</div>
                <div>Balance(eth): {formatWei(ethAccountCheck?.balance_wei)}</div>
                <div>Has Expected Account: {String(!!ethAccountCheck?.has_expected_account)}</div>
                <div>Unlock OK: {String(!!ethAccountCheck?.unlock_ok)}</div>
                {ethAccountCheck?.unlock_error ? (
                  <div style={{ color: "#dc2626" }}>Unlock Error: {ethAccountCheck.unlock_error}</div>
                ) : null}
                <AntdButton size="small" loading={ethAccountCheckLoading} onClick={() => loadEthAccountCheck(false)}>
                  Refresh Account Check
                </AntdButton>
              </>
            )}
          </Space>
        ) : null}
      </Modal>
    </>
  );
};

export default Overview;
