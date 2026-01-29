const fs = require('fs');
const http = require('http');
const path = require('path');
const axios = require('axios');

const ROOT_DIR = path.resolve(__dirname, '..', '..');
const deployment = JSON.parse(
  fs.readFileSync(path.join(ROOT_DIR, 'deployment', 'deployment.json'), 'utf8')
);

const DMN_URL =
  process.env.DMN_URL || 'http://dmn-node1:8080/api/dmn/evaluate';
const DMN_CACHE_HOSTS = (process.env.DMN_CACHE_HOSTS ||
  'http://localhost:8081,http://localhost:8082,http://localhost:8083,http://localhost:8084')
  .split(',')
  .map((item) => item.trim())
  .filter(Boolean);

function rpcCall(method, params) {
  return new Promise((resolve, reject) => {
    const postData = JSON.stringify({
      jsonrpc: '2.0',
      method,
      params,
      id: 1,
    });

    const options = {
      hostname: 'localhost',
      port: 8545,
      path: '/',
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
    console.log('');

    const compiled = JSON.parse(
      fs.readFileSync(path.join(ROOT_DIR, 'deployment', 'compiled.json'), 'utf8')
    );
    const abi =
      compiled.contracts['contracts/MyChainlinkRequesterDMN.sol:MyChainlinkRequesterDMN']
        .abi;
    const contractAddress = deployment.contractAddress;

    const accounts = await rpcCall('eth_accounts', []);
    const deployer = accounts[0];
    console.log('测试账户:', deployer);

    const Web3EthAbi = require('web3-eth-abi');

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
    const txHash = await rpcCall('eth_sendTransaction', [
      {
        from: deployer,
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
