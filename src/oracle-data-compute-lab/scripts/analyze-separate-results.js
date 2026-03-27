import fs from "fs";
import path from "path";

function readJson(file) {
  const p = path.resolve(file);
  if (!fs.existsSync(p)) {
    throw new Error(`missing report file: ${p}`);
  }
  return JSON.parse(fs.readFileSync(p, "utf-8"));
}

function minBy(arr, key) {
  if (!arr.length) return null;
  return arr.reduce((best, cur) =>
    Number(cur[key]) < Number(best[key]) ? cur : best
  );
}

function summarizeData(aggregationReport) {
  const methods = aggregationReport.methods || [];
  const clean = aggregationReport.scenarios?.clean || {};
  const outlier = aggregationReport.scenarios?.outlier || {};

  const rows = methods.map((m) => ({
    method: m,
    cleanMae: Number(clean[m]?.mae ?? Number.POSITIVE_INFINITY),
    outlierMae: Number(outlier[m]?.mae ?? Number.POSITIVE_INFINITY),
    cleanStddev: Number(clean[m]?.stddev ?? Number.POSITIVE_INFINITY),
    outlierStddev: Number(outlier[m]?.stddev ?? Number.POSITIVE_INFINITY),
    cleanAvgTotalGas: Number(clean[m]?.avgTotalGas ?? Number.POSITIVE_INFINITY),
    robustnessMaeIncrease: Number(
      aggregationReport.robustness?.[m]?.maeIncrease ?? Number.POSITIVE_INFINITY
    )
  }));

  return {
    rounds: aggregationReport.rounds,
    trueValue: aggregationReport.trueValue,
    methods: rows,
    bestAccuracyClean: minBy(rows, "cleanMae")?.method || null,
    bestAccuracyOutlier: minBy(rows, "outlierMae")?.method || null,
    bestRobustness: minBy(rows, "robustnessMaeIncrease")?.method || null,
    bestGasCost: minBy(rows, "cleanAvgTotalGas")?.method || null
  };
}

function summarizeCompute(computeReport) {
  const offchainGas = Number(computeReport.offchain?.avgTotalGas ?? 0);
  const onchainDirect = Number(computeReport.onchain?.avgDirectGas ?? 0);
  const onchainHeavy = Number(computeReport.onchain?.avgHeavyGas ?? 0);
  return {
    rounds: computeReport.rounds,
    heavyLoops: computeReport.heavyLoops,
    expression: computeReport.expression,
    offchainAvgTotalGas: offchainGas,
    offchainAvgCpuMs: Number(computeReport.offchain?.avgCpuMs ?? 0),
    onchainAvgDirectGas: onchainDirect,
    onchainAvgHeavyGas: onchainHeavy,
    gasRatioOffchainVsDirect: onchainDirect > 0 ? offchainGas / onchainDirect : null,
    gasRatioOffchainVsHeavy: onchainHeavy > 0 ? offchainGas / onchainHeavy : null
  };
}

function main() {
  const aggregation = readJson("deployments/aggregation-report.json");
  const compute = readJson("deployments/compute-cost-report.json");

  const output = {
    generatedAt: new Date().toISOString(),
    dataTask: summarizeData(aggregation),
    computeTask: summarizeCompute(compute)
  };

  const outPath = path.resolve("deployments/separate-analysis-report.json");
  fs.writeFileSync(outPath, JSON.stringify(output, null, 2));

  console.log("separate analysis report:", outPath);
  console.table([
    {
      section: "data",
      best_clean_accuracy: output.dataTask.bestAccuracyClean,
      best_outlier_accuracy: output.dataTask.bestAccuracyOutlier,
      best_robustness: output.dataTask.bestRobustness,
      best_gas: output.dataTask.bestGasCost
    },
    {
      section: "compute",
      offchain_avg_gas: Math.round(output.computeTask.offchainAvgTotalGas),
      onchain_direct_avg_gas: Math.round(output.computeTask.onchainAvgDirectGas),
      onchain_heavy_avg_gas: Math.round(output.computeTask.onchainAvgHeavyGas),
      offchain_cpu_ms: output.computeTask.offchainAvgCpuMs.toFixed(6)
    }
  ]);
}

main();
