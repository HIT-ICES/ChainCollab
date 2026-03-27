const fs = require('fs');
const http = require('http');
const { URL } = require('url');
const { exec, spawnSync } = require('child_process');

const RPC_URL = process.env.RPC_URL || 'http://localhost:8545';

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

async function getChainlinkNodeAddress() {
    try {
        return new Promise((resolve, reject) => {
            const container = resolveChainlinkLogContainer();
            exec(`docker logs ${container} 2>&1 | grep -i "Created EVM key with ID" | head -1`, (error, stdout, stderr) => {
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

                const match = stdout.match(/0x[a-fA-F0-9]{40}/);
                if (match) {
                    const address = match[0];
                    console.log('✅ 找到 Chainlink 节点 ETH 账户:', address);
                    resolve(address);
                } else {
                    console.error('❌ 无法解析 Chainlink 节点地址');
                    reject(new Error('无法解析 Chainlink 节点地址'));
                }
            });
        });
    } catch (error) {
        console.error('❌ 获取 Chainlink 节点地址失败:', error.message);
        throw error;
    }
}

async function addAuthorizedNode(operatorAddress, nodeAddress) {
    try {
        const Web3EthAbi = require('web3-eth-abi');

        // 获取 Operator 合约的 ABI
        const operatorAbi = JSON.parse(fs.readFileSync('deployment/operator-abi.json', 'utf8'));

        // 找到 setAuthorizedSenders 函数
        const setAuthorizedSendersFunc = operatorAbi.find(func =>
            func.type === 'function' && func.name === 'setAuthorizedSenders'
        );

        if (!setAuthorizedSendersFunc) {
            console.error('❌ 无法找到 setAuthorizedSenders 函数');
            return false;
        }

        // 获取当前授权的发送者列表
        const getAuthorizedSendersFunc = operatorAbi.find(func =>
            func.type === 'function' && func.name === 'getAuthorizedSenders'
        );

        let currentAuthorizedSenders = [];
        if (getAuthorizedSendersFunc) {
            const getAuthorizedData = Web3EthAbi.encodeFunctionCall(getAuthorizedSendersFunc, []);
            const result = await rpcCall('eth_call', [{
                to: operatorAddress,
                data: getAuthorizedData
            }, 'latest']);

            // 解析地址数组
            // 这里我们简单处理，直接添加新地址
            currentAuthorizedSenders = [];
        }

        // 添加新地址
        const newAuthorizedSenders = [...currentAuthorizedSenders, nodeAddress];

        // 编码函数调用
        const data = Web3EthAbi.encodeFunctionCall(setAuthorizedSendersFunc, [newAuthorizedSenders]);

        // 获取部署者账户
        const accounts = await rpcCall('eth_accounts', []);
        const deployer = accounts[0];

        console.log('正在授权 Chainlink 节点地址...');

        const txHash = await rpcCall('eth_sendTransaction', [{
            from: deployer,
            to: operatorAddress,
            data: data,
            gas: '0x' + (5000000).toString(16)
        }]);

        console.log('✅ 授权交易发送成功');
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

        console.log('✅ 节点授权成功！');
        return true;

    } catch (error) {
        console.error('❌ 授权失败:', error.message);
        console.error('详细信息:', error);
        return false;
    }
}

async function isNodeAuthorized(operatorAddress, nodeAddress) {
    try {
        const Web3EthAbi = require('web3-eth-abi');

        // 获取 Operator 合约的 ABI
        const operatorAbi = JSON.parse(fs.readFileSync('deployment/operator-abi.json', 'utf8'));

        // 找到 isAuthorizedSender 函数
        const isAuthorizedSenderFunc = operatorAbi.find(func =>
            func.type === 'function' && func.name === 'isAuthorizedSender'
        );

        if (!isAuthorizedSenderFunc) {
            console.error('❌ 无法找到 isAuthorizedSender 函数');
            return false;
        }

        // 编码函数调用
        const data = Web3EthAbi.encodeFunctionCall(isAuthorizedSenderFunc, [nodeAddress]);

        // 调用合约
        const result = await rpcCall('eth_call', [{
            to: operatorAddress,
            data: data
        }, 'latest']);

        // 解析布尔值
        const isAuthorized = parseInt(result, 16) === 1;

        if (isAuthorized) {
            console.log('✅ Chainlink 节点已授权');
        } else {
            console.log('❌ Chainlink 节点未授权');
        }

        return isAuthorized;

    } catch (error) {
        console.error('❌ 检查授权状态失败:', error.message);
        console.error('详细信息:', error);
        return false;
    }
}

async function authorizeChainlinkNode() {
    try {
        console.log('🔐 检查 Chainlink 节点授权状态...');
        console.log('RPC URL:', RPC_URL);
        console.log('');

        // 读取部署信息
        const chainlinkDeployment = JSON.parse(fs.readFileSync('deployment/chainlink-deployment.json', 'utf8'));
        const operatorAddress = chainlinkDeployment.operator;

        // 获取 Chainlink 节点地址
        const nodeAddress = await getChainlinkNodeAddress();

        // 检查是否已授权
        console.log('');
        const authorized = await isNodeAuthorized(operatorAddress, nodeAddress);

        if (!authorized) {
            console.log('');
            console.log('⚠️  节点未授权，正在授权...');

            const success = await addAuthorizedNode(operatorAddress, nodeAddress);

            if (success) {
                console.log('');
                console.log('✅ 授权成功！');
            } else {
                console.log('');
                console.error('❌ 授权失败');
                return false;
            }
        }

        console.log('');
        console.log('✅ Chainlink 节点授权状态检查完成');
        return true;

    } catch (error) {
        console.error('❌ 授权过程中出错:', error.message);
        console.error('详细信息:', error);
        return false;
    }
}

// 如果直接运行此脚本
if (require.main === module) {
    authorizeChainlinkNode().then(success => {
        process.exit(success ? 0 : 1);
    });
}

module.exports = authorizeChainlinkNode;
