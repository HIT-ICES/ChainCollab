# Asset 建模重构方案（最终版）

> 本文只描述代码修改方案，不讨论论文表述。
>
> 最终目标：**保持当前前端交互方式基本不变，仅替换底层建模类型、持久化方式和解析逻辑；translator 后续链码生成逻辑保持不变。**

---

## 1. 总体修改原则

本次允许修改：

- 前端 Asset 元素底层类型；
- Asset Operation 的保存方式；
- Asset 与 ChoreographyTask 的输入/输出关联实现；
- 前端校验规则；
- BPMN XML 扩展结构；
- Python parser / compatibility adapter。

本次不修改：

- translator 后续的 `doc_data` 消费逻辑；
- `_generate_chaincode_for_tokenElement()` 的业务分支；
- `snippet.py`；
- `snippet.json`；
- `CreateInstance` 的 TokenElement 初始化语义；
- `FlatokenElement` / `TokenElement` / `Token`；
- FFI；
- 最终生成的 Fabric Go chaincode 业务逻辑。

最终兼容边界：

```text
新前端模型
    ↓
新 XML
    ↓
Parser / Compatibility Adapter
    ↓
Legacy merged doc_data
=================================
以下保持不变
    ↓
现有 translator
    ↓
现有 snippets
    ↓
现有 Go chaincode
```

最关键要求：

```text
新 parser 输出的数据结构
==
旧 _merge_task_with_dataobject() 输出的数据结构
```

---

# 2. 当前建模方式

当前实现：

```text
Asset
= bpmn:DataObjectReference

Asset Task
= bpmn:Task

Asset → Task
= bpmn:DataInputAssociation

Task → Asset
= bpmn:DataOutputAssociation

Asset 属性
= DataObject.documentation(JSON)

Asset Task 操作
= Task.documentation(JSON)
```

translator 最终执行：

```text
Task documentation
    +
DataObject documentation
    ↓
_merge_task_with_dataobject()
    ↓
legacy doc_data
```

例如：

```json
{
  "assetType": "transferable",
  "tokenType": "NFT",
  "tokenName": "ProductNFT",
  "tokenId": "token-001",
  "tokenHasExistInERC": false,
  "operation": "Transfer",
  "caller": "Participant_A",
  "callee": ["Participant_B"]
}
```

后续链码生成都依赖这份结构。

---

# 3. 新建模方式

本次新增两个 AssetBlockCollab 领域建模元素：

```text
abc:Asset
abc:AssetOperation
```

新的关系：

```text
abc:Asset
    │
    │ AssetInputReference
    ▼
bpmn:ChoreographyTask
    │
    └── abc:AssetOperation
    │
    │ AssetOutputReference
    ▼
abc:Asset
```

注意：

```text
AssetOperation 不是 ChoreographyTask 的子类。

Asset-enabled ChoreographyTask
=
标准 bpmn:ChoreographyTask
+
abc:AssetOperation extension
```

因此，旧的：

```text
AssetTask extends Task
Asset extends DataObject
AssetInputAssociation extends DataAssociation
AssetOutputAssociation extends DataAssociation
```

全部退出实现。

---

# 4. 前端用户交互保持不变

用户仍然按照当前方式建模：

```text
1. 从 Palette 创建 Asset

2. 双击 Asset
   ↓
   AssetModal
   ↓
   配置 assetType / tokenType / tokenName / tokenId 等

3. 创建标准 ChoreographyTask

4. 双击 / ContextPad 配置 Asset Operation
   ↓
   AssetOperationModal

5. 画输入输出连线

Asset A ─────▶ ChoreographyTask

ChoreographyTask ─────▶ Asset B
```

因此：

- 不引入 Asset Manager；
- 不取消 Asset 画布节点；
- 不取消连线操作；
- 不要求用户手工填写 `inputAssetRefs` / `outputAssetRefs`；
- 不要求用户手工填写 Participant ID。

本次重构主要改变底层实现，不改变用户建模习惯。

---

# 5. 新增 `abc:Asset`

## 5.1 Asset 仍然作为画布元素

当前：

```js
const shape = elementFactory.createShape({
  type: 'bpmn:DataObjectReference'
});
```

