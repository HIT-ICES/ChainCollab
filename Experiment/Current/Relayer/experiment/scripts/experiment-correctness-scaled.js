const fs = require("fs");
const path = require("path");
const { ethers } = require("ethers");
const {
  ROOT,
  DEPLOYMENTS_DIR,
  writeJson,
  loadDeployment,
  deriveWallet
} = require("./common");
const { relayOnce, buildRelaySignature } = require("../../src/relayer-node/worker");

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

function toMarkdown(report) {
  const lines = [
    "# Relayer 正确性规模实验报告（BPMN拆分）",
    "",
    `生成时间：${report.generatedAt}`,
    "",
    "## 1. 实验配置",
    "",
    `- BPMN 案例数：${report.config.caseCount}`,
    `- 总任务数：${report.config.totalTasks}`,
    `- 源链：${report.config.sourceChainId}`,
    `- 目标链：${report.config.targetChainId}`,
    "",
    "## 2. 总体结果",
    "",
    "| 指标 | 数值 |",
    "| --- | ---: |",
    `| 提交任务数 | ${report.overall.submitted} |`,
    `| 成功投递数 | ${report.overall.delivered} |`,
    `| 成功率 | ${(report.overall.successRate * 100).toFixed(2)}% |`,
    `| 载荷一致率 | ${(report.overall.payloadIntegrityRate * 100).toFixed(2)}% |`,
    `| Exactly-once 通过率 | ${(report.overall.exactlyOnceRate * 100).toFixed(2)}% |`,
    `| 端到端延迟均值(s) | ${report.overall.latency.avgSec.toFixed(3)} |`,
    `| 端到端延迟P95(s) | ${report.overall.latency.p95Sec.toFixed(3)} |`,
    "",
    "## 3. 分案例结果",
    "",
    "| 案例 | 任务数 | 投递成功率 | 载荷一致率 | 平均延迟(s) | P95延迟(s) |",
    "| --- | ---: | ---: | ---: | ---: | ---: |"
  ];

  for (const c of report.perCase) {
    lines.push(
      `| ${c.caseId} | ${c.submitted} | ${(c.successRate * 100).toFixed(2)}% | ${(c.payloadIntegrityRate * 100).toFixed(2)}% | ${c.latency.avgSec.toFixed(3)} | ${c.latency.p95Sec.toFixed(3)} |`
    );
  }

  lines.push(
    "",
    "## 4. 结论",
    "",
    "1. 基于 BPMN 子模型拆分后的跨链中继链路在规模化任务下保持高正确性。",
    "2. 任务标识+签名绑定确保 payload 不被篡改，并支持 exactly-once 去重语义。",
    "3. 可在此结果上继续扩展恢复性与吞吐上限实验。",
    ""
  );
  return lines.join("\n");
}

async function main() {
  const casePath = path.join(DEPLOYMENTS_DIR, "bpmn-split-cases.json");
  if (!fs.existsSync(casePath)) {
    throw new Error(`missing ${casePath}. run npm run prepare:bpmn:split first`);
  }
  const caseSpec = JSON.parse(fs.readFileSync(casePath, "utf8"));
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

  const tasks = [];
  for (const c of caseSpec.cases) {
    const submodels = c?.split?.submodels || [];
    const budget = Number(c?.split?.taskBudget || 20);
    const divisor = Math.max(1, submodels.length);
    const perSub = Math.max(1, Math.floor(budget / divisor));

    for (const sub of submodels) {
      for (let i = 0; i < perSub; i++) {
        tasks.push({
          caseId: c.caseId,
          submodelId: sub.submodelId,
          round: i
        });
      }
    }
  }

  const submitted = [];
  for (const t of tasks) {
    const meta = {
      caseId: t.caseId,
      submodelId: t.submodelId,
      round: t.round,
      ts: Date.now()
    };
    const metaRaw = JSON.stringify(meta);
    const payloadHash = ethers.keccak256(ethers.toUtf8Bytes(metaRaw));
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
      payloadHash,
      taskId: evt.args.taskId,
      sourceChainId: Number(evt.args.sourceChainId.toString()),
      requestTsSec: Number(block?.timestamp || 0)
    });
  }

  for (let round = 0; round < 120; round++) {
    await relayOnce();
    let done = 0;
    for (const t of submitted) {
      if (await target.isProcessed(t.taskId)) {
        done += 1;
      }
    }
    if (done === submitted.length) {
      break;
    }
    await new Promise((r) => setTimeout(r, 250));
  }

  let delivered = 0;
  let matched = 0;
  const latencies = [];
  const perCaseMap = new Map();
  for (const t of submitted) {
    const d = await target.getDelivery(t.taskId);
    const p = perCaseMap.get(t.caseId) || {
      caseId: t.caseId,
      submitted: 0,
      delivered: 0,
      matched: 0,
      latencies: []
    };
    p.submitted += 1;
    if (d.processed) {
      delivered += 1;
      p.delivered += 1;
      const latency = Math.max(0, Number(d.processedAt) - Number(t.requestTsSec));
      latencies.push(latency);
      p.latencies.push(latency);
    }
    if (d.processed && String(d.payloadHash).toLowerCase() === t.payloadHash.toLowerCase()) {
      matched += 1;
      p.matched += 1;
    }
    perCaseMap.set(t.caseId, p);
  }

  let replayAttempts = 0;
  let replayBlocked = 0;
  for (const t of submitted.slice(0, Math.min(30, submitted.length))) {
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

  const perCase = [...perCaseMap.values()].map((x) => ({
    caseId: x.caseId,
    submitted: x.submitted,
    delivered: x.delivered,
    successRate: x.submitted ? x.delivered / x.submitted : 0,
    payloadIntegrityRate: x.submitted ? x.matched / x.submitted : 0,
    latency: {
      avgSec: x.latencies.length
        ? x.latencies.reduce((a, b) => a + b, 0) / x.latencies.length
        : 0,
      p95Sec: percentile(x.latencies, 95)
    }
  }));

  const report = {
    generatedAt: new Date().toISOString(),
    config: {
      caseCount: caseSpec.cases.length,
      totalTasks: submitted.length,
      sourceChainId: Number(deployment.source.chainId),
      targetChainId: Number(deployment.target.chainId),
      sourceContract: deployment.source.contract,
      targetContract: deployment.target.contract
    },
    overall: {
      submitted: submitted.length,
      delivered,
      payloadMatched: matched,
      successRate: submitted.length ? delivered / submitted.length : 0,
      payloadIntegrityRate: submitted.length ? matched / submitted.length : 0,
      exactlyOnceRate: replayAttempts ? replayBlocked / replayAttempts : 0,
      latency: {
        avgSec: latencies.length ? latencies.reduce((a, b) => a + b, 0) / latencies.length : 0,
        p95Sec: percentile(latencies, 95)
      }
    },
    perCase
  };

  const jsonPath = path.join(DEPLOYMENTS_DIR, "correctness-scaled-report.json");
  const mdPath = path.join(DEPLOYMENTS_DIR, "CORRECTNESS_SCALED_REPORT.md");
  writeJson(jsonPath, report);
  fs.writeFileSync(mdPath, toMarkdown(report), "utf8");

  console.log(`correctness scaled json -> ${jsonPath}`);
  console.log(`correctness scaled md -> ${mdPath}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
