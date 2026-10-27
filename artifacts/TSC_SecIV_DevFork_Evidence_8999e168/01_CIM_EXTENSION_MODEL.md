基准：dev-MultiBlockChain-fork，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`；日期 2026-10-27（Asia/Shanghai）。生成成功不代表部署或 DMN 执行成功。

已落地的扩展机制为 BPMN extensionElements + abc 自定义命名空间 + bpmn-moddle descriptor；未发现该机制独立 XSD。descriptor 有六个 Element 子类。

| 宿主 | 扩展标签 | 属性 | PIM 去向 |
|---|---|---|---|
| message | MessageSchema/Property | name,type,description,required,definition | Message.schema；标量推导 GlobalVar |
| message | MessageSchema/File | name,type,description,required,definition | schema.files；本例文件未进入 globals |
| businessRuleTask | BusinessRule/Input, Output | name,type,description,definition | BusinessRule ParamMapping，globals |

MessageSchema 的 properties/files 和 BusinessRule 的 inputs/outputs 为多值包含关系。definition 属性仍装 JSON，并未彻底消除 JSON。规则解析以 JSON 为基础 setdefault name/type/description，重复字段冲突时 definition 内值优先；消息类似。

Participant、MessageFlow、ChoreographyTask、Gateway、SequenceFlow 没有该 descriptor 的专用扩展类型。Participant 用标准 name/ID/multiplicity；MessageFlow sourceRef/targetRef/messageRef、Task participantRef/messageFlowRef、SequenceFlow sourceRef/targetRef/conditionExpression 均使用标准结构。身份由 bindings.json 或默认值提供。

扩展没有实际 DMN resource/decision 引用或独立 globalRef；I/O 用 name 推导首字母大写的 global。解析器按 local-name 匹配，没有严格核验 abc namespace；扩展优先，缺失扩展时 documentation 回退。读取后转成内部兼容 JSON，再进入原有转换器。

`src/bpmn-chor-app/src/modeler/moddle/abc.json:7` (`"name": "MessageSchema"`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

原始摘录：`src/newTranslator/generator/parser/choreography_parser/parser.py:46`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```python
def _read_message_schema_extension(element: ET.Element) -> str | None:
    """Read abc:MessageSchema and return the legacy message documentation JSON."""
    extension_elements = next(
        (child for child in list(element) if _local_name(child.tag) == "extensionElements"),
        None,
    )
    if extension_elements is None:
        return None

    schema_element = next(
        (
            child
            for child in list(extension_elements)
            if _local_name(child.tag) == "MessageSchema"
        ),
        None,
    )
    if schema_element is None:
        return None

    properties = {}
    required = []
    files = {}
    file_required = []

    for child in list(schema_element):
        child_name = _local_name(child.tag)
        field_name = child.attrib.get("name", "")
        if not field_name:
            continue
        raw_definition = child.attrib.get("definition", "")
        try:
            field_def = json.loads(raw_definition) if raw_definition else {}
        except json.JSONDecodeError:
            field_def = {}
        if not isinstance(field_def, dict):
            field_def = {}
        field_def.pop("required", None)
        field_def.setdefault("type", child.attrib.get("type", "string"))
        if "description" in child.attrib:
            field_def.setdefault("description", child.attrib.get("description", ""))
        if child_name == "Property":
            properties[field_name] = field_def
            if _bool_attr(child.attrib.get("required", "")):
                required.append(field_name)
        elif child_name == "File":
            files[field_name] = field_def
            if _bool_attr(child.attrib.get("required", "")):
                file_required.append(field_name)

    return json.dumps(
        {
            "properties": properties,
            "required": required,
            "files": files,
            "file required": file_required,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
```
原始摘录：`src/newTranslator/generator/parser/choreography_parser/parser.py:108`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```python
def _read_business_rule_extension(element: ET.Element) -> str | None:
    """Read abc:BusinessRule and return the legacy business-rule documentation JSON."""
    extension_elements = next(
        (child for child in list(element) if _local_name(child.tag) == "extensionElements"),
        None,
    )
    if extension_elements is None:
        return None

    business_rule = next(
        (
            child
            for child in list(extension_elements)
            if _local_name(child.tag) == "BusinessRule"
        ),
        None,
    )
    if business_rule is None:
        return None

    payload = {
        "inputs": [],
        "outputs": [],
    }

    for child in list(business_rule):
        child_name = _local_name(child.tag)
        raw_definition = child.attrib.get("definition", "")
        try:
            item = json.loads(raw_definition) if raw_definition else {}
        except json.JSONDecodeError:
            item = {}
        if not isinstance(item, dict):
            item = {}
        item.setdefault("name", child.attrib.get("name", ""))
        item.setdefault("type", child.attrib.get("type", "string"))
        if "description" in child.attrib:
            item.setdefault("description", child.attrib.get("description", ""))
        if not item.get("name"):
            continue
        if child_name == "Input":
            payload["inputs"].append(item)
        elif child_name == "Output":
            payload["outputs"].append(item)

    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
```
原始摘录：`src/newTranslator/generator/parser/choreography_parser/parser.py:217`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```python
            case NodeType.MESSAGE.value:
                documentation_list = element.findall(f"./{bpmn2prefix}documentation")
                documentation = (
                    documentation_list[0].text if documentation_list else None
                )
                extension_documentation = _read_message_schema_extension(element)
                return Message(
                    self,
                    element.attrib["id"],
                    element.attrib.get("name", ""),
                    documentation=extension_documentation
                    if extension_documentation is not None
                    else (documentation if documentation is not None else "{}"),
                )
            case NodeType.BUSINESS_RULE_TASK.value:
                # Parser Input & Output
                documentation_list = element.findall(f"./{bpmn2prefix}documentation")
                documentation = (
                    documentation_list[0].text if documentation_list else None
                )
                extension_documentation = _read_business_rule_extension(element)
                return BusinessRuleTask(
                    self,
                    element.attrib["id"],
                    element.attrib.get("name", ""),
                    incoming=_first_text(f"./{bpmn2prefix}incoming"),
                    outgoing=_first_text(f"./{bpmn2prefix}outgoing"),
                    documentation=extension_documentation
                    if extension_documentation is not None
                    else (documentation if documentation is not None else "{}"),
                )
            case NodeType.RECEIVE_TASK.value:
```
XML 摘录（继承根命名空间 xmlns:bpmn2="http://www.omg.org/spec/BPMN/20100524/MODEL"；xmlns:abc="https://chaincollab.io/schema/abc"）：`Experiment/BPMNwithDMNcase/new/SupplyChainPaper.bpmn:59` (`id="Message_0rwz1km"`, commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`)

```xml
<bpmn2:message id="Message_0rwz1km" name="Request Details">
    <bpmn2:extensionElements>
      <abc:MessageSchema>
        <abc:Property name="requestId" type="number" description=" Unique identifier of the request for additional details " required="true" definition="{&quot;type&quot;:&quot;number&quot;,&quot;description&quot;:&quot; Unique identifier of the request for additional details &quot;}" />
        <abc:Property name="numberOfUnits" type="number" description=" Total number of units in the order requested" required="true" definition="{&quot;type&quot;:&quot;number&quot;,&quot;description&quot;:&quot; Total number of units in the order requested&quot;}" />
        <abc:Property name="urgent" type="boolean" description="Indicates whether the order requires urgent delivery." required="true" definition="{&quot;type&quot;:&quot;boolean&quot;,&quot;description&quot;:&quot;Indicates whether the order requires urgent delivery.&quot;}" />
      </abc:MessageSchema>
    </bpmn2:extensionElements>
  </bpmn2:message>
```
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

前端真实构造/迁移方法原始摘录：`src/bpmn-chor-app/src/ChorModelerApp.tsx:96`，commit `8999e1687b505e013bbec789a8a231cd3afb5c3a`

```tsx
const buildMessageSchemaExtension = (modeler: any, element: any, payload: any) => {
  const businessObject = element.businessObject;
  const moddle = modeler._moddle;
  const extensionElements = businessObject.extensionElements
    || moddle.create('bpmn:ExtensionElements', { values: [] });
  const messageSchema = moddle.create('abc:MessageSchema', {
    properties: [],
    files: []
  });

  Object.keys(payload.properties).forEach((name) => {
    const definition = payload.properties[name];
    const required = payload.required.includes(name);
    const property = moddle.create('abc:Property', {
      name,
      type: definition.type,
      description: definition.description,
      required,
      definition: JSON.stringify(definition)
    });
    property.$parent = messageSchema;
    messageSchema.properties.push(property);
  });

  Object.keys(payload.files).forEach((name) => {
    const definition = payload.files[name];
    const required = payload['file required'].includes(name);
    const file = moddle.create('abc:File', {
      name,
      type: definition.type,
      description: definition.description,
      required,
      definition: JSON.stringify(definition)
    });
    file.$parent = messageSchema;
    messageSchema.files.push(file);
  });

  messageSchema.$parent = extensionElements;
  extensionElements.values = (extensionElements.values || [])
    .filter((value: any) => localModdleName(value) !== 'MessageSchema')
    .concat(messageSchema);
  extensionElements.$parent = businessObject;

  return extensionElements;
};

const buildBusinessRuleExtension = (modeler: any, element: any, payload: any) => {
  const businessObject = element.businessObject;
  const moddle = modeler._moddle;
  const extensionElements = businessObject.extensionElements
    || moddle.create('bpmn:ExtensionElements', { values: [] });
  const businessRule = moddle.create('abc:BusinessRule', {
    inputs: [],
    outputs: []
  });

  payload.inputs.forEach((item: any) => {
    const input = moddle.create('abc:Input', {
      name: item.name,
      type: item.type,
      description: item.description,
      definition: JSON.stringify(item)
    });
    input.$parent = businessRule;
    businessRule.inputs.push(input);
  });

  payload.outputs.forEach((item: any) => {
    const output = moddle.create('abc:Output', {
      name: item.name,
      type: item.type,
      description: item.description,
      definition: JSON.stringify(item)
    });
    output.$parent = businessRule;
    businessRule.outputs.push(output);
  });

  businessRule.$parent = extensionElements;
  extensionElements.values = (extensionElements.values || [])
    .filter((value: any) => localModdleName(value) !== 'BusinessRule')
    .concat(businessRule);
  extensionElements.$parent = businessObject;

  return extensionElements;
};

const normalizeDocumentationExtensions = (modeler: any) => {
  const elementRegistry = modeler.get('elementRegistry');
  const eventBus = modeler.get('eventBus');
  elementRegistry.forEach((element: any) => {
    if (element.type === 'bpmn:Message') {
      const payload = parseLegacyMessageDocumentation(element.businessObject);
      if (!payload) {
        return;
      }
      element.businessObject.extensionElements = buildMessageSchemaExtension(modeler, element, payload);
      element.businessObject.documentation = [];
      eventBus.fire('element.changed', { element });
    }
    if (element.type === 'bpmn:BusinessRuleTask') {
      const payload = parseLegacyBusinessRuleDocumentation(element.businessObject);
      if (!payload) {
        return;
      }
      element.businessObject.extensionElements = buildBusinessRuleExtension(modeler, element, payload);
      element.businessObject.documentation = [];
      eventBus.fire('element.changed', { element });
    }
  });
};

```
