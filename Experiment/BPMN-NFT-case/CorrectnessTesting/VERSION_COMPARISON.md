# 脚本版本对比与推荐

## 📊 三个版本功能对比

| 功能特性 | main.py | main_config.py | main_enhanced.py ⭐ |
|---------|---------|----------------|---------------------|
| **配置方式** | 硬编码在脚本中 | 读取JSON配置文件 | 读取JSON配置文件 |
| **控制台输出** | ✓ 基本日志 | ✓ 基本日志 | ✓ 详细日志 |
| **JSON结果输出** | ✗ 无 | ✗ 无 | ✓ **详细结果** |
| **步骤状态记录** | ✗ 仅显示成功/失败 | ✗ 仅显示成功/失败 | ✓ **每步都有状态** |
| **时间戳** | ✗ 无 | ✗ 无 | ✓ **任务和步骤级别** |
| **错误信息** | ✓ 控制台显示 | ✓ 控制台显示 | ✓ **记录到JSON** |
| **结果提取** | ✗ 不提取 | ✗ 不提取 | ✓ **从operation提取** |
| **统计摘要** | ✗ 无 | ✗ 无 | ✓ **成功/失败/错误计数** |
| **历史记录** | ✗ 无 | ✗ 无 | ✓ **支持多次执行追加** |
| **适用场景** | 快速测试 | 生产环境 | **自动化测试/CI/CD** |
| **文件大小** | 17KB | 11KB | 15KB |

## ⭐ 推荐使用 main_enhanced.py

### 为什么推荐？

1. **完整的结果收集** - 像参考的NoiseExperiment一样，收集每个步骤的详细结果
2. **便于分析** - JSON格式便于后续分析、报告生成和自动化处理
3. **可追溯性** - 完整的时间戳和执行历史
4. **CI/CD友好** - 输出结构化数据，便于集成到自动化流程
5. **调试方便** - 详细记录每一步的结果和错误信息

### 结果输出特点

与 NoiseExperiment/main.py 类似，main_enhanced.py 会：

```python
# NoiseExperiment 的结果结构
{
    "task_name": "...",
    "results": [
        {"path": [...], "results": "...", "tag": 0}  # 0=pass, 1=error, 2=fail
    ],
    "count": "succeed:X,error:Y,fail:Z"
}

# main_enhanced.py 的结果结构（更详细）
{
    "task_name": "...",
    "timestamp": "...",
    "instance_id": "...",
    "steps_executed": [
        {
            "step_number": 1,
            "step_id": "...",
            "status": "success",  # success/failed/error
            "result": "...",      # 从operation提取的实际结果
            "error": null,
            "timestamp": "..."
        }
    ],
    "status": "success",  # success/failed/error
    "error_message": null
}
```

## 📝 快速使用指南

### 1. 准备配置文件

```bash
cp config_runtime.json.template config_runtime.json
nano config_runtime.json  # 编辑配置
```

### 2. 运行增强版脚本

```bash
# 基本用法
python3 main_enhanced.py config_runtime.json

# 指定输出文件
python3 main_enhanced.py config_runtime.json my_result.json

# 后台运行并记录日志
nohup python3 main_enhanced.py config_runtime.json > run.log 2>&1 &
```

### 3. 查看结果

```bash
# 查看最新执行结果
cat execution_result.json | jq '.[0]'

# 查看执行摘要
cat execution_result.json | jq '.[0] | {
  status: .status,
  instance_id: .instance_id,
  total_steps: (.steps_executed | length),
  successful: (.steps_executed | map(select(.status == "success")) | length)
}'

# 查找失败的步骤
cat execution_result.json | jq '.[0].steps_executed[] | select(.status != "success")'
```

### 4. 多次执行和历史记录

```bash
# 第一次执行
python3 main_enhanced.py config_runtime.json test_results.json

# 第二次执行（结果会追加）
python3 main_enhanced.py config_runtime.json test_results.json

# 查看所有历史记录
cat test_results.json | jq '. | length'  # 查看执行次数
cat test_results.json | jq '.[] | {timestamp, status}'  # 查看所有执行的时间和状态
```

## 🔄 与 NoiseExperiment 的对比

| 特性 | NoiseExperiment | main_enhanced.py |
|-----|----------------|------------------|
| **用途** | 带噪音的鲁棒性测试 | 清洁路径验证 |
| **路径生成** | 随机生成多条路径（add/remove/switch） | 固定的正确路径 |
| **结果标记** | tag: 0/1/2 (pass/error/fail) | status: success/failed/error |
| **结果输出** | JSON + 文本日志 | JSON + 控制台日志 |
| **统计方式** | passNum/errorNum/failNum | 步骤级别统计 |
| **时间记录** | 无 | 每步都有时间戳 |
| **详细程度** | 路径级别 | 步骤级别（更细粒度） |

## 💡 使用建议

### 什么时候用哪个版本？

| 场景 | 推荐版本 | 理由 |
|-----|---------|------|
| **快速手动测试** | main.py | 配置简单，快速验证 |
| **生产环境单次验证** | main_config.py | 配置灵活，输出清晰 |
| **自动化测试** | main_enhanced.py ⭐ | 结果可追溯，便于分析 |
| **CI/CD集成** | main_enhanced.py ⭐ | 结构化输出，易于解析 |
| **批量测试** | main_enhanced.py ⭐ | 支持历史记录 |
| **报告生成** | main_enhanced.py ⭐ | 完整的数据支持 |

### 结合使用建议

```bash
# 1. 先用可视化工具查看路径
python3 visualize_path.py

# 2. 用main.py快速测试配置是否正确
python3 main.py

# 3. 确认无误后，用main_enhanced.py进行正式测试
python3 main_enhanced.py config_runtime.json official_test.json

# 4. 分析结果
cat official_test.json | jq '.'
```

## 📈 进一步扩展

基于 main_enhanced.py，可以很容易扩展：

1. **生成HTML报告**
```python
# 读取JSON结果，生成HTML报告
import json
with open('execution_result.json') as f:
    results = json.load(f)
    # 生成HTML...
```

2. **集成到测试框架**
```python
# pytest 集成示例
def test_supply_chain():
    result = run_clean_path(config)
    assert result['status'] == 'success'
    assert len(result['steps_executed']) == 17
```

3. **性能分析**
```python
# 分析每步执行时间
from datetime import datetime
for step in result['steps_executed']:
    # 计算时间差...
```

## 🎯 总结

- ✅ **main_enhanced.py** 是最完整的版本，推荐用于自动化测试和生产环境
- ✅ 完全兼容配置文件格式
- ✅ 输出格式参考了NoiseExperiment，但更加详细
- ✅ 从operation中提取真实的执行结果
- ✅ 支持多次执行历史记录
- ✅ 便于后续分析和报告生成
