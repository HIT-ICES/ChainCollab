const fs = require("fs");
const path = require("path");

function readJson(p) {
  return JSON.parse(fs.readFileSync(p, "utf8"));
}

function fmtN(v) {
  return Number(v).toLocaleString("en-US", { maximumFractionDigits: 3 });
}

function fmtP(v) {
  return `${(Number(v) * 100).toFixed(2)}%`;
}

function toMarkdown(report) {
  const esc = (s) => String(s).replace(/\|/g, "\\|");
  const normalizeProfileName = (name) => {
    const raw = String(name || "");
    if (raw.includes("轻微噪声")) return "轻微扰动场景";
    if (raw.includes("单节点异常值")) return "单点异常场景";
    if (raw.includes("存在缺失值")) return "缺失数据场景";
    return raw;
  };
  const lines = [];

  const modeNames = Object.keys(report.summary.overallByMode || {});
  const profileNames = report.profileNames || [];
  const scenarios = report.scenarios || [];
  const datasetMap = new Map();
  for (const s of scenarios) {
    const key = `${s.datasetName}||${s.metricCol}`;
    if (!datasetMap.has(key)) {
      datasetMap.set(key, {
        datasetName: s.datasetName,
        metricCol: s.metricCol,
        datasetRef: s.datasetRef
      });
    }
  }
  const datasets = Array.from(datasetMap.values());
  const modeRows = [];
  const overall = {};
  for (const mode of modeNames) {
    overall[mode] = { mapeSum: 0, gasSum: 0, count: 0 };
  }

  const getBestBy = (arr, field, tieField) => {
    const sorted = [...arr].sort((a, b) => {
      const d = a[field] - b[field];
      if (d !== 0) return d;
      return a[tieField] - b[tieField];
    });
    return sorted[0]?.mode || "-";
  };

  const profileAgg = {};
  for (const profile of profileNames) {
    profileAgg[profile] = {};
    for (const mode of modeNames) {
      let mapeSum = 0;
      let gasSum = 0;
      let count = 0;
      for (const s of scenarios) {
        const m = s.profiles?.[profile]?.[mode];
        if (!m) continue;
        mapeSum += Number(m.mape || 0);
        gasSum += Number(m.avgTotalGas || 0);
        count += 1;
      }
      const avgMape = count > 0 ? mapeSum / count : 0;
      const avgGas = count > 0 ? gasSum / count : 0;
      profileAgg[profile][mode] = { avgMape, avgGas };
      overall[mode].mapeSum += avgMape;
      overall[mode].gasSum += avgGas;
      overall[mode].count += 1;
    }
  }

  for (const mode of modeNames) {
    const row = { mode };
    for (const profile of profileNames) {
      const v = profileAgg[profile][mode] || { avgMape: 0, avgGas: 0 };
      row[`MAPE_${profile}`] = v.avgMape;
      row[`GAS_${profile}`] = v.avgGas;
    }
    modeRows.push(row);
  }

  lines.push("# 工业数据采集聚合实验报告");
  lines.push("");
  lines.push(`生成时间：${report.generatedAt}`);
  lines.push("");
  lines.push("## 实验设置（简述）");
  lines.push("");
  lines.push("- 本实验为仿真实验，采用公开数据集并模拟多节点观测。");
  lines.push(`- 数据集数量：${datasets.length}；聚合方法：${modeNames.join(" / ")}。`);
  lines.push(`- 场景：${profileNames.map(normalizeProfileName).join("、")}。`);
  lines.push("- 核心表按场景展示（跨数据集平均），不再在表中区分数据集。");
  lines.push("");
  lines.push("## 数据集介绍");
  lines.push("");
  lines.push("| 数据集 | 指标列 | 链接 |");
  lines.push("| --- | --- | --- |");
  for (const d of datasets) {
    lines.push(`| ${esc(d.datasetName)} | ${esc(d.metricCol)} | ${esc(d.datasetRef)} |`);
  }
  lines.push("");
  lines.push("## 核心结果（单表）");
  lines.push("");
  const normProfiles = profileNames.map((p) => ({
    raw: p,
    label: normalizeProfileName(p)
  }));
  const sceneCols = [];
  for (const p of normProfiles) {
    sceneCols.push(`${p.label}-MAPE`);
    sceneCols.push(`${p.label}-Cost(gas)`);
  }
  lines.push(`| 聚合方法 | ${sceneCols.join(" | ")} |`);
  lines.push(`| --- | ${sceneCols.map(() => "---:").join(" | ")} |`);
  for (const r of modeRows) {
    const cells = [];
    for (const p of normProfiles) {
      cells.push(fmtP(r[`MAPE_${p.raw}`]));
      cells.push(fmtN(r[`GAS_${p.raw}`]));
    }
    lines.push(`| ${r.mode} | ${cells.join(" | ")} |`);
  }
  lines.push("");
  lines.push("## 结果分析");
  lines.push("");
  const modeOverallRows = modeNames.map((mode) => {
    const c = overall[mode].count || 1;
    return {
      mode,
      avgMape: overall[mode].mapeSum / c,
      avgGas: overall[mode].gasSum / c
    };
  });
  const bestOverallPrecision = [...modeOverallRows].sort((a, b) => a.avgMape - b.avgMape || a.avgGas - b.avgGas)[0];
  const bestOverallCost = [...modeOverallRows].sort((a, b) => a.avgGas - b.avgGas || a.avgMape - b.avgMape)[0];
  const profileBest = normProfiles.map((p) => {
    const byPrecision = [...modeRows].sort(
      (a, b) => a[`MAPE_${p.raw}`] - b[`MAPE_${p.raw}`] || a[`GAS_${p.raw}`] - b[`GAS_${p.raw}`]
    )[0];
    return { profile: p.label, bestMode: byPrecision.mode };
  });
  const cleanBest = profileBest.find((x) => x.profile.includes("轻微扰动"));
  const issueBest = profileBest.filter((x) => !x.profile.includes("轻微扰动"));
  const issueModeCount = {};
  for (const x of issueBest) {
    issueModeCount[x.bestMode] = (issueModeCount[x.bestMode] || 0) + 1;
  }
  const topIssueMode = Object.entries(issueModeCount).sort((a, b) => b[1] - a[1])[0]?.[0] || "-";
  lines.push(
    `1. 总体上，精度最佳为 ${bestOverallPrecision.mode}（平均 MAPE ${fmtP(
      bestOverallPrecision.avgMape
    )}），成本最低为 ${bestOverallCost.mode}（平均 Cost ${fmtN(bestOverallCost.avgGas)} gas）。`
  );
  lines.push(
    `2. 在“轻微扰动场景”中，${cleanBest ? cleanBest.bestMode : "-"} 为精度最佳，更适合较干净数据。`
  );
  lines.push(`3. 在“单点异常/缺失数据场景”中，${topIssueMode} 更适合问题数据。`);
  lines.push("4. 结论可直接用于方法选择：先看数据质量，再在精度与链上成本之间做折中。");
  lines.push("");
  lines.push("## 说明");
  lines.push("");
  lines.push("- MAPE 越低越好；Cost(gas) 越低越好。");
  lines.push("- “异构权重”仅作 Gas 测算，不纳入本表精度对比。");
  lines.push("");
  lines.push("## 复现实验命令");
  lines.push("");
  lines.push("```bash");
  lines.push("cd /home/logres/system/Experiment/Current/Oracle");
  lines.push("npm run experiment:data-industrial-report");
  lines.push("```");
  lines.push("");

  return lines.join("\n");
}

function main() {
  const root = path.join(__dirname, "..");
  const jsonPath = path.join(root, "report", "data-industrial-aggregation-report.json");
  const outPath = path.join(root, "report", "DATA_INDUSTRIAL_AGGREGATION_REPORT.md");

  const report = readJson(jsonPath);
  fs.writeFileSync(outPath, toMarkdown(report), "utf8");
  console.log(`markdown report -> ${outPath}`);
}

main();
