const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");
const {
  ROOT,
  RUNTIME_DIR,
  DEPLOYMENTS_DIR,
  writeJson,
  loadDatasetConfig,
  datasetConfigPath
} = require("./common");

const TRANSLATOR_ROOT = "/home/logres/system/src/newTranslator";
const TRANSLATOR_VENV_PYTHON = path.join(TRANSLATOR_ROOT, ".venv", "bin", "python");

const DEFAULT_CASES = [
  "/home/logres/system/Experiment/CaseTest/SupplyChain.bpmn",
  "/home/logres/system/Experiment/CaseTest/Manufactory.bpmn",
  "/home/logres/system/Experiment/CaseTest/Coffee_machine.bpmn"
];

function run(cmd, args, opts = {}) {
  const ret = spawnSync(cmd, args, {
    encoding: "utf8",
    stdio: "pipe",
    ...opts
  });
  if (ret.status !== 0) {
    const detail = ret.stderr || ret.stdout || "unknown error";
    throw new Error(`${cmd} ${args.join(" ")} failed: ${detail}`);
  }
  return ret.stdout || "";
}

function resolveTranslatorPython() {
  if (process.env.TRANSLATOR_PYTHON && process.env.TRANSLATOR_PYTHON.trim()) {
    return process.env.TRANSLATOR_PYTHON.trim();
  }
  if (fs.existsSync(TRANSLATOR_VENV_PYTHON)) {
    return TRANSLATOR_VENV_PYTHON;
  }
  return "python3";
}

function safeName(filePath) {
  return path.basename(filePath).replace(/\.bpmn$/i, "").replace(/\s+/g, "_");
}

function parseCases(datasetConfig) {
  const fromEnv = process.env.BPMN_CASES;
  if (!fromEnv) {
    const fromDataset = Array.isArray(datasetConfig?.bpmnCases)
      ? datasetConfig.bpmnCases
      : [];
    if (!fromDataset.length) {
      return DEFAULT_CASES.map((p) => ({ path: p, splitPointIds: [], mergePointId: "" }));
    }
    return fromDataset.map((x) => {
      if (typeof x === "string") {
        return { path: x, splitPointIds: [], mergePointId: "" };
      }
      return {
        path: String(x.path || "").trim(),
        splitPointIds: Array.isArray(x.splitPointIds)
          ? x.splitPointIds.map((s) => String(s).trim()).filter(Boolean)
          : [],
        mergePointId: String(x.mergePointId || "").trim()
      };
    });
  }
  return fromEnv
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean)
    .map((p) => ({ path: p, splitPointIds: [], mergePointId: "" }));
}

function parseGlobalSplitPoints(datasetConfig) {
  const fromEnv = process.env.SPLIT_POINT_IDS || "";
  if (fromEnv.trim()) {
    return fromEnv
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean);
  }
  const points = datasetConfig?.split?.globalPointIds;
  if (!Array.isArray(points)) {
    return [];
  }
  return points.map((x) => String(x).trim()).filter(Boolean);
}

function deriveTaskBudget(submodels, taskPolicy) {
  const base = submodels.reduce((acc, x) => acc + Number(x.nodeCount || 0), 0);
  const multiplier = Number(taskPolicy?.budgetMultiplier || 3);
  const minTasks = Number(taskPolicy?.minTasks || 20);
  const maxTasks = Number(taskPolicy?.maxTasks || 90);
  return Math.max(minTasks, Math.min(maxTasks, Math.round(base * multiplier)));
}

