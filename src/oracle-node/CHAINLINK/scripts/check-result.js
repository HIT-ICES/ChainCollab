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

async function checkResult() {
    try {
        const compiled = JSON.parse(fs.readFileSync('deployment/compiled.json', 'utf8'));
        const abi = compiled.contracts['contracts/MyChainlinkRequester.sol:MyChainlinkRequester'].abi;
        const contractAddress = deployment.contractAddress;

        // 编码 result() 函数调用
        const Web3EthAbi = require('web3-eth-abi');
        const resultData = Web3EthAbi.encodeFunctionCall({
            name: 'result',
            type: 'function',
            inputs: [],
            outputs: [{ type: 'uint256' }]
        }, []);

        const resultHex = await rpcCall('eth_call', [{
            to: contractAddress,
            data: resultData
        }, 'latest']);

        const result = parseInt(resultHex, 16);
        console.log('📊 当前合约存储的结果:');
        console.log('   Value:', result);
        console.log('');

        if (result === 0) {
            console.log('⚠️  结果为 0，可能请求尚未完成');
            console.log('   请等待几分钟后再次检查');
            console.log('');
            console.log('检查 Chainlink 节点日志:');
            console.log('   docker logs chainlink-node --tail 50');
        } else {
            console.log('✅ Oracle 响应成功！');
            console.log('结果:', result);
            console.log('');
            console.log('🎉 测试成功！Chainlink Oracle 工作正常');
        }

        return result;

    } catch (error) {
        console.error('❌ 检查结果失败:', error.message);
    }
}

checkResult();
