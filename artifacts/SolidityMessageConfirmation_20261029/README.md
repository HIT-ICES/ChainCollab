# Solidity 消息确认实现与验证

日期：2026-10-29。实现基线：`36981317fb505a2dd2a3720912e178867dc95f28`，工作分支 `dev-MultiBlockChain-fork`。实施阶段未自动提交/推送；随后按用户明确授权提交至 dev 并合入 release。未修改论文、已有实验报告或既有生成证据归档。原有未跟踪目录保持原样。

## 结论与行为

BusinessRule 原已实现 WAITING/request/Continue；本次缺口是 Message 的接收确认，不是缺少状态枚举或未开启配置。

新增默认消息生命周期：ENABLED → Send → WAITING_FOR_CONFIRMATION → 接收方 Complete → COMPLETED。Send 负责参数写回、保存 fireflyTranId、发出 MessageSent 和执行 `sent` 动作；Complete 检查接收方身份及 WAITING，发出 MessageCompleted（含原始交易标识），执行 `completed` 动作。保留 Fabric 的 sent/completed 区分，不擅自改变 BPMN→DSL 流程触发条件。

## 修改文件

- `src/newTranslator/CodeGenerator/b2cdsl-solidity/b2cdsl_solidity/__init__.py`：拆分 sent/completed 动作；生成 Send 和 Complete；execution layout 增加确认方法。
- `templates/actions/message_send.sol.jinja`：发送后进入 WAITING_FOR_CONFIRMATION。
- `templates/actions/message_complete.sol.jinja`：真实接收确认 Jinja 函数骨架。
- `templates/contract.sol.jinja`：新增 MessageCompleted 事件。BusinessRule 源码未改变。
- `src/front/src/views/BPMN/Execution/SvgComponent/index.tsx`：等待状态且 ABI 有 Complete 时显示确认入口。
- `tests/test_flow_templates.py`：保留 Go 原输出和 Solidity 非消息函数的精确 golden 校验，增加消息阶段分离与 layout 检查；不把有意的消息行为变化错误地要求为旧输出字节一致。
- `tests/fixtures/message_confirmation.b2c`、`tests/message_confirmation.evm.cjs`：明确为测试数据的本地 EVM 回归，非论文实验。
- `docs/Solidity_Message_Confirmation.md`：调用协议和升级说明。

## 验证

1. Python unittest：4 项通过。Go 整合约仍与重构前 golden SHA256 一致；Solidity 非消息 flow blocks 与原 golden 逐字节校验值一致；消息等待/确认和元数据检查通过。
2. 28 个 Solidity 样例生成成功：既有冻结语料 27 个 + 新确认测试夹具 1 个；既有所有 PIM 输出与旧基线逐字节一致。真实命令、输出和 SHA256 见 `generation_commands.json`、`generated/`、`generated.sha256.json`。
3. solc 0.8.30：全部 28 个生成源码通过类型检查；原版、新版 SupplyChainPaper 均生成字节码（optimizer runs=200、viaIR、Shanghai），见 `compiler_typecheck.json`、`supplychain_bytecode.json`。本地 EVM 测试夹具也实际编译、部署和执行，不只是类型检查。
4. 本地 in-process Ganache EVM：16 项通过，见 `evm_results.json`。覆盖未发送确认、越权发送、WAITING 状态、参数写回（由值相关网关验证）、交易标识保留、实例隔离、重复发送/确认、接收方权限、完成事件、sent/completed 动作分离、并行汇合、组织身份确认及不存在实例。
5. 前端实际 action-selection TypeScript 函数隔离运行，5 项状态路由检查通过，见 `frontend_routing.json`；其中 payload builder 是测试 stub，未声称完整浏览器端到端测试。整个前端 `tsc --noEmit` 通过。
6. `git diff --check` 通过。未修改 Fabric/Go 源码；未运行线上部署、真实 DMN 求值或重新压测。

本地 EVM 首次运行中第二个 createInstance 在自动 gas 估算下执行失败，失败日志保留为 `evm_initial_gas_estimate.log`。测试为实例创建设置 2,000,000 的显式 gas 上限后，16 项全部通过；未修改产品合约绕过检查。Node 20 运行使用测试依赖 solc 0.8.30、ethers 6、ganache 7；安装锁文件与实际版本见 `test-dependencies/`。

## 可复现命令

从仓库根目录，已有 Python 环境：

```bash
src/newTranslator/.venv/bin/python -m unittest discover \
  -s src/newTranslator/CodeGenerator/b2cdsl-solidity/tests -v
src/newTranslator/.venv/bin/python \
  artifacts/SolidityMessageConfirmation_20261029/generate_corpus.py
```

EVM 测试依赖安装在 `/tmp/chaincollab-message-confirmation-20261029/node_modules`，没有写入产品工程依赖：

```bash
NODE_PATH=/tmp/chaincollab-message-confirmation-20261029/node_modules \
/home/shenxz-lab/.nvm/versions/node/v20.20.0/bin/node \
  src/newTranslator/CodeGenerator/b2cdsl-solidity/tests/message_confirmation.evm.cjs \
  artifacts/SolidityMessageConfirmation_20261029/generated/fixture/message_confirmation/message_confirmation.sol \
  artifacts/SolidityMessageConfirmation_20261029/evm_results.json
```

重新生成、部署合约及 ABI 后，新流程才生效。之前已部署的单阶段 Solidity 不会自动改变；前端对没有 Complete 的旧 ABI 不提供确认按钮。该实现没有新增兼容开关。
