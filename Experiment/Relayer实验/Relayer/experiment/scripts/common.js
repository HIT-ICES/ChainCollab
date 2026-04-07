const fs = require("fs");
const path = require("path");
const { ethers } = require("ethers");

const ROOT = path.join(__dirname, "..", "..");
const RUNTIME_DIR = path.join(ROOT, "src", "relayer-node", "runtime");
const DEPLOYMENTS_DIR = path.join(ROOT, "experiment", "report");

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function loadJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function writeJson(filePath, obj) {
  ensureDir(path.dirname(filePath));
  fs.writeFileSync(filePath, JSON.stringify(obj, null, 2), "utf8");
}

function devnetConfigPath() {
  return path.join(RUNTIME_DIR, "devnet.json");
}

function deploymentPath() {
  return path.join(DEPLOYMENTS_DIR, "multichain-addresses.json");
}

function relayerStatePath() {
  return path.join(RUNTIME_DIR, "relayer-state.json");
}

function contractArtifactPath(contractName, sourcePath = null) {
  const targetName = String(contractName || "").trim();
  if (!targetName) {
    throw new Error("contractArtifactPath requires a contract name");
  }
  const candidates = [];
  if (sourcePath) {
    const normSource = String(sourcePath).replace(/\\/g, "/");
    const base = normSource
      .replace(/^.*\/src\/contract\//, "")
      .replace(/^.*\/contracts\//, "");
    if (base.endsWith(".sol")) {
      candidates.push(path.join(ROOT, "artifacts", "src", "contract", base, `${targetName}.json`));
      candidates.push(path.join(ROOT, "artifacts", "contracts", base, `${targetName}.json`));
    }
  }
  candidates.push(
    path.join(ROOT, "artifacts", "src", "contract", "generated", `${targetName}.sol`, `${targetName}.json`)
  );
  candidates.push(
    path.join(ROOT, "artifacts", "contracts", "generated", `${targetName}.sol`, `${targetName}.json`)
  );
  candidates.push(path.join(ROOT, "artifacts", "src", "contract", `${targetName}.sol`, `${targetName}.json`));
  candidates.push(path.join(ROOT, "artifacts", "contracts", `${targetName}.sol`, `${targetName}.json`));
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }
  return candidates[0];
}

function datasetConfigPath() {
  const fromEnv = process.env.RELAYER_DATASET_CONFIG;
  if (fromEnv && fromEnv.trim()) {
    return path.isAbsolute(fromEnv)
      ? fromEnv.trim()
      : path.join(ROOT, fromEnv.trim());
  }
  return path.join(ROOT, "experiment", "dataset", "relayer_experiment_dataset.json");
}

function loadDevnetConfig() {
  const cfgPath = devnetConfigPath();
  if (!fs.existsSync(cfgPath)) {
    throw new Error(`devnet config not found: ${cfgPath}. run npm run chain:up first`);
  }
  return loadJson(cfgPath);
}

function loadDeployment() {
  const p = deploymentPath();
  if (!fs.existsSync(p)) {
    throw new Error(`deployment file not found: ${p}. run npm run deploy first`);
  }
  return loadJson(p);
}

function loadDatasetConfig(optional = true) {
  const p = datasetConfigPath();
  if (!fs.existsSync(p)) {
    if (optional) {
      return null;
    }
    throw new Error(`dataset config not found: ${p}`);
  }
  return loadJson(p);
}

function deriveWallet(mnemonic, index, provider) {
  const wallet = ethers.HDNodeWallet.fromPhrase(
    mnemonic,
    undefined,
    `m/44'/60'/0'/0/${index}`
  );
  return wallet.connect(provider);
}

module.exports = {
  ROOT,
  RUNTIME_DIR,
  DEPLOYMENTS_DIR,
  ensureDir,
  loadJson,
  writeJson,
  devnetConfigPath,
  deploymentPath,
  relayerStatePath,
  contractArtifactPath,
  loadDevnetConfig,
  loadDeployment,
  datasetConfigPath,
  loadDatasetConfig,
  deriveWallet
};
