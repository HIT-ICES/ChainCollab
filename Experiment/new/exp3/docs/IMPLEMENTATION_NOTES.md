# Exp3 Implementation Notes

## 当前实现阶段

当前先实现 DSL 参考语义闭环，不直接调用 Fabric 或 Solidity。

本阶段约束：

- 只读取 `src/` 内现有文法和 DSL 生成结果，不修改源码
- 在 `exp3/` 目录内新增实验脚本、case 配置和输出
- 先验证 DSL 模拟执行是否能产出统一轨迹

当前 DSL 模拟器已覆盖：

- `start event`
- `message`
- `gateway`
- `businessrule`
- `oracletask` 的统一触发接口
- `enable`
- `disable`
- `set global`
- `choose`
- `parallel join`

当前不做：

- Fabric 链码调用
- Solidity 合约调用
- 三方差异比较
- 自动穷举路径搜索


## 目录约定

```text
exp3/
  README.md
  IMPLEMENTATION_NOTES.md
  cases/
    Hotel_Booking/
      case.json
    SupplyChain/
      case.json
  scripts/
    common.py
    parse_b2c.py
    dsl_simulator.py
    run_exp3.py
  outputs/
    ...
```


## 运行方式

在仓库根目录执行：

```bash
/root/code/ChainCollab/src/newTranslator/.venv/bin/python Experiment/new/exp3/scripts/run_exp3.py
```

只跑单个 case：

```bash
/root/code/ChainCollab/src/newTranslator/.venv/bin/python Experiment/new/exp3/scripts/run_exp3.py --case Hotel_Booking
```


## 路径输入格式

当前路径由 `case.json` 显式给定，每一步格式如下：

```json
{
  "type": "message|gateway|businessrule|oracletask|event",
  "element": "DSL element name",
  "payload": {},
  "outputs": {}
}
```

说明：

- `message` 步骤可通过 `payload` 写入与全局变量同名或归一化同名的字段
- `businessrule` / `oracletask` 步骤可通过 `outputs` 写入输出映射对应的全局变量
- `gateway` 步骤会读取当前全局变量并执行 `choose` 分支


## 当前样例

- `Hotel_Booking`
  - 覆盖 exclusive gateway 与 businessrule
- `SupplyChain`
  - 覆盖 parallel join 与 businessrule

每个 case 当前都包含：

- 1 条应被接受的代表性路径
- 1 条应被拒绝的非法路径


## 输出内容

当前生成到 `outputs/<case_name>/`：

- `paths.json`
- `dsl_model.json`
- `dsl_trace_<path>.json`
- `report.md`

汇总输出：

- `outputs/summary.json`
- `outputs/summary.md`


## 下一阶段

当 DSL 参考轨迹稳定后，下一步再补：

1. Fabric/Go 调用包装
2. Solidity/Geth 调用包装
3. 统一轨迹对齐与差异报告
