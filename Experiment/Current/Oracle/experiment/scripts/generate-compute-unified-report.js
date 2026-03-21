const fs = require("fs");
const path = require("path");

function readJson(p) {
  return JSON.parse(fs.readFileSync(p, "utf8"));
}

function fmtN(v) {
  return Number(v).toLocaleString("en-US");
}

function fmtP(v) {
  return `${Number(v).toFixed(2)}%`;
}

function avg(arr) {
  if (!arr.length) return 0;
  return arr.reduce((a, b) => a + b, 0) / arr.length;
}

function buildDatasetRows(computeReport, dmnReport) {
  const m = new Map();
  for (const r of computeReport.rows) {
    const key = `${r.datasetName}`.trim().toLowerCase();
    if (!m.has(key)) {
      m.set(key, {
        datasetName: r.datasetName,
        datasetRef: r.datasetRef || "",
        computeTaskCount: 0,
        computeScenarioSet: new Set(),
        dmnCaseCount: 0,
        dmnScenarioSet: new Set()
      });
    }
    const obj = m.get(key);
    obj.computeTaskCount += 1;
    obj.computeScenarioSet.add(r.scenarioName);
    if (!obj.datasetRef && r.datasetRef) {
      obj.datasetRef = r.datasetRef;
    }
  }
  for (const r of dmnReport.rows) {
    const key = `${r.datasetName}`.trim().toLowerCase();
    if (!m.has(key)) {
      m.set(key, {
        datasetName: r.datasetName,
        datasetRef: r.datasetRef || "",
        computeTaskCount: 0,
        computeScenarioSet: new Set(),
        dmnCaseCount: 0,
        dmnScenarioSet: new Set()
      });
    }
    const obj = m.get(key);
    obj.dmnCaseCount += 1;
    obj.dmnScenarioSet.add(r.scenarioName);
    if (!obj.datasetRef && r.datasetRef) {
      obj.datasetRef = r.datasetRef;
    }
  }

  return [...m.values()].map((x) => ({
    datasetName: x.datasetName,
    datasetRef: x.datasetRef,
    computeScenarioCount: x.computeScenarioSet.size,
    computeTaskCount: x.computeTaskCount,
    dmnScenarioCount: x.dmnScenarioSet.size,
    dmnCaseCount: x.dmnCaseCount
  }));
}

