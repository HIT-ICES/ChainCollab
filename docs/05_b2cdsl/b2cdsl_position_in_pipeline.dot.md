# B2CDSL 位置图说明

对应图片：

- [b2cdsl_position_in_pipeline.png](/home/shenxz-lab/code/ChainCollab/docs/05_b2cdsl/b2cdsl_position_in_pipeline.png)

图中表达的是：

1. BPMN Choreography 与 DMN Decision Tables 先进入解析层
2. 解析层把两者收敛为 B2CDSL
3. `b2c.tx` 作为 textX 元模型为 B2CDSL 提供语法和对象模型约束
4. 后续 Go 与 Solidity 生成器都消费这份中间表示
5. 同时该中间表示还能进入 Ecore/XMI/OCL 校验链

如果只保留一句话：

**B2CDSL 位于“业务模型”与“区块链代码生成”之间，是整个 `newTranslator` 的中间枢纽层。**
