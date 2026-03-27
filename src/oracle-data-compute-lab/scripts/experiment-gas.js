import fs from "fs";
import path from "path";
import hre from "hardhat";
import {
  DEPLOYMENT_FILE,
  fmtGas,
  readBuildArtifact,
  readDeployment,
  toSlotKey,
  writeDeployment
} from "./common.js";
import {
  encodeDslTask,
  executeTaskSpec,
  toChainString
} from "./compute-task-executor.js";

const REQUESTED = 1;
const { ethers } = hre;

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

async function deployIfMissing() {
  if (fs.existsSync(DEPLOYMENT_FILE)) {
    const existing = readDeployment();
    if (existing.contracts?.dataOracleHub?.address && existing.contracts?.computeOracleHub?.address) {
      return existing;
    }
  }

  const [owner, relayer, user] = await ethers.getSigners();
  const slotArtifact = readBuildArtifact("SlotRegistry");
  const dataArtifact = readBuildArtifact("DataOracleHub");
  const computeArtifact = readBuildArtifact("ComputeOracleHub");

  const slotFactory = new ethers.ContractFactory(slotArtifact.abi, slotArtifact.bytecode, owner);
  const slotRegistry = await slotFactory.deploy();
  await slotRegistry.waitForDeployment();

  const dataFactory = new ethers.ContractFactory(dataArtifact.abi, dataArtifact.bytecode, owner);
  const dataHub = await dataFactory.deploy(await slotRegistry.getAddress());
  await dataHub.waitForDeployment();

  const computeFactory = new ethers.ContractFactory(computeArtifact.abi, computeArtifact.bytecode, owner);
  const computeHub = await computeFactory.deploy(await slotRegistry.getAddress());
  await computeHub.waitForDeployment();

  await (await slotRegistry.connect(owner).setWriter(await dataHub.getAddress(), true)).wait();
  await (await slotRegistry.connect(owner).setWriter(await computeHub.getAddress(), true)).wait();
  await (await dataHub.connect(owner).setRelayer(relayer.address, true)).wait();
  await (await computeHub.connect(owner).setRelayer(relayer.address, true)).wait();

  const payload = {
    chainId: (await ethers.provider.getNetwork()).chainId.toString(),
    contracts: {
      slotRegistry: { name: "SlotRegistry", address: await slotRegistry.getAddress() },
      dataOracleHub: { name: "DataOracleHub", address: await dataHub.getAddress() },
      computeOracleHub: { name: "ComputeOracleHub", address: await computeHub.getAddress() }
    },
    accounts: {
      owner: owner.address,
      relayer: relayer.address,
      user: user.address
    },
    generatedAt: new Date().toISOString()
  };
  writeDeployment(payload);
  return payload;
}

async function runExternalOnce(dataHub, relayer, gasRows) {
  const maxTasks = Number(await dataHub.nextTaskId());
  for (let i = 0; i < maxTasks; i++) {
    const task = await dataHub.tasks(i);
    if (Number(task.status) !== REQUESTED) {
      continue;
    }
    const resp = await fetch(task.sourceUrl);
    const json = await resp.json();
    const raw = readJsonPath(json, task.jsonPath);
    const value = typeof raw === "string" ? raw : JSON.stringify(raw);
    const tx = await dataHub.connect(relayer).fulfillExternalDataTask(i, value);
    const rc = await tx.wait();
    gasRows.push(fmtGas(rc, `fulfillExternalDataTask#${i}`));
  }
}

async function runComputeOnce(computeHub, slotRegistry, relayer, gasRows) {
  const maxTasks = Number(await computeHub.nextTaskId());
  for (let i = 0; i < maxTasks; i++) {
    const task = await computeHub.getTask(i);
    if (Number(task.statusCode) !== REQUESTED) {
      continue;
    }
    const keys = await computeHub.getTaskInputSlotKeys(i);
    const values = {};
    for (let idx = 0; idx < keys.length; idx++) {
      const [exists, value] = await slotRegistry.getSlot(keys[idx]);
      if (!exists) {
        throw new Error(`missing slot for compute: ${keys[idx]}`);
      }
      const n = Number(value);
      values[`x${idx}`] = Number.isFinite(n) ? n : value;
    }
    const raw = executeTaskSpec(task.expression, values);
    const result = toChainString(raw);
    const tx = await computeHub.connect(relayer).fulfillComputeTask(i, result);
    const rc = await tx.wait();
    gasRows.push(fmtGas(rc, `fulfillComputeTask#${i}`));
  }
}

async function main() {
  const deployment = await deployIfMissing();
  const [owner, relayer, user] = await ethers.getSigners();

  const dataArtifact = readBuildArtifact("DataOracleHub");
  const computeArtifact = readBuildArtifact("ComputeOracleHub");
  const slotArtifact = readBuildArtifact("SlotRegistry");

  const dataHub = new ethers.Contract(
    deployment.contracts.dataOracleHub.address,
    dataArtifact.abi,
    owner
  );
  const computeHub = new ethers.Contract(
    deployment.contracts.computeOracleHub.address,
    computeArtifact.abi,
    owner
  );
  const slotRegistry = new ethers.Contract(
    deployment.contracts.slotRegistry.address,
    slotArtifact.abi,
    owner
  );

  const gasRows = [];
  const sourceBase = process.env.MOCK_SOURCE_URL || "http://127.0.0.1:18080/metrics";

  const slotTemperature = toSlotKey("oracle.external.temperature");
  const slotBtc = toSlotKey("oracle.external.btc_usd");
  const slotRisk = toSlotKey("oracle.compute.risk_score");

  const tx1 = await dataHub
    .connect(user)
    .requestExternalDataTask(slotTemperature, sourceBase, "weather.temperature");
  gasRows.push(fmtGas(await tx1.wait(), "requestExternalDataTask#temperature"));

  const tx2 = await dataHub
    .connect(user)
    .requestExternalDataTask(slotBtc, sourceBase, "market.btc.usd");
  gasRows.push(fmtGas(await tx2.wait(), "requestExternalDataTask#btc"));

  await runExternalOnce(dataHub, relayer, gasRows);

  const computeExpr = encodeDslTask({
    kind: "numeric",
    cast: "number",
    expr: {
      op: "add",
      args: [
        { op: "mul", args: [{ var: "x0" }, { const: 0.2 }] },
        { op: "mul", args: [{ var: "x1" }, { const: 0.00001 }] }
      ]
    }
  });
  const tx3 = await computeHub
    .connect(user)
    .requestComputeTask(slotRisk, computeExpr, [slotTemperature, slotBtc]);
  gasRows.push(fmtGas(await tx3.wait(), "requestComputeTask#risk"));

  await runComputeOnce(computeHub, slotRegistry, relayer, gasRows);

  const [, riskValue] = await slotRegistry.getSlot(slotRisk);
  const result = {
    deployment,
    sourceBase,
    computeExpr,
    final: {
      slotTemperature,
      slotBtc,
      slotRisk,
      riskValue
    },
    gasRows
  };

  const outPath = path.resolve("deployments/gas-report.json");
  fs.writeFileSync(outPath, JSON.stringify(result, null, 2));

  console.log("experiment complete. final risk:", riskValue);
  console.table(
    gasRows.map((r) => ({
      step: r.step,
      gasUsed: r.gasUsed,
      txHash: r.txHash.slice(0, 12)
    }))
  );
  console.log(`gas report saved: ${outPath}`);
  console.log(`owner=${owner.address} relayer=${relayer.address} user=${user.address}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
