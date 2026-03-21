const fs = require('fs');
const http = require('http');
const path = require('path');
const axios = require('axios');

const ROOT_DIR = path.resolve(__dirname, '..', '..');
const deployment = JSON.parse(
  fs.readFileSync(path.join(ROOT_DIR, 'deployment', 'deployment.json'), 'utf8')
);
const chainlinkDeployment = JSON.parse(
  fs.readFileSync(path.join(ROOT_DIR, 'deployment', 'chainlink-deployment.json'), 'utf8')
);

const DMN_URL =
  process.env.DMN_URL || 'http://dmn-node1:8080/api/dmn/evaluate';
const DMN_CACHE_HOSTS = (process.env.DMN_CACHE_HOSTS ||
  'http://localhost:8081,http://localhost:8082,http://localhost:8083,http://localhost:8084')
  .split(',')
  .map((item) => item.trim())
  .filter(Boolean);

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

async function getCode(address) {
  if (!address) return '0x';
  return rpcCall('eth_getCode', [address, 'latest']);
}

function isZeroJobId(id) {
  if (!id) return true;
  const raw = id.toLowerCase().replace(/-/g, '').replace(/^0x/, '');
  return raw === '' || /^0+$/.test(raw);
}

function normalizeAddress(addr) {
  return String(addr || '').trim().toLowerCase();
}

async function getOwner(contractAddress) {
  const Web3EthAbi = require('web3-eth-abi');
  const data = Web3EthAbi.encodeFunctionCall(
    {
      name: 'owner',
      type: 'function',
      inputs: [],
    },
    []
  );
  const result = await rpcCall('eth_call', [{ to: contractAddress, data }, 'latest']);
  const decoded = Web3EthAbi.decodeParameters([{ type: 'address', name: 'owner' }], result);
  return decoded.owner;
}

async function getLinkBalance(linkToken, account) {
  const Web3EthAbi = require('web3-eth-abi');
  const data = Web3EthAbi.encodeFunctionCall(
    {
      name: 'balanceOf',
      type: 'function',
      inputs: [{ type: 'address', name: 'owner' }],
    },
    [account]
  );
  const result = await rpcCall('eth_call', [{ to: linkToken, data }, 'latest']);
  const decoded = Web3EthAbi.decodeParameters([{ type: 'uint256', name: 'balance' }], result);
  return BigInt(decoded.balance);
}

