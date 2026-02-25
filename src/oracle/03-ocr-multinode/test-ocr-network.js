const fs = require('fs');
const http = require('http');
const path = require('path');

const ROOT_DIR = path.resolve(__dirname, '..', '..');

// RPC 调用函数
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
                if (response.error) {
                    reject(new Error(response.error.message));
                } else {
                    resolve(response.result);
                }
            });
        });

        req.on('error', reject);
        req.write(postData);
        req.end();
    });
}

// 读取 OCR 合约部署信息
function getOCRDeployment() {
    const ocrDeploymentFile = path.join(ROOT_DIR, 'deployment', 'ocr-deployment.json');
    if (!fs.existsSync(ocrDeploymentFile)) {
        console.error('❌ 找不到 ocr-deployment.json，请先运行 deploy-ocr-contract.js');
        process.exit(1);
    }
    return JSON.parse(fs.readFileSync(ocrDeploymentFile, 'utf8'));
}

// 读取 OCR 合约 ABI
function getOCRContractABI() {
    const deploymentDir = path.join(ROOT_DIR, 'deployment');
    const compiledFile = path.join(deploymentDir, 'compiled.json');

    if (!fs.existsSync(compiledFile)) {
        console.error('❌ 合约未编译，请先运行 compile.sh');
        process.exit(1);
    }

    const compiled = JSON.parse(fs.readFileSync(compiledFile, 'utf8'));
    const contractKey = 'contracts/ocr/OffchainAggregator.sol:OffchainAggregator';
    const contractData = compiled.contracts[contractKey];

    if (!contractData) {
        console.error('❌ 找不到合约:', contractKey);
        process.exit(1);
    }

    return contractData.abi;
}

// 调用合约方法
async function callContractMethod(contractAddress, abi, methodName, params) {
    const method = abi.find(m => m.type === 'function' && m.name === methodName);
    if (!method) {
        throw new Error(`Method ${methodName} not found`);
    }

    const Web3EthAbi = require('web3-eth-abi');
    const encodedData = Web3EthAbi.encodeFunctionCall(method, params);

    return rpcCall('eth_call', [
        {
            to: contractAddress,
            data: encodedData
        },
        'latest'
    ]);
}

// 解码合约返回值
function decodeReturnValue(abi, methodName, encodedData) {
    const method = abi.find(m => m.type === 'function' && m.name === methodName);
    if (!method) {
        throw new Error(`Method ${methodName} not found`);
    }

    const Web3EthAbi = require('web3-eth-abi');
    return Web3EthAbi.decodeParameter(method.outputs[0], encodedData.slice(2));
}

async function testOCRNetwork() {
    try {
        const ocrDeployment = getOCRDeployment();
        const contractABI = getOCRContractABI();
        const contractAddress = ocrDeployment.contractAddress;

        console.log('=== 测试 OCR 网络 ===');
        console.log('合约地址:', contractAddress);

        // 检查合约是否存在
        console.log('\n1. 检查合约是否部署');
        try {
            const code = await rpcCall('eth_getCode', [contractAddress, 'latest']);
            if (code === '0x') {
                console.error('❌ 合约不存在');
                return false;
            } else {
                console.log('✅ 合约已部署');
            }
        } catch (error) {
            console.error('❌ 合约检查失败:', error.message);
            return false;
        }

        // 测试 latestConfigDetails 方法
        console.log('\n2. 测试 latestConfigDetails 方法');
        try {
            const result = await callContractMethod(contractAddress, contractABI, 'latestConfigDetails', []);
            const Web3EthAbi = require('web3-eth-abi');
            const decoded = Web3EthAbi.decodeParameters(
                [
                    { type: 'uint32', name: 'configCount' },
                    { type: 'uint32', name: 'blockNumber' },
                    { type: 'bytes16', name: 'configDigest' }
                ],
                result.slice(2)
            );
            const output = {
                configCount: decoded.configCount.toString(),
                blockNumber: decoded.blockNumber.toString(),
                configDigest: decoded.configDigest
            };
            console.log('返回值:', JSON.stringify(output, null, 2));
            console.log('✅ 方法调用成功');
        } catch (error) {
            console.error('❌ 调用失败:', error.message);
            return false;
        }

        // 测试 latestAnswer 方法
        console.log('\n3. 测试 latestAnswer 方法');
        try {
            const result = await callContractMethod(contractAddress, contractABI, 'latestAnswer', []);
            const answer = decodeReturnValue(contractABI, 'latestAnswer', result);
            console.log(`返回值: ${answer}`);
            console.log('✅ 方法调用成功');
        } catch (error) {
            console.error('❌ 调用失败:', error.message);
            return false;
        }

        // 测试 latestRoundData 方法
        console.log('\n4. 测试 latestRoundData 方法');
        try {
            const result = await callContractMethod(contractAddress, contractABI, 'latestRoundData', []);
            const Web3EthAbi = require('web3-eth-abi');
            const decoded = Web3EthAbi.decodeParameters(
                [
                    { type: 'uint80', name: 'roundId' },
                    { type: 'int256', name: 'answer' },
                    { type: 'uint256', name: 'startedAt' },
                    { type: 'uint256', name: 'updatedAt' },
                    { type: 'uint80', name: 'answeredInRound' }
                ],
                result.slice(2)
            );
            const output = {
                roundId: decoded.roundId.toString(),
                answer: decoded.answer.toString(),
                startedAt: decoded.startedAt.toString(),
                updatedAt: decoded.updatedAt.toString(),
                answeredInRound: decoded.answeredInRound.toString()
            };
            console.log('返回值:', JSON.stringify(output, null, 2));
            console.log('✅ 方法调用成功');

            // 检查价格是否已更新
            if (decoded.roundId === '0' || decoded.answer === '0') {
                console.log('⚠️  注意：价格尚未更新');
            } else {
                console.log('✅ 价格已更新');
            }
        } catch (error) {
            console.error('❌ 调用失败:', error.message);
            return false;
        }

        // 测试 description 方法
        console.log('\n5. 测试 description 方法');
        try {
            const result = await callContractMethod(contractAddress, contractABI, 'description', []);
            const description = decodeReturnValue(contractABI, 'description', result);
            console.log(`返回值: ${description}`);
            console.log('✅ 方法调用成功');
        } catch (error) {
            console.error('❌ 调用失败:', error.message);
            return false;
        }

        console.log('\n=== OCR 网络测试通过 ===');
        return true;
    } catch (error) {
        console.error('❌ 测试过程中出错:', error.message);
        return false;
    }
}

async function main() {
    const success = await testOCRNetwork();
    process.exit(success ? 0 : 1);
}

main();
