const fs = require("fs");
const path = require("path");
const { ethers } = require("ethers");
const {
  ROOT,
  DEPLOYMENTS_DIR,
  RUNTIME_DIR,
  loadJson,
  writeJson,
  deriveWallet
} = require("../../experiment/scripts/common");

const RELAY_DOMAIN = ethers.id("BPMN_SPLIT_RELAY_V1");

function splitDeploymentPath() {
  return path.join(DEPLOYMENTS_DIR, "split-generated-addresses.json");
}

function splitRelayerStatePath() {
  return path.join(RUNTIME_DIR, "split-relayer-state.json");
}

function loadArtifact(contractName) {
  const p = path.join(
    ROOT,
    "artifacts",
    "contracts",
    "generated",
    `${contractName}.sol`,
    `${contractName}.json`
  );
  if (!fs.existsSync(p)) {
    throw new Error(`artifact not found: ${p}. run npm run compile`);
  }
  return loadJson(p);
}

function loadState() {
  const p = splitRelayerStatePath();
  if (!fs.existsSync(p)) {
    return {
      generatedAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      perCase: {}
    };
  }
  return loadJson(p);
}

function saveState(state) {
  state.updatedAt = new Date().toISOString();
  writeJson(splitRelayerStatePath(), state);
}

function pickErr(err) {
  return err?.shortMessage || err?.info?.error?.message || err?.message || "unknown";
}

function taskKey(taskId) {
  return String(taskId || "").toLowerCase();
}

