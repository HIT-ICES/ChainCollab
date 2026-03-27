import fs from "fs";
import path from "path";
import hre from "hardhat";
import { readBuildArtifact, readDeployment, toSlotKey } from "./common.js";
import {
  encodeDslTask,
  executeTaskSpec,
  toChainString
} from "./compute-task-executor.js";

const { ethers } = hre;

function mean(values) {
  if (!values.length) return 0;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

async function main() {
  const deployment = readDeployment();
  if (!deployment.contracts?.computeOracleHub?.address) {
    throw new Error("computeOracleHub missing in deployment. run npm run deploy first");
  }
  if (!deployment.contracts?.slotRegistry?.address) {
    throw new Error("slotRegistry missing in deployment. run npm run deploy first");
  }
  if (!deployment.contracts?.computeCostLab?.address) {
    throw new Error("computeCostLab missing in deployment. run npm run deploy first");
  }

  const rounds = Number(process.env.COMPUTE_ROUNDS || 15);
  const heavyLoops = Number(process.env.HEAVY_LOOPS || 600);
  const expression = encodeDslTask({
    kind: "numeric",
    cast: "number",
    expr: {
      op: "div",
      args: [
        {
          op: "add",
          args: [
            { op: "mul", args: [{ var: "x0" }, { const: 2 }] },
            { var: "x1" }
          ]
        },
        { const: 10 }
      ]
    }
  });

  const [owner, relayer, user] = await ethers.getSigners();
  const slotArtifact = readBuildArtifact("SlotRegistry");
  const computeHubArtifact = readBuildArtifact("ComputeOracleHub");
  const computeCostArtifact = readBuildArtifact("ComputeCostLab");

  const slotRegistry = new ethers.Contract(
    deployment.contracts.slotRegistry.address,
    slotArtifact.abi,
    owner
  );
  const computeHub = new ethers.Contract(
    deployment.contracts.computeOracleHub.address,
    computeHubArtifact.abi,
    owner
  );
  const computeCostLab = new ethers.Contract(
    deployment.contracts.computeCostLab.address,
    computeCostArtifact.abi,
    owner
  );

  const slotX0 = toSlotKey("bench.compute.input.x0");
  const slotX1 = toSlotKey("bench.compute.input.x1");
  const outputPrefix = "bench.compute.output";

  const x0 = 2500;
  const x1 = 50000;
  await (await slotRegistry.connect(owner).setSlot(slotX0, String(x0), "bench-input")).wait();
  await (await slotRegistry.connect(owner).setSlot(slotX1, String(x1), "bench-input")).wait();

  const offchainRequestGas = [];
  const offchainFulfillGas = [];
  const offchainCpuNs = [];
  const onchainGas = [];
  const onchainHeavyGas = [];

  for (let i = 0; i < rounds; i++) {
    const outSlot = toSlotKey(`${outputPrefix}.${i}`);
    const taskId = Number(await computeHub.nextTaskId());
    const txReq = await computeHub
      .connect(user)
      .requestComputeTask(outSlot, expression, [slotX0, slotX1]);
    const rcReq = await txReq.wait();
    offchainRequestGas.push(Number(rcReq.gasUsed));

    const t0 = process.hrtime.bigint();
    const result = executeTaskSpec(expression, { x0, x1 });
    const t1 = process.hrtime.bigint();
    offchainCpuNs.push(Number(t1 - t0));

    const txFulfill = await computeHub
      .connect(relayer)
      .fulfillComputeTask(taskId, toChainString(result));
    const rcFulfill = await txFulfill.wait();
    offchainFulfillGas.push(Number(rcFulfill.gasUsed));

    const txOn = await computeCostLab.connect(user).computeRiskOnChain(x0, x1);
    const rcOn = await txOn.wait();
    onchainGas.push(Number(rcOn.gasUsed));

    const txHeavy = await computeCostLab
      .connect(user)
      .computeRiskHeavyOnChain(x0, x1, heavyLoops);
    const rcHeavy = await txHeavy.wait();
    onchainHeavyGas.push(Number(rcHeavy.gasUsed));
  }

  const report = {
    rounds,
    heavyLoops,
    expression,
    inputs: { x0, x1 },
    offchain: {
      avgRequestGas: mean(offchainRequestGas),
      avgFulfillGas: mean(offchainFulfillGas),
      avgTotalGas: mean(
        offchainRequestGas.map((v, i) => v + offchainFulfillGas[i])
      ),
      avgCpuNs: mean(offchainCpuNs),
      avgCpuMs: mean(offchainCpuNs) / 1e6
    },
    onchain: {
      avgDirectGas: mean(onchainGas),
      avgHeavyGas: mean(onchainHeavyGas)
    }
  };

  const outPath = path.resolve("deployments/compute-cost-report.json");
  fs.writeFileSync(outPath, JSON.stringify(report, null, 2));

  console.log("compute-cost experiment done:", outPath);
  console.table([
    {
      metric: "offchain_total_gas(avg)",
      value: Math.round(report.offchain.avgTotalGas)
    },
    {
      metric: "offchain_cpu_ms(avg)",
      value: report.offchain.avgCpuMs.toFixed(6)
    },
    {
      metric: "onchain_direct_gas(avg)",
      value: Math.round(report.onchain.avgDirectGas)
    },
    {
      metric: `onchain_heavy_gas(avg,loops=${heavyLoops})`,
      value: Math.round(report.onchain.avgHeavyGas)
    }
  ]);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
