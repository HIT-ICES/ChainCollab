基准：dev-MultiBlockChain-fork，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`；日期 2026-10-27（Asia/Shanghai）。生成成功不代表部署或 DMN 执行成功。

历史归档在 f98238e8 的 docs/SupplyChainPaper/；本轮保存历史摘录，并重新跑新版模型，没有拼接未经执行的转换链。两个比较基准的完整 git diff 见 logs/diff_f98238e8.stdout 和 logs/diff_release-MultiBlockchain.stdout。

- 新增 abc descriptor、新版 BPMN/DMN 样例和解析器扩展读取。前端 MessageModal/DmnModal 编辑接口，ChorModelerApp 构造/迁移扩展并注册 moddle；原文件已保存。
- documentation 没有全局移除：message/businessRule 扩展优先、缺失回退，Oracle/split 的文档兼容路径仍在。definition 属性中继续有 JSON。
- 对 f98238e8，translator.py/grammar 未改变；BusinessRule/DMN 资源名及 decision ID 推导未变；Go renderer 把 Send 后 COMPLETED 改为 WAITINGFORCONFIRMATION。Jinja 模板/Solidity renderer 未改。release 比较的核心修改也在 parser 和 Go renderer，具体以原始 diff 为准。
- 旧函数/模板证据经当前 HEAD 核对可作参考；旧 documentation XML 不能作为新扩展证据。generated_pim/legacy_source_current_translator.b2c 是旧模型用当前转换器重新生成，并非历史产物；比较见 new_legacy_comparison.json。

实现边界和问题：

1. DMN ID 不匹配仍存在：PIM 合成 Activity_0rm8bkp.dmn / Activity_0rm8bkp_DecisionID；实际 supplyChainPaper.dmn 决策为 decision_0tybghz、Decision_0zwjfyy。CIM→PIM 不读 requiredDecision。DMN 服务执行 NOT_RUN。
2. Fabric 消息闭环的旧状态问题已在源码修正：Send→WAITINGFORCONFIRMATION；Complete→COMPLETED，完成后激活后继。此为静态/生成证据，没有链上事务验证。
3. Geth 仍是单 Send→COMPLETED，没有 Complete；不能声称与 Fabric 有相同接收确认协议。
4. 并行 join 检查 Message_0cba4t6 和 Message_0pm90nx 均 COMPLETED。guard 在 gateway 完成和后继启用前；前驱只 enable gateway，仍需调用它。未做并发链上执行测试。
5. Go 规则 I/O 依赖 runtime ParamMapping；context 未消费 PIM I/O 逐字段展开。Continue 多处错误返回可能被覆盖/未立即返回（GetInstance、Invoke_Other_chaincode、SetGlobalVariable）；不能以成功展开证明正确执行。
6. number→int；文件只保留 schema；required/复杂 schema 保留不代表全部运行时验证。namespace 按 local-name 匹配，不是 XSD 校验。
7. 平台编译、部署、真实身份配置、Oracle/DMNEngine/IDmnLite 调用均 NOT_RUN。生成 PASS 不能证明 DMN 绑定有效、平台行为等价或运行成功。

初始 tracked 修改为空；src/backend/api/ 与 src/java-env-custom-image/ 为既有未跟踪项。本轮只新增 artifacts，未改现有模型/grammar/转换器/生成器/模板/论文，未提交 Git。

原始摘录：`src/newTranslator/CodeGenerator/b2cdsl-go/b2cdsl_go/__init__.py:458`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```python
    def _parallel_guard_block(self, sources: List[Any]) -> str:
        checks = [self._element_ready_check(source) for source in sources]
        checks = [check for check in checks if check]
        if not checks:
            return ""
        condition = " && ".join(checks)
        block = "\tif !(" + condition + ") {\n"
        block += '\t\treturn fmt.Errorf("Parallel gateway prerequisite not met")\n'
        block += "\t}\n"
        return block
```
原始摘录：`src/newTranslator/CodeGenerator/b2cdsl-solidity/b2cdsl_solidity/__init__.py:822`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```python
    def _parallel_guard_block(self, sources: List[Any]) -> str:
        checks = [self._element_ready_check(source) for source in sources]
        checks = [check for check in checks if check]
        if not checks:
            return ""
        condition = " && ".join(checks)
        return f"if (!({condition})) {{\n            revert(\"Parallel gateway prerequisites not met\");\n        }}\n"
```

本轮补充核验：旧模型和新模型分别用当前 HEAD 转换，生成 DSL 逐字节相同（logs/new_legacy_comparison.json）。这说明本例接口迁移保留了原转换输出，不代表真实 DMN 引用已增加。
