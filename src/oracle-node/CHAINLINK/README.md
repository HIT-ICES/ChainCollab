# Chainlink Oracle 节点 - Geth 私链集成

## 概述

本项目实现了 Chainlink Oracle 节点与 Geth 私链的完整集成,支持智能合约通过 Oracle 请求链外数据。

### 核心特性

- **链外数据访问**: 智能合约可以请求任意 HTTP API 数据
- **JSON 解析**: 支持 JSONPath 提取和解析 JSON 响应
- **自动回调**: Chainlink 自动将结果返回给合约
- **LINK Token**: 使用 LINK Token 支付 Oracle 服务费用
- **Docker 部署**: 完整的 Docker Compose 配置,一键启动

## 架构图

```
用户合约 (simple.sol)
    ↓ 支付 LINK Token
Operator 合约
    ↓ 触发 OracleRequest 事件
Chainlink 节点
    ↓ HTTP GET 请求
外部 API
    ↓ JSON 响应
Chainlink 节点
    ↓ fulfillOracleRequest2
Operator 合约
    ↓ 回调 fulfill 函数
用户合约 (保存结果)
```

## 项目结构

```
CHAINLINK/
├── contracts/              # 智能合约
│   ├── simple.sol         # Chainlink 客户端合约
│   └── MockLinkToken.sol  # LINK Token 合约
│
├── scripts/               # 部署脚本
│   ├── deploy-chainlink.js    # 部署 LINK + Operator
│   ├── deploy-contract.js     # 部署客户端合约
│   └── create-job.js          # 创建 Chainlink Job
│
├── geth-node/             # Geth 节点配置
│   ├── Dockerfile
│   ├── genesis.json
│   └── datadir/keystore/
│
├── chainlink/             # Chainlink 节点配置
│   ├── config.toml
│   └── secrets.toml
│
├── config/                # 配置文件
│   └── job-spec.toml      # Job 规范
│
├── deployment/            # 部署信息
│   └── deployment/chainlink-deployment.json
│
├── 🚀 一键脚本
│   ├── start.sh           # 一键启动所有服务
│   ├── status.sh          # 查看服务状态
│   ├── unlock-account.sh  # 解锁 Geth 账户
│   ├── compile.sh         # 编译合约
│   ├── deploy.sh          # 完整部署流程 (编译+解锁+部署)
│   ├── clean-jobs.sh      # 清理 Chainlink Jobs (保留区块链)
│   └── clean.sh           # 完全清理所有数据 ⚠️
│
└── docker-compose.yml     # Docker 编排
```

## 已部署信息

### 合约地址 (Chain ID: 3456)

```
LINK Token:  0xe640cdaf5df426bfaa1664e47a91f3106db07792
Operator:    0x75cd7081c3224a11b2b013faed8606acd4cec737
部署账户:    0x7e9519a329908320829f4a747b8bac06cf0955cb
```

### Chainlink Job

```
Job ID:      1e7d2a7c-fd9c-40c0-bb7f-287032908212
Job Type:    directrequest (HTTP GET)
```

### 服务端口

```
Chainlink UI:  http://localhost:6688
  用户名: admin@chain.link
  密码:   change-me-strong

Geth RPC:      http://localhost:8545
PostgreSQL:    localhost:5432
```

## 快速开始

### 方式 1: 一键启动 (推荐)

```bash
# 一键启动所有服务并检查状态
./start.sh

# 查看服务状态
./status.sh

# 解锁账户 (部署合约前需要)
./unlock-account.sh
```

### 方式 2: 手动启动

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看 Chainlink 日志
docker logs chainlink-node -f
```

### 2. 访问 Chainlink UI

打开浏览器访问 http://localhost:6688

- 用户名: `admin@chain.link`
- 密码: `change-me-strong`

### 3. 创建 Chainlink Job (首次使用必需)

**如果是首次部署或清理过 Jobs,需要创建 Chainlink Job:**

```bash
# 创建 Job (会读取 config/job-spec.toml)
node scripts/create-job.js
```

这将创建一个 HTTP GET Job,用于从外部 API 获取数据。

**输出示例:**
```
✅ Job 创建成功!
Job ID: 1e7d2a7c-fd9c-40c0-bb7f-287032908212
Job External Job ID: 1e7d2a7c-fd9c-40c0-bb7f-287032908212
```

**注意**:
- Job 会保存在 PostgreSQL 数据库中,重启服务后仍然存在
- 如果已经创建过 Job,可以跳过此步骤
- 如果需要重新创建 Job,先运行 `./clean-jobs.sh` 清理旧 Job

### 4. 部署客户端合约 (可选)

**方式 1: 一键部署 (推荐)**

```bash
# 自动完成编译、解锁、部署全流程
./deploy.sh
```

**方式 2: 分步部署**

```bash
# 步骤 1: 编译合约
./compile.sh

