import fs from "fs";
import path from "path";
import { id } from "ethers";

export const DEPLOYMENT_FILE = path.resolve("deployments/local.json");

export function ensureDeploymentsDir() {
  const dir = path.dirname(DEPLOYMENT_FILE);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

export function writeDeployment(payload) {
  ensureDeploymentsDir();
  fs.writeFileSync(DEPLOYMENT_FILE, JSON.stringify(payload, null, 2));
}

export function readDeployment() {
  if (!fs.existsSync(DEPLOYMENT_FILE)) {
    throw new Error(`deployment file missing: ${DEPLOYMENT_FILE}`);
  }
  return JSON.parse(fs.readFileSync(DEPLOYMENT_FILE, "utf-8"));
}

export function readBuildArtifact(contractName) {
  const artifactPath = path.resolve(`build/${contractName}.json`);
  if (!fs.existsSync(artifactPath)) {
    throw new Error(
      `build artifact missing: ${artifactPath}. run npm run build first`
    );
  }
  return JSON.parse(fs.readFileSync(artifactPath, "utf-8"));
}

export function toSlotKey(name) {
  return id(name);
}

export function fromBigNumberish(v) {
  if (typeof v === "bigint") {
    return Number(v);
  }
  if (typeof v === "number") {
    return v;
  }
  return Number(v.toString());
}

export function fmtGas(receipt, label) {
  return {
    step: label,
    gasUsed: receipt.gasUsed.toString(),
    effectiveGasPrice: receipt.effectiveGasPrice?.toString() || "0",
    txHash: receipt.hash
  };
}
