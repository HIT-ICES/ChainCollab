const fs = require("fs");
const path = require("path");
const { ethers } = require("ethers");
const {
  ROOT,
  loadJson,
  writeJson,
  relayerStatePath,
  loadDeployment,
  deriveWallet
} = require("../../experiment/scripts/common");

const RELAY_DOMAIN = ethers.id("RELAY_EXECUTION_V1");

function loadArtifact(relativePath) {
  const full = path.join(ROOT, "artifacts", relativePath);
  if (!fs.existsSync(full)) {
    throw new Error(`artifact not found: ${full}. run npm run compile`);
  }
  return loadJson(full);
}

function loadState() {
  const p = relayerStatePath();
  if (!fs.existsSync(p)) {
    return {
      sourceLastScannedBlock: 0,
      relayedTasks: {}
    };
  }
  return loadJson(p);
}

function saveState(state) {
  writeJson(relayerStatePath(), state);
}

async function buildRelaySignature(relayerSigner, payload) {
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
  return relayerSigner.signMessage(ethers.getBytes(digest));
}

async function relayOnce() {
  const deployment = loadDeployment();
  const state = loadState();

  const sourceProvider = new ethers.JsonRpcProvider(deployment.source.rpcUrl);
  const targetProvider = new ethers.JsonRpcProvider(deployment.target.rpcUrl);
  const relayerSigner = new ethers.NonceManager(
    deriveWallet(
      deployment.derivation.mnemonic,
      deployment.derivation.relayerIndex,
      targetProvider
    )
  );

  const sourceArtifact = loadArtifact(
    "contracts/SourceTaskEmitter.sol/SourceTaskEmitter.json"
  );
  const targetArtifact = loadArtifact(
    "contracts/TargetTaskReceiver.sol/TargetTaskReceiver.json"
  );

  const source = new ethers.Contract(
    deployment.source.contract,
    sourceArtifact.abi,
    sourceProvider
  );
  const target = new ethers.Contract(
    deployment.target.contract,
    targetArtifact.abi,
    relayerSigner
  );

  const latest = await sourceProvider.getBlockNumber();
  const fromBlock = Math.max(
    Number(state.sourceLastScannedBlock || 0) + 1,
    Number(deployment.source.deployBlock || 0)
  );

  if (fromBlock > latest) {
    state.sourceLastScannedBlock = latest;
    saveState(state);
    return {
      scannedFrom: fromBlock,
      scannedTo: latest,
      events: 0,
      relayed: 0,
      skipped: 0
    };
  }

  const logs = await source.queryFilter(source.filters.TaskRequested(), fromBlock, latest);

  let relayed = 0;
  let skipped = 0;

  for (const ev of logs) {
    const taskId = ev.args.taskId;
    const payloadHash = ev.args.payloadHash;
    const sourceChainId = Number(ev.args.sourceChainId.toString());
    const sourceContract = deployment.source.contract;

    if (state.relayedTasks[taskId]) {
      skipped += 1;
      continue;
    }

    const sig = await buildRelaySignature(relayerSigner, {
      targetContract: deployment.target.contract,
      targetChainId: Number(deployment.target.chainId),
      sourceChainId,
      sourceContract,
      taskId,
      payloadHash
    });

    try {
      const tx = await target.relayTask(
        taskId,
        payloadHash,
        sourceChainId,
        sourceContract,
        sig
      );
      await tx.wait();
      state.relayedTasks[taskId] = {
        relayedAt: new Date().toISOString(),
        txHash: tx.hash
      };
      relayed += 1;
    } catch (err) {
      const msg = err?.shortMessage || err?.message || "relay error";
      if (msg.includes("task already processed")) {
        state.relayedTasks[taskId] = {
          relayedAt: new Date().toISOString(),
          txHash: null,
          note: "already processed"
        };
        skipped += 1;
      } else {
        throw err;
      }
    }
  }

  state.sourceLastScannedBlock = latest;
  saveState(state);

  return {
    scannedFrom: fromBlock,
    scannedTo: latest,
    events: logs.length,
    relayed,
    skipped
  };
}

async function runForever() {
  const intervalMs = Number(process.env.RELAYER_POLL_MS || 1500);
  console.log(`relayer worker start. poll=${intervalMs}ms`);
  while (true) {
    try {
      const summary = await relayOnce();
      if (summary.events > 0) {
        console.log("relay summary", summary);
      }
    } catch (err) {
      console.error("relay loop error", err?.shortMessage || err?.message || err);
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}

if (require.main === module) {
  if (process.argv.includes("--once")) {
    relayOnce()
      .then((summary) => {
        console.log(summary);
      })
      .catch((err) => {
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
  relayOnce,
  buildRelaySignature,
  RELAY_DOMAIN
};