修改为：

```js
const shape = elementFactory.createShape({
  type: 'abc:Asset'
});
```

Asset 的视觉样式继续复用当前 Asset/DataObject 图标和画布风格。

变化仅是 businessObject：

```text
旧：
bpmn:DataObjectReference

新：
abc:Asset
```

---

## 5.2 Asset 字段

保留当前后端需要的字段：

```text
id
assetType
tokenType
tokenName
tokenId
tokenHasExistInERC
```

例如：

```xml
<abc:asset
    id="Asset_Product"
    assetType="transferable"
    tokenType="NFT"
    tokenName="ProductNFT"
    tokenId="token-001"
    tokenHasExistInERC="false" />
```

`refTokenIds` 不再作为 Asset 上的人工编辑字段。

value-added 的 `refTokenIds` 后续由 parser 根据：

```text
inputAssetRefs
```

自动推导。

---

# 6. AssetModal 修改

当前：

```text
AssetModal
→ DataObject.documentation
→ JSON.parse / JSON.stringify
```

修改为：

```text
AssetModal
→ abc:Asset businessObject 属性
```

读取：

```ts
const bo = shape.businessObject;

bo.assetType;
bo.tokenType;
bo.tokenName;
bo.tokenId;
bo.tokenHasExistInERC;
```

保存：

```ts
modeling.updateProperties(assetElement, {
  assetType,
  tokenType,
  tokenName,
  tokenId,
  tokenHasExistInERC,
});
```

不再写：

```text
bpmn:documentation
```

---

# 7. 原 AssetTask 改为复用 ChoreographyTask

当前 Asset Task palette 实际创建：

```js
elementFactory.create(
  'shape',
  { type: 'bpmn:Task' }
)
```

该逻辑退出。

以后资产操作直接配置到标准：

```text
bpmn:ChoreographyTask
```

因此：

```text
旧：

AssetTask
=
bpmn:Task
```

改成：

```text
新：

Asset Task（UI 概念）
=
bpmn:ChoreographyTask
+
abc:AssetOperation
```

前端可以继续保留：

```text
Asset Operation
```

图标、菜单入口或 Task 标记。

但是底层不再创建独立的：

```text
bpmn:Task
```

---

# 8. 新增 `abc:AssetOperation`

`AssetOperation` 附着到 ChoreographyTask 的：

```text
extensionElements
```

中。

字段：

```text
operation

inputAssetRefs
outputAssetRefs

recipientRefs

tokenNumber
outputs
```

其中：

```text
inputAssetRefs
outputAssetRefs
recipientRefs
```

都不允许用户手工填写 ID。

---

## 8.1 示例

普通 transfer：

```xml
<bpmn:choreographyTask
    id="Task_Transfer"
    initiatingParticipantRef="Participant_A">

    <bpmn:extensionElements>

        <abc:assetOperation
            operation="Transfer"
            inputAssetRefs="Asset_Product" />

    </bpmn:extensionElements>

</bpmn:choreographyTask>
```

---

# 9. AssetOperationModal 修改

建议：

```text
AssetTaskModal.tsx
→
AssetOperationModal.tsx
```

绑定对象从：

```text
bpmn:Task
```

修改为：

```text
bpmn:ChoreographyTask
```

保留：

```text
operation
tokenNumber
outputs
```

根据 operation 条件性增加：

```text
recipients
```

删除：

```text
caller
callee

assetType
tokenType
tokenName
tokenId
tokenHasExistInERC
```

其中：

```text
caller / callee
→ 根据 ChoreographyTask + operation 自动得到

Asset 信息
→ 根据 inputAssetRefs / outputAssetRefs 获取
```

---

# 10. caller / callee 总体规则

这是本次修改的重点。

原则：

```text
caller
始终复用 ChoreographyTask 的 initiatingParticipantRef

callee
根据 operation 分类处理
```

不再统一要求用户填写 caller / callee。

---

# 11. caller 规则

所有资产操作统一：

```text
caller
=
initiatingParticipantRef
```

例如：

```xml
initiatingParticipantRef="Participant_A"
```

parser 输出：

```json
{
  "caller": "Participant_A"
}
```

