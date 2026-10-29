# Solidity / Go 函数骨架 Jinja 重构与等价性报告

日期：2026-10-29。

当前工作树：`/home/shenxz-lab/code/ChainCollab`，分支 `dev-MultiBlockChain-fork`，修改前 HEAD `be8bd359`。其生成器实现与固定提交 `8999e168` 相同。实施阶段未自动提交或推送；随后按用户明确授权提交并推送本次重构及验证证据。未修改论文工程；release 分支未在本次任务中修改。

## 修改范围和真实生成链路

修改两个 renderer：

- `src/newTranslator/CodeGenerator/b2cdsl-solidity/b2cdsl_solidity/__init__.py`
- `src/newTranslator/CodeGenerator/b2cdsl-go/b2cdsl_go/__init__.py`

新增真实模板（下表路径均相对于 `src/newTranslator/CodeGenerator`）：

| 模板 | 可引用范围 | 内容 |
| --- | --- | --- |
| `b2cdsl-solidity/templates/actions/message_send.sol.jinja` | 1–12 | 完整消息 Send 骨架 |
| `b2cdsl-solidity/templates/flows/start_event.sol.jinja` | 全文件 | 开始事件 |
| `b2cdsl-solidity/templates/flows/gateway.sol.jinja` | 全文件 | 网关，包括插入并行守卫和条件分支 |
| `b2cdsl-solidity/templates/flows/event.sol.jinja` | 全文件 | 其他事件处理 |
| `b2cdsl-solidity/templates/actions/oracle_task.sol.jinja` | 全文件 | Oracle 任务完成处理 |
| `b2cdsl-solidity/templates/actions/oracle_outputs.sol.jinja` | 全文件 | external-data / compute-task 调用与类型化输出写回 |
| `b2cdsl-solidity/templates/flows/gateway_branch.sol.jinja` | 全文件 | 分支块 |
| `b2cdsl-solidity/templates/flows/parallel_guard.sol.jinja` | 全文件 | 并行先决条件守卫 |
| `b2cdsl-go/templates/flows/oracle_task.go.jinja` | 全文件 | 原 Go 中残留的 Oracle 任务函数骨架 |

现有 BusinessRule 请求与 Continue 完成逻辑已经在真实 Jinja 中，无需重新实现：Solidity `templates/contract.sol.jinja` 717–799；Go 也保留原有主模板。保留所有状态、调用、输入输出、空白、缩进和事件行为。Solidity Message 仍为单次 Send→COMPLETED；BusinessRule 仍有 WAITING/request/Continue，不能混同。

Solidity 的新链路：

```text
B2CDSL model
 → DSLContractAdapter
 → SolidityRenderer.build_context()                 __init__.py:100–119
 → SolidityFlowRenderer.render_blocks()             __init__.py:384–391
 → _render_messages() 等组织模板上下文              __init__.py:452–470
 → _render_template() 加载真实 actions/ 和 flows/ 下的 *.sol.jinja    __init__.py:381–382
 → 函数字符串列表 flow_functions
 → contract.sol.jinja:801–805 插入该列表
 → generator_callback():849–858 渲染完整合约并写出
```

Python 保留解析、标识符和类型映射、参数列表、动作收集/去重、字面量/条件表达式以及少量单句动作片段，未宣称所有辅助代码字符串都已移入模板。通用完整函数骨架已不再使用 Python f-string；AST 审计结果见 `audit.json`。Go Oracle 任务现在通过 `__init__.py:339–345` 调用真实 Jinja。

新消息模板全文可直接作为附录完整函数级证据：

```jinja
function {{ message_name }}_Send({{ signature }}) external onlyInitialized {
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.{{ message_name }}];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
{{ parameter_assignments }}        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.{{ message_name }}, fireflyTranId);
{{ after_hooks }}
    }
```

## 基线与输入配置

在任何生成器修改前，保存全部冻结输入、输入 SHA256、原始生成输出、执行命令和环境，并完成两轮独立目录生成，验证基线稳定。之后才修改源码。

- `inputs/`：11 个原版 BPMN、11 个结构化 BPMN，两个目录中全部 companion DMN；`Exclusive`、`Parallel`、`Event-based` 和仓库 `oracleDiagram.bpmn`；另有 1 个明确标注为测试夹具的 DSL。
- `inputs.sha256.json`：每个输入文件及 bindings 的校验值。
- `inputs/bindings.json`：从 `generator/bindings.json` 原样复制。每轮运行前检查实际默认配置文件仍与冻结值一致；未引入新的绑定。
- `environment.json`：解释器、依赖版本、HEAD、初始工作区状态、显式 PYTHONPATH。平台使用真实 native textX Go/Solidity 生成器默认设置，没有外部 PSM 或部署配置。
- 原始输出分别在 `baseline/`、`baseline_repeat/`、`after_layout/`。各阶段的 `*.commands.json` 保存逐条 argv、cwd、PYTHONPATH、返回码、日志路径。
- `baseline_source/` 保存修改前源码与 Solidity 模板；`after_source/` 和 `after_source.sha256.json` 保存修改后源码、模板与校验值。

DMN 文件作为相同输入资源保存并校验；本生成路径不会打开并执行 companion DMN，不把本次测试解释为真实 DMN 绑定、求值或链上验证。

