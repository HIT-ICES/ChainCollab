# 实例验证

本模块为 BPMN 实例创建提供验证功能,专门检查区块链操作的代币所有权和参与者权限。

## 功能特性

验证器检查以下方面:

### 1. 代币所有权跟踪
- 通过流程流跟踪代币所有权
- 验证操作是由授权参与者执行的
- 确保在销毁/转移操作前代币已被拥有

### 2. 特定操作验证

#### 铸造操作 (Mint)
- 创建新代币并将所有权分配给铸造者
- 要求铸造参与者具有特定用户绑定
- 验证铸造者具有适当的授权

#### 销毁操作 (Burn)
- 要求调用者拥有要销毁的代币
- 销毁后从所有权跟踪中移除代币
- 如果调用者不拥有代币则报告错误

#### 转移操作 (Transfer)
- 要求调用者拥有要转移的代币
- 验证接收者(callee)已正确绑定
- 转移后将代币所有权更新给接收者
- 确保接收者参与者绑定到有效身份

#### 授予/撤销使用权
- 要求调用者拥有代币
- 验证被授权者/被撤销者已指定
- 检查适当的参与者绑定

#### 分支/合并 (Branch/Merge) - 增值型代币
- 验证源代币的所有权
- 将所有权更新给分支/合并参与者
- 特定于增值资产类型

#### 查询操作 (Query)
- 不改变所有权
- **无所有权要求** - 任何参与者都可以查询
- 对所有参与者开放,无论代币所有权如何
- 仅验证调用者的适当参与者绑定

### 3. 代币类型验证
- **FT (同质化代币)**: 验证非查询操作指定了 `tokenNumber`
- **NFT (非同质化代币)**:
  - 验证 `tokenId` 所有权和转移
  - **关键**: NFT 一旦被销毁,就无法对其执行任何进一步操作(查询除外)
  - NFT 代币是唯一的,销毁后无法重新铸造
- **分发型代币**: 验证使用权操作
- **增值型代币**: 验证分支/合并操作和引用代币 ID

### 4. NFT 销毁生命周期验证
- **关键规则**: NFT 代币在被销毁后无法使用
- 一旦对 NFT 执行销毁操作:
  - 转移操作被阻止
  - 销毁操作被阻止(不能销毁两次)
  - 授予/撤销使用权被阻止
  - 分支/合并操作被阻止
  - 只有查询操作仍然允许(检查历史数据)
- **FT 例外**: FT 代币在销毁后可以重新铸造,因为它们是可替代的
- 示例错误: "无法对代币 'TokenA (ID: 123)' 执行 'transfer' 操作,因为它已在任务 'Burn TokenA' 中被销毁。NFT 代币在销毁后无法使用。"

### 5. 参与者绑定验证
- 确保所有调用者都绑定到参与者
- 验证被调用者(接收者)已正确绑定
- 检查绑定类型(equal vs. group)
- 验证敏感操作(如铸造)的特定用户绑定

### 6. ERC 合约绑定一致性
- **关键**: 验证同一代币在所有操作中使用相同的 ERC 合约
- 通过确保铸造、转移、销毁等操作都使用相同合约来防止数据不一致
- 当操作同一代币的不同任务绑定到不同合约时报告错误
- 示例错误: "代币 'rawMaterial' 必须在所有操作中使用相同的 ERC 合约。任务 'mint rawMaterial' 使用 'ERC721Contract_A',但任务 'burn rawMaterial' 使用 'ERC721Contract_B'"

### 7. 已存在代币的预铸造支持 (tokenHasExistInERC)
- **新功能**: 支持标记已在 ERC 合约中存在的代币
- 当 `tokenHasExistInERC = true` 时:
  - 验证器在处理流程前会查询区块链获取代币当前所有者
  - 使用 `OwnerOf` 方法查询 ERC 合约获取所有者身份
  - 解析区块链身份(格式: "MSP::x509::CN=user,OU=client::...")
  - 根据 User CN 匹配参与者绑定
  - 设置初始所有权并标记为已铸造
  - 防止对已存在代币的重复铸造操作
