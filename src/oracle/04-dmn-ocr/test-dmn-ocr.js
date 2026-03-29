const fs = require('fs');
const http = require('http');
const path = require('path');
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

const ROOT_DIR = resolveChainlinkRoot();
const DEPLOYMENT_DIR = path.resolve(
  process.env.CHAINCOLLAB_RUNTIME_DEPLOYMENT_DIR || path.join(ROOT_DIR, 'deployment')
);
function requireFromChainlink(modName) {
  try {
    return require(modName);
  } catch (_) {
    return require(path.join(ROOT_DIR, 'node_modules', modName));
  }
}

const axios = requireFromChainlink('axios');
const deployment = JSON.parse(
  fs.readFileSync(path.join(DEPLOYMENT_DIR, 'deployment.json'), 'utf8')
);
const chainlinkDeployment = JSON.parse(
  fs.readFileSync(path.join(DEPLOYMENT_DIR, 'chainlink-deployment.json'), 'utf8')
);

const DMN_URL =
  process.env.DMN_URL || 'http://dmn-node1:8080/api/dmn/evaluate';
const DMN_CACHE_HOSTS = (process.env.DMN_CACHE_HOSTS ||
  'http://localhost:8081,http://localhost:8082,http://localhost:8083,http://localhost:8084')
  .split(',')
  .map((item) => item.trim())
  .filter(Boolean);
const DMN_MODE = process.env.DMN_MODE === 'lite' ? 'lite' : 'full';

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
  const Web3EthAbi = requireFromChainlink('web3-eth-abi');
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

