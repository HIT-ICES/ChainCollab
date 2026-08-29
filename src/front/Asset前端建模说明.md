# Asset 前端建模说明

本文总结 BPMN 前端绘图中 Asset 相关元素的建模逻辑。当前实现的核心思路是：

1. 在 BPMN 画布左侧工具栏增加资产相关元素。
2. 使用 `bpmn:Task` 表达资产操作任务。
3. 使用 `bpmn:DataObjectReference` 表达资产/Token 对象。
4. 通过 `DataInputAssociation` 和 `DataOutputAssociation` 表达资产对象与资产任务之间的输入输出关系。
5. 将资产定义和任务操作配置保存到 BPMN 元素的 `documentation` 字段中，后续 Python translator 会解析这些字段生成链码。

## 入口注册

文件：

- `src/views/BPMN/Chor-js/index.tsx`
- `src/views/BPMN/Chor-js/lib-provider/assettask-elements/index.js`
- `src/views/BPMN/Chor-js/lib-provider/data-elements/index.js`

`Chor-js/index.tsx` 是 BPMN 绘图页面入口。这里把 AssetTask 和 DataObject 扩展模块注册到 `ChoreoModeler`。

```tsx
import AssetTaskProvider from './lib-provider/assettask-elements'
import DataElementsModule from './lib-provider/data-elements'

modeler.current = new ChoreoModeler({
  container: '#canvas',
  propertiesPanel: {
    parent: '#properties-panel'
  },
  additionalModules: [
    PropertiesPanelModule,
    PropertiesProviderModule,
    TestPaletteProvider,
    AssetTaskProvider,
    DataElementsModule,
  ],
  keyboard: {
    bindTo: document
  }
})
```

这里的 `additionalModules` 是扩展点。只要模块按 bpmn-js/diagram-js 的 provider 格式暴露，就可以被 modeler 加载。

## Asset Task 元素

文件：

- `src/views/BPMN/Chor-js/lib-provider/assettask-elements/AssetTaskPaletteProvider.js`

Asset Task 的 palette 按钮在这里定义。它显示为“创建 NFT资产”，但实际创建的是标准 BPMN Task：

```js
function startCreate(event) {
  const serviceTaskShape = elementFactory.create(
    'shape',
    { type: 'bpmn:Task' },
  )

  create.start(event, serviceTaskShape)
}
```

也就是说，前端没有定义新的 BPMN 类型，而是复用 `bpmn:Task`。这个 Task 是否是资产任务，主要由它的 `documentation` 中是否保存了资产操作配置决定。

palette 配置如下：

```js
return {
  'create-test-data': {
    group: 'activity',
    title: '创建 NFT资产',
    imageUrl: icon,
    action: {
      dragstart: startCreate,
      click: startCreate,
    },
  },
}
```

## Asset DataObject 元素

文件：

- `src/views/BPMN/Chor-js/lib-provider/data-elements/DataPaletteProvider.js`
- `src/views/BPMN/Chor-js/lib-provider/data-elements/DataContextPadProvider.js`

DataObject 的 palette 按钮创建的是：

```js
const shape = elementFactory.createShape({
  type: 'bpmn:DataObjectReference'
});
create.start(event, shape);
```

`bpmn:DataObjectReference` 用来表示一个资产对象或 Token 对象。它的资产字段同样保存在 `documentation` 中。

DataObject 右键菜单提供两个能力：

- `connect`: 连接到 Task，生成 DataAssociation。
- `delete`: 删除 DataObject。

Task 右键菜单也增加了连接 DataObject 的入口：

```js
if (is(element, 'bpmn:Task')) {
  assign(actions, {
    'connect.data': {
      group: 'connect',
      className: 'bpmn-icon-data-object',
      title: translate('Connect to DataObject'),
      action: {
        click: startConnect,
        dragstart: startConnect,
      },
    },
  });
}
```

## 双击弹窗分发

文件：

- `src/views/BPMN/Chor-js/pop-up/MainPage.tsx`
- `src/views/BPMN/Chor-js/pop-up/AssetTaskModal.tsx`
- `src/views/BPMN/Chor-js/pop-up/AssetModal.tsx`

`MainPage.tsx` 监听画布元素双击事件，根据 BPMN 元素类型打开不同弹窗。

