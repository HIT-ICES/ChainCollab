const path = require("path");
const { spawn } = require("child_process");
const { ethers } = require("ethers");
const {
  ROOT,
  DEFAULTS,
  DEPLOY_DIR,
  readArtifact,
  readDeployment,
  writeJson
} = require("../scripts/common");

const ROUNDS = Number(process.env.IIOT_ROUNDS || 12);
const TIMEOUT_MS = Number(process.env.IIOT_TIMEOUT_MS || 25000);

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function mean(values) {
  if (!values.length) return 0;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

function percentile(values, p) {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const idx = Math.max(0, Math.ceil(sorted.length * p) - 1);
  return sorted[idx];
}

function parseRelayRequested(receipt, endpointIface) {
  for (const log of receipt.logs) {
    try {
      const parsed = endpointIface.parseLog(log);
      if (parsed && parsed.name === "RelayRequested") {
        return {
          msgId: parsed.args.msgId,
          srcSender: parsed.args.srcSender,
          dstReceiver: parsed.args.dstReceiver,
          payload: parsed.args.payload,
          nonce: parsed.args.nonce
        };
      }
    } catch (err) {
      // ignore
    }
  }
  throw new Error("RelayRequested event not found");
}

function parseRelayExecuted(receipt, endpointIface, expectedMsgId) {
  for (const log of receipt.logs) {
    try {
      const parsed = endpointIface.parseLog(log);
      if (!parsed || parsed.name !== "RelayExecuted") {
        continue;
      }
      const msgId = parsed.args.msgId || parsed.args[0];
      if (
        expectedMsgId &&
        String(msgId).toLowerCase() !== String(expectedMsgId).toLowerCase()
      ) {
        continue;
      }
      const okRaw = parsed.args.ok != null ? parsed.args.ok : parsed.args[1];
      const returnData =
        parsed.args.returnData != null ? parsed.args.returnData : parsed.args[2];
      return { ok: Boolean(okRaw), returnData };
    } catch (err) {
      // ignore non-endpoint logs
    }
  }
  throw new Error("RelayExecuted event not found in receipt");
}

function decodeRevertReason(returnData) {
  try {
    const data = String(returnData || "");
    if (!data || data === "0x") {
      return "no return data";
    }
    if (data.startsWith("0x08c379a0") && data.length >= 10 + 64 + 64) {
      const hexLen = data.slice(10 + 64, 10 + 64 + 64);
      const len = parseInt(hexLen, 16);
      const reasonHex = data.slice(10 + 64 + 64, 10 + 64 + 64 + len * 2);
      return Buffer.from(reasonHex, "hex").toString("utf8");
    }
    return data;
  } catch (err) {
    return String(returnData || "");
  }
}

async function waitRelayExecuted(endpoint, msgId, fromBlock, timeoutMs) {
  const filter = endpoint.filters.RelayExecuted(msgId);
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    const logs = await endpoint.queryFilter(filter, fromBlock, "latest");
    if (logs.length > 0) {
      return logs[0];
    }
    await sleep(350);
  }
  throw new Error(`relay timeout msgId=${msgId}`);
}

function computeExpectedDecision(riskScore, alert) {
  if (!alert) return "NORMAL";
  if (riskScore >= 140) return "EMERGENCY_STOP";
  if (riskScore >= 100) return "SCHEDULE_MAINTENANCE";
  return "INSPECT";
}

function lineNameFor(deviceNo) {
  const line = Math.floor(deviceNo / 2) + 1;
  return `line-${line}`;
}

