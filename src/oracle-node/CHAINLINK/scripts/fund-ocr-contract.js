const fs = require('fs');
const http = require('http');

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
            }
        }, (res) => {
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

async function fundOcrContract() {
    try {
        let amount = 1;
        const amountIndex = process.argv.indexOf('--amount');
        if (amountIndex !== -1 && process.argv[amountIndex + 1]) {
            amount = Number(process.argv[amountIndex + 1]);
        }

        if (!Number.isFinite(amount) || amount <= 0) {
            throw new Error('amount 必须是大于 0 的数字');
        }

        const ocrDeployment = JSON.parse(fs.readFileSync('deployment/ocr-deployment.json', 'utf8'));
        const chainlinkDeployment = JSON.parse(fs.readFileSync('deployment/chainlink-deployment.json', 'utf8'));

        const ocrContractAddress = ocrDeployment.contractAddress;
        const linkTokenAddress = chainlinkDeployment.linkToken;

        if (!ocrContractAddress) {
            throw new Error('ocr-deployment.json 缺少 contractAddress');
        }

        if (!linkTokenAddress) {
            throw new Error('chainlink-deployment.json 缺少 linkToken');
        }

        const accounts = await rpcCall('eth_accounts', []);
        const deployer = accounts[0];

        const Web3EthAbi = require('web3-eth-abi');
        const amountWei = (BigInt(Math.floor(amount * 1e6)) * BigInt(1e12)).toString();
        const transferData = Web3EthAbi.encodeFunctionCall({
            name: 'transfer',
            type: 'function',
            inputs: [
                { type: 'address', name: 'to' },
                { type: 'uint256', name: 'value' }
            ]
        }, [ocrContractAddress, amountWei]);

        console.log(`正在向 OCR 合约转账 ${amount} LINK...`);
        const txHash = await rpcCall('eth_sendTransaction', [{
            from: deployer,
            to: linkTokenAddress,
            data: transferData,
            gas: '0x' + (1000000).toString(16)
        }]);

        console.log('交易哈希:', txHash);
        console.log('等待交易确认...');

        let receipt = null;
        for (let i = 0; i < 30; i++) {
            await new Promise(resolve => setTimeout(resolve, 2000));
            receipt = await rpcCall('eth_getTransactionReceipt', [txHash]);
            if (receipt) break;
        }

        if (receipt && receipt.status === '0x1') {
            console.log('✅ LINK Token 转账成功！');
        } else {
            console.error('❌ 转账失败');
        }

    } catch (error) {
        console.error('❌ 错误:', error.message);
    }
}

fundOcrContract();
