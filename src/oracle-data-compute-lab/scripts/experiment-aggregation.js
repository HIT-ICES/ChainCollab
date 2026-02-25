import fs from "fs";
import path from "path";
import hre from "hardhat";
import { readBuildArtifact, readDeployment, toSlotKey } from "./common.js";

const { ethers } = hre;

const METHODS = [
  { name: "MEAN", id: 0 },
  { name: "MEDIAN", id: 1 },
  { name: "TRIMMED_MEAN", id: 2 },
  { name: "WEIGHTED_MEAN", id: 3 }
];

function seededRng(seed) {
  let state = seed >>> 0;
  return () => {
    state = (1664525 * state + 1013904223) >>> 0;
    return state / 0xffffffff;
  };
}

function stddev(values) {
  if (!values.length) return 0;
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const v = values.reduce((a, b) => a + (b - mean) ** 2, 0) / values.length;
  return Math.sqrt(v);
}

function mean(values) {
  if (!values.length) return 0;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

async function ensureOracles(aggregation, oracleSigners, owner) {
  for (const signer of oracleSigners) {
    const addr = await signer.getAddress();
    const enabled = await aggregation.oracles(addr);
    if (!enabled) {
      await (await aggregation.connect(owner).setOracle(addr, true)).wait();
    }
  }
}

async function main() {
  const deployment = readDeployment();
  const aggAddress = deployment.contracts?.dataAggregationLab?.address;
  if (!aggAddress) {
    throw new Error("dataAggregationLab missing in deployment. run npm run deploy first");
  }

  const aggregationArtifact = readBuildArtifact("DataAggregationLab");
  const [owner, ...others] = await ethers.getSigners();
  const oracleSigners = others.slice(0, 5);
  const aggregation = new ethers.Contract(aggAddress, aggregationArtifact.abi, owner);

  await ensureOracles(aggregation, oracleSigners, owner);

  const rounds = Number(process.env.AGG_ROUNDS || 12);
  const trueValue = Number(process.env.AGG_TRUE_VALUE || 1000);
  const trimBps = Number(process.env.AGG_TRIM_BPS || 2000);
  const scenarios = [
    { name: "clean", outlierRate: 0, noiseRange: 8, outlierMagnitude: 0 },
    { name: "outlier", outlierRate: 0.4, noiseRange: 8, outlierMagnitude: 250 }
  ];

  const report = {
    rounds,
    trueValue,
    trimBps,
    methods: METHODS.map((m) => m.name),
    scenarios: {}
  };

  for (const scenario of scenarios) {
    report.scenarios[scenario.name] = {};
    for (const method of METHODS) {
      const rng = seededRng(
        (scenario.name === "clean" ? 1001 : 2003) + method.id * 13
      );
      const results = [];
      const errors = [];
      const gasRequest = [];
      const gasSubmit = [];
      const gasFinalize = [];

      for (let round = 0; round < rounds; round++) {
        const slotKey = toSlotKey(
          `agg.${scenario.name}.${method.name.toLowerCase()}.${round}`
        );
        const taskId = Number(await aggregation.nextTaskId());
        const txReq = await aggregation
          .connect(owner)
          .requestTask(
            slotKey,
            "mock://source",
            "metrics.value",
            method.id,
            oracleSigners.length,
            trimBps
          );
        const rcReq = await txReq.wait();
        gasRequest.push(Number(rcReq.gasUsed));

        for (let i = 0; i < oracleSigners.length; i++) {
          const noise = (rng() * 2 - 1) * scenario.noiseRange;
          let observed = trueValue + noise;
          const isOutlier = rng() < scenario.outlierRate;
          if (isOutlier) {
            const direction = rng() > 0.5 ? 1 : -1;
            observed = trueValue + direction * scenario.outlierMagnitude;
          }
          const value = Math.max(0, Math.round(observed));
          const weight = [1, 2, 3, 2, 1][i] || 1;
          const txSub = await aggregation
            .connect(oracleSigners[i])
            .submit(taskId, value, weight);
          const rcSub = await txSub.wait();
          gasSubmit.push(Number(rcSub.gasUsed));
        }

        const txFin = await aggregation.connect(owner).finalize(taskId);
        const rcFin = await txFin.wait();
        gasFinalize.push(Number(rcFin.gasUsed));

        const task = await aggregation.tasks(taskId);
        const result = Number(task.result);
        results.push(result);
        errors.push(Math.abs(result - trueValue));
      }

      report.scenarios[scenario.name][method.name] = {
        mae: mean(errors),
        stddev: stddev(results),
        avgRequestGas: mean(gasRequest),
        avgSubmitGas: mean(gasSubmit),
        avgFinalizeGas: mean(gasFinalize),
        avgTotalGas: mean(
          gasRequest.map((_, i) =>
            gasRequest[i] +
            gasFinalize[i] +
            gasSubmit.slice(i * oracleSigners.length, (i + 1) * oracleSigners.length).reduce((a, b) => a + b, 0)
          )
        )
      };
    }
  }

  const robustness = {};
  for (const m of METHODS) {
    const cleanMae = report.scenarios.clean[m.name].mae;
    const outlierMae = report.scenarios.outlier[m.name].mae;
    robustness[m.name] = {
      maeIncrease: outlierMae - cleanMae,
      ratio: cleanMae === 0 ? null : outlierMae / cleanMae
    };
  }
  report.robustness = robustness;

  const outPath = path.resolve("deployments/aggregation-report.json");
  fs.writeFileSync(outPath, JSON.stringify(report, null, 2));

  console.log("aggregation experiment done:", outPath);
  const table = METHODS.map((m) => ({
    method: m.name,
    clean_mae: report.scenarios.clean[m.name].mae.toFixed(3),
    outlier_mae: report.scenarios.outlier[m.name].mae.toFixed(3),
    mae_increase: robustness[m.name].maeIncrease.toFixed(3),
    clean_stddev: report.scenarios.clean[m.name].stddev.toFixed(3),
    outlier_stddev: report.scenarios.outlier[m.name].stddev.toFixed(3),
    avg_total_gas: Math.round(report.scenarios.clean[m.name].avgTotalGas)
  }));
  console.table(table);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
