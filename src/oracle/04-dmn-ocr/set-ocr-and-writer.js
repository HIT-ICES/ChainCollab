const fs = require('fs');
const http = require('http');
const path = require('path');
const { URL } = require('url');

const ROOT_DIR = path.resolve(__dirname, '..', '..');

function resolveChainlinkRoot() {
  const candidates = [];
  if (process.env.CHAINLINK_ROOT) {
    candidates.push(path.resolve(process.env.CHAINLINK_ROOT));
  }
  candidates.push(path.resolve(__dirname, '..', 'CHAINLINK'));
  candidates.push(path.resolve(__dirname, '..', '..'));

  for (const candidate of candidates) {
    if (fs.existsSync(path.join(candidate, 'deployment')) && fs.existsSync(path.join(candidate, 'package.json'))) {
      return candidate;
    }
  }
  return candidates[0];
}

function readJson(filePath, required = true) {
  if (!fs.existsSync(filePath)) {
    if (required) {
      throw new Error(`缺少部署文件: ${filePath}`);
    }
    return null;
  }
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function firstExisting(paths, required = true) {
  for (const filePath of paths) {
    if (fs.existsSync(filePath)) {
      return filePath;
    }
  }
  if (required) {
    throw new Error(`找不到文件: ${paths.join(' | ')}`);
  }
  return null;
}

const CHAINLINK_ROOT = resolveChainlinkRoot();
const CHAINLINK_DEPLOYMENT_DIR = path.join(CHAINLINK_ROOT, 'deployment');
const SHARED_DEPLOYMENT_DIR = path.join(ROOT_DIR, 'deployment');

function requireFromChainlink(modName) {
  try {
    return require(modName);
  } catch (_) {
    return require(path.join(CHAINLINK_ROOT, 'node_modules', modName));
  }
}

const deployment = readJson(path.join(CHAINLINK_DEPLOYMENT_DIR, 'deployment.json'));
const chainlinkDeployment = readJson(path.join(CHAINLINK_DEPLOYMENT_DIR, 'chainlink-deployment.json'));
const nodeInfo = readJson(
  firstExisting([
    path.join(SHARED_DEPLOYMENT_DIR, 'node-info.json'),
    path.join(CHAINLINK_DEPLOYMENT_DIR, 'node-info.json'),
  ])
);
const compiled = readJson(path.join(CHAINLINK_DEPLOYMENT_DIR, 'compiled.json'));
const DMN_MODE = process.env.DMN_MODE === 'lite' ? 'lite' : 'full';
const contractKey =
  DMN_MODE === 'lite'
    ? 'contracts/MyChainlinkRequesterDMN_Lite.sol:MyChainlinkRequesterDMN_Lite'
    : 'contracts/MyChainlinkRequesterDMN.sol:MyChainlinkRequesterDMN';
const abi = compiled.contracts[contractKey].abi;

const RPC_URL = process.env.RPC_URL || 'http://localhost:8545';

function rpcCall(method, params) {
  return new Promise((resolve, reject) => {
    const postData = JSON.stringify({
      jsonrpc: '2.0',
      method,
      params,
      id: 1,
    });

    const rpc = new URL(RPC_URL);
    const options = {
      hostname: rpc.hostname,
      port: rpc.port || (rpc.protocol === 'https:' ? 443 : 80),
      path: rpc.pathname === '' ? '/' : rpc.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData),
      },
    };

    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => {
        data += chunk;
      });
      res.on('end', () => {
        const response = JSON.parse(data);
        if (response.error) reject(new Error(response.error.message));
        else resolve(response.result);
      });
    });

    req.on('error', reject);
    req.write(postData);
    req.end();
  });
}

function findBaselineWriters() {
  if (!Array.isArray(nodeInfo)) return [];
  return nodeInfo
    .filter((node) => node.name && (node.name.startsWith('node') || node.name === 'bootstrap'))
    .map((node) => node.ethAddress)
    .filter(Boolean);
}

function getFunctionAbi(name) {
  return abi.find((item) => item.type === 'function' && item.name === name);
}

async function sendTx(contractAddress, fnName, args, gas) {
  const fn = getFunctionAbi(fnName);
  if (!fn) {
    throw new Error(`Missing ABI for ${fnName}`);
  }
  const Web3EthAbi = requireFromChainlink('web3-eth-abi');
  const data = Web3EthAbi.encodeFunctionCall(fn, args);
  const accounts = await rpcCall('eth_accounts', []);
  const deployer = accounts[0];
  const txHash = await rpcCall('eth_sendTransaction', [
    {
      from: deployer,
      to: contractAddress,
      data,
      gas: '0x' + gas.toString(16),
    },
  ]);
  return txHash;
}

async function main() {
  const contractAddress =
    process.env.DMN_REQUEST_CONTRACT_ADDRESS || deployment.contractAddress;
  const ocrAggregator =
    process.env.OCR_AGGREGATOR_ADDRESS || chainlinkDeployment.ocrContract;
  const writers = process.env.BASELINE_WRITERS
    ? process.env.BASELINE_WRITERS.split(',').map((v) => v.trim()).filter(Boolean)
    : findBaselineWriters();
  const hasSetOcrAggregator = Boolean(getFunctionAbi('setOcrAggregator'));

  if (!contractAddress) {
    console.error('缺少合约地址：deployment/deployment.json 或 DMN_REQUEST_CONTRACT_ADDRESS');
    process.exit(1);
  }
  if (hasSetOcrAggregator && !ocrAggregator) {
    console.error('缺少 OCR aggregator 地址：deployment/chainlink-deployment.json 或 OCR_AGGREGATOR_ADDRESS');
    process.exit(1);
  }
  if (!writers || writers.length === 0) {
    console.error('缺少 baseline writer 地址：deployment/node-info.json 或 BASELINE_WRITERS');
    process.exit(1);
  }

  console.log('合约地址:', contractAddress);
  console.log('模式:', DMN_MODE);
  if (hasSetOcrAggregator) {
    console.log('OCR aggregator:', ocrAggregator);
  } else {
    console.log('OCR aggregator: <skip in lite mode>');
  }
  console.log('baseline writers:', writers.join(', '));

  if (hasSetOcrAggregator) {
    const tx1 = await sendTx(contractAddress, 'setOcrAggregator', [ocrAggregator], 200000);
    console.log('✅ setOcrAggregator 交易已发送:', tx1);
  }

  for (const writer of writers) {
    const tx2 = await sendTx(contractAddress, 'setBaselineWriter', [writer, true], 200000);
    console.log(`✅ setBaselineWriter(${writer}) 交易已发送:`, tx2);
  }
}

main().catch((err) => {
  console.error('❌ 失败:', err.message);
  process.exit(1);
});
