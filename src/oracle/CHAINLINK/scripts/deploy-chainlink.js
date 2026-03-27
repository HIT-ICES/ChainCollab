const fs = require('fs');
const path = require('path');
const { execSync, spawnSync } = require('child_process');
const http = require('http');
const axios = require('axios');
const { URL } = require('url');

const RPC_URL = process.env.RPC_URL || 'http://localhost:8545';
const EXPECTED_DEPLOYER = (process.env.DEPLOYER_ACCOUNT || process.env.ETH_SYSTEM_ACCOUNT || '').toLowerCase();
const CHAINLINK_ROOT = path.resolve(__dirname, '..');
const SOLC_IMAGE = process.env.SOLC_IMAGE || 'ethereum/solc:0.8.19';
const OPERATOR_SOLC_IMAGE = process.env.OPERATOR_SOLC_IMAGE || 'ethereum/solc:0.8.19';

let cachedSolcRunner = null;

function resolveChainlinkLogContainer() {
    const explicit = process.env.CHAINLINK_LOG_CONTAINER;
    if (explicit) {
        return explicit;
    }

    const candidates = ['chainlink-node', 'chainlink-node1', 'chainlink-bootstrap'];
    for (const name of candidates) {
        const probe = spawnSync('docker', ['ps', '--filter', `name=^/${name}$`, '--format', '{{.Names}}'], {
            encoding: 'utf8'
        });
        if (probe.status === 0 && probe.stdout.trim()) {
            return probe.stdout.trim().split('\n')[0];
        }
    }
    return 'chainlink-node1';
}

function rpcOptions(postData) {
    const rpc = new URL(RPC_URL);
    return {
        hostname: rpc.hostname,
        port: rpc.port || (rpc.protocol === 'https:' ? 443 : 80),
        path: rpc.pathname === '' ? '/' : rpc.pathname,
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Content-Length': Buffer.byteLength(postData)
        }
    };
}

function pickDeployer(accounts) {
    if (!Array.isArray(accounts) || accounts.length === 0) {
        throw new Error(`eth_accounts returned empty on ${RPC_URL}`);
    }
    if (EXPECTED_DEPLOYER) {
        const matched = accounts.find((a) => String(a).toLowerCase() === EXPECTED_DEPLOYER);
        if (!matched) {
            throw new Error(
                `expected deployer ${EXPECTED_DEPLOYER} not found on ${RPC_URL}; got ${accounts.join(', ')}`
            );
        }
        return matched;
    }
    return accounts[0];
}

function isDockerAvailable() {
    const probe = spawnSync('docker', ['version', '--format', '{{.Server.Version}}'], {
        encoding: 'utf8'
    });
    return probe.status === 0;
}

function resolveSolcRunner() {
    if (cachedSolcRunner) {
        return cachedSolcRunner;
    }

    const localProbe = spawnSync('solc', ['--version'], {
        cwd: CHAINLINK_ROOT,
        encoding: 'utf8'
    });
    if (localProbe.status === 0) {
        cachedSolcRunner = { command: 'solc', args: [] };
        return cachedSolcRunner;
    }

    if (!isDockerAvailable()) {
        const message = localProbe.stderr || localProbe.stdout || `solc exit code ${localProbe.status}`;
        throw new Error(`solc 不可用，且 docker 不可用: ${message}`);
    }

    cachedSolcRunner = {
        command: 'docker',
        args: ['run', '--rm', '-v', `${CHAINLINK_ROOT}:/sources`, '-w', '/sources', SOLC_IMAGE]
    };
    return cachedSolcRunner;
}

function runSolc(args, outputPath) {
    const runner = resolveSolcRunner();
    return runSolcWithRunner(runner, args, outputPath);
}

function runSolcWithRunner(runner, args, outputPath) {
    const result = spawnSync(runner.command, [...runner.args, ...args], {
        cwd: CHAINLINK_ROOT,
        encoding: 'utf8',
        maxBuffer: 50 * 1024 * 1024
    });

    if (result.status !== 0) {
        if (runner.command !== 'docker' && isDockerAvailable()) {
            console.log(`⚠️  本机 solc 失败，改用 Docker 版 ${SOLC_IMAGE} 重试`);
            cachedSolcRunner = {
                command: 'docker',
                args: ['run', '--rm', '-v', `${CHAINLINK_ROOT}:/sources`, '-w', '/sources', SOLC_IMAGE]
            };
            return runSolc(args, outputPath);
        }

        const detail = [result.stdout, result.stderr].filter(Boolean).join('\n').trim();
        throw new Error(
            `solc 编译失败${detail ? `:\n${detail}` : ` (exit ${result.status})`}`
        );
    }

    if (outputPath) {
        fs.writeFileSync(outputPath, result.stdout);
    }

    return result.stdout;
}

