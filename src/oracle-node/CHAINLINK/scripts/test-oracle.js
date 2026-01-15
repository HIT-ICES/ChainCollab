const fs = require('fs');
const http = require('http');

const deployment = JSON.parse(fs.readFileSync('deployment/deployment.json', 'utf8'));

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
        console.log('📋 测试 Chainlink Oracle...');
        console.log('合约地址:', deployment.contractAddress);
        console.log('');

        // 读取合约 ABI
        const compiled = JSON.parse(fs.readFileSync('deployment/compiled.json', 'utf8'));
        const abi = compiled.contracts['contracts/MyChainlinkRequester.sol:MyChainlinkRequester'].abi;
        const contractAddress = deployment.contractAddress;

        // 获取账户
        const accounts = await rpcCall('eth_accounts', []);
        const deployer = accounts[0];
        console.log('测试账户:', deployer);

        // 检查合约余额
        const balance = await rpcCall('eth_getBalance', [contractAddress, 'latest']);
        console.log('合约 ETH 余额:', parseInt(balance, 16) / 1e18, 'ETH');

        // 检查 LINK 余额
        const linkAbi = JSON.parse(fs.readFileSync('deployment/chainlink-deployment.json', 'utf8'));
        const linkTokenAddress = JSON.parse(fs.readFileSync('deployment/chainlink-deployment.json', 'utf8')).linkToken;

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

        // 使用本地测试服务器（推荐）
        const testUrl = 'http://172.31.61.180:3000';
        console.log('测试 URL:', testUrl);
        console.log('');

        // 编码 requestOffchainData 函数调用
        const requestData = Web3EthAbi.encodeFunctionCall({
            name: 'requestOffchainData',
            type: 'function',
            inputs: [{ type: 'string', name: 'url' }]
        }, [testUrl]);

        // 发送请求
        console.log('🚀 发起 Oracle 请求...');
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
        console.log('   node scripts/check-result.js');

    } catch (error) {
        console.error('❌ 测试过程中出错:', error.message);
        console.error('详细信息:', error);
    }
}

async function parseRequestIdFromReceipt(receipt) {
    try {
        const compiled = JSON.parse(fs.readFileSync('deployment/compiled.json', 'utf8'));
        const abi = compiled.contracts['contracts/MyChainlinkRequester.sol:MyChainlinkRequester'].abi;

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