function toMarkdown(computeReport, dmnReport) {
  const esc = (s) => String(s).replace(/\|/g, "\\|");
  const computeRows = computeReport.rows;
  const offchainWins = computeRows.filter((r) => r.offchainGas < r.directGas);
  const directWins = computeRows.filter((r) => r.directGas <= r.offchainGas);

  const offchainWinRate = (offchainWins.length / computeRows.length) * 100;
  const directWinRate = (directWins.length / computeRows.length) * 100;

  const topOffchain = [...offchainWins]
    .sort((a, b) => (b.directGas - b.offchainGas) - (a.directGas - a.offchainGas))
    .slice(0, 5);
  const worstOffchain = [...directWins]
    .sort((a, b) => (b.offchainGas - b.directGas) - (a.offchainGas - a.directGas))
    .slice(0, 5);

  const byModel = dmnReport.summary.byModel || [];
  const dg = dmnReport.rows.filter((r) => r.modelRaw === "decision_graph");
  const nonDg = dmnReport.rows.filter((r) => r.modelRaw !== "decision_graph");
  const dgMin = Math.min(...dg.map((x) => x.onchainGas));
  const nonDgMax = Math.max(...nonDg.map((x) => x.onchainGas));

  const datasetRows = buildDatasetRows(computeReport, dmnReport);

  const lines = [];
  lines.push("# 计算任务统一实验报告（Compute + DMN）");
  lines.push("");
  lines.push(`生成时间：${new Date().toISOString()}`);
  lines.push("");
  lines.push("## 1. 实验设计");
  lines.push("");
  lines.push("### 1.1 目标");
  lines.push("- 评估不同计算任务在链上执行的成本差异。");
  lines.push("- 评估“链下计算 + 链上确认”相对“直接链上计算”的成本收益。");
  lines.push("- 针对 DMN 决策逻辑，量化模型复杂度与链上 gas 的关系。");
  lines.push("");
  lines.push("### 1.2 实验组成");
  lines.push("1. `Compute-10`：10 个工业场景、20 个任务（数值/逻辑/混合）直接链上 vs 链下确认。");
  lines.push("2. `DMN-Complexity`：10 个 DMN 案例（DecisionTable/Scorecard/DecisionGraph）链上复杂度基准。");
  lines.push("");
  lines.push("### 1.3 成本口径");
  lines.push("- `directGas`：任务在业务合约中直接执行交易的 `gasUsed`。");
  lines.push("- `offchainGas`：`registerComputeTask + submitComputeResultBatch` 的链上总 `gasUsed`。");
  lines.push("- `optimizationRatio`：`(directGas - offchainGas) / directGas`。");
  lines.push("");
  lines.push("## 2. 数据集介绍");
  lines.push("");
  lines.push("| 数据集 | Compute 场景数 | Compute 任务数 | DMN 场景数 | DMN 案例数 | 链接 |");
  lines.push("| --- | ---: | ---: | ---: | ---: | --- |");
  for (const r of datasetRows) {
    const ref = r.datasetRef ? r.datasetRef : "-";
    lines.push(
      `| ${esc(r.datasetName)} | ${r.computeScenarioCount} | ${r.computeTaskCount} | ${r.dmnScenarioCount} | ${r.dmnCaseCount} | ${esc(ref)} |`
    );
  }
  lines.push("");
  lines.push("## 3. 实验结果展示");
  lines.push("");
  lines.push("### 3.1 Compute-10 总体结果");
  lines.push("");
  lines.push("| 指标 | 数值 |");
  lines.push("| --- | ---: |");
  lines.push(`| 场景数 | ${computeReport.scenarioCount} |`);
  lines.push(`| 任务数 | ${computeReport.taskCount} |`);
  lines.push(`| 平均 direct gas | ${fmtN(computeReport.summary.avgDirectGas)} |`);
  lines.push(`| 平均 offchain gas | ${fmtN(computeReport.summary.avgOffchainGas)} |`);
  lines.push(`| 全量链下相对优化 | ${fmtP(computeReport.summary.overallOptimizationRatio)} |`);
  lines.push(
    `| 自适应调度相对全 direct 优化 | ${fmtP(computeReport.summary.adaptive.vsAllDirectRatio)} |`
  );
  lines.push(
    `| 路由分布（direct/offchain） | ${computeReport.summary.adaptive.directCount}/${computeReport.summary.adaptive.offchainCount} |`
  );
  lines.push("");
  lines.push("| 路径胜率 | 占比 |");
  lines.push("| --- | ---: |");
  lines.push(`| offchain 更优 | ${fmtP(offchainWinRate)} |`);
  lines.push(`| direct 更优 | ${fmtP(directWinRate)} |`);
  lines.push("");
  lines.push("### 3.2 Compute-10 代表性任务");
  lines.push("");
  lines.push("#### Offchain 最优 Top5");
  lines.push("");
  lines.push("| 任务 | directGas | offchainGas | 节省Gas | 优化比例 |");
  lines.push("| --- | ---: | ---: | ---: | ---: |");
  for (const r of topOffchain) {
    lines.push(
      `| ${esc(r.taskName)} | ${fmtN(r.directGas)} | ${fmtN(r.offchainGas)} | ${fmtN(
        r.directGas - r.offchainGas
      )} | ${fmtP(r.optimizationRatio)} |`
    );
  }
  lines.push("");
  lines.push("#### Offchain 不适用 Top5（direct 更优）");
  lines.push("");
  lines.push("| 任务 | directGas | offchainGas | 额外Gas | 优化比例 |");
  lines.push("| --- | ---: | ---: | ---: | ---: |");
  for (const r of worstOffchain) {
    lines.push(
      `| ${esc(r.taskName)} | ${fmtN(r.directGas)} | ${fmtN(r.offchainGas)} | ${fmtN(
        r.offchainGas - r.directGas
      )} | ${fmtP(r.optimizationRatio)} |`
    );
  }
  lines.push("");
  lines.push("### 3.3 DMN 复杂度结果");
  lines.push("");
  lines.push("| 指标 | 数值 |");
  lines.push("| --- | ---: |");
  lines.push(`| 案例数 | ${dmnReport.caseCount} |`);
  lines.push(`| 平均链上 gas | ${fmtN(dmnReport.summary.avgGas)} |`);
  lines.push(`| 最小链上 gas | ${fmtN(dmnReport.summary.minGas)} |`);
  lines.push(`| 最大链上 gas | ${fmtN(dmnReport.summary.maxGas)} |`);
  lines.push(`| 非 DecisionGraph 最大 gas | ${fmtN(nonDgMax)} |`);
  lines.push(`| DecisionGraph 最小 gas | ${fmtN(dgMin)} |`);
  lines.push("");
  lines.push("| DMN 模型 | 平均Gas | 最小Gas | 最大Gas |");
  lines.push("| --- | ---: | ---: | ---: |");
  for (const m of byModel) {
    lines.push(
      `| ${m.modelType} | ${fmtN(m.avgGas)} | ${fmtN(m.minGas)} | ${fmtN(m.maxGas)} |`
    );
  }
  lines.push("");
  lines.push("## 4. 实验结果分析");
  lines.push("");
  lines.push("1. 任务分层现象明显：");
  lines.push(
    `- 轻量任务（结算/门控/风险）direct gas 常在 ${fmtN(
      Math.round(avg(directWins.map((x) => x.directGas)))
    )} 左右；`
  );
  lines.push(
    `- 重负载优化任务 direct gas 常在 ${fmtN(
      Math.round(avg(offchainWins.map((x) => x.directGas)))
    )} 量级。`
  );
  lines.push("");
  lines.push("2. 链下计算价值主要来自复杂任务：");
  lines.push(`- offchain 仅在 ${offchainWins.length}/${computeRows.length} 任务中获胜，但这些任务贡献了绝大多数节省。`);
  lines.push("- 采用自适应路由后，总体优化高于统一策略。");
  lines.push("");
  lines.push("3. DMN 复杂逻辑链上开销随结构复杂度快速增长：");
  lines.push("- DecisionTable / Scorecard 在低维规则下可链上直算；");
  lines.push("- DecisionGraph 进入高复杂区后，链上成本显著跃升。");
  lines.push("");
  lines.push("4. 统一结论（针对计算任务）：");
  lines.push("- 建议采用“复杂度感知路由”：轻量规则留链上，复杂决策图下链执行并链上确认。");
  lines.push("- 当前实验的经验阈值：当预估链上 gas 超过约 40~50 万时，链下路径通常更有优势。");
  lines.push("");
  return lines.join("\n");
}

function main() {
  const root = path.join(__dirname, "..");
  const computePath = path.join(root, "report", "compute-10-scenarios-report.json");
  const dmnPath = path.join(root, "report", "dmn-complexity-report.json");

  const computeReport = readJson(computePath);
  const dmnReport = readJson(dmnPath);

  const md = toMarkdown(computeReport, dmnReport);
  const outPath = path.join(root, "report", "COMPUTE_UNIFIED_EXPERIMENT_REPORT.md");
  fs.writeFileSync(outPath, md, "utf8");
  console.log(`markdown report -> ${outPath}`);
}

main();