- 支持的 ERC 标准:
  - **ERC721** (可转移型 NFT): 使用 `OwnerOf(tokenId)` 查询
  - **ERC5521** (分发型): 使用 `OwnerOf(tokenId)` 查询
  - **ERC5521** (增值型): 使用 `OwnerOf(tokenId)` 查询
- 区块链查询 URL 构造:
  - 从 BPMN 的 `firefly_url` 提取基础 URL
  - 从 `taskERCMap` 获取 ERC 合约名称
  - 构造完整 URL: `{basefirelfyUrl}/apis/{ercName}`
- 身份匹配逻辑:
  - 解析 MSP ID 和 User CN
  - 匹配 `selectedValidationType === 'equal'` 的参与者
  - 根据 `selectedUser` 字段匹配 User CN

## 使用方法

### 在模态组件中使用

验证功能已集成到 `ParticipantDmnBindingModal` 组件中:

```tsx
import { validateInstance, formatValidationErrors } from "./validator/InstanceValidator";

// 在组件中:
const handleValidation = async () => {
  const bpmn = await retrieveBPMN(bpmnId);
  const bpmnXml = bpmn.content || bpmn.bpmnContent || bpmn.xml;
  const fireflyUrl = bpmn.firefly_url;

  const result = await validateInstance(
    bpmnXml,
    showBindingParticipantValueMap,
    showTaskERCMap,
    fireflyUrl  // 传递 firefly URL 用于区块链查询
  );

  if (result.isValid) {
    message.success('验证通过!');
  } else {
    // 显示错误
    setValidationErrors(result.errors);
  }
};
```

### 验证按钮

点击模态框中的"验证实例"按钮以:
1. 检查所有代币操作与参与者绑定
2. 验证整个流程中的代币所有权链
3. 显示详细的错误和警告消息

## 验证结果结构

```typescript
interface ValidationResult {
  isValid: boolean;      // 如果没有错误则为 true(警告可以接受)
  errors: ValidationError[];
}

interface ValidationError {
  taskId: string;        // 有错误的任务 ID
  taskName: string;      // 用于显示的任务名称
  message: string;       // 详细错误消息
  severity: 'error' | 'warning';
}
```

### 错误严重性级别

- **Error (错误)**: 可能导致实例失败的关键问题。部署前必须修复。
  - 缺少调用者绑定
  - 代币所有权违规
  - 缺少必需字段(如转移的被调用者)
  - 未知操作类型
  - 对已销毁的 NFT 执行操作
  - 同一代币使用不同的 ERC 合约

- **Warning (警告)**: 可能不会阻止执行但应审查的潜在问题。
  - 没有所有权的使用权操作
  - FT 操作缺少代币数量
  - 未指定的可选字段

## 验证规则

### 所有权规则
1. 代币必须先铸造才能使用
2. 只有代币所有者才能销毁或转移代币
3. 转移操作后所有权转移给接收者
4. 多个参与者可以拥有同一代币(用于群组场景)
5. **已存在代币**: 如果代币标记为 `tokenHasExistInERC = true`,验证器会查询区块链确定初始所有者

### 参与者绑定规则
1. 所有调用者必须绑定到参与者
2. 所有被调用者(接收者)必须绑定到参与者
3. 铸造操作应该有特定用户绑定(equal 类型)
4. 大多数操作允许群组绑定

### 代币流规则
1. 代币生命周期遵循序列: 铸造 → 操作 → 销毁
2. 代币在铸造前不能使用
3. 代币在销毁后不能使用(NFT - 查询除外)
4. 增值代币可以通过 `refTokenIds` 引用其他代币

### NFT 特殊规则
1. **NFT 不能重复铸造**: 每个 tokenId 只能铸造一次(除非先销毁)
2. **NFT 销毁后不可用**: 销毁后除查询外不能执行任何操作
3. **FT 可以重复铸造**: 同质化代币销毁后可以重新铸造

## 示例场景

### 有效流程
```
1. 铸造 (制造商) → Token1 由制造商拥有
2. 转移 (制造商 → 批发商) → Token1 由批发商拥有
3. 销毁 (批发商) → Token1 被移除
✅ 所有验证通过
```

