const fs = require('fs');
const http = require('http');
const path = require('path');

const ROOT_DIR = path.resolve(__dirname, '..', '..');
const deployment = JSON.parse(fs.readFileSync(path.join(ROOT_DIR, 'deployment', 'deployment.json'), 'utf8'));

function rpcCall(method, params) {
    return new Promise((resolve, reject) => {
        const postData = JSON.stringify({
            jsonrpc: '2.0',
            method: method,
            params: params,
            id: 1
        });

        const options = {
            hostname: 'localhost',
            port: 8545,
            path: '/',
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(postData)
            }
        };

        const req = http.request(options, (res) => {
            let data = '';
            res.on('data', (chunk) => { data += chunk; });
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

async function testOracle() {
    try {
        console.log('📋 测试 DMN Oracle...');
        console.log('合约地址:', deployment.contractAddress);
        console.log('');

        // 读取合约 ABI
        const compiled = JSON.parse(fs.readFileSync(path.join(ROOT_DIR, 'deployment', 'compiled.json'), 'utf8'));
        const abi = compiled.contracts['contracts/MyChainlinkRequesterDMN.sol:MyChainlinkRequesterDMN'].abi;
        const contractAddress = deployment.contractAddress;

        // 获取账户
        const accounts = await rpcCall('eth_accounts', []);
        const deployer = accounts[0];
        console.log('测试账户:', deployer);

        // 检查合约余额
        const balance = await rpcCall('eth_getBalance', [contractAddress, 'latest']);
        console.log('合约 ETH 余额:', parseInt(balance, 16) / 1e18, 'ETH');

        // 检查 LINK 余额
        const linkAbi = JSON.parse(fs.readFileSync(path.join(ROOT_DIR, 'deployment', 'chainlink-deployment.json'), 'utf8'));
        const linkTokenAddress = JSON.parse(fs.readFileSync(path.join(ROOT_DIR, 'deployment', 'chainlink-deployment.json'), 'utf8')).linkToken;

        const Web3EthAbi = require('web3-eth-abi');
        const balanceData = Web3EthAbi.encodeFunctionCall({
            name: 'balanceOf',
            type: 'function',
            inputs: [{ type: 'address', name: 'account' }]
        }, [contractAddress]);

        const linkBalanceHex = await rpcCall('eth_call', [{
            to: linkTokenAddress,
            data: balanceData
        }, 'latest']);
        const linkBalance = parseInt(linkBalanceHex, 16) / 1e18;
        console.log('合约 LINK 余额:', linkBalance, 'LINK');
        console.log('');

        if (linkBalance < 0.1) {
            console.error('❌ 合约 LINK 余额不足 0.1 LINK，无法发起请求');
            console.log('请先运行: node scripts/fund-contract.js');
            return;
        }

        // 测试数据
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

        const decisionId = "dish";
        const inputData = JSON.stringify({ temperature: 20, dayType: "Weekday" });
        const testUrl = 'http://172.31.61.180:8080/api/dmn/evaluate';

        console.log('测试 DMN 决策...');
        console.log('决策 ID:', decisionId);
        console.log('输入数据:', inputData);
        console.log('');

        // 编码 requestDMNDecision 函数调用
        const requestData = Web3EthAbi.encodeFunctionCall({
            name: 'requestDMNDecision',
            type: 'function',
            inputs: [
                { type: 'string', name: 'url' },
                { type: 'string', name: 'dmnContent' },
                { type: 'string', name: 'decisionId' },
                { type: 'string', name: 'inputData' }
            ]
        }, [testUrl, dmnContent, decisionId, inputData]);

        // 发送请求
        console.log('🚀 发起 DMN Oracle 请求...');
        const txHash = await rpcCall('eth_sendTransaction', [{
            from: deployer,
            to: contractAddress,
            data: requestData,
            gas: '0x' + (5000000).toString(16)
        }]);

        console.log('交易哈希:', txHash);

        // 等待交易确认
        console.log('等待交易确认...');
        let receipt = null;
        for (let i = 0; i < 30; i++) {
            await new Promise(resolve => setTimeout(resolve, 2000));
            receipt = await rpcCall('eth_getTransactionReceipt', [txHash]);
            if (receipt) break;
        }

        if (!receipt) {
            console.error('❌ 交易确认超时');
            return;
        }

        if (receipt.status === '0x0') {
            console.error('❌ 交易失败');
            return;
        }

        console.log('✅ 请求已发送！');

        // 解析事件
        const requestId = await parseRequestIdFromReceipt(receipt);
        if (requestId) {
            console.log('请求 ID:', requestId);
        }

        console.log('');
        console.log('⏳ 等待 Chainlink 节点响应（通常需要 30-60 秒）');
        console.log('');

        // 检查结果
        console.log('1. 检查 Chainlink 节点日志:');
        console.log('   docker logs chainlink-node -f');
        console.log('');
        console.log('2. 访问 Chainlink UI:');
        console.log('   http://localhost:6688');
        console.log('   用户名: admin@chain.link');
        console.log('   密码: change-me-strong');
        console.log('');
        console.log('3. 等待 1-2 分钟后检查结果:');
        console.log('   目前 check-dmn-result.js 文件不存在，您可以通过以下方式检查合约状态:');
        console.log('   node scripts/parse-logs.js', txHash);

    } catch (error) {
        console.error('❌ 测试过程中出错:', error.message);
        console.error('详细信息:', error);
    }
}

async function parseRequestIdFromReceipt(receipt) {
    try {
        const compiled = JSON.parse(fs.readFileSync('deployment/compiled.json', 'utf8'));
        const abi = compiled.contracts['contracts/MyChainlinkRequesterDMN.sol:MyChainlinkRequesterDMN'].abi;

        // 找到 RequestSent 事件的 ABI
        const eventAbi = abi.find(item => item.type === 'event' && item.name === 'RequestSent');

        if (!eventAbi) {
            console.warn('⚠️  无法找到 RequestSent 事件 ABI');
            return null;
        }

        console.warn('⚠️  事件解析需要 web3.js 库');
        console.log('建议使用以下命令查看事件:');
        console.log('node scripts/parse-logs.js', receipt.transactionHash);

        return null;
    } catch (error) {
        console.warn('⚠️  事件解析失败:', error.message);
        return null;
    }
}

testOracle();