---

# 12. callee 根据 operation 分类

最终规则如下：

| operation | caller 来源 | callee 来源 | recipientRefs |
|---|---|---|---|
| `mint` | `initiatingParticipantRef` | `[]` | 不使用 |
| `burn` | `initiatingParticipantRef` | `[]` | 不使用 |
| `query` | `initiatingParticipantRef` | `[]` | 不使用 |
| `branch` | `initiatingParticipantRef` | `[]` | 不使用 |
| `merge` | `initiatingParticipantRef` | `[]` | 不使用 |
| `Transfer` / `transfer` | `initiatingParticipantRef` | ChoreographyTask receiving participant | 默认不使用 |
| `grant usage rights` | `initiatingParticipantRef` | `recipientRefs` | 支持多个 |
| `revoke usage rights` | `initiatingParticipantRef` | `recipientRefs` | 支持多个 |

---

# 13. Transfer 的 callee

普通 Transfer：

```text
Seller → Buyer
```

不在 AssetOperation 中重复配置 callee。

parser：

```text
caller
=
initiatingParticipantRef
```

然后：

```text
callee
=
participantRefs - initiatingParticipantRef
```

例如：

```text
initiatingParticipantRef:
Participant_Seller

participantRefs:
Participant_Seller
Participant_Buyer
```

生成：

```json
{
  "caller": "Participant_Seller",
  "callee": [
    "Participant_Buyer"
  ]
}
```

必须继续保持：

```text
callee = array
```

即使只有一个 callee，也不要改成字符串。

---

# 14. grant/revoke usage rights 的多个 callee

由于 distributive asset 的：

```text
grant usage rights
revoke usage rights
```

可能作用于多个目标参与方，因此新增：

```text
recipientRefs [0..*]
```

`recipientRefs` 不是 BPMN ChoreographyTask participant 的替代品。

它的语义是：

```text
asset operation targets
```

只用于一对多资产授权目标。

例如：

```xml
<abc:assetOperation
    operation="grant usage rights"
    inputAssetRefs="Asset_Book"
    recipientRefs="Participant_B Participant_C Participant_D" />
```

parser 输出旧结构：

```json
{
  "caller": "Participant_A",
  "callee": [
    "Participant_B",
    "Participant_C",
    "Participant_D"
  ]
}
```

因此 downstream translator 不需要认识：

```text
recipientRefs
```

---

# 15. recipientRefs 的前端交互

`recipientRefs` 不允许用户直接填写：

```text
Participant_B Participant_C
```

这种 ID 字符串。

AssetOperationModal 应根据 operation 动态显示。

## mint / burn / query / branch / merge

不显示：

```text
Recipient
```

---

## Transfer / transfer

不显示 Recipient 多选框。

可以只读显示：

```text
Recipient:
Participant_B

Derived from ChoreographyTask
```

---

## grant usage rights / revoke usage rights

显示多选：

```text
Recipients

☑ Participant B
☑ Participant C
☑ Participant D
```

前端内部保存：

```text
recipientRefs
```

---

# 16. caller/callee parser 函数

建议新增：

```python
def derive_caller_and_callee(
    choreo_task,
    asset_operation
):
    caller = choreo_task.initiatingParticipantRef
    operation = asset_operation.operation

    if operation in [
        "mint",
        "burn",
        "query",
        "branch",
        "merge",
    ]:
        return caller, []

    if operation in [
        "grant usage rights",
        "revoke usage rights",
    ]:
        return (
            caller,
            asset_operation.recipientRefs or []
        )

    if operation in [
        "Transfer",
        "transfer",
    ]:
        callee = [
            participant
            for participant
            in choreo_task.participantRefs
            if participant != caller
        ]

        return caller, callee

    return caller, []
```

最终 translator 仍然只看到：

```json
{
  "caller": "...",
  "callee": [...]
}
```

---

# 17. 输入/输出 Asset 连线交互保持不变

用户仍然通过拖线表达：

```text
Asset → ChoreographyTask
```

以及：

```text
ChoreographyTask → Asset
```

但是底层不再创建：

```text
bpmn:DataInputAssociation
bpmn:DataOutputAssociation
```

---

