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

const ROUNDS = Number(process.env.RELAY_EXPERIMENT_ROUNDS || 10);
const TIMEOUT_MS = Number(process.env.RELAY_EXPERIMENT_TIMEOUT_MS || 20000);

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function mean(values) {
  if (!values.length) return 0;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

async function waitForRelayExecuted(endpoint, msgId, fromBlock, timeoutMs) {
  const filter = endpoint.filters.RelayExecuted(msgId);
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    const logs = await endpoint.queryFilter(filter, fromBlock, "latest");
    if (logs.length > 0) {
      return logs[0];
    }
    await sleep(300);
  }
  throw new Error(`wait relay timeout msgId=${msgId}`);
}

function parseRelayRequested(receipt, endpointIface) {
  for (const log of receipt.logs) {
    try {
      const parsed = endpointIface.parseLog(log);
      if (parsed && parsed.name === "RelayRequested") {
        return {
          msgId: parsed.args.msgId,
          dstChainId: Number(parsed.args.dstChainId),
          dstReceiver: parsed.args.dstReceiver,
          srcSender: parsed.args.srcSender,
          payload: parsed.args.payload,
          nonce: parsed.args.nonce
        };
      }
    } catch (err) {
      // ignore non-endpoint logs
    }
  }
  throw new Error("RelayRequested log not found");
}

async function main() {
  const deployment = readDeployment();
  const endpointArtifact = readArtifact("CrossChainEndpoint");
  const receiverArtifact = readArtifact("RelayTaskReceiver");

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

  const receiverA = new ethers.Contract(deployment.chainA.receiver, receiverArtifact.abi, userA);
  const receiverB = new ethers.Contract(deployment.chainB.receiver, receiverArtifact.abi, userB);

  const relayProc = spawn("node", ["relay-server/index.js"], {
    cwd: ROOT,
    stdio: ["ignore", "pipe", "pipe"]
  });

  relayProc.stdout.on("data", (d) => process.stdout.write(`[relay] ${d}`));
  relayProc.stderr.on("data", (d) => process.stderr.write(`[relay-err] ${d}`));

  await sleep(1500);

  const rows = [];

  try {
    for (let i = 0; i < ROUNDS; i++) {
      const fromA = i % 2 === 0;
      const src = fromA
        ? {
            name: "chainA",
            chainId: Number(deployment.chainA.chainId),
            endpoint: endpointA,
            endpointRelayer: endpointARelayer,
            receiver: receiverB,
            dstName: "chainB",
            dstProvider: providerB,
            dstEndpoint: endpointB,
            srcEndpointAddress: deployment.chainA.endpoint,
            dstReceiverAddress: deployment.chainB.receiver
          }
        : {
            name: "chainB",
            chainId: Number(deployment.chainB.chainId),
            endpoint: endpointB,
            endpointRelayer: endpointBRelayer,
            receiver: receiverA,
            dstName: "chainA",
            dstProvider: providerA,
            dstEndpoint: endpointA,
            srcEndpointAddress: deployment.chainB.endpoint,
            dstReceiverAddress: deployment.chainA.receiver
          };

      const isDataTask = i % 3 !== 0;
      const iface = src.receiver.interface;

      const payload = isDataTask
        ? iface.encodeFunctionData("handleDataTask", [src.chainId, 100 + i, `sensor-${i}`])
        : iface.encodeFunctionData("handleComputeTask", [
            src.chainId,
            10 + i,
            2 + (i % 5),
            i % 2 === 0 ? "mul" : "pow2sum"
          ]);

      const beforeBlock = await src.dstProvider.getBlockNumber();
      const t0 = Date.now();
      const sendTx = await src.endpoint.sendMessage(
        fromA ? Number(deployment.chainB.chainId) : Number(deployment.chainA.chainId),
        src.dstReceiverAddress,
        payload
      );
      const sendRc = await sendTx.wait();
      const req = parseRelayRequested(sendRc, src.endpoint.interface);

      const relayEvent = await waitForRelayExecuted(
        src.dstEndpoint,
        req.msgId,
        beforeBlock,
        TIMEOUT_MS
      );
      const execRc = await relayEvent.getTransactionReceipt();

      const latencyMs = Date.now() - t0;
      const ok = relayEvent.args.ok;
      if (!ok) {
        throw new Error(`relay execution returned ok=false for msgId ${req.msgId}`);
      }

      rows.push({
        round: i,
        direction: `${src.name}->${src.dstName}`,
        taskType: isDataTask ? "data" : "compute",
        msgId: req.msgId,
        sendGas: Number(sendRc.gasUsed),
        executeGas: Number(execRc.gasUsed),
        totalGas: Number(sendRc.gasUsed) + Number(execRc.gasUsed),
        latencyMs,
        sendTxHash: sendRc.hash,
        executeTxHash: execRc.hash
      });
    }

    // idempotency check: replay an already executed message manually should revert
    const probe = rows[0];
    const replaySourceIsA = probe.direction.startsWith("chainA");
    const srcChainId = replaySourceIsA
      ? Number(deployment.chainA.chainId)
      : Number(deployment.chainB.chainId);
    const srcEndpoint = replaySourceIsA
      ? deployment.chainA.endpoint
      : deployment.chainB.endpoint;
    const dstEndpointRelayer = replaySourceIsA ? endpointBRelayer : endpointARelayer;

    const sendReceipt = await (replaySourceIsA ? providerA : providerB).getTransactionReceipt(
      probe.sendTxHash
    );
    const endpointIface = new ethers.Interface(endpointArtifact.abi);
    const req = parseRelayRequested(sendReceipt, endpointIface);

    let replayReverted = false;
    try {
      await dstEndpointRelayer.executeMessage(
        req.msgId,
        srcChainId,
        srcEndpoint,
        req.srcSender,
        req.dstReceiver,
        req.nonce,
        req.payload
      );
    } catch (err) {
      replayReverted = true;
    }

    const report = {
      generatedAt: new Date().toISOString(),
      rounds: ROUNDS,
      summary: {
        avgSendGas: mean(rows.map((r) => r.sendGas)),
        avgExecuteGas: mean(rows.map((r) => r.executeGas)),
        avgTotalGas: mean(rows.map((r) => r.totalGas)),
        avgLatencyMs: mean(rows.map((r) => r.latencyMs)),
        p95LatencyMs: rows
          .map((r) => r.latencyMs)
          .sort((a, b) => a - b)[Math.max(0, Math.ceil(rows.length * 0.95) - 1)],
        replayProtectionWorks: replayReverted
      },
      rows
    };

    const out = path.join(DEPLOY_DIR, "relay-experiment-report.json");
    writeJson(out, report);

    console.log("experiment done:", out);
    console.table(
      rows.map((r) => ({
        round: r.round,
        dir: r.direction,
        type: r.taskType,
        latencyMs: r.latencyMs,
        totalGas: r.totalGas
      }))
    );
    console.log(report.summary);
  } finally {
    relayProc.kill("SIGTERM");
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
