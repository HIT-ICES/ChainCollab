# 一键脚本使用说明

本项目提供了 7 个便捷的 Shell 脚本,帮助你快速启动、管理、部署和清理 Chainlink Oracle 服务。

## 📋 脚本列表

### 1. start.sh - 一键启动服务

自动执行 README 中的所有启动步骤。

**功能**:
- ✅ 检查 Docker 环境
- ✅ 停止旧服务
- ✅ 启动所有 Docker 服务
- ✅ 等待服务就绪
- ✅ 检查服务状态
- ✅ 显示访问信息

**使用方法**:
```bash
./start.sh
```

**输出示例**:
```
================================================
  Chainlink Oracle 一键启动脚本
================================================

[1/6] 检查 Docker 环境...
✅ Docker 环境正常

[2/6] 停止旧服务（如果存在）...
✅ 旧服务已停止

[3/6] 启动 Docker 服务...
✅ 服务启动成功

[4/6] 等待服务初始化...
✅ Geth 节点已就绪
✅ Chainlink 节点已就绪

[5/6] 检查服务状态...
✅ Geth 账户存在
✅ Chainlink 已连接到 Chain ID 3456

[6/6] 部署信息

🎉 Chainlink Oracle 启动成功！
```

---

### 2. status.sh - 查看服务状态

实时查看所有服务的运行状态和关键信息。

**功能**:
- 📦 Docker 服务状态
- ⛓️ Geth 节点状态 (区块高度、挖矿状态、连接数)
- 🔗 Chainlink 节点状态 (UI 可用性、链连接)
- 🗄️ PostgreSQL 状态
- 📋 最近日志预览

**使用方法**:
```bash
./status.sh
```

**输出示例**:
```
================================================
  Chainlink Oracle 服务状态
================================================

📦 Docker 服务状态:
NAME                    STATUS              PORTS
chainlink-node          Up 5 minutes        0.0.0.0:6688->6688/tcp
chainlink-postgres-1    Up 5 minutes        5432/tcp
<mybootnode-container>  Up 5 minutes        0.0.0.0:8545->8545/tcp

⛓️ Geth 节点状态:
  状态: 运行中
  区块高度: 12345
  挖矿状态: 进行中
  连接节点数: 0

🔗 Chainlink 节点状态:
  状态: 运行中
  UI 地址: http://localhost:6688
  链连接: 已连接 (Chain ID: 3456)

🗄️ PostgreSQL 状态:
  状态: 运行中
  端口: 5432
```

---

### 3. unlock-account.sh - 解锁账户

快速解锁 Geth 部署账户,部署合约前必须执行。

**功能**:
- 🔓 永久解锁部署账户
- 💰 显示账户余额
- ℹ️ 显示账户信息

**使用方法**:
```bash
./unlock-account.sh
```

**输出示例**:
```
================================================
  Geth 账户解锁脚本
================================================

正在解锁账户: 0x7e9519A329908320829F4a747b8Bac06cF0955cb

✅ 账户解锁成功！

账户信息:
  地址: 0x7e9519A329908320829F4a747b8Bac06cF0955cb

查询账户余额...
  余额: 1000000 ETH

现在可以部署合约了:
  node scripts/deploy-contract.js
```

---

## 🎯 典型工作流程

### 第一次启动

```bash
# 1. 启动所有服务
./start.sh

# 2. 等待服务完全启动 (约 30 秒)

# 3. 访问 Chainlink UI
open http://localhost:6688

# 4. 如需部署合约
./unlock-account.sh
node scripts/deploy-contract.js
```

### 日常使用

```bash
# 查看服务状态
./status.sh

# 重启服务
docker-compose restart

# 查看日志
docker logs chainlink-node -f

# 停止服务
docker-compose down
```

## ⚠️ 注意事项

1. **首次启动**: 首次启动可能需要 30-60 秒等待服务初始化
2. **账户解锁**: 每次重启 Geth 节点后需要重新解锁账户
3. **日志查看**: 如果服务启动失败,使用 `docker logs` 查看详细日志
4. **端口占用**: 确保 6688、8545、5432 端口未被占用

## 🐛 故障排除

### start.sh 失败

```bash
# 查看错误日志
docker-compose logs

# 清理并重新启动
docker-compose down -v
./start.sh
```

### 服务无响应

```bash
# 检查服务状态
./status.sh

# 重启特定服务
docker-compose restart chainlink-node
docker-compose restart mybootnode
```

### 账户解锁失败

```bash
# 检查 Geth 是否运行
docker ps | grep mybootnode

# 手动尝试连接
docker exec -it <mybootnode-container> geth attach /root/.ethereum/geth.ipc
```

## 📚 相关文档