```tsx
const type = shape.type;

if (
  type === 'bpmn:BusinessRuleTask' ||
  type === 'bpmn:Message' ||
  type === 'bpmn:Task' ||
  type === 'bpmn:DataObjectReference'
) {
  setModalOpen(true);
}
```

Asset 相关分发逻辑：

```tsx
{dataElementType === 'bpmn:Task' && dataElementId ? (
  <AssetTaskModal
    dataElementId={dataElementId}
    open={modalOpen && 'bpmn:Task' === dataElementType}
    onClose={() => setModalOpen(false)}
  />
) : null}

{dataElementType === 'bpmn:DataObjectReference' && dataElementId ? (
  <AssetModal
    dataElementId={dataElementId}
    open={modalOpen && 'bpmn:DataObjectReference' === dataElementType}
    onClose={() => setModalOpen(false)}
  />
) : null}
```

因此：

- 双击 `bpmn:Task` 打开资产操作配置弹窗。
- 双击 `bpmn:DataObjectReference` 打开资产对象定义弹窗。

## AssetModal：资产对象定义

文件：

- `src/views/BPMN/Chor-js/pop-up/AssetModal.tsx`

`AssetModal` 负责编辑 DataObject 上的资产定义。主要字段包括：

- `assetType`: 资产类型，支持 `distributive`、`transferable`、`value-added`。
- `tokenType`: Token 类型，仅 `transferable` 时显示，支持 `NFT`、`FT`。
- `tokenName`: Token 名称。
- `tokenId`: Token ID，FT 类型不需要。
- `refTokenIds`: value-added 资产引用的源 Token ID 列表。
- `tokenHasExistInERC`: Token 是否已经存在于 ERC 合约中。

打开弹窗时，从当前 DataObject 的 `documentation` 读取已有数据：

```tsx
const doc = shape.businessObject.documentation;
if (Array.isArray(doc) && doc.length) {
  const parsed = JSON.parse(doc[0].text);
  setAssetType(parsed.assetType || '');
  setTokenType(parsed.tokenType || '');
  setTokenName(parsed.tokenName || '');
  setTokenId(parsed.tokenId || '');
  setTokenHasExistInERC(parsed.tokenHasExistInERC || false);
}
```

保存时，把表单字段写回 BPMN `documentation`：

```tsx
const payload = {
  assetType,
  tokenName
};

if (assetType === 'transferable') {
  if (tokenType) payload.tokenType = tokenType;
  if (tokenName) payload.tokenName = tokenName;
}

if (!(assetType === 'transferable' && tokenType === 'FT') && tokenId) {
  payload.tokenId = tokenId;
  payload.tokenHasExistInERC = tokenHasExistInERC;
}

if (assetType === 'value-added') {
  payload.refTokenIds = refTokenIds;
}

commandStack.execute('element.updateProperties', {
  element: shape,
  properties: {
    documentation: [
      modeler._moddle.create('bpmn:Documentation', {
        text: JSON.stringify(payload, null, 2),
      }),
    ],
  },
});
```

这个 `documentation` 是后端 translator 解析资产对象信息的主要来源。

示例：

```json
{
  "assetType": "transferable",
  "tokenType": "NFT",
  "tokenName": "ProductNFT",
  "tokenId": "token-001",
  "tokenHasExistInERC": false
}
```

## AssetTaskModal：资产操作定义

文件：

- `src/views/BPMN/Chor-js/pop-up/AssetTaskModal.tsx`

`AssetTaskModal` 负责编辑 Task 上的资产操作信息。主要字段包括：

- `caller`: 操作发起方。
- `callee`: 操作接收方。
- `operation`: 操作类型。
- `tokenNumber`: FT 数量。
- `outputs`: query 操作的输出字段定义。

资产基本信息优先从连接的 DataObject 读取，而不是从 Task 自身读取：

```tsx
const linkedAsset = getLinkedDataObjectAsset();

if (linkedAsset) {
  setAssetType(linkedAsset.assetType || '');
  setTokenType(linkedAsset.tokenType || '');
  setTokenName(linkedAsset.tokenName || '');
  setTokenId(linkedAsset.tokenId || '');
  setTokenHasExistInERC(linkedAsset.tokenHasExistInERC || false);
}
```

这种设计把“资产是什么”放在 DataObject 上，把“对资产做什么操作”放在 Task 上。

不同资产类型对应的操作选项：

