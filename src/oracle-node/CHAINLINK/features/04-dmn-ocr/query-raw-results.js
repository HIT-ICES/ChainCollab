const fs = require('fs');
const path = require('path');
const { ethers } = require('ethers');

const ROOT_DIR = path.resolve(__dirname, '..', '..');
const DEPLOYMENT_DIR = path.join(ROOT_DIR, 'deployment');
const COMPILED_PATH = path.join(DEPLOYMENT_DIR, 'compiled.json');
const DEPLOYMENT_PATH = path.join(DEPLOYMENT_DIR, 'deployment.json');

const RPC_URL = process.env.RPC_URL || 'http://localhost:8545';

function readJson(filePath) {
  if (!fs.existsSync(filePath)) return null;
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch (_) {
    return null;
  }
}

function loadAbi() {
  const compiled = readJson(COMPILED_PATH);
  const key = 'contracts/MyChainlinkRequesterDMN.sol:MyChainlinkRequesterDMN';
  const abi = compiled?.contracts?.[key]?.abi;
  if (!abi) {
    throw new Error(`Missing ABI in ${COMPILED_PATH}`);
  }
  return abi;
}

async function main() {
  const deployment = readJson(DEPLOYMENT_PATH);
  const contractAddress =
    process.env.DMN_REQUEST_CONTRACT_ADDRESS || deployment?.contractAddress;
  if (!contractAddress) {
    console.error('Missing contract address: set DMN_REQUEST_CONTRACT_ADDRESS or deployment/deployment.json');
    process.exit(1);
  }

  const abi = loadAbi();
  const provider = new ethers.JsonRpcProvider(RPC_URL);
  const contract = new ethers.Contract(contractAddress, abi, provider);

  const args = process.argv.slice(2).filter(Boolean);
  if (args.length > 0) {
    for (const hash of args) {
      const raw = await contract.rawResults(hash);
      console.log(`${hash} -> ${raw}`);
    }
    return;
  }

  if (typeof contract.getAllRawResults === 'function') {
    const [hashes, raws] = await contract.getAllRawResults();
    const total = hashes.length;
    const limit = Math.min(total, Number(process.env.LIMIT || total));
    console.log(`rawResultCount=${total}`);
    for (let i = 0; i < limit; i += 1) {
      console.log(`[${i}] ${hashes[i]} -> ${raws[i]}`);
    }
    return;
  }

  if (typeof contract.rawResultCount !== 'function' || typeof contract.rawResultHashAt !== 'function') {
    console.error('Contract missing getAllRawResults/rawResultCount/rawResultHashAt. Redeploy with updated contract.');
    process.exit(1);
  }

  const count = await contract.rawResultCount();
  const total = Number(count);
  const limit = Math.min(total, Number(process.env.LIMIT || total));
  console.log(`rawResultCount=${total}`);
  for (let i = 0; i < limit; i += 1) {
    const hash = await contract.rawResultHashAt(i);
    const raw = await contract.rawResults(hash);
    console.log(`[${i}] ${hash} -> ${raw}`);
  }
}

main().catch((err) => {
  console.error('❌ Failed:', err.message);
  process.exit(1);
});