# 18. 新 Asset Reference 语义

视觉连接定义为：

```text
abc:AssetInputReference
abc:AssetOutputReference
```

其中：

```text
Asset → ChoreographyTask
=
AssetInputReference
```

以及：

```text
ChoreographyTask → Asset
=
AssetOutputReference
```

但是实际业务持久化字段是：

```text
inputAssetRefs
outputAssetRefs
```

因此：

```text
refs
=
持久化业务数据

connection
=
前端视觉 projection
```

---

# 19. 新建连线时自动维护 refs

## Asset → Task

用户：

```text
Asset_A → Task_X
```

前端：

```js
addInputAssetRef(
  taskX,
  assetA.id
)
```

结果：

```xml
<abc:assetOperation
    operation="Transfer"
    inputAssetRefs="Asset_A" />
```

---

## Task → Asset

用户：

```text
Task_X → Asset_B
```

前端：

```js
addOutputAssetRef(
  taskX,
  assetB.id
)
```

结果：

```xml
<abc:assetOperation
    operation="mint"
    outputAssetRefs="Asset_B" />
```

---

# 20. 删除连线时同步 refs

删除：

```text
Asset_A → Task_X
```

执行：

```js
removeInputAssetRef(
  taskX,
  assetA.id
)
```

删除：

```text
Task_X → Asset_B
```

执行：

```js
removeOutputAssetRef(
  taskX,
  assetB.id
)
```

---

# 21. 加载 XML 时恢复视觉连线

解析：

```text
inputAssetRefs
outputAssetRefs
```

然后重新绘制：

```text
AssetInputReference
AssetOutputReference
```

因此不再依赖：

```text
DataInputAssociation
DataOutputAssociation
```

恢复 Asset 连线。

---

# 22. operation 对应的 Asset Reference 数量

| operation | inputAssetRefs | outputAssetRefs |
|---|---:|---:|
| `mint` | 0 | 1 |
| `Transfer` / `transfer` | 1 | 0 |
| `burn` | 1 | 0 |
| `query` | 1 | 0 |
| `grant usage rights` | 1 | 0 |
| `revoke usage rights` | 1 | 0 |
| `branch` | 1..* | 1 |
| `merge` | 2..* | 1 |

用户仍然通过画线建立这些关系。

---

# 23. ChoreoRules 修改

当前主要判断：

```text
bpmn:DataObjectReference
+
bpmn:Task
```

修改为：

```text
abc:Asset
+
bpmn:ChoreographyTask
```

---

## mint

允许：

```text
Task → Asset
```

禁止：

```text
Asset → Task
```

---

## Transfer / burn / query / grant / revoke

允许：

```text
Asset → Task
```

禁止：

```text
Task → Asset
```

---

## branch / merge

允许：

```text
Asset A ─┐
         ├──▶ Task
Asset B ─┘

Task ───▶ Asset C
```

---

# 24. Validator 修改

旧：

```text
AssetTaskConnectionConstraint
AssetTaskOperationConstraint
```

建议调整为：

```text
AssetReferenceConstraint
AssetOperationConstraint
AssetRecipientConstraint
```

---

# 25. AssetReferenceConstraint

检查：

```text
inputAssetRefs
outputAssetRefs
```

包括：

- 引用的 Asset 是否存在；
- input 数量是否正确；
- output 数量是否正确；
- 是否存在重复引用；
- 是否违反 operation 对应的方向约束。

例如：

```text
mint:
input = 0
output = 1

branch:
input >= 1
output = 1

merge:
input >= 2
output = 1
```

---

# 26. AssetOperationConstraint

继续检查：

```text
assetType
tokenType
operation
```

之间的兼容关系。

例如：

```text
transferable NFT
→ mint / Transfer / burn / query
```

```text
distributive
→ mint
→ transfer
→ burn
→ query
→ grant usage rights
→ revoke usage rights
```

```text
value-added
→ branch
→ merge
→ Transfer
→ burn
→ query
```

---

# 27. AssetRecipientConstraint

根据 operation 检查 recipient：

```text
mint
burn
query
branch
merge

→ recipientRefs 必须为空
```

