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

async function checkLinkBalance() {
    try {
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

        return linkBalance >= 0.1; // 至少需要 0.1 LINK 来发送请求

    } catch (error) {
        console.error('❌ 检查 LINK 余额失败:', error.message);
        return false;
    }
}

// 如果直接运行这个脚本，输出结果
if (require.main === module) {
    checkLinkBalance().then(hasEnough => {
        process.exit(hasEnough ? 0 : 1);
    });
}

module.exports = checkLinkBalance;
