const fs = require('fs');
const http = require('http');
const path = require('path');
const { URL } = require('url');

const ROOT_DIR = path.resolve(__dirname, '..', '..');
const DEPLOYMENT_DIR = path.join(ROOT_DIR, 'deployment');

const deployment = JSON.parse(
  fs.readFileSync(path.join(DEPLOYMENT_DIR, 'deployment.json'), 'utf8')
);
const chainlinkDeployment = JSON.parse(
  fs.readFileSync(path.join(DEPLOYMENT_DIR, 'chainlink-deployment.json'), 'utf8')
);
const nodeInfo = JSON.parse(
  fs.readFileSync(path.join(DEPLOYMENT_DIR, 'node-info.json'), 'utf8')
);
const compiled = JSON.parse(
  fs.readFileSync(path.join(DEPLOYMENT_DIR, 'compiled.json'), 'utf8')
);
const abi =
  compiled.contracts['contracts/MyChainlinkRequesterDMN.sol:MyChainlinkRequesterDMN'].abi;

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
  const Web3EthAbi = require('web3-eth-abi');
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

  if (!contractAddress) {
    console.error('缺少合约地址：deployment/deployment.json 或 DMN_REQUEST_CONTRACT_ADDRESS');
    process.exit(1);
  }
  if (!ocrAggregator) {
    console.error('缺少 OCR aggregator 地址：deployment/chainlink-deployment.json 或 OCR_AGGREGATOR_ADDRESS');
    process.exit(1);
  }
  if (!writers || writers.length === 0) {
    console.error('缺少 baseline writer 地址：deployment/node-info.json 或 BASELINE_WRITERS');
    process.exit(1);
  }

  console.log('合约地址:', contractAddress);
  console.log('OCR aggregator:', ocrAggregator);
  console.log('baseline writers:', writers.join(', '));

  const tx1 = await sendTx(contractAddress, 'setOcrAggregator', [ocrAggregator], 200000);
  console.log('✅ setOcrAggregator 交易已发送:', tx1);

  for (const writer of writers) {
    const tx2 = await sendTx(contractAddress, 'setBaselineWriter', [writer, true], 200000);
    console.log(`✅ setBaselineWriter(${writer}) 交易已发送:`, tx2);
  }
}

main().catch((err) => {
  console.error('❌ 失败:', err.message);
  process.exit(1);
});
