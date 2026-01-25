const fs = require('fs');
const http = require('http');
const path = require('path');

// 读取编译后的合约
const ROOT_DIR = path.resolve(__dirname, '..', '..');
const deploymentDir = path.join(ROOT_DIR, 'deployment');

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

async function deploy() {
    try {
        // 检查是否已编译合约
        if (!fs.existsSync(`${deploymentDir}/compiled.json`)) {
            console.error('❌ 合约未编译，请先运行 compile.sh');
            process.exit(1);
        }

        const compiled = JSON.parse(fs.readFileSync(`${deploymentDir}/compiled.json`, 'utf8'));

        // 获取账户
        const accounts = await rpcCall('eth_accounts', []);
        if (accounts.length === 0) {
            console.error('❌ 没有可用的账户');
            return;
        }

        const deployer = accounts[0];
        console.log('部署账户:', deployer);

        // 检查余额
        const balance = await rpcCall('eth_getBalance', [deployer, 'latest']);
        const balanceEth = parseInt(balance, 16) / 1e18;
        console.log('账户余额:', balanceEth, 'ETH');

        if (balanceEth === 0) {
            console.error('\n❌ 账户余额为 0，无法部署合约');
            process.exit(1);
        }

        // 获取合约数据
        const contractKey = 'contracts/ocr/OffchainAggregator_Allequal.sol:OffchainAggregator';
        const contractData = compiled.contracts[contractKey];

        if (!contractData) {
            console.error('❌ 找不到合约:', contractKey);
            console.log('\n可用的合约:');
            Object.keys(compiled.contracts).forEach(key => {
                console.log(' -', key);
            });
            process.exit(1);
        }

        const abi = contractData.abi;
        const bytecode = '0x' + contractData.bin;

        console.log(`开始部署 ${contractKey.split(':')[1]} 合约...\n`);

        // 准备构造函数参数
        // OffchainAggregator 构造函数参数：
        // 1. uint32 _maximumGasPrice
        // 2. uint32 _reasonableGasPrice
        // 3. uint32 _microLinkPerEth
        // 4. uint32 _linkGweiPerObservation
        // 5. uint32 _linkGweiPerTransmission
        // 6. LinkTokenInterface _link
        // 7. int192 _minAnswer
        // 8. int192 _maxAnswer
        // 9. AccessControllerInterface _billingAccessController
        // 10. AccessControllerInterface _requesterAccessController
        // 11. uint8 _decimals
        // 12. string memory _description

        // 使用已部署的 LinkToken 合约地址
        const chainlinkDeploymentFile = `${deploymentDir}/chainlink-deployment.json`;
        if (!fs.existsSync(chainlinkDeploymentFile)) {
            console.error('❌ 找不到 chainlink-deployment.json，请先部署 LinkToken');
            process.exit(1);
        }

        const chainlinkDeployment = JSON.parse(fs.readFileSync(chainlinkDeploymentFile, 'utf8'));
        const linkTokenAddress = chainlinkDeployment.linkToken;
        if (!linkTokenAddress || linkTokenAddress === '0x0000000000000000000000000000000000000000') {
            console.error('❌ chainlink-deployment.json 中缺少有效的 LinkToken 地址');
            process.exit(1);
        }

        console.log('✅ 使用已部署的 LinkToken 地址:', linkTokenAddress);

        // 配置参数
        const maximumGasPrice = 100; // 100 Gwei (uint32 in gwei)
        const reasonableGasPrice = 50; // 50 Gwei (uint32 in gwei)
        const microLinkPerEth = 1000000; // 1 LINK per ETH
        const linkGweiPerObservation = 100000000; // 0.1 LINK per observation
        const linkGweiPerTransmission = 500000000; // 0.5 LINK per transmission
        const billingAccessController = '0x0000000000000000000000000000000000000000'; // 临时设置为零地址
        const requesterAccessController = '0x0000000000000000000000000000000000000000'; // 临时设置为零地址
        const decimals = 8;
        const description = 'My OCR Price Feed';
        const minAnswer = '0';
        const maxAnswer = '1000000000000000000'; // 1 ETH

        // 编码构造函数参数
        const Web3EthAbi = require('web3-eth-abi');
        const encodedParams = Web3EthAbi.encodeParameters(
            ['uint32', 'uint32', 'uint32', 'uint32', 'uint32', 'address', 'int192', 'int192', 'address', 'address', 'uint8', 'string'],
            [maximumGasPrice, reasonableGasPrice, microLinkPerEth, linkGweiPerObservation, linkGweiPerTransmission, linkTokenAddress, minAnswer, maxAnswer, billingAccessController, requesterAccessController, decimals, description]
        ).slice(2);

        const deployData = bytecode + encodedParams;

        // 发送部署交易
        const txHash = await rpcCall('eth_sendTransaction', [{
            from: deployer,
            data: deployData,
            gas: '0x' + (8000000).toString(16)
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

        console.log('\n✅ 合约部署成功!');
        console.log('合约地址:', receipt.contractAddress);
        console.log('Gas 使用:', parseInt(receipt.gasUsed, 16));

        // 保存部署信息
        const deploymentInfo = {
            contractAddress: receipt.contractAddress,
            deployer: deployer,
            timestamp: new Date().toISOString(),
            txHash: txHash
        };

        // 确保 deployment 文件夹存在
        if (!fs.existsSync(deploymentDir)) {
            fs.mkdirSync(deploymentDir);
        }

        fs.writeFileSync(`${deploymentDir}/ocr-deployment.json`, JSON.stringify(deploymentInfo, null, 2));
        console.log('\n部署信息已保存到 deployment/ocr-deployment.json');

        // 将 OCR 合约地址添加到 chainlink-deployment.json
        chainlinkDeployment.ocrContract = receipt.contractAddress;
        fs.writeFileSync(chainlinkDeploymentFile, JSON.stringify(chainlinkDeployment, null, 2));

    } catch (error) {
        console.error('❌ 部署失败:', error.message);
    }
}

deploy();