async function getOwner(contractAddress) {
  const Web3EthAbi = requireFromChainlink('web3-eth-abi');
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
  const Web3EthAbi = requireFromChainlink('web3-eth-abi');
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

function decodeUint(value) {
  if (typeof value === 'bigint') return Number(value);
  if (typeof value === 'number') return value;
  if (typeof value === 'string') {
    if (value.startsWith('0x')) return Number(BigInt(value));
    return Number(value);
  }
  return 0;
}

function readJsonIfExists(filePath) {
  if (!fs.existsSync(filePath)) return null;
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function findBaselineWriters(nodeInfo) {
  if (!Array.isArray(nodeInfo)) return [];
  return nodeInfo
    .filter((node) => node.name && (node.name.startsWith('node') || node.name === 'bootstrap'))
    .map((node) => node.ethAddress)
    .filter(Boolean);
}

function resolveRequiredOrganizations() {
  const explicit = process.env.DMN_REQUIRED_ORGS;
  if (explicit) {
    const parsed = Number(explicit);
    if (Number.isInteger(parsed) && parsed > 0) {
      return parsed;
    }
    throw new Error(`DMN_REQUIRED_ORGS 非法: ${explicit}`);
  }

  const nodeInfo = readJsonIfExists(path.join(DEPLOYMENT_DIR, 'node-info.json'));
  const writers = findBaselineWriters(nodeInfo);
  if (writers.length > 0) {
    return writers.length;
  }
  return Math.max(1, DMN_CACHE_HOSTS.length);
}

function extractRequestIdFromReceipt(receipt, contractAddress, abi) {
  const Web3EthAbi = requireFromChainlink('web3-eth-abi');
  const sentEvent = abi.find((item) => item.type === 'event' && item.name === 'RequestSent');
  const pendingEvent = abi.find((item) => item.type === 'event' && item.name === 'RequestPending');
  const signatures = [sentEvent, pendingEvent]
    .filter(Boolean)
    .map((item) => Web3EthAbi.encodeEventSignature(item));

  for (const log of receipt.logs || []) {
    if (!log.address || log.address.toLowerCase() !== contractAddress.toLowerCase()) {
      continue;
    }
    if (!log.topics || log.topics.length < 2) {
      continue;
    }
    if (!signatures.includes(log.topics[0])) {
      continue;
    }
    return log.topics[1];
  }
  return null;
}

async function pollConsensus(contractAddress, abi, requestId, tries = 20, intervalMs = 2000) {
  const Web3EthAbi = requireFromChainlink('web3-eth-abi');
  const getRequestStatusAbi = abi.find((item) => item.type === 'function' && item.name === 'getRequestStatus');
  const getConsensusStatusAbi = abi.find((item) => item.type === 'function' && item.name === 'getConsensusStatus');
  if (!getRequestStatusAbi || !requestId) {
    return { ok: true, supported: false };
  }

  for (let i = 0; i < tries; i++) {
    let requestStatus;
    let consensusStatus = null;
    try {
      const requestStatusData = Web3EthAbi.encodeFunctionCall(getRequestStatusAbi, [requestId]);
      const requestStatusResult = await rpcCall('eth_call', [{ to: contractAddress, data: requestStatusData }, 'latest']);
      requestStatus = Web3EthAbi.decodeParameters(getRequestStatusAbi.outputs, requestStatusResult);
      if (getConsensusStatusAbi) {
        const consensusStatusData = Web3EthAbi.encodeFunctionCall(getConsensusStatusAbi, [requestId]);
        const consensusStatusResult = await rpcCall('eth_call', [{ to: contractAddress, data: consensusStatusData }, 'latest']);
        consensusStatus = Web3EthAbi.decodeParameters(getConsensusStatusAbi.outputs, consensusStatusResult);
      }
    } catch (error) {
      return { ok: false, error: error.message };
    }

    const state = decodeUint(requestStatus.state);
    const fulfilled = state === 2;
    const quorum = consensusStatus ? decodeUint(consensusStatus.quorum) : null;
    const decidedVotes = consensusStatus ? decodeUint(consensusStatus.decidedVotes) : null;

    if (consensusStatus) {
      console.log(
        `链上共识状态: state=${state} quorum=${quorum} decidedVotes=${decidedVotes} fulfilled=${consensusStatus.fulfilled}`
      );
    } else {
      console.log(`链上请求状态: state=${state} fulfilledAt=${requestStatus.fulfilledAt}`);
    }

    if (fulfilled) {
      if (consensusStatus && decidedVotes < quorum) {
        return {
          ok: false,
          error: `请求已 Fulfilled，但票数不足多数: ${decidedVotes}/${quorum}`,
        };
      }
      return {
        ok: true,
        supported: true,
        state,
        quorum,
        decidedVotes,
        fulfilled,
      };
    }

    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }

  return {
    ok: false,
    supported: true,
    error: '等待链上多数共识超时，请求仍未 Fulfilled',
  };
}

async function testOracle() {
  try {
    console.log('📋 测试 DMN OCR 流程（directrequest 缓存）...');
    console.log('合约地址:', deployment.contractAddress);
    console.log('RPC URL:', RPC_URL);
    console.log('');

    const compiled = JSON.parse(
      fs.readFileSync(path.join(DEPLOYMENT_DIR, 'compiled.json'), 'utf8')
    );
    const contractKey =
      DMN_MODE === 'lite'
        ? 'contracts/MyChainlinkRequesterDMN_Lite.sol:MyChainlinkRequesterDMN_Lite'
        : 'contracts/MyChainlinkRequesterDMN.sol:MyChainlinkRequesterDMN';
    const contractEntry = compiled.contracts?.[contractKey];
    if (!contractEntry?.abi) {
      console.error(`❌ compiled.json 缺少合约 ABI: ${contractKey}`);
      return false;
    }
    const abi = contractEntry.abi;
    const contractAddress = deployment.contractAddress;
    if (!contractAddress) {
      console.error('❌ 缺少合约地址：deployment/deployment.json');
      return false;
    }
    const contractCode = await getCode(contractAddress);
    console.log('contract code:', contractCode === '0x' ? '0x' : '0x...(' + contractCode.length + ')');
    if (!contractCode || contractCode === '0x') {
      console.error('❌ 合约地址无代码，可能部署失败或地址错误:', contractAddress);
      return false;
    }
    if (isZeroJobId(chainlinkDeployment?.dmnJobId)) {
      console.error('❌ dmnJobId 为空或未设置，请先创建 Job 并写回合约:');
      console.error('   1) node features/04-dmn-ocr/create-dmn-directrequest-job.js');
      console.error('   2) node features/04-dmn-ocr/set-dmn-job-id.js');
      return false;
    }
    console.log('dmnJobId:', chainlinkDeployment?.dmnJobId);
    console.log('oracle:', deployment.oracle);
    const oracleCode = await getCode(deployment.oracle);
    console.log('oracle code:', oracleCode === '0x' ? '0x' : '0x...(' + oracleCode.length + ')');
    if (!oracleCode || oracleCode === '0x') {
      console.error('❌ oracle 地址无代码，可能 operator 未部署或地址不匹配');
      return false;
    }
    if (deployment.linkToken) {
      const linkCode = await getCode(deployment.linkToken);
      console.log('link token:', deployment.linkToken);
      console.log('link code:', linkCode === '0x' ? '0x' : '0x...(' + linkCode.length + ')');
      if (!linkCode || linkCode === '0x') {
        console.error('❌ LINK token 地址无代码，可能部署未成功');
        return false;
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
        return false;
      }
      sender = ownerInAccounts;
    }
    console.log('测试账户:', sender);

    const Web3EthAbi = requireFromChainlink('web3-eth-abi');
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
      const balance = await getLinkBalance(deployment.linkToken, contractAddress);
      if (balance === 0n) {
        console.error('❌ 合约 LINK 余额为 0，request 会失败');
        console.error('   请先运行: node scripts/fund-contract.js');
        return false;
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

    const requestInputs = [
      { type: 'string', name: 'url' },
      { type: 'string', name: 'dmnContent' },
      { type: 'string', name: 'decisionId' },
      { type: 'string', name: 'inputData' },
    ];
    const requestArgs = [DMN_URL, dmnContent, decisionId, inputData];

    if (DMN_MODE === 'lite') {
      const requiredOrganizations = resolveRequiredOrganizations();
      console.log('要求参与组织数:', requiredOrganizations);
      console.log('多数阈值:', Math.floor(requiredOrganizations / 2) + 1);
      requestInputs.push({ type: 'uint256', name: 'requiredOrganizations' });
      requestArgs.push(requiredOrganizations);
    }

    const requestData = Web3EthAbi.encodeFunctionCall(
      {
        name: 'requestDMNDecision',
        type: 'function',
        inputs: requestInputs,
      },
      requestArgs
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
      return false;
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
      return false;
    }

    if (receipt.status === '0x0') {
      console.error('❌ 交易失败');
      console.error('receipt:', receipt);
      return false;
    }

    const requestId = extractRequestIdFromReceipt(receipt, contractAddress, abi);
    if (requestId) {
      console.log('requestId:', requestId);
    } else {
      console.warn('⚠️  未能从 receipt 提取 requestId，将只做缓存检查');
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

    const consensus = await pollConsensus(contractAddress, abi, requestId);
    if (!consensus.ok) {
      console.error('❌ 链上多数共识检查失败:', consensus.error);
      return false;
    }
    if (consensus.supported) {
      console.log('✅ 链上请求已达到多数共识并 Fulfilled');
    }
    return true;
  } catch (error) {
    console.error('❌ 测试过程中出错:', error.message);
    return false;
  }
}

testOracle().then((ok) => {
  if (!ok) {
    process.exit(1);
  }
});
