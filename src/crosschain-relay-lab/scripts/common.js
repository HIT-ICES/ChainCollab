const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const BUILD_DIR = path.join(ROOT, "build");
const DEPLOY_DIR = path.join(ROOT, "deployments");
const LOCAL_DEPLOY_FILE = path.join(DEPLOY_DIR, "local.json");

const DEFAULTS = {
  chainA: {
    name: "chainA",
    chainId: 31337,
    rpcUrl: process.env.CHAIN_A_RPC || "http://127.0.0.1:8545"
  },
  chainB: {
    name: "chainB",
    chainId: 31338,
    rpcUrl: process.env.CHAIN_B_RPC || "http://127.0.0.1:9545"
  },
  keys: {
    deployer:
      process.env.DEPLOYER_KEY ||
      "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
    relayer:
      process.env.RELAYER_KEY ||
      "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",
    user:
      process.env.USER_KEY ||
      "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a"
  }
};

function ensureDir(dir) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

function writeJson(file, payload) {
  ensureDir(path.dirname(file));
  fs.writeFileSync(file, JSON.stringify(payload, null, 2));
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf-8"));
}

function readArtifact(name) {
  const file = path.join(BUILD_DIR, `${name}.json`);
  if (!fs.existsSync(file)) {
    throw new Error(`artifact missing: ${file}. run npm run build first`);
  }
  return readJson(file);
}

function readDeployment(file = LOCAL_DEPLOY_FILE) {
  if (!fs.existsSync(file)) {
    throw new Error(`deployment missing: ${file}. run npm run deploy first`);
  }
  return readJson(file);
}

module.exports = {
  ROOT,
  BUILD_DIR,
  DEPLOY_DIR,
  LOCAL_DEPLOY_FILE,
  DEFAULTS,
  ensureDir,
  writeJson,
  readJson,
  readArtifact,
  readDeployment
};