```tsx
const operationOptions = {
  'distributive': [
    'mint',
    'burn',
    'grant usage rights',
    'revoke usage rights',
    'transfer',
    'query'
  ],
  'transferable': [
    'mint',
    'burn',
    'Transfer',
    'query'
  ],
  'value-added': [
    'branch',
    'Transfer',
    'burn',
    'query'
  ],
};
```

说明：

- `distributive`: 分发型资产，支持授权、撤权、转移等。
- `transferable`: 可转移资产，分 NFT/FT。
- `value-added`: 增值型资产，支持 branch/merge/transfer/burn/query 等语义。

## DataAssociation 连线语义

文件：

- `src/views/BPMN/Chor-js/chor-js/features/rules/ChoreoRules.js`
- `src/views/BPMN/Chor-js/chor-js/features/modeling/ChoreoModeling.js`
- `src/views/BPMN/Chor-js/chor-js/features/modeling/behavior/DataAssociationBehavior.js`

Asset 建模通过 DataAssociation 表达输入输出关系：

- `DataObject -> Task`: `bpmn:DataInputAssociation`
- `Task -> DataObject`: `bpmn:DataOutputAssociation`

`ChoreoRules.js` 根据 Task 的 `operation` 限制连线方向。

核心规则：

- `mint`: 只允许 `Task -> DataObject`，表示创建新 Token。
- `transfer`、`burn`、`query`: 只允许 `DataObject -> Task`，表示读取已有 Token。
- `branch`、`merge`: 允许多个 `DataObject -> Task` 输入，同时允许一个 `Task -> DataObject` 输出。
- 其他非 Task 与 DataObject 的连接会被阻止。

简化代码如下：

```js
if (is(source, 'bpmn:DataObjectReference') && is(target, 'bpmn:Task')) {
  const operation = getTaskOperation(target);

  if (operation && ['branch', 'merge'].includes(operation)) {
    return { type: 'bpmn:DataInputAssociation' };
  }

  if (operation && ['mint'].includes(operation)) {
    return false;
  }

  return { type: 'bpmn:DataInputAssociation' };
}

if (is(target, 'bpmn:DataObjectReference') && is(source, 'bpmn:Task')) {
  const operation = getTaskOperation(source);

  if (operation && ['branch', 'merge'].includes(operation)) {
    return { type: 'bpmn:DataOutputAssociation' };
  }

  if (operation && ['mint'].includes(operation)) {
    return { type: 'bpmn:DataOutputAssociation' };
  }

  return false;
}
```

`ChoreoModeling.js` 对 `connect` 做了增强，确保 DataAssociation 可以挂到对应的 BPMN businessObject 上：

```js
if (is(source, 'bpmn:ChoreographyActivity')) {
  const sourceBo = source.businessObject;
  if (!sourceBo.dataOutputAssociations) {
    sourceBo.dataOutputAssociations = [];
  }
}

if (is(target, 'bpmn:ChoreographyActivity')) {
  const targetBo = target.businessObject;
  if (!targetBo.dataInputAssociations) {
    targetBo.dataInputAssociations = [];
  }
}
```

## value-added 的 refTokenIds 自动同步

文件：

- `src/views/BPMN/Chor-js/chor-js/features/modeling/behavior/DataAssociationBehavior.js`
- `src/views/BPMN/Chor-js/pop-up/AssetModal.tsx`
- `src/views/BPMN/Chor-js/pop-up/AssetTaskModal.tsx`

value-added 资产的 `refTokenIds` 用来记录它引用了哪些源 Token。这个字段主要由连线自动维护。

典型建模方式：

```text
DataObject(token-A) ─┐
                    ├─> Task(branch/merge) ─> DataObject(value-added-token)
DataObject(token-B) ─┘
```

当 Task 是 `branch` 或 `merge`，并且输出 DataObject 的 `assetType` 是 `value-added` 时，`DataAssociationBehavior` 会收集输入 DataObject 的 `tokenId`，写入输出 DataObject 的 `refTokenIds`。

核心逻辑：