```text
Transfer / transfer

→ 默认不使用 recipientRefs
→ receiving participant 必须可以从 ChoreographyTask 得到
```

```text
grant usage rights
revoke usage rights

→ recipientRefs 至少包含一个 Participant
```

同时：

```text
recipientRefs 中引用的 Participant 必须存在。
```

---

# 28. value-added 的 refTokenIds

旧：

```text
DataAssociationBehavior
    ↓
输入 DataObject.tokenId
    ↓
输出 DataObject.refTokenIds
```

新：

```text
Asset_A ─┐
         ├──▶ Task_Branch ───▶ Asset_C
Asset_B ─┘
```

持久化：

```text
inputAssetRefs
=
[Asset_A, Asset_B]

outputAssetRefs
=
[Asset_C]
```

parser：

```python
ref_token_ids = [
    assets_by_id[asset_id]["tokenId"]
    for asset_id
    in input_asset_refs
    if assets_by_id[asset_id].get("tokenId")
]
```

输出：

```json
{
  "refTokenIds": [
    "token-A",
    "token-B"
  ]
}
```

因此：

```text
AddValueMintFrame
```

完全不修改。

---

# 29. outputs 保存

query 仍然需要：

```text
outputs
```

因为 translator 会根据它生成：

```text
StateMemory
```

例如：

```xml
<abc:assetOperation
    operation="query"
    inputAssetRefs="Asset_Product">

    <abc:outputs>

        <abc:output
            name="owner"
            type="owner"
            dataType="string" />

    </abc:outputs>

</abc:assetOperation>
```

parser 恢复：

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

现有：

```text
_generate_query_output_filed()
```

和 StateMemory 生成逻辑保持不变。

---

# 30. moddle extension

新增：

```text
src/views/BPMN/Chor-js/moddle/asset.json
```

核心定义：

```text
Asset
AssetOperation
Output
```

如果：

```text
AssetInputReference
AssetOutputReference
```

只用于 diagram-js 视觉层，则不必把连接本身作为真实业务对象持久化。

推荐：

```text
XML 持久化 refs
    ↓
重新加载
    ↓
根据 refs 恢复 connection
```

---

# 31. Parser 的职责

Parser 负责把：

```text
abc:Asset
+
abc:AssetOperation
+
ChoreographyTask participant
+
input/output AssetRefs
+
recipientRefs
```

转换成：

```text
legacy merged doc_data
```

从这个边界之后，translator 不需要知道建模方式已经变化。

---

# 32. Asset Registry Parser

遍历所有：

```text
abc:Asset
```

形成：

```python
assets_by_id = {

    "Asset_Product": {

        "assetType": "transferable",

        "tokenType": "NFT",

        "tokenName": "ProductNFT",

        "tokenId": "token-001",

        "tokenHasExistInERC": False
    }
}
```

---

# 33. AssetOperation Parser

遍历：

```text
bpmn:ChoreographyTask
```

检查：

```text
abc:AssetOperation
```

存在则认为：

```text
Asset-enabled ChoreographyTask
```

解析：

```text
operation

inputAssetRefs
outputAssetRefs

recipientRefs

tokenNumber

outputs
```

---

# 34. 主 Asset 选择规则

为了保证现有链码生成逻辑不变，继续沿用旧 DataAssociation 的方向语义。

## 创建型操作

```text
mint
branch
merge
```

主 Asset：

```text
outputAssetRefs[0]
```

---

## 已有资产操作

```text
Transfer
transfer
burn
query
grant usage rights
revoke usage rights
```

主 Asset：

```text
inputAssetRefs[0]
```

---

# 35. build_legacy_asset_doc

建议集中实现：

