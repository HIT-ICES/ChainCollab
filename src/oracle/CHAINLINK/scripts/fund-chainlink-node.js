const fs = require('fs');
const path = require('path');
const http = require('http');
const { URL } = require('url');
const { exec, spawnSync } = require('child_process');
const axios = require('axios');
const RPC_URL = process.env.RPC_URL || 'http://localhost:8545';
const EXPECTED_DEPLOYER = (process.env.DEPLOYER_ACCOUNT || process.env.ETH_SYSTEM_ACCOUNT || '').toLowerCase();

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
                if (response.error) reject(new Error(response.error.message));
                else resolve(response.result);
            });
        });

        req.on('error', reject);
        req.write(postData);
        req.end();
    });
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

    return keys?.data?.data?.[0]?.attributes?.address || null;
}

function persistChainlinkNodeAddress(address) {
    try {
        const deploymentPath = path.resolve(__dirname, '../deployment/chainlink-deployment.json');
        if (!fs.existsSync(deploymentPath)) {
            return;
        }
        const deployment = JSON.parse(fs.readFileSync(deploymentPath, 'utf8'));
        deployment.chainlinkNodeAddress = address;
        fs.writeFileSync(deploymentPath, JSON.stringify(deployment, null, 2));
    } catch (error) {
        console.warn('⚠️  写入 chainlinkNodeAddress 失败:', error.message);
    }
}

async function getChainlinkNodeAddress() {
    try {
        // Highest priority: explicit caller override.
        if (arguments.length && arguments[0]) {
            console.log('✅ 使用命令行参数提供的地址:', arguments[0]);
            persistChainlinkNodeAddress(arguments[0]);
            return arguments[0];
        }

        const fromEnv = process.env.CHAINLINK_NODE_ADDRESS;
        if (fromEnv) {
            console.log('✅ 使用环境变量 CHAINLINK_NODE_ADDRESS:', fromEnv);
            persistChainlinkNodeAddress(fromEnv);
            return fromEnv;
        }

        const deploymentPath = path.resolve(__dirname, '../deployment/chainlink-deployment.json');
        if (fs.existsSync(deploymentPath)) {
            const deployment = JSON.parse(fs.readFileSync(deploymentPath, 'utf8'));
            if (deployment.chainlinkNodeAddress) {
                console.log('✅ 使用部署文件中的 chainlinkNodeAddress:', deployment.chainlinkNodeAddress);
                return deployment.chainlinkNodeAddress;
            }
        }

        try {
            const fromApi = await fetchChainlinkNodeAddressFromApi();
            if (fromApi) {
                console.log('✅ 从 Chainlink API 获取节点地址:', fromApi);
                persistChainlinkNodeAddress(fromApi);
                return fromApi;
            }
        } catch (error) {
            // Ignore API failures; fallback to docker logs.
        }

        return new Promise((resolve, reject) => {
            const container = resolveChainlinkLogContainer();
            exec(`docker logs ${container} 2>&1 | grep -i "Unlocked .*ETH keys" | head -1`, (error, stdout, stderr) => {
                if (error) {
                    console.error('❌ 获取 Chainlink 节点账户失败:', error.message);
                    reject(error);
                    return;
                }

                if (stderr) {
                    console.error('❌ 错误:', stderr);
                    reject(new Error(stderr));
                    return;
                }

                // 解析地址
                // 匹配: Unlocked 1 ETH keys                                keystore/models.go:298           keys=["0xbB64621210982bb8504E20F1D81b2028647A5957"]
                const match = stdout.match(/0x[a-fA-F0-9]{40}/);
                if (match) {
                    const address = match[0];
                    console.log('✅ 找到 Chainlink 节点 ETH 账户:', address);
                    persistChainlinkNodeAddress(address);
                    resolve(address);
                } else {
                    console.error('❌ 无法解析 Chainlink 节点地址');
                    console.error('请在 deployment/chainlink-deployment.json 中设置 chainlinkNodeAddress');
                    console.error('请手动传入地址: node scripts/fund-chainlink-node.js <address>');
                    reject(new Error('无法解析 Chainlink 节点地址'));
                }
            });
        });
    } catch (error) {
        console.error('❌ 获取 Chainlink 节点地址失败:', error.message);
        throw error;
    }
}

async function getBalance(address) {
    try {
        const balanceHex = await rpcCall('eth_getBalance', [address, 'latest']);
        const balanceEth = parseInt(balanceHex, 16) / 1e18;
        console.log('Chainlink 节点 ETH 余额:', balanceEth.toFixed(6), 'ETH');
        return balanceEth;
    } catch (error) {
        console.error('❌ 获取余额失败:', error.message);
        throw error;
    }
}