```js
if (!taskData.operation || !['branch', 'merge'].includes(taskData.operation)) {
  return;
}

const incomingTokenIds = [];
const incoming = taskElement.incoming || [];

for (const inConn of incoming) {
  if (is(inConn.businessObject, 'bpmn:DataInputAssociation')) {
    const inDataObject = inConn.source;
    const inData = JSON.parse(inDataObject.businessObject.documentation[0].text);
    if (inData.tokenId) {
      incomingTokenIds.push(inData.tokenId);
    }
  }
}

dataObjectData.refTokenIds = incomingTokenIds;
modeling.updateProperties(dataObjectElement, {
  documentation: [
    modeler._moddle.create('bpmn:Documentation', {
      text: JSON.stringify(dataObjectData, null, 2),
    }),
  ],
});
```

## distributive 授权连线标签

文件：

- `src/views/BPMN/Chor-js/chor-js/features/modeling/behavior/DataAssociationBehavior.js`

当 DataObject 是 `distributive`，Task 操作是：

- `grant usage rights`
- `revoke usage rights`

系统会给 `DataObject -> Task` 的 DataInputAssociation 自动加上 `use` 标签。

```js
const shouldHaveLabel =
  assetType === 'distributive' &&
  operation &&
  ['grant usage rights', 'revoke usage rights'].includes(operation);

const newLabel = shouldHaveLabel ? 'use' : '';
modeling.updateProperties(connection, {
  name: newLabel
});
```

## 前端校验

文件：

- `src/views/BPMN/Chor-js/lib-provider/validator/Validator.js`
- `src/views/BPMN/Chor-js/lib-provider/validator/constraints/AssetTaskConnectionConstraint.js`
- `src/views/BPMN/Chor-js/lib-provider/validator/constraints/AssetTaskOperationConstraint.js`

`Validator.js` 注册了 asset 相关校验：

```js
import assetTaskOperationConstraint from './constraints/AssetTaskOperationConstraint';
import assetTaskConnectionConstraint from './constraints/AssetTaskConnectionConstraint';

const CONSTRAINTS = [
  // ...
  assetTaskOperationConstraint,
  assetTaskConnectionConstraint,
];
```

`AssetTaskConnectionConstraint` 校验连接数量和方向：

- `mint` 必须有 `Task -> DataObject` 输出。
- `branch` 必须有 `Task -> DataObject` 输出，输入可选。
- `merge` 需要多个输入和一个输出。
- `transfer`、`burn`、`query` 需要 `DataObject -> Task` 输入。
- `grant usage rights`、`revoke usage rights` 需要输入 DataObject。

`AssetTaskOperationConstraint` 校验操作和资产状态：

- `mint`: 要求 Token 不存在。
- `branch`、`merge`: 对 value-added 来说类似 mint，要求目标 Token 不存在。
- `transfer`、`burn`、`query`、授权、撤权：要求 Token 已存在。
- FT 不做严格的 tokenId 状态流转校验。

## 后端 translator 识别流程

文件：

- `../py_translator/translator.py`
- `../py_translator/choreography_parser/parser.py`
- `../py_translator/choreography_parser/elements.py`
- `../py_translator/chaincode_snippet/snippet.py`
- `../py_translator/chaincode_snippet/snippet.json`

前端最终保存的是标准 BPMN XML。Asset 信息不是新 XML 标签，而是挂在元素的 `documentation` 字段中。

Python 后端的入口在 `server.py`：

```py
@app.post("/api/v1/chaincode/generate")
async def generate_chaincode(params: ChaincodeGenerateParams):
    translator = GoChaincodeTranslator(params.bpmnContent)
    chaincode = translator.generate_chaincode()
    ffi = translator.generate_ffi()
    return ChaincodeGenerateResponse(bpmnContent=chaincode, ffiContent=ffi)
```

`GoChaincodeTranslator` 初始化时会把 BPMN XML 解析成 Python 对象图，同时保留原始 XML root，后面用它查找 DataAssociation 和 DataObjectReference。

```py
if bpmnContent:
    choreography.load_diagram_from_string(bpmnContent)
    self._bpmn_xml_root = ET.fromstring(bpmnContent)
```

其中 `choreography_parser` 会把 BPMN 中的 `bpmn:Task` 解析为 `Task` 对象：

```py
case NodeType.TASK.value:
    documentation_list = element.findall(f"./{bpmn2prefix}documentation")
    documentation = documentation_list[0].text if documentation_list else None
    return Task(
        self,
        element.attrib["id"],
        element.attrib.get("name", ""),
        incoming=element.findall(f"./{bpmn2prefix}incoming")[0].text,
        outgoing=element.findall(f"./{bpmn2prefix}outgoing")[0].text,
        documentation=documentation if documentation is not None else "{}",
    )
```