```python
def build_legacy_asset_doc(
    choreo_task,
    asset_operation,
    assets_by_id
):

    result = {}

    operation = asset_operation.operation


    if operation in [
        "mint",
        "branch",
        "merge"
    ]:

        main_asset_id = (
            asset_operation.outputAssetRefs[0]
        )

    else:

        main_asset_id = (
            asset_operation.inputAssetRefs[0]
        )


    main_asset = assets_by_id[
        main_asset_id
    ]


    for key in [
        "assetType",
        "tokenType",
        "tokenName",
        "tokenId",
        "tokenHasExistInERC",
    ]:

        if key in main_asset:
            result[key] = main_asset[key]


    result["operation"] = operation


    caller, callee = (
        derive_caller_and_callee(
            choreo_task,
            asset_operation
        )
    )


    result["caller"] = caller
    result["callee"] = callee


    if asset_operation.tokenNumber is not None:

        result["tokenNumber"] = (
            asset_operation.tokenNumber
        )


    if asset_operation.outputs:

        result["outputs"] = (
            asset_operation.outputs
        )


    if operation in [
        "branch",
        "merge"
    ]:

        result["refTokenIds"] = [

            assets_by_id[
                asset_id
            ]["tokenId"]

            for asset_id
            in asset_operation.inputAssetRefs

            if assets_by_id[
                asset_id
            ].get("tokenId")

        ]


    return result
```

---

# 36. AssetTaskProjection

为了避免修改 translator 后续逻辑，parser 生成 Python 内存兼容对象：

```text
AssetTaskProjection
```

它不是 BPMN XML 中的新流程节点。

只是：

```text
Compatibility Object
```

关系：

```text
ChoreographyTask
+
AssetOperation
+
Asset
+
Participants
    ↓
AssetTaskProjection
```

必须保证：

```text
projection.id
=
原 ChoreographyTask.id
```

因为现有链码函数生成使用：

```text
activityId = task.id
```

---

# 37. Projection.documentation

新 XML 中不再使用：

```text
bpmn:documentation
```

保存 Asset 信息。

但是 Python 内存兼容层可以继续：

```python
projection.documentation = json.dumps(
    legacy_doc
)
```

需要区分：

```text
BPMN XML documentation
→ 删除 Asset JSON 使用

Python compatibility documentation
→ 保留作为内部数据接口
```

---

# 38. NodeType.TASK 兼容

当前 translator 大量调用：

```python
query_element_with_type(
    NodeType.TASK
)
```

因此 parser 应让：

```text
AssetTaskProjection
```

继续通过：

```text
NodeType.TASK
```

返回。

这样以下代码尽量完全不修改：

```text
_generate_create_instance_code()

_generate_chaincode_for_tokenElement()

_generate_ffi_items_for_tokenTask()

StateMemory outputs 扫描
```

---

# 39. `_merge_task_with_dataobject()` 最小修改

建议保留函数名。

V2：

```python
def _merge_task_with_dataobject(
    self,
    task
):

    if getattr(
        task,
        "is_asset_projection",
        False
    ):

        return json.loads(
            task.documentation
        )


    # legacy V1 logic
    ...
```

这样同时支持：

```text
V1

Task
+
DataObject
+
DataAssociation
```

和：

```text
V2

ChoreographyTask
+
AssetOperation
+
Asset
```

最终两种模型都得到：

```text
legacy doc_data
```

---

# 40. operation 字符串本次不修改

当前实现存在：

```text
Transfer
transfer
```

等历史字符串差异。

因为 translator 当前按字符串选择模板，本次不要顺便修改 operation 命名。

原则：

```text
只换模型来源
不换后端数据协议
```

---

# 41. 不修改 translator 后半段

继续使用：

```python
token_type = doc_data.get(
    "tokenType"
)

token_operation = doc_data.get(
    "operation"
)

token_assetType = doc_data.get(
    "assetType"
)
```

后面的：

```text
NFTMint_code
NFTTransfer_code
NFTBurn_code
NFTQuery_code

FTMint_code
FTTransfer_code
FTBurn_code
FTQuery_code

DistributiveMint_code
DistributiveApprove_code
DistributiveDisapprove_code
DistributiveTransfer_code
DistributiveBurn_code
DisQuery_code

AddValueMint_code
```

全部保持不变。

---

# 42. 明确禁止修改

原则上零修改：

```text
../py_translator/chaincode_snippet/snippet.py

../py_translator/chaincode_snippet/snippet.json
```

以及：

```text
FlatokenElement

TokenElement

Token

CreateTokenElement

Asset SC invocation

FFI contract
```

---

# 43. 前端主要修改文件

