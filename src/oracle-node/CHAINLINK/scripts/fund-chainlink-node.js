const http = require('http');

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

async function getChainlinkNodeAddress() {
    try {
        // 使用 Docker 命令获取 Chainlink 节点的 ETH 账户地址
        const { exec } = require('child_process');

        return new Promise((resolve, reject) => {
            exec('docker logs chainlink-node 2>&1 | grep -i "Created EVM key with ID" | head -1', (error, stdout, stderr) => {
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
                // 匹配: Created EVM key with ID 0xEce2A0846275575BB5f7ac98fEFd2246b09CaBA7
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
        const deployer = accounts[0];

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

async function fundChainlinkNode() {
    try {
        console.log('📦 检查 Chainlink 节点账户状态...');
        console.log('');

        // 获取 Chainlink 节点地址
        const nodeAddress = await getChainlinkNodeAddress();

        // 检查当前余额
        const currentBalance = await getBalance(nodeAddress);

        // 如果余额小于 10 ETH，转账 100 ETH
        const MIN_BALANCE = 10;
        const TRANSFER_AMOUNT = 100;

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
    fundChainlinkNode().then(success => {
        process.exit(success ? 0 : 1);
    });
}

module.exports = fundChainlinkNode;