function main() {
  if (!fs.existsSync(TRANSLATOR_ROOT)) {
    throw new Error(`translator root not found: ${TRANSLATOR_ROOT}`);
  }
  const translatorPython = resolveTranslatorPython();

  const runtimeForkOutDir = path.join(RUNTIME_DIR, "translator_split_mode");
  const generatedContractDir = path.join(ROOT, "src", "contract", "generated");
  fs.mkdirSync(runtimeForkOutDir, { recursive: true });
  fs.rmSync(generatedContractDir, { recursive: true, force: true });
  fs.mkdirSync(generatedContractDir, { recursive: true });

  const datasetConfig = loadDatasetConfig(true);
  const bpmnCases = parseCases(datasetConfig);
  const globalSplitPoints = parseGlobalSplitPoints(datasetConfig);
  const taskPolicy = datasetConfig?.taskPolicy || null;
  const cases = [];

  for (const caseConfig of bpmnCases) {
    const bpmnPath = caseConfig.path;
    if (!fs.existsSync(bpmnPath)) {
      throw new Error(`BPMN not found: ${bpmnPath}`);
    }
    const caseId = safeName(bpmnPath);
    const cliArgs = [
      "-m",
      "generator.bpmn_to_dsl",
      bpmnPath,
      "-o",
      path.join(runtimeForkOutDir, `${caseId}.b2c`),
      "--split-mode",
      "--split-output-dir",
      runtimeForkOutDir,
    ];
    if (generatedContractDir) {
      cliArgs.push("--split-contracts-dir", generatedContractDir);
    }
    const caseSplitPoints = Array.isArray(caseConfig.splitPointIds)
      ? caseConfig.splitPointIds
      : [];
    for (const point of [...globalSplitPoints, ...caseSplitPoints]) {
      cliArgs.push("--split-point-id", point);
    }
    if (caseConfig.mergePointId) {
      cliArgs.push("--merge-point-id", caseConfig.mergePointId);
    }
    run(translatorPython, cliArgs, {
      cwd: TRANSLATOR_ROOT,
      env: { ...process.env, PYTHONPATH: TRANSLATOR_ROOT },
    });

    const planPath = path.join(runtimeForkOutDir, caseId, "split-plan.json");
    if (!fs.existsSync(planPath)) {
      throw new Error(`split plan missing: ${planPath}`);
    }
    const plan = JSON.parse(fs.readFileSync(planPath, "utf8"));
    const submodels = plan?.splitArtifacts?.submodels || [];

    const sourceContractName = plan.splitArtifacts.contracts.sourceContractName;
    const targetContractName = plan.splitArtifacts.contracts.targetContractName;
    const sourceGeneratedPath = plan.splitArtifacts.contracts.sourceContractPath;
    const targetGeneratedPath = plan.splitArtifacts.contracts.targetContractPath;

    const sourceContractPath = path.join(generatedContractDir, `${sourceContractName}.sol`);
    const targetContractPath = path.join(generatedContractDir, `${targetContractName}.sol`);
    if (sourceGeneratedPath !== sourceContractPath) {
      fs.copyFileSync(sourceGeneratedPath, sourceContractPath);
    }
    if (targetGeneratedPath !== targetContractPath) {
      fs.copyFileSync(targetGeneratedPath, targetContractPath);
    }

    const taskBudget = deriveTaskBudget(submodels, taskPolicy);
    const splitModel = submodels.length >= 2 ? "dual-submodel" : "single-submodel";

    cases.push({
      caseId,
      bpmnPath,
      generatedArtifacts: {
        splitPlanPath: planPath,
        sesePath: plan.splitArtifacts.sesePath,
        b2cPath: plan.fullArtifacts.b2cPath,
        solidityPath: plan.fullArtifacts.solidityPath,
        splitDslPath: plan.splitArtifacts.splitDslPath,
        splitContracts: {
          sourceContractName,
          sourceContractPath,
          targetContractName,
          targetContractPath
        }
      },
      split: {
        model: splitModel,
        selectedMarker: plan?.splitMarkers?.selected || null,
        selectedMerge: plan?.splitMarkers?.mergeSelected || null,
        submodels,
        taskBudget
      },
      crossChainPlan: {
        sourceChain: "chainA",
        targetChain: "chainB",
        routing: submodels.map((x) => ({
          submodelId: x.submodelId,
          route: "chainA->relayer->chainB"
        }))
      }
    });
  }

  const out = {
    generatedAt: new Date().toISOString(),
    datasetConfig: {
      path: datasetConfigPath(),
      loaded: Boolean(datasetConfig),
      taskPolicy: taskPolicy || {
        budgetMultiplier: 3,
        minTasks: 20,
        maxTasks: 90
      }
    },
    translator: {
      root: TRANSLATOR_ROOT,
      python: translatorPython,
      splitModeEntry: `${translatorPython} -m generator.bpmn_to_dsl --split-mode`
    },
    cases
  };

  const datasetOut = path.join(ROOT, "experiment", "dataset", "bpmn_split_cases.json");
  const deploymentOut = path.join(DEPLOYMENTS_DIR, "bpmn-split-cases.json");
  writeJson(datasetOut, out);
  writeJson(deploymentOut, out);

  console.log(`bpmn split dataset -> ${datasetOut}`);
  console.log(`bpmn split deployment -> ${deploymentOut}`);
}

main();