注意：当前 parser 只把 `bpmn:Task` 建成 Python `Task` 对象；`DataObjectReference` 没有被单独建成 `Element` 节点，而是由 translator 通过原始 XML root 查询。

## Task 与 DataObject 字段合并

文件：

- `../py_translator/translator.py`

前端建模中，资产信息主要在 DataObject 上，操作信息主要在 Task 上。后端生成链码前，会把两边字段合并成一个 `doc_data`。

### 按操作方向找关联 DataObject

translator 使用 `_get_linked_dataobject_for_task` 根据 Task 操作类型决定查哪个方向的 DataAssociation：

```py
operation = task_doc.get('operation')

if operation in ['mint', 'branch', 'merge']:
    output_associations = task_elem.findall(".//bpmn:dataOutputAssociation", namespaces)
    # Task -> DataObject，读取 targetRef 指向的 DataObjectReference

input_associations = task_elem.findall(".//bpmn:dataInputAssociation", namespaces)
# DataObject -> Task，读取 sourceRef 指向的 DataObjectReference
```

这与前端连线语义保持一致：

- `mint`、`branch`、`merge`: 主要读取 `Task -> DataObject` 输出对象，因为这些操作会创建新资产。
- `transfer`、`burn`、`query`、授权、撤权: 主要读取 `DataObject -> Task` 输入对象，因为这些操作作用于已有资产。

找到 DataObjectReference 后，translator 读取它的 `documentation`：

```py
doc_elem = dataobj_elem.find("bpmn:documentation", namespaces)
if doc_elem is not None and doc_elem.text:
    doc_data = json.loads(doc_elem.text)
    return doc_data
```

### 合并资产字段和操作字段

`_merge_task_with_dataobject` 是 asset 后端识别最关键的函数。

```py
task_doc = json.loads(task.documentation)
dataobject_doc = self._get_linked_dataobject_for_task(task.id)

merged_doc = {}
```

如果找到了关联 DataObject，就优先使用 DataObject 的资产定义：

```py
if dataobject_doc:
    if 'assetType' in dataobject_doc:
        merged_doc['assetType'] = dataobject_doc['assetType']
    if 'tokenType' in dataobject_doc:
        merged_doc['tokenType'] = dataobject_doc['tokenType']
    if 'tokenName' in dataobject_doc:
        merged_doc['tokenName'] = dataobject_doc['tokenName']
    if 'tokenId' in dataobject_doc:
        merged_doc['tokenId'] = dataobject_doc['tokenId']
    if 'refTokenIds' in dataobject_doc:
        merged_doc['refTokenIds'] = dataobject_doc['refTokenIds']
    if 'tokenHasExistInERC' in dataobject_doc:
        merged_doc['tokenHasExistInERC'] = dataobject_doc['tokenHasExistInERC']
```

然后再追加 Task 自己的操作信息：

```py
if 'operation' in task_doc:
    merged_doc['operation'] = task_doc['operation']
if 'caller' in task_doc:
    merged_doc['caller'] = task_doc['caller']
if 'callee' in task_doc:
    merged_doc['callee'] = task_doc['callee']
if 'tokenNumber' in task_doc:
    merged_doc['tokenNumber'] = task_doc['tokenNumber']
if 'outputs' in task_doc:
    merged_doc['outputs'] = task_doc['outputs']
```

合并后的结构大致如下：

```json
{
  "assetType": "transferable",
  "tokenType": "NFT",
  "tokenName": "ProductNFT",
  "tokenId": "token-001",
  "tokenHasExistInERC": false,
  "operation": "mint",
  "caller": "Participant_issuer",
  "callee": ["Participant_receiver"]
}
```

因此前端保存字段时要注意边界：

- DataObject 保存“资产是什么”。
- Task 保存“谁对资产做什么操作”。
- 后端以 `_merge_task_with_dataobject` 的结果作为链码生成依据。

## CreateInstance 中初始化 TokenElement

文件：

- `../py_translator/translator.py`
- `../py_translator/chaincode_snippet/snippet.py`
- `../py_translator/chaincode_snippet/snippet.json`

`generate_chaincode` 会先生成通用代码，再生成实例初始化代码。