# 步骤 2: 解锁账户
./unlock-account.sh

# 步骤 3: 部署合约
node scripts/deploy-contract.js
```

**方式 3: 手动部署**

```bash
# 编译合约
solc --optimize --base-path . --include-path node_modules \
  --combined-json abi,bin contracts/simple.sol > deployment/compiled.json

# 解锁账户
docker exec chainlink-mybootnode-1 geth --exec \
  "personal.unlockAccount('0x7e9519A329908320829F4a747b8Bac06cF0955cb', 'password123', 0)" \
  attach /root/.ethereum/geth.ipc

# 部署合约
node scripts/deploy-contract.js
```

### 4. 测试 Oracle 请求

```javascript
// 1. 给合约转入 LINK Token
await linkToken.transfer(contractAddress, ethers.utils.parseEther("1"));

// 2. 发起 Oracle 请求
await contract.requestOffchainData("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd");

// 3. 等待 Chainlink 处理 (约 10-30 秒)

// 4. 读取结果
const result = await contract.result();
console.log("Result:", result.toString());
```

## 完整工作流程

### 首次部署完整流程

```bash
# 1. 启动所有服务
./start.sh

# 2. 创建 Chainlink Job (首次必需)
node scripts/create-job.js

# 3. 编译合约
./compile.sh

# 4. 部署合约
./deploy.sh
```

### 重新部署合约

如果 Job 已经存在,只需要重新部署合约:

```bash
# 1. 确保服务运行
./status.sh

# 2. 重新编译和部署
./deploy.sh
```

### 重置 Jobs 并重新部署

如果需要修改 Job 配置:

```bash
# 1. 清理旧 Job
./clean-jobs.sh

# 2. 重新启动服务
./start.sh

# 3. 创建新 Job
node scripts/create-job.js

# 4. 重新部署合约 (使用新的 Job ID)
./deploy.sh
```

### 完全重置

如果需要从头开始:

```bash
# 1. 完全清理
./clean.sh

# 2. 重新启动
./start.sh

# 3. 重新部署基础设施 (如果需要)
node scripts/deploy-chainlink.js

# 4. 创建 Job
node scripts/create-job.js

# 5. 部署合约
./deploy.sh
```

## 常用命令

### 服务管理

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 重启服务
docker-compose restart

# 查看日志
docker logs chainlink-node --tail 100 -f
docker logs chainlink-mybootnode-1 --tail 100 -f
```

### 账户管理

```bash
# 查看账户列表
docker exec chainlink-mybootnode-1 geth --exec "eth.accounts" attach /root/.ethereum/geth.ipc

# 查看账户余额
docker exec chainlink-mybootnode-1 geth --exec \
  "web3.fromWei(eth.getBalance('0x7e9519A329908320829F4a747b8Bac06cF0955cb'), 'ether')" \
  attach /root/.ethereum/geth.ipc

# 解锁账户 (0 表示永久解锁)
docker exec chainlink-mybootnode-1 geth --exec \
  "personal.unlockAccount('0x7e9519A329908320829F4a747b8Bac06cF0955cb', 'password123', 0)" \
  attach /root/.ethereum/geth.ipc
```

## 合约部署参数

部署 `MyChainlinkRequester` 合约时使用以下参数:

```javascript
const params = {
  linkToken: "0xe640cdaf5df426bfaa1664e47a91f3106db07792",
  oracle: "0x75cd7081c3224a11b2b013faed8606acd4cec737",
  jobId: "0x3961656236363530303833653436366661353330616464323632656630333765",
  fee: "100000000000000000" // 0.1 LINK
};
```

## 技术要点

### 1. Chainlink 合约 API (v1.4.0)

- 所有函数添加下划线前缀: `_setChainlinkToken()`, `_buildChainlinkRequest()`
- 导入路径更新: `@chainlink/contracts/src/v0.8/operatorforwarder/`

### 2. WebSocket 配置

Geth 启动参数必须包含:
- `--ws` - 启用 WebSocket
- `--ws.addr 0.0.0.0` - 监听所有接口
- `--ws.port 8546` - WebSocket 端口
- `--ws.api eth,net,web3,personal,admin` - 允许的 API

### 3. EIP55 地址格式

Job 配置中的合约地址必须使用 EIP55 校验和格式,否则会报错。

### 4. Job Spec 配置

关键配置项:
- `evmChainID = "3456"` - 必须匹配 Geth Chain ID
- `contractAddress` - 使用 EIP55 格式的 Operator 地址
- `allowUnrestrictedNetworkAccess = true` - 允许访问外部 API

## 故障排除

### Chainlink 无法连接到 Geth

**症状**: 日志显示 "No live RPC nodes available"

