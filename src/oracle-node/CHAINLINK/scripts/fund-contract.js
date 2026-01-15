const fs = require('fs');
const http = require('http');

const deployment = JSON.parse(fs.readFileSync('deployment/deployment.json', 'utf8'));
const chainlinkDeployment = JSON.parse(fs.readFileSync('deployment/chainlink-deployment.json', 'utf8'));

const contractAddress = deployment.contractAddress;
const linkTokenAddress = chainlinkDeployment.linkToken;

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

async function fundContract() {
    try {
        const accounts = await rpcCall('eth_accounts', []);
        const deployer = accounts[0];

        // 获取 LinkToken ABI
        const compiled = JSON.parse(fs.readFileSync('deployment/compiled.json', 'utf8'));
        const linkAbi = compiled.contracts['contracts/LinkToken-v0.6-fix/LinkToken.sol:LinkToken'].abi;

        // 构造 transfer 函数调用数据
        const Web3EthAbi = require('web3-eth-abi');
        const transferData = Web3EthAbi.encodeFunctionCall({
            name: 'transfer',
            type: 'function',
            inputs: [
                { type: 'address', name: 'to' },
                { type: 'uint256', name: 'value' }
            ]
        }, [contractAddress, '1000000000000000000']); // 1 LINK

        console.log('正在向合约转账 1 LINK...');
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

fundContract();
