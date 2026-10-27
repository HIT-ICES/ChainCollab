基准：dev-MultiBlockChain-fork，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`；日期 2026-10-27（Asia/Shanghai）。生成成功不代表部署或 DMN 执行成功。

此前做过：f98238e8 中有 2026-09-22 SupplyChainPaper 归档。本次依据用户指定 new/SupplyChainPaper.bpmn 重新取证；new/supplyChainPaper.dmn 只是相关模型，不是本次 CIM→PIM 的实际输入。

| 阶段 | 状态 |
|---|---|
| 新结构化扩展 | CONFIRMED：消息 schema、规则 I/O |
| 原生 CIM→PIM | PASS |
| 当前 textX grammar 解析 | PASS |
| Fabric/Go 原生生成 | PASS |
| Geth/Solidity 原生生成 | PASS |
| 诊断 context 展开对比原生结果 | PASS：两端 byte-identical |
| 平台编译、部署、实际 DMN 执行 | NOT_RUN |

01 扩展模型；02 新旧源状态；03 CIM→PIM；04 九项矩阵（含 CSV）；05 暂态 context/模板架构；06 BusinessRule 贯穿；07 其他模式；08 版本差异/边界。

关键边界：DMN 资源/decision ID 为合成值，与原始 DMN 不匹配；没有独立原生 PSM 或外置 platform profile；Go 参数映射依赖初始化；消息/决策请求协议两平台不同。完整 PIM/context/template/function 生成证据已获得，真实 DMN 运行闭环未验证。

source_models 为原始 CIM/DMN；generated_* 为本轮原生输出；generation_contexts 为非原生诊断；source_references 包含当前源码和隔离的历史摘录；logs 记录命令、版本、退出码、读取审计及复现脚本。manifest.csv 保存来源、commit、SHA256。未采集 bindings 内容、私钥、口令或敏感部署配置。

review_bundle/ 为精选审阅包，review_bundle.zip 为 ZIP。完整产物保留主归档。

本轮补充核验：旧模型和新模型分别用当前 HEAD 转换，生成 DSL 逐字节相同（logs/new_legacy_comparison.json）。这说明本例接口迁移保留了原转换输出，不代表真实 DMN 引用已增加。
