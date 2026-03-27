const fs = require("fs");
const path = require("path");
const { ethers } = require("ethers");
const { performance } = require("node:perf_hooks");
const {
  ROOT,
  DEPLOYMENTS_DIR,
  writeJson,
  deriveWallet,
  loadDatasetConfig,
  datasetConfigPath
} = require("./common");

const RELAY_DOMAIN = ethers.id("BPMN_SPLIT_RELAY_V1");
const RELAYER_DELIVERY_TIMEOUT_MS = Number(process.env.RELAYER_DELIVERY_TIMEOUT_MS || 180000);
const RELAYER_DELIVERY_POLL_MS = Number(process.env.RELAYER_DELIVERY_POLL_MS || 200);
const RELAYER_USE_BATCH = process.env.RELAYER_USE_BATCH === "1";
const RELAYER_RUNS_PER_CASE = Number(process.env.RELAYER_RUNS_PER_CASE || 0);
const RELAYER_FIXED_TASKS_PER_CASE = Number(process.env.RELAYER_FIXED_TASKS_PER_CASE || 0);

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

function pickErr(e) {
  return e?.shortMessage || e?.info?.error?.message || e?.message || "unknown";
}

async function expectRevert(fn) {
  try {
    const res = await fn();
    if (res && typeof res.wait === "function") {
      await res.wait();
    }
    return { reverted: false, reason: "not reverted" };
  } catch (e) {
    return { reverted: true, reason: pickErr(e) };
  }
}

function buildRelaySignature(relayer, payload) {
  const digest = ethers.solidityPackedKeccak256(
    ["bytes32", "address", "uint256", "uint256", "address", "bytes32", "bytes32"],
    [
      RELAY_DOMAIN,
      payload.targetContract,
      payload.targetChainId,
      payload.sourceChainId,
      payload.sourceContract,
      payload.taskId,
      payload.payloadHash
    ]
  );
  return relayer.signMessage(ethers.getBytes(digest));
}

function resolveTaskCount(taskBudget, taskPolicy) {
  if (Number.isFinite(RELAYER_RUNS_PER_CASE) && RELAYER_RUNS_PER_CASE > 0) {
    return Math.max(1, Math.round(RELAYER_RUNS_PER_CASE));
  }
  if (Number.isFinite(RELAYER_FIXED_TASKS_PER_CASE) && RELAYER_FIXED_TASKS_PER_CASE > 0) {
    return Math.max(1, Math.round(RELAYER_FIXED_TASKS_PER_CASE));
  }
  const fixed = Number(taskPolicy?.fixedTasksPerCase || 0);
  if (Number.isFinite(fixed) && fixed > 0) {
    return Math.max(1, Math.round(fixed));
  }
  const minTasks = Number(taskPolicy?.minTasks || 20);
  const maxTasks = Number(taskPolicy?.maxTasks || 60);
  const scale = Number(taskPolicy?.executionScale || 1);
  const raw = Math.round(Number(taskBudget || 30) * scale);
  return Math.max(minTasks, Math.min(maxTasks, raw));
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

async function waitDeliveryAndReceipt({
  target,
  targetProvider,
  taskId,
  fromBlock,
  timeoutMs = RELAYER_DELIVERY_TIMEOUT_MS,
  pollMs = RELAYER_DELIVERY_POLL_MS
}) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    const delivery = await target.getDelivery(taskId);
    if (delivery && delivery.processed) {
      const latest = await targetProvider.getBlockNumber();
      const logs = await target.queryFilter(
        target.filters.HandoffAccepted(taskId),
        Math.max(0, Number(fromBlock || 0)),
        latest
      );
      if (logs.length > 0) {
        const ev = logs[logs.length - 1];
        const relayReceipt = await targetProvider.getTransactionReceipt(ev.transactionHash);
        const relayBlock = await targetProvider.getBlock(ev.blockNumber);
        return { delivery, relayReceipt, relayBlock };
      }
    }
    await new Promise((resolve) => setTimeout(resolve, pollMs));
  }
  throw new Error(`wait delivery timeout for taskId=${taskId}`);
}

function collectNodeFunctionsFromAbi(abi, arity, blockedNames) {
  const blocked = new Set(blockedNames || []);
  return (abi || [])
    .filter(
      (x) =>
        x &&
        x.type === "function" &&
        x.stateMutability !== "view" &&
        x.stateMutability !== "pure" &&
        Array.isArray(x.inputs) &&
        x.inputs.length === arity &&
        !blocked.has(x.name)
    )
    .map((x) => x.name);
}