```text
src/views/BPMN/Chor-js/index.tsx

src/views/BPMN/Chor-js/pop-up/MainPage.tsx

src/views/BPMN/Chor-js/pop-up/AssetModal.tsx

src/views/BPMN/Chor-js/pop-up/AssetTaskModal.tsx


src/views/BPMN/Chor-js/lib-provider/assettask-elements/

src/views/BPMN/Chor-js/lib-provider/data-elements/


src/views/BPMN/Chor-js/chor-js/features/rules/ChoreoRules.js

src/views/BPMN/Chor-js/chor-js/features/modeling/ChoreoModeling.js

src/views/BPMN/Chor-js/chor-js/features/modeling/behavior/DataAssociationBehavior.js


src/views/BPMN/Chor-js/lib-provider/validator/
```

---

# 44. 前端新增/重命名

建议新增：

```text
src/views/BPMN/Chor-js/moddle/asset.json

src/views/BPMN/Chor-js/utils/assetExtension.ts
```

建议：

```text
AssetTaskModal.tsx
→
AssetOperationModal.tsx
```

以及：

```text
DataAssociationBehavior.js
→
AssetReferenceBehavior.js
```

原 Asset palette 仍然保留，只是从创建：

```text
bpmn:DataObjectReference
```

修改成：

```text
abc:Asset
```

---

# 45. Python 修改范围

主要：

```text
../py_translator/choreography_parser/parser.py

../py_translator/choreography_parser/elements.py
```

建议新增：

```text
../py_translator/choreography_parser/asset_extension.py
```

职责：

```text
parse_assets()

parse_asset_operation()

resolve_asset_refs()

derive_caller_and_callee()

derive_ref_token_ids()

build_legacy_asset_doc()

create_asset_task_projection()
```

---

# 46. 新旧字段最终映射

| 新模型来源 | Parser 输出 | 现有后端 |
|---|---|---|
| `abc:Asset.assetType` | `assetType` | 不变 |
| `abc:Asset.tokenType` | `tokenType` | 不变 |
| `abc:Asset.tokenName` | `tokenName` | 不变 |
| `abc:Asset.tokenId` | `tokenId` | 不变 |
| `abc:Asset.tokenHasExistInERC` | `tokenHasExistInERC` | 不变 |
| `abc:AssetOperation.operation` | `operation` | 不变 |
| `initiatingParticipantRef` | `caller` | 不变 |
| ChoreographyTask receiving participant | `callee`，用于 Transfer | 不变 |
| `recipientRefs` | `callee`，用于 grant/revoke | 不变 |
| `abc:AssetOperation.tokenNumber` | `tokenNumber` | 不变 |
| `inputAssetRefs` | `refTokenIds`，用于 branch/merge | 不变 |
| `abc:AssetOperation.outputs` | `outputs` | 不变 |

---

# 47. 第一层回归测试：doc_data 等价

同一个业务场景：

```text
旧 BPMN
    ↓
旧 parser
    ↓
_merge_task_with_dataobject()
    ↓
old_doc
```

与：

```text
新 BPMN
    ↓
新 parser
    ↓
AssetTaskProjection
    ↓
new_doc
```

要求：

```python
assert old_doc == new_doc
```

这是本次重构最关键的回归测试。

---

# 48. Golden Test 覆盖

至少覆盖：

```text
transferable NFT
├─ mint
├─ Transfer
├─ burn
└─ query


transferable FT
├─ mint
├─ Transfer
├─ burn
└─ query


distributive
├─ mint
├─ grant usage rights
│  ├─ 单 recipient
│  └─ 多 recipient
├─ revoke usage rights
│  ├─ 单 recipient
│  └─ 多 recipient
├─ transfer
├─ burn
└─ query


value-added
├─ branch
├─ merge
├─ Transfer
├─ burn
└─ query
```

重点比较：

```text
assetType

tokenType

tokenName

tokenId

tokenHasExistInERC

operation

caller

callee

tokenNumber

refTokenIds

outputs
```

---

# 49. 第二层回归测试：生成链码等价

比较：

```text
旧 BPMN
    ↓
generated_old.go
```

和：

```text
新 BPMN
    ↓
generated_new.go
```

确认：

