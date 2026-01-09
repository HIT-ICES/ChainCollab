# 编译和构建说明

## 环境要求

- Solidity 编译器 (solc) >= 0.8.19
- Python >= 3.8
- Web3.py

## 安装依赖

### 安装 Solidity 编译器

```bash
# Ubuntu/Debian
sudo add-apt-repository ppa:ethereum/ethereum
sudo apt-get update
sudo apt-get install solc

# macOS
brew tap ethereum/ethereum
brew install solidity

# 或使用 solc-select 管理多版本
pip install solc-select
solc-select install 0.8.19
solc-select use 0.8.19
```

### 安装 Python 依赖

```bash
pip install web3
```

## 编译步骤

### 1. 创建构建目录

```bash
cd geth_identity_contract
mkdir -p build
```

### 2. 编译合约

```bash
solc --optimize --bin --abi contracts/IdentityRegistry.sol -o build/
```

编译成功后，在 `build/` 目录下会生成：
- `IdentityRegistry.bin` - 合约字节码
- `IdentityRegistry.abi` - 合约ABI（应用程序二进制接口）

### 3. 验证编译结果

```bash
ls -l build/
# 应该看到两个文件：
# - IdentityRegistry.abi
# - IdentityRegistry.bin
```

## 编译选项说明

- `--optimize`: 启用优化器，减少合约字节码大小
- `--bin`: 生成二进制字节码
- `--abi`: 生成ABI文件
- `-o build/`: 指定输出目录

## 高级编译选项

如果需要更多信息，可以添加以下选项：

```bash
# 生成完整的编译输出
solc --optimize --bin --abi --asm --opcodes contracts/IdentityRegistry.sol -o build/

# 查看合约元数据
solc --metadata contracts/IdentityRegistry.sol

# 检查合约语法
solc --parse-only contracts/IdentityRegistry.sol
```

## Gas 优化

合约已经使用了以下优化技术：
- 使用 `string memory` 而非 `string calldata` 适当场景
- 合理使用 `storage` 和 `memory`
- 批量操作减少交易次数

如需进一步优化，可以：
1. 调整 solc 优化次数：`solc --optimize --optimize-runs 200 ...`
2. 考虑使用事件代替存储（查询场景）
3. 批量注册身份以减少 Gas 成本

## 常见问题

### Q: 编译时提示版本不匹配

A: 确保 solc 版本 >= 0.8.19:
```bash
solc --version
```

### Q: 找不到 solc 命令

A: 检查是否已正确安装，或使用完整路径：
```bash
/usr/bin/solc --version
```

### Q: 生成的 bin 文件很大

A: 这是正常的，IdentityRegistry 包含较多功能。可以通过 `--optimize` 减小大小。

## 下一步

编译完成后，请参考：
- [DEPLOYMENT.md](DEPLOYMENT.md) - 部署合约到网络
- [INTEGRATION.md](INTEGRATION.md) - 集成到Django项目
