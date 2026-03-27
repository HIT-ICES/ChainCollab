const fs = require("fs");
const path = require("path");
const hre = require("hardhat");
const { mean, writeJson } = require("./common");

const COMPUTE_DOMAIN = hre.ethers.id("COMPUTE");

function encodeComputeType(str) {
  const b = Buffer.from(str, "utf8");
  if (b.length > 32) return hre.ethers.keccak256(hre.ethers.toUtf8Bytes(str));
  return hre.ethers.zeroPadValue(hre.ethers.hexlify(b), 32);
}

function encodeResultHash(resultBigInt) {
  const coder = hre.ethers.AbiCoder.defaultAbiCoder();
  const encoded = coder.encode(["uint256"], [resultBigInt]);
  return hre.ethers.keccak256(encoded);
}

async function signCompute(oracleSigner, contractAddress, taskId, resultHash) {
  const digest = hre.ethers.solidityPackedKeccak256(
    ["address", "bytes32", "uint256", "bytes32"],
    [contractAddress, COMPUTE_DOMAIN, taskId, resultHash]
  );
  return oracleSigner.signMessage(hre.ethers.getBytes(digest));
}

function toBi(v) {
  return BigInt(v);
}

function computeJs(task) {
  const i = task.inputs;
  switch (task.task_type) {
    case "numeric_settlement":
      return toBi(i.energy_kwh) * toBi(i.tariff_wei_per_kwh) + toBi(i.penalty_wei);
    case "availability_bps":
      return (toBi(i.run_minutes) * 10000n) / toBi(i.planned_minutes);
    case "performance_bps":
      return (toBi(i.ideal_cycle_ms) * toBi(i.total_count) * 10000n) / toBi(i.run_time_ms);
    case "quality_bps":
      return (toBi(i.good_count) * 10000n) / toBi(i.total_count);
    case "oee_bps":
      return ((toBi(i.availability_bps) * toBi(i.performance_bps)) / 10000n * toBi(i.quality_bps)) / 10000n;
    case "mtbf_minutes":
      return toBi(i.failure_count) === 0n ? toBi(i.total_run_minutes) : toBi(i.total_run_minutes) / toBi(i.failure_count);
    case "mttr_minutes":
      return toBi(i.repair_count) === 0n ? 0n : toBi(i.total_repair_minutes) / toBi(i.repair_count);
    case "availability_mtbf_mttr_bps": {
      const denom = toBi(i.mtbf_minutes) + toBi(i.mttr_minutes);
      return denom === 0n ? 0n : (toBi(i.mtbf_minutes) * 10000n) / denom;
    }
    case "kw_per_ton_milli":
      return 12000000n / toBi(i.eer_milli);
    case "fpy_bps":
      return (toBi(i.first_pass_good) * 10000n) / toBi(i.first_pass_input);
    case "rty3_bps":
      return ((toBi(i.fpy1_bps) * toBi(i.fpy2_bps)) / 10000n * toBi(i.fpy3_bps)) / 10000n;
    case "complex_optimization": {
      const targetScore = toBi(i.target_score);
      const budget = toBi(i.budget);
      const step = toBi(i.step);
      const xMin = toBi(i.x_min);
      const xMax = toBi(i.x_max);
      const yMin = toBi(i.y_min);
      const yMax = toBi(i.y_max);
      const zMin = toBi(i.z_min);
      const zMax = toBi(i.z_max);
      let best = null;

      for (let x = xMin; x <= xMax; x += step) {
        for (let y = yMin; y <= yMax; y += step) {
          for (let z = zMin; z <= zMax; z += step) {
            const score = 60n * x + 25n * y + 15n * z;
            const cost = 400n * x + 120n * y + 80n * z;
            const scoreGap = score >= targetScore ? score - targetScore : targetScore - score;
            const costGap = cost >= budget ? cost - budget : budget - cost;
            const objective = scoreGap * scoreGap + 2n * costGap * costGap;
            if (best === null || objective < best) best = objective;
          }
        }
      }

      return best === null ? 0n : best;
    }
    case "nonlinear_health_index_float": {
      const score =
        0.42 * Math.log(Number(i.vibration) + 1) +
        0.35 * Math.exp(Number(i.temperature) / 100) +
        0.23 * Math.sqrt(Number(i.load));
      return toBi(Math.round(score * 1_000_000));
    }
    case "nonlinear_process_risk_float": {
      const z =
        0.015 * Number(i.pressure) +
        0.02 * Number(i.flow) -
        0.01 * Number(i.ph) +
        0.5 * Math.sin(Number(i.vibration) / 10);
      const risk = 1 / (1 + Math.exp(-z));
      return toBi(Math.round(risk * 1_000_000));
    }
    case "random_sampling_confidence": {
      const MOD = 2147483647n;
      const MUL = 48271n;
      let state = toBi(i.seed) % MOD;
      let hit = 0n;
      const draws = Number(i.draws);
      const p = Number(i.alert_prob);
      for (let idx = 0; idx < draws; idx++) {
        state = (state * MUL) % MOD;
        const u = Number(state % 10000n) / 10000;
        if (u < p) hit += 1n;
      }
      return toBi(Math.round((Number(hit) * 1_000_000) / draws));
    }
    default:
      throw new Error(`unknown task_type: ${task.task_type}`);
  }
}

