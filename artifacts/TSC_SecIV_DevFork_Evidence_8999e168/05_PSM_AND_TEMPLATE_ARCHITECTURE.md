基准：dev-MultiBlockChain-fork，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`；日期 2026-10-27（Asia/Shanghai）。生成成功不代表部署或 DMN 执行成功。

没有独立 PSM 元模型、原生 PSM 文件或外置 platform profile 文件。平台具体化分布于 Python 类型映射/state alias、adapter、renderer、Jinja 主/子模板及内置 runtime/helper。两份 context JSON 为本次诊断，不能宣称为原生 PSM。

Fabric context keys：package_name, imports, globals, init_params, create_instance, business_rules, flow_functions。

Geth context keys：contract_name, participants, messages, gateways, events, oracle_tasks, globals, business_rules, flow_functions。

globals/participants/messages 等为属性映射及类型具体化；flow_functions 和 done_actions 已是平台代码字符串。Go business_rules payload 仅 name/done_actions；不把 PIM input/outputMappings 逐字段展开，而依赖初始化 ParamMapping。Solidity payload 将 I/O 具体化为 param_literal/slot_name/sol_type，用于静态输入构造和输出写回。

Fabric 消息、事件、gateway 的函数使用 Jinja 子模板；规则 Request/Continue、Participant、globals/初始化在 contract.go.jinja。Geth 消息、事件、gateway 使用 Python f-string 函数骨架，主模板插入 flow_functions；规则 Request/Continue 和结构初始化在 contract.sol.jinja。Gateway 模式共用 handler 形状；顺序 flow 只是函数中的状态更新；并非每个源对象生成一函数。

诊断调用未经修改的 build_context 和原模板 render，与两平台原生 textX CLI 输出均 byte-identical，详见 logs/stage_status.json。没有人为新建 PSM 格式或替换生成行为。

原始摘录：`src/newTranslator/CodeGenerator/b2cdsl-go/b2cdsl_go/__init__.py:600`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```python
    def build_context(self) -> dict:
        flow_functions = self.flow_renderer.render_blocks()
        rule_done_actions = self.flow_renderer.rule_done_actions()
        return {
            "package_name": "chaincode",
            "imports": self._imports(),
            "globals": self._state_memory_fields(),
            "init_params": self._init_parameter_fields(),
            "create_instance": self._create_instance_payload(),
            "business_rules": self._business_rule_payload(rule_done_actions),
            "flow_functions": flow_functions,
        }
```
原始摘录：`src/newTranslator/CodeGenerator/b2cdsl-solidity/b2cdsl_solidity/__init__.py:100`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```python
    def build_context(self) -> dict:
        enum_maps = self._enum_maps()
        flow_renderer = SolidityFlowRenderer(
            self.adapter,
            enum_maps,
            self._global_type_map(),
        )
        flow_functions = flow_renderer.render_blocks()
        rule_done_actions = flow_renderer.rule_done_actions()
        return {
            "contract_name": sanitize_contract_name(getattr(self.adapter.contract, "name", "")),
            "participants": self._participant_payload(),
            "messages": self._message_payload(),
            "gateways": self._simple_payload(self.adapter.gateways),
            "events": self._simple_payload(self.adapter.events),
            "oracle_tasks": self._oracle_task_payload(),
            "globals": self._global_variables(),
            "business_rules": self._business_rule_payload(rule_done_actions),
            "flow_functions": flow_functions,
        }
```
原始摘录：`src/newTranslator/CodeGenerator/b2cdsl-go/b2cdsl_go/__init__.py:685`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```python
    def _business_rule_payload(self, rule_done_actions: dict[str, str]) -> List[dict]:
        payload: List[dict] = []
        for rule in self.adapter.business_rules:
            payload.append(
                {
                    "name": rule.name,
                    "done_actions": rule_done_actions.get(rule.name, ""),
                }
            )
        return payload
```
原始摘录：`src/newTranslator/CodeGenerator/b2cdsl-solidity/b2cdsl_solidity/__init__.py:304`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```python
    def _business_rule_payload(self, rule_done_actions: dict[str, str]) -> List[dict]:
        global_type_map = self._global_type_map()
        payload: List[dict] = []
        for rule in self.adapter.business_rules:
            enum_name = sanitize_identifier(rule.name)
            input_mappings = []
            for mapping in getattr(rule, "inputMappings", []) or []:
                global_ref = getattr(mapping, "globalRef", None)
                global_name = getattr(global_ref, "name", "")
                if not global_name:
                    continue
                slot_name = sanitize_identifier(public_the_name(global_name))
                param_name = (getattr(mapping, "dmnParam", "") or global_name).strip()
                input_mappings.append(
                    {
                        "param_name": param_name,
                        "param_literal": json.dumps(param_name),
                        "slot_name": slot_name,
                        "sol_type": SOLIDITY_TYPE.get(global_type_map.get(global_name, "string"), "string"),
                    }
                )

            output_mappings = []
            for mapping in getattr(rule, "outputMappings", []) or []:
                global_ref = getattr(mapping, "globalRef", None)
                global_name = getattr(global_ref, "name", "")
                if not global_name:
                    continue
                slot_name = sanitize_identifier(public_the_name(global_name))
                param_name = (getattr(mapping, "dmnParam", "") or global_name).strip()
                output_mappings.append(
                    {
                        "param_name": param_name,
                        "param_literal": json.dumps(param_name),
                        "slot_name": slot_name,
                        "sol_type": SOLIDITY_TYPE.get(global_type_map.get(global_name, "string"), "string"),
                    }
                )

            payload.append(
                {
                    "name": rule.name,
                    "enum_name": enum_name,
                    "config_param": enum_name,
                    "content_param": "dmnCid",
                    "hash_param": "dmnHash",
                    "decision_param": "decisionId",
                    "caller_restricted_param": "callerRestricted",
                    "allowed_caller_param": "allowedCaller",
                    "input_mappings": input_mappings,
                    "output_mappings": output_mappings,
                    "done_actions": rule_done_actions.get(rule.name, ""),
                }
            )
        return payload
```
原始摘录：`src/newTranslator/CodeGenerator/b2cdsl-solidity/b2cdsl_solidity/__init__.py:454`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```python
    def _render_messages(self) -> List[str]:
        functions: List[str] = []
        for message in self.adapter.messages:
            enum_name = self.enum_maps["message"].get(message.name, sanitize_identifier(message.name))
            method_params, assignment_block = self._message_method_signature(message)
            # The Solidity runtime has a single message send transition that also
            # marks the message as completed. Support both DSL conditions here so
            # message follow-up flow is not dropped when the DSL uses `completed`.
            send_actions = self._indent("".join(self._message_transition_actions(message.name)), 2)
            signature = ", ".join(["uint256 instanceId", "string calldata fireflyTranId", *method_params])
            body = f"""function {enum_name}_Send({signature}) external onlyInitialized {{
        Instance storage inst = _getInstance(instanceId);
        Message storage m = inst.messages[MessageKey.{enum_name}];
        require(m.exists, "message not set");
        _checkParticipant(inst, m.sendParticipant);
        require(m.state == ElementState.ENABLED, "message state not allowed");

        m.fireflyTranId = fireflyTranId;
{assignment_block}\
        m.state = ElementState.COMPLETED;
        emit MessageSent(instanceId, MessageKey.{enum_name}, fireflyTranId);
{send_actions}
    }}"""
            functions.append(body)
        return functions
```
