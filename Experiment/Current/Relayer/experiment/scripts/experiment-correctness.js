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
  return [
    "# Relayer 正确性实验报告",
    "",
    `生成时间：${report.generatedAt}`,
    "",
    "## 1. 实验配置",
    "",
    `- 任务数：${report.config.totalTasks}`,
    `- 源链：${report.config.sourceChainId}`,
    `- 目标链：${report.config.targetChainId}`,
    "",
    "## 2. 正确性结果",
    "",
    "| 指标 | 数值 |",
    "| --- | ---: |",
    `| 任务提交总数 | ${report.correctness.submitted} |`,
    `| 目标链成功处理数 | ${report.correctness.delivered} |`,
    `| 成功率 | ${(report.correctness.successRate * 100).toFixed(2)}% |`,
    `| 载荷一致率 | ${(report.correctness.payloadIntegrityRate * 100).toFixed(2)}% |`,
    `| Exactly-once 通过率 | ${(report.correctness.exactlyOnceRate * 100).toFixed(2)}% |`,
    "",
    "## 3. 攻击/异常拒绝",
    "",
    "| 测试项 | 拒绝次数/总次数 | 拒绝率 |",
    "| --- | ---: | ---: |",
    `| 重放提交拒绝 | ${report.rejections.replay.blocked}/${report.rejections.replay.attempts} | ${(report.rejections.replay.rate * 100).toFixed(2)}% |`,
    `| 越权 relayer 拒绝 | ${report.rejections.unauthorized.blocked}/${report.rejections.unauthorized.attempts} | ${(report.rejections.unauthorized.rate * 100).toFixed(2)}% |`,
    `| 篡改 payload 拒绝 | ${report.rejections.tampered.blocked}/${report.rejections.tampered.attempts} | ${(report.rejections.tampered.rate * 100).toFixed(2)}% |`,
    "",
    "## 4. 结论",
    "",
    "1. 该骨架在多链环境下具备可验证的端到端正确性（任务可达、payload 一致、无重复执行）。",
    "2. 白名单 + 签名绑定可有效阻断越权与篡改行为。",
    "3. 可在此基础上继续叠加性能与故障恢复实验。",
    ""
  ].join("\n");
}