function resolveSplitNodePlan(plan, sourceAbi, targetAbi) {
  const sourceNodeFns = new Set(
    collectNodeFunctionsFromAbi(sourceAbi, 2, [
      "startAndRequestHandoff",
      "getTask",
      "isNodeExecuted"
    ])
  );
  const targetNodeFns = new Set(
    collectNodeFunctionsFromAbi(targetAbi, 1, [
      "setRelayer",
      "acceptHandoff",
      "isProcessed",
      "getDelivery",
      "isNodeExecuted",
      "getTaskRuntime"
    ])
  );

  return {
    marker: String(plan?.split?.selectedMarker || "").trim() || null,
    sourceFns: Array.from(sourceNodeFns).sort(),
    targetFns: Array.from(targetNodeFns).sort()
  };
}

async function executeSourceNodeFns({
  contract,
  provider,
  taskId,
  payloadHash,
  fns,
  caseId,
  phase
}) {
  if (!Array.isArray(fns) || !fns.length) {
    return {
      gas: 0,
      firstTs: 0,
      lastTs: 0,
      ok: true,
      executed: 0,
      executedFns: [],
      remainingFns: []
    };
  }
  let gas = 0;
  let firstTs = 0;
  let lastTs = 0;
  const remaining = [...fns];
  const executedFns = [];
  let guard = 0;
  while (remaining.length && guard < 2000) {
    guard += 1;
    let progressed = false;
    if (RELAYER_USE_BATCH && remaining.length > 1 && typeof contract.executeBatch === "function") {
      try {
        const tx = await contract.executeBatch(taskId, payloadHash, remaining);
        const rc = await waitReceipt(provider, tx, `${phase} case=${caseId} executeBatch`);
        const block = await provider.getBlock(rc.blockNumber);
        const ts = Number(block?.timestamp || 0);
        if (!firstTs) {
          firstTs = ts;
        }
        lastTs = ts;
        gas += Number(rc.gasUsed || 0);
        executedFns.push(...remaining);
        remaining.length = 0;
        progressed = true;
      } catch {
        // fall through to step-wise probing
      }
    }
    if (progressed) {
      continue;
    }
    for (let i = 0; i < remaining.length; i++) {
      const fn = remaining[i];
      try {
        await contract[fn].staticCall(taskId, payloadHash);
        const tx = await contract[fn](taskId, payloadHash);
        const rc = await waitReceipt(provider, tx, `${phase} case=${caseId} fn=${fn}`);
        const block = await provider.getBlock(rc.blockNumber);
        if (!firstTs) {
          firstTs = Number(block?.timestamp || 0);
        }
        lastTs = Number(block?.timestamp || 0);
        gas += Number(rc.gasUsed || 0);
        executedFns.push(fn);
        remaining.splice(i, 1);
        progressed = true;
        break;
      } catch {
        // not enabled yet
      }
    }
    if (!progressed) {
      break;
    }
  }
  return {
    gas,
    firstTs,
    lastTs,
    ok: true,
    executed: executedFns.length,
    executedFns,
    remainingFns: remaining
  };
}

async function executeTargetNodeFns({
  contract,
  provider,
  taskId,
  fns,
  caseId
}) {
  if (!Array.isArray(fns) || !fns.length) {
    return {
      gas: 0,
      firstTs: 0,
      lastTs: 0,
      ok: true,
      executed: 0,
      executedFns: [],
      remainingFns: []
    };
  }
  let gas = 0;
  let firstTs = 0;
  let lastTs = 0;
  const remaining = [...fns];
  const executedFns = [];
  let guard = 0;
  while (remaining.length && guard < 2000) {
    guard += 1;
    let progressed = false;
    if (RELAYER_USE_BATCH && remaining.length > 1 && typeof contract.executeBatch === "function") {
      try {
        const tx = await contract.executeBatch(taskId, remaining);
        const rc = await waitReceipt(provider, tx, `target case=${caseId} executeBatch`);
        const block = await provider.getBlock(rc.blockNumber);
        const ts = Number(block?.timestamp || 0);
        if (!firstTs) {
          firstTs = ts;
        }
        lastTs = ts;
        gas += Number(rc.gasUsed || 0);
        executedFns.push(...remaining);
        remaining.length = 0;
        progressed = true;
      } catch {
        // fall through to step-wise probing
      }
    }
    if (progressed) {
      continue;
    }
    for (let i = 0; i < remaining.length; i++) {
      const fn = remaining[i];
      try {
        await contract[fn].staticCall(taskId);
        const tx = await contract[fn](taskId);
        const rc = await waitReceipt(provider, tx, `target case=${caseId} fn=${fn}`);
        const block = await provider.getBlock(rc.blockNumber);
        if (!firstTs) {
          firstTs = Number(block?.timestamp || 0);
        }
        lastTs = Number(block?.timestamp || 0);
        gas += Number(rc.gasUsed || 0);
        executedFns.push(fn);
        remaining.splice(i, 1);
        progressed = true;
        break;
      } catch {
        // not enabled yet
      }
    }
    if (!progressed) {
      break;
    }
  }
  return {
    gas,
    firstTs,
    lastTs,
    ok: true,
    executed: executedFns.length,
    executedFns,
    remainingFns: remaining
  };
}

