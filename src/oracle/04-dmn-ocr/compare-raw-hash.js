const fs = require('fs');
const path = require('path');
const { ethers } = require('ethers');
const axios = require('axios');

const ROOT_DIR = path.resolve(__dirname, '..', '..');
const DEPLOYMENT_DIR = path.join(ROOT_DIR, 'deployment');
const chainlinkDeployment = JSON.parse(
  fs.readFileSync(path.join(DEPLOYMENT_DIR, 'chainlink-deployment.json'), 'utf8')
);
const deploymentPath = path.join(DEPLOYMENT_DIR, 'deployment.json');
const deployment = fs.existsSync(deploymentPath)
  ? JSON.parse(fs.readFileSync(deploymentPath, 'utf8'))
  : null;

const RPC_URL = process.env.RPC_URL || 'http://localhost:8545';

function parseArgs(args) {
  const out = {};
  for (let i = 0; i < args.length; i += 1) {
    const key = args[i];
    const next = args[i + 1];
    if (key === '--raw' && next) {
      out.raw = next;
      i += 1;
    } else if (key === '--raw-file' && next) {
      out.rawFile = next;
      i += 1;
    } else if (key === '--hash' && next) {
      out.hash = next;
      i += 1;
    } else if (key === '--request-id' && next) {
      out.requestId = next;
      i += 1;
    } else if (key === '--dmn-url' && next) {
      out.dmnUrl = next;
      i += 1;
    } else if (key === '--rpc' && next) {
      out.rpc = next;
      i += 1;
    } else if (key === '--ocr' && next) {
      out.ocr = next;
      i += 1;
    } else if (key === '--contract' && next) {
      out.contract = next;
      i += 1;
    } else if (!key.startsWith('--') && !out.raw) {
      out.raw = key;
    }
  }
  return out;
}

function pad128(value) {
  return '0x' + value.toString(16).padStart(32, '0');
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const ocrAddress =
    args.ocr || process.env.OCR_AGGREGATOR_ADDRESS || chainlinkDeployment.ocrContract;
  const rpcUrl = args.rpc || RPC_URL;
  const contractAddress =
    args.contract || process.env.DMN_REQUEST_CONTRACT_ADDRESS || deployment?.contractAddress;

  let raw = args.raw || process.env.RAW;
  if (!raw && args.rawFile) {
    raw = fs.readFileSync(args.rawFile, 'utf8');
  }
  if (!raw && (args.hash || process.env.HASH)) {
    const hash = args.hash || process.env.HASH;
    const dmnUrl = args.dmnUrl || process.env.DMN_RAW_BY_HASH_URL;
    if (!dmnUrl) {
      console.error('缺少 DMN_RAW_BY_HASH_URL 或 --dmn-url');
      process.exit(1);
    }
    const url = `${dmnUrl}${dmnUrl.includes('?') ? '&' : '?'}hash=${encodeURIComponent(hash)}`;
    const res = await axios.get(url, { timeout: 10000 });
    raw = res?.data?.raw;
  }

  if (!raw) {
    if (args.requestId) {
      raw = null;
    } else {
      console.error('用法: node features/04-dmn-ocr/compare-raw-hash.js --raw \'[{"result":"Pasta"}]\'');
      console.error('或:   RAW=\'[{"result":"Pasta"}]\' node features/04-dmn-ocr/compare-raw-hash.js');
      console.error('或:   node features/04-dmn-ocr/compare-raw-hash.js --raw-file ./raw.txt');
      console.error('或:   DMN_RAW_BY_HASH_URL=http://.../api/dmn/by-hash HASH=0x... node features/04-dmn-ocr/compare-raw-hash.js');
      console.error('或:   node features/04-dmn-ocr/compare-raw-hash.js --request-id 0x...');
      process.exit(1);
    }
  }
  if (!ocrAddress) {
    console.error('缺少 OCR aggregator 地址：设置 OCR_AGGREGATOR_ADDRESS 或 deployment/chainlink-deployment.json');
    process.exit(1);
  }

  const provider = new ethers.JsonRpcProvider(rpcUrl);
  const ocr = new ethers.Contract(ocrAddress, ['function latestAnswer() view returns (int256)'], provider);
  const latest = await ocr.latestAnswer();

  const mask = (1n << 128n) - 1n;
  if (latest < 0n) {
    console.error('OCR latestAnswer 为负数，无法比较');
    process.exit(1);
  }
  const ocrHash = BigInt(latest) & mask;

  if (raw) {
    const rawHashHex = ethers.keccak256(ethers.toUtf8Bytes(raw));
    const rawHash = BigInt(rawHashHex);
    const rawHashLow = rawHash & mask;

    console.log('OCR latestAnswer (int256):', latest.toString());
    console.log('OCR hash (low128 hex):   ', pad128(ocrHash));
    console.log('raw keccak256 (hex):     ', rawHashHex);
    console.log('raw hash (low128 hex):   ', pad128(rawHashLow));
    console.log('match:', ocrHash === rawHashLow);
    return;
  }

  if (!args.requestId) {
    console.error('缺少 --request-id 或 raw');
    process.exit(1);
  }
  if (!contractAddress) {
    console.error('缺少合约地址：设置 DMN_REQUEST_CONTRACT_ADDRESS 或 deployment/deployment.json');
    process.exit(1);
  }

  const dmn = new ethers.Contract(
    contractAddress,
    [
      'function baselines(bytes32) view returns (bytes32 hash, uint128 hashLow, string raw, bool exists)',
      'function isOcrMatch(bytes32 requestId) view returns (bool)',
    ],
    provider
  );
  const baseline = await dmn.baselines(args.requestId);
  const ok = await dmn.isOcrMatch(args.requestId);
  console.log('OCR latestAnswer (int256):', latest.toString());
  console.log('OCR hash (low128 hex):   ', pad128(ocrHash));
  console.log('baseline.exists:', baseline.exists);
  console.log('baseline.hash:', baseline.hash);
  console.log('baseline.hashLow:', pad128(BigInt(baseline.hashLow)));
  console.log('match:', ok);
}

main().catch((err) => {
  console.error('❌ Failed:', err.message);
  process.exit(1);
});