async function buildRelaySignature(relayer, payload) {
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

async function createContext() {
  const deploymentFile = splitDeploymentPath();
  if (!fs.existsSync(deploymentFile)) {
    throw new Error(`split deployment not found: ${deploymentFile}. run npm run deploy:split`);
  }
  const deployment = loadJson(deploymentFile);
  const sourceProvider = new ethers.JsonRpcProvider(deployment.sourceChain.rpcUrl);
  const targetProvider = new ethers.JsonRpcProvider(deployment.targetChain.rpcUrl);
  sourceProvider.pollingInterval = 200;
  targetProvider.pollingInterval = 200;

  const relayerWallet = deriveWallet(
    deployment.derivation.mnemonic,
    deployment.derivation.relayerIndex,
    targetProvider
  );
  const relayerTxSigner = new ethers.NonceManager(relayerWallet);

  const caseContracts = new Map();
  for (const c of deployment.cases || []) {
    const sourceArtifact = loadArtifact(c.source.contractName);
    const targetArtifact = loadArtifact(c.target.contractName);
    const source = new ethers.Contract(c.source.contractAddress, sourceArtifact.abi, sourceProvider);
    const target = new ethers.Contract(c.target.contractAddress, targetArtifact.abi, relayerTxSigner);
    caseContracts.set(c.caseId, { meta: c, source, target });
  }

  return {
    deployment,
    sourceProvider,
    targetProvider,
    relayerWallet,
    relayerTxSigner,
    caseContracts
  };
}

async function relayCase({
  caseId,
  state,
  ctx,
  confirmations
}) {
  const handle = ctx.caseContracts.get(caseId);
  if (!handle) {
    return { caseId, scannedFrom: 0, scannedTo: 0, events: 0, relayed: 0, skipped: 0, errors: 0 };
  }
  const { meta, source, target } = handle;
  const caseState = state.perCase[caseId] || {
    sourceLastScannedBlock: Number(meta.source.deployBlock || 0),
    relayedTasks: {}
  };

  const latest = await ctx.sourceProvider.getBlockNumber();
  const scannedTo = latest - Math.max(0, Number(confirmations || 0));
  const scannedFrom = Math.max(
    Number(caseState.sourceLastScannedBlock || 0) + 1,
    Number(meta.source.deployBlock || 0)
  );
  if (scannedTo < scannedFrom) {
    state.perCase[caseId] = caseState;
    return { caseId, scannedFrom, scannedTo, events: 0, relayed: 0, skipped: 0, errors: 0 };
  }

  const logs = await source.queryFilter(source.filters.HandoffRequested(), scannedFrom, scannedTo);
  let relayed = 0;
  let skipped = 0;
  let errors = 0;

  for (const ev of logs) {
    const taskId = ev.args.taskId;
    const key = taskKey(taskId);
    if (caseState.relayedTasks[key]) {
      skipped += 1;
      continue;
    }

    const payloadHash = ev.args.payloadHash;
    const sourceChainId = Number(ev.args.sourceChainId?.toString?.() || meta.source.chainId);
    const sourceContract = meta.source.contractAddress;
    try {
      const sig = await buildRelaySignature(ctx.relayerWallet, {
        targetContract: meta.target.contractAddress,
        targetChainId: Number(meta.target.chainId),
        sourceChainId,
        sourceContract,
        taskId,
        payloadHash
      });
      const signatures = [sig];
      const tx = await target.acceptHandoff(
        taskId,
        payloadHash,
        sourceChainId,
        sourceContract,
        Number(meta.target.chainId),
        signatures
      );
      const rc = await tx.wait();
      caseState.relayedTasks[key] = {
        relayedAt: new Date().toISOString(),
        txHash: tx.hash,
        blockNumber: rc?.blockNumber || null,
        payloadHash
      };
      relayed += 1;
    } catch (err) {
      const msg = pickErr(err);
      if (msg.includes("task already processed")) {
        caseState.relayedTasks[key] = {
          relayedAt: new Date().toISOString(),
          txHash: null,
          blockNumber: null,
          payloadHash,
          note: "already processed"
        };
        skipped += 1;
      } else {
        errors += 1;
        console.error(`[split-worker] case=${caseId} task=${taskId} relay failed: ${msg}`);
      }
    }
  }

  caseState.sourceLastScannedBlock = scannedTo;
  state.perCase[caseId] = caseState;
  return { caseId, scannedFrom, scannedTo, events: logs.length, relayed, skipped, errors };
}

async function relayOnce(ctx, state, confirmations) {
  const summaries = [];
  for (const caseId of ctx.caseContracts.keys()) {
    summaries.push(
      await relayCase({
        caseId,
        state,
        ctx,
        confirmations
      })
    );
  }
  saveState(state);
  return summaries;
}

async function runForever() {
  const pollMs = Number(process.env.RELAYER_POLL_MS || 1000);
  const confirmations = Number(process.env.RELAYER_CONFIRMATIONS || 0);
  const ctx = await createContext();
  const state = loadState();
  console.log(
    `[split-worker] start poll=${pollMs}ms confirmations=${confirmations} cases=${ctx.caseContracts.size}`
  );
  while (true) {
    try {
      const summaries = await relayOnce(ctx, state, confirmations);
      const relayed = summaries.reduce((acc, x) => acc + Number(x.relayed || 0), 0);
      const errors = summaries.reduce((acc, x) => acc + Number(x.errors || 0), 0);
      if (relayed > 0 || errors > 0) {
        console.log(
          `[split-worker] cycle relayed=${relayed} errors=${errors} details=${JSON.stringify(summaries)}`
        );
      }
    } catch (err) {
      console.error(`[split-worker] cycle error: ${pickErr(err)}`);
    }
    await new Promise((resolve) => setTimeout(resolve, pollMs));
  }
}

async function runOnce() {
  const confirmations = Number(process.env.RELAYER_CONFIRMATIONS || 0);
  const ctx = await createContext();
  const state = loadState();
  const summaries = await relayOnce(ctx, state, confirmations);
  console.log(JSON.stringify({ confirmations, summaries }, null, 2));
}

if (require.main === module) {
  if (process.argv.includes("--once")) {
    runOnce().catch((err) => {
      console.error(err);
      process.exit(1);
    });
  } else {
    runForever().catch((err) => {
      console.error(err);
      process.exit(1);
    });
  }
}

module.exports = {
  RELAY_DOMAIN,
  relayOnce,
  buildRelaySignature
};
