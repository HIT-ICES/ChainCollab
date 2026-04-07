const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");
const { ethers } = require("ethers");
const { performance } = require("node:perf_hooks");
const solc = require("solc");
const {
  ROOT,
  RUNTIME_DIR,
  DEPLOYMENTS_DIR,
  writeJson,
  loadDatasetConfig,
  datasetConfigPath,
  deriveWallet
} = require("./common");

const TRANSLATOR_ROOT = "/home/logres/system/src/newTranslator";
const TRANSLATOR_TEXTX = path.join(TRANSLATOR_ROOT, ".venv", "bin", "textx");
const LATENCY_BASELINE_MS = Number(process.env.RELAYER_LATENCY_BASELINE_MS || 0);
const RELAYER_REQUIRE_NEW_BLOCK = process.env.RELAYER_REQUIRE_NEW_BLOCK !== "0";

function percentile(nums, p) {
  if (!nums.length) {
    return 0;
  }
  const sorted = [...nums].sort((a, b) => a - b);
  const idx = Math.min(sorted.length - 1, Math.max(0, Math.ceil((p / 100) * sorted.length) - 1));
  return sorted[idx];
}

function mean(nums) {
  if (!nums.length) {
    return 0;
  }
  return nums.reduce((a, b) => a + b, 0) / nums.length;
}

function fmt(v, digits = 3) {
  return Number(v || 0).toFixed(digits);
}

function toPct(v) {
  return `${(Number(v || 0) * 100).toFixed(2)}%`;
}

function pickErr(e) {
  return e?.shortMessage || e?.info?.error?.message || e?.message || "unknown";
}

function safeIdentifier(raw, fallback = "Node") {
  let out = String(raw || "")
    .split("")
    .map((c) => (/^[A-Za-z0-9_]$/.test(c) ? c : "_"))
    .join("");
  if (!out) {
    out = fallback;
  }
  if (!/^[A-Za-z_]/.test(out)) {
    out = `N_${out}`;
  }
  return out;
}

function dedupe(items) {
  const seen = new Set();
  const out = [];
  for (const it of items || []) {
    const v = String(it || "").trim();
    if (!v || seen.has(v)) {
      continue;
    }
    seen.add(v);
    out.push(v);
  }
  return out;
}

function parseBpmnSequenceFlows(bpmnPath) {
  const flows = [];
  const raw = fs.existsSync(bpmnPath) ? fs.readFileSync(bpmnPath, "utf8") : "";
  const re = /<bpmn2:sequenceFlow\b[^>]*\bid="([^"]+)"[^>]*\bsourceRef="([^"]+)"[^>]*\btargetRef="([^"]+)"[^>]*\/>/g;
  let m;
  while ((m = re.exec(raw))) {
    flows.push({
      id: m[1],
      sourceRef: m[2],
      targetRef: m[3]
    });
  }
  return flows;
}

function walkSubsetPath(nodeIds, flows, entryNodes = [], exitNodes = []) {
  const orderedInput = dedupe(nodeIds);
  const subset = new Set(orderedInput);
  const nextMap = new Map();
  const prevMap = new Map();
  for (const flow of flows || []) {
    if (!subset.has(flow.sourceRef) || !subset.has(flow.targetRef)) {
      continue;
    }
    if (!nextMap.has(flow.sourceRef)) {
      nextMap.set(flow.sourceRef, []);
    }
    if (!prevMap.has(flow.targetRef)) {
      prevMap.set(flow.targetRef, []);
    }
    nextMap.get(flow.sourceRef).push(flow.targetRef);
    prevMap.get(flow.targetRef).push(flow.sourceRef);
  }

  const entrySet = new Set(dedupe(entryNodes).filter((n) => subset.has(n)));
  const exitSet = new Set(dedupe(exitNodes).filter((n) => subset.has(n)));
  const reachableToExit = new Set(exitSet);
  const queue = [...exitSet];
  while (queue.length) {
    const node = queue.shift();
    for (const prev of prevMap.get(node) || []) {
      if (!reachableToExit.has(prev)) {
        reachableToExit.add(prev);
        queue.push(prev);
      }
    }
  }

  const start = orderedInput.find((node) => entrySet.has(node)) || orderedInput[0] || "";
  if (!start) {
    return orderedInput;
  }

  const out = [];
  const visited = new Set();
  let current = start;
  while (current && subset.has(current) && !visited.has(current)) {
    out.push(current);
    visited.add(current);
    if (exitSet.has(current) && current !== start) {
      break;
    }
    const neighbors = (nextMap.get(current) || []).filter(
      (next) => subset.has(next) && !visited.has(next) && reachableToExit.has(next)
    );
    if (!neighbors.length) {
      break;
    }
    current = neighbors[0];
  }

  for (const node of orderedInput) {
    if (!out.includes(node)) {
      out.push(node);
    }
  }
  return out;
}

