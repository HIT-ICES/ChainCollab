const http = require("http");
const { ethers } = require("ethers");
const {
  DEFAULTS,
  readArtifact,
  readDeployment
} = require("../scripts/common");

const POLL_MS = Number(process.env.RELAYER_POLL_MS || 1500);
const MAX_RETRIES = Number(process.env.RELAYER_MAX_RETRIES || 8);
const BASE_RETRY_MS = Number(process.env.RELAYER_RETRY_MS || 1000);
const PORT = Number(process.env.RELAYER_PORT || 18888);
const EXEC_GAS_LIMIT = Number(process.env.RELAYER_EXEC_GAS_LIMIT || 1500000);

const pending = [];
let processing = false;
const seen = new Set();

const metrics = {
  startedAt: new Date().toISOString(),
  enqueued: 0,
  relayed: 0,
  failed: 0,
  retries: 0,
  duplicateDropped: 0,
  lastError: null,
  lastRelay: null,
  perDirection: {}
};

function directionKey(src, dst) {
  return `${src}->${dst}`;
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

function parseRelayExecuted(receipt, endpointContract, expectedMsgId) {
  for (const log of receipt.logs) {
    try {
      const parsed = endpointContract.interface.parseLog(log);
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
      const ok = parsed.args.ok != null ? Boolean(parsed.args.ok) : Boolean(parsed.args[1]);
      const returnData =
        parsed.args.returnData != null ? parsed.args.returnData : parsed.args[2];
      return { ok, returnData };
    } catch (err) {
      // ignore non-endpoint log
    }
  }
  throw new Error("RelayExecuted event not found in receipt");
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function encodeJobKey(job) {
  return `${job.srcName}:${job.msgId}`;
}

function enqueue(job) {
  const key = encodeJobKey(job);
  if (seen.has(key)) {
    metrics.duplicateDropped += 1;
    return false;
  }
  seen.add(key);
  metrics.enqueued += 1;
  pending.push(job);
  return true;
}

async function processQueue(targetContracts) {
  if (processing) return;
  processing = true;
  try {
    while (pending.length > 0) {
      const job = pending[0];
      const t0 = Date.now();
      const dirKey = directionKey(job.srcName, job.dstName);
      if (!metrics.perDirection[dirKey]) {
        metrics.perDirection[dirKey] = {
          relayed: 0,
          failed: 0,
          retries: 0,
          avgLatencyMs: 0
        };
      }

      try {
        const target = targetContracts[job.dstName];
        const tx = await target.executeMessage(
          job.msgId,
          job.srcChainId,
          job.srcEndpoint,
          job.srcSender,
          job.dstReceiver,
          job.nonce,
          job.payload,
          { gasLimit: EXEC_GAS_LIMIT }
        );
        const rc = await tx.wait();
        const exec = parseRelayExecuted(rc, target, job.msgId);
        if (!exec.ok) {
          const reason = decodeRevertReason(exec.returnData);
          throw new Error(`target call reverted: ${reason}`);
        }

        const latency = Date.now() - job.observedAt;
        const duration = Date.now() - t0;

        metrics.relayed += 1;
        const pd = metrics.perDirection[dirKey];
        pd.relayed += 1;
        pd.avgLatencyMs =
          pd.relayed === 1
            ? latency
            : (pd.avgLatencyMs * (pd.relayed - 1) + latency) / pd.relayed;

        metrics.lastRelay = {
          at: new Date().toISOString(),
          msgId: job.msgId,
          direction: dirKey,
          txHash: rc.hash,
          gasUsed: rc.gasUsed.toString(),
          relayDurationMs: duration,
          observedToMinedMs: latency
        };

        console.log(
          `[relay] ok ${dirKey} msgId=${job.msgId} tx=${rc.hash} gas=${rc.gasUsed}`
        );

        pending.shift();
      } catch (err) {
        job.retries += 1;
        metrics.retries += 1;
        metrics.lastError = {
          at: new Date().toISOString(),
          msgId: job.msgId,
          direction: dirKey,
          error: err.message || String(err)
        };

        if (job.retries > MAX_RETRIES) {
          metrics.failed += 1;
          metrics.perDirection[dirKey].failed += 1;
          console.error(
            `[relay] fail ${dirKey} msgId=${job.msgId} retries=${job.retries} error=${err.message}`
          );
          pending.shift();
          continue;
        }

        metrics.perDirection[dirKey].retries += 1;
        const backoff = BASE_RETRY_MS * Math.min(job.retries, 6);
        console.warn(
          `[relay] retry ${dirKey} msgId=${job.msgId} retries=${job.retries} waitMs=${backoff} error=${err.message}`
        );
        await sleep(backoff);
      }
    }
  } finally {
    processing = false;
  }
}

function attachListeners(source, destination, sourceContract) {
  sourceContract.on(
    "RelayRequested",
    (msgId, dstChainId, dstReceiver, srcSender, payload, nonce, event) => {
      const dstChain = Number(dstChainId);
      if (dstChain !== destination.chainId) {
        return;
      }

      const job = {
        msgId,
        srcName: source.name,
        dstName: destination.name,
        srcChainId: source.chainId,
        srcEndpoint: source.endpoint,
        srcSender,
        dstReceiver,
        payload,
        nonce,
        observedAt: Date.now(),
        srcBlockNumber: event.log.blockNumber,
        srcTxHash: event.log.transactionHash,
        retries: 0
      };

      if (enqueue(job)) {
        console.log(
          `[relay] enqueue ${source.name}->${destination.name} msgId=${msgId} srcTx=${event.log.transactionHash}`
        );
      }
    }
  );
}

function startHttpServer() {
  const server = http.createServer((req, res) => {
    res.setHeader("Content-Type", "application/json; charset=utf-8");

    if (req.method === "GET" && req.url === "/health") {
      res.end(JSON.stringify({ ok: true, now: new Date().toISOString() }));
      return;
    }

    if (req.method === "GET" && req.url === "/metrics") {
      res.end(JSON.stringify(metrics, null, 2));
      return;
    }

    if (req.method === "GET" && req.url === "/queue") {
      res.end(
        JSON.stringify(
          {
            pending: pending.length,
            items: pending.map((j) => ({
              msgId: j.msgId,
              direction: directionKey(j.srcName, j.dstName),
              retries: j.retries,
              srcTxHash: j.srcTxHash
            }))
          },
          null,
          2
        )
      );
      return;
    }

    res.statusCode = 404;
    res.end(JSON.stringify({ error: "not found" }));
  });

  server.listen(PORT, "127.0.0.1", () => {
    console.log(`[relay] api http://127.0.0.1:${PORT}`);
  });

  return server;
}

async function main() {
  const deployment = readDeployment();
  const endpointArtifact = readArtifact("CrossChainEndpoint");

  const chainA = {
    name: deployment.chainA.name,
    chainId: Number(deployment.chainA.chainId),
    rpcUrl: deployment.chainA.rpcUrl || DEFAULTS.chainA.rpcUrl,
    endpoint: deployment.chainA.endpoint
  };

  const chainB = {
    name: deployment.chainB.name,
    chainId: Number(deployment.chainB.chainId),
    rpcUrl: deployment.chainB.rpcUrl || DEFAULTS.chainB.rpcUrl,
    endpoint: deployment.chainB.endpoint
  };

  const providerA = new ethers.JsonRpcProvider(chainA.rpcUrl);
  const providerB = new ethers.JsonRpcProvider(chainB.rpcUrl);
  const relayerA = new ethers.Wallet(DEFAULTS.keys.relayer, providerA);
  const relayerB = new ethers.Wallet(DEFAULTS.keys.relayer, providerB);

  const sourceA = new ethers.Contract(chainA.endpoint, endpointArtifact.abi, providerA);
  const sourceB = new ethers.Contract(chainB.endpoint, endpointArtifact.abi, providerB);
  const targetA = new ethers.Contract(chainA.endpoint, endpointArtifact.abi, relayerA);
  const targetB = new ethers.Contract(chainB.endpoint, endpointArtifact.abi, relayerB);

  console.log(`[relay] ready chainA=${chainA.rpcUrl} endpoint=${chainA.endpoint}`);
  console.log(`[relay] ready chainB=${chainB.rpcUrl} endpoint=${chainB.endpoint}`);

  attachListeners(chainA, chainB, sourceA);
  attachListeners(chainB, chainA, sourceB);

  const httpServer = startHttpServer();

  const timer = setInterval(() => {
    processQueue({ [chainA.name]: targetA, [chainB.name]: targetB }).catch((err) => {
      metrics.lastError = {
        at: new Date().toISOString(),
        error: err.message || String(err)
      };
      console.error(`[relay] queue loop error: ${err.message}`);
    });
  }, POLL_MS);

  const shutdown = async () => {
    clearInterval(timer);
    httpServer.close();
    sourceA.removeAllListeners();
    sourceB.removeAllListeners();
    console.log("[relay] stopped");
    process.exit(0);
  };

  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