### 无效流程
```
1. 铸造 (制造商) → Token1 由制造商拥有
2. 销毁 (供应商) → Token1
❌ 错误: 供应商不拥有 Token1
```

### 缺少绑定
```
1. 铸造 (制造商) → Token1
2. 转移 (制造商 → ???) → 未指定被调用者
❌ 错误: 转移需要接收者
```

### 查询操作(无所有权要求)
```
1. 铸造 (制造商) → Token1 由制造商拥有
2. 查询 (供应商) → 查询 Token1
✅ 有效: 供应商即使不拥有 Token1 也可以查询
3. 查询 (批发商) → 查询 Token1
✅ 有效: 任何参与者都可以查询代币信息
4. 转移 (制造商 → 批发商) → Token1 由批发商拥有
5. 查询 (供应商) → 查询 Token1
✅ 有效: 所有权更改后供应商仍可查询
```

### NFT 销毁生命周期(销毁后无法使用)
```
1. 铸造 (制造商) → NFT Token1 (ID: 123) 由制造商拥有
2. 转移 (制造商 → 供应商) → NFT Token1 由供应商拥有
3. 销毁 (供应商) → NFT Token1 被销毁
4. 转移 (供应商 → 批发商) → NFT Token1
❌ 错误: 无法对代币 "Token1 (ID: 123)" 执行 "transfer" 操作,因为它已在任务 "Burn Token1" 中被销毁
```

### FT 可以重新铸造(与 NFT 不同)
```
1. 铸造 (制造商) → FT Token_A (100 单位) 由制造商拥有
2. 转移 (制造商 → 供应商) → FT Token_A 由供应商拥有
3. 销毁 (供应商) → FT Token_A 被销毁
4. 铸造 (制造商) → FT Token_A (50 单位) 由制造商拥有
✅ 有效: FT 代币销毁后可以重新铸造,因为它们是可替代的
```

### NFT 不能重新铸造(销毁后)
```
1. 铸造 (制造商) → NFT Token1 (ID: 123) 由制造商拥有
2. 销毁 (制造商) → NFT Token1 被销毁
3. 铸造 (制造商) → NFT Token1 (ID: 123)
❌ 错误: 无法铸造代币 "Token1 (ID: 123)",因为它已在任务 "Mint Token1" 中通过操作 "mint" 被铸造。NFT 代币只能铸造一次,除非先销毁。
   注意: 销毁后可以重新铸造,但这会创建一个具有相同 ID 的新代币
```

### 销毁后查询(始终允许)
```
1. 铸造 (制造商) → NFT Token1 (ID: 123) 由制造商拥有
2. 销毁 (制造商) → NFT Token1 被销毁
3. 查询 (供应商) → 查询 NFT Token1
✅ 有效: 查询操作始终允许,即使对于已销毁的代币(检查历史记录)
```

### 已存在代币的预铸造(tokenHasExistInERC = true)
```
1. DataObject 配置: tokenId="456", tokenHasExistInERC=true
2. 验证器查询区块链: OwnerOf("456") → "Mem.org.comMSP::x509::CN=user1,OU=client::..."
3. 解析身份并匹配参与者: user1 → Participant_Supplier
4. 设置初始所有权: Token456 由 Supplier 拥有(预铸造)
5. 转移 (Supplier → Bulk buyer) → Token456 由 Bulk buyer 拥有
✅ 有效: 已存在的代币被正确识别并设置初始所有者
6. 铸造 (Manufacturer) → Token456
❌ 错误: 无法铸造代币 "Token456",因为它已在任务 "[Pre-existing in ERC]" 中通过操作 "mint" 被铸造(预铸造)
```

### ERC 合约绑定一致性
```
1. 铸造 (制造商) → Token1, 绑定到 ERC721Contract_A
2. 转移 (制造商 → 供应商) → Token1, 绑定到 ERC721Contract_A
✅ 有效: 使用相同的 ERC 合约

3. 销毁 (供应商) → Token1, 绑定到 ERC721Contract_B
❌ 错误: 代币 "Token1" 必须在所有操作中使用相同的 ERC 合约。任务 "Mint Token1" 使用 "ERC721Contract_A" (ID: xxx),但此任务使用 "ERC721Contract_B" (ID: yyy)
```

