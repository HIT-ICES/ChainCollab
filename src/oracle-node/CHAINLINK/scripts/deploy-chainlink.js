const fs = require('fs');
const { execSync } = require('child_process');
const http = require('http');

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

async function deployContract(contractName, bytecode, args = []) {
    console.log(`\n正在部署 ${contractName}...`);

    const accounts = await rpcCall('eth_accounts', []);
    const deployer = accounts[0];

    const Web3EthAbi = require('web3-eth-abi');
    let deployData = bytecode;

    if (args.length > 0) {
        const encodedParams = Web3EthAbi.encodeParameters(
            args.map(a => a.type),
            args.map(a => a.value)
        ).slice(2);
        deployData = bytecode + encodedParams;
    }

    const txHash = await rpcCall('eth_sendTransaction', [{
        from: deployer,
        data: deployData,
        gas: '0x' + (5000000).toString(16)
    }]);

    console.log('交易哈希:', txHash);
    console.log('等待确认...');

    let receipt = null;
    for (let i = 0; i < 30; i++) {
        await new Promise(resolve => setTimeout(resolve, 2000));
        receipt = await rpcCall('eth_getTransactionReceipt', [txHash]);
        if (receipt) break;
    }

    if (!receipt || receipt.status === '0x0') {
        throw new Error('部署失败');
    }

    console.log(`✅ ${contractName} 部署成功!`);
    console.log('合约地址:', receipt.contractAddress);

    return receipt.contractAddress;
}

async function main() {
    try {
        console.log('开始部署 Chainlink 基础设施...\n');

        // 确保 deployment 文件夹存在
        const deploymentDir = 'deployment';
        if (!fs.existsSync(deploymentDir)) {
            fs.mkdirSync(deploymentDir);
        }

        // 1. 检查是否已编译合约
        if (!fs.existsSync(`${deploymentDir}/compiled.json`)) {
            console.log('=== 步骤 1: 编译合约 ===');
            execSync('./compile.sh', { stdio: 'inherit' });
        } else {
            console.log('=== 步骤 1: 合约已编译 ===');
        }

        // 读取编译后的合约
        const compiled = JSON.parse(fs.readFileSync(`${deploymentDir}/compiled.json`, 'utf8'));

        // 2. 部署 LinkToken 合约
        console.log('\n=== 步骤 2: 部署 LinkToken ===');
        const linkTokenKey = 'contracts/LinkToken-v0.6-fix/LinkToken.sol:LinkToken';
        const linkTokenData = compiled.contracts[linkTokenKey];

        if (!linkTokenData) {
            console.error('❌ 找不到 LinkToken 合约');
            process.exit(1);
        }

        const linkTokenBytecode = '0x' + linkTokenData.bin;
        const linkTokenAddress = await deployContract('LinkToken', linkTokenBytecode);

        // 3. 部署 Operator 合约
        console.log('\n=== 步骤 3: 编译并部署 Operator ===');
        const operatorPath = 'node_modules/@chainlink/contracts/src/v0.8/operatorforwarder/Operator.sol';
        execSync(`solc --optimize --base-path . --include-path node_modules --combined-json abi,bin ${operatorPath} > ${deploymentDir}/operator-compiled.json`, { stdio: 'inherit' });

        const operatorCompiled = JSON.parse(fs.readFileSync(`${deploymentDir}/operator-compiled.json`, 'utf8'));
        const operatorData = operatorCompiled.contracts[operatorPath + ':Operator'];
        const operatorBytecode = '0x' + operatorData.bin;
        const operatorAbi = operatorData.abi;

        const accounts = await rpcCall('eth_accounts', []);
        const deployer = accounts[0];

        const operatorAddress = await deployContract('Operator', operatorBytecode, [
            { type: 'address', value: linkTokenAddress },
            { type: 'address', value: deployer }
        ]);

        // 5. 保存部署信息
        const deploymentInfo = {
            linkToken: linkTokenAddress,
            operator: operatorAddress,
            operatorOwner: deployer,
            deployer: deployer,
            timestamp: new Date().toISOString(),
            chainId: 3456
        };

        // 确保 deployment 文件夹存在（已在第 93 行声明）
        if (!fs.existsSync(deploymentDir)) {
            fs.mkdirSync(deploymentDir);
        }

        fs.writeFileSync(`${deploymentDir}/chainlink-deployment.json`, JSON.stringify(deploymentInfo, null, 2));
        fs.writeFileSync(`${deploymentDir}/operator-abi.json`, JSON.stringify(operatorAbi, null, 2));

        console.log('\n========================================');
        console.log('✅ 所有合约部署完成!');
        console.log('========================================');
        console.log('LINK Token 地址:', linkTokenAddress);
        console.log('Operator 地址:', operatorAddress);
        console.log('Owner 地址:', deployer);
        console.log('\n部署信息已保存到 deployment/chainlink-deployment.json');
        console.log('Operator ABI 已保存到 deployment/operator-abi.json');

        // 清理临时编译文件
        if (fs.existsSync(`${deploymentDir}/operator-compiled.json`)) {
            fs.unlinkSync(`${deploymentDir}/operator-compiled.json`);
        }

        console.log('\n========================================');
        console.log('下一步: 创建 Chainlink Job');
        console.log('========================================');
        console.log('1. 访问 Chainlink 节点 UI: http://localhost:6688');
        console.log('2. 使用以下 Operator 地址创建 Job:', operatorAddress);

    } catch (error) {
        console.error('\n❌ 部署失败:', error.message);
        process.exit(1);
    }
}

main();
