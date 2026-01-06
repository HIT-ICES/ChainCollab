# ER 图（四大类：资源、身份、BPMN→合约、Oracle-node）

本文档给出四个独立 ER 图，分别覆盖：  
1) 后端资源相关数据结构  
2) 后端身份相关数据结构  
3) 后端 BPMN 到智能合约相关数据结构  
4) oracle-node 运行态数据结构（SQLite）

---

## 1) 后端资源相关（资源集合/环境/节点/端口）

```mermaid
erDiagram
    Environment {
        UUID id PK
        text name
        text status
    }
    ResourceSet {
        UUID id PK
        UUID environment_id FK
        UUID agent_id FK
        text name
    }
    FabricResourceSet {
        UUID id PK
        UUID resource_set_id FK
    }
    EthereumResourceSet {
        UUID id PK
        UUID resource_set_id FK
    }
    Agent {
        UUID id PK
        text name
        text type
    }
    Node {
        UUID id PK
        text name
        UUID fabric_resource_set_id FK
        UUID agent_id FK
        text status
    }
    EthNode {
        UUID id PK
        text name
        UUID fabric_resource_set_id FK
        UUID agent_id FK
        text status
    }
    Port {
        UUID id PK
        UUID node_id FK
        UUID eth_node_id FK
        int internal
        int external
    }
    Environment ||--o{ ResourceSet : contains
    ResourceSet ||--|| FabricResourceSet : wraps
    ResourceSet ||--o{ EthereumResourceSet : wraps
    ResourceSet }o--|| Agent : uses
    FabricResourceSet ||--o{ Node : hosts
    EthereumResourceSet ||--o{ EthNode : hosts
    Node ||--o{ Port : exposes
    EthNode ||--o{ Port : exposes
```

要点：
- `ResourceSet` 是组织在某环境中的资源集合，桥接身份与运行态资源。
- `Agent` 是执行面，节点/端口最终落在 Agent 上。
- `FabricResourceSet` / `EthereumResourceSet` 区分链类型。

---

## 2) 后端身份相关（组织/联盟/成员/用户/凭据）

```mermaid
erDiagram
    UserProfile {
        UUID id PK
        text email
        text role
    }
    LoleidoOrganization {
        UUID id PK
        text name
    }
    LoleidoMemebership {
        UUID id PK
        UUID loleido_organization_id FK
        UUID user_id FK
    }
    Consortium {
        UUID id PK
        text name
    }
    Membership {
        UUID id PK
        UUID loleido_organization_id FK
        UUID consortium_id FK
    }
    APISecretKey {
        UUID id PK
        UUID user_id FK
        UUID environment_id FK
        text key
        text key_secret
    }
    FabricIdentity {
        UUID id PK
        UUID environment_id FK
        UUID membership_id FK
        text name
    }
    Environment {
        UUID id PK
        text name
    }

    UserProfile ||--o{ LoleidoMemebership : joins
    LoleidoOrganization ||--o{ LoleidoMemebership : includes
    LoleidoOrganization ||--o{ Membership : participates
    Consortium ||--o{ Membership : includes
    UserProfile ||--o{ APISecretKey : has
    Environment ||--o{ APISecretKey : scopes
    Membership ||--o{ FabricIdentity : owns
    Environment ||--o{ FabricIdentity : scopes
```

要点：
- `Membership` 将组织与联盟绑定，是权限与资源分配的核心锚点。
- `APISecretKey` / `FabricIdentity` 为身份与链上操作提供凭据。

---

## 3) BPMN → 智能合约（模型/实例/链码/通道）

```mermaid
erDiagram
    BPMN {
        UUID id PK
        text name
        text status
    }
    DSL {
        UUID id PK
        UUID bpmn_id FK
        UUID bpmn_instance_id FK
        text content
    }
    BPMNInstance {
        UUID id PK
        UUID bpmn_id FK
        int instance_chaincode_id
        datetime create_at
        UUID chaincode_id FK
    }
    IdentityInfo {
        UUID id PK
        UUID bpmn_instance_id FK
        text identity_ref
    }
    DataInfo {
        UUID id PK
        UUID bpmn_instance_id FK
        text data_ref
    }
    ComputeInfo {
        UUID id PK
        UUID bpmn_instance_id FK
        text compute_ref
    }
    ChainCode {
        UUID id PK
        text name
        text content
        text abi
    }
    BPMNInstance ||--o| ChainCode : executes
    BPMN ||--o{ BPMNInstance : instantiates
    BPMN ||--o{ DSL : defines
    BPMNInstance ||--o{ DSL : derives
    BPMNInstance ||--o{ IdentityInfo : records
    BPMNInstance ||--o{ DataInfo : records
    BPMNInstance ||--o{ ComputeInfo : records
```

要点：
- `BPMN` 存模型与生成产物，`ChainCode` 表示部署后的合约元数据。
- `BPMNInstance` 体现运行时实例与链上实例 ID 绑定。
- `DMN` 与 `BPMNInstance` 通过绑定记录衔接。

---

## 4) oracle-node（运行态 SQLite）

```mermaid
erDiagram
    data_sources {
        text id PK
        text name
        text type
        text endpoint
    }
    contracts {
        text id PK
        text name
        text chain_type
        text address
    }
    events {
        text id PK
        text contract_interface_id FK
        text event_name
    }
    event_logs {
        text id PK
        text event_id FK
        text payload
    }
    identities {
        text id PK
        text name
        text chain_type
        text address
    }
    compute_watchers {
        text id PK
        text contract_address
        text identity_id FK
        int poll_interval
        int enabled
    }
    compute_logs {
        text id PK
        text watcher_id FK
        int task_id
        text tx_hash
        text status
    }

    contracts ||--o{ events : defines
    events ||--o{ event_logs : logs
    data_sources ||--o{ events : feeds
    identities ||--o{ compute_watchers : signs
    compute_watchers ||--o{ compute_logs : logs
    contracts ||--o{ compute_watchers : observes
```

要点：
- `contracts/events/event_logs` 形成“事件订阅 → 触发 → 记录”的闭环。
- `identities` 提供链上身份与私钥支撑计算任务签名。
- `compute_watchers/compute_logs` 记录链外计算与回写状态。
