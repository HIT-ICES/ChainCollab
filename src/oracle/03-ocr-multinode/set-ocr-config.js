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

// 读取节点信息
function getNodeInfo() {
    const nodeInfoFile = path.join(ROOT_DIR, 'deployment', 'node-info.json');
    if (!fs.existsSync(nodeInfoFile)) {
        console.error('❌ 找不到 node-info.json，请先运行 get-node-info.js');
        process.exit(1);
    }
    return JSON.parse(fs.readFileSync(nodeInfoFile, 'utf8'));
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
        console.log('\n可用的合约:');
        Object.keys(compiled.contracts).forEach(key => {
            console.log(' -', key);
        });
        process.exit(1);
    }

    return contractData.abi;
}

// 读取 OCR 配置生成结果
function getGeneratedOCRConfig() {
    const configFile = path.join(ROOT_DIR, 'deployment', 'ocr-config-gen.json');
    if (!fs.existsSync(configFile)) {
        console.error('❌ 找不到 ocr-config-gen.json，请先运行 gen-ocr-config.go');
        process.exit(1);
    }

    const data = JSON.parse(fs.readFileSync(configFile, 'utf8'));
    const requiredFields = ['signers', 'transmitters', 'threshold', 'encodedConfigVersion', 'encodedConfigHex'];
    const missing = requiredFields.filter(field => data[field] === undefined || data[field] === null);
    if (missing.length > 0) {
        console.error(`❌ ocr-config-gen.json 缺少字段: ${missing.join(', ')}`);
        process.exit(1);
    }
    return data;
}

async function main() {
    try {
        // 读取节点信息和合约部署信息
        const nodeInfo = getNodeInfo();
        const ocrDeployment = getOCRDeployment();
        const contractABI = getOCRContractABI();
        const generatedConfig = getGeneratedOCRConfig();

        const contractAddress = ocrDeployment.contractAddress;
        const deployer = ocrDeployment.deployer;

        // 获取账户
        const accounts = await rpcCall('eth_accounts', []);
        if (!accounts.includes(deployer)) {
            console.error('❌ 部署账户未找到');
            process.exit(1);
        }

        console.log('OCR 合约地址:', contractAddress);
        console.log('部署账户:', deployer);

        // 准备 setConfig 参数
        // OffchainAggregator.setConfig 方法参数：
        // 1. address[] _signers - 签名者地址列表
        // 2. address[] _transmitters - 传输者地址列表
        // 3. uint8 _threshold - 容错节点数（_threshold < n/3）
        // 4. uint64 _encodedConfigVersion - 链下配置版本
        // 5. bytes _encoded - 链下配置

        const signers = generatedConfig.signers;
        const transmitters = generatedConfig.transmitters;
        const threshold = generatedConfig.threshold;
        const encodedConfigVersion = generatedConfig.encodedConfigVersion;
        const encodedConfigHex = generatedConfig.encodedConfigHex;

        // 编码调用数据
        // 我们需要找到 setConfig 方法的签名
        let setConfigAbi = contractABI.find(method =>
            method.type === 'function' && method.name === 'setConfig'
        );

        if (!setConfigAbi) {
            console.error('❌ 找不到 setConfig 方法');
            process.exit(1);
        }

        const Web3EthAbi = require('web3-eth-abi');
        const encodedData = Web3EthAbi.encodeFunctionCall(setConfigAbi, [
            signers,
            transmitters,
            threshold,
            encodedConfigVersion,
            encodedConfigHex
        ]);

        // 先设置 payees（setConfig 要求 transmitters 已设置 payee）
        const setPayeesAbi = contractABI.find(method =>
            method.type === 'function' && method.name === 'setPayees'
        );
        if (!setPayeesAbi) {
            console.error('❌ 找不到 setPayees 方法');
            process.exit(1);
        }

        const payees = transmitters; // 简化处理：payee 使用与 transmitter 相同的地址
        const setPayeesData = Web3EthAbi.encodeFunctionCall(setPayeesAbi, [
            transmitters,
            payees
        ]);

        console.log('发送 setPayees 交易...');
        const payeesTxHash = await rpcCall('eth_sendTransaction', [{
            from: deployer,
            to: contractAddress,
            data: setPayeesData,
            gas: '0x' + (1000000).toString(16)
        }]);

        console.log('setPayees 交易哈希:', payeesTxHash);
        console.log('等待 setPayees 交易确认...');

        let payeesReceipt = null;
        for (let i = 0; i < 30; i++) {
            await new Promise(resolve => setTimeout(resolve, 2000));
            payeesReceipt = await rpcCall('eth_getTransactionReceipt', [payeesTxHash]);
            if (payeesReceipt) break;
        }

        if (!payeesReceipt) {
            console.error('❌ setPayees 交易确认超时');
            return;
        }

        if (payeesReceipt.status === '0x0') {
            console.error('❌ setPayees 交易失败');
            return;
        }

        // 预先 eth_call 检查 setConfig 是否会 revert
        console.log('检查 setConfig 预执行...');
        try {
            await rpcCall('eth_call', [{
                from: deployer,
                to: contractAddress,
                data: encodedData
            }, 'latest']);
        } catch (callError) {
            console.error('❌ setConfig 预执行失败:', callError.message);
            return;
        }

        // 发送交易
        console.log('发送 setConfig 交易...');
        const txHash = await rpcCall('eth_sendTransaction', [{
            from: deployer,
            to: contractAddress,
            data: encodedData,
            gas: '0x' + (3000000).toString(16)
        }]);

        console.log('交易哈希:', txHash);
        console.log('等待交易确认...');

        // 等待交易收据
        let receipt = null;
        for (let i = 0; i < 30; i++) {
            await new Promise(resolve => setTimeout(resolve, 2000));
            receipt = await rpcCall('eth_getTransactionReceipt', [txHash]);
            if (receipt) break;
        }

        if (!receipt) {
            console.error('❌ 交易确认超时');
            return;
        }

        if (receipt.status === '0x0') {
            console.error('❌ 交易失败');
            return;
        }

        console.log('\n✅ setConfig 成功!');
        console.log('Gas 使用:', parseInt(receipt.gasUsed, 16));

        // 获取最新配置详情
        const { Web3 } = require('web3');
        const web3 = new Web3('http://localhost:8545');

        const contract = new web3.eth.Contract(contractABI, contractAddress);
        const latestConfig = await contract.methods.latestConfigDetails().call();

        // 保存配置信息
        const configInfo = {
            configCount: latestConfig.configCount.toString(),
            blockNumber: latestConfig.blockNumber.toString(),
            configDigest: latestConfig.configDigest,
            txHash,
            timestamp: new Date().toISOString(),
            signers,
            transmitters,
            threshold,
            encodedConfigVersion,
            encodedConfigHex,
            configParams: generatedConfig.params || null
        };

        const configFile = path.join(ROOT_DIR, 'deployment', 'ocr-config.json');
        fs.writeFileSync(configFile, JSON.stringify(configInfo, null, 2));

        console.log('\n配置信息已保存到 deployment/ocr-config.json');

    } catch (error) {
        console.error('❌ 错误:', error.message);
    }
}

main();
