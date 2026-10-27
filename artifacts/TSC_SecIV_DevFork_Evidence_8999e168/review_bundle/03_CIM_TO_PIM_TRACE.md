基准：dev-MultiBlockChain-fork，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`；日期 2026-10-27（Asia/Shanghai）。生成成功不代表部署或 DMN 执行成功。

原生 CIM→PIM PASS；当前 textX grammar 解析 PASS。完整命令/输出/退出码在 logs/cim_to_pim.*；生成完整原文位于 generated_pim/SupplyChainPaper.b2c。使用已有 .venv，未修改或安装依赖。

链路：Choreography._parse_node → MessageCatalog / ParameterExtractor → DSLContractBuilder → FlowPlanner。参与方身份来自 ParticipantMetadataResolver 的 bindings/default；端点来自 messageFlow；schema 来自 abc 扩展转成的内部 JSON；globals 从消息 properties、规则 I/O、条件变量提取，number→int、boolean→bool；文件保留 schema，不推导为本例 globals。

BusinessRule 字段来源：dmnResource=<taskID>.dmn；decisionID=<taskID>_DecisionID（均为命名约定）；inputMappings/outputMappings 为接口 name→public_the_name(name)；initialState=INACTIVE（默认）；RuleFlow 来自后继关系。Start READY，其余本例元素 INACTIVE。旁边 DMN 的规则和决策依赖未展开为 PIM。

原始摘录：`src/newTranslator/generator/translator.py:645`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```python
    def _build_business_rules_section(self) -> str:
        """Render business rule declarations with DMN metadata and mappings."""
        items = []
        for rule in self._choreography.query_element_with_type(NodeType.BUSINESS_RULE_TASK):
            doc = parse_json_documentation(rule.documentation)
            input_block = "".join(
                dsl_snippet.DSL_BusinessRuleInputMappingItem(
                    param=entry.get("name", ""),
                    global_var=public_the_name(entry.get("name", "")),
                )
                for entry in doc.get("inputs", [])
            )
            output_block = "".join(
                dsl_snippet.DSL_BusinessRuleOutputMappingItem(
                    param=entry.get("name", ""),
                    global_var=public_the_name(entry.get("name", "")),
                )
                for entry in doc.get("outputs", [])
            )
            items.append(
                dsl_snippet.DSL_BusinessRuleItem(
                    id=rule.id,
                    dmn=f"{rule.id}.dmn",
                    decision=f"{rule.id}_DecisionID",
                    input_map=input_block,
                    output_map=output_block,
                    state=dsl_snippet.MapElementState("DISABLED"),
                )
            )
        return dsl_snippet.DSL_BusinessRulesFrame("".join(items))
```
原始摘录：`src/newTranslator/generator/translator.py:323`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```python
    def _business_rule_flows(self) -> List[str]:
        """Express that business rule completion enables the next step."""
        flows = []
        for rule in self._choreography.query_element_with_type(NodeType.BUSINESS_RULE_TASK):
            target = self._activation_target(rule.outgoing.target)
            targets = self._successor_targets(rule)
            if targets:
                flows.append(
                    dsl_snippet.DSL_WhenBusinessRuleDoneEnable(
                        rule=rule.id,
                        targets=self._format_action_chain("enable", targets),
                    )
                )
        return flows
```
原始摘录：`src/newTranslator/generator/translator.py:356`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```python
    def _parallel_join_flows(self) -> List[str]:
        """Emit parallel gateway join semantics requiring multiple prerequisites."""
        flows: List[str] = []
        for gateway in self._choreography.query_element_with_type(NodeType.PARALLEL_GATEWAY):
            incomings = gateway.incomings or []
            if len(incomings) <= 1:
                continue
            sources = []
            for incoming in incomings:
                source_name = self._activation_target(incoming.source)
                if source_name:
                    sources.append(source_name)
            sources = [source for source in sources if source]
            if len(sources) <= 1:
                continue
            targets = self._successor_targets(gateway)
            if not targets:
                continue
            flows.append(
                dsl_snippet.DSL_ParallelGatewayAwait(
                    gateway=gateway.id,
                    sources=", ".join(sources),
                    actions=self._format_prefixed_actions("enable", targets),
                )
            )
        return flows
