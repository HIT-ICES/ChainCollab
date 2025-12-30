import React, { useEffect, useState } from "react";
import { ethers } from "ethers";

const API_BASE = "";

const sections = [
  { id: "dashboard", label: "Dashboard" },
  { id: "identity", label: "Chain Identity" },
  { id: "watchers", label: "Watchers" },
  { id: "tasks", label: "Task Logs" },
  { id: "control", label: "Control Panel" },
  { id: "localchain", label: "Local Chain" }
];

export default function App() {
  const [active, setActive] = useState("dashboard");
  const [identities, setIdentities] = useState([]);
  const [watchers, setWatchers] = useState([]);
  const [logs, setLogs] = useState([]);
  const [selectedWatcher, setSelectedWatcher] = useState("");
  const [identityView, setIdentityView] = useState("overview");
  const [identityMode, setIdentityMode] = useState("create");
  const [identityDetail, setIdentityDetail] = useState(null);
  const [watcherView, setWatcherView] = useState("overview");
  const [watcherDetail, setWatcherDetail] = useState(null);
  const [taskView, setTaskView] = useState("overview");
  const [taskDetail, setTaskDetail] = useState(null);
  const [unifiedAbi, setUnifiedAbi] = useState(null);
  const [unifiedSource, setUnifiedSource] = useState("");
  const [localChainConfig, setLocalChainConfig] = useState(null);
  const [localChainAccounts, setLocalChainAccounts] = useState([]);
  const [showAccountPicker, setShowAccountPicker] = useState(false);
  const [control, setControl] = useState({
    rpc_url: "",
    private_key: "",
    contract_address: "",
    contract_bytecode: ""
  });
  const [controlOutput, setControlOutput] = useState("");
  const [controlPayload, setControlPayload] = useState(null);
  const [controlSigner, setControlSigner] = useState("local:0");
  const [showCustomKey, setShowCustomKey] = useState(false);
  const [oracleAddress, setOracleAddress] = useState("");
  const [controlTab, setControlTab] = useState("oracle");
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [dataTaskForm, setDataTaskForm] = useState({
    source_config: "",
    mode: "0",
    allowed_oracles: [],
    weights: {},
    min_responses: ""
  });
  const [computeTaskForm, setComputeTaskForm] = useState({
    compute_type: "",
    payload_hash: "",
    allowed_oracles: "",
    threshold: ""
  });
  const [submitDataForm, setSubmitDataForm] = useState({
    task_id: "",
    value: ""
  });
  const [submitComputeForm, setSubmitComputeForm] = useState({
    task_id: "",
    payload_hash: "",
    result: ""
  });
  const [queryForm, setQueryForm] = useState({
    data_task_id: "",
    compute_task_id: ""
  });
  const [notice, setNotice] = useState(null);

  const initialIdentityForm = {
    name: "",
    chain_type: "evm",
    rpc_url: "",
    private_key: "",
    address: "",
    notes: "",
    metadata: {
      connection_profile: "",
      wallet_path: "",
      identity: "",
      channel_name: "",
      chaincode_name: "",
      msp_id: ""
    }
  };
  const [identityForm, setIdentityForm] = useState(initialIdentityForm);
  const [watcherForm, setWatcherForm] = useState({
    name: "",
    chain_type: "evm",
    contract_address: "",
    identity_id: "",
    poll_interval: 5,
    compute_profiles: "{}"
  });

  useEffect(() => {
    refreshAll();
  }, []);

  useEffect(() => {
    if (active === "identity") {
      loadIdentities();
    }
    if (active === "watchers") {
      loadWatchers();
    }
    if (active === "control") {
      const saved = window.localStorage.getItem("oracle_control");
      if (saved) {
        try {
          setControl(JSON.parse(saved));
        } catch {
          // ignore
        }
      }
      fetchUnifiedContract();
      refreshLocalChain();
    }
    if (active === "localchain") {
      refreshLocalChain();
    }
  }, [active, identityView, watcherView]);

  async function refreshLocalChain() {
    try {
      const [cfgRes, accRes] = await Promise.all([
        fetch(`${API_BASE}/local-chain/config`),
        fetch(`${API_BASE}/local-chain/accounts`)
      ]);
      if (cfgRes.ok) {
        const cfg = await cfgRes.json();
        setLocalChainConfig(cfg);
        if (!control.rpc_url && cfg.rpc_url) {
          setControl((prev) => ({ ...prev, rpc_url: cfg.rpc_url }));
        }
      }
      if (accRes.ok) {
        const data = await accRes.json();
        setLocalChainAccounts(data.accounts || []);
      }
    } catch (err) {
      showNotice(String(err), "error");
    }
  }

  async function copyText(value) {
    try {
      await navigator.clipboard.writeText(value);
      showNotice("已复制。");
    } catch {
      showNotice("复制失败。", "error");
    }
  }

  async function fetchUnifiedContract() {
    try {
      const [abiRes, solRes] = await Promise.all([
        fetch(`${API_BASE}/contracts/unified/abi`),
        fetch(`${API_BASE}/contracts/unified/sol`)
      ]);
      if (abiRes.ok) {
        const abi = await abiRes.json();
        setUnifiedAbi(abi);
      }
      if (solRes.ok) {
        const sol = await solRes.text();
        setUnifiedSource(sol);
      }
    } catch {
      // ignore fetch errors
    }
  }

  async function fetchUnifiedBytecode() {
    try {
      const res = await fetch(`${API_BASE}/contracts/unified/bytecode`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        showNotice(err.detail || "failed to compile bytecode", "error");
        return null;
      }
      const data = await res.json();
      if (data.bytecode) {
        setControl((prev) => ({ ...prev, contract_bytecode: data.bytecode }));
        showNotice("Bytecode 已加载。");
        return data.bytecode;
      }
      return null;
    } catch (err) {
      showNotice(String(err), "error");
      return null;
    }
  }

  async function compileAndDeploy() {
    const bytecode = await fetchUnifiedBytecode();
    if (!bytecode) {
      return;
    }
    await handleDeployContract({ bytecode });
  }

  useEffect(() => {
    if (active !== "control" || !autoRefresh) {
      return undefined;
    }
    const timer = window.setInterval(() => {
      refreshContractState();
    }, 5000);
    return () => window.clearInterval(timer);
  }, [active, autoRefresh, control, queryForm]);

  async function refreshAll() {
    await Promise.all([loadIdentities(), loadWatchers()]);
    await loadLogs("");
  }

  async function loadIdentities() {
    const res = await fetch(`${API_BASE}/identities`);
    const data = await res.json();
    setIdentities(data);
    if (!watcherForm.identity_id && data.length > 0) {
      setWatcherForm((prev) => ({ ...prev, identity_id: data[0].id }));
    }
  }

  async function loadWatchers() {
    const res = await fetch(`${API_BASE}/compute-watchers`);
    const data = await res.json();
    setWatchers(data);
  }

  async function loadLogs(watcherId) {
    if (!watcherId) {
      const all = [];
      for (const w of watchers) {
        const res = await fetch(`${API_BASE}/compute-watchers/${w.id}/logs`);
        const data = await res.json();
        all.push(...data);
      }
      setLogs(all);
      return;
    }
    const res = await fetch(`${API_BASE}/compute-watchers/${watcherId}/logs`);
    const data = await res.json();
    setLogs(data);
  }

  function showNotice(text, type = "success") {
    setNotice({ text, type });
    window.clearTimeout(showNotice._t);
    showNotice._t = window.setTimeout(() => setNotice(null), 2600);
  }

  function closeNotice() {
    setNotice(null);
  }

  async function submitIdentity(e) {
    e.preventDefault();
    const payload = {
      name: identityForm.name,
      chain_type: identityForm.chain_type,
      address: identityForm.address,
      notes: identityForm.notes
    };
    if (identityForm.chain_type === "evm") {
      payload.rpc_url = identityForm.rpc_url;
      payload.private_key = identityForm.private_key;
    } else {
      payload.metadata = identityForm.metadata;
    }
    const url =
      identityMode === "edit" && identityDetail
        ? `${API_BASE}/identities/${identityDetail.id}`
        : `${API_BASE}/identities`;
    const method = identityMode === "edit" ? "PUT" : "POST";
    const res = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      let message = "保存失败，请检查字段或后端日志。";
      try {
        const err = await res.json();
        if (err && err.detail) {
          message = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
        }
      } catch {
        // ignore parse errors
      }
      showNotice(message, "error");
      return;
    }
    setIdentityForm(initialIdentityForm);
    setIdentityView("overview");
    setIdentityMode("create");
    setIdentityDetail(null);
    await loadIdentities();
    showNotice(identityMode === "edit" ? "Identity 已更新。" : "Identity 注册成功。");
  }

  async function loadIdentityDetail(id) {
    const res = await fetch(`${API_BASE}/identities/${id}`);
    if (!res.ok) {
      return;
    }
    const data = await res.json();
    setIdentityDetail(data);
  }

  function openRegister() {
    setIdentityMode("create");
    setIdentityForm(initialIdentityForm);
    setIdentityDetail(null);
    setIdentityView("register");
  }

  function openIdentityDetail(id) {
    loadIdentityDetail(id);
    setIdentityView("detail");
  }

  function openIdentityEdit() {
    if (!identityDetail) {
      return;
    }
    const metadata = identityDetail.metadata || {};
    setIdentityForm({
      name: identityDetail.name || "",
      chain_type: identityDetail.chain_type || "evm",
      rpc_url: identityDetail.rpc_url || "",
      private_key: identityDetail.private_key || "",
      address: identityDetail.address || "",
      notes: identityDetail.notes || "",
      metadata: {
        connection_profile: metadata.connection_profile || "",
        wallet_path: metadata.wallet_path || "",
        identity: metadata.identity || "",
        channel_name: metadata.channel_name || "",
        chaincode_name: metadata.chaincode_name || "",
        msp_id: metadata.msp_id || ""
      }
    });
    setIdentityMode("edit");
    setIdentityView("register");
  }

  async function deleteIdentity() {
    if (!identityDetail) {
      return;
    }
    if (!window.confirm(`Delete identity ${identityDetail.name}?`)) {
      return;
    }
    const res = await fetch(`${API_BASE}/identities/${identityDetail.id}`, { method: "DELETE" });
    if (!res.ok) {
      let message = "删除失败，请检查后端日志。";
      try {
        const err = await res.json();
        if (err && err.detail) {
          message = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
        }
      } catch {
        // ignore parse errors
      }
      showNotice(message, "error");
      return;
    }
    setIdentityDetail(null);
    setIdentityView("overview");
    await loadIdentities();
    showNotice("Identity 已删除。");
  }

  function openWatcherRegister() {
    setWatcherForm({
      name: "",
      chain_type: "evm",
      contract_address: "",
      identity_id: identities.length > 0 ? identities[0].id : "",
      poll_interval: 5,
      compute_profiles: "{}"
    });
    setWatcherDetail(null);
    setWatcherView("register");
  }

  function openWatcherDetail(watcher) {
    setWatcherDetail(watcher);
    setWatcherView("detail");
  }

  function openTaskDetail(log) {
    setTaskDetail(log);
    setTaskView("detail");
  }

  function getWatcherName(watcherId) {
    const item = watchers.find((w) => w.id === watcherId);
    return item ? item.name : watcherId;
  }

  function saveControlConfig() {
    window.localStorage.setItem("oracle_control", JSON.stringify(control));
    showNotice("已保存区块链配置。");
  }

  function ensureControlReady() {
    if (!control.rpc_url || !control.private_key || !control.contract_address) {
      showNotice("请先填写 RPC / Private Key / Contract Address。", "error");
      return false;
    }
    return true;
  }

  function toBytes32(input) {
    if (!input) {
      return ethers.ZeroHash;
    }
    if (input.startsWith("0x") && input.length === 66) {
      return input;
    }
    if (input.length <= 31) {
      return ethers.encodeBytes32String(input);
    }
    return ethers.keccak256(ethers.toUtf8Bytes(input));
  }

  function parseAddressList(raw) {
    return raw
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function parseNumberList(raw) {
    if (!raw) {
      return [];
    }
    return raw
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean)
      .map((item) => Number(item));
  }

  function getContract() {
    const provider = new ethers.JsonRpcProvider(control.rpc_url);
    const signerKey = resolveSignerKey() || control.private_key;
    const wallet = new ethers.Wallet(signerKey, provider);
    const fallbackAbi = [
      "function registerOracle(address oracle)",
      "function removeOracle(address oracle)",
      "function registerDataTask(string sourceConfig,uint8 mode,address[] allowedOracles,uint256[] weights,uint256 minResponses) returns (uint256)",
      "function registerComputeTask(bytes32 computeType,bytes32 payloadHash,address[] allowedOracles,uint256 threshold) returns (uint256)",
      "function submitData(uint256 taskId,uint256 value,bytes signature)",
      "function submitComputeResult(uint256 taskId,bytes32 result,bytes signature)",
      "function getDataTask(uint256 taskId) view returns (address,bytes32,uint8,uint256,bool,uint256,uint256)",
      "function getDataSourceConfig(uint256 taskId) view returns (string)",
      "function getDataTaskSummary(uint256 taskId) view returns (bytes32,uint8,bool,uint256,uint256,uint256)",
      "function getComputeTask(uint256 taskId) view returns (address,bytes32,bytes32,uint256,bool,bytes32)",
      "function getComputeTaskSummary(uint256 taskId) view returns (bytes32,bytes32,bool,bytes32,uint256,uint256)",
      "function nextDataTaskId() view returns (uint256)",
      "function nextComputeTaskId() view returns (uint256)",
      "function getAllDataTaskIds() view returns (uint256[])",
      "function getAllComputeTaskIds() view returns (uint256[])",
      "function getHealth() view returns (address,uint256,uint256,uint256,uint256)",
      "function getCounts() view returns (uint256,uint256,uint256)",
      "function isOracleActive(address) view returns (bool)",
      "function oracleCount() view returns (uint256)"
    ];
    const abi = unifiedAbi || fallbackAbi;
    const contract = new ethers.Contract(control.contract_address, abi, wallet);
    return { provider, wallet, contract, abi };
  }

  function serializeValue(value) {
    if (typeof value === "bigint") {
      return value.toString();
    }
    if (Array.isArray(value)) {
      return value.map((item) => serializeValue(item));
    }
    if (value && typeof value === "object") {
      const out = {};
      for (const [key, item] of Object.entries(value)) {
        out[key] = serializeValue(item);
      }
      return out;
    }
    return value;
  }

  function setOutput(payload, title = "Result") {
    setControlPayload({ title, payload });
    setControlOutput(JSON.stringify(payload, null, 2));
  }

  async function handleDeployContract(options = {}) {
    const rpcUrl = options.rpc_url || control.rpc_url;
    const privateKey = options.private_key || resolveSignerKey() || control.private_key;
    const bytecode = options.bytecode || control.contract_bytecode;
    if (!rpcUrl || !privateKey) {
      showNotice("请先填写 RPC 与 Private Key。", "error");
      return;
    }
    if (!bytecode) {
      showNotice("请先填写合约 Bytecode。", "error");
      return;
    }
    try {
      const provider = new ethers.JsonRpcProvider(rpcUrl);
      const wallet = new ethers.Wallet(privateKey, provider);
      const { abi } = getContract();
      const factory = new ethers.ContractFactory(abi, bytecode, wallet);
      const contract = await factory.deploy();
      await contract.deploymentTransaction().wait();
      setControl((prev) => ({
        ...prev,
        rpc_url: rpcUrl,
        private_key: privateKey,
        contract_bytecode: bytecode,
        contract_address: contract.target
      }));
      showNotice("合约已部署，地址已写入。");
    } catch (err) {
      showNotice(String(err), "error");
    }
  }

  async function refreshContractState() {
    if (!ensureControlReady()) {
      return;
    }
    try {
      const { contract } = getContract();
      const nextDataTaskId = await contract.nextDataTaskId();
      const nextComputeTaskId = await contract.nextComputeTaskId();
      const payload = {
        nextDataTaskId: Number(nextDataTaskId),
        nextComputeTaskId: Number(nextComputeTaskId)
      };
      if (queryForm.data_task_id !== "") {
        const dataTask = await contract.getDataTask(Number(queryForm.data_task_id));
        payload.dataTask = serializeValue(dataTask);
      }
      if (queryForm.compute_task_id !== "") {
        const computeTask = await contract.getComputeTask(Number(queryForm.compute_task_id));
        payload.computeTask = serializeValue(computeTask);
      }
      setOutput(serializeValue(payload), "Contract State");
    } catch (err) {
      showNotice(String(err), "error");
    }
  }

  async function handleRegisterOracle() {
    if (!ensureControlReady()) {
      return;
    }
    try {
      const { contract } = getContract();
      const tx = await contract.registerOracle(oracleAddress);
      const receipt = await tx.wait();
      setOutput({ txHash: receipt.hash }, "Transaction");
      showNotice("Oracle 已注册。");
    } catch (err) {
      showNotice(String(err), "error");
    }
  }

  async function handleRemoveOracle() {
    if (!ensureControlReady()) {
      return;
    }
    try {
      const { contract } = getContract();
      const tx = await contract.removeOracle(oracleAddress);
      const receipt = await tx.wait();
      setOutput({ txHash: receipt.hash }, "Transaction");
      showNotice("Oracle 已移除。");
    } catch (err) {
      showNotice(String(err), "error");
    }
  }

  async function handleRegisterDataTask() {
    if (!ensureControlReady()) {
      return;
    }
    try {
      const { contract } = getContract();
      const allowed = dataTaskForm.allowed_oracles;
      const weights =
        Number(dataTaskForm.mode) === 2
          ? allowed.map((addr) => Number(dataTaskForm.weights[addr] || 0))
          : [];
      const tx = await contract.registerDataTask(
        dataTaskForm.source_config,
        Number(dataTaskForm.mode),
        allowed,
        weights,
        Number(dataTaskForm.min_responses || 0)
      );
      const receipt = await tx.wait();
      setOutput({ txHash: receipt.hash }, "Transaction");
      showNotice("DataTask 已注册。");
    } catch (err) {
      showNotice(String(err), "error");
    }
  }

  async function handleRegisterComputeTask() {
    if (!ensureControlReady()) {
      return;
    }
    try {
      const { contract } = getContract();
      const allowed = parseAddressList(computeTaskForm.allowed_oracles);
      const tx = await contract.registerComputeTask(
        toBytes32(computeTaskForm.compute_type),
        toBytes32(computeTaskForm.payload_hash),
        allowed,
        Number(computeTaskForm.threshold || 0)
      );
      const receipt = await tx.wait();
      setOutput({ txHash: receipt.hash }, "Transaction");
      showNotice("ComputeTask 已注册。");
    } catch (err) {
      showNotice(String(err), "error");
    }
  }

  async function handleSubmitData() {
    if (!ensureControlReady()) {
      return;
    }
    try {
      const { contract, wallet } = getContract();
      const taskId = Number(submitDataForm.task_id);
      const value = Number(submitDataForm.value);
      const digest = ethers.solidityPackedKeccak256(["uint256", "uint256"], [taskId, value]);
      const signature = await wallet.signMessage(ethers.getBytes(digest));
      const tx = await contract.submitData(taskId, value, signature);
      const receipt = await tx.wait();
      setOutput({ txHash: receipt.hash }, "Transaction");
      showNotice("Data 已提交。");
    } catch (err) {
      showNotice(String(err), "error");
    }
  }

  async function handleSubmitCompute() {
    if (!ensureControlReady()) {
      return;
    }
    try {
      const { contract, wallet } = getContract();
      const taskId = Number(submitComputeForm.task_id);
      const payloadHash = toBytes32(submitComputeForm.payload_hash);
      const result = toBytes32(submitComputeForm.result);
      const digest = ethers.solidityPackedKeccak256(
        ["uint256", "bytes32", "bytes32"],
        [taskId, payloadHash, result]
      );
      const signature = await wallet.signMessage(ethers.getBytes(digest));
      const tx = await contract.submitComputeResult(taskId, result, signature);
      const receipt = await tx.wait();
      setOutput({ txHash: receipt.hash }, "Transaction");
      showNotice("Compute 结果已提交。");
    } catch (err) {
      showNotice(String(err), "error");
    }
  }

  async function handleQueryDataTask() {
    if (!ensureControlReady()) {
      return;
    }
    try {
      const { contract } = getContract();
      const taskId = Number(queryForm.data_task_id);
      const result = await contract.getDataTask(taskId);
      const sourceConfig = await contract.getDataSourceConfig(taskId);
      setOutput({ taskId, result: serializeValue(result), sourceConfig }, "Data Task");
    } catch (err) {
      showNotice(String(err), "error");
    }
  }

  async function handleQueryComputeTask() {
    if (!ensureControlReady()) {
      return;
    }
    try {
      const { contract } = getContract();
      const taskId = Number(queryForm.compute_task_id);
      const result = await contract.getComputeTask(taskId);
      setOutput({ taskId, result: serializeValue(result) }, "Compute Task");
    } catch (err) {
      showNotice(String(err), "error");
    }
  }

  async function handleQueryHealth() {
    if (!ensureControlReady()) {
      return;
    }
    try {
      const { contract } = getContract();
      const result = await contract.getHealth();
      setOutput({ health: serializeValue(result) }, "Health");
    } catch (err) {
      showNotice(String(err), "error");
    }
  }

  async function handleListDataTasks() {
    if (!ensureControlReady()) {
      return;
    }
    try {
      const { contract } = getContract();
      const ids = await contract.getAllDataTaskIds();
      const summaries = [];
      for (const id of ids) {
        const summary = await contract.getDataTaskSummary(Number(id));
        summaries.push({ taskId: Number(id), summary: serializeValue(summary) });
      }
      setOutput({ dataTasks: summaries }, "Data Tasks");
    } catch (err) {
      showNotice(String(err), "error");
    }
  }

  async function handleListComputeTasks() {
    if (!ensureControlReady()) {
      return;
    }
    try {
      const { contract } = getContract();
      const ids = await contract.getAllComputeTaskIds();
      const summaries = [];
      for (const id of ids) {
        const summary = await contract.getComputeTaskSummary(Number(id));
        summaries.push({ taskId: Number(id), summary: serializeValue(summary) });
      }
      setOutput({ computeTasks: summaries }, "Compute Tasks");
    } catch (err) {
      showNotice(String(err), "error");
    }
  }

  async function handleQuickDeploy() {
    try {
      const res = await fetch(`${API_BASE}/local-chain/accounts`);
      if (!res.ok) {
        showNotice("无法获取本地链账户。", "error");
        return;
      }
      const data = await res.json();
      setLocalChainConfig((prev) => prev || { rpc_url: data.rpc_url });
      setLocalChainAccounts(data.accounts || []);
      setShowAccountPicker(true);
    } catch (err) {
      showNotice(String(err), "error");
    }
  }

  async function deployWithAccount(account) {
    try {
      const rpcUrl = localChainConfig?.rpc_url || control.rpc_url;
      if (!rpcUrl) {
        showNotice("缺少 RPC URL。", "error");
        return;
      }
      const rawKey = account.private_key || "";
      const privateKey = rawKey.startsWith("0x") ? rawKey : `0x${rawKey}`;
      const bytecode = await fetchUnifiedBytecode();
      if (!bytecode) {
        return;
      }
      await handleDeployContract({ rpc_url: rpcUrl, private_key: privateKey, bytecode });
      setShowAccountPicker(false);
    } catch (err) {
      showNotice(String(err), "error");
    }
  }

  function resolveSignerKey() {
    if (showCustomKey) {
      return control.private_key;
    }
    const [scope, idxStr] = controlSigner.split(":");
    if (scope !== "local") {
      return control.private_key;
    }
    const idx = Number(idxStr);
    const acct = localChainAccounts.find((item) => item.index === idx);
    if (!acct) {
      return "";
    }
    const rawKey = acct.private_key || "";
    return rawKey.startsWith("0x") ? rawKey : `0x${rawKey}`;
  }

  function resolveSignerAddress() {
    const [scope, idxStr] = controlSigner.split(":");
    if (scope !== "local") {
      return "";
    }
    const idx = Number(idxStr);
    const acct = localChainAccounts.find((item) => item.index === idx);
    return acct ? acct.address : "";
  }

  function updateIdentityMetadata(key, value) {
    setIdentityForm((prev) => ({
      ...prev,
      metadata: {
        ...prev.metadata,
        [key]: value
      }
    }));
  }

  async function submitWatcher(e) {
    e.preventDefault();
    const payload = {
      name: watcherForm.name,
      chain_type: watcherForm.chain_type,
      contract_address: watcherForm.contract_address,
      identity_id: watcherForm.identity_id,
      poll_interval: parseInt(watcherForm.poll_interval, 10),
      compute_profiles: JSON.parse(watcherForm.compute_profiles || "{}")
    };
    const res = await fetch(`${API_BASE}/compute-watchers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      let message = "保存失败，请检查字段或后端日志。";
      try {
        const err = await res.json();
        if (err && err.detail) {
          message = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
        }
      } catch {
        // ignore parse errors
      }
      showNotice(message, "error");
      return;
    }
    setWatcherForm({ name: "", chain_type: "evm", contract_address: "", identity_id: watcherForm.identity_id, poll_interval: 5, compute_profiles: "{}" });
    setWatcherView("overview");
    await loadWatchers();
    showNotice("Watcher 注册成功。");
  }

  async function startWatcher(id) {
    await fetch(`${API_BASE}/compute-watchers/${id}/start`, { method: "POST" });
    await loadWatchers();
  }

  async function stopWatcher(id) {
    await fetch(`${API_BASE}/compute-watchers/${id}/stop`, { method: "POST" });
    await loadWatchers();
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          <div className="logo">ORACLE</div>
          <div className="subtitle">Control Plane</div>
        </div>
        <nav>
          {sections.map((s) => (
            <button
              key={s.id}
              className={active === s.id ? "nav active" : "nav"}
              onClick={() => setActive(s.id)}
            >
              {s.label}
            </button>
          ))}
        </nav>
        <div className="status">
          <div className="status-label">Watchers</div>
          <div className="status-value">{watchers.length}</div>
        </div>
      </aside>
      <main>
        {notice && (
          <div className="modal-backdrop" onClick={closeNotice}>
            <div
              className={notice.type === "error" ? "modal error" : "modal"}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="modal-title">{notice.type === "error" ? "失败" : "成功"}</div>
              <div className="modal-body">{notice.text}</div>
              <div className="actions">
                <button onClick={closeNotice}>OK</button>
              </div>
            </div>
          </div>
        )}
        {showAccountPicker && (
          <div className="modal-backdrop" onClick={() => setShowAccountPicker(false)}>
            <div className="modal" onClick={(e) => e.stopPropagation()}>
              <div className="modal-title">Select Local Account</div>
              <div className="list-stack scroll-list">
                {localChainAccounts.map((acct) => (
                  <div className="list-card" key={`pick-${acct.index}`}>
                    <div className="list-title">#{acct.index} {acct.address}</div>
                    <div className="muted">{acct.path}</div>
                    <div className="actions">
                      <button onClick={() => deployWithAccount(acct)}>Deploy</button>
                    </div>
                  </div>
                ))}
              </div>
              <div className="actions">
                <button className="secondary" onClick={() => setShowAccountPicker(false)}>Cancel</button>
              </div>
            </div>
          </div>
        )}
        {active === "dashboard" && (
          <section>
            <h1>Dashboard</h1>
            <div className="grid">
              <div className="card">
                <div className="label">Watchers</div>
                <div className="value">{watchers.length}</div>
              </div>
              <div className="card">
                <div className="label">Identities</div>
                <div className="value">{identities.length}</div>
              </div>
              <div className="card">
                <div className="label">Task Logs</div>
                <div className="value">{logs.length}</div>
              </div>
            </div>
            <div className="card large">
              <h3>Active Watchers</h3>
              <ul>
                {watchers.map((w) => (
                  <li key={w.id}>
                    {w.name} <span className={w.enabled ? "pill ok" : "pill"}>{w.enabled ? "RUNNING" : "STOPPED"}</span>
                    <span className="muted"> {w.contract_address}</span>
                  </li>
                ))}
              </ul>
            </div>
          </section>
        )}

        {active === "identity" && (
          <section>
            <h1>Chain Identity</h1>

            {identityView === "overview" && (
              <>
                <div className="card header">
                  <h3>Configured Identities</h3>
                  <button onClick={openRegister}>Register</button>
                </div>
                <div className="card large">
                  <ul>
                    {identities.map((idn) => (
                      <li key={idn.id}>
                        <div className="list-row">
                          <div>
                            <div className="list-title">{idn.name}</div>
                            <div className="muted">{idn.chain_type} {idn.rpc_url}</div>
                          </div>
                          <div className="actions">
                            <button className="secondary" onClick={() => openIdentityDetail(idn.id)}>
                              Detail
                            </button>
                          </div>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              </>
            )}

            {identityView === "detail" && identityDetail && (
              <div className="card large">
                <div className="detail-header">
                  <div>
                    <h3>{identityDetail.name}</h3>
                    <div className="muted">{identityDetail.chain_type}</div>
                  </div>
                  <div className="actions">
                    <button onClick={openIdentityEdit}>Edit</button>
                    <button className="secondary" onClick={deleteIdentity}>Delete</button>
                  </div>
                </div>
                {identityDetail.chain_type === "evm" && (
                  <div className="detail-grid">
                    <div>
                      <div className="label">RPC URL</div>
                      <div>{identityDetail.rpc_url}</div>
                    </div>
                    <div>
                      <div className="label">Address</div>
                      <div>{identityDetail.address || "-"}</div>
                    </div>
                    <div>
                      <div className="label">Private Key</div>
                      <div className="muted">********</div>
                    </div>
                  </div>
                )}
                {identityDetail.chain_type === "fabric" && (
                  <div className="detail-grid">
                    <div>
                      <div className="label">Connection Profile</div>
                      <div>{identityDetail.metadata?.connection_profile || "-"}</div>
                    </div>
                    <div>
                      <div className="label">Wallet Path</div>
                      <div>{identityDetail.metadata?.wallet_path || "-"}</div>
                    </div>
                    <div>
                      <div className="label">Identity</div>
                      <div>{identityDetail.metadata?.identity || "-"}</div>
                    </div>
                    <div>
                      <div className="label">Channel</div>
                      <div>{identityDetail.metadata?.channel_name || "-"}</div>
                    </div>
                    <div>
                      <div className="label">Chaincode</div>
                      <div>{identityDetail.metadata?.chaincode_name || "-"}</div>
                    </div>
                    <div>
                      <div className="label">MSP ID</div>
                      <div>{identityDetail.metadata?.msp_id || "-"}</div>
                    </div>
                  </div>
                )}
                {identityDetail.notes && (
                  <div className="detail-notes">
                    <div className="label">Notes</div>
                    <div>{identityDetail.notes}</div>
                  </div>
                )}
              </div>
            )}

            {identityView === "register" && (
              <form className="card centered" onSubmit={submitIdentity}>
                <h3>{identityMode === "edit" ? "Edit Identity" : "Register Identity"}</h3>
                <div className="field">
                  <label>Name</label>
                  <input
                    value={identityForm.name}
                    onChange={(e) => setIdentityForm({ ...identityForm, name: e.target.value })}
                  />
                </div>
                <div className="field">
                  <label>Chain Type</label>
                  <select
                    value={identityForm.chain_type}
                    onChange={(e) => setIdentityForm({ ...identityForm, chain_type: e.target.value })}
                  >
                    <option value="evm">Solidity / EVM</option>
                    <option value="fabric">Fabric</option>
                  </select>
                </div>
                {identityForm.chain_type === "evm" && (
                  <>
                    <div className="field">
                      <label>RPC URL</label>
                      <input
                        value={identityForm.rpc_url}
                        onChange={(e) => setIdentityForm({ ...identityForm, rpc_url: e.target.value })}
                      />
                    </div>
                    <div className="field">
                      <label>Private Key</label>
                      <input
                        value={identityForm.private_key}
                        onChange={(e) => setIdentityForm({ ...identityForm, private_key: e.target.value })}
                      />
                    </div>
                    <div className="field">
                      <label>Address (optional)</label>
                      <input
                        value={identityForm.address}
                        onChange={(e) => setIdentityForm({ ...identityForm, address: e.target.value })}
                      />
                    </div>
                  </>
                )}
                {identityForm.chain_type === "fabric" && (
                  <>
                    <div className="field">
                      <label>Connection Profile</label>
                      <input
                        value={identityForm.metadata.connection_profile}
                        onChange={(e) => updateIdentityMetadata("connection_profile", e.target.value)}
                      />
                    </div>
                    <div className="field">
                      <label>Wallet Path</label>
                      <input
                        value={identityForm.metadata.wallet_path}
                        onChange={(e) => updateIdentityMetadata("wallet_path", e.target.value)}
                      />
                    </div>
                    <div className="field">
                      <label>Identity</label>
                      <input
                        value={identityForm.metadata.identity}
                        onChange={(e) => updateIdentityMetadata("identity", e.target.value)}
                      />
                    </div>
                    <div className="field">
                      <label>Channel Name</label>
                      <input
                        value={identityForm.metadata.channel_name}
                        onChange={(e) => updateIdentityMetadata("channel_name", e.target.value)}
                      />
                    </div>
                    <div className="field">
                      <label>Chaincode Name</label>
                      <input
                        value={identityForm.metadata.chaincode_name}
                        onChange={(e) => updateIdentityMetadata("chaincode_name", e.target.value)}
                      />
                    </div>
                    <div className="field">
                      <label>MSP ID</label>
                      <input
                        value={identityForm.metadata.msp_id}
                        onChange={(e) => updateIdentityMetadata("msp_id", e.target.value)}
                      />
                    </div>
                  </>
                )}
                <div className="field">
                  <label>Notes</label>
                  <textarea
                    value={identityForm.notes}
                    onChange={(e) => setIdentityForm({ ...identityForm, notes: e.target.value })}
                  />
                </div>
                <div className="actions">
                  <button type="submit">Save</button>
                  <button
                    className="secondary"
                    type="button"
                    onClick={() => {
                      setIdentityView(identityDetail ? "detail" : "overview");
                      setIdentityMode("create");
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </form>
            )}
          </section>
        )}

        {active === "watchers" && (
          <section>
            <h1>Watchers</h1>

            {watcherView === "overview" && (
              <>
                <div className="card header">
                  <h3>Current Watchers</h3>
                  <button onClick={openWatcherRegister}>Add Watcher</button>
                </div>
                <div className="card large">
                  <ul>
                    {watchers.map((w) => (
                      <li key={w.id}>
                        <div className="list-row">
                          <div>
                            <div className="list-title">{w.name}</div>
                            <div className="muted">{w.contract_address}</div>
                          </div>
                          <div className="actions">
                            <button className="secondary" onClick={() => openWatcherDetail(w)}>
                              Detail
                            </button>
                          </div>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              </>
            )}

            {watcherView === "detail" && watcherDetail && (
              <div className="card large">
                <div className="detail-header">
                  <div>
                    <h3>{watcherDetail.name}</h3>
                    <div className="muted">{watcherDetail.contract_address}</div>
                  </div>
                  <div className="actions">
                    <button onClick={() => startWatcher(watcherDetail.id)}>Start</button>
                    <button className="secondary" onClick={() => stopWatcher(watcherDetail.id)}>Stop</button>
                  </div>
                </div>
                <div className="detail-grid">
                  <div>
                    <div className="label">Chain Type</div>
                    <div>{watcherDetail.chain_type}</div>
                  </div>
                  <div>
                    <div className="label">Identity ID</div>
                    <div>{watcherDetail.identity_id}</div>
                  </div>
                  <div>
                    <div className="label">Poll Interval</div>
                    <div>{watcherDetail.poll_interval}s</div>
                  </div>
                  <div>
                    <div className="label">Status</div>
                    <div className={watcherDetail.enabled ? "pill ok" : "pill"}>
                      {watcherDetail.enabled ? "RUNNING" : "STOPPED"}
                    </div>
                  </div>
                </div>
                <div className="card nested">
                  <div className="header-row">
                    <h4>Related Tasks</h4>
                    <button className="secondary" onClick={() => loadLogs(watcherDetail.id)}>Refresh</button>
                  </div>
                  <ul>
                    {logs
                      .filter((log) => log.watcher_id === watcherDetail.id)
                      .slice(-50)
                      .map((log, idx) => (
                        <li key={`${log.id}-${idx}`}>
                          <div className="list-row">
                            <div>
                              <div className="list-title">Task #{log.task_id}</div>
                              <div className="muted">{log.compute_type}</div>
                            </div>
                            <div className="actions">
                              <button className="secondary" onClick={() => openTaskDetail(log)}>
                                Detail
                              </button>
                            </div>
                          </div>
                        </li>
                      ))}
                  </ul>
                </div>
              </div>
            )}

            {watcherView === "register" && (
              <form className="card centered" onSubmit={submitWatcher}>
                <div className="field">
                  <label>Name</label>
                  <input value={watcherForm.name} onChange={(e) => setWatcherForm({ ...watcherForm, name: e.target.value })} />
                </div>
                <div className="field">
                  <label>Chain Type</label>
                  <select
                    value={watcherForm.chain_type}
                    onChange={(e) => setWatcherForm({ ...watcherForm, chain_type: e.target.value })}
                  >
                    <option value="evm">Solidity / EVM</option>
                    <option value="fabric">Fabric</option>
                  </select>
                </div>
                <div className="field">
                  <label>Contract Address</label>
                  <input value={watcherForm.contract_address} onChange={(e) => setWatcherForm({ ...watcherForm, contract_address: e.target.value })} />
                </div>
                <div className="field">
                  <label>Chain Identity</label>
                  <select
                    value={watcherForm.identity_id}
                    onChange={(e) => setWatcherForm({ ...watcherForm, identity_id: e.target.value })}
                  >
                    {identities.map((idn) => (
                      <option key={idn.id} value={idn.id}>{idn.name}</option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label>Poll Interval (sec)</label>
                  <input value={watcherForm.poll_interval} onChange={(e) => setWatcherForm({ ...watcherForm, poll_interval: e.target.value })} />
                </div>
                <div className="field">
                  <label>Compute Profiles (JSON)</label>
                  <textarea value={watcherForm.compute_profiles} onChange={(e) => setWatcherForm({ ...watcherForm, compute_profiles: e.target.value })} />
                </div>
                <div className="actions">
                  <button type="submit">Save</button>
                  <button className="secondary" type="button" onClick={() => setWatcherView("overview")}>Cancel</button>
                </div>
              </form>
            )}
          </section>
        )}

        {active === "tasks" && (
          <section>
            <h1>Task Logs</h1>
            {taskView === "overview" && (
              <>
                <div className="card">
                  <label>Filter by Watcher</label>
                  <select value={selectedWatcher} onChange={(e) => setSelectedWatcher(e.target.value)}>
                    <option value="">All Watchers</option>
                    {watchers.map((w) => (
                      <option key={w.id} value={w.id}>{w.name}</option>
                    ))}
                  </select>
                  <div className="actions">
                    <button onClick={() => loadLogs(selectedWatcher)}>Refresh</button>
                  </div>
                </div>
                <div className="card large">
                  <ul>
                    {logs.slice(-80).map((log, idx) => (
                      <li key={`${log.id}-${idx}`}>
                        <div className="list-row">
                          <div>
                            <div className="list-title">Task #{log.task_id}</div>
                            <div className="muted">{getWatcherName(log.watcher_id)}</div>
                            <div className="muted">{log.compute_type}</div>
                          </div>
                          <div className="actions">
                            <button className="secondary" onClick={() => openTaskDetail(log)}>
                              Detail
                            </button>
                          </div>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              </>
            )}
            {taskView === "detail" && taskDetail && (
              <div className="card large">
                <div className="detail-header">
                  <div>
                    <h3>Task #{taskDetail.task_id}</h3>
                    <div className="muted">{taskDetail.compute_type}</div>
                  </div>
                  <div className="actions">
                    <button className="secondary" onClick={() => setTaskView("overview")}>Back</button>
                  </div>
                </div>
                <div className="detail-grid">
                  <div>
                    <div className="label">Watcher</div>
                    <div>{getWatcherName(taskDetail.watcher_id)}</div>
                  </div>
                  <div>
                    <div className="label">Status</div>
                    <div className="pill">{taskDetail.status}</div>
                  </div>
                  <div>
                    <div className="label">Payload Hash</div>
                    <div className="muted">{taskDetail.payload_hash}</div>
                  </div>
                  <div>
                    <div className="label">Result</div>
                    <div className="muted">{taskDetail.result}</div>
                  </div>
                </div>
                {taskDetail.error && (
                  <div className="detail-notes">
                    <div className="label">Error</div>
                    <div className="muted">{taskDetail.error}</div>
                  </div>
                )}
              </div>
            )}
          </section>
        )}

        {active === "control" && (
          <section>
            <h1>Control Panel</h1>
            <div className="control-bar">
              <div className="control-bar-title">Connection</div>
              <div className="control-bar-fields">
                <div className="field">
                  <label>RPC URL</label>
                  <input
                    value={control.rpc_url}
                    onChange={(e) => setControl({ ...control, rpc_url: e.target.value })}
                  />
                </div>
                <div className="field">
                  <label>Contract Address</label>
                  <input
                    value={control.contract_address}
                    onChange={(e) => setControl({ ...control, contract_address: e.target.value })}
                  />
                </div>
                <div className="field">
                  <label>Deployed</label>
                  <div className="muted">{control.contract_address || "-"}</div>
                </div>
              </div>
              <div className="actions">
                <button onClick={saveControlConfig}>Save</button>
                <button className="secondary" onClick={compileAndDeploy}>Compile + Deploy</button>
                <button className="secondary" onClick={handleQuickDeploy}>Quick Deploy</button>
              </div>
            </div>

            <div className="card">
              <div className="header-row">
                <h3>Signer Account</h3>
                <div className="actions">
                  <button className="secondary" onClick={refreshLocalChain}>Reload Accounts</button>
                </div>
              </div>
              <div className="detail-grid">
                <div className="field">
                  <label>Account</label>
                  <select
                    value={controlSigner}
                    onChange={(e) => {
                      const value = e.target.value;
                      setControlSigner(value);
                      setShowCustomKey(value === "custom");
                    }}
                  >
                    {localChainAccounts.map((acct) => (
                      <option key={`local-${acct.index}`} value={`local:${acct.index}`}>
                        Local #{acct.index} {acct.address}
                      </option>
                    ))}
                    <option value="custom">Custom Private Key</option>
                  </select>
                </div>
                {showCustomKey && (
                  <div className="field">
                    <label>Private Key</label>
                    <input
                      value={control.private_key}
                      onChange={(e) => setControl({ ...control, private_key: e.target.value })}
                    />
                  </div>
                )}
                <div>
                  <div className="label">Selected Address</div>
                  <div className="muted">{resolveSignerAddress() || "-"}</div>
                </div>
              </div>
            </div>

            <div className="control-tabs">
              <button
                className={controlTab === "oracle" ? "subnav-btn active" : "subnav-btn"}
                onClick={() => setControlTab("oracle")}
              >
                Oracle
              </button>
              <button
                className={controlTab === "data" ? "subnav-btn active" : "subnav-btn"}
                onClick={() => setControlTab("data")}
              >
                Data Task
              </button>
              <button
                className={controlTab === "compute" ? "subnav-btn active" : "subnav-btn"}
                onClick={() => setControlTab("compute")}
              >
                Compute Task
              </button>
              <button
                className={controlTab === "submit" ? "subnav-btn active" : "subnav-btn"}
                onClick={() => setControlTab("submit")}
              >
                Submit
              </button>
              <button
                className={controlTab === "query" ? "subnav-btn active" : "subnav-btn"}
                onClick={() => setControlTab("query")}
              >
                Query
              </button>
            </div>

            <div className="control-grid">
              <div className="card">
                {controlTab === "oracle" && (
                  <>
                    <h3>Oracle Registry</h3>
                    <div className="field">
                      <label>Oracle Address</label>
                      <input
                        value={oracleAddress}
                        onChange={(e) => setOracleAddress(e.target.value)}
                      />
                    </div>
                    <div className="actions">
                      <button onClick={handleRegisterOracle}>Register</button>
                      <button className="secondary" onClick={handleRemoveOracle}>Remove</button>
                    </div>
                  </>
                )}
                {controlTab === "data" && (
                  <>
                    <h3>Register Data Task</h3>
                    <div className="field">
                      <label>Source Config (JSON)</label>
                      <textarea
                        rows="6"
                        value={dataTaskForm.source_config}
                        onChange={(e) => setDataTaskForm({ ...dataTaskForm, source_config: e.target.value })}
                      />
                    </div>
                    <div className="field">
                      <label>Mode</label>
                      <select
                        value={dataTaskForm.mode}
                        onChange={(e) => setDataTaskForm({ ...dataTaskForm, mode: e.target.value })}
                      >
                        <option value="0">MEAN</option>
                        <option value="1">MEDIAN</option>
                        <option value="2">WEIGHTED_MEAN</option>
                      </select>
                    </div>
                    <div className="field">
                      <label>Allowed Oracles</label>
                      <div className="check-grid">
                        {localChainAccounts.length === 0 && (
                          <div className="muted">No local accounts loaded.</div>
                        )}
                        {localChainAccounts.map((acct) => (
                          <label className="check-item" key={`oracle-${acct.index}`}>
                            <input
                              type="checkbox"
                              checked={dataTaskForm.allowed_oracles.includes(acct.address)}
                              onChange={(e) => {
                                const checked = e.target.checked;
                                setDataTaskForm((prev) => {
                                  const next = checked
                                    ? [...prev.allowed_oracles, acct.address]
                                    : prev.allowed_oracles.filter((addr) => addr !== acct.address);
                                  return { ...prev, allowed_oracles: next };
                                });
                              }}
                            />
                            <span className="address" title={acct.address}>
                              #{acct.index} {acct.address}
                            </span>
                          </label>
                        ))}
                      </div>
                    </div>
                    {Number(dataTaskForm.mode) === 2 && (
                      <div className="field">
                        <label>Weights</label>
                        <div className="check-grid">
                          {dataTaskForm.allowed_oracles.map((addr) => (
                            <div className="weight-row" key={`weight-${addr}`}>
                              <span className="muted">{addr}</span>
                              <input
                                className="weight-input"
                                value={dataTaskForm.weights[addr] || ""}
                                onChange={(e) => {
                                  const value = e.target.value;
                                  setDataTaskForm((prev) => ({
                                    ...prev,
                                    weights: { ...prev.weights, [addr]: value }
                                  }));
                                }}
                              />
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    <div className="field">
                      <label>Min Responses</label>
                      <input
                        value={dataTaskForm.min_responses}
                        onChange={(e) => setDataTaskForm({ ...dataTaskForm, min_responses: e.target.value })}
                      />
                    </div>
                    <div className="actions">
                      <button onClick={handleRegisterDataTask}>Register Data Task</button>
                    </div>
                  </>
                )}
                {controlTab === "compute" && (
                  <>
                    <h3>Register Compute Task</h3>
                    <div className="field">
                      <label>Compute Type</label>
                      <input
                        value={computeTaskForm.compute_type}
                        onChange={(e) => setComputeTaskForm({ ...computeTaskForm, compute_type: e.target.value })}
                      />
                    </div>
                    <div className="field">
                      <label>Payload Hash / Input</label>
                      <input
                        value={computeTaskForm.payload_hash}
                        onChange={(e) => setComputeTaskForm({ ...computeTaskForm, payload_hash: e.target.value })}
                      />
                    </div>
                    <div className="field">
                      <label>Allowed Oracles (comma)</label>
                      <input
                        value={computeTaskForm.allowed_oracles}
                        onChange={(e) => setComputeTaskForm({ ...computeTaskForm, allowed_oracles: e.target.value })}
                      />
                    </div>
                    <div className="field">
                      <label>Threshold</label>
                      <input
                        value={computeTaskForm.threshold}
                        onChange={(e) => setComputeTaskForm({ ...computeTaskForm, threshold: e.target.value })}
                      />
                    </div>
                    <div className="actions">
                      <button onClick={handleRegisterComputeTask}>Register Compute Task</button>
                    </div>
                  </>
                )}
                {controlTab === "submit" && (
                  <>
                    <h3>Submit Data</h3>
                    <div className="field">
                      <label>Task ID</label>
                      <input
                        value={submitDataForm.task_id}
                        onChange={(e) => setSubmitDataForm({ ...submitDataForm, task_id: e.target.value })}
                      />
                    </div>
                    <div className="field">
                      <label>Value</label>
                      <input
                        value={submitDataForm.value}
                        onChange={(e) => setSubmitDataForm({ ...submitDataForm, value: e.target.value })}
                      />
                    </div>
                    <div className="actions">
                      <button onClick={handleSubmitData}>Submit Data</button>
                    </div>
                    <div className="divider" />
                    <h3>Submit Compute Result</h3>
                    <div className="field">
                      <label>Task ID</label>
                      <input
                        value={submitComputeForm.task_id}
                        onChange={(e) => setSubmitComputeForm({ ...submitComputeForm, task_id: e.target.value })}
                      />
                    </div>
                    <div className="field">
                      <label>Payload Hash / Input</label>
                      <input
                        value={submitComputeForm.payload_hash}
                        onChange={(e) => setSubmitComputeForm({ ...submitComputeForm, payload_hash: e.target.value })}
                      />
                    </div>
                    <div className="field">
                      <label>Result</label>
                      <input
                        value={submitComputeForm.result}
                        onChange={(e) => setSubmitComputeForm({ ...submitComputeForm, result: e.target.value })}
                      />
                    </div>
                    <div className="actions">
                      <button onClick={handleSubmitCompute}>Submit Compute</button>
                    </div>
                  </>
                )}
                {controlTab === "query" && (
                  <>
                    <h3>Query Tasks</h3>
                    <div className="actions">
                      <button className="secondary" onClick={handleQueryHealth}>Health</button>
                      <button className="secondary" onClick={handleListDataTasks}>List Data Tasks</button>
                      <button className="secondary" onClick={handleListComputeTasks}>List Compute Tasks</button>
                    </div>
                    <div className="field">
                      <label>Data Task ID</label>
                      <input
                        value={queryForm.data_task_id}
                        onChange={(e) => setQueryForm({ ...queryForm, data_task_id: e.target.value })}
                      />
                    </div>
                    <div className="actions">
                      <button className="secondary" onClick={handleQueryDataTask}>Query Data Task</button>
                    </div>
                    <div className="field">
                      <label>Compute Task ID</label>
                      <input
                        value={queryForm.compute_task_id}
                        onChange={(e) => setQueryForm({ ...queryForm, compute_task_id: e.target.value })}
                      />
                    </div>
                    <div className="actions">
                      <button className="secondary" onClick={handleQueryComputeTask}>Query Compute Task</button>
                    </div>
                  </>
                )}
              </div>

              <div className="card">
                <div className="header-row">
                  <h3>Contract State</h3>
                  <div className="actions">
                    <button className="secondary" onClick={() => setAutoRefresh(!autoRefresh)}>
                      {autoRefresh ? "Auto On" : "Auto Off"}
                    </button>
                    <button onClick={refreshContractState}>Refresh</button>
                  </div>
                </div>
                {controlPayload ? (
                  <div className="control-output">
                    <div className="output-title">{controlPayload.title}</div>
                    {controlPayload.payload.health && (
                      <div className="detail-grid">
                        <div>
                          <div className="label">Owner</div>
                          <div>{controlPayload.payload.health[0]}</div>
                        </div>
                        <div>
                          <div className="label">Data Tasks</div>
                          <div>{controlPayload.payload.health[1]}</div>
                        </div>
                        <div>
                          <div className="label">Compute Tasks</div>
                          <div>{controlPayload.payload.health[2]}</div>
                        </div>
                        <div>
                          <div className="label">Active Oracles</div>
                          <div>{controlPayload.payload.health[3]}</div>
                        </div>
                        <div>
                          <div className="label">Block</div>
                          <div>{controlPayload.payload.health[4]}</div>
                        </div>
                      </div>
                    )}
                    {controlPayload.payload.dataTasks && (
                      <div className="list-stack">
                        {controlPayload.payload.dataTasks.map((item) => (
                          <div className="list-card" key={`data-${item.taskId}`}>
                            <div className="list-title">Data Task #{item.taskId}</div>
                            <div className="muted">source {item.summary[0]} | mode {item.summary[1]}</div>
                            <div className="muted">finished {String(item.summary[2])} | final {item.summary[3]}</div>
                            <div className="muted">submissions {item.summary[4]} | min {item.summary[5]}</div>
                          </div>
                        ))}
                      </div>
                    )}
                    {controlPayload.payload.computeTasks && (
                      <div className="list-stack">
                        {controlPayload.payload.computeTasks.map((item) => (
                          <div className="list-card" key={`compute-${item.taskId}`}>
                            <div className="list-title">Compute Task #{item.taskId}</div>
                            <div className="muted">type {item.summary[0]}</div>
                            <div className="muted">finished {String(item.summary[2])} | final {item.summary[3]}</div>
                            <div className="muted">responses {item.summary[5]}</div>
                          </div>
                        ))}
                      </div>
                    )}
                    {controlPayload.payload.taskId !== undefined &&
                      controlPayload.payload.result && (
                        <div className="detail-grid">
                          <div>
                            <div className="label">Task</div>
                            <div>#{controlPayload.payload.taskId}</div>
                          </div>
                          <div>
                            <div className="label">Result</div>
                            <div className="muted">{JSON.stringify(controlPayload.payload.result)}</div>
                          </div>
                        </div>
                      )}
                    {controlPayload.payload.nextDataTaskId !== undefined && (
                      <div className="detail-grid">
                        <div>
                          <div className="label">Next Data Task</div>
                          <div>{controlPayload.payload.nextDataTaskId}</div>
                        </div>
                        <div>
                          <div className="label">Next Compute Task</div>
                          <div>{controlPayload.payload.nextComputeTaskId}</div>
                        </div>
                      </div>
                    )}
                    <div className="raw-title">Raw JSON</div>
                    <pre className="code-block">{controlOutput}</pre>
                  </div>
                ) : (
                  <pre className="code-block">{controlOutput || "No output yet."}</pre>
                )}
              </div>
            </div>
          </section>
        )}

        {active === "localchain" && (
          <section>
            <h1>Local Chain</h1>
            <div className="card header">
              <h3>Local Chain Accounts</h3>
              <button onClick={refreshLocalChain}>Refresh</button>
            </div>
            <div className="card">
              <div className="detail-grid">
                <div>
                  <div className="label">RPC URL</div>
                  <div>{localChainConfig?.rpc_url || "-"}</div>
                </div>
                <div>
                  <div className="label">Mnemonic</div>
                  <div className="muted">{localChainConfig?.mnemonic || "-"}</div>
                </div>
              </div>
            </div>
            <div className="card large">
              <ul>
                {localChainAccounts.map((acct) => (
                  <li key={acct.index}>
                    <div className="list-row">
                      <div>
                        <div className="list-title">#{acct.index} {acct.address}</div>
                        <div className="muted">{acct.path}</div>
                      </div>
                      <div className="actions">
                        <button className="secondary" onClick={() => copyText(acct.address)}>Copy Address</button>
                        <button className="secondary" onClick={() => copyText(acct.private_key)}>Copy Key</button>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