async function computeDirect(contract, task) {
  const i = task.inputs;
  switch (task.task_type) {
    case "numeric_settlement":
      return contract.calcSettlement.staticCall(i.energy_kwh, i.tariff_wei_per_kwh, 0, 0, i.penalty_wei);
    case "availability_bps":
      return contract.calcAvailabilityBps.staticCall(i.run_minutes, i.planned_minutes);
    case "performance_bps":
      return contract.calcPerformanceBps.staticCall(i.ideal_cycle_ms, i.total_count, i.run_time_ms);
    case "quality_bps":
      return contract.calcQualityBps.staticCall(i.good_count, i.total_count);
    case "oee_bps":
      return contract.calcOEEBps.staticCall(i.availability_bps, i.performance_bps, i.quality_bps);
    case "mtbf_minutes":
      return contract.calcMTBFMinutes.staticCall(i.total_run_minutes, i.failure_count);
    case "mttr_minutes":
      return contract.calcMTTRMinutes.staticCall(i.total_repair_minutes, i.repair_count);
    case "availability_mtbf_mttr_bps":
      return contract.calcAvailabilityFromMTBFMTTRBps.staticCall(i.mtbf_minutes, i.mttr_minutes);
    case "kw_per_ton_milli":
      return contract.calcKwPerTonMilli.staticCall(i.eer_milli);
    case "fpy_bps":
      return contract.calcFPYBps.staticCall(i.first_pass_good, i.first_pass_input);
    case "rty3_bps":
      return contract.calcRTY3Bps.staticCall(i.fpy1_bps, i.fpy2_bps, i.fpy3_bps);
    case "complex_optimization":
      return contract.computeComplexOptimization.staticCall(
        i.target_score,
        i.budget,
        i.step,
        i.x_min,
        i.x_max,
        i.y_min,
        i.y_max,
        i.z_min,
        i.z_max,
        {
          gasLimit: 16000000
        }
      );
    default:
      throw new Error(`unknown task_type: ${task.task_type}`);
  }
}

