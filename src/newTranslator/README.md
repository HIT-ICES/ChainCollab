# newTranslator 模块结构

```
newTranslator/
├── generator/          # BPMN/DMN 解析与链码生成核心逻辑（Python package）
├── service/            # FastAPI 服务层，包装 generator 对外提供 REST
├── dashboard/          # React + Vite + Material/AWS 风格前端工作台
├── CodeGenerator/      # textX 目标（Go / Solidity）
├── DSL/                # DSL 语法定义
├── newtranslator_env.sh
└── todo.md
```

## 目录职责

- `generator/`：封装 `GoChaincodeTranslator`、BPMN/DMN 解析器、资源等；以 `newTranslator.generator.*` 形式对外提供 API。
- `service/`：`api.py` 暴露 FastAPI 接口，所有 handler 仅调用 generator 模块；运行方式 `python -m newTranslator.service.api` 或 `uvicorn newTranslator.service.api:app --reload --app-dir src`.
- `dashboard/`：面板端调用 service 提供的 REST 接口，支持 BPMN 上传、链码/FFI 生成、元数据洞察、DMN 决策分析等。
- `newtranslator_env.sh`：命令行工具集，`nt-bpmn-to-b2c` 已更新为引用 `generator/bpmn_to_dsl.py`。

> 旧 `DSLGenerator` 目录已退役，仅保留历史 README / requirements。

## 快速上手

1. **激活虚拟环境**
   ```bash
   cd src/newTranslator
   source .venv/bin/activate  # 如需
   ```
2. **安装依赖（留痕迹）**
   ```bash
   pip install -r requirements.txt
   # 安装 textX 语言与生成器（本地可迁移）
   pip install -e DSL/B2CDSL
   pip install -e CodeGenerator/b2cdsl-go
   pip install -e CodeGenerator/b2cdsl-solidity
   ```
3. **后端服务**
   ```bash
   export PYTHONPATH="$PWD/.."  # 确保上层在 sys.path 中
   uvicorn newTranslator.service.api:app --reload --host 0.0.0.0 --port 9999
   ```
4. **前端面板**
   ```bash
   cd dashboard
   cp .env.example .env        # 设置 VITE_TRANSLATOR_API_BASE
   npm install
   npm run dev
   ```
5. **命令行生成**
   ```bash
   source newtranslator_env.sh
   nt-bpmn-to-b2c path/to/file.bpmn
   nt-go-gen && nt-go-build
   ```

## 迁移与可移植性说明

- `newtranslator_env.sh` 不再绑定绝对路径，使用脚本所在目录自动定位项目根。
- DSL 与生成器均通过 `pip install -e` 安装，确保可迁移、可复现。
- 可选依赖：
  - `pyvis`：子图 HTML 可视化
  - `solc` / `solhint`：Solidity 编译与语法检查
  - `graphviz`：`nt-b2c-view` 生成 PNG

## 命令速览（每条一行）

- `nt-bootstrap` — 一键创建/安装本地环境（.venv + 依赖）; 例：`source newtranslator_env.sh && nt-bootstrap`
- `nt-clean-env` — 清理本地虚拟环境; 例：`source newtranslator_env.sh && nt-clean-env`
- `nt-bpmn-to-b2c` — BPMN → B2C DSL; 例：`source newtranslator_env.sh && nt-bpmn-to-b2c ./build/bpmn/BikeRental.bpmn ./build/b2c/BikeRental.b2c`
- `nt-go-gen` — B2C → Go 链码; 例：`source newtranslator_env.sh && nt-go-gen ./build/b2c/BikeRental.b2c`
- `nt-go-fmt` — 格式化 Go 输出; 例：`source newtranslator_env.sh && nt-go-fmt`
- `nt-go-build` — 构建 Go 链码; 例：`source newtranslator_env.sh && nt-go-build`
- `nt-go-clean` — 清理 Go 产物; 例：`source newtranslator_env.sh && nt-go-clean`
- `nt-sol-gen` — B2C → Solidity 合约; 例：`source newtranslator_env.sh && nt-sol-gen ./build/b2c/BikeRental.b2c`
- `nt-sol-fmt` — Solidity 语法检查（solhint）; 例：`source newtranslator_env.sh && nt-sol-fmt`
- `nt-sol-build` — Solidity 编译（solc）; 例：`source newtranslator_env.sh && nt-sol-build`
- `nt-sol-clean` — 清理 Solidity 产物; 例：`source newtranslator_env.sh && nt-sol-clean`
- `nt-b2c-view` — 导出 DSL 结构图（DOT/PNG）; 例：`source newtranslator_env.sh && nt-b2c-view ./build/b2c/BikeRental.b2c`
