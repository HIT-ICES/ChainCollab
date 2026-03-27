import { ethers } from "ethers";
import { readBuildArtifact, readDeployment } from "./common.js";
import { executeTaskSpec, toChainString } from "./compute-task-executor.js";

const REQUESTED = 1;
const POLL_MS = Number(process.env.WORKER_POLL_MS || 3000);

function readJsonPath(payload, jsonPath) {
  if (!jsonPath || jsonPath === ".") {
    return payload;
  }
  const parts = jsonPath.split(".").filter(Boolean);
  let current = payload;
  for (const part of parts) {
    if (current == null || !(part in current)) {
      throw new Error(`jsonPath not found: ${jsonPath}`);
    }
    current = current[part];
  }
  return current;
}

function truncate(text, max = 240) {
  const source = String(text || "");
  if (source.length <= max) {
    return source;
  }
  return `${source.slice(0, max - 3)}...`;
}

async function processExternalTask(dataHub, taskId) {
  const task = await dataHub.tasks(taskId);
  if (Number(task.status) !== REQUESTED) {
    return false;
  }

  try {
    const resp = await fetch(task.sourceUrl);
    if (!resp.ok) {
      throw new Error(`source http ${resp.status}`);
    }
    const payload = await resp.json();
    const raw = readJsonPath(payload, task.jsonPath);
    const value = typeof raw === "string" ? raw : JSON.stringify(raw);
    const tx = await dataHub.fulfillExternalDataTask(taskId, value);
    const rc = await tx.wait();
    console.log(
      `[external] fulfilled task=${taskId} slot=${task.slotKey} value=${value} gas=${rc.gasUsed}`
    );
    return true;
  } catch (err) {
    const reason = truncate(err.message || String(err));
    const tx = await dataHub.failExternalDataTask(taskId, reason);
    await tx.wait();
    console.log(`[external] failed task=${taskId} reason=${reason}`);
    return true;
  }
}

async function processComputeTask(computeHub, slotRegistry, taskId) {
  const task = await computeHub.getTask(taskId);
  if (Number(task.statusCode) !== REQUESTED) {
    return false;
  }

  try {
    const inputSlotKeys = await computeHub.getTaskInputSlotKeys(taskId);
    const values = {};
    for (let i = 0; i < inputSlotKeys.length; i++) {
      const key = inputSlotKeys[i];
      const [exists, value] = await slotRegistry.getSlot(key);
      if (!exists) {
        throw new Error(`missing input slot ${key}`);
      }
      const numeric = Number(value);
      values[`x${i}`] = Number.isFinite(numeric) ? numeric : value;
    }

    const computed = executeTaskSpec(task.expression, values);
    const result = toChainString(computed);

    const tx = await computeHub.fulfillComputeTask(taskId, result);
    const rc = await tx.wait();
    console.log(
      `[compute] fulfilled task=${taskId} output=${task.outputSlotKey} result=${result} gas=${rc.gasUsed}`
    );
    return true;
  } catch (err) {
    const reason = truncate(err.message || String(err));
    const tx = await computeHub.failComputeTask(taskId, reason);
    await tx.wait();
    console.log(`[compute] failed task=${taskId} reason=${reason}`);
    return true;
  }
}

async function drainPending(dataHub, computeHub, slotRegistry) {
  let processed = 0;
  const maxExternal = Number(await dataHub.nextTaskId());
  const maxCompute = Number(await computeHub.nextTaskId());
  for (let i = 0; i < maxExternal; i++) {
    if (await processExternalTask(dataHub, i)) {
      processed += 1;
    }
  }
  for (let i = 0; i < maxCompute; i++) {
    if (await processComputeTask(computeHub, slotRegistry, i)) {
      processed += 1;
    }
  }
  return processed;
}

async function main() {
  const deployment = readDeployment();
  const dataArtifact = readBuildArtifact("DataOracleHub");
  const computeArtifact = readBuildArtifact("ComputeOracleHub");
  const slotArtifact = readBuildArtifact("SlotRegistry");
  const rpcUrl = process.env.RPC_URL || "http://127.0.0.1:8545";
  const relayerIndex = Number(process.env.RELAYER_INDEX || 1);
  const once = process.argv.includes("--once");

  const provider = new ethers.JsonRpcProvider(rpcUrl);
  const signer = await provider.getSigner(relayerIndex);

  const dataHub = new ethers.Contract(
    deployment.contracts.dataOracleHub.address,
    dataArtifact.abi,
    signer
  );
  const computeHub = new ethers.Contract(
    deployment.contracts.computeOracleHub.address,
    computeArtifact.abi,
    signer
  );
  const slotRegistry = new ethers.Contract(
    deployment.contracts.slotRegistry.address,
    slotArtifact.abi,
    signer
  );

  console.log(
    `worker connected rpc=${rpcUrl} dataHub=${deployment.contracts.dataOracleHub.address} computeHub=${deployment.contracts.computeOracleHub.address} signer=${await signer.getAddress()}`
  );

  if (once) {
    const count = await drainPending(dataHub, computeHub, slotRegistry);
    console.log(`worker once done processed=${count}`);
    return;
  }

  dataHub.on("ExternalDataTaskRequested", async (taskId) => {
    await processExternalTask(dataHub, Number(taskId));
  });
  computeHub.on("ComputeTaskRequested", async (taskId) => {
    await processComputeTask(computeHub, slotRegistry, Number(taskId));
  });

  console.log(`worker running poll=${POLL_MS}ms`);
  setInterval(async () => {
    try {
      const count = await drainPending(dataHub, computeHub, slotRegistry);
      if (count > 0) {
        console.log(`worker polled and processed=${count}`);
      }
    } catch (err) {
      console.error("worker poll error:", err);
    }
  }, POLL_MS);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