async function sendDirect(contract, task) {
  const i = task.inputs;
  switch (task.task_type) {
    case "numeric_settlement":
      return contract.calcSettlement(i.energy_kwh, i.tariff_wei_per_kwh, 0, 0, i.penalty_wei);
    case "availability_bps":
      return contract.calcAvailabilityBps(i.run_minutes, i.planned_minutes);
    case "performance_bps":
      return contract.calcPerformanceBps(i.ideal_cycle_ms, i.total_count, i.run_time_ms);
    case "quality_bps":
      return contract.calcQualityBps(i.good_count, i.total_count);
    case "oee_bps":
      return contract.calcOEEBps(i.availability_bps, i.performance_bps, i.quality_bps);
    case "mtbf_minutes":
      return contract.calcMTBFMinutes(i.total_run_minutes, i.failure_count);
    case "mttr_minutes":
      return contract.calcMTTRMinutes(i.total_repair_minutes, i.repair_count);
    case "availability_mtbf_mttr_bps":
      return contract.calcAvailabilityFromMTBFMTTRBps(i.mtbf_minutes, i.mttr_minutes);
    case "kw_per_ton_milli":
      return contract.calcKwPerTonMilli(i.eer_milli);
    case "fpy_bps":
      return contract.calcFPYBps(i.first_pass_good, i.first_pass_input);
    case "rty3_bps":
      return contract.calcRTY3Bps(i.fpy1_bps, i.fpy2_bps, i.fpy3_bps);
    case "complex_optimization":
      return contract.computeComplexOptimization(
        i.target_score,
        i.budget,
        i.step,
        i.x_min,
        i.x_max,
        i.y_min,
        i.y_max,
        i.z_min,
        i.z_max,
        {
          gasLimit: 16000000
        }
      );
    default:
      throw new Error(`unknown task_type: ${task.task_type}`);
  }
}

function combineScenarioResults(values) {
  const MOD = (1n << 251n) - 9n;
  let acc = 0n;
  for (let i = 0; i < values.length; i++) {
    acc = (acc + values[i] * BigInt(i + 1)) % MOD;
  }
  return acc;
}

function toMarkdown(report) {
  const fmtGas = (v) => (v === null || v === undefined ? "N/A（链上不支持）" : `${v}`);
  const fmtRatio = (v) => (v === null || v === undefined ? "N/A" : `${v.toFixed(2)}%`);
  const lines = [];
  lines.push("# 工业计算场景开销对比实验报告");
  lines.push("");
  lines.push(`生成时间：${report.generatedAt}`);
  lines.push("");
  lines.push(`场景数：${report.scenarioCount}，原子任务总数：${report.atomicTaskCount}`);
  lines.push("");
  lines.push("| 场景 | 任务链（原子任务） | 直接计算Cost(gas) | 链下计算Cost(gas) | 优化率 |");
  lines.push("| --- | --- | ---: | ---: | ---: |");
  for (const row of report.rows) {
    lines.push(
      `| ${row.scenarioName} | ${row.taskNames.join(" + ")} | ${fmtGas(row.directGas)} | ${row.offchainGas} | ${fmtRatio(row.optimizationRatio)} |`
    );
  }
  lines.push("");
  lines.push("## 汇总");
  lines.push("");
  lines.push(`- 平均 direct gas（仅可链上计算场景）：${report.summary.avgDirectGas.toFixed(1)}`);
  lines.push(`- 平均 offchain gas：${report.summary.avgOffchainGas.toFixed(1)}`);
  lines.push(`- 链下更优场景数：${report.summary.offchainBetterCount}/${report.summary.comparableScenarioCount}`);
  lines.push(`- 平均优化率（仅可链上计算场景）：${report.summary.avgOptimizationRatio.toFixed(2)}%`);
  lines.push(`- 链上不可计算场景数：${report.summary.onchainUnsupportedCount}`);
  lines.push("");
  return lines.join("\n");
}

