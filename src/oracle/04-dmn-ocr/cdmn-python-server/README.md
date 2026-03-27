# CDMN Python Server

一个基于 Python Flask 和 cdmn 库的 DMN（Decision Model and Notation）决策引擎服务器，用于 Chainlink Oracle 集成。

## 功能特点

- 提供 RESTful API 接口
- 支持 DMN 1.3 决策表评估
- 内置结果缓存机制
- 与 Chainlink OCR 集成
- 轻量级 Flask 框架
- Docker 容器化部署

## API 接口

### 1. 健康检查

**GET /api/dmn/health**

检查服务器状态。

响应：
```json
{
  "status": "ok",
  "timestamp": 1706598000000,
  "service": "CDMN Decision Engine",
  "version": "1.0.0"
}
```

### 2. 评估决策

**POST /api/dmn/evaluate**

执行 DMN 决策。

请求体：
```json
{
  "dmnContent": "<DMN XML 内容>",
  "decisionId": "决策ID",
  "inputData": {
    "变量名": 值
  }
}
```

响应：
```json
{
  "success": true,
  "result": [决策结果列表],
  "decisionId": "决策ID",
  "timestamp": 1706598000000
}
```

### 3. 计算并缓存

**POST /api/dmn/calc**

执行 DMN 决策并缓存结果（用于 OCR 观测）。

请求体：
```json
{
  "requestId": "请求ID（可选）",
  "dmnContent": "<DMN XML 内容>",
  "decisionId": "决策ID",
  "inputData": {...}
}
```

响应：
```json
{
  "ok": true,
  "requestId": "请求ID",
  "value": [决策结果列表],
  "raw": "原始JSON结果",
  "hash": "SHA3-256哈希",
  "hashDec": "十进制哈希值",
  "updatedAt": 1706598000000
}
```

### 4. 获取最新结果

**GET /api/dmn/latest**

获取最近一次缓存结果（用于 OCR 观测）。

参数：
- requireReady (可选): 是否要求结果已准备好 (1 或 true 要求准备好)

响应：
```json
{
  "ok": true,
  "ready": true,
  "value": [决策结果列表],
  "raw": "原始JSON结果",
  "hash": "SHA3-256哈希",
  "hashDec": "十进制哈希值",
  "requestId": "请求ID",
  "updatedAt": 1706598000000
}
```

### 5. 按哈希获取结果

**GET /api/dmn/by-hash?hash=...**

按哈希值获取原始结果（用于 OCR 写回对齐）。

响应：
```json
{
  "ok": true,
  "raw": "原始JSON结果",
  "hash": "SHA3-256哈希",
  "hashDec": "十进制哈希值",
  "updatedAt": 1706598000000
}
```

### 6. 确认并清除缓存

**POST /api/dmn/ack**

OCR 写回链上后确认并清理缓存。

请求体：
```json
{
  "requestId": "请求ID（可选）",
  "aggregatorRoundId": 12,
  "answer": "123",
  "txHash": "0x...",
  "blockTimestampMs": 1706598000000
}
```

响应：
```json
{
  "ok": true,
  "clearedLatest": true,
  "removedByRequestId": false
}
```

### 7. 获取决策信息

**POST /api/dmn/input-info**

获取 DMN 决策的输入信息。

请求体：
```json
{
  "dmnContent": "<DMN XML 内容>"
}
```

响应：
```json
{
  "success": true,
  "inputs": [输入信息列表],
  "timestamp": 1706598000000
}
```

## 快速开始

### 1. 安装依赖

```bash
cd /path/to/cdmn-python-server
pip install -r requirements.txt
```

### 2. 配置环境变量

编辑 `.env` 文件：

```
FLASK_APP=app.py
FLASK_ENV=development
FLASK_RUN_PORT=5000
FLASK_RUN_HOST=0.0.0.0

# OCR Listener Configuration
OCR_LISTENER_ENABLED=True
OCR_RPC_URL=http://localhost:8545
OCR_AGGREGATOR_ADDRESS=
```

### 3. 启动服务器

```bash
python app.py
```

服务器将在 http://localhost:5000 启动。

### 4. 使用 Docker 部署

```bash
# 构建镜像
docker build -t cdmn-python-server .

# 运行容器
docker run -p 5000:5000 --env-file .env cdmn-python-server
```

## 项目结构

```
cdmn-python-server/
├── app.py              # Flask 应用程序入口
├── cdmn.py             # DMN 引擎实现
├── requirements.txt    # Python 依赖包
├── .env                # 环境变量配置
├── Dockerfile          # Docker 容器配置
└── README.md           # 项目文档
```

## 依赖库

- Flask: Web 服务器框架
- Flask-CORS: 跨域请求支持
- cdmn: DMN 决策引擎
- web3: Ethereum 区块链访问
- python-dotenv: 环境变量加载
- jsonpickle: JSON 序列化

## 开发说明

服务器使用 CDMN 库来解析和评估 DMN 文件。目前支持 DMN 1.3 版本的决策表。

## 版权和许可

MIT License
