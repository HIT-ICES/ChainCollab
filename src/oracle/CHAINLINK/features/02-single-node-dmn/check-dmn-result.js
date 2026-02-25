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

async function checkResult() {
    try {
        const compiled = JSON.parse(fs.readFileSync(path.join(ROOT_DIR, 'deployment', 'compiled.json'), 'utf8'));
        const abi = compiled.contracts['contracts/MyChainlinkRequesterDMN.sol:MyChainlinkRequesterDMN'].abi;
        const contractAddress = deployment.contractAddress;

        // 编码 getDMNResult() 函数调用
        const Web3EthAbi = require('web3-eth-abi');
        const resultData = Web3EthAbi.encodeFunctionCall({
            name: 'getDMNResult',
            type: 'function',
            inputs: [],
            outputs: [{ type: 'bytes' }]
        }, []);

        const resultHex = await rpcCall('eth_call', [{
            to: contractAddress,
            data: resultData
        }, 'latest']);

        // 解析响应 - bytes 返回值格式为 offset + length + data
        const offset = parseInt(resultHex.slice(2, 66), 16) * 2;
        const length = parseInt(resultHex.slice(2 + offset, 2 + offset + 64), 16);
        const dataHex = resultHex.slice(2 + offset + 64, 2 + offset + 64 + length * 2);
        const result = Buffer.from(dataHex, 'hex').toString('utf8');

        console.log('📊 当前合约存储的 DMN 决策结果:');
        console.log('');

        if (!result || result.length === 0 || result === '0x') {
            console.log('⚠️  结果为空，可能请求尚未完成');
            console.log('   请等待几分钟后再次检查');
            console.log('');
            console.log('检查 Chainlink 节点日志:');
            console.log('   docker logs chainlink-node --tail 50');
        } else {
            console.log('✅ DMN Oracle 响应成功！');
            console.log('');
            console.log('响应内容:');
            try {
                const parsedResult = JSON.parse(result);
                console.log('   决策 ID:', parsedResult.decisionId);
                console.log('   输入数据:', parsedResult.input);
                console.log('   输出结果:', parsedResult.output);
            } catch (parseError) {
                console.log('   原始数据:', result);
            }
            console.log('');
            console.log('🎉 测试成功！Chainlink Oracle 工作正常');
        }

    } catch (error) {
        console.error('❌ 检查结果失败:', error.message);
        console.error('详细信息:', error);
    }
}

checkResult();