**解决方案**:
```bash
# 检查 Geth WebSocket 是否启用
docker exec chainlink-mybootnode-1 ps aux | grep ws

# 重启服务
docker-compose restart
```

### 账户未解锁

**症状**: "authentication needed: password or unlock"

**解决方案**:
```bash
docker exec chainlink-mybootnode-1 geth --exec \
  "personal.unlockAccount('0x7e9519A329908320829F4a747b8Bac06cF0955cb', 'password123', 0)" \
  attach /root/.ethereum/geth.ipc
```

### Job 未触发

**可能原因**:
1. 合约没有足够的 LINK Token
2. Job ID 不匹配
3. Operator 地址不正确
4. Gas 费用不足

**检查步骤**:
```bash
# 查看 Chainlink 日志
docker logs chainlink-node --tail 100

# 访问 Chainlink UI 查看 Job Runs
open http://localhost:6688/jobs/1e7d2a7c-fd9c-40c0-bb7f-287032908212
```

### EIP55 地址错误

**症状**: "is not a valid EIP55 formatted address"

**解决方案**: 使用正确的校验和地址格式。可以通过以下方式生成:

```javascript
const {keccak256} = require('@ethersproject/keccak256');
const {toUtf8Bytes} = require('@ethersproject/strings');

function toChecksumAddress(address) {
  address = address.toLowerCase().replace('0x', '');
  const hash = keccak256(toUtf8Bytes(address)).slice(2);
  let result = '0x';
  for (let i = 0; i < address.length; i++) {
    result += parseInt(hash[i], 16) >= 8 ?
              address[i].toUpperCase() :
              address[i].toLowerCase();
  }
  return result;
}
```

## 使用场景示例

### 获取加密货币价格

```solidity
// 请求以太坊价格
string memory url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd";
requestOffchainData(url);
```

### 获取天气数据

```solidity
// 请求天气数据
string memory url = "https://api.openweathermap.org/data/2.5/weather?q=London&appid=YOUR_API_KEY";
requestOffchainData(url);
```

### 获取随机数

```solidity
// 请求随机数 API
string memory url = "https://api.random.org/json-rpc/4/invoke";
requestOffchainData(url);
```

## 开发工具

### 编译合约

```bash
# 使用 solc 编译
solc --optimize --base-path . --include-path node_modules \
  --combined-json abi,bin contracts/simple.sol

# 使用 Hardhat 编译
npx hardhat compile
```

### 部署脚本

```bash
# 部署基础设施 (仅首次)
node scripts/deploy-chainlink.js

# 创建 Chainlink Job (仅首次)
node scripts/create-job.js

# 部署客户端合约
node scripts/deploy-contract.js
```

## 技术栈

- **区块链**: Geth (私链, Chain ID: 3456)
- **Oracle**: Chainlink Node
- **智能合约**: Solidity ^0.8.19
- **开发工具**: Node.js, Hardhat, solc
- **数据库**: PostgreSQL
- **部署**: Docker Compose

## 下一步优化

### 短期
- [ ] 添加单元测试
- [ ] 实现多 Oracle 聚合
- [ ] 添加 POST 请求支持

### 中期
- [ ] 实现数据签名验证
- [ ] 添加请求重试机制
- [ ] 优化 Gas 费用

### 长期
- [ ] 迁移到主网/测试网
- [ ] 集成真实 LINK Token
- [ ] 实现去中心化 Oracle 网络

## 相关文档

- [Chainlink 官方文档](https://docs.chain.link/)
- [Geth 节点配置](geth-node/README.md)
- [合约源码](contracts/simple.sol)
- [Job 配置](config/job-spec.toml)

## 注意事项

1. **私钥安全**: 私钥和密码仅用于测试环境,生产环境请妥善保管
2. **Gas 费用**: 每次 Oracle 请求需要消耗 Gas 和 LINK Token
3. **网络访问**: 确保 Chainlink 节点可以访问外部 API
4. **数据验证**: 建议在合约中验证返回的数据是否合理

## 许可证

MIT License

## 数据清理

### 清理 Chainlink Jobs (推荐)

如果只想删除 Chainlink Jobs 和数据库,但保留区块链数据和已部署合约:

```bash
./clean-jobs.sh
```

**删除内容:**
- Chainlink Jobs 和配置
- PostgreSQL 数据库

**保留内容:**
- Geth 区块链数据
- 账户 keystore
- 已部署的合约

### 完全清理 (谨慎使用)

如果需要完全重置,删除所有数据:

```bash
./clean.sh
```

**删除内容:**
- Chainlink Jobs 和运行时数据
- PostgreSQL 数据库
- Geth 区块链数据
- Docker volumes
- 编译产物和部署记录

**保留内容:**
- 账户 keystore
- 配置文件
- 智能合约源码

