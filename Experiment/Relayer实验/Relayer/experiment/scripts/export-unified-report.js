const fs = require("fs");
const path = require("path");
const {
  ROOT,
  DEPLOYMENTS_DIR,
  writeJson,
  loadDatasetConfig,
  datasetConfigPath
} = require("./common");

function loadIfExists(filePath) {
  if (!fs.existsSync(filePath)) {
    return null;
  }
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function fmtPct(v) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) {
    return "N/A";
  }
  return `${(Number(v || 0) * 100).toFixed(2)}%`;
}

function fmtNum(v, digits = 3) {
  return Number(v || 0).toFixed(digits);
}

const CASE_NAME_ZH = {
  SupplyChain: "供应链",
  Manufactory: "制造业",
  ManagementSystem: "管理系统",
  Purchase: "采购",
  IncidentManagement: "客户服务",
  HotelBooking: "酒店预订",
  Hotel_Booking: "酒店预订",
  CustomerService: "客户服务",
  customer_new: "客户服务",
  BloodAnalysis: "血液检测",
  Blood_analysis: "血液检测",
  AmazonSLA: "Amazon 服务级别协议",
  amazon: "Amazon 服务级别协议",
  amazon_new2: "Amazon 服务级别协议",
  PizzaOrder: "披萨订购",
  Pizza_Order: "披萨订购",
  RentalClaim: "租赁理赔",
  Rental_Claim: "租赁理赔",
  BikeRental: "单车租赁"
};

function caseNameZh(caseId) {
  return CASE_NAME_ZH[caseId] || caseId;
}

function buildMarkdown(payload) {
  const c = payload.correctness;
  const o = payload.overheadLatency;
  const submittedSet = new Set(
    (c?.perCase || [])
      .map((x) => Number(x.submitted || 0))
      .filter((v) => Number.isFinite(v) && v > 0)
  );
  const uniformRuns = submittedSet.size === 1 ? Array.from(submittedSet)[0] : null;
  const lines = [
    "# Relayer 实验报告（正确性与开销/延迟）",
    "",
    `生成时间：${payload.generatedAt}`,
    "",
    "## 1. 实验设置",
    "",
    `- 配置文件：\`${payload.dataset.path}\``,
    `- 数据集名称：\`${payload.dataset.name || "N/A"}\``,
    `- BPMN 案例数：${payload.dataset.caseCount}`,
    uniformRuns ? `- 每场景实验次数：${uniformRuns}（统一）` : "- 每场景实验次数：不统一",
    `- 源链：${payload.chains.source.name} (${payload.chains.source.chainId})`,
    `- 目标链：${payload.chains.target.name} (${payload.chains.target.chainId})`,
    "- 执行口径：Full 与 Split 均采用“逐函数推进”执行（不是单笔占位交易）。",
    "- 说明：部分场景在流程结构上存在重合，用于验证 Relayer 机制在相近流程模板下的稳定性。",
    "",
    "| 场景（中文） | 场景标识 | BPMN路径 |",
    "| --- | --- | --- |"
  ];

  for (const c of payload.dataset.cases) {
    lines.push(`| ${caseNameZh(c.caseId || "-")} | ${c.caseId || "-"} | ${c.bpmnPath || "-"} |`);
  }

  if (c) {
    const overheadByCase = new Map((o?.perCase || []).map((x) => [x.caseId, x]));
    const splitByCase = new Map((c?.perCase || []).map((x) => [x.caseId, x]));
    lines.push(
      "",
      "## 2. 正确性与开销实验结果",
      "",
      "| 场景 | 成功率 | Full平均Gas（gas） | Split平均Gas（gas） | 跨链附加开销（gas） | 总成本变化（gas） | 总成本变化比例 |",
      "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"
    );
    for (const x of c.perCase || []) {
      const overhead = overheadByCase.get(x.caseId);
      const splitCase = splitByCase.get(x.caseId);
      const fullGas = overhead ? fmtNum(overhead.full.gasTotalAvg, 2) : "N/A";
      const splitGas = overhead ? fmtNum(overhead.split.gasTotalAvg, 2) : "N/A";
      const bridgeGas = splitCase?.gas?.bridgeAvg;
      const gasDelta = overhead ? fmtNum(overhead.comparison.gasDelta, 2) : "N/A";
      const gasOverhead = overhead ? fmtPct(overhead.comparison.gasOverheadRatio) : "N/A";
      lines.push(
        `| ${caseNameZh(x.caseId)} | ${fmtPct(x.successRate)} | ${fullGas} | ${splitGas} | ${bridgeGas !== undefined ? fmtNum(bridgeGas, 2) : "N/A"} | ${gasDelta} | ${gasOverhead} |`
      );
    }
    lines.push("");
  }

  if (o) {
    lines.push("## 3. Latency 实验结果（按场景）", "");
    lines.push(
      "| 场景 | Full E2E均值（s, wall-clock） | Split E2E均值（s, wall-clock） | 延迟开销比例 |",
      "| --- | ---: | ---: | ---: |"
    );
    for (const x of o.perCase || []) {
      const fullSec = Number(x?.full?.wallAvgMs || 0) / 1000;
      const splitSec = Number(x?.split?.wallAvgMs || 0) / 1000;
      const overhead = x?.comparison?.wallOverheadRatio ?? x?.comparison?.chainOverheadRatio;
      lines.push(
        `| ${caseNameZh(x.caseId)} | ${fmtNum(fullSec)} | ${fmtNum(splitSec)} | ${fmtPct(overhead)} |`
      );
    }
    lines.push("");
  }

  lines.push(
    "## 4. 一键复现实验与导出",
    "",
    "```bash",
    "cd /home/logres/system/Experiment/Current/Relayer",
    "npm install",
    "npm run experiment:relayer:full",
    "```",
    "",
    "产物：",
    "- `experiment/report/RELAYER_UNIFIED_EXPERIMENT_REPORT.md`",
    "- `experiment/report/relayer-unified-report.json`",
    "- `experiment/report/LATENCY_FULL_VS_SPLIT_REPORT.md`",
    "- `experiment/report/latency-full-vs-split-report.json`",
    "- `experiment/report/CORRECTNESS_SPLIT_LATENCY_REPORT.md`",
    ""
  );

  return lines.join("\n");
}