测试夹具首次包含 DSL 不支持的 `//` 行注释，初次夹具生成失败；日志、原始夹具和返回码保留在 `initial_fixture_attempt*`。在修改生成器前删除该测试夹具注释、用 UTF-8 保存后，重新建立成功基线。26 个仓库 BPMN 在首次尝试中均成功。最终基线及所有等价性结论基于修正后的同一冻结测试输入，不修改 DSL 语法或生成器来迎合夹具。

## 验证结果

| 阶段 | 样例 | CLI 命令 | 生成文件 | 失败 | 与基线字节差异 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 修改前 baseline | 27 | 80 | 297 | 0 | — |
| 修改前 baseline_repeat | 27 | 80 | 297 | 0 | 0 |
| 修改后 after_layout | 27 | 80 | 297 | 0 | 0 |

每轮：26 次真实 BPMN→B2CDSL + 27 次 Go + 27 次 Solidity 生成；27 个 B2CDSL、27 个 Go 主文件、27 个 Solidity 主文件和 216 个 Go scaffold 文件，共 297 个。除 SHA256 相等，还直接读取每个输出的 bytes 比较，没有归一化或忽略空白。

- `byte_comparison.json` / `.csv`：全部 297 个文件的前后 SHA256、直接字节相等结果、基线重复运行相等结果。
- `generation.diff`：空文件，表示零字节差异。
- `baseline.result.json`、`baseline_repeat.result.json`、`after_layout.result.json`：失败/差异均为空。
- 原始脚本 `verify_generation_equivalence.py` 拒绝覆盖已存在的运行目录和基线；`compare_bytes_and_audit.py` 可重复核查现存证据。
- Go scaffold 中相同的大型 `oracle_stub` 二进制使用硬链接去重，所有路径仍存在、bytes 和 SHA256 不变。证据约 42 MiB；不要在现有 baseline/after 输出路径上原位重新生成，以免改写共享 inode。新生成必须使用独立目录。

SupplyChainPaper（结构化新版）前后 SHA256：

| 输出 | before = after SHA256 |
| --- | --- |
| Go | `038a425578d7e334e852003060effb4c223a5d25e38737cd634c4ba471188e4c` |
| Solidity | `0e31fd5096d5f88cc661e7e306c8fd9ff46f3668282fc8a739773f9b6444c0b2` |

覆盖消息参数/文件参数、后继启用、sent/completed 动作合并、开始/结束事件、异或/事件型/并行网关、条件分支和并行守卫、BusinessRule 输入输出、request/Continue、external-data/compute-task 的 int/bool/string 输出及空映射。测试夹具还覆盖参数名冲突、数字开头字段、无后继动作、全局赋值和 disable 动作；它只用于回归测试，不作为实验案例或链上结果。

新增 `b2cdsl-solidity/tests/test_flow_templates.py` 和 `tests/fixtures/`：3 个 golden 测试全部通过，核对 Go 整合约、Solidity 整合约及每个 Solidity flow block 的修改前精确字节 SHA256。`unittest.log` 保存结果。

既有 Go/Solidity/DSL 生成器测试目录此前只有 `.dummy`；既有 Go/DSL 目录 unittest discovery 为 0 tests，不能把它称为已有测试通过。`git diff --check` 通过，新增模板均由实际生成覆盖。未执行链上部署或重新压测，也不以编译通过代替等价性证明。

可重复验证（从仓库根目录）：

```bash
src/newTranslator/.venv/bin/python -m unittest discover \
  -s src/newTranslator/CodeGenerator/b2cdsl-solidity/tests -v
src/newTranslator/.venv/bin/python \
  artifacts/SolidityJinjaRefactor_20261029/compare_bytes_and_audit.py
```

## 论文需要同步的表述

1. 新实现可以表述为：Fabric/Go 与 Solidity 的函数骨架均由实际 Jinja 模板表达，Python 负责平台映射与上下文组织；部分上下文值仍为已渲染的动作或函数字符串。
2. Solidity 消息应引用真实 `actions/message_send.sol.jinja:1–12`，同时展示 `_render_messages():452–470` 的上下文参数，主模板 `join` 仅作为最后插入位置。不要继续仅用 `join` 证明函数如何生成。
3. BusinessRule request/Continue 可以继续引用未变的 `contract.sol.jinja:717–799`；与消息单次完成语义分别说明。
4. `8999e168` 和 `be8bd359` 代表原实现及原证据，不能用于声称这些旧提交已包含本次新增模板。论文远端代码引用应固定到实际包含本次模板和本报告的重构提交 SHA；可用 `git log -- artifacts/SolidityJinjaRefactor_20261029/README.md` 查得，不应沿用旧实现 SHA。
5. 本次验证结论仅为相同冻结输入/配置下的生成输出逐字节一致，不扩大为全部模型的形式化等价证明、真实 DMN 执行或链上验证。

目录分类按用户要求：Solidity Message/Oracle 任务模板位于 actions/；gateway、start/end event、branch、parallel guard 位于 flows/。after/ 保留目录调整前的首次等价验证输出；after_layout/ 是最终目录结构的验证输出。