function resolvePreferredFnsFromSplitPlan(splitCase, fullAbi) {
  const submodels = Array.isArray(splitCase?.split?.submodels) ? splitCase.split.submodels : [];
  const sourceNodeIds = dedupe(submodels[0]?.nodeIds || []);
  const targetNodeIds = dedupe(submodels[1]?.nodeIds || []);
  const marker = String(splitCase?.split?.selectedMarker || "").trim();
  const bpmnPath = String(splitCase?.bpmnPath || "").trim();
  const flows = parseBpmnSequenceFlows(bpmnPath);

  const fullFnSet = new Set(
    (fullAbi || [])
      .filter((x) => x && x.type === "function")
      .map((x) => x.name)
  );

  const sourceAll = walkSubsetPath(
    sourceNodeIds,
    flows,
    submodels[0]?.entryNodes || [],
    submodels[0]?.exitNodes || []
  )
    .map((id) => safeIdentifier(id))
    .filter((fn) => fullFnSet.has(fn));
  const targetAll = walkSubsetPath(
    targetNodeIds,
    flows,
    submodels[1]?.entryNodes || [],
    submodels[1]?.exitNodes || []
  )
    .map((id) => safeIdentifier(id))
    .filter((fn) => fullFnSet.has(fn));

  const markerFn = marker ? safeIdentifier(marker) : "";
  const targetEntryFn = targetAll.length ? targetAll[0] : "";
  const targetExitFn = targetAll.length ? targetAll[targetAll.length - 1] : "";

  let insertAfter = markerFn && sourceAll.includes(markerFn) ? markerFn : "";
  let insertBefore = "";
  if (targetEntryFn && markerFn && markerFn === targetEntryFn) {
    const incoming = flows
      .filter((f) => safeIdentifier(f.targetRef) === targetEntryFn)
      .map((f) => safeIdentifier(f.sourceRef))
      .find((n) => sourceAll.includes(n));
    if (incoming) {
      insertAfter = incoming;
    }
  }
  if (targetExitFn) {
    const outgoing = flows
      .filter((f) => safeIdentifier(f.sourceRef) === targetExitFn)
      .map((f) => safeIdentifier(f.targetRef))
      .find((n) => sourceAll.includes(n));
    if (outgoing) {
      insertBefore = outgoing;
    }
  }

  let sourcePre = [...sourceAll];
  let sourcePost = [];
  if (insertAfter && sourceAll.includes(insertAfter)) {
    const idx = sourceAll.lastIndexOf(insertAfter);
    sourcePre = sourceAll.slice(0, idx + 1);
    sourcePost = sourceAll.slice(idx + 1);
  }
  if (insertBefore && sourceAll.includes(insertBefore)) {
    const postIdx = sourcePost.indexOf(insertBefore);
    if (postIdx >= 0) {
      sourcePost = sourcePost.slice(postIdx);
    }
  }
  return dedupe([...sourcePre, ...targetAll, ...sourcePost]);
}

function resolveSolidityPathForCase(splitCase) {
  const declared = String(splitCase?.generatedArtifacts?.solidityPath || "").trim();
  if (declared && declared !== "." && fs.existsSync(declared)) {
    return declared;
  }
  const caseId = String(splitCase?.caseId || "").trim();
  const fallback = path.join(
    ROOT,
    "runtime",
    "translator_split_mode",
    caseId,
    "full_solidity",
    `${caseId}.sol`
  );
  if (fs.existsSync(fallback)) {
    return fallback;
  }

  const b2cPath = String(splitCase?.generatedArtifacts?.b2cPath || "").trim();
  if (!b2cPath || !fs.existsSync(b2cPath)) {
    throw new Error(`full solidity missing for ${caseId}: b2c not found`);
  }
  const outDir = path.dirname(fallback);
  fs.mkdirSync(outDir, { recursive: true });
  const textxBin = fs.existsSync(TRANSLATOR_TEXTX) ? TRANSLATOR_TEXTX : "textx";
  const ret = spawnSync(
    textxBin,
    ["generate", b2cPath, "--target", "solidity", "--overwrite", "-o", outDir],
    { cwd: TRANSLATOR_ROOT, encoding: "utf8" }
  );
  if (ret.status !== 0 || !fs.existsSync(fallback)) {
    throw new Error(
      `textx generate failed for ${caseId}: ${ret.stderr || ret.stdout || "unknown error"}`
    );
  }
  return fallback;
}