function main() {
  const datasetPath = datasetConfigPath();
  const dataset = loadDatasetConfig(true) || {};
  const splitCases =
    loadIfExists(path.join(DEPLOYMENTS_DIR, "bpmn-split-cases.json")) ||
    loadIfExists(path.join(ROOT, "experiment", "dataset", "bpmn_split_cases.json")) ||
    { cases: [] };
  const splitLatency = loadIfExists(
    path.join(DEPLOYMENTS_DIR, "correctness-split-latency-report.json")
  );
  const fullVsSplitLatency = loadIfExists(
    path.join(DEPLOYMENTS_DIR, "latency-full-vs-split-report.json")
  );

  const sourceChain = dataset?.chains?.source || {
    name: "chainA",
    type: "local-anvil-evm",
    rpcUrl: "http://127.0.0.1:8545",
    chainId: 31337
  };
  const targetChain = dataset?.chains?.target || {
    name: "chainB",
    type: "local-anvil-evm",
    rpcUrl: "http://127.0.0.1:9545",
    chainId: 31338
  };

  const payload = {
    generatedAt: new Date().toISOString(),
    dataset: {
      path: datasetPath,
      name: dataset?.name || null,
      caseCount: (splitCases.cases || []).length,
      cases: (splitCases.cases || []).map((x) => ({
        caseId: x.caseId,
        bpmnPath: x.bpmnPath
      }))
    },
    chains: {
      source: sourceChain,
      target: targetChain
    },
    results: {
      splitLatency,
      fullVsSplitLatency
    },
    correctness: splitLatency || null,
    overheadLatency: fullVsSplitLatency || null
  };

  const reportJsonPath = path.join(DEPLOYMENTS_DIR, "relayer-unified-report.json");
  const reportMdPath = path.join(DEPLOYMENTS_DIR, "RELAYER_UNIFIED_EXPERIMENT_REPORT.md");
  writeJson(reportJsonPath, payload);
  fs.writeFileSync(reportMdPath, buildMarkdown(payload), "utf8");

  console.log(`relayer unified report json -> ${reportJsonPath}`);
  console.log(`relayer unified report md -> ${reportMdPath}`);
}

main();
