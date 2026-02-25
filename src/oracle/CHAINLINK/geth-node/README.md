# Geth 节点配置

此目录包含 Geth 以太坊节点的所有配置文件和数据。

## 📁 目录结构

```
geth-node/
├── Dockerfile          # Geth 节点 Docker 镜像
├── bootnode.key        # Bootnode 密钥
├── genesis.json        # 创世区块配置
├── datadir/            # Geth 数据目录
│   └── keystore/       # 账户密钥存储
└── README.md           # 本文档
```

## 📝 文件说明

### Dockerfile
定义 Geth 节点的 Docker 镜像构建配置。基于官方 Geth 镜像。

### bootnode.key
Bootnode 节点的私钥文件，用于 P2P 网络发现。

### genesis.json
创世区块配置文件，包含：
- Chain ID: 3456
- 预分配账户: `0x365Acf78C44060CAF3A4789D804Df11E3B4AA17d` (10000 ETH)
- 共识算法: Ethash (PoW)
- 初始难度: 1

### datadir/keystore/
存储 Geth 账户的加密私钥文件。

**当前账户**:
- 地址: `0x7e9519A329908320829F4a747b8Bac06cF0955cb`
- 密码: `password123`
- 用途: 部署合约和挖矿

## ⚙️ 节点配置

### 网络设置
- **Network ID**: 3456
- **Chain ID**: 3456
- **RPC 端口**: 8545
- **P2P 端口**: 30303
- **挖矿**: 启用
- **挖矿地址**: `0x365acf78c44060caf3a4789d804df11e3b4aa17d`

### 启用的功能
- HTTP RPC
- WebSocket RPC
- 挖矿（单线程）
- 零 Gas 价格
- 不安全解锁（仅开发环境）

### API 接口
- admin
- eth
- miner
- web3
- personal
- net
- txpool

## 🚀 使用方式

### 通过 Docker Compose 启动

```bash
# 启动 Geth 节点
docker-compose up -d mybootnode

# 查看日志
docker logs <mybootnode-container> -f

# 停止节点
docker-compose stop mybootnode
```

### 连接到 Geth 控制台

```bash
# 进入容器
docker exec -it <mybootnode-container> sh

# 连接到 Geth 控制台
geth attach /root/.ethereum/geth.ipc
```

### 常用 Geth 命令

```javascript
// 查看账户
eth.accounts

// 查看余额
web3.fromWei(eth.getBalance(eth.accounts[0]), 'ether')

// 解锁账户
personal.unlockAccount(eth.accounts[0], 'password123', 0)

// 查看挖矿状态
eth.mining

// 查看区块高度
eth.blockNumber

// 查看节点信息
admin.nodeInfo
```

## 🔒 安全注意事项

⚠️ **警告**: 此配置仅用于开发环境！

生产环境请注意：
1. 使用强密码保护账户
2. 不要暴露 RPC 端口到公网
3. 启用防火墙
4. 禁用 `--allow-insecure-unlock`
5. 备份私钥文件
6. 使用硬件钱包或更安全的密钥管理方案

## 📊 预分配账户

创世区块预分配了一个账户：

```
地址: 0x365Acf78C44060CAF3A4789D804Df11E3B4AA17d
余额: 10,000 ETH
```

**注意**: 此账户的私钥未导入到 keystore，余额会通过挖矿转移到其他账户。

## 🔄 数据持久化

`datadir/` 目录通过 Docker 卷挂载，数据会持久化存储：
- 区块链数据
- 账户密钥
- 节点状态

删除容器不会丢失数据，除非手动删除 `datadir/` 目录。

## 🐛 故障排除

### 节点无法启动
```bash
# 检查容器日志
docker logs <mybootnode-container>

# 检查端口占用
netstat -tuln | grep 8545
```

### WebSocket 连接失败
确保启动参数包含：
```
--ws
--ws.addr=0.0.0.0
--ws.port=8545
--ws.origins=*
```

### 账户无法解锁
```bash
# 在容器内执行
docker exec <mybootnode-container> geth --exec \
  "personal.unlockAccount('0x7e9519A329908320829F4a747b8Bac06cF0955cb', 'password123', 0)" \
  attach /root/.ethereum/geth.ipc
```

## 🔗 相关链接

- [Geth 官方文档](https://geth.ethereum.org/docs)
- [项目主 README](../README.md)
- [Docker Compose 配置](../docker-compose.yml)

---

**最后更新**: 2026-01-09
**Chain ID**: 3456
**Network ID**: 3456
