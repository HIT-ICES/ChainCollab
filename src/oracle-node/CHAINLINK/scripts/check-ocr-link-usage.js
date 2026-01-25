const fs = require('fs');
const http = require('http');
const Web3EthAbi = require('web3-eth-abi');

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
        const ocrDeployment = JSON.parse(fs.readFileSync('deployment/ocr-deployment.json', 'utf8'));
        const ocrAddress = ocrDeployment.contractAddress;

        const getLinkTokenData = Web3EthAbi.encodeFunctionCall({
            name: 'getLinkToken',
            type: 'function',
            inputs: []
        }, []);

        const linkTokenRaw = await rpcCall('eth_call', [{
            to: ocrAddress,
            data: getLinkTokenData
        }, 'latest']);

        const linkToken = '0x' + linkTokenRaw.slice(26);

        const balanceOfData = Web3EthAbi.encodeFunctionCall({
            name: 'balanceOf',
            type: 'function',
            inputs: [{ type: 'address', name: 'account' }]
        }, [ocrAddress]);

        const balanceHex = await rpcCall('eth_call', [{
            to: linkToken,
            data: balanceOfData
        }, 'latest']);

        const linkAvailableData = Web3EthAbi.encodeFunctionCall({
            name: 'linkAvailableForPayment',
            type: 'function',
            inputs: []
        }, []);

        const availableHex = await rpcCall('eth_call', [{
            to: ocrAddress,
            data: linkAvailableData
        }, 'latest']);

        const balance = parseInt(balanceHex, 16) / 1e18;

        const raw = BigInt(availableHex);
        const signBit = 1n << 255n;
        const available = (raw & signBit) ? -(~raw + 1n & ((1n << 256n) - 1n)) : raw;
        const availableLink = Number(available) / 1e18;

        const latestBlockHex = await rpcCall('eth_blockNumber', []);
        const latestBlock = parseInt(latestBlockHex, 16);
        const fromBlock = Math.max(0, latestBlock - 2000);

        const oraclePaidEvent = {
            anonymous: false,
            inputs: [
                { indexed: true, name: 'transmitter', type: 'address' },
                { indexed: true, name: 'payee', type: 'address' },
                { indexed: false, name: 'amount', type: 'uint256' },
                { indexed: false, name: 'linkToken', type: 'address' }
            ],
            name: 'OraclePaid',
            type: 'event'
        };

        const eventSig = Web3EthAbi.encodeEventSignature(oraclePaidEvent);

        const logs = await rpcCall('eth_getLogs', [{
            address: ocrAddress,
            fromBlock: '0x' + fromBlock.toString(16),
            toBlock: '0x' + latestBlock.toString(16),
            topics: [eventSig]
        }]);

        console.log('=== OCR LINK 使用情况 ===');
        console.log('OCR 合约地址:', ocrAddress);
        console.log('LinkToken 地址:', linkToken);
        console.log('LINK 余额:', balance, 'LINK');
        console.log('linkAvailableForPayment:', availableLink, 'LINK');
        console.log(`OraclePaid 事件数量(最近 2000 blocks): ${logs.length}`);

        if (logs.length > 0) {
            const last = logs[logs.length - 1];
            const decoded = Web3EthAbi.decodeLog(
                oraclePaidEvent.inputs,
                last.data,
                last.topics.slice(1)
            );
            console.log('最近一次 OraclePaid:');
            console.log('  transmitter:', decoded.transmitter);
            console.log('  payee:', decoded.payee);
            console.log('  amount:', parseInt(decoded.amount, 10) / 1e18, 'LINK');
            console.log('  linkToken:', decoded.linkToken);
        }

    } catch (error) {
        console.error('❌ 查询失败:', error.message);
        process.exit(1);
    }
}

main();