- [README.md](README.md) - 完整项目文档
- [Chainlink 官方文档](https://docs.chain.link/)
- [Docker Compose 文档](https://docs.docker.com/compose/)

---

💡 **提示**: 建议将这三个脚本添加到你的 PATH 或创建别名以便快速访问！

---

### 4. compile.sh - 编译合约

编译 Solidity 智能合约生成 ABI 和字节码。

**功能**:
- 🔍 检查 solc 编译器
- 📝 编译 simple.sol 合约
- 💾 生成 deployment/compiled.json 文件
- ℹ️ 显示合约信息

**使用方法**:
```bash
./compile.sh
```

**输出示例**:
```
================================================
  合约编译脚本
================================================

Solidity 版本:
solc, the solidity compiler commandline interface

正在编译 simple.sol...
✅ 合约编译成功

生成的文件:
  deployment/compiled.json - 合约 ABI 和字节码

合约信息:
  合约数量: 15
  合约名称: contracts/simple.sol:MyChainlinkRequester

现在可以部署合约了:
  ./unlock-account.sh
  node scripts/deploy-contract.js
```

**前置条件**:
- 已安装 solc 编译器
- 已安装 Node.js 依赖 (`npm install`)

---

### 5. deploy.sh - 完整部署流程 ⭐

自动完成编译、解锁、部署的完整流程,最推荐使用!

**功能**:
- 📝 自动编译合约
- 🔓 自动解锁账户
- 🚀 自动部署合约
- 💾 保存部署信息到 deployment/deployment.json
- ℹ️ 显示下一步操作提示

**使用方法**:
```bash
./deploy.sh
```

**输出示例**:
```
================================================
  完整部署流程
================================================

[1/3] 编译合约...
✅ 合约编译完成

[2/3] 解锁账户...
✅ 账户解锁完成

[3/3] 部署合约...
开始部署 MyChainlinkRequester 合约...
部署账户: 0x7e9519a329908320829f4a747b8bac06cf0955cb
账户余额: 1000000 ETH

部署参数:
- LINK Token: 0xe640cdaf5df426bfaa1664e47a91f3106db07792
- Oracle: 0x75cd7081c3224a11b2b013faed8606acd4cec737
- Job ID: 0x85666de4e963484fb3423eaa583733ad...
- Fee: 0.1 LINK

正在部署合约...
✅ 合约部署成功!
合约地址: 0xABCDEF...

================================================
🎉 部署流程完成！
================================================
```

**前置条件**:
- 服务已启动 (`./start.sh`)
- 已安装 solc 和 Node.js

---

## 🎯 推荐工作流程

### 完整流程 (第一次使用)

```bash
# 1. 启动所有服务
./start.sh

# 2. 等待服务完全启动 (约 30 秒)
sleep 30

# 3. 部署合约 (包含编译、解锁、部署)
./deploy.sh

# 4. 访问 Chainlink UI 查看
open http://localhost:6688
```

### 快速启动 (日常使用)

```bash
# 启动服务
./start.sh

# 查看状态
./status.sh

# 如需重新部署合约
./deploy.sh
```

### 分步操作 (调试用)

```bash
# 1. 启动服务
./start.sh

# 2. 编译合约
./compile.sh

# 3. 解锁账户
./unlock-account.sh

# 4. 手动部署
node scripts/deploy-contract.js

# 5. 查看状态
./status.sh
```

---

## 📊 完整脚本对比表

| 脚本 | 用途 | 前置条件 | 推荐场景 | 执行时间 |
|------|------|----------|----------|----------|
| **start.sh** | 启动所有服务 | Docker | 每次使用前必须运行 | ~1分钟 |
| **status.sh** | 查看服务状态 | 服务已启动 | 检查服务健康状态 | ~5秒 |
| **unlock-account.sh** | 解锁部署账户 | Geth 运行中 | 部署合约前 | ~5秒 |
| **compile.sh** | 编译合约 | solc | 修改合约代码后 | ~10秒 |
| **deploy.sh** ⭐ | 完整部署流程 | 服务已启动 | **首选部署方式** | ~1分钟 |
| **clean-jobs.sh** | 清理 Jobs | - | 重置 Jobs 配置 | ~30秒 |
| **clean.sh** ⚠️ | 完全清理 | - | 完全重置环境 | ~1分钟 |

---

## 🔧 脚本依赖

### 系统依赖

- **Docker & Docker Compose**: 必需,用于运行服务
- **Node.js**: 必需,用于部署脚本
- **solc**: 推荐安装原生编译器,脚本优先使用本机 `solc`
- **jq**: 格式化 JSON 输出,可选但推荐

### 安装依赖

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install docker.io docker-compose nodejs npm solc jq

# 如果系统仓库没有 solc，可使用 Python 安装 solc-select
python3 -m pip install solc-select
solc-select install 0.8.19
solc-select use 0.8.19

# macOS
brew install docker docker-compose node solidity jq

# Node.js 依赖
npm install
```

补充说明:

- 不推荐 `npm install -g solc`, 这通常提供的是 `solcjs`, 可能不支持项目脚本需要的 `--evm-version`、`--via-ir` 等参数
- 如果本机 `solc` 不可用, `compile.sh` 会回退到 Docker 版 Solidity 编译器

---

## ⚠️ 重要提示

1. **执行顺序**: 必须先运行 `./start.sh` 启动服务,再运行其他脚本
2. **账户解锁**: 每次重启 Geth 后需要重新解锁账户
3. **编译需求**: 部署前必须先编译合约 (deploy.sh 会自动编译)
4. **合约参数**: 部署脚本使用的是已部署的 LINK Token 和 Operator 地址

---


## 🧹 数据清理脚本

### 6. clean-jobs.sh - 清理 Jobs (推荐)

只清理 Chainlink Jobs 和数据库,保留区块链数据和已部署合约。

**功能**:
- 🗑️ 删除 Chainlink Jobs
- 🗄️ 清空 PostgreSQL 数据库
- 💾 保留 Geth 区块链数据
- 🔑 保留账户 keystore
- 📜 保留已部署的合约

**使用方法**:
```bash
./clean-jobs.sh
```

**使用场景**:
- Job 配置错误需要重新创建
- 数据库损坏需要重置
- 测试不同的 Job 配置
- 保留区块链状态但重置 Chainlink

**输出示例**:
```
================================================
  Chainlink Jobs 清理脚本
================================================

这将删除:
  - Chainlink Jobs 和配置
  - PostgreSQL 数据库

保留:
  - Geth 区块链数据
  - 账户 keystore
  - 已部署的合约

确定要继续吗? (y/n): y

[1/3] 停止服务...
✅ 服务已停止

[2/3] 删除 PostgreSQL volume...
✅ 数据库已清理

[3/3] 清理 Chainlink 运行时数据...
✅ Chainlink 运行时数据已删除

🎉 清理完成！
```

---

### 7. clean.sh - 完全清理 ⚠️

**警告**: 彻底删除所有数据,包括区块链、数据库、Jobs 等。

**功能**:
- 🗑️ 删除所有 Chainlink 数据
- 🗄️ 删除 PostgreSQL 数据库
- ⛓️ 删除 Geth 区块链数据
- 🐳 删除 Docker volumes
- 📝 删除编译产物和部署记录
- 🔑 保留账户 keystore
- ⚙️ 保留配置文件

**使用方法**:
```bash
./clean.sh
```

**使用场景**:
- 完全重新开始
- 区块链数据损坏
- 切换到新的测试环境
- 磁盘空间清理

**输出示例**:
```
================================================
  ⚠️  Chainlink Oracle 完全清理脚本
================================================

警告: 这将删除以下所有数据:

  - Chainlink Jobs 和配置
  - PostgreSQL 数据库
  - Geth 区块链数据
  - Docker volumes
  - 编译产物和部署记录

此操作不可恢复!

确定要继续吗? (输入 'yes' 确认): yes

[1/6] 停止所有容器...
✅ 容器已停止

[2/6] 删除容器、网络和 volumes...
✅ 容器和 volumes 已删除

[3/6] 清理 Geth 区块链数据...
✅ Geth 区块链数据已删除
✅ Geth 其他数据已清理 (keystore 保留)

[4/6] 清理 Chainlink 节点数据...
✅ Chainlink 运行时数据已删除

[5/6] 清理编译和部署产物...
  - 已删除 deployment/compiled.json
  - 已删除 deployment/deployment.json
✅ 编译产物已清理

[6/6] 清理 Docker 系统缓存...
是否清理 Docker 系统缓存? (y/n): y
✅ Docker 缓存已清理

🎉 清理完成！
```

---

## 🎯 清理场景对比

| 场景 | 使用脚本 | 保留内容 | 删除内容 |
|------|----------|----------|----------|
| **重新配置 Job** | `clean-jobs.sh` | 区块链、合约、keystore | Jobs、数据库 |
| **测试新 Job** | `clean-jobs.sh` | 区块链、合约、keystore | Jobs、数据库 |
| **数据库损坏** | `clean-jobs.sh` | 区块链、合约、keystore | Jobs、数据库 |
| **区块链损坏** | `clean.sh` | keystore、配置 | 所有数据 |
| **完全重置** | `clean.sh` | keystore、配置 | 所有数据 |
| **切换环境** | `clean.sh` | keystore、配置 | 所有数据 |

---

## 🔄 完整重置流程

### 场景 1: 只重置 Jobs

```bash
# 1. 清理 Jobs
./clean-jobs.sh

# 2. 重新启动
./start.sh

# 3. 重新创建 Job
node scripts/create-job.js
```

### 场景 2: 完全重置

```bash
# 1. 完全清理
./clean.sh

# 2. 重新启动
./start.sh

# 3. 重新部署一切
node scripts/deploy-chainlink.js  # 部署 LINK Token 和 Operator
node scripts/create-job.js         # 创建 Job
./deploy.sh                        # 部署客户端合约
```

---

## ⚠️ 清理注意事项

1. **备份重要数据**: 清理前确保备份重要的配置和密钥
2. **确认操作**: 两个脚本都需要确认才会执行
3. **keystore 安全**: 账户密钥始终会被保留
4. **配置保留**: config.toml 和 secrets.toml 不会被删除
5. **合约地址**: 清理后需要重新部署合约,地址会改变

---
