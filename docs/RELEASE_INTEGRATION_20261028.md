# dev-fork 扩展元素与压测补充合入记录

日期：2026-10-28。目标分支：`release-MultiBlockchain`。

以 release 原有 HEAD `f98238e8` 为基线，选择性移植以下提交，保留来源 SHA（cherry-pick -x）：

| 来源提交 | 内容 | release 提交 |
| --- | --- | --- |
| `21cc93b9b736631337e1e34c3cd3752dd2b45a6b` | MessageSchema/Property/File 扩展、编辑器及解析/展示链路、新版案例 | `2979eaa5` |
| `da3be4a82aba3a88cdf2a35d791d75a9e23d258d` | BusinessRule/Input/Output 扩展及编辑、解析、绑定、展示链路 | `cfc7e753` |
| `8999e1687b505e013bbec789a8a231cd3afb5c3a` | Fabric/Geth TPS 压测及对比报告 19 份 | `3abbbaf9` |

`21cc93b9` 本身包含 Message 扩展，是 BusinessRule 扩展所需的前置提交，因此一并移植。

## 保留 release 的内容

- 原有实验目录和文件不删除、不移动、不覆盖，尤其是 `Experiment/new` 和 `Experiment/NoiseExperiment`；原版 `Experiment/BPMNwithDMNcase` 案例仍保留。
- 结构化案例只新增到 `Experiment/BPMNwithDMNcase/new`；压测报告只新增到 `Experiment/PerformanceTest/PlatformTPSComparison`。
- 不引入 dev 的 `Experiment/Current`、旧实验目录或已在 release 整理/移走的实验工程。
- 不移植 `be8bd359` 的论文证据归档；release 既有 `docs/SupplyChainPaper` 内容原样保留。
- `da3be4a8` 同时修改了一份生成后的示例链码。它与 release 现有示例的消息参数/写回逻辑冲突，并非扩展元素解析器或生成规则。保留 release 的 `src/backend/opt/chaincode-go-bpmn/chaincode-go-bpmn/chaincode/smartcontract.go` 及对应 `src/backend/opt/bpmn_chaincode.zip`，未用 dev 示例覆盖。
- 其他后端 opt 文件和 release 的 go.sum 原样保留。编辑器本地依赖包 `bpmn-chor-app-0.1.2.tgz` 随扩展支持一并更新。

## 验证

- 合入功能文件共 52 个：修改既有文件 9 个，新增 43 个，无删除、无重命名。全部 52 个文件内容与来源 `8999e168` 对应文件逐一按 Git blob SHA 核对一致。
- 对 release 原有所有已跟踪文件按 blob SHA 核查：除上述 9 个功能文件外均保持原样。原有实验、文档、后端 opt 均未被覆盖。
- Python 修改文件语法检查、abc descriptor JSON、新增 BPMN/DMN XML 解析通过。
- 11 个原版 BPMN + 11 个结构化 BPMN：CIM→B2CDSL、B2CDSL→Go、B2CDSL→Solidity 共 66 项检查全部通过。导入路径已核查，使用本次 release 工作树中的解析器、DSL、生成器和模板，而非 dev 的 editable 安装源文件。
- SupplyChainPaper 输出核查：输入字段、FinalPriority 输出槽、Fabric/Geth request/Continue 和各自 WAITING 状态存在。
- 模型编辑器 TypeScript `tsc -b` 通过；Vite 生产构建通过。
- 主前端 TypeScript `tsc --noEmit` 通过。
- 未重新执行链上部署或压测；合入的是来源提交的既有压测报告，未改写数据。

验证输出保存在 `/tmp/chaincollab-release-verification-20261028/`；TypeScript/Vite 日志位于 `/tmp/chaincollab-*-20261028.log`，均未作为产品文件提交。

原 dev 工作树及其未跟踪文件保持原样。合入在独立工作树 `/home/shenxz-lab/code/ChainCollab-release-integration-20261028` 完成。
