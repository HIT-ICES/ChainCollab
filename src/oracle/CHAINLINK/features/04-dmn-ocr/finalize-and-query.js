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
const compiled = JSON.parse(
  fs.readFileSync(path.join(DEPLOYMENT_DIR, 'compiled.json'), 'utf8')
);
const abi =
  compiled.contracts['contracts/MyChainlinkRequesterDMN.sol:MyChainlinkRequesterDMN'].abi;

const RPC_URL = process.env.RPC_URL || 'http://localhost:8545';
const WAIT_TRIES = Number(process.env.WAIT_TRIES || 30);
const WAIT_INTERVAL_MS = Number(process.env.WAIT_INTERVAL_MS || 2000);

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

function getFunctionAbi(name) {
  return abi.find((item) => item.type === 'function' && item.name === name);
}

function decodeRevertReason(data) {
  if (!data || data === '0x') return null;
  const Web3EthAbi = require('web3-eth-abi');
  if (data.startsWith('0x08c379a0')) {
    try {
      return Web3EthAbi.decodeParameter('string', '0x' + data.slice(10));
    } catch (_) {
      return null;
    }
  }
  if (data.startsWith('0x4e487b71')) {
    try {
      const code = Web3EthAbi.decodeParameter('uint256', '0x' + data.slice(10));
      return `panic code ${code}`;
    } catch (_) {
      return null;
    }
  }
  return null;
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

function rpcCallRaw(method, params) {
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
        try {
          const response = JSON.parse(data);
          resolve(response);
        } catch (err) {
          reject(err);
        }
      });
    });

    req.on('error', reject);
    req.write(postData);
    req.end();
  });
}

async function readCall(contractAddress, fnName, args) {
  const fn = getFunctionAbi(fnName);
  if (!fn) {
    throw new Error(`Missing ABI for ${fnName}`);
  }
  const Web3EthAbi = require('web3-eth-abi');
  const data = Web3EthAbi.encodeFunctionCall(fn, args);
  const result = await rpcCall('eth_call', [{ to: contractAddress, data }, 'latest']);
  return Web3EthAbi.decodeParameters(fn.outputs, result);
}

function parseArgs() {
  const args = process.argv.slice(2);
  const out = {};
  for (let i = 0; i < args.length; i += 1) {
    const key = args[i];
    const next = args[i + 1];
    if (key === '--request-id' && next) {
      out.requestId = next;
      i += 1;
    } else if (key === '--contract' && next) {
      out.contract = next;
      i += 1;
    } else if (key === '--no-finalize') {
      out.noFinalize = true;
    }
  }
  return out;
}

async function main() {
  const args = parseArgs();
  const contractAddress =
    args.contract || process.env.DMN_REQUEST_CONTRACT_ADDRESS || deployment.contractAddress;
  const ocrAddress =
    process.env.OCR_AGGREGATOR_ADDRESS || chainlinkDeployment.ocrContract;
  const requestId = args.requestId || process.env.REQUEST_ID;

  if (!contractAddress) {
    console.error('缺少合约地址：deployment/deployment.json 或 DMN_REQUEST_CONTRACT_ADDRESS');
    process.exit(1);
  }
  if (!requestId) {
    console.error('缺少 requestId：--request-id 或 REQUEST_ID');
    process.exit(1);
  }

  console.log('合约地址:', contractAddress);
  console.log('requestId:', requestId);

  try {
    const baseline = await readCall(contractAddress, 'baselines', [requestId]);
    console.log('baseline.exists:', baseline[3]);
    console.log('baseline.hash:', baseline[0]);
    console.log('baseline.hashLow:', baseline[1]?.toString?.() ?? baseline[1]);
    const match = await readCall(contractAddress, 'isOcrMatch', [requestId]);
    console.log('isOcrMatch:', match[0]);
    if (ocrAddress) {
      const Web3EthAbi = require('web3-eth-abi');
      const data = Web3EthAbi.encodeFunctionCall(
        {
          name: 'latestAnswer',
          type: 'function',
          inputs: [],
          outputs: [{ type: 'int256', name: '' }],
        },
        []
      );
      const res = await rpcCall('eth_call', [{ to: ocrAddress, data }, 'latest']);
      const decoded = Web3EthAbi.decodeParameters([{ type: 'int256', name: 'answer' }], res);
      console.log('OCR latestAnswer:', decoded.answer.toString());
    } else {
      console.warn('⚠️  缺少 OCR 合约地址，无法读取 latestAnswer');
    }
  } catch (err) {
    console.warn('⚠️  读取 baseline/isOcrMatch 失败:', err.message);
  }

  if (!args.noFinalize) {
    const fn = getFunctionAbi('finalize');
    const Web3EthAbi = require('web3-eth-abi');
    const data = Web3EthAbi.encodeFunctionCall(fn, [requestId]);
    const sim = await rpcCallRaw('eth_call', [{ to: contractAddress, data }, 'latest']);
    if (sim.error) {
      const raw =
        typeof sim.error?.data === 'string'
          ? sim.error.data
          : sim.error?.data?.data || sim.error?.data?.result || '';
      const reason = typeof raw === 'string' ? decodeRevertReason(raw) : null;
      console.error('❌ 预执行失败，finalize 会回滚');
      console.error('error:', sim.error?.message || sim.error);
      if (raw) {
        console.error('raw:', raw);
      }
      if (reason) {
        console.error('revert reason:', reason);
      }
      process.exit(1);
    }

    const tx = await sendTx(contractAddress, 'finalize', [requestId], 200000);
    console.log('✅ finalize 交易已发送:', tx);
    let receipt = null;
    for (let i = 0; i < WAIT_TRIES; i += 1) {
      await new Promise((resolve) => setTimeout(resolve, WAIT_INTERVAL_MS));
      receipt = await rpcCall('eth_getTransactionReceipt', [tx]);
      if (receipt) break;
    }
    if (!receipt) {
      console.error('❌ 等待交易确认超时');
      process.exit(1);
    }
    if (receipt.status === '0x0') {
      console.error('❌ finalize 交易失败');
      console.error('receipt:', receipt);
      process.exit(1);
    }
  }

  const finalized = await readCall(contractAddress, 'finalized', [requestId]);
  console.log('finalized:', finalized[0]);

  if (finalized[0]) {
    const raw = await readCall(contractAddress, 'getFinalizedRaw', [requestId]);
    console.log('raw:', raw[0]);
  } else {
    console.log('结果尚未 finalize，无法读取 raw');
  }
}

main().catch((err) => {
  console.error('❌ 失败:', err.message);
  process.exit(1);
});