async function main() {
  const deployment = readDeployment();
  if (!deployment.chainA.iiotReceiver || !deployment.chainB.iiotReceiver) {
    throw new Error("iiotReceiver missing in deployment. run npm run deploy first");
  }

  const endpointArtifact = readArtifact("CrossChainEndpoint");
  const iiotArtifact = readArtifact("IndustrialIoTReceiver");

  const providerA = new ethers.JsonRpcProvider(deployment.chainA.rpcUrl || DEFAULTS.chainA.rpcUrl);
  const providerB = new ethers.JsonRpcProvider(deployment.chainB.rpcUrl || DEFAULTS.chainB.rpcUrl);

  const userA = new ethers.Wallet(DEFAULTS.keys.user, providerA);
  const userB = new ethers.Wallet(DEFAULTS.keys.user, providerB);
  const relayerA = new ethers.Wallet(DEFAULTS.keys.relayer, providerA);
  const relayerB = new ethers.Wallet(DEFAULTS.keys.relayer, providerB);

  const endpointA = new ethers.Contract(deployment.chainA.endpoint, endpointArtifact.abi, userA);
  const endpointB = new ethers.Contract(deployment.chainB.endpoint, endpointArtifact.abi, userB);
  const endpointARelayer = endpointA.connect(relayerA);
  const endpointBRelayer = endpointB.connect(relayerB);

  const iiotA = new ethers.Contract(deployment.chainA.iiotReceiver, iiotArtifact.abi, userA);
  const iiotB = new ethers.Contract(deployment.chainB.iiotReceiver, iiotArtifact.abi, userB);

  const relayProc = spawn("node", ["relay-server/index.js"], {
    cwd: ROOT,
    stdio: ["ignore", "pipe", "pipe"]
  });
  relayProc.stdout.on("data", (d) => process.stdout.write(`[relay] ${d}`));
  relayProc.stderr.on("data", (d) => process.stderr.write(`[relay-err] ${d}`));

  await sleep(1500);

  const rows = [];
  let firstReqForReplay = null;
  const devices = [
    ethers.id("press-01"),
    ethers.id("press-02"),
    ethers.id("cutter-01"),
    ethers.id("furnace-01")
  ];

  const sampleTsBase = Math.floor(Date.now() / 1000);

  try {
    for (let i = 0; i < ROUNDS; i++) {
      const device = devices[i % devices.length];
      const lineId = lineNameFor(i % devices.length);
      const sampleTs = sampleTsBase + i * 7;

      // deterministic pseudo-variation for reproducibility
      const shock = i % 4 === 0 ? 1 : 0;
      const temperatureMilliC =
        62000 + (i % 5) * 2500 + (i % 3 === 0 ? 5000 : 0) + shock * 22000;
      const vibrationUm = 120 + (i * 17) % 420 + shock * 500;
      const pressureKpa = 105 + (i * 11) % 28 + shock * 25;

      const payloadTelemetry = iiotB.interface.encodeFunctionData("ingestTelemetry", [
        Number(deployment.chainA.chainId),
        device,
        lineId,
        temperatureMilliC,
        vibrationUm,
        pressureKpa,
        sampleTs
      ]);

      const t0 = Date.now();
      const beforeBlockB = await providerB.getBlockNumber();
      const sendTelemetryTx = await endpointA.sendMessage(
        Number(deployment.chainB.chainId),
        deployment.chainB.iiotReceiver,
        payloadTelemetry
      );
      const sendTelemetryRc = await sendTelemetryTx.wait();
      const req1 = parseRelayRequested(sendTelemetryRc, endpointA.interface);
      if (!firstReqForReplay) {
        firstReqForReplay = { ...req1 };
      }

      const execTelemetryEvent = await waitRelayExecuted(
        endpointB,
        req1.msgId,
        beforeBlockB,
        TIMEOUT_MS
      );
      const execTelemetryRc = await execTelemetryEvent.getTransactionReceipt();
      const telemetryExec = parseRelayExecuted(
        execTelemetryRc,
        endpointB.interface,
        req1.msgId
      );
      if (!telemetryExec.ok) {
        const reason = decodeRevertReason(telemetryExec.returnData);
        throw new Error(
          `telemetry relay failed msgId=${req1.msgId} reason=${reason}`
        );
      }
      const t1 = Date.now();

      const telemetry = await iiotB.latestTelemetry(device);
      const riskScore = Number(telemetry.riskScore);
      const alert = Boolean(telemetry.alert);
      const decision = computeExpectedDecision(riskScore, alert);

      const payloadDecision = iiotA.interface.encodeFunctionData("ingestMaintenanceDecision", [
        Number(deployment.chainB.chainId),
        device,
        riskScore,
        decision,
        sampleTs
      ]);

      const beforeBlockA = await providerA.getBlockNumber();
      const sendDecisionTx = await endpointB.sendMessage(
        Number(deployment.chainA.chainId),
        deployment.chainA.iiotReceiver,
        payloadDecision
      );
      const sendDecisionRc = await sendDecisionTx.wait();
      const req2 = parseRelayRequested(sendDecisionRc, endpointB.interface);

      const execDecisionEvent = await waitRelayExecuted(
        endpointA,
        req2.msgId,
        beforeBlockA,
        TIMEOUT_MS
      );
      const execDecisionRc = await execDecisionEvent.getTransactionReceipt();
      const decisionExec = parseRelayExecuted(
        execDecisionRc,
        endpointA.interface,
        req2.msgId
      );
      if (!decisionExec.ok) {
        const reason = decodeRevertReason(decisionExec.returnData);
        throw new Error(
          `decision relay failed msgId=${req2.msgId} reason=${reason}`
        );
      }
      const t2 = Date.now();

      const decisionOnA = await iiotA.latestDecision(device);

      rows.push({
        round: i,
        device,
        lineId,
        sampleTs,
        temperatureMilliC,
        vibrationUm,
        pressureKpa,
        riskScore,
        alert,
        decision,
        decisionConfirmed: decisionOnA.decision,
        telemetryLatencyMs: t1 - t0,
        decisionLatencyMs: t2 - t1,
        cycleLatencyMs: t2 - t0,
        telemetrySendGas: Number(sendTelemetryRc.gasUsed),
        telemetryExecGas: Number(execTelemetryRc.gasUsed),
        decisionSendGas: Number(sendDecisionRc.gasUsed),
        decisionExecGas: Number(execDecisionRc.gasUsed),
        telemetrySendTxHash: sendTelemetryRc.hash,
        decisionSendTxHash: sendDecisionRc.hash
      });
    }

    const report = {
      generatedAt: new Date().toISOString(),
      scenario: "industrial-iot-crosschain-telemetry-maintenance-loop",
      rounds: ROUNDS,
      summary: {
        alertRate: rows.filter((r) => r.alert).length / rows.length,
        avgTelemetryLatencyMs: mean(rows.map((r) => r.telemetryLatencyMs)),
        p95TelemetryLatencyMs: percentile(rows.map((r) => r.telemetryLatencyMs), 0.95),
        avgDecisionLatencyMs: mean(rows.map((r) => r.decisionLatencyMs)),
        p95DecisionLatencyMs: percentile(rows.map((r) => r.decisionLatencyMs), 0.95),
        avgCycleLatencyMs: mean(rows.map((r) => r.cycleLatencyMs)),
        p95CycleLatencyMs: percentile(rows.map((r) => r.cycleLatencyMs), 0.95),
        avgTelemetryGas: mean(rows.map((r) => r.telemetrySendGas + r.telemetryExecGas)),
        avgDecisionGas: mean(rows.map((r) => r.decisionSendGas + r.decisionExecGas)),
        avgTotalGasPerCycle: mean(
          rows.map(
            (r) =>
              r.telemetrySendGas +
              r.telemetryExecGas +
              r.decisionSendGas +
              r.decisionExecGas
          )
        ),
        decisionConsistency: rows.every((r) => r.decision === r.decisionConfirmed)
      },
      rows
    };

    const out = path.join(DEPLOY_DIR, "iiot-relay-experiment-report.json");
    writeJson(out, report);

    console.log(`iiot experiment done: ${out}`);
    console.table(
      rows.map((r) => ({
        round: r.round,
        line: r.lineId,
        risk: r.riskScore,
        alert: r.alert,
        decision: r.decision,
        cycleLatencyMs: r.cycleLatencyMs,
        cycleGas:
          r.telemetrySendGas +
          r.telemetryExecGas +
          r.decisionSendGas +
          r.decisionExecGas
      }))
    );
    console.log(report.summary);

    // sanity: replay should revert
    let replayReverted = false;
    if (firstReqForReplay) {
      try {
        await endpointBRelayer.executeMessage(
          firstReqForReplay.msgId,
          Number(deployment.chainA.chainId),
          deployment.chainA.endpoint,
          firstReqForReplay.srcSender,
          firstReqForReplay.dstReceiver,
          firstReqForReplay.nonce,
          firstReqForReplay.payload
        );
      } catch (err) {
        replayReverted = true;
      }
    }
    report.summary.replayProtectionWorks = replayReverted;
    writeJson(out, report);
    console.log(`replay check (iiot): ${replayReverted ? "ok" : "failed"}`);
  } finally {
    relayProc.kill("SIGTERM");
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
