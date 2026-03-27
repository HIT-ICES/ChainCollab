const fs = require('fs');
const http = require('http');
const path = require('path');

const ROOT_DIR = path.resolve(__dirname, '..', '..');

function rpcCall(method, params) {
    return new Promise((resolve, reject) => {
        const postData = JSON.stringify({
            jsonrpc: '2.0',
            method: method,
            params: params,
            id: 1
        });

        const req = http.request({
            hostname: 'localhost',
            port: 8545,
            path: '/',
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(postData)
            },
            timeout: 5000
        }, (res) => {
            let data = '';
            res.on('data', (chunk) => { data += chunk; });
            res.on('end', () => {
                try {
                    const response = JSON.parse(data);
                    if (response.error) {
                        reject(new Error(response.error.message));
                    } else {
                        resolve(response.result);
                    }
                } catch (error) {
                    reject(new Error(`RPC 响应解析失败: ${error.message}`));
                }
            });
        });

        req.on('error', reject);
        req.on('timeout', () => reject(new Error('RPC 请求超时')));
        req.write(postData);
        req.end();
    });
}

async function main() {
    try {
        const ocrDeployment = JSON.parse(fs.readFileSync(path.join(ROOT_DIR, 'deployment', 'ocr-deployment.json'), 'utf8'));
        const ocrAddress = ocrDeployment.contractAddress;

        const Web3EthAbi = require('web3-eth-abi');
        const data = Web3EthAbi.encodeFunctionCall({
            name: 'getLinkToken',
            type: 'function',
            inputs: []
        }, []);

        const result = await rpcCall('eth_call', [{
            to: ocrAddress,
            data: data
        }, 'latest']);

        if (!result || result === '0x') {
            console.error('❌ 未返回 linkToken 地址');
            process.exit(1);
        }

        const linkToken = '0x' + result.slice(26);
        console.log('OCR 合约地址:', ocrAddress);
        console.log('OCR linkToken 地址:', linkToken);

    } catch (error) {
        console.error('❌ 查询失败:', error.message);
        process.exit(1);
    }
}

main();