async function pollLatest(host, tries = 30, intervalMs = 2000) {
  const url = `${host}/api/dmn/latest`;
  for (let i = 0; i < tries; i++) {
    try {
      const res = await axios.get(url, { timeout: 5000 });
      if (res.data && res.data.ready) {
        return res.data;
      }
    } catch (_) {
      // ignore and retry
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  return null;
}

async function testOracle() {
  try {
    console.log('📋 测试 DMN OCR 流程（directrequest 缓存）...');
    console.log('合约地址:', deployment.contractAddress);
    console.log('RPC URL:', RPC_URL);
    console.log('');

    const compiled = JSON.parse(
      fs.readFileSync(path.join(ROOT_DIR, 'deployment', 'compiled.json'), 'utf8')
    );
    const abi =
      compiled.contracts['contracts/MyChainlinkRequesterDMN.sol:MyChainlinkRequesterDMN']
        .abi;
    const contractAddress = deployment.contractAddress;
    if (!contractAddress) {
      console.error('❌ 缺少合约地址：deployment/deployment.json');
      return;
    }
    const contractCode = await getCode(contractAddress);
    console.log('contract code:', contractCode === '0x' ? '0x' : '0x...(' + contractCode.length + ')');
    if (!contractCode || contractCode === '0x') {
      console.error('❌ 合约地址无代码，可能部署失败或地址错误:', contractAddress);
      return;
    }
    if (isZeroJobId(chainlinkDeployment?.dmnJobId)) {
      console.error('❌ dmnJobId 为空或未设置，请先创建 Job 并写回合约:');
      console.error('   1) node features/04-dmn-ocr/create-dmn-directrequest-job.js');
      console.error('   2) node features/04-dmn-ocr/set-dmn-job-id.js');
      return;
    }
    console.log('dmnJobId:', chainlinkDeployment?.dmnJobId);
    console.log('oracle:', deployment.oracle);
    const oracleCode = await getCode(deployment.oracle);
    console.log('oracle code:', oracleCode === '0x' ? '0x' : '0x...(' + oracleCode.length + ')');
    if (!oracleCode || oracleCode === '0x') {
      console.error('❌ oracle 地址无代码，可能 operator 未部署或地址不匹配');
      return;
    }
    if (deployment.linkToken) {
      const linkCode = await getCode(deployment.linkToken);
      console.log('link token:', deployment.linkToken);
      console.log('link code:', linkCode === '0x' ? '0x' : '0x...(' + linkCode.length + ')');
      if (!linkCode || linkCode === '0x') {
        console.error('❌ LINK token 地址无代码，可能部署未成功');
        return;
      }
    }

    const accounts = await rpcCall('eth_accounts', []);
    let sender = accounts[0];
    const owner = await getOwner(contractAddress);
    console.log('合约 owner:', owner);
    if (owner && owner.toLowerCase() !== sender.toLowerCase()) {
      const ownerInAccounts = accounts.find((a) => a.toLowerCase() === owner.toLowerCase());
      if (!ownerInAccounts) {
        console.error('❌ 当前默认账户不是 owner，且 owner 不在本地可用账户中');
        console.error('   请解锁/使用 owner 账户发送交易');
        return;
      }
      sender = ownerInAccounts;
    }
    console.log('测试账户:', sender);

    const Web3EthAbi = require('web3-eth-abi');
    try {
      const jobIdData = Web3EthAbi.encodeFunctionCall(
        {
          name: 'getJobId',
          type: 'function',
          inputs: [],
        },
        []
      );
      const jobIdRes = await rpcCall('eth_call', [{ to: contractAddress, data: jobIdData }, 'latest']);
      const jobIdDecoded = Web3EthAbi.decodeParameters([{ type: 'bytes32', name: 'jobId' }], jobIdRes);
      console.log('jobId(onchain):', jobIdDecoded.jobId);
    } catch (err) {
      console.warn('⚠️  读取 jobId 失败（可能未重新编译/部署）:', err.message);
    }
    if (deployment.linkToken) {
      const currentLinkToken = chainlinkDeployment?.linkToken;
      if (
        currentLinkToken &&
        normalizeAddress(currentLinkToken) !== normalizeAddress(deployment.linkToken)
      ) {
        console.error('❌ deployment.json 里的 LINK Token 已过期');
        console.error('   deployment.json:', deployment.linkToken);
        console.error('   chainlink-deployment.json:', currentLinkToken);
        console.error('   请先重新跑 [4] 步骤确保 DMN 合约按当前 Chainlink 地址重部署');
        return;
      }
      const balance = await getLinkBalance(deployment.linkToken, contractAddress);
      if (balance === 0n) {
        console.error('❌ 合约 LINK 余额为 0，request 会失败');
        console.error('   请先运行: node scripts/fund-contract.js');
        return;
      }
      console.log('合约 LINK 余额:', balance.toString());
    }

    const dmnContent = `<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/DMN/20151101/dmn.xsd"
             id="dish-decision"
             name="Dish Decision"
             namespace="http://camunda.org/schema/1.0/dmn">
  <decision id="dish" name="Dish">
    <decisionTable id="decisionTable">
      <input id="input1" label="Temperature">
        <inputExpression id="expr1" typeRef="integer">
          <text>temperature</text>
        </inputExpression>
      </input>
      <input id="input2" label="Day Type">
        <inputExpression id="expr2" typeRef="string">
          <text>dayType</text>
        </inputExpression>
      </input>
      <output id="output1" label="Dish" typeRef="string" name="result"/>

      <rule id="rule1">
        <inputEntry id="entry1">
          <text>&lt; 10</text>
        </inputEntry>
        <inputEntry id="entry2">
          <text>"Weekday"</text>
        </inputEntry>
        <outputEntry id="entry3">
          <text>"Soup"</text>
        </outputEntry>
      </rule>

      <rule id="rule2">
        <inputEntry id="entry4">
          <text>&gt; 20</text>
        </inputEntry>
        <inputEntry id="entry5">
          <text>"Weekday"</text>
        </inputEntry>
        <outputEntry id="entry6">
          <text>"Salad"</text>
        </outputEntry>
      </rule>

      <rule id="rule3">
        <inputEntry id="entry7">
          <text>[11..20]</text>
        </inputEntry>
        <inputEntry id="entry8">
          <text>"Weekday"</text>
        </inputEntry>
        <outputEntry id="entry10">
          <text>"Pasta"</text>
        </outputEntry>
      </rule>

      <rule id="rule4">
        <inputEntry id="entry11">
          <text>&lt; 10</text>
        </inputEntry>
        <inputEntry id="entry12">
          <text>"Weekend"</text>
        </inputEntry>
        <outputEntry id="entry13">
          <text>"Roast"</text>
        </outputEntry>
      </rule>

      <rule id="rule5">
        <inputEntry id="entry14">
          <text>&gt; 20</text>
        </inputEntry>
        <inputEntry id="entry15">
          <text>"Weekend"</text>
        </inputEntry>
        <outputEntry id="entry16">
          <text>"Light Salad"</text>
        </outputEntry>
      </rule>
    </decisionTable>
  </decision>
</definitions>`;

    const decisionId = 'dish';
    const defaultTemp = Number(process.env.DMN_TEMPERATURE || 20);
    const defaultDayType = process.env.DMN_DAY_TYPE || 'Weekday';
    const randomize = process.env.DMN_RANDOM === '1';
    const temp = randomize ? (Date.now() % 30) + 1 : defaultTemp;
    const dayType = randomize ? (temp % 2 === 0 ? 'Weekday' : 'Weekend') : defaultDayType;
    const inputData =
      process.env.DMN_INPUT_DATA ||
      JSON.stringify({ temperature: temp, dayType });

    const expectedDish =
      dayType === 'Weekday'
        ? temp < 10
          ? 'Soup'
          : temp > 20
            ? 'Salad'
            : 'Pasta'
        : temp < 10
          ? 'Roast'
          : temp > 20
            ? 'Light Salad'
            : null;

    console.log('DMN 输入:', { temperature: temp, dayType });
    console.log('预计 DMN 输出:', expectedDish ?? '(无匹配规则)');
    console.log('');

    const requestData = Web3EthAbi.encodeFunctionCall(
      {
        name: 'requestDMNDecision',
        type: 'function',
        inputs: [
          { type: 'string', name: 'url' },
          { type: 'string', name: 'dmnContent' },
          { type: 'string', name: 'decisionId' },
          { type: 'string', name: 'inputData' },
        ],
      },
      [DMN_URL, dmnContent, decisionId, inputData]
    );

    console.log('🚀 发起 DMN Oracle 请求...');
    const sim = await rpcCallRaw('eth_call', [
      {
        from: sender,
        to: contractAddress,
        data: requestData,
      },
      'latest',
    ]);
    if (sim.error) {
      const data = sim.error?.data || '';
      const raw =
        typeof data === 'string'
          ? data
          : data?.data || data?.result || '';
      const reason =
        typeof raw === 'string' ? decodeRevertReason(raw) : null;
      console.error('❌ 预执行失败，交易会回滚');
      console.error('error:', sim.error?.message || sim.error);
      if (raw) {
        console.error('raw:', raw);
      }
      if (reason) {
        console.error('revert reason:', reason);
      }
      return;
    }

    const txHash = await rpcCall('eth_sendTransaction', [
      {
        from: sender,
        to: contractAddress,
        data: requestData,
        gas: '0x' + (5000000).toString(16),
      },
    ]);
    console.log('交易哈希:', txHash);

    console.log('等待交易确认...');
    let receipt = null;
    for (let i = 0; i < 30; i++) {
      await new Promise((resolve) => setTimeout(resolve, 2000));
      receipt = await rpcCall('eth_getTransactionReceipt', [txHash]);
      if (receipt) break;
    }

    if (!receipt) {
      console.error('❌ 交易确认超时');
      return;
    }

    if (receipt.status === '0x0') {
      console.error('❌ 交易失败');
      console.error('receipt:', receipt);
      return;
    }

    console.log('✅ 请求已发送，开始检查各 DMN 缓存节点...');
    for (const host of DMN_CACHE_HOSTS) {
      const data = await pollLatest(host);
      if (data) {
        console.log(`✅ ${host} 缓存已更新:`, data.value);
      } else {
        console.log(`⚠️  ${host} 未检测到缓存更新`);
      }
    }
  } catch (error) {
    console.error('❌ 测试过程中出错:', error.message);
  }
}

testOracle();