## 扩展验证器

添加自定义验证规则:

1. 打开 `InstanceValidator.ts`
2. 在操作 switch 语句中添加新的 case:
```typescript
case 'your_operation':
  // 您的验证逻辑
  if (invalidCondition) {
    errors.push({
      taskId,
      taskName,
      message: '您的错误消息',
      severity: 'error'
    });
  }
  break;
```

3. 如果需要,更新代币所有权:
```typescript
tokenOwnership.set(effectiveTokenId, [newOwner]);
```

## 故障排除

### "Caller is not bound to any participant" (调用者未绑定到任何参与者)
- 确保在"绑定参与者"部分选择了参与者
- 检查参与者名称与 BPMN 图中使用的名称匹配

### "Operation requires caller to own token" (操作要求调用者拥有代币)
- 验证代币流: 检查此操作之前是否有铸造操作
- 确保跨操作的代币 ID 一致
- 检查之前的转移是否更改了所有权

### "Transfer recipient is not bound" (转移接收者未绑定)
- 在任务配置中选择接收者
- 确保接收者参与者在"绑定参与者"部分绑定

### "Token must use the same ERC contract across all operations" (代币必须在所有操作中使用相同的 ERC 合约)
- 检查操作同一代币的所有任务
- 确保它们都在"绑定任务到 ERC"中绑定到相同的 ERC 合约
- 如果看到此错误,解除绑定并重新绑定任务以使用一致的合约

### "Cannot perform operation on burned token" (无法对已销毁的代币执行操作)
- 检查代币是否在之前的任务中被销毁
- NFT 一旦销毁就无法再次使用(查询除外)
- 如果需要使用相同的 tokenId,必须先移除销毁操作

### "Token already exists in ERC but owner could not be determined" (代币已存在于 ERC 但无法确定所有者)
- 确保 `tokenHasExistInERC = true` 的代币有正确的参与者绑定
- 检查参与者绑定的 `selectedUser` 是否与区块链上的 User CN 匹配
- 验证 BPMN 的 `firefly_url` 字段是否正确设置
- 确保 ERC 合约已正确绑定到任务

## 技术详情

### 验证器架构
- 验证器使用 DOMParser 解析 BPMN XML
- 它遍历所有任务并通过流跟踪状态(代币所有权)
- BPMN 元素中的文档字段包含操作元数据(JSON 格式)
- 验证器是无状态的,可以多次运行而不会产生副作用

### 预铸造机制 (tokenHasExistInERC)
1. **扫描阶段**: 扫描所有 DataObjectReference 以构建代币注册表
2. **预铸造阶段**: 对于 `tokenHasExistInERC = true` 的代币:
   - 构造 ERC 合约 URL: `{basefirelfyUrl}/apis/{ercName}`
   - 调用 `OwnerOf(tokenId)` 查询区块链
   - 解析返回的身份字符串(MSP::x509::CN=user::...)
   - 匹配参与者绑定获取 participantId
   - 设置初始所有权: `tokenOwnership.set(tokenIdentifier, [participantId])`
   - 标记为已铸造: `mintedTokens.set(tokenIdentifier, {...})`
3. **验证阶段**: 按执行顺序处理任务,使用预铸造的所有权状态

### 区块链查询函数
- **queryTokenOwnerFromBlockchain**: 调用 ERC 合约的 OwnerOf 方法
- **parseBlockchainIdentity**: 解析 "MSP::x509::CN=user::..." 格式
- **findParticipantByBlockchainIdentity**: 匹配区块链身份和参与者绑定

### 支持的 ERC 标准
- **ERC721** (可转移型 NFT): `OwnerOf(tokenId) -> string`
- **ERC5521** (分发型): `OwnerOf(tokenId) -> string`
- **ERC5521** (增值型): `OwnerOf(tokenId) -> string`

所有三种类型都使用相同的 `OwnerOf` 方法签名返回所有者身份字符串。