function toMarkdown(report) {
  const lines = [
    "# Relayer 拆分合约正确性与延迟实验报告",
    "",
    `生成时间：${report.generatedAt}`,
    "",
    "## 1. 实验配置",
    "",
    `- 案例数：${report.config.caseCount}`,
    `- 总任务数：${report.config.totalTasks}`,
    `- 源链：${report.config.sourceChainId}`,
    `- 目标链：${report.config.targetChainId}`,
    "",
    "## 2. 总体结果",
    "",
    "| 指标 | 数值 |",
    "| --- | ---: |",
    `| 提交任务数 | ${report.overall.submitted} |`,
    `| 成功任务数 | ${report.overall.delivered} |`,
    `| 成功率 | ${(report.overall.successRate * 100).toFixed(2)}% |`,
    `| 载荷一致率 | ${(report.overall.payloadIntegrityRate * 100).toFixed(2)}% |`,
    `| Exactly-once 通过率 | ${(report.overall.exactlyOnceRate * 100).toFixed(2)}% |`,
    `| 链上端到端延迟均值(s) | ${report.overall.latency.chainAvgSec.toFixed(3)} |`,
    `| 链上端到端延迟P95(s) | ${report.overall.latency.chainP95Sec.toFixed(3)} |`,
    `| 平均Gas(请求侧) | ${report.overall.gas.requestAvg.toFixed(2)} |`,
    `| 平均Gas(接收侧) | ${report.overall.gas.acceptAvg.toFixed(2)} |`,
    `| 平均Gas(总计) | ${report.overall.gas.totalAvg.toFixed(2)} |`,
    "",
    "## 3. 分案例结果",
    "",
    "| 案例 | 任务数 | 成功率 | 载荷一致率 | 链上平均(s) | 链上P95(s) | 平均Gas(总计) |",
    "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"
  ];

  for (const c of report.perCase) {
    lines.push(
      `| ${c.caseId} | ${c.submitted} | ${(c.successRate * 100).toFixed(2)}% | ${(c.payloadIntegrityRate * 100).toFixed(2)}% | ${c.latency.chainAvgSec.toFixed(3)} | ${c.latency.chainP95Sec.toFixed(3)} | ${c.gas.totalAvg.toFixed(2)} |`
    );
  }

  lines.push(
    "",
    "## 4. 延迟口径说明",
    "",
    "1. 链上端到端延迟：`最后一步交易区块时间 - startAndRequestHandoff区块时间`。",
    "2. 同时保留 wall-clock（毫秒）用于 Full/Split 对照计算。",
    ""
  );

  return lines.join("\n");
}

