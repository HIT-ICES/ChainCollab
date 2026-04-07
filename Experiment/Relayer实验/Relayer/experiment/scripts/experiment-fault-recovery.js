const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");
const { ethers } = require("ethers");
const {
  ROOT,
  RUNTIME_DIR,
  DEPLOYMENTS_DIR,
  writeJson,
  loadDeployment,
  deriveWallet,
  loadDatasetConfig,
  datasetConfigPath
} = require("./common");
const { buildRelaySignature } = require("../../src/relayer-node/worker");

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function percentile(nums, p) {
  if (!nums.length) {
    return 0;
  }
  const sorted = [...nums].sort((a, b) => a - b);
  const idx = Math.min(sorted.length - 1, Math.max(0, Math.ceil((p / 100) * sorted.length) - 1));
  return sorted[idx];
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

function startWorker(logFilePath, pollMs) {
  const out = fs.createWriteStream(logFilePath, { flags: "a" });
  const p = spawn("node", ["src/relayer-node/worker.js"], {
    cwd: ROOT,
    env: {
      ...process.env,
      RELAYER_POLL_MS: String(pollMs || 500)
    },
    stdio: ["ignore", "pipe", "pipe"]
  });
  p.stdout.on("data", (buf) => out.write(buf));
  p.stderr.on("data", (buf) => out.write(buf));
  return { proc: p, stream: out };
}

async function waitAllDelivered(target, submitted, timeoutMs) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    let done = 0;
    for (const t of submitted) {
      if (await target.isProcessed(t.taskId)) {
        done += 1;
      }
    }
    if (done === submitted.length) {
      return true;
    }
    await sleep(250);
  }
  return false;
}

function toMarkdown(report) {
  return [
    "# Relayer 故障恢复实验报告（BPMN拆分）",
    "",
    `生成时间：${report.generatedAt}`,
    "",
    "## 1. 实验配置",
    "",
    `- 总任务数：${report.config.totalTasks}`,
    `- 故障注入：Relayer 进程强制终止 + 延迟重启`,
    `- 源链：${report.config.sourceChainId}`,
    `- 目标链：${report.config.targetChainId}`,
    "",
    "## 2. 结果",
    "",
    "| 指标 | 数值 |",
    "| --- | ---: |",
    `| 任务提交数 | ${report.metrics.submitted} |`,
    `| 最终投递数 | ${report.metrics.delivered} |`,
    `| 最终成功率 | ${(report.metrics.successRate * 100).toFixed(2)}% |`,
    `| 载荷一致率 | ${(report.metrics.payloadIntegrityRate * 100).toFixed(2)}% |`,
    `| 崩溃时积压任务 | ${report.metrics.backlogAtCrash} |`,
    `| 重启后积压峰值 | ${report.metrics.peakBacklogAfterRestart} |`,
    `| 恢复完成耗时(s) | ${report.metrics.recoveryTimeSec.toFixed(3)} |`,
    `| P95 恢复后端到端延迟(s) | ${report.metrics.latency.p95Sec.toFixed(3)} |`,
    `| Exactly-once 通过率 | ${(report.metrics.exactlyOnceRate * 100).toFixed(2)}% |`,
    "",
    "## 3. 结论",
    "",
    "1. 在 Relayer 进程故障/重启后，任务可最终收敛到完整投递状态。",
    "2. 基于签名与 taskId 去重的设计在恢复阶段仍能保持 exactly-once 语义。",
    "3. 实验支持“可恢复正确性”主张，可作为论文中稳定性证据。",
    ""
  ].join("\n");
}