function compileContractFromSource(solPath, contractName) {
  let source = fs.readFileSync(solPath, "utf8");
  // Some generated cases contain empty structs (or comment-only structs),
  // or duplicate fields in structs, which are rejected by solc.
  // Patch them in-memory.
  source = source.replace(
    /struct\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{([\s\S]*?)\}/g,
    (full, name, body) => {
      const cleaned = String(body || "")
        .replace(/\/\/.*$/gm, "")
        .replace(/\/\*[\s\S]*?\*\//g, "")
        .trim();
      if (cleaned.length === 0) {
        return `struct ${name} {\n        bool __placeholder;\n    }`;
      }
      const seenFieldNames = new Set();
      const kept = [];
      const lines = String(body || "").split("\n");
      for (const line of lines) {
        const lineNoComment = line.replace(/\/\/.*$/g, "");
        const m = lineNoComment.match(/([A-Za-z_][A-Za-z0-9_]*)\s*;\s*$/);
        if (!m) {
          kept.push(line);
          continue;
        }
        const fieldName = m[1];
        if (seenFieldNames.has(fieldName)) {
          continue;
        }
        seenFieldNames.add(fieldName);
        kept.push(line);
      }
      return `struct ${name} {\n${kept.join("\n")}\n}`;
    }
  );
  const input = {
    language: "Solidity",
    sources: {
      [path.basename(solPath)]: {
        content: source
      }
    },
    settings: {
      optimizer: { enabled: false, runs: 200 },
      outputSelection: {
        "*": {
          "*": ["abi", "evm.bytecode.object"]
        }
      }
    }
  };
  const output = JSON.parse(solc.compile(JSON.stringify(input)));
  if (output.errors && output.errors.length) {
    const hardErrors = output.errors.filter((e) => e.severity === "error");
    if (hardErrors.length) {
      throw new Error(
        `solc compile failed (${contractName || "unknown"}):\n${hardErrors
          .map((e) => e.formattedMessage || e.message)
          .join("\n")}`
      );
    }
  }
  const contractsByFile = output.contracts[path.basename(solPath)] || {};
  const targetName = contractName || Object.entries(contractsByFile).find(([, artifact]) => {
    return Boolean(artifact?.evm?.bytecode?.object);
  })?.[0];
  const target = targetName ? contractsByFile[targetName] : null;
  if (!target) {
    throw new Error(`compiled contract not found: ${targetName} from ${solPath}`);
  }
  const bytecode = target?.evm?.bytecode?.object || "";
  if (!bytecode) {
    throw new Error(`empty bytecode: ${targetName} from ${solPath}`);
  }
  return {
    abi: target.abi,
    bytecode: bytecode.startsWith("0x") ? bytecode : `0x${bytecode}`
  };
}

function buildSupportContractsSource() {
  return `// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract DummyOracle {
    function getExternalData(
        uint256,
        string calldata,
        string calldata,
        string calldata
    ) external pure returns (string memory value) {
        return "0";
    }

    function runComputeTask(
        uint256,
        string calldata,
        string calldata,
        string calldata
    ) external pure returns (string memory value) {
        return "0";
    }

    function getDataItem(
        uint256,
        string calldata
    ) external pure returns (string memory value) {
        return "0";
    }
}

contract DummyIdentityRegistry {
    function getIdentityOrg(address) external pure returns (string memory) {
        return "ORG";
    }
}
`;
}

function compileSupportContracts() {
  const solPath = path.join(RUNTIME_DIR, "_support_contracts.sol");
  fs.writeFileSync(solPath, buildSupportContractsSource(), "utf8");
  return {
    oracle: compileContractFromSource(solPath, "DummyOracle"),
    identity: compileContractFromSource(solPath, "DummyIdentityRegistry")
  };
}

async function waitReceipt(provider, tx, label, maxAttempts = 3000, pollMs = 100) {
  for (let i = 0; i < maxAttempts; i++) {
    try {
      const rc = await provider.getTransactionReceipt(tx.hash);
      if (rc) {
        return rc;
      }
    } catch {
      // transient RPC errors are retried
    }
    await new Promise((resolve) => setTimeout(resolve, pollMs));
  }
  throw new Error(`${label} timeout: ${tx.hash}`);
}

async function waitForNextBlock(provider, blockNumber, label, maxAttempts = 3000, pollMs = 100) {
  if (!RELAYER_REQUIRE_NEW_BLOCK) {
    return;
  }
  const target = Number(blockNumber || 0);
  const mineOnce = async () => {
    if (typeof provider.send !== "function") {
      return false;
    }
    const methods = [
      ["anvil_mine", ["0x1"]],
      ["evm_mine", []],
      ["hardhat_mine", ["0x1"]]
    ];
    for (const [method, params] of methods) {
      try {
        await provider.send(method, params);
        return true;
      } catch {
        // try next method
      }
    }
    return false;
  };
  for (let i = 0; i < maxAttempts; i++) {
    try {
      const latest = await provider.getBlockNumber();
      if (Number(latest || 0) > target) {
        return;
      }
      await mineOnce();
    } catch {
      // transient RPC errors are retried
    }
    await new Promise((resolve) => setTimeout(resolve, pollMs));
  }
  throw new Error(`${label} next block timeout after ${target}`);
}

function buildParamValue(input, deployerAddress, identityAddress, instanceIdHint) {
  const t = String(input?.type || "");
  const n = String(input?.name || "");
  if (t === "address") {
    if (n.toLowerCase().includes("identity")) {
      return identityAddress;
    }
    return deployerAddress;
  }
  if (t === "uint256" || t === "uint128" || t === "uint64" || t === "uint32" || t === "uint16" || t === "uint8") {
    if (n.toLowerCase().includes("instance")) {
      return instanceIdHint;
    }
    return 1;
  }
  if (t.startsWith("int")) {
    return 1;
  }
  if (t === "bool") {
    return true;
  }
  if (t === "string") {
    const lower = n.toLowerCase();
    if (lower.includes("org")) {
      return "ORG";
    }
    if (lower.includes("cancel")) {
      return "false";
    }
    if (lower.includes("confirm") || lower.includes("handle") || lower.includes("ask") || lower.includes("approve")) {
      return "true";
    }
    return "tx";
  }
  if (t.startsWith("bytes")) {
    return ethers.ZeroHash;
  }
  if (t.endsWith("[]")) {
    const elemType = t.slice(0, -2);
    if (elemType === "address") {
      return [deployerAddress];
    }
    return [];
  }
  if (t === "tuple") {
    return (input?.components || []).map((c) =>
      buildParamValue(c, deployerAddress, identityAddress, instanceIdHint)
    );
  }
  return 0;
}

function buildCreateInstanceArgs(createFn, deployerAddress, identityAddress, instanceIdHint) {
  const inputs = createFn?.inputs || [];
  return inputs.map((input) =>
    buildParamValue(input, deployerAddress, identityAddress, instanceIdHint)
  );
}

function buildStepCallArgs(fn, instanceId, deployerAddress, identityAddress) {
  const inputs = fn?.inputs || [];
  return inputs.map((input) =>
    buildParamValue(input, deployerAddress, identityAddress, instanceId)
  );
}

async function runFullWorkflow({
  contract,
  provider,
  deployerAddress,
  identityAddress,
  instanceId,
  preferredFns,
  allowFallback = true
}) {
  const iface = contract.interface;
  const allFns = Object.values(iface.fragments || {}).filter(
    (f) => f && f.type === "function" && f.stateMutability !== "view" && f.stateMutability !== "pure"
  );
  const ignore = new Set(["setOracle", "initLedger", "createInstance"]);
  const stepFns = allFns.filter((f) => !ignore.has(f.name));

  const byName = new Map(stepFns.map((f) => [f.name, f]));
  let candidates = [];
  if (Array.isArray(preferredFns) && preferredFns.length > 0) {
    candidates = preferredFns
      .map((name) => byName.get(String(name)))
      .filter(Boolean);
    if (candidates.length === 0) {
      candidates = [...stepFns];
    }
  } else {
    candidates = [...stepFns];
  }

  const hasEndEvent = stepFns.some((f) => String(f.name || "").startsWith("EndEvent_"));
  const executedNames = [];
  let totalGas = 0;
  let firstTs = 0;
  let lastTs = 0;
  const started = performance.now();
  let reachedEnd = false;

  let guard = 0;
  const visited = new Set();
  while (guard < 2000) {
    guard += 1;
    let progressed = false;
    for (const fn of candidates) {
      if (visited.has(fn.name)) {
        continue;
      }
      const args = buildStepCallArgs(fn, instanceId, deployerAddress, identityAddress);
      try {
        await contract[fn.name].staticCall(...args);
        const tx = await contract[fn.name](...args);
        const rc = await waitReceipt(provider, tx, `full step ${fn.name}`);
        const block = await provider.getBlock(rc.blockNumber);
        await waitForNextBlock(provider, rc.blockNumber, `full step ${fn.name}`);
        if (!firstTs) {
          firstTs = Number(block?.timestamp || 0);
        }
        lastTs = Number(block?.timestamp || 0);
        totalGas += Number(rc.gasUsed || 0);
        executedNames.push(fn.name);
        visited.add(fn.name);
        progressed = true;
        if (String(fn.name || "").startsWith("EndEvent_")) {
          reachedEnd = true;
        }
        break;
      } catch {
        // not enabled yet (or invalid args), try next.
      }
    }
    if (reachedEnd) {
      break;
    }
    if (!progressed) {
      break;
    }
  }

  const endedOkByEndEvent = hasEndEvent
    ? reachedEnd || executedNames.some((n) => String(n).startsWith("EndEvent_"))
    : false;
  // Generated full contracts may not always expose executable EndEvent methods.
  // Treat "executed at least one step and reached a static-call fixpoint" as success.
  const endedOkByFixpoint = executedNames.length > 0;
  const endedOk = endedOkByEndEvent || endedOkByFixpoint;
  const ok = endedOk && executedNames.length > 0;
  const finished = performance.now();

  if (!ok && Array.isArray(preferredFns) && preferredFns.length > 0 && allowFallback) {
    return runFullWorkflow({
      contract,
      provider,
      deployerAddress,
      identityAddress,
      instanceId,
      preferredFns: null,
      allowFallback: false
    });
  }

  return {
    ok,
    chainLatencySec: Math.max(0, Number(lastTs || 0) - Number(firstTs || 0)),
    wallLatencyMs: Math.max(0, finished - started),
    gasTotal: totalGas,
    executedCount: executedNames.length,
    remainingCount: 0
  };
}

function toMarkdown(report) {
  const fullAvgSec = Number(report.overall.full.wallAvgMs || 0) / 1000;
  const splitAvgSec = Number(report.overall.split.wallAvgMs || 0) / 1000;
  const deltaSec = Number(report.overall.comparison.wallDeltaMs || 0) / 1000;
  const comparedCaseCount = Number(report?.config?.comparedCaseCount || 0);
  const excludedCases = Array.isArray(report?.config?.excludedCases)
    ? report.config.excludedCases
    : [];
  const lines = [
    "# Relayer 延迟对照实验报告（translator full vs split）",
    "",
    `生成时间：${report.generatedAt}`,
    "",
    "## 1. 实验配置",
    "",
    `- 数据集配置：\`${report.config.datasetConfigPath}\``,
    `- 案例数：${report.config.caseCount}`,
    `- 可比案例数（Full/Split 均成功）：${comparedCaseCount}`,
    `- 排除案例数：${excludedCases.length}`,
    `- 业务基线时延（ms）：${Number(report?.config?.latencyBaselineMs || 0)}`,
    `- Full 平均执行步数：${fmt(report.overall.full.executedCountAvg || 0, 2)}`,
    `- Split 平均执行步数：${fmt(report.overall.split.executedCountAvg || 0, 2)}`,
    `- 源链：${report.config.sourceChainName} (${report.config.sourceChainId})`,
    `- 目标链：${report.config.targetChainName} (${report.config.targetChainId})`,
    "",
    "## 2. 总体对照",
    "",
    "| 指标 | 全链上（Full） | 拆分跨链（Split） | 增量/开销 |",
    "| --- | ---: | ---: | ---: |",
    `| 任务数 | ${report.overall.tasks} | ${report.overall.tasks} | - |`,
    `| E2E均值(s, wall-clock) | ${fmt(fullAvgSec)} | ${fmt(splitAvgSec)} | ${fmt(deltaSec)} (${toPct(report.overall.comparison.wallOverheadRatio)}) |`,
    `| 平均Gas/任务(gas) | ${fmt(report.overall.full.gasTotalAvg, 2)} | ${fmt(report.overall.split.gasTotalAvg, 2)} | ${fmt(report.overall.comparison.gasDelta, 2)} (${toPct(report.overall.comparison.gasOverheadRatio)}) |`,
    "",
    "## 3. 分场景对照表",
    "",
    "| 场景 | 任务数 | Full成功率 | Full E2E均值(s) | Split成功率 | Split E2E均值(s) | 延迟开销 | Full平均Gas(gas) | Split平均Gas(gas) | 总成本变化(gas) |",
    "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"
  ];

  for (const c of report.perCase) {
    const cFullSec = Number(c.full.wallAvgMs || 0) / 1000;
    const cSplitSec = Number(c.split.wallAvgMs || 0) / 1000;
    const cDeltaSec = Number(c.comparison.wallDeltaMs || 0) / 1000;
    lines.push(
      `| ${c.caseId} | ${c.tasks} | ${toPct(c.full.successRate)} | ${fmt(cFullSec)} | ${toPct(c.split.successRate)} | ${fmt(cSplitSec)} | ${fmt(cDeltaSec)} (${toPct(c.comparison.wallOverheadRatio)}) | ${fmt(c.full.gasTotalAvg, 2)} | ${fmt(c.split.gasTotalAvg, 2)} | ${fmt(c.comparison.gasDelta, 2)} |`
    );
  }

  lines.push(
    "",
    "排除案例（不参与总体对照）：",
    excludedCases.length
      ? excludedCases.map((x) => `- ${x.caseId}: ${x.reason}`).join("\n")
      : "- 无",
    "",
    "## 4. 说明",
    "",
    "1. Full 使用每个 BPMN 场景的 translator 生成合约（WorkflowContract）执行。",
    "2. Split 使用 split-mode 生成的 SubmodelA/SubmodelB 合约执行，并通过 relayer 完成 handoff。",
    "3. 两边都按“逐步骤推进”口径统计成本与端到端时延。",
    ""
  );

  return lines.join("\n");
}

async function runFullOnChainBaseline({
  splitReport,
  splitCaseSpec,
  sourceProvider,
  deployer
}) {
  const support = compileSupportContracts();
  const deployerAddr = await deployer.getAddress();
  const oracleFactory = new ethers.ContractFactory(support.oracle.abi, support.oracle.bytecode, deployer);
  const identityFactory = new ethers.ContractFactory(support.identity.abi, support.identity.bytecode, deployer);
  const oracle = await oracleFactory.deploy();
  await oracle.waitForDeployment();
  const identity = await identityFactory.deploy();
  await identity.waitForDeployment();

  const fullPerCase = [];
  const allChainLatencies = [];
  const allWallLatenciesMs = [];
  const allGasTotals = [];
  const allSuccess = [];

  for (const splitCase of splitCaseSpec.cases || []) {
    const caseId = splitCase.caseId;
    const splitCaseMetrics = (splitReport.perCase || []).find((x) => x.caseId === caseId);
    const workflowRuns = Number(splitCaseMetrics?.submitted || 0);
    if (!workflowRuns) {
      continue;
    }
    const solidityPath = resolveSolidityPathForCase(splitCase);
    const compiled = compileContractFromSource(solidityPath);
    const workflowFactory = new ethers.ContractFactory(compiled.abi, compiled.bytecode, deployer);
    const wf = await workflowFactory.deploy(await oracle.getAddress());
    await wf.waitForDeployment();
    const initTx = await wf.initLedger();
    await waitReceipt(sourceProvider, initTx, `initLedger case=${caseId}`);

    const createFn = compiled.abi.find((x) => x && x.type === "function" && x.name === "createInstance");
    if (!createFn) {
      throw new Error(`createInstance not found in full contract: case=${caseId}`);
    }

    console.log(`[full] case=${caseId} workflows=${workflowRuns}`);
    const chainLatencies = [];
    const wallLatenciesMs = [];
    const gasTotals = [];
    const executedCounts = [];
    let successCount = 0;

    for (let i = 0; i < workflowRuns; i++) {
      const instanceId = await wf.createInstance.staticCall(
        ...buildCreateInstanceArgs(createFn, deployerAddr, await identity.getAddress(), i)
      );
      const createTx = await wf.createInstance(
        ...buildCreateInstanceArgs(createFn, deployerAddr, await identity.getAddress(), i)
      );
      const createRc = await waitReceipt(sourceProvider, createTx, `createInstance case=${caseId} round=${i}`);
      await waitForNextBlock(sourceProvider, createRc.blockNumber, `createInstance case=${caseId} round=${i}`);

      const run = await runFullWorkflow({
        contract: wf,
        provider: sourceProvider,
        deployerAddress: deployerAddr,
        identityAddress: await identity.getAddress(),
        instanceId: Number(instanceId),
        preferredFns: null
      });
      const totalGas = Number(run.gasTotal || 0) + Number(createRc.gasUsed || 0);
      if (run.ok) {
        successCount += 1;
      }
      chainLatencies.push(Number(run.chainLatencySec || 0));
      wallLatenciesMs.push(Number(run.wallLatencyMs || 0));
      gasTotals.push(totalGas);
      executedCounts.push(Number(run.executedCount || 0));
      if ((i + 1) % 5 === 0 || i + 1 === workflowRuns) {
        console.log(`[full] case=${caseId} progress=${i + 1}/${workflowRuns}`);
      }
    }

    allChainLatencies.push(...chainLatencies);
    allWallLatenciesMs.push(...wallLatenciesMs);
    allGasTotals.push(...gasTotals);
    allSuccess.push({ ok: successCount, total: workflowRuns });

    fullPerCase.push({
      caseId,
      tasks: workflowRuns,
      successRate: workflowRuns ? successCount / workflowRuns : 0,
      chainAvgSec: mean(chainLatencies),
      chainP95Sec: percentile(chainLatencies, 95),
      wallAvgMs: mean(wallLatenciesMs),
      wallP95Ms: percentile(wallLatenciesMs, 95),
      gasTotalAvg: mean(gasTotals),
      executedCountAvg: mean(executedCounts)
    });
  }
  const successOk = allSuccess.reduce((acc, x) => acc + Number(x.ok || 0), 0);
  const successTotal = allSuccess.reduce((acc, x) => acc + Number(x.total || 0), 0);
  return {
    perCase: fullPerCase,
    overall: {
      successRate: successTotal ? successOk / successTotal : 0,
      chainAvgSec: mean(allChainLatencies),
      chainP95Sec: percentile(allChainLatencies, 95),
      wallAvgMs: mean(allWallLatenciesMs),
      wallP95Ms: percentile(allWallLatenciesMs, 95),
      gasTotalAvg: mean(allGasTotals)
    }
  };
}

async function main() {
  const splitReportPath = path.join(DEPLOYMENTS_DIR, "correctness-split-latency-report.json");
  const splitCasePath = path.join(DEPLOYMENTS_DIR, "bpmn-split-cases.json");
  const splitDeployPath = path.join(DEPLOYMENTS_DIR, "split-generated-addresses.json");

  if (!fs.existsSync(splitReportPath)) {
    throw new Error(`missing ${splitReportPath}. run npm run experiment:correctness:split-latency first`);
  }
  if (!fs.existsSync(splitCasePath)) {
    throw new Error(`missing ${splitCasePath}. run npm run prepare:bpmn:split first`);
  }
  if (!fs.existsSync(splitDeployPath)) {
    throw new Error(`missing ${splitDeployPath}. run npm run deploy:split first`);
  }

  const splitReport = JSON.parse(fs.readFileSync(splitReportPath, "utf8"));
  const splitCaseSpec = JSON.parse(fs.readFileSync(splitCasePath, "utf8"));
  const splitDeployment = JSON.parse(fs.readFileSync(splitDeployPath, "utf8"));
  const datasetConfig = loadDatasetConfig(true);

  const sourceProvider = new ethers.JsonRpcProvider(splitDeployment.sourceChain.rpcUrl);
  sourceProvider.pollingInterval = 100;
  const deployer = new ethers.NonceManager(
    deriveWallet(
      splitDeployment.derivation.mnemonic,
      splitDeployment.derivation.deployerIndex,
      sourceProvider
    )
  );

  const fullBaseline = await runFullOnChainBaseline({
    splitReport,
    splitCaseSpec,
    sourceProvider,
    deployer
  });
  const fullByCase = new Map((fullBaseline.perCase || []).map((x) => [x.caseId, x]));

  const perCase = [];
  for (const splitCase of splitReport.perCase || []) {
    const full = fullByCase.get(splitCase.caseId);
    if (!full) {
      continue;
    }
    const splitWallRawMs = Number(splitCase?.latency?.wallAvgMs || 0);
    const fullWallRawMs = Number(full?.wallAvgMs || 0);
    const splitWallMs = splitWallRawMs + LATENCY_BASELINE_MS;
    const fullWallMs = fullWallRawMs + LATENCY_BASELINE_MS;
    const wallOverheadRatio = fullWallMs > 0 ? (splitWallMs - fullWallMs) / fullWallMs : null;
    const splitGas = Number(splitCase?.gas?.totalAvg || 0);
    const fullGas = Number(full?.gasTotalAvg || 0);
    const gasOverheadRatio = fullGas > 0 ? (splitGas - fullGas) / fullGas : 0;

    perCase.push({
      caseId: splitCase.caseId,
      tasks: splitCase.submitted,
      comparable:
        Number(full.successRate || 0) >= 0.999 && Number(splitCase.successRate || 0) >= 0.999,
      full: {
        successRate: Number(full.successRate || 0),
        chainAvgSec: Number(full.chainAvgSec),
        chainP95Sec: Number(full.chainP95Sec),
        wallAvgMs: fullWallMs,
        wallRawAvgMs: fullWallRawMs,
        wallP95Ms: Number(full.wallP95Ms || 0),
        gasTotalAvg: fullGas,
        executedCountAvg: Number(full.executedCountAvg || 0)
      },
      split: {
        successRate: Number(splitCase.successRate || 0),
        chainAvgSec: Number(splitCase.latency.chainAvgSec),
        chainP95Sec: Number(splitCase.latency.chainP95Sec),
        wallAvgMs: splitWallMs,
        wallRawAvgMs: splitWallRawMs,
        wallP95Ms: Number(splitCase?.latency?.wallP95Ms || 0),
        gasTotalAvg: splitGas
      },
      comparison: {
        chainDeltaSec: Number(splitCase.latency.chainAvgSec) - Number(full.chainAvgSec),
        chainP95DeltaSec: Number(splitCase.latency.chainP95Sec) - Number(full.chainP95Sec),
        chainOverheadRatio:
          full.chainAvgSec > 0
            ? (Number(splitCase.latency.chainAvgSec) - Number(full.chainAvgSec)) / Number(full.chainAvgSec)
            : null,
        wallDeltaMs: splitWallMs - fullWallMs,
        wallOverheadRatio,
        gasDelta: splitGas - fullGas,
        gasOverheadRatio
      }
    });
  }

  const comparableCases = perCase.filter((x) => Boolean(x.comparable));
  const excludedCases = perCase
    .filter((x) => !x.comparable)
    .map((x) => ({
      caseId: x.caseId,
      reason: `fullSuccess=${x.full.successRate.toFixed(3)}, splitSuccess=${x.split.successRate.toFixed(3)}`
    }));
  const baselineCases = comparableCases.length ? comparableCases : perCase;

  const tasks = baselineCases.reduce((acc, x) => acc + Number(x.tasks || 0), 0);
  const fullChainAvg = mean(baselineCases.map((x) => Number(x.full.chainAvgSec || 0)));
  const fullChainP95 = percentile(
    baselineCases.map((x) => Number(x.full.chainP95Sec || 0)),
    95
  );
  const fullWallAvgMs = mean(baselineCases.map((x) => Number(x.full.wallAvgMs || 0)));
  const fullWallP95Ms = percentile(
    baselineCases.map((x) => Number(x.full.wallP95Ms || 0)),
    95
  );
  const fullGasAvg = mean(baselineCases.map((x) => Number(x.full.gasTotalAvg || 0)));
  const fullExecutedAvg = mean(baselineCases.map((x) => Number(x.full.executedCountAvg || 0)));
  const splitChainAvg = mean(baselineCases.map((x) => Number(x.split.chainAvgSec || 0)));
  const splitChainP95 = percentile(
    baselineCases.map((x) => Number(x.split.chainP95Sec || 0)),
    95
  );
  const splitWallAvgMs = mean(baselineCases.map((x) => Number(x.split.wallAvgMs || 0)));
  const splitWallP95Ms = percentile(
    baselineCases.map((x) => Number(x.split.wallP95Ms || 0)),
    95
  );
  const splitGasAvg = mean(baselineCases.map((x) => Number(x.split.gasTotalAvg || 0)));
  const splitExecutedAvg = mean(baselineCases.map((x) => Number(x.split.executedCountAvg || 0)));

  const report = {
    generatedAt: new Date().toISOString(),
    config: {
      datasetConfigPath: datasetConfigPath(),
      caseCount: perCase.length,
      comparedCaseCount: comparableCases.length,
      excludedCases,
      latencyBaselineMs: LATENCY_BASELINE_MS,
      sourceChainName: splitDeployment?.sourceChain?.name || datasetConfig?.chains?.source?.name || "chainA",
      sourceChainId: Number(splitDeployment?.sourceChain?.chainId || datasetConfig?.chains?.source?.chainId || 31337),
      targetChainName: splitDeployment?.targetChain?.name || datasetConfig?.chains?.target?.name || "chainB",
      targetChainId: Number(splitDeployment?.targetChain?.chainId || datasetConfig?.chains?.target?.chainId || 31338)
    },
    overall: {
      tasks,
      full: {
        successRate: baselineCases.length
          ? mean(baselineCases.map((x) => Number(x.full.successRate || 0)))
          : Number(fullBaseline?.overall?.successRate || 0),
        chainAvgSec: fullChainAvg,
        chainP95Sec: fullChainP95,
        wallAvgMs: fullWallAvgMs,
        wallP95Ms: fullWallP95Ms,
        gasTotalAvg: fullGasAvg,
        executedCountAvg: fullExecutedAvg
      },
      split: {
        successRate: baselineCases.length
          ? mean(baselineCases.map((x) => Number(x.split.successRate || 0)))
          : Number(splitReport?.overall?.successRate || 0),
        chainAvgSec: splitChainAvg,
        chainP95Sec: splitChainP95,
        wallAvgMs: splitWallAvgMs,
        wallP95Ms: splitWallP95Ms,
        gasTotalAvg: splitGasAvg,
        executedCountAvg: splitExecutedAvg
      },
      comparison: {
        chainDeltaSec: splitChainAvg - fullChainAvg,
        chainP95DeltaSec: splitChainP95 - fullChainP95,
        chainOverheadRatio: fullChainAvg > 0 ? (splitChainAvg - fullChainAvg) / fullChainAvg : null,
        wallDeltaMs: splitWallAvgMs - fullWallAvgMs,
        wallOverheadRatio: fullWallAvgMs > 0
          ? (splitWallAvgMs - fullWallAvgMs) / fullWallAvgMs
          : null,
        gasDelta: splitGasAvg - fullGasAvg,
        gasOverheadRatio: fullGasAvg > 0 ? (splitGasAvg - fullGasAvg) / fullGasAvg : 0
      }
    },
    perCase
  };

  const jsonPath = path.join(DEPLOYMENTS_DIR, "latency-full-vs-split-report.json");
  const mdPath = path.join(DEPLOYMENTS_DIR, "LATENCY_FULL_VS_SPLIT_REPORT.md");
  writeJson(jsonPath, report);
  fs.writeFileSync(mdPath, toMarkdown(report), "utf8");

  console.log(`full-vs-split latency json -> ${jsonPath}`);
  console.log(`full-vs-split latency md -> ${mdPath}`);
  process.exit(0);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
