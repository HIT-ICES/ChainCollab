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
2. **后端服务**
   ```bash
   export PYTHONPATH="$PWD/.."  # 确保上层在 sys.path 中
   uvicorn newTranslator.service.api:app --reload --host 0.0.0.0 --port 9999
   ```
3. **前端面板**
   ```bash
   cd dashboard
   cp .env.example .env        # 设置 VITE_TRANSLATOR_API_BASE
   npm install
   npm run dev
   ```
4. **命令行生成**
   ```bash
   source newtranslator_env.sh
   nt-bpmn-to-b2c path/to/file.bpmn
   nt-go-gen && nt-go-build
   ```