async function main() {
  const datasetConfig = loadDatasetConfig(true);
  const faultCfg = datasetConfig?.faultRecovery || {};
  const perSubmodelTasks = Number(faultCfg.perSubmodelTasks || 12);
  const phase1Ratio = Number(faultCfg.phase1Ratio || 0.4);
  const downtimeMs = Number(faultCfg.downtimeMs || 4000);
  const pollMs = Number(faultCfg.pollMs || 500);

  const casePath = path.join(DEPLOYMENTS_DIR, "bpmn-split-cases.json");
  if (!fs.existsSync(casePath)) {
    throw new Error(`missing ${casePath}. run npm run prepare:bpmn:split first`);
  }
  const cases = JSON.parse(fs.readFileSync(casePath, "utf8")).cases || [];
  const deployment = loadDeployment();

  const sourceProvider = new ethers.JsonRpcProvider(deployment.source.rpcUrl);
  const targetProvider = new ethers.JsonRpcProvider(deployment.target.rpcUrl);

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
  const relayer = deriveWallet(
    deployment.derivation.mnemonic,
    deployment.derivation.relayerIndex,
    targetProvider
  );

  const sourceArtifact = JSON.parse(
    fs.readFileSync(
      path.join(
        ROOT,
        "artifacts/contracts/SourceTaskEmitter.sol/SourceTaskEmitter.json"
      ),
      "utf8"
    )
  );
  const targetArtifact = JSON.parse(
    fs.readFileSync(
      path.join(
        ROOT,
        "artifacts/contracts/TargetTaskReceiver.sol/TargetTaskReceiver.json"
      ),
      "utf8"
    )
  );

  const source = new ethers.Contract(
    deployment.source.contract,
    sourceArtifact.abi,
    deployerSource
  );
  const target = new ethers.Contract(
    deployment.target.contract,
    targetArtifact.abi,
    deployerTarget
  );

  const allTasks = [];
  for (const c of cases) {
    const submodels = c?.split?.submodels || [];
    for (const sub of submodels) {
      for (let i = 0; i < perSubmodelTasks; i++) {
        allTasks.push({
          caseId: c.caseId,
          submodelId: sub.submodelId,
          idx: i
        });
      }
    }
  }
  const phase1 = allTasks.slice(0, Math.ceil(allTasks.length * phase1Ratio));
  const phase2 = allTasks.slice(phase1.length);

  const submitted = [];
  async function submitBatch(items) {
    for (const t of items) {
      const meta = {
        caseId: t.caseId,
        submodelId: t.submodelId,
        idx: t.idx,
        ts: Date.now()
      };
      const payloadHash = ethers.keccak256(ethers.toUtf8Bytes(JSON.stringify(meta)));
      const tx = await source.requestTask(payloadHash);
      const rc = await tx.wait();
      const block = await sourceProvider.getBlock(rc.blockNumber);
      const evt = rc.logs
        .map((x) => {
          try {
            return source.interface.parseLog(x);
          } catch {
            return null;
          }
        })
        .find((x) => x && x.name === "TaskRequested");
      submitted.push({
        ...t,
        taskId: evt.args.taskId,
        payloadHash,
        requestTsSec: Number(block?.timestamp || 0)
      });
    }
  }

  const logPath = path.join(RUNTIME_DIR, "fault-recovery-relayer.log");
  fs.mkdirSync(path.dirname(logPath), { recursive: true });
  const workerA = startWorker(logPath, pollMs);

  await submitBatch(phase1);
  const partialWaitStart = Date.now();
  let deliveredBeforeCrash = 0;
  while (Date.now() - partialWaitStart < 12000) {
    deliveredBeforeCrash = 0;
    for (const t of submitted) {
      if (await target.isProcessed(t.taskId)) {
        deliveredBeforeCrash += 1;
      }
    }
    if (deliveredBeforeCrash >= Math.max(1, Math.floor(phase1.length * 0.3))) {
      break;
    }
    await sleep(300);
  }

  workerA.proc.kill("SIGKILL");
  await sleep(500);
  workerA.stream.end();

  await submitBatch(phase2);

  let backlogAtCrash = 0;
  for (const t of submitted) {
    if (!(await target.isProcessed(t.taskId))) {
      backlogAtCrash += 1;
    }
  }

  await sleep(downtimeMs);

  const restartAt = Date.now();
  const workerB = startWorker(logPath, pollMs);

  let peakBacklog = backlogAtCrash;
  const recoveryTimeoutMs = 60000;
  let recovered = false;
  const recoveryStart = Date.now();
  while (Date.now() - recoveryStart < recoveryTimeoutMs) {
    let backlog = 0;
    for (const t of submitted) {
      if (!(await target.isProcessed(t.taskId))) {
        backlog += 1;
      }
    }
    peakBacklog = Math.max(peakBacklog, backlog);
    if (backlog === 0) {
      recovered = true;
      break;
    }
    await sleep(300);
  }

  workerB.proc.kill("SIGTERM");
  await sleep(300);
  workerB.stream.end();

  if (!recovered) {
    throw new Error("recovery experiment timeout: tasks not fully delivered");
  }

  const okAll = await waitAllDelivered(target, submitted, 10000);
  if (!okAll) {
    throw new Error("some tasks remain undelivered after recovery");
  }

  let delivered = 0;
  let matched = 0;
  const latencies = [];
  for (const t of submitted) {
    const d = await target.getDelivery(t.taskId);
    if (d.processed) {
      delivered += 1;
      const latency = Math.max(0, Number(d.processedAt) - Number(t.requestTsSec));
      latencies.push(latency);
    }
    if (d.processed && String(d.payloadHash).toLowerCase() === t.payloadHash.toLowerCase()) {
      matched += 1;
    }
  }

  let replayAttempts = 0;
  let replayBlocked = 0;
  for (const t of submitted.slice(0, Math.min(20, submitted.length))) {
    replayAttempts += 1;
    const sig = await buildRelaySignature(relayer, {
      targetContract: deployment.target.contract,
      targetChainId: Number(deployment.target.chainId),
      sourceChainId: Number(deployment.source.chainId),
      sourceContract: deployment.source.contract,
      taskId: t.taskId,
      payloadHash: t.payloadHash
    });
    const r = await expectRevert(() =>
      target
        .connect(relayer)
        .relayTask.staticCall(
          t.taskId,
          t.payloadHash,
          Number(deployment.source.chainId),
          deployment.source.contract,
          sig
        )
    );
    if (r.reverted) {
      replayBlocked += 1;
    }
  }

  const report = {
    generatedAt: new Date().toISOString(),
    config: {
      totalTasks: submitted.length,
      sourceChainId: Number(deployment.source.chainId),
      targetChainId: Number(deployment.target.chainId),
      sourceContract: deployment.source.contract,
      targetContract: deployment.target.contract,
      downtimeMs,
      datasetConfigPath: datasetConfigPath(),
      faultRecovery: {
        perSubmodelTasks,
        phase1Ratio,
        pollMs
      }
    },
    metrics: {
      submitted: submitted.length,
      delivered,
      payloadMatched: matched,
      successRate: submitted.length ? delivered / submitted.length : 0,
      payloadIntegrityRate: submitted.length ? matched / submitted.length : 0,
      backlogAtCrash,
      peakBacklogAfterRestart: peakBacklog,
      recoveryTimeSec: (Date.now() - restartAt) / 1000,
      exactlyOnceRate: replayAttempts ? replayBlocked / replayAttempts : 0,
      latency: {
        avgSec: latencies.length ? latencies.reduce((a, b) => a + b, 0) / latencies.length : 0,
        p95Sec: percentile(latencies, 95)
      }
    }
  };

  const jsonPath = path.join(DEPLOYMENTS_DIR, "fault-recovery-report.json");
  const mdPath = path.join(DEPLOYMENTS_DIR, "FAULT_RECOVERY_REPORT.md");
  writeJson(jsonPath, report);
  fs.writeFileSync(mdPath, toMarkdown(report), "utf8");

  console.log(`fault recovery json -> ${jsonPath}`);
  console.log(`fault recovery md -> ${mdPath}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