async function main() {
  const root = path.join(__dirname, "..");
  const dataset = JSON.parse(
    fs.readFileSync(path.join(root, "dataset", "compute_tasks_10_scenarios.json"), "utf8")
  );

  const [owner, ...signers] = await hre.ethers.getSigners();
  const oracleSigner = signers[0];
  const oracleAddress = await oracleSigner.getAddress();

  const OracleFactory = await hre.ethers.getContractFactory("UnifiedOracleLab");
  const oracle = await OracleFactory.connect(owner).deploy();
  await oracle.waitForDeployment();
  await (await oracle.connect(owner).registerOracle(oracleAddress)).wait();

  const DirectFactory = await hre.ethers.getContractFactory("IndustrialComputeDirect");
  const direct = await DirectFactory.connect(owner).deploy();
  await direct.waitForDeployment();

  const rows = [];
  let seq = 1;
  let atomicTaskCount = 0;
  for (const scenario of dataset.scenarios) {
    let directGas = 0;
    let directComparable = true;
    const unsupportedTasks = [];
    const outputs = [];
    const taskNames = [];
    const jsExpressions = [];
    for (const task of scenario.tasks) {
      const jsRes = computeJs(task);
      if (task.onchain_supported === false) {
        directComparable = false;
        unsupportedTasks.push(task.task_id);
        outputs.push(jsRes);
        taskNames.push(task.task_name);
        jsExpressions.push(task.js_expression || task.expression || task.task_type);
        atomicTaskCount += 1;
        continue;
      }

      const directRes = await computeDirect(direct, task);
      if (BigInt(directRes.toString()) !== jsRes) {
        throw new Error(`direct result mismatch: ${scenario.scenario_id}/${task.task_id}`);
      }
      const tx = await sendDirect(direct, task);
      const rc = await tx.wait();
      directGas += Number(rc.gasUsed);
      outputs.push(jsRes);
      taskNames.push(task.task_name);
      jsExpressions.push(task.js_expression || task.expression || task.task_type);
      atomicTaskCount += 1;
    }

    const scenarioResult = combineScenarioResults(outputs);
    const payloadJson = JSON.stringify({
      scenario_id: scenario.scenario_id,
      tasks: scenario.tasks.map((t) => ({ task_id: t.task_id, inputs: t.inputs }))
    });
    const payloadHash = hre.ethers.keccak256(hre.ethers.toUtf8Bytes(payloadJson));
    const resultHash = encodeResultHash(scenarioResult);
    const offTx = await oracle
      .connect(oracleSigner)
      .submitComputeResultLite(
        encodeComputeType("industrial_atomic_bundle"),
        payloadHash,
        resultHash
      );
    const offRc = await offTx.wait();
    const offchainGas = Number(offRc.gasUsed);

    const ratio = directComparable && directGas > 0 ? ((directGas - offchainGas) / directGas) * 100 : null;
    rows.push({
      seq,
      scenarioId: scenario.scenario_id,
      scenarioClass: scenario.scenario_class || "",
      scenarioName: scenario.scenario_name,
      datasetName: scenario.dataset_name,
      datasetRef: scenario.dataset_ref,
      taskCount: scenario.tasks.length,
      taskNames,
      jsExpressions,
      directGas: directComparable ? directGas : null,
      offchainGas,
      optimizationRatio: ratio,
      directComparable,
      unsupportedTasks,
      recommendedRoute: !directComparable ? "offchain_required" : (offchainGas < directGas ? "offchain" : "direct")
    });
    seq += 1;
  }

  const report = {
    generatedAt: new Date().toISOString(),
    threshold: 1,
    mode: "lite_single_submit",
    scenarioCount: dataset.scenarios.length,
    atomicTaskCount,
    scenarios: dataset.scenarios.map((s) => ({
      scenarioId: s.scenario_id,
      scenarioClass: s.scenario_class || "",
      scenarioName: s.scenario_name,
      datasetName: s.dataset_name,
      datasetRef: s.dataset_ref
    })),
    rows,
    summary: {
      avgDirectGas: mean(rows.filter((x) => x.directGas !== null).map((x) => x.directGas)),
      avgOffchainGas: mean(rows.map((x) => x.offchainGas)),
      avgOptimizationRatio: mean(rows.filter((x) => x.optimizationRatio !== null).map((x) => x.optimizationRatio)),
      offchainBetterCount: rows.filter((x) => x.directComparable && x.offchainGas < x.directGas).length,
      onchainUnsupportedCount: rows.filter((x) => !x.directComparable).length,
      comparableScenarioCount: rows.filter((x) => x.directComparable).length
    }
  };

  const jsonPath = path.join(root, "report", "compute-10-scenarios-report.json");
  const mdPath = path.join(root, "report", "COMPUTE_10_SCENARIOS_REPORT.md");
  writeJson(jsonPath, report);
  fs.writeFileSync(mdPath, toMarkdown(report), "utf8");
  console.log(`json report -> ${jsonPath}`);
  console.log(`markdown report -> ${mdPath}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