```text
函数名一致

CreateInstance 一致

TokenElement 初始化一致

Asset SC 调用参数一致

caller / callee 一致

refTokenIds 一致

StateMemory 一致

FFI 一致

_Continue 方法一致
```

理想目标：

```text
generated_old.go
==
generated_new.go
```

---

# 50. 推荐实施顺序

```text
Step 1
增加 abc:Asset moddle 定义

Step 2
Asset palette 从 DataObjectReference 改为 abc:Asset

Step 3
AssetModal 从 documentation JSON 改为 abc:Asset 属性

Step 4
增加 abc:AssetOperation

Step 5
AssetTaskModal 改为配置 ChoreographyTask 的 AssetOperation

Step 6
删除 caller/callee 手工配置

Step 7
实现 operation-specific caller/callee 规则

Step 8
为 grant/revoke 增加 recipientRefs 多选

Step 9
DataAssociation 改成 AssetReference visual connection

Step 10
连线自动维护 inputAssetRefs/outputAssetRefs

Step 11
删除 value-added 前端 refTokenIds 同步逻辑

Step 12
修改 ChoreoRules

Step 13
修改 Validator

Step 14
Python parser 解析 abc:Asset

Step 15
Python parser 解析 abc:AssetOperation

Step 16
实现 derive_caller_and_callee()

Step 17
实现 refTokenIds 推导

Step 18
生成 AssetTaskProjection

Step 19
保持 NodeType.TASK compatibility

Step 20
让 _merge_task_with_dataobject() 对 V2 直接返回 projection documentation

Step 21
执行 old_doc == new_doc

Step 22
执行 generated_old.go / generated_new.go 回归测试
```

---

# 51. 最终架构

```text
┌────────────────────────────────────────┐
│               用户交互                 │
│                                        │
│ Asset Palette                          │
│ Asset 图形                             │
│ AssetModal                             │
│ ChoreographyTask                       │
│ AssetOperationModal                    │
│ Asset 输入/输出拖线                    │
│ recipient 多选（仅 grant/revoke）      │
│                                        │
│              基本保持不变              │
└───────────────────┬────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────┐
│            前端底层新模型              │
│                                        │
│ abc:Asset                              │
│ abc:AssetOperation                     │
│ AssetInputReference                    │
│ AssetOutputReference                   │
│ inputAssetRefs                         │
│ outputAssetRefs                        │
│ recipientRefs                          │
└───────────────────┬────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────┐
│        Parser / Compatibility          │
│                                        │
│ Asset resolution                       │
│ operation resolution                   │
│ caller/callee derivation               │
│ recipientRefs → callee                 │
│ inputAssetRefs → refTokenIds           │
│ Legacy AssetTaskProjection             │
└───────────────────┬────────────────────┘
                    │
                    ▼

            Legacy merged doc_data

================================================
               Compatibility Boundary
================================================

                    │
                    ▼
┌────────────────────────────────────────┐
│           Existing Translator          │
│                 不修改                 │
└───────────────────┬────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────┐
│        snippet.py / snippet.json       │
│                 不修改                 │
└───────────────────┬────────────────────┘
                    │
                    ▼
             Existing Go Chaincode
```

---

# 52. 最终原则

本次重构不是重新设计用户的建模方式。

用户仍然看到：

```text
Asset ─────▶ ChoreographyTask ─────▶ Asset
```

仍然使用：

```text
Palette
双击配置
ContextPad
拖线
```

变化的是底层：

```text
旧：

DataObject
+
Task
+
DataAssociation
+
documentation JSON
```

替换成：

```text
新：

Asset
+
AssetOperation
+
AssetReference
+
typed extension
```

Participant 规则最终固定为：

```text
caller
=
ChoreographyTask.initiatingParticipantRef
```

```text
Transfer 的 callee
=
ChoreographyTask receiving participant
```

```text
grant/revoke 的多个 callee
=
AssetOperation.recipientRefs
```

```text
mint / burn / query / branch / merge
=
callee []
```

最后由 parser 将新模型统一恢复成：

```text
legacy merged doc_data
```

因此：

```text
translator 后半段不修改

snippet.py 不修改

snippet.json 不修改

生成链码逻辑不修改
```