async function main() {
  const datasetConfig = loadDatasetConfig(true);
  const taskPolicy = datasetConfig?.taskPolicy || null;
  const splitCasePath = path.join(DEPLOYMENTS_DIR, "bpmn-split-cases.json");
  const splitDeployPath = path.join(DEPLOYMENTS_DIR, "split-generated-addresses.json");
  if (!fs.existsSync(splitCasePath) || !fs.existsSync(splitDeployPath)) {
    throw new Error(
      "missing split artifacts. run: prepare:bpmn:split -> compile -> deploy:split first"
    );
  }
  const splitCases = JSON.parse(fs.readFileSync(splitCasePath, "utf8"));
  const deployment = JSON.parse(fs.readFileSync(splitDeployPath, "utf8"));

  const sourceProvider = new ethers.JsonRpcProvider(deployment.sourceChain.rpcUrl);
  const targetProvider = new ethers.JsonRpcProvider(deployment.targetChain.rpcUrl);
  sourceProvider.pollingInterval = 100;
  targetProvider.pollingInterval = 100;
  const deployerSource = new ethers.NonceManager(
    deriveWallet(
      deployment.derivation.mnemonic,
      deployment.derivation.deployerIndex,
      sourceProvider
    )
  );
  const deployerTarget = new ethers.NonceManager(
    deriveWallet(
      deployment.derivation.mnemonic,
      deployment.derivation.deployerIndex,
      targetProvider
    )
  );
  const relayerWallet = deriveWallet(
    deployment.derivation.mnemonic,
    deployment.derivation.relayerIndex,
    targetProvider
  );
  const inlineRelay = process.env.RELAYER_INLINE === "1";

  const deploymentByCase = new Map(deployment.cases.map((x) => [x.caseId, x]));
  const casePlanByCase = new Map(splitCases.cases.map((x) => [x.caseId, x]));

  const perCaseResults = [];
  const global = {
    submitted: 0,
    delivered: 0,
    matched: 0,
    replayAttempts: 0,
    replayBlocked: 0,
    chainLatencies: [],
    wallLatenciesMs: [],
    requestGases: [],
    acceptGases: [],
    bridgeGases: [],
    executeGases: [],
    totalGases: []
  };

  for (const caseId of deploymentByCase.keys()) {
    const dep = deploymentByCase.get(caseId);
    const plan = casePlanByCase.get(caseId);
    const sourceName = dep.source.contractName;
    const targetName = dep.target.contractName;
    const sourceArtifactPath = path.join(
      ROOT,
      "artifacts",
      "contracts",
      "generated",
      `${sourceName}.sol`,
      `${sourceName}.json`
    );
    const targetArtifactPath = path.join(
      ROOT,
      "artifacts",
      "contracts",
      "generated",
      `${targetName}.sol`,
      `${targetName}.json`
    );
    const sourceArtifact = JSON.parse(fs.readFileSync(sourceArtifactPath, "utf8"));
    const targetArtifact = JSON.parse(fs.readFileSync(targetArtifactPath, "utf8"));

    const source = new ethers.Contract(
      dep.source.contractAddress,
      sourceArtifact.abi,
      deployerSource
    );
    const target = new ethers.Contract(
      dep.target.contractAddress,
      targetArtifact.abi,
      deployerTarget
    );
    const nodePlan = resolveSplitNodePlan(plan, sourceArtifact.abi, targetArtifact.abi);

    const budget = Number(plan?.split?.taskBudget || 30);
    const workflowRuns = resolveTaskCount(budget, taskPolicy);
    const stepsPerWorkflow = nodePlan.sourceFns.length + nodePlan.targetFns.length;
    console.log(
      `[split] case=${caseId} workflows=${workflowRuns} source=${nodePlan.sourceFns.length} target=${nodePlan.targetFns.length} marker=${nodePlan.marker || "N/A"} relayMode=${inlineRelay ? "inline" : "worker"}`
    );

    const workflows = [];
    const replayCandidates = [];
    for (let i = 0; i < workflowRuns; i++) {
      const wfStartMs = performance.now();
      const payload = {
        caseId,
        submodel: "A->B",
        round: i,
        ts: Date.now()
      };
      const payloadHash = ethers.keccak256(ethers.toUtf8Bytes(JSON.stringify(payload)));

      const targetScanStart = await targetProvider.getBlockNumber();
      const startTx = await source.startAndRequestHandoff(payloadHash);
      const startRc = await waitReceipt(sourceProvider, startTx, `start handoff case=${caseId} round=${i}`);
      const startBlock = await sourceProvider.getBlock(startRc.blockNumber);
      const evt = startRc.logs
        .map((x) => {
          try {
            return source.interface.parseLog(x);
          } catch {
            return null;
          }
        })
        .find((x) => x && x.name === "HandoffRequested");
      if (!evt) {
        throw new Error(`HandoffRequested not found: case=${caseId} round=${i}`);
      }
      const taskId = evt.args.taskId;

      const sourcePre = await executeSourceNodeFns({
        contract: source,
        provider: sourceProvider,
        taskId,
        payloadHash,
        fns: nodePlan.sourceFns,
        caseId,
        phase: "source-pre"
      });

      let relayRc;
      let targetBlock;
      let delivery;
      if (inlineRelay) {
        const relaySig = await buildRelaySignature(relayerWallet, {
          targetContract: dep.target.contractAddress,
          targetChainId: Number(dep.target.chainId),
          sourceChainId: Number(dep.source.chainId),
          sourceContract: dep.source.contractAddress,
          taskId,
          payloadHash
        });
        const relaySignatures = [relaySig];
        const relayTx = await target
          .connect(relayerWallet)
          .acceptHandoff(
            taskId,
            payloadHash,
            Number(dep.source.chainId),
            dep.source.contractAddress,
            Number(dep.target.chainId),
            relaySignatures
          );
        relayRc = await waitReceipt(
          targetProvider,
          relayTx,
          `inline relay case=${caseId} round=${i}`
        );
        targetBlock = await targetProvider.getBlock(relayRc.blockNumber);
        delivery = await target.getDelivery(taskId);
      } else {
        const relayResult = await waitDeliveryAndReceipt({
          target,
          targetProvider,
          taskId,
          fromBlock: targetScanStart
        });
        relayRc = relayResult.relayReceipt;
        targetBlock = relayResult.relayBlock;
        delivery = relayResult.delivery;
      }

      const targetRun = await executeTargetNodeFns({
        contract: target,
        provider: targetProvider,
        taskId,
        fns: nodePlan.targetFns,
        caseId
      });

      const sourcePost = await executeSourceNodeFns({
        contract: source,
        provider: sourceProvider,
        taskId,
        payloadHash,
        fns: sourcePre.remainingFns,
        caseId,
        phase: "source-post"
      });

      replayCandidates.push({ taskId, payloadHash });

      const deliveredOk = Number(relayRc.status || 0) === 1 && Boolean(delivery.processed);
      const matchedOk =
        deliveredOk &&
        String(delivery.payloadHash).toLowerCase() === payloadHash.toLowerCase();
      const nodeExecOk =
        sourcePre.ok &&
        targetRun.ok &&
        sourcePost.ok &&
        (sourcePre.executed + targetRun.executed + sourcePost.executed > 0);
      const workflowOk = deliveredOk && matchedOk && nodeExecOk;

      const firstSourceTs = Number(startBlock?.timestamp || 0);
      const lastWorkflowTs =
        sourcePost.lastTs || targetRun.lastTs || Number(targetBlock?.timestamp || 0);

      const requestGas =
        Number(startRc.gasUsed || 0) + Number(sourcePre.gas || 0) + Number(sourcePost.gas || 0);
      const acceptGas = Number(relayRc.gasUsed || 0) + Number(targetRun.gas || 0);
      const bridgeGas = Number(startRc.gasUsed || 0) + Number(relayRc.gasUsed || 0);
      const executeGas =
        Number(sourcePre.gas || 0) + Number(sourcePost.gas || 0) + Number(targetRun.gas || 0);
      const totalGas = requestGas + acceptGas;
      const wfEndMs = performance.now();

      workflows.push({
        delivered: workflowOk,
        matched: matchedOk,
        sourceTs: firstSourceTs,
        targetTs: lastWorkflowTs,
        wallLatencyMs: Math.max(0, wfEndMs - wfStartMs),
        requestGas,
        acceptGas,
        bridgeGas,
        executeGas,
        totalGas,
        sourceExecuted: sourcePre.executed + sourcePost.executed,
        targetExecuted: targetRun.executed
      });
      console.log(`[split] case=${caseId} progress=${i + 1}/${workflowRuns}`);
    }

    let delivered = 0;
    let matched = 0;
    const chainLatencies = [];
    const wallLatenciesMs = [];
    const requestGases = [];
    const acceptGases = [];
    const bridgeGases = [];
    const executeGases = [];
    const totalGases = [];
    const sourceExecutedCounts = [];
    const targetExecutedCounts = [];
    for (const wf of workflows) {
      if (wf.delivered) {
        delivered += 1;
        chainLatencies.push(Math.max(0, wf.targetTs - wf.sourceTs));
        wallLatenciesMs.push(Number(wf.wallLatencyMs || 0));
        requestGases.push(Number(wf.requestGas || 0));
        acceptGases.push(Number(wf.acceptGas || 0));
        bridgeGases.push(Number(wf.bridgeGas || 0));
        executeGases.push(Number(wf.executeGas || 0));
        totalGases.push(Number(wf.totalGas || 0));
        sourceExecutedCounts.push(Number(wf.sourceExecuted || 0));
        targetExecutedCounts.push(Number(wf.targetExecuted || 0));
      }
      if (wf.matched) {
        matched += 1;
      }
    }

    let replayAttempts = 0;
    let replayBlocked = 0;
    if (replayCandidates.length > 0) {
      const candidate = replayCandidates[0];
      const replaySig = await buildRelaySignature(relayerWallet, {
        targetContract: dep.target.contractAddress,
        targetChainId: Number(dep.target.chainId),
        sourceChainId: Number(dep.source.chainId),
        sourceContract: dep.source.contractAddress,
        taskId: candidate.taskId,
        payloadHash: candidate.payloadHash
      });
      const replay = await expectRevert(() =>
        target
          .connect(relayerWallet)
          .acceptHandoff
          .staticCall(
            candidate.taskId,
            candidate.payloadHash,
            Number(dep.source.chainId),
            dep.source.contractAddress,
            replaySig
          )
      );
      replayAttempts = 1;
      replayBlocked = replay.reverted ? 1 : 0;
    }

    global.submitted += workflows.length;
    global.delivered += delivered;
    global.matched += matched;
    global.replayAttempts += replayAttempts;
    global.replayBlocked += replayBlocked;
    global.chainLatencies.push(...chainLatencies);
    global.wallLatenciesMs.push(...wallLatenciesMs);
    global.requestGases.push(...requestGases);
    global.acceptGases.push(...acceptGases);
    global.bridgeGases.push(...bridgeGases);
    global.executeGases.push(...executeGases);
    global.totalGases.push(...totalGases);

    perCaseResults.push({
      caseId,
      submitted: workflows.length,
      sourceSteps: nodePlan.sourceFns.length,
      targetSteps: nodePlan.targetFns.length,
      stepsPerWorkflow,
      delivered,
      replayAttempts,
      replayBlocked,
      sourceExecutedAvg: mean(sourceExecutedCounts),
      targetExecutedAvg: mean(targetExecutedCounts),
      successRate: workflows.length ? delivered / workflows.length : 0,
      payloadIntegrityRate: workflows.length ? matched / workflows.length : 0,
      exactlyOnceRate: replayAttempts ? replayBlocked / replayAttempts : 0,
      latency: {
        chainAvgSec: mean(chainLatencies),
        chainP95Sec: percentile(chainLatencies, 95),
        wallAvgMs: mean(wallLatenciesMs),
        wallP95Ms: percentile(wallLatenciesMs, 95)
      },
      gas: {
        requestAvg: mean(requestGases),
        acceptAvg: mean(acceptGases),
        bridgeAvg: mean(bridgeGases),
        executeAvg: mean(executeGases),
        totalAvg: mean(totalGases)
      }
    });
  }

  const report = {
    generatedAt: new Date().toISOString(),
    config: {
      caseCount: perCaseResults.length,
      totalTasks: global.submitted,
      sourceChainId: Number(deployment.sourceChain.chainId),
      targetChainId: Number(deployment.targetChain.chainId),
      datasetConfigPath: datasetConfigPath(),
      taskPolicy: taskPolicy || {
        minTasks: 20,
        maxTasks: 60,
        executionScale: 1
      }
    },
    overall: {
      submitted: global.submitted,
      delivered: global.delivered,
      payloadMatched: global.matched,
      successRate: global.submitted ? global.delivered / global.submitted : 0,
      payloadIntegrityRate: global.submitted ? global.matched / global.submitted : 0,
      exactlyOnceRate: global.replayAttempts
        ? global.replayBlocked / global.replayAttempts
        : 0,
      latency: {
        chainAvgSec: mean(global.chainLatencies),
        chainP95Sec: percentile(global.chainLatencies, 95),
        wallAvgMs: mean(global.wallLatenciesMs),
        wallP95Ms: percentile(global.wallLatenciesMs, 95)
      },
      gas: {
        requestAvg: mean(global.requestGases),
        acceptAvg: mean(global.acceptGases),
        bridgeAvg: mean(global.bridgeGases),
        executeAvg: mean(global.executeGases),
        totalAvg: mean(global.totalGases)
      }
    },
    perCase: perCaseResults
  };

  const jsonPath = path.join(DEPLOYMENTS_DIR, "correctness-split-latency-report.json");
  const mdPath = path.join(DEPLOYMENTS_DIR, "CORRECTNESS_SPLIT_LATENCY_REPORT.md");
  writeJson(jsonPath, report);
  fs.writeFileSync(mdPath, toMarkdown(report), "utf8");

  console.log(`split correctness/latency json -> ${jsonPath}`);
  console.log(`split correctness/latency md -> ${mdPath}`);
  process.exit(0);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
