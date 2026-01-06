# Solidity Contract JSON Converter

将 `solc --combined-json abi,bin` 生成的标准JSON格式转换为Firefly兼容的合约部署格式。

## 输出格式

转换后的JSON包含三个字段:

```json
{
  "contract": "字节码(bytecode)",
  "definition": [ABI数组],
  "input": []
}
```

**注意**: `input` 字段是构造函数的**参数值**数组，不是参数定义。这符合Firefly的要求。

## 使用方法

### 基本用法

```bash
# 不带构造函数参数（input为空数组）
python3 convert_contract.py simple_storage.json -o output.json

# 指定合约名称
python3 convert_contract.py simple_storage.json -c WorkflowContract

# 带构造函数参数
python3 convert_contract.py simple_storage.json -c WorkflowContract \
  -p '["0x1234567890123456789012345678901234567890"]'

# 多个构造函数参数
python3 convert_contract.py simple_storage.json -c MyContract \
  -p '["0x123...", 100, "string_value", true]'

# 输出紧凑格式（不美化）
python3 convert_contract.py simple_storage.json --compact
```

### 实际示例

假设你的合约有一个构造函数 `constructor(address oracleAddress)`:

```bash
# 转换并提供oracle地址
python3 convert_contract.py compiled.json -c WorkflowContract \
  -p '["0xYourOracleAddressHere"]' \
  -o deployable.json
```

### 批量转换示例

```bash
# 转换所有JSON文件（不带参数）
for file in *.json; do
    python3 convert_contract.py "$file" -o "converted_${file}"
done
```

### 集成到编译流程

```bash
# 1. 编译Solidity合约
solc --combined-json abi,bin -o output/ MyContract.sol

# 2. 转换格式（准备部署）
python3 convert_contract.py output/combined.json \
  -c MyContract \
  -p '["0xConstructorParam1", 123]' \
  -o deployable.json

# 3. 使用Firefly部署
# 现在可以使用 deployable.json 通过Firefly API部署合约
```

## 参数说明

- `input`: 输入的JSON文件（必需）
- `-o, --output`: 输出文件路径（可选，默认覆盖输入文件）
- `-c, --contract`: 要提取的合约名称（可选，默认提取第一个有字节码的合约）
- `-p, --params`: 构造函数参数值，JSON数组格式（可选，默认为空数组）
- `--compact`: 输出紧凑JSON，不美化格式（可选）

## 构造函数参数格式

`-p` 参数需要提供JSON数组格式的构造函数参数值：

| 参数类型 | 示例 |
|---------|------|
| address | `'["0x1234567890123456789012345678901234567890"]'` |
| uint256 | `'[123]'` |
| string | `'["hello world"]'` |
| bool | `'[true]'` |
| 多个参数 | `'["0x123...", 100, "test", false]'` |

**重要**: 在bash中使用单引号包裹JSON，避免特殊字符被解析。

## 注意事项

1. **Firefly兼容性**: `input` 字段必须是构造函数参数的**值**数组，而非参数定义
2. **合约选择**: 如果文件中有多个合约，建议使用 `-c` 参数指定合约名称
3. **接口过滤**: 脚本会自动跳过没有字节码的接口（interface）
4. **参数类型**: Firefly会根据ABI自动验证参数类型，确保提供正确的值
5. **编码**: 所有文件使用UTF-8编码

## 常见错误

### FF10111错误
```
Error from ethereum connector: FF22034: Unable to parse input...
```
**原因**: `input` 字段包含了参数定义而不是参数值
**解决**: 使用此脚本转换，确保 `input` 是空数组或包含实际参数值

### 示例对比

❌ **错误格式** (参数定义):
```json
{
  "input": [
    {"name": "oracleAddress", "type": "address", "internalType": "address"}
  ]
}
```

✅ **正确格式** (参数值):
```json
{
  "input": ["0x1234567890123456789012345678901234567890"]
}
```

或者不带构造函数参数:
```json
{
  "input": []
}
```
