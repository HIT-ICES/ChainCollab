const fs = require('fs');
const http = require('http');

// 读取编译后的合约
const deploymentDir = 'deployment';
const compiled = JSON.parse(fs.readFileSync(`${deploymentDir}/compiled.json`, 'utf8'));
const contractKey = 'contracts/MyChainlinkRequester.sol:MyChainlinkRequester';
const contractData = compiled.contracts[contractKey];

if (!contractData) {
    console.error('❌ 找不到合约:', contractKey);
    console.log('\n可用的合约:');
    Object.keys(compiled.contracts).forEach(key => {
        if (key.includes('simple.sol')) {
            console.log(' -', key);
        }
    });
    process.exit(1);
}

const abi = contractData.abi;
const bytecode = '0x' + contractData.bin;

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
        console.log('开始部署 MyChainlinkRequester 合约...\n');

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
            console.log('请先使用以下命令解锁挖矿账户并转账:');
            console.log(`docker exec chainlink-mybootnode-1 geth --exec "eth.sendTransaction({from: eth.coinbase, to: '${deployer}', value: web3.toWei(100, 'ether')})" attach /root/.ethereum/geth.ipc`);
            return;
        }

        // 构造函数参数（使用已部署的合约地址）
        let linkToken;
        let oracle;
        let chainlinkDeployment;

        const deploymentDir = 'deployment';
        if (fs.existsSync(`${deploymentDir}/chainlink-deployment.json`)) {
            chainlinkDeployment = JSON.parse(fs.readFileSync(`${deploymentDir}/chainlink-deployment.json`, 'utf8'));
            linkToken = chainlinkDeployment.linkToken;
            oracle = chainlinkDeployment.operator;
            console.log('✅ 使用已部署的 LinkToken 地址:', linkToken);
            console.log('✅ 使用已部署的 Operator 地址:', oracle);
        } else {
            console.error('❌ 请先部署 Chainlink 基础设施: node scripts/deploy-chainlink.js');
            process.exit(1);
        }

        // 从 chainlink-deployment.json 中读取 Job ID
        let jobId;
        if (chainlinkDeployment.jobId) {
            jobId = chainlinkDeployment.jobId;
            // 将 Job ID 转换为 bytes32 格式
            if (!jobId.startsWith('0x')) {
                jobId = '0x' + Buffer.from(jobId.replace(/-/g, ''), 'utf8').toString('hex').padEnd(64, '0');
            }
            console.log('✅ 使用已创建的 Job ID:', jobId);
        } else {
            console.error('❌ 请先创建 Chainlink Job: node scripts/create-job.js');
            process.exit(1);
        }
        const fee = '0x' + (BigInt('100000000000000000')).toString(16); // 0.1 LINK

        console.log('\n部署参数:');
        console.log('- LINK Token:', linkToken);
        console.log('- Oracle:', oracle);
        console.log('- Job ID:', jobId);
        console.log('- Fee:', '0.1 LINK');

        // 编码构造函数参数
        const Web3EthAbi = require('web3-eth-abi');
        const encodedParams = Web3EthAbi.encodeParameters(
            ['address', 'address', 'bytes32', 'uint256'],
            [linkToken, oracle, jobId, fee]
        ).slice(2); // 移除 '0x'

        const deployData = bytecode + encodedParams;

        console.log('\n正在部署合约...');

        // 发送部署交易
        const txHash = await rpcCall('eth_sendTransaction', [{
            from: deployer,
            data: deployData,
            gas: '0x' + (5000000).toString(16)
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
            txHash: txHash,
            linkToken: linkToken,
            oracle: oracle,
            jobId: jobId,
            fee: '0.1 LINK'
        };

        // 确保 deployment 文件夹存在（已在第 5 行声明）
        if (!fs.existsSync(deploymentDir)) {
            fs.mkdirSync(deploymentDir);
        }

        fs.writeFileSync(`${deploymentDir}/deployment.json`, JSON.stringify(deploymentInfo, null, 2));
        console.log('\n部署信息已保存到 deployment/deployment.json');

    } catch (error) {
        console.error('❌ 部署失败:', error.message);
    }
}

// 检查 web3-eth-abi 是否安装
try {
    require.resolve('web3-eth-abi');
    // 依赖已存在，直接部署
    deploy();
} catch (e) {
    console.error('❌ 缺少依赖: web3-eth-abi');
    console.error('');
    console.error('请先安装依赖:');
    console.error('  npm install web3-eth-abi');
    console.error('');
    console.error('然后重新运行部署脚本:');
    console.error('  node scripts/deploy-contract.js');
    console.error('  或者运行: ./deploy.sh');
    process.exit(1);
}
