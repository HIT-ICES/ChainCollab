基准：dev-MultiBlockChain-fork，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`；日期 2026-10-27（Asia/Shanghai）。生成成功不代表部署或 DMN 执行成功。

此前已汇总：f98238e8:docs/SupplyChainPaper/SupplyChainPaper_20260922_133943/。本分支工作树没有该目录；历史 README/issues/status/provenance/traceability/worked_mapping 用 git show 保存到 source_references/historical_f98238e8/，不把旧 XML 当成新扩展证据。

本轮主输入为用户指定 `Experiment/BPMNwithDMNcase/new/SupplyChainPaper.bpmn`。统计：{"participant": 5, "message": 13, "messageFlow": 13, "businessRuleTask": 1, "exclusiveGateway": 2, "parallelGateway": 2, "startEvent": 1, "endEvent": 1, "documentation": 0, "extensionElements": 14}。

新版 SupplyChainPaper 的所有消息 schema 和 Priority Decision I/O 已迁移。上级目录旧同名 BPMN 与两版 DMN 原样保存在 source_models/；原始模型不改动。Activity_0rm8bkp 有 numberOfUnits/urgent/supplierReputation 输入及 finalPriority 输出，但没有 dmnResource/decisionID 属性。name 到 global 的映射由转换器推导。

相关 DMN 真实决策为 decision_0tybghz 和 Decision_0zwjfyy，后者 requiredDecision 指向前者。CIM→PIM 没读取该 DMN 文件；静态调用链与 logs/cim_read_audit.json 的实际读取审计一致，审计重跑的 DSL 与原生 CLI byte-equal。

模型接口迁移已完成；若要声称显式 DMN 引用已完成，仍缺模型字段、解析逻辑和真实运行配置核验。本轮不修复。

XML 摘录（继承根命名空间 xmlns:bpmn2="http://www.omg.org/spec/BPMN/20100524/MODEL"；xmlns:abc="https://chaincollab.io/schema/abc"）：`Experiment/BPMNwithDMNcase/new/SupplyChainPaper.bpmn:212` (`id="Activity_0rm8bkp"`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

```xml
<bpmn2:businessRuleTask id="Activity_0rm8bkp" name="Priority Decision">
      <bpmn2:extensionElements>
        <abc:BusinessRule>
          <abc:Input name="numberOfUnits" type="number" description=" Total number of units in the order requested" definition="{&quot;name&quot;:&quot;numberOfUnits&quot;,&quot;type&quot;:&quot;number&quot;,&quot;description&quot;:&quot; Total number of units in the order requested&quot;}" />
          <abc:Input name="urgent" type="boolean" description="Indicates whether the order requires urgent delivery." definition="{&quot;name&quot;:&quot;urgent&quot;,&quot;type&quot;:&quot;boolean&quot;,&quot;description&quot;:&quot;Indicates whether the order requires urgent delivery.&quot;}" />
          <abc:Input name="supplierReputation" type="number" description="A numerical rating representing the supplier's reputation." definition="{&quot;name&quot;:&quot;supplierReputation&quot;,&quot;type&quot;:&quot;number&quot;,&quot;description&quot;:&quot;A numerical rating representing the supplier's reputation.&quot;}" />
          <abc:Output name="finalPriority" type="string" description="" definition="{&quot;name&quot;:&quot;finalPriority&quot;,&quot;type&quot;:&quot;string&quot;,&quot;description&quot;:&quot;&quot;}" />
        </abc:BusinessRule>
      </bpmn2:extensionElements>
      <bpmn2:incoming>Flow_19s99wl</bpmn2:incoming>
      <bpmn2:outgoing>Flow_1jxt9fr</bpmn2:outgoing>
    </bpmn2:businessRuleTask>
```
原始摘录：`Experiment/BPMNwithDMNcase/new/supplyChainPaper.dmn:70`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```xml
  <decision id="Decision_0zwjfyy" name="Final Priority Adjustment Decision">
    <informationRequirement id="InformationRequirement_0hefcti">
      <requiredDecision href="#decision_0tybghz" />
    </informationRequirement>
    <informationRequirement id="InformationRequirement_1o26uw3">
      <requiredInput href="#InputData_01mbjhm" />
    </informationRequirement>
```

本轮补充核验：旧模型和新模型分别用当前 HEAD 转换，生成 DSL 逐字节相同（logs/new_legacy_comparison.json）。这说明本例接口迁移保留了原转换输出，不代表真实 DMN 引用已增加。
