const fs = require("fs");
const path = require("path");
const hre = require("hardhat");
const { mean, writeJson } = require("./common");

function buildFirstRules(ruleCount) {
  const packedRules = [];
  for (let i = 0; i < ruleCount; i++) {
    packedRules.push(i * 5);
    packedRules.push(i * 5 + 4);
    packedRules.push(i * 7);
    packedRules.push(i * 7 + 6);
    packedRules.push(i + 1);
  }
  return { packedRules };
}

function buildCollectRules(ruleCount) {
  const packedRules = [];
  for (let i = 0; i < ruleCount; i++) {
    packedRules.push(0);
    packedRules.push(1000);
    packedRules.push(0);
    packedRules.push(1000);
    packedRules.push((i % 9) + 1);
  }
  return { packedRules };
}

function buildScorecard(featureCount) {
  const features = [];
  const thresholds = [];
  const highWeights = [];
  const lowWeights = [];
  for (let i = 0; i < featureCount; i++) {
    features.push(40 + ((i * 7) % 80));
    thresholds.push(65 + (i % 10));
    highWeights.push(3 + (i % 5));
    lowWeights.push(1 + (i % 2));
  }
  return { features, thresholds, highWeights, lowWeights };
}

function buildGraph(featureCount, nodeCount) {
  const features = [];
  const weights = [];
  const biases = [];

  for (let i = 0; i < featureCount; i++) {
    features.push(10 + ((i * 13) % 90));
  }
  for (let n = 0; n < nodeCount; n++) {
    biases.push((n % 17) + 3);
    for (let j = 0; j < featureCount; j++) {
      weights.push(((n + 1) * (j + 3)) % 11 + 1);
    }
  }
  return { features, weights, biases };
}

function complexityScale(c) {
  switch (c.model_type) {
    case "table_first":
    case "table_collect":
      return c.rule_count;
    case "scorecard":
      return c.feature_count;
    case "decision_graph":
      return c.feature_count * c.node_count * c.iterations;
    default:
      return 0;
  }
}

function modelLabel(t) {
  if (t === "table_first") return "DecisionTable-FIRST";
  if (t === "table_collect") return "DecisionTable-COLLECT";
  if (t === "scorecard") return "Scorecard";
  if (t === "decision_graph") return "DecisionGraph";
  return t;
}

function toMarkdown(report) {
  const esc = (s) => String(s).replace(/\|/g, "\\|");
  const lines = [];
  lines.push("# DMN 决策任务链上复杂度实验报告");
  lines.push("");
  lines.push(`生成时间：${report.generatedAt}`);
  lines.push("");
  lines.push(`案例数：${report.caseCount}`);
  lines.push("");
  lines.push("| 序号 | 案例 | 模型类型 | 复杂度规模 | 链上Gas | 说明 |");
  lines.push("| --- | --- | --- | ---: | ---: | --- |");
  for (const r of report.rows) {
    lines.push(
      `| ${r.seq} | ${esc(r.scenarioName)} | ${r.modelType} | ${r.complexityScale} | ${r.onchainGas} | ${esc(
        r.expression
      )} |`
    );
  }
  lines.push("");
  lines.push("## 分模型统计");
  lines.push("");
  lines.push("| 模型 | 平均Gas | 最小Gas | 最大Gas |");
  lines.push("| --- | ---: | ---: | ---: |");
  for (const m of report.summary.byModel) {
    lines.push(`| ${m.modelType} | ${m.avgGas.toFixed(1)} | ${m.minGas} | ${m.maxGas} |`);
  }
  lines.push("");
  lines.push("## 结论");
  lines.push("");
  lines.push(
    `1. 总体平均链上Gas为 ${report.summary.avgGas.toFixed(
      1
    )}，其中最高复杂度案例达到 ${report.summary.maxGas}。`
  );
  lines.push(
    "2. DecisionGraph 随 node/feature/iteration 增长呈明显高开销，适合作为链下计算候选。"
  );
  lines.push(
    "3. FIRST/COLLECT/Scorecard 类 DMN 规则在低维规模下可直接链上执行，在高规则数场景建议采用链下执行+链上确认。"
  );
  lines.push("");
  return lines.join("\n");
}

async function runCase(contract, c) {
  if (c.model_type === "table_first") {
    const rules = buildFirstRules(c.rule_count);
    const tx = await contract.evalDecisionTableFirst(c.input_x, c.input_y, rules.packedRules, {
      gasLimit: 16000000
    });
    return tx.wait();
  }

  if (c.model_type === "table_collect") {
    const rules = buildCollectRules(c.rule_count);
    const tx = await contract.evalDecisionTableCollect(c.input_x, c.input_y, rules.packedRules, {
      gasLimit: 16000000
    });
    return tx.wait();
  }

  if (c.model_type === "scorecard") {
    const sc = buildScorecard(c.feature_count);
    const tx = await contract.evalScorecard(
      sc.features,
      sc.thresholds,
      sc.highWeights,
      sc.lowWeights,
      c.base_score || 0,
      { gasLimit: 16000000 }
    );
    return tx.wait();
  }

  if (c.model_type === "decision_graph") {
    const g = buildGraph(c.feature_count, c.node_count);
    const tx = await contract.evalDecisionGraph(
      g.features,
      g.weights,
      g.biases,
      c.node_count,
      c.iterations,
      { gasLimit: 16000000 }
    );
    return tx.wait();
  }

  throw new Error(`unknown model_type: ${c.model_type}`);
}

async function main() {
  const root = path.join(__dirname, "..");
  const dataset = JSON.parse(
    fs.readFileSync(path.join(root, "dataset", "dmn_compute_cases.json"), "utf8")
  );

  const [owner] = await hre.ethers.getSigners();
  const Factory = await hre.ethers.getContractFactory("DMNDecisionBenchmark");
  const dmn = await Factory.connect(owner).deploy();
  await dmn.waitForDeployment();

  const rows = [];
  let seq = 1;
  for (const c of dataset.cases) {
    const rc = await runCase(dmn, c);
    rows.push({
      seq,
      caseId: c.case_id,
      scenarioName: c.scenario_name,
      datasetName: c.dataset_name,
      datasetRef: c.dataset_ref,
      modelType: modelLabel(c.model_type),
      modelRaw: c.model_type,
      complexityScale: complexityScale(c),
      onchainGas: Number(rc.gasUsed),
      expression: c.dmn_expression
    });
    seq += 1;
  }

  const models = [...new Set(rows.map((x) => x.modelType))];
  const byModel = models.map((m) => {
    const arr = rows.filter((x) => x.modelType === m).map((x) => x.onchainGas);
    return {
      modelType: m,
      avgGas: mean(arr),
      minGas: Math.min(...arr),
      maxGas: Math.max(...arr)
    };
  });

  const report = {
    generatedAt: new Date().toISOString(),
    caseCount: rows.length,
    rows,
    summary: {
      avgGas: mean(rows.map((x) => x.onchainGas)),
      minGas: Math.min(...rows.map((x) => x.onchainGas)),
      maxGas: Math.max(...rows.map((x) => x.onchainGas)),
      byModel
    }
  };

  const jsonPath = path.join(root, "report", "dmn-complexity-report.json");
  const mdPath = path.join(root, "report", "DMN_COMPLEXITY_REPORT.md");
  writeJson(jsonPath, report);
  fs.writeFileSync(mdPath, toMarkdown(report), "utf8");
  console.log(`json report -> ${jsonPath}`);
  console.log(`markdown report -> ${mdPath}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