function runSolcWithImage(image, args, outputPath) {
    const runner = {
        command: 'docker',
        args: ['run', '--rm', '-v', `${CHAINLINK_ROOT}:/sources`, '-w', '/sources', image]
    };
    return runSolcWithRunner(runner, args, outputPath);
}

// RPC 调用函数
function rpcCall(method, params) {
    return new Promise((resolve, reject) => {
        const postData = JSON.stringify({
            jsonrpc: '2.0',
            method: method,
            params: params,
            id: 1
        });

        const options = rpcOptions(postData);

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
    const deployer = pickDeployer(accounts);

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

function readChainlinkApiCredentials() {
    const apiPath = path.resolve(__dirname, '../chainlink/.api');
    if (!fs.existsSync(apiPath)) {
        return null;
    }
    const lines = fs.readFileSync(apiPath, 'utf8').split('\n').map(line => line.trim()).filter(Boolean);
    if (lines.length < 2) {
        return null;
    }
    return { email: lines[0], password: lines[1] };
}

async function fetchChainlinkNodeAddressFromApi() {
    const chainlinkUrl = process.env.CHAINLINK_URL || 'http://localhost:6688';
    const creds = readChainlinkApiCredentials();
    if (!creds) {
        return null;
    }

    const session = await axios.post(`${chainlinkUrl}/sessions`, {
        email: creds.email,
        password: creds.password
    });

    const cookies = session.headers['set-cookie'];
    if (!cookies || cookies.length === 0) {
        return null;
    }

    const keys = await axios.get(`${chainlinkUrl}/v2/keys/eth`, {
        headers: { Cookie: cookies.join('; ') }
    });

    const address = keys?.data?.data?.[0]?.attributes?.address;
    return address || null;
}

async function getChainlinkNodeAddress(existingDeployment) {
    if (existingDeployment && existingDeployment.chainlinkNodeAddress) {
        return existingDeployment.chainlinkNodeAddress;
    }

    if (process.env.CHAINLINK_NODE_ADDRESS) {
        return process.env.CHAINLINK_NODE_ADDRESS;
    }

    try {
        const fromApi = await fetchChainlinkNodeAddressFromApi();
        if (fromApi) {
            return fromApi;
        }
    } catch (error) {
        // Ignore API failures; fallback to docker logs.
    }

    try {
        const container = resolveChainlinkLogContainer();
        const stdout = execSync(`docker logs ${container} 2>&1 | grep -i "Unlocked .*ETH keys" | head -1`, { encoding: 'utf8' });
        const match = stdout.match(/0x[a-fA-F0-9]{40}/);
        if (match) {
            return match[0];
        }
    } catch (error) {
        // Ignore log parsing failures; caller will decide whether to use null.
    }

    return null;
}

async function main() {
    try {
        console.log('开始部署 Chainlink 基础设施...\n');
        console.log('RPC URL:', RPC_URL);
        if (EXPECTED_DEPLOYER) {
            console.log('Expected deployer:', EXPECTED_DEPLOYER);
        }

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
        const operatorCompiledJson = runSolcWithImage(OPERATOR_SOLC_IMAGE, [
            '--optimize',
            '--base-path', '.',
            '--include-path', 'node_modules',
            '--combined-json', 'abi,bin',
            operatorPath
        ], `${deploymentDir}/operator-compiled.json`);

        const operatorCompiled = JSON.parse(operatorCompiledJson);
        const operatorData = operatorCompiled.contracts[operatorPath + ':Operator'];
        const operatorBytecode = '0x' + operatorData.bin;
        const operatorAbi = operatorData.abi;

        const accounts = await rpcCall('eth_accounts', []);
        const deployer = pickDeployer(accounts);

        const operatorAddress = await deployContract('Operator', operatorBytecode, [
            { type: 'address', value: linkTokenAddress },
            { type: 'address', value: deployer }
        ]);

        // 5. 保存部署信息
        let existingDeployment = {};
        if (fs.existsSync(`${deploymentDir}/chainlink-deployment.json`)) {
            existingDeployment = JSON.parse(fs.readFileSync(`${deploymentDir}/chainlink-deployment.json`, 'utf8'));
        }

        const chainlinkNodeAddress = await getChainlinkNodeAddress(existingDeployment);

        const deploymentInfo = {
            linkToken: linkTokenAddress,
            operator: operatorAddress,
            operatorOwner: deployer,
            deployer: deployer,
            timestamp: new Date().toISOString(),
            chainId: 3456,
            chainlinkNodeAddress: chainlinkNodeAddress
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
        if (chainlinkNodeAddress) {
            console.log('Chainlink 节点地址:', chainlinkNodeAddress);
        }
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
