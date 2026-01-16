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

async function parseLogs(txHash) {
    try {
        const receipt = await rpcCall('eth_getTransactionReceipt', [txHash]);

        if (!receipt) {
            console.error('❌ 无法获取交易收据');
            return;
        }

        console.log('📋 交易收据:');
        console.log('');
        console.log('   交易哈希:', receipt.transactionHash);
        console.log('   区块号:', parseInt(receipt.blockNumber, 16));
        console.log('   状态:', receipt.status === '0x1' ? '成功' : '失败');
        console.log('');

        if (receipt.logs && receipt.logs.length > 0) {
            console.log('📄 交易日志:');
            console.log('');
            receipt.logs.forEach((log, index) => {
                console.log(`   日志 ${index + 1}:`);
                console.log('      地址:', log.address);
                console.log('      数据:', log.data);
                console.log('      主题:', log.topics);
                console.log('');
            });
        } else {
            console.log('⚠️  没有找到交易日志');
        }

        // 尝试解析 RequestSent 事件
        const compiled = JSON.parse(fs.readFileSync('deployment/compiled.json', 'utf8'));
        const abi = compiled.contracts['contracts/MyChainlinkRequester.sol:MyChainlinkRequester'].abi;

        const eventAbi = abi.find(item => item.type === 'event' && item.name === 'RequestSent');

        if (eventAbi) {
            console.log('🔍 解析 RequestSent 事件:');
            console.log('');
            console.log('事件 ABI:');
            console.log(JSON.stringify(eventAbi, null, 2));
            console.log('');

            // 由于解析事件需要 web3.js 库，这里提供安装提示
            console.log('💡 要解析事件数据，请安装 web3.js 库:');
            console.log('   npm install web3');
            console.log('');
            console.log('然后可以使用以下代码解析事件:');
            console.log('');
            console.log(`const Web3 = require('web3');`);
            console.log(`const web3 = new Web3('http://localhost:8545');`);
            console.log(`const event = new web3.eth.Contract([${JSON.stringify(eventAbi)}], '${deployment.contractAddress}');`);
            console.log(`const decoded = event.decodeLog([${JSON.stringify(eventAbi.inputs)}], receipt.logs[0].data, receipt.logs[0].topics.slice(1));`);
            console.log(`console.log(decoded);`);
        }

    } catch (error) {
        console.error('❌ 解析日志失败:', error.message);
        console.error('详细信息:', error);
    }
}

// 检查是否提供了交易哈希参数
if (process.argv.length < 3) {
    console.error('❌ 请提供交易哈希');
    console.log('使用方法: node scripts/parse-logs.js <交易哈希>');
    process.exit(1);
}

// 解析日志
parseLogs(process.argv[2]);
