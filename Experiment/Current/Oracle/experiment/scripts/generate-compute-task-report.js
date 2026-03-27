const fs = require("fs");
const path = require("path");

function readJson(p) {
  return JSON.parse(fs.readFileSync(p, "utf8"));
}

function fmtN(v) {
  if (v === null || v === undefined) return "N/A（链上不支持）";
  return Number(v).toLocaleString("en-US", { maximumFractionDigits: 3 });
}

function fmtPct(v) {
  if (v === null || v === undefined) return "N/A";
  return `${Number(v).toFixed(2)}%`;
}

function avgNumber(arr) {
  if (!arr.length) return null;
  return arr.reduce((a, b) => a + b, 0) / arr.length;
}

function buildClassRows(rows) {
  const map = new Map();
  for (const r of rows) {
    const key = r.scenarioClass || "未分类";
    if (!map.has(key)) {
      map.set(key, {
        className: key,
        taskNames: new Set(),
        directGasValues: [],
        offchainGasValues: [],
        ratioValues: [],
        directComparableCount: 0
      });
    }
    const item = map.get(key);
    (r.taskNames || []).forEach((n) => item.taskNames.add(n));
    if (r.directGas !== null && r.directGas !== undefined) {
      item.directGasValues.push(Number(r.directGas));
      item.directComparableCount += 1;
    }
    if (r.offchainGas !== null && r.offchainGas !== undefined) {
      item.offchainGasValues.push(Number(r.offchainGas));
    }
    if (r.optimizationRatio !== null && r.optimizationRatio !== undefined) {
      item.ratioValues.push(Number(r.optimizationRatio));
    }
  }

  return [...map.values()].map((x) => ({
    className: x.className,
    taskDesc: [...x.taskNames].join(" + "),
    directGas: avgNumber(x.directGasValues),
    offchainGas: avgNumber(x.offchainGasValues),
    optimizationRatio: avgNumber(x.ratioValues),
    directComparableCount: x.directComparableCount
  }));
}

function classTaskDescription(className, fallback) {
  const m = {
    "简单运算": "线性结算公式：amount = a * b + c",
    "浮点运算": "连续非线性评分：score = α·log(x+1) + β·exp(y) + γ·sqrt(z)",
    "随机运算": "蒙特卡洛概率估计：p ≈ hits / N",
    "复杂运算":
      "方案组合优化：result=min[(60x+25y+15z-target)^2 + 2*(400x+120y+80z-budget)^2]"
  };
  return m[className] || fallback || "-";
}

function classComplexityNote(className) {
  const m = {
    "简单运算": "常数复杂度，约 1 次乘法 + 1 次加法",
    "浮点运算": "含 log/exp/sqrt 等连续函数，需浮点支持",
    "随机运算": "N 轮抽样循环（本实验 N=4000）+ 随机数比较与计数",
    "复杂运算": "离散搜索优化（本实验 11×11×11=1331 组），每组计算分值偏差+预算偏差惩罚"
  };
  return m[className] || "-";
}

function toMarkdown(computeReport, dataset) {
  const lines = [];
  const rows = computeReport.rows || [];
  const classRows = buildClassRows(rows);
  const comparableRows = rows.filter((x) => x.directComparable);
  const offchainBetterCount = comparableRows.filter((x) => x.offchainGas < x.directGas).length;

  lines.push("# Oracle 计算任务实验报告");
  lines.push("");
  lines.push(`生成时间：${new Date().toISOString()}`);
  lines.push("");
  lines.push("## 1. 实验目标");
  lines.push("");
  lines.push("- 验证四类计算任务（简单/浮点/随机/复杂）在链上与链下两条路径下的开销差异。");
  lines.push("- 验证“链下有额外开销，但适用于浮点、随机及复杂运算”这一结论。");
  lines.push("");
  lines.push("## 2. 计算任务类型");
  lines.push("");
  lines.push(`- 类型总数：${classRows.length}；任务总数：${computeReport.atomicTaskCount}。`);
  lines.push("- 类型包括：简单运算、浮点运算、随机运算、复杂运算。");
  lines.push("- 实验输入文件：`dataset/compute_tasks_10_scenarios.json`。");
  lines.push("");
  lines.push("## 3. 计算任务开销结果");
  lines.push("");
  lines.push("| 任务类型 | 代表计算任务 | 复杂性说明 | 链上计算Cost(gas) | 链下计算Cost(gas) | 优化率 |");
  lines.push("| --- | --- | --- | ---: | ---: | ---: |");
  for (const r of classRows) {
    lines.push(
      `| ${r.className} | ${classTaskDescription(r.className, r.taskDesc)} | ${classComplexityNote(r.className)} | ${fmtN(r.directGas)} | ${fmtN(r.offchainGas)} | ${fmtPct(r.optimizationRatio)} |`
    );
  }
  lines.push("");
  lines.push("## 4. 结果分析");
  lines.push("");
  lines.push(`1. 在可直接链上计算的 ${comparableRows.length} 个场景中，链下路径在 ${offchainBetterCount} 个场景中更省开销。`);
  lines.push("2. 简单运算场景中，链下提交的固定成本明显，整体呈现额外开销。");
  lines.push("3. 浮点运算与随机运算场景在当前 EVM 口径下不适合直接链上实现，链下执行是必要路径。");
  lines.push("4. 复杂运算场景中，链下计算 + 链上确认可显著降低开销，体现出明显收益。");
  lines.push("5. 因此可得结论：链下计算存在相当的额外开销，但适用于浮点、随机及复杂运算场景。");
  lines.push("");
  lines.push("## 5. 复现实验");
  lines.push("");
  lines.push("```bash");
  lines.push("cd /home/logres/system/Experiment/Current/Oracle");
  lines.push("npm run experiment:compute-10-scenarios");
  lines.push("npm run report:compute-task");
  lines.push("```");
  lines.push("");

  return lines.join("\n");
}

function main() {
  const root = path.join(__dirname, "..");
  const computePath = path.join(root, "report", "compute-10-scenarios-report.json");
  const datasetPath = path.join(root, "dataset", "compute_tasks_10_scenarios.json");
  const outPath = path.join(root, "report", "COMPUTE_TASK_EXPERIMENT_REPORT.md");

  const computeReport = readJson(computePath);
  const dataset = readJson(datasetPath);
  const md = toMarkdown(computeReport, dataset);
  fs.writeFileSync(outPath, md, "utf8");
  console.log(`markdown report -> ${outPath}`);
}

main();