```
完整原始 DSL：

```text
contract GeneratedContract {

    participants {
        participant Participant_0w6qkdf {
            msp "Bulk_buyerMSP"
            x509 ""
            isMulti false
            multiMin 0
            multiMax 0
            attributes {
                role = "Bulk buyer"

            }
        }
        participant Participant_19mgbdn {
            msp "ManufacturerMSP"
            x509 ""
            isMulti false
            multiMin 0
            multiMax 0
            attributes {
                role = "Manufacturer"

            }
        }
        participant Participant_09cjol2 {
            msp "MiddlemanMSP"
            x509 ""
            isMulti false
            multiMin 0
            multiMax 0
            attributes {
                role = "Middleman"

            }
        }
        participant Participant_0sa2v7d {
            msp "SupplierMSP"
            x509 ""
            isMulti false
            multiMin 0
            multiMax 0
            attributes {
                role = "Supplier"

            }
        }
        participant Participant_19j1e3o {
            msp "Special_carrierMSP"
            x509 ""
            isMulti false
            multiMin 0
            multiMax 0
            attributes {
                role = "Special carrier"

            }
        }

    }



    globals {
        Confirm1: bool
        Confirm2: bool
        Confirm3: string
        DeliveryConfirmation: bool
        FinalPriority: string
        NumberOfUnits: int
        OrderDetails: string
        ProductionStart: string
        RequestId: int
        SupplierReputation: int
        SupplyOrderDetails: string
        SupplyOrderId: string
        TransportOrderId: string
        Urgent: bool

    }



    messages {
        message Message_04wmlqe from Participant_19mgbdn to Participant_0w6qkdf {
            initial state INACTIVE
            schema "{\"properties\":{\"productionStart\":{\"type\":\"string\",\"description\":\"Notification of the commencement of production, including the date and time\"}},\"required\":[\"productionStart\"],\"files\":{},\"file required\":[]}"
        }
        message Message_0cba4t6 from Participant_09cjol2 to Participant_0sa2v7d {
            initial state INACTIVE
            schema "{\"properties\":{\"supplyOrderId\":{\"type\":\"string\",\"description\":\" Identifier of the supply order being forwarded\"}},\"required\":[\"supplyOrderId\"],\"files\":{},\"file required\":[]}"
        }
        message Message_0d2xte5 from Participant_19j1e3o to Participant_19mgbdn {
            initial state INACTIVE
            schema "{\"properties\":{\"deliveryConfirmation\":{\"type\":\"boolean\",\"description\":\"Confirmation of whether the supplies have been successfully delivered\"}},\"required\":[\"deliveryConfirmation\"],\"files\":{},\"file required\":[]}"
        }
        message Message_0hpha6h from Participant_0sa2v7d to Participant_19j1e3o {
            initial state INACTIVE
            schema "{\"properties\":{\"requestId\":{\"type\":\"number\",\"description\":\"Unique identifier of the request for additional details \"},\"supplierReputation\":{\"type\":\"number\",\"description\":\"A numerical rating representing the supplier's reputation.\"}},\"required\":[\"requestId\",\"supplierReputation\"],\"files\":{},\"file required\":[]}"
        }
        message Message_0pm90nx from Participant_09cjol2 to Participant_19j1e3o {
            initial state INACTIVE
            schema "{\"properties\":{\"transportOrderId\":{\"type\":\"string\",\"description\":\"Identifier of the transport order being forwarded\"}},\"required\":[\"transportOrderId\"],\"files\":{},\"file required\":[]}"
        }
        message Message_0rwz1km from Participant_19j1e3o to Participant_0sa2v7d {
            initial state INACTIVE
            schema "{\"properties\":{\"requestId\":{\"type\":\"number\",\"description\":\" Unique identifier of the request for additional details \"},\"numberOfUnits\":{\"type\":\"number\",\"description\":\" Total number of units in the order requested\"},\"urgent\":{\"type\":\"boolean\",\"description\":\"Indicates whether the order requires urgent delivery.\"}},\"required\":[\"requestId\",\"numberOfUnits\",\"urgent\"],\"files\":{},\"file required\":[]}"
        }
        message Message_196q1fj from Participant_19mgbdn to Participant_0w6qkdf {
            initial state INACTIVE
            schema "{\"properties\":{},\"required\":[],\"files\":{\"deliveryNote\":{\"type\":\"file\",\"description\":\"A document confirming the delivery of goods\"}},\"file required\":[\"deliveryNote\"]}"
        }
        message Message_1ajdm9l from Participant_19mgbdn to Participant_09cjol2 {
            initial state INACTIVE
            schema "{\"properties\":{\"supplyOrderDetails\":{\"type\":\"string\",\"description\":\" Details of the supplies needed\"}},\"required\":[\"supplyOrderDetails\"],\"files\":{},\"file required\":[]}"
        }
        message Message_1dmeexg from Participant_19j1e3o to Participant_19mgbdn {
            initial state INACTIVE
            schema "{\"properties\":{\"confirm3\":{\"type\":\"string\",\"description\":\"\"}},\"required\":[],\"files\":{},\"file required\":[]}"
        }
        message Message_1dzkcn0 from Participant_19j1e3o to Participant_19mgbdn {
            initial state INACTIVE
            schema "{\"properties\":{\"confirm2\":{\"type\":\"boolean\",\"description\":\"\"}},\"required\":[],\"files\":{},\"file required\":[]}"
        }
        message Message_1io2g9u from Participant_0sa2v7d to Participant_19j1e3o {
            initial state INACTIVE
            schema "{\"properties\":{},\"required\":[],\"files\":{\"waybill\":{\"type\":\"file\",\"description\":\"Digital or physical waybill document\uff0cdetailing the shipment contents and destination.\"}},\"file required\":[\"waybill\"]}"
        }
        message Message_1oxmq1k from Participant_19j1e3o to Participant_19mgbdn {
            initial state INACTIVE
            schema "{\"properties\":{\"confirm1\":{\"type\":\"boolean\",\"description\":\"\"}},\"required\":[],\"files\":{},\"file required\":[]}"
        }
        message Message_1wswgqu from Participant_0w6qkdf to Participant_19mgbdn {
            initial state INACTIVE
            schema "{\"properties\":{\"orderDetails\":{\"type\":\"string\",\"description\":\"Detailed list of goods ordered\"}},\"required\":[\"orderDetails\"],\"files\":{},\"file required\":[]}"
        }

    }



    gateways {
        gateway Gateway_1cr0nma {
            type exclusive
            initial state INACTIVE
        }
        gateway Gateway_0ep8cuh {
            type exclusive
            initial state INACTIVE
        }
        gateway Gateway_0onpe6x {
            type parallel
            initial state INACTIVE
        }
        gateway Gateway_1fbifca {
            type parallel
            initial state INACTIVE
        }

    }



    events {
        event Event_06sexe6 {
            initial state READY
        }
        event Event_13pbqdz {
            initial state INACTIVE
        }

    }



    businessrules {
        businessrule Activity_0rm8bkp {
            dmn "Activity_0rm8bkp.dmn"
            decision "Activity_0rm8bkp_DecisionID"
            input mapping {
                numberOfUnits -> NumberOfUnits
                urgent -> Urgent
                supplierReputation -> SupplierReputation

            }
            output mapping {
                finalPriority -> FinalPriority

            }

            initial state INACTIVE
        }

    }



    oracletasks {

    }



    flows {
        start event Event_06sexe6 enables Message_1wswgqu;

        when message Message_1wswgqu completed
        then enable Message_1ajdm9l;
        when message Message_1ajdm9l completed
        then enable Gateway_0onpe6x;
        when message Message_0cba4t6 completed
        then enable Gateway_1fbifca;
        when message Message_0pm90nx completed
        then enable Gateway_1fbifca;
        when message Message_0rwz1km completed
        then enable Message_0hpha6h;
        when message Message_0hpha6h completed
        then enable Message_1io2g9u;
        when message Message_1io2g9u completed
        then enable Activity_0rm8bkp;
        when message Message_0d2xte5 completed
        then enable Gateway_1cr0nma;
        when message Message_04wmlqe completed
        then enable Message_196q1fj;
        when message Message_196q1fj completed
        then enable Event_13pbqdz;
        when message Message_1oxmq1k completed
        then enable Gateway_1cr0nma;
        when message Message_1dzkcn0 completed
        then enable Gateway_1cr0nma;
        when message Message_1dmeexg completed
        then enable Gateway_1cr0nma;

        when gateway Gateway_1cr0nma completed
        then enable Message_04wmlqe;
        when gateway Gateway_0ep8cuh completed
        choose {
            if FinalPriority == "Low"
            then enable Message_1oxmq1k;
            if FinalPriority == "High"
            then enable Message_1dmeexg;
            if FinalPriority == "Medium"
            then enable Message_1dzkcn0;
            if FinalPriority == "VeryLow"
            then enable Message_0d2xte5;

        }
        when gateway Gateway_0onpe6x completed
        then enable Message_0cba4t6, enable Message_0pm90nx;

        parallel gateway Gateway_1fbifca await Message_0cba4t6, Message_0pm90nx
        then enable Message_0rwz1km;

        when businessrule Activity_0rm8bkp done
        then enable Gateway_0ep8cuh;

    }

}

```