如果 BPMN 中存在 `bpmn:Task`，translator 会引入 token 相关 import：

```py
chaincode_list.append(
    snippet.import_code(
        if_oracle=len(self._choreography.query_element_with_type(NodeType.BUSINESS_RULE_TASK)) > 0,
        if_Token=len(self._choreography.query_element_with_type(NodeType.TASK)) > 0
    )
)
```

`_generate_create_instance_code` 会扫描所有 Task，并为每个 Task 生成一个 token element 初始化项：

```py
tasks = choreography.query_element_with_type(NodeType.TASK)
tokenelements = [
    {
        "id": task.id,
        "documentation": json.dumps(self._merge_task_with_dataobject(task))
    }
    for task in tasks
]
```

然后交给模板层：

```py
snippet.CreateInstance_code(
    start_event=start_event.id,
    end_events=[end_event.id for end_event in end_events],
    messages=[...],
    gateways=[gateway.id for gateway in gateways],
    participants=participant_to_be_added,
    business_rules=business_rules,
    tokenelements=tokenelements,
)
```

`snippet.py` 中会把合并后的 JSON 压缩后填入 `InitTokenElementFrame`：

```py
def InitTokenElement(tokenelementID: str, documentation: str) -> str:
    data = json.loads(documentation)
    documentation = json.dumps(data, separators=(',', ':'))
    return content["InitTokenElementFrame"].format(
        TokenelementId=tokenelementID,
        format=documentation
    )
```

`snippet.json` 中的通用结构体定义包含：

- `FlatokenElement`: 用来从 JSON 反序列化前端/translator 合并后的字段。
- `TokenElement`: 链码运行时保存的资产操作节点。
- `Token`: 链码运行时保存的 Token 对象。

`CreateTokenElement` 会把 `FlatokenElement` 转成 `TokenElement`，并放进：

```go
instance.InstanceTokenElements[tokenElementID] = &tokenElement
```

这一步相当于把前端建模配置落到链码实例状态中。

## Asset Task 到模板函数的映射

文件：

- `../py_translator/translator.py`
- `../py_translator/chaincode_snippet/snippet.py`
- `../py_translator/chaincode_snippet/snippet.json`

真正为每个 Asset Task 生成 Go 函数的是 `_generate_chaincode_for_tokenElement`。

主流程：

```py
doc_data = self._merge_task_with_dataobject(task)

token_type = doc_data.get("tokenType")
token_operation = doc_data.get("operation")
token_assetType = doc_data.get("assetType")
```

之后 translator 根据 `assetType`、`tokenType`、`operation` 选择不同模板。

### transferable NFT

```py
if token_type == "NFT":
    if token_operation == "mint":
        snippet.NFTMint_code(activityId=task.id, after_all_hook=after_all_hook)
    elif token_operation == "Transfer":
        snippet.NFTTransfer_code(activityId=task.id, after_all_hook=after_all_hook)
    elif token_operation == "burn":
        snippet.NFTBurn_code(activityId=task.id, after_all_hook=after_all_hook)
    elif token_operation == "query":
        snippet.NFTQuery_code(activityId=task.id, after_all_hook=after_all_hook, filed=filed)
```

对应 `snippet.py`：

```py
def NFTMint_code(activityId: str, after_all_hook: str = ""):
    return content["NFTMintFrame"].format(
        activityId=activityId,
        after_all_hook=after_all_hook,
    )
```

最终使用 `snippet.json` 中的 `NFTMintFrame`、`NFTTransferFrame`、`NFTBurnFrame`、`NFTQueryFrame` 等 Go 代码模板。

### transferable FT

```py
elif token_type == "FT":
    if token_operation == "mint":
        snippet.FTMint_code(...)
    elif token_operation == "Transfer":
        snippet.FTTransfer_code(...)
    elif token_operation == "burn":
        snippet.FTBurn_code(...)
    elif token_operation == "query":
        snippet.FTQuery_code(...)
```

FT 查询输出一般使用 `number` 类型，所以 query 时会调用：

```py
filed = self._generate_query_output_filed(outputs, "number")
```

### distributive