async function transferEth(toAddress, amountEth) {
    try {
        const accounts = await rpcCall('eth_accounts', []);
        const deployer = pickDeployer(accounts);

        const valueWei = '0x' + (BigInt(Math.floor(amountEth * 1e18))).toString(16);

        console.log(`正在向 Chainlink 节点账户转账 ${amountEth} ETH...`);
        const txHash = await rpcCall('eth_sendTransaction', [{
            from: deployer,
            to: toAddress,
            value: valueWei,
            gas: '0x' + (210000).toString(16) // 标准转账的 gas 限制
        }]);

        console.log('✅ 转账交易发送成功');
        console.log('交易哈希:', txHash);

        // 等待交易确认
        console.log('等待交易确认...');
        let receipt = null;
        for (let i = 0; i < 30; i++) {
            await new Promise(resolve => setTimeout(resolve, 2000));
            receipt = await rpcCall('eth_getTransactionReceipt', [txHash]);
            if (receipt) break;
        }

        if (!receipt) {
            console.warn('⚠️  交易确认超时，但通常已成功');
            return false;
        }

        if (receipt.status === '0x0') {
            console.error('❌ 交易失败');
            return false;
        }

        console.log('✅ 交易确认成功');
        return true;

    } catch (error) {
        console.error('❌ 转账失败:', error.message);
        throw error;
    }
}

function getArgValue(args, flag) {
    const idx = args.indexOf(flag);
    if (idx === -1 || idx + 1 >= args.length) return null;
    return args[idx + 1];
}

function parseAmount(value, fallback) {
    if (!value) return fallback;
    const num = Number(value);
    return Number.isFinite(num) && num >= 0 ? num : fallback;
}

function getNodeInfoAddresses() {
    const deploymentPath = path.resolve(__dirname, '../deployment/node-info.json');
    if (!fs.existsSync(deploymentPath)) {
        throw new Error('deployment/node-info.json 不存在，无法批量获取节点地址');
    }
    const info = JSON.parse(fs.readFileSync(deploymentPath, 'utf8'));
    const addresses = info
        .map((node) => node.ethAddress)
        .filter(Boolean);
    return Array.from(new Set(addresses));
}

async function fundAddresses(addresses, minBalance, transferAmount) {
    for (const address of addresses) {
        console.log('');
        console.log('📦 检查节点账户:', address);
        const currentBalance = await getBalance(address);
        if (currentBalance < minBalance) {
            console.log(`⚠️  节点余额低于 ${minBalance} ETH，需要充值`);
            const success = await transferEth(address, transferAmount);
            if (success) {
                const newBalance = await getBalance(address);
                console.log('✅ 充值成功！新的余额:', newBalance.toFixed(6), 'ETH');
            }
        } else {
            console.log('✅ 节点余额充足');
        }
    }
}

async function fundChainlinkNode(addressOverride, minBalance, transferAmount) {
    try {
        console.log('📦 检查 Chainlink 节点账户状态...');
        console.log('RPC URL:', RPC_URL);
        if (EXPECTED_DEPLOYER) {
            console.log('Expected deployer:', EXPECTED_DEPLOYER);
        }
        console.log('');

        // 获取 Chainlink 节点地址
        const nodeAddress = await getChainlinkNodeAddress(addressOverride);

        // 检查当前余额
        const currentBalance = await getBalance(nodeAddress);

        // 如果余额小于 10 ETH，转账 100 ETH
        const MIN_BALANCE = minBalance ?? 10;
        const TRANSFER_AMOUNT = transferAmount ?? 100;

        if (currentBalance < MIN_BALANCE) {
            console.log('');
            console.log(`⚠️  节点余额低于 ${MIN_BALANCE} ETH，需要充值`);

            const success = await transferEth(nodeAddress, TRANSFER_AMOUNT);

            if (success) {
                const newBalance = await getBalance(nodeAddress);
                console.log('');
                console.log('✅ 充值成功！');
                console.log('新的余额:', newBalance.toFixed(6), 'ETH');
            }
        } else {
            console.log('');
            console.log('✅ Chainlink 节点余额充足');
        }

        return true;

    } catch (error) {
        console.error('❌ 充值过程中出错:', error.message);
        console.error('详细信息:', error);
        return false;
    }
}

// 如果直接运行此脚本
if (require.main === module) {
    const args = process.argv.slice(2);
    const useAll = args.includes('--all');
    const minBalance = parseAmount(getArgValue(args, '--min'), 10);
    const transferAmount = parseAmount(getArgValue(args, '--amount'), 100);
    const addressOverride = getArgValue(args, '--address') || args.find((arg) => !arg.startsWith('-'));

    if (useAll) {
        fundAddresses(getNodeInfoAddresses(), minBalance, transferAmount)
            .then(() => process.exit(0))
            .catch((error) => {
                console.error('❌ 批量充值失败:', error.message);
                process.exit(1);
            });
    } else {
        fundChainlinkNode(addressOverride, minBalance, transferAmount).then(success => {
            process.exit(success ? 0 : 1);
        });
    }
}

module.exports = fundChainlinkNode;
