# AI 阅读指令

请分析 SupplyChainPaper 的真实转换与运行链，不要先遍历上级完整审计归档，也不要把缺失环节补成理想化实现。

按以下顺序读取：

1. `00_START_HERE.md`
2. `FLOW_OVERVIEW.md`
3. `evidence/worked_mapping_extracts.md`
4. `pim/SupplyChainPaper.b2c`
5. 根据问题定位 `generated/fabric/SupplyChainPaper.go` 或 `generated/geth/SupplyChainPaper.sol`
6. 有争议时用 `evidence/traceability.csv` 和 `source_models/` 回查

分析时区分三类结论：

- 转换期已经生成和静态可见的行为；
- 部署或运行时需要注入的 DMN 内容、CID、decision ID、参数映射和服务地址；
- 尚未通过 Fabric DMN 链码或 Chainlink 实际执行验证的行为。

不要声称转换器读取了 DMN，不要声称 DMN 的两级依赖已实际执行，也不要把 Solidity 编译成功等同于链上执行成功。
