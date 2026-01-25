# BPMN-NFT Supply Chain Clean Path Runner

这是一个用于**按 JSON 配置自动执行 BPMN-NFT（SupplyChain）“clean path”**的 Python 脚本。它会：

- 从配置文件读取：合约 API 地址、BPMN ID、参与方身份、ERC 链码映射、执行路径（event/message/gateway/activity）
- 调用 `CreateInstance` 创建流程实例
- 通过 FireFly WebSocket 订阅监听 `InstanceCreated` 事件，获取真实 `InstanceID`
- 按 `execution_path` 顺序逐步执行 invoke，并轮询 operation 直到成功/失败
- 将完整执行过程写入结果 JSON（支持多次运行**追加写入**）

---

## 1. 目录与文件说明

- `main_enhanced.py`：主执行脚本（本项目入口）
- `config_example.json`：✅ **已验证的示例输入配置**
- `execution_result.json`：✅ **已验证的示例输出结果（一次运行的输出示例）**
- （默认）`config_runtime.json`：若运行时不传参，脚本会默认读取此文件（你可以把 `config_example.json` 复制一份改名为它）

---

## 2. 环境要求

- Python 3.8+（建议 3.10+）
- 能访问 FireFly API（HTTP）以及对应 WebSocket（脚本会自动从 API URL 推导 WS 地址）

安装依赖：

```bash
pip install requests websocket-client
```

> 说明：脚本使用 `requests` 进行 HTTP 调用，使用 `websocket-client` 监听 `InstanceCreated` 事件。

---

## 3. 快速开始（直接跑通示例）

用示例输入配置执行：

```bash
python main_enhanced.py config_example.json
```

脚本启动后会提示你按回车开始执行：

- 回车：开始 clean path 执行
- Ctrl+C：取消

执行完成后，结果会默认写入：`execution_result.json`（如果已存在，会把本次 run 追加进去）。

---

## 4. 命令行用法

脚本支持两个参数：

```bash
python main_enhanced.py [config_file] [output_file]
```

- `config_file`：配置文件路径（默认 `config_runtime.json`）
- `output_file`：输出文件路径（默认 `execution_result.json`）

例如：

```bash
python main_enhanced.py config_runtime.json my_result.json
```

---

## 5. 配置文件格式（config_example.json）

配置文件是一个 JSON，核心字段如下：

### 5.1 顶层字段

- `url`：合约 API base URL（通常形如：`http://.../api/v1/namespaces/default/apis/<API_NAME>`）
- `contract_name`：合约名称（用于订阅/日志等命名，例如 `SupplyChain`）
- `bpmn_id`：BPMN 流程定义 ID（创建实例时传入）
- `participants`：参与方身份信息（keyed by BPMN Participant ID）
- `erc_chaincodes`：Activity 到 ERC 链码类型的映射（例如某些 activity 使用 `ERC721`）
- `execution_path`：clean path 执行步骤数组（按顺序执行）

### 5.2 participants 结构（示意）

```json
"participants": {
  "Participant_xxx": {
    "name": "Manufacturer",
    "key": "Mem.org.comMSP::x509::CN=user2,...",
    "x509": "eDUwOTo6Q049dXNlcjIsT1U9...@Mem.org.comMSP",
    "msp": "Mem.org.comMSP"
  }
}
```

> 脚本在执行 message / activity 时会使用对应参与方的 `key` 作为 invoker key。

### 5.3 execution_path 结构（示意）

```json
"execution_path": [
  {
    "step": 1,
    "type": "event",
    "id": "Event_xxx",
    "description": "Start event"
  },
  {
    "step": 2,
    "type": "message",
    "id": "Message_xxx",
    "invoker": "Participant_xxx",
    "params": { "order": "..." }
  },
  {
    "step": 3,
    "type": "gateway",
    "id": "Gateway_xxx"
  },
  {
    "step": 4,
    "type": "activity",
    "id": "Activity_xxx",
    "invoker": "Participant_xxx",
    "params": { "tokenId": "..." }
  }
]
```

- `type` 支持：`event` / `message` / `gateway` / `activity`
- `invoker`（可选）：message/activity 一般需要（指向 `participants` 里的 participant id）
- `params`（可选）：会合并到 invoke 的 input 中（脚本也会自动加上 `InstanceID`）

---

## 6. 输出文件格式（execution_result.json）

输出是一个 **JSON 数组**，每次执行会 append 一条 run 记录：

```json
[
  {
    "task_name": "SupplyChain Clean Path Execution",
    "timestamp": "2026-01-24T20:31:09.820785",
    "instance_id": "xxxxx",
    "status": "success | failed | error",
    "error_message": null,
    "steps_executed": [
      {
        "step_number": 1,
        "step_id": "Event_...",
        "step_type": "event",
        "description": "Start event",
        "status": "success | failed | error",
        "result": "...",
        "error": null,
        "timestamp": "..."
      }
    ]
  }
]
```

> 注意：`result` 字段可能是字符串化后的返回内容（便于直接落盘，不强制保证为结构化 JSON）。

---

## 7. 常见问题（Troubleshooting）

1) **一直等不到 InstanceCreated / 超时**
- 检查 `url` 是否指向正确的 FireFly 合约 API
- 确保 FireFly WebSocket 可达（脚本会从 API URL 推导 WS 地址）
- 合约/监听器未正确部署时，也可能收不到事件

2) **invoke 返回 Failed**
- 直接看输出 JSON 里的 `error_message` 或某一步 `error`
- 常见原因：身份 key 不对、BPMN ID 不对、链码未部署/未批准、参数缺失等

3) **结果文件被覆盖？**
- 脚本是“读取已有 -> append -> 写回”模式；确保你没有同时并发运行多个脚本写同一个输出文件。

---

## 8. 最推荐的工作流

1. 复制示例配置：

```bash
cp config_example.json config_runtime.json
```

2. 修改 `config_runtime.json` 的 `url / bpmn_id / participants / execution_path` 等字段

3. 运行：

```bash
python main_enhanced.py
```

（不传参时默认读取 `config_runtime.json`，输出到 `execution_result.json`）