```py
elif token_assetType == "distributive":
    if token_operation == "mint":
        snippet.DistributiveMint_code(...)
    elif token_operation == "grant usage rights":
        snippet.DistributiveApprove_code(...)
    elif token_operation == "burn":
        snippet.DistributiveBurn_code(...)
    elif token_operation == "revoke usage rights":
        snippet.DistributiveDisapprove_code(...)
    elif token_operation == "transfer":
        snippet.DistributiveTransfer_code(...)
    elif token_operation == "query":
        snippet.DisQuery_code(...)
```

这些方法会分别填充 `snippet.json` 中的：

- `DisMintFrame`
- `DisApproveFrame`
- `DisBurnFrame`
- `DisDisapproveFrame`
- `DisTransferFrame`
- `DisQueryFrame`

### value-added

```py
elif token_assetType == "value-added":
    if token_operation == "branch":
        snippet.AddValueMint_code(...)
    elif token_operation == "merge":
        snippet.AddValueMint_code(...)
    elif token_operation == "Transfer":
        snippet.NFTTransfer_code(...)
    elif token_operation == "burn":
        snippet.NFTBurn_code(...)
    elif token_operation == "query":
        snippet.AddValueQuery_code(...)
```

这里 `branch` 和 `merge` 都复用 `AddValueMint_code`，对应 `snippet.json` 中的 `AddValueMintFrame`。该模板会生成两个函数：

- `{activityId}`: 触发资产上传事件，将 TokenElement 设置为 `WAITINGFORCONFIRMATION`。
- `{activityId}_Continue`: 读取上传后的 URL/CID，调用 ERC5521 的 `SafeMint`，并写入引用关系。

其中 `refTokenIds` 会在模板中被加上 `bpmnID-instanceID-` 前缀后传给 ERC5521：

```go
tempRefTokenIds := tokenElement.RefTokenIds
for i := 0; i < len(tempRefTokenIds); i++ {
    tempRefTokenIds[i] = bpmnID + "-" + instanceID + "-" + tempRefTokenIds[i]
}
```

这就是前端 value-added 连线自动维护 `refTokenIds` 的后端消费位置。

## 查询输出字段生成

文件：

- `../py_translator/translator.py`

前端在 AssetTaskModal 中配置的 `outputs` 会影响 query 类模板。translator 通过 `_generate_query_output_filed` 生成 Go 的 `switch name` 写入片段。

```py
for name, spec in outputs.items():
    field_name = public_the_name(name)
    datatype = spec.get("dataType")
    if data_type == datatype:
        lines.append(f'\tcase "{name}":')
        lines.append(f'\t\tinstance.InstanceStateMemory.{field_name} = value')
```

同时，`generate_chaincode` 会扫描所有 Task 的 `outputs`，为 `StateMemory` 增加字段：

```py
for task in self._choreography.query_element_with_type(NodeType.TASK):
    merged_doc = self._merge_task_with_dataobject(task)
    outputs = merged_doc.get("outputs", {})

    for name, info in outputs.items():
        data_type = info.get("dataType")
        field_name = public_the_name(name)
        go_type = type_change_from_bpmn_to_go(data_type)
        output_fields[field_name] = (
            f'{field_name} {go_type} `json:"{field_name}"`'
        )
```

这表示前端 query 输出字段会变成链码 `StateMemory` 的字段。比如：

```json
{
  "outputs": {
    "owner": {
      "type": "owner",
      "dataType": "string"
    }
  }
}
```

会生成类似：

```go
type StateMemory struct {
    Owner string `json:"Owner"`
}
```

并在 query 模板中把查询结果写入：

```go
instance.InstanceStateMemory.Owner = value
```

## FFI 生成中的 Asset 方法

文件：

- `../py_translator/translator.py`

除了链码字符串，translator 还会生成 FireFly FFI。`generate_ffi` 会扫描所有节点，遇到 `NodeType.TASK` 时调用 `_generate_ffi_items_for_tokenTask`：

```py
for element in self._choreography.nodes:
    match element.type:
        case NodeType.TASK:
            ffi_items.extend(self._generate_ffi_items_for_tokenTask(element))
```

每个 Asset Task 至少生成一个同名方法：

```py
items = [
    self._generate_ffi_item(
        name=task.id,
        pathname=task.id,
        params=[
            {
                "name": "InstanceID",
                "schema": {"type": "string"},
            }
        ],
    )
]
```

对于需要异步上传/继续确认的资产操作，还会额外生成 `{task.id}_Continue`：

