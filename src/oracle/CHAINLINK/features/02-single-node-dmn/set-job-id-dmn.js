const fs = require('fs');
const http = require('http');
const path = require('path');

const ROOT_DIR = path.resolve(__dirname, '..', '..');
const deployment = JSON.parse(fs.readFileSync(path.join(ROOT_DIR, 'deployment', 'deployment.json'), 'utf8'));
const chainlinkDeployment = JSON.parse(fs.readFileSync(path.join(ROOT_DIR, 'deployment', 'chainlink-deployment.json'), 'utf8'));

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

function normalizeJobId(id) {
    let raw = id.toLowerCase().replace(/-/g, '');
    if (raw.startsWith('0x')) {
        raw = raw.slice(2);
    }
    if (!/^[0-9a-f]+$/.test(raw)) {
        throw new Error(`Job ID 不是有效的十六进制字符串: ${id}`);
    }
    if (raw.length > 64) {
        throw new Error(`Job ID 长度不正确: ${id}`);
    }
    return '0x' + raw.padEnd(64, '0');
}

async function main() {
    try {
        const rawJobId = process.argv[2] || chainlinkDeployment.dmnJobId;
        if (!rawJobId) {
            console.error('❌ 未找到 Job ID，请传参或先创建 DMN Job');
            console.log('用法: node features/02-single-node-dmn/set-job-id-dmn.js <jobId>');
            process.exit(1);
        }

        const jobId = normalizeJobId(rawJobId);
        const contractAddress = deployment.contractAddress;

        const accounts = await rpcCall('eth_accounts', []);
        const from = accounts[0];

        const Web3EthAbi = require('web3-eth-abi');
        const data = Web3EthAbi.encodeFunctionCall({
            name: 'setJobId',
            type: 'function',
            inputs: [{ type: 'bytes32', name: '_jobId' }]
        }, [jobId]);

        console.log('准备更新 Job ID:');
        console.log('  合约地址:', contractAddress);
        console.log('  发送账户:', from);
        console.log('  新 Job ID:', jobId);

        const txHash = await rpcCall('eth_sendTransaction', [{
            from: from,
            to: contractAddress,
            data: data,
            gas: '0x' + (300000).toString(16)
        }]);

        console.log('交易哈希:', txHash);
        console.log('等待交易确认...');

        let receipt = null;
        for (let i = 0; i < 30; i++) {
            await new Promise(resolve => setTimeout(resolve, 2000));
            receipt = await rpcCall('eth_getTransactionReceipt', [txHash]);
            if (receipt) break;
        }

        if (!receipt) {
            console.error('❌ 交易确认超时');
            process.exit(1);
        }

        if (receipt.status === '0x0') {
            console.error('❌ 交易失败');
            process.exit(1);
        }

        console.log('✅ Job ID 更新成功');
    } catch (error) {
        console.error('❌ 更新失败:', error.message);
        console.error('详细信息:', error);
        process.exit(1);
    }
}

main();