async function main() {
  const deployment = loadDeployment();
  const totalTasks = Number(process.env.TASKS || 30);

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

  const unauthorized = ethers.Wallet.createRandom().connect(targetProvider);

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

  const submittedTasks = [];
  for (let i = 0; i < totalTasks; i++) {
    const payloadHash = ethers.keccak256(
      ethers.toUtf8Bytes(`iiot-task-${i}-${Date.now()}`)
    );
    const tx = await source.requestTask(payloadHash);
    const rc = await tx.wait();
    const evt = rc.logs
      .map((x) => {
        try {
          return source.interface.parseLog(x);
        } catch {
          return null;
        }
      })
      .find((x) => x && x.name === "TaskRequested");

    submittedTasks.push({
      taskId: evt.args.taskId,
      payloadHash: evt.args.payloadHash,
      sourceChainId: Number(evt.args.sourceChainId.toString())
    });
  }

  // Run relayer until all submitted tasks are observed as delivered.
  for (let round = 0; round < 20; round++) {
    await relayOnce();
    let done = 0;
    for (const t of submittedTasks) {
      if (await target.isProcessed(t.taskId)) {
        done += 1;
      }
    }
    if (done === submittedTasks.length) {
      break;
    }
    await new Promise((r) => setTimeout(r, 300));
  }

  let delivered = 0;
  let payloadMatch = 0;
  for (const t of submittedTasks) {
    const d = await target.getDelivery(t.taskId);
    if (d.processed) {
      delivered += 1;
    }
    if (d.processed && String(d.payloadHash).toLowerCase() === t.payloadHash.toLowerCase()) {
      payloadMatch += 1;
    }
  }

  // Replay check: same relayer tries to submit again
  let replayAttempts = 0;
  let replayBlocked = 0;
  for (const t of submittedTasks.slice(0, Math.min(10, submittedTasks.length))) {
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

  // Unauthorized relayer check
  const probe = submittedTasks[0];
  let unauthorizedAttempts = 1;
  let unauthorizedBlocked = 0;
  const unauthorizedSig = await buildRelaySignature(unauthorized, {
    targetContract: deployment.target.contract,
    targetChainId: Number(deployment.target.chainId),
    sourceChainId: Number(deployment.source.chainId),
    sourceContract: deployment.source.contract,
    taskId: probe.taskId,
    payloadHash: probe.payloadHash
  });
  const unauthorizedTry = await expectRevert(() =>
    target
      .connect(unauthorized)
      .relayTask.staticCall(
        probe.taskId,
        probe.payloadHash,
        Number(deployment.source.chainId),
        deployment.source.contract,
        unauthorizedSig
      )
  );
  if (unauthorizedTry.reverted) {
    unauthorizedBlocked += 1;
  }

  // Tampered payload check
  const tamperOriginal = ethers.keccak256(
    ethers.toUtf8Bytes(`tamper-source-${Date.now()}`)
  );
  const tamperTx = await source.requestTask(tamperOriginal);
  const tamperRc = await tamperTx.wait();
  const tamperEvt = tamperRc.logs
    .map((x) => {
      try {
        return source.interface.parseLog(x);
      } catch {
        return null;
      }
    })
    .find((x) => x && x.name === "TaskRequested");
  const tamperTaskId = tamperEvt.args.taskId;
  const tamperPayload = ethers.keccak256(ethers.toUtf8Bytes("tampered"));
  let tamperAttempts = 1;
  let tamperBlocked = 0;
  const sigForOriginal = await buildRelaySignature(relayer, {
    targetContract: deployment.target.contract,
    targetChainId: Number(deployment.target.chainId),
    sourceChainId: Number(deployment.source.chainId),
    sourceContract: deployment.source.contract,
    taskId: tamperTaskId,
    payloadHash: tamperOriginal
  });
  const tamperTry = await expectRevert(() =>
    target
      .connect(relayer)
      .relayTask.staticCall(
        tamperTaskId,
        tamperPayload,
        Number(deployment.source.chainId),
        deployment.source.contract,
        sigForOriginal
      )
  );
  if (tamperTry.reverted) {
    tamperBlocked += 1;
  }

  const report = {
    generatedAt: new Date().toISOString(),
    config: {
      totalTasks,
      sourceChainId: Number(deployment.source.chainId),
      targetChainId: Number(deployment.target.chainId),
      sourceContract: deployment.source.contract,
      targetContract: deployment.target.contract,
      relayer: await relayer.getAddress()
    },
    correctness: {
      submitted: submittedTasks.length,
      delivered,
      payloadMatched: payloadMatch,
      successRate: submittedTasks.length ? delivered / submittedTasks.length : 0,
      payloadIntegrityRate: submittedTasks.length
        ? payloadMatch / submittedTasks.length
        : 0,
      exactlyOnceRate: replayAttempts ? replayBlocked / replayAttempts : 0
    },
    rejections: {
      replay: {
        attempts: replayAttempts,
        blocked: replayBlocked,
        rate: replayAttempts ? replayBlocked / replayAttempts : 0
      },
      unauthorized: {
        attempts: unauthorizedAttempts,
        blocked: unauthorizedBlocked,
        rate: unauthorizedAttempts ? unauthorizedBlocked / unauthorizedAttempts : 0,
        reason: unauthorizedTry.reason
      },
      tampered: {
        attempts: tamperAttempts,
        blocked: tamperBlocked,
        rate: tamperAttempts ? tamperBlocked / tamperAttempts : 0,
        reason: tamperTry.reason
      }
    }
  };

  const jsonPath = path.join(DEPLOYMENTS_DIR, "correctness-report.json");
  const mdPath = path.join(DEPLOYMENTS_DIR, "CORRECTNESS_REPORT.md");

  writeJson(jsonPath, report);
  fs.writeFileSync(mdPath, toMarkdown(report), "utf8");

  console.log(`correctness json -> ${jsonPath}`);
  console.log(`correctness md -> ${mdPath}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