```py
if (
    (token_operation == "mint" and token_Type == "NFT") or
    (token_assetType == "distributive" and token_operation == "mint") or
    (token_assetType == "value-added" and (token_operation == "branch" or token_operation == "merge"))
):
    items.append(
        self._generate_ffi_item(
            name=continue_method,
            pathname=continue_method,
            params=[{"name": "InstanceID", "schema": {"type": "string"}}],
        )
    )
```

这与模板中的 `_Continue` 函数保持对应。

## 前后端字段对应关系

| 前端字段 | 保存位置 | translator 读取位置 | 生成影响 |
| --- | --- | --- | --- |
| `assetType` | DataObject `documentation` | `_merge_task_with_dataobject` | 决定 distributive / value-added 模板分支 |
| `tokenType` | DataObject `documentation` | `_merge_task_with_dataobject` | 决定 NFT / FT 模板分支 |
| `tokenName` | DataObject `documentation` | `CreateTokenElement` 模板 | FT token key 或 token 元数据 |
| `tokenId` | DataObject `documentation` | `CreateTokenElement` 模板 | NFT/distributive/value-added token key |
| `tokenHasExistInERC` | DataObject `documentation` | `CreateTokenElement` 模板 | 决定是否给 tokenId 加 BPMN/Instance 前缀 |
| `refTokenIds` | DataObject `documentation` | `AddValueMintFrame` | value-added SafeMint 引用关系 |
| `operation` | Task `documentation` | `_generate_chaincode_for_tokenElement` | 决定具体 Go 函数模板 |
| `caller` | Task `documentation` | `CreateTokenElement` 模板 | 链码运行时身份校验 |
| `callee` | Task `documentation` | `CreateTokenElement` 模板 | transfer / 授权 / 撤权目标 |
| `tokenNumber` | Task `documentation` | `CreateTokenElement` 模板 | FT 或操作数量 |
| `outputs` | Task `documentation` | `generate_chaincode` / `_generate_query_output_filed` | 生成 StateMemory 字段和 query 写入逻辑 |

## 前后端建模约束

因此前端建模需要保证：

1. Asset Task 使用 `bpmn:Task`。
2. Asset 对象使用 `bpmn:DataObjectReference`。
3. 资产定义写入 DataObject 的 `documentation`。
4. 操作定义写入 Task 的 `documentation`。
5. Task 与 DataObject 的连接方向符合操作语义。
6. `mint`、`branch`、`merge` 需要能通过 `DataOutputAssociation` 找到输出 DataObject。
7. `transfer`、`burn`、`query`、授权、撤权需要能通过 `DataInputAssociation` 找到输入 DataObject。
8. query 操作如果需要把结果写入链码状态，需要在 Task 的 `outputs` 中声明输出字段和数据类型。

## 快速定位清单

| 功能 | 文件 |
| --- | --- |
| 绘图页面入口 | `src/views/BPMN/Chor-js/index.tsx` |
| Asset Task palette | `src/views/BPMN/Chor-js/lib-provider/assettask-elements/AssetTaskPaletteProvider.js` |
| DataObject palette | `src/views/BPMN/Chor-js/lib-provider/data-elements/DataPaletteProvider.js` |
| DataObject/Task 右键连接菜单 | `src/views/BPMN/Chor-js/lib-provider/data-elements/DataContextPadProvider.js` |
| 双击弹窗分发 | `src/views/BPMN/Chor-js/pop-up/MainPage.tsx` |
| DataObject 资产定义弹窗 | `src/views/BPMN/Chor-js/pop-up/AssetModal.tsx` |
| Task 资产操作弹窗 | `src/views/BPMN/Chor-js/pop-up/AssetTaskModal.tsx` |
| 连线规则 | `src/views/BPMN/Chor-js/chor-js/features/rules/ChoreoRules.js` |
| DataAssociation 建模增强 | `src/views/BPMN/Chor-js/chor-js/features/modeling/ChoreoModeling.js` |
| refTokenIds/连线标签同步 | `src/views/BPMN/Chor-js/chor-js/features/modeling/behavior/DataAssociationBehavior.js` |
| Asset 连接校验 | `src/views/BPMN/Chor-js/lib-provider/validator/constraints/AssetTaskConnectionConstraint.js` |
| Asset 操作校验 | `src/views/BPMN/Chor-js/lib-provider/validator/constraints/AssetTaskOperationConstraint.js` |
