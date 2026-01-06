# 业务数据表结构分析（环境构建/身份体系、BPMN与合约、Oracle）

> 本文档独立整理与平台业务直接相关的数据表组织结构与表项内容，按三条业务维度描述：  
> 1) 环境构建与身份体系；2) BPMN 流程、实例与智能合约；3) Oracle 运行态数据（oracle-node）。

## 1. 环境构建与身份体系

平台的环境构建从“联盟与组织身份”起步，经由“成员关系与资源集合”落到“节点与端口的运行态资源”。这部分的核心是将身份体系与基础设施编排绑定到同一个可追溯的数据链路上，使得每一个节点都能被追溯到组织与联盟归属。

### 1.1 身份与组织层

- **LoleidoOrganization**：组织主体，承载成员用户与组织身份。  
  关键字段：`id`, `name`。  
- **Consortium**：联盟实体，组织的集合体。  
  关键字段：`id`, `name`。  
- **Membership**：组织与联盟的绑定关系，是后续资源分配与权限边界的核心节点。  
  关键字段：`id`, `loleido_organization_id`, `consortium_id`, `name`, `primary_contact_email`。  
- **UserProfile / LoleidoMemebership**：用户与组织的绑定关系，决定操作权限与组织归属。  
  关键字段：`UserProfile.email`, `role`；`LoleidoMemebership.loleido_organization_id`, `user_id`, `role`。  
- **APISecretKey / FabricIdentity**：API 与链上身份凭据，既能关联 `Environment`，也能关联 `Membership`，用于运行期鉴权与链上交互。  
  关键字段：`APISecretKey.key/key_secret`；`FabricIdentity.signer/secret/firefly_identity_id`。  

### 1.2 环境与资源集合层

- **Environment / EthEnvironment**：环境实体，承载链类型与运行状态。  
  关键字段：`id`, `consortium_id`, `network_id`, `status`。  
- **ResourceSet**：环境内的组织资源集合，是“身份 → 资源”映射的中枢。  
  关键字段：`id`, `membership_id`, `environment_id`, `agent_id`。  
- **FabricResourceSet / EthereumResourceSet**：资源集合的链类型具体化。  
  关键字段：`resource_set_id`, `org_type`。  

> 逻辑链条：组织 → 成员关系 → ResourceSet（环境内资源边界）→ Fabric/EthereumResourceSet（链类型具体化）  
> 这条链路保证了“组织身份”最终落到“可部署资源”。

### 1.3 运行态节点与端口层

- **Agent / KubernetesConfig**：执行代理与运行配置，决定节点在哪个宿主侧落地。  
  关键字段：`Agent.urls`, `Agent.type`, `KubernetesConfig.parameters`。  
- **Node / EthNode**：链上节点（peer/orderer/ca 或 ETH 节点），关联 `ResourceSet` 与 `Agent`。  
  关键字段：`name`, `type`, `status`, `agent_id`。  
- **Port**：端口映射表，确保容器与宿主之间端口可追溯且唯一。  
  关键字段：`node_id`, `internal`, `external`。  
- **FabricCA / PeerCa / PeerCaUser / NodeUser**：CA 与用户身份的细分记录，支撑证书签发与注册。  
  关键字段：`FabricCA.admin_name/admin_password`，`NodeUser.user_type`。  

> 资源集是运行态实体归属的边界，Agent 则是执行面。节点、端口、证书等资源通过这两者与身份体系建立一一对应关系。

## 2. BPMN 流程、实例与智能合约

流程相关数据从“模型 → 产物 → 实例”展开：模型定义存储在 BPMN/DMN 表中；生成产物（链码/FFI/通道等）进入合约和环境层；实例层记录运行中的流程与绑定关系。

### 2.1 流程模型层

- **BPMN**：保存 BPMN 模型内容、SVG 与解析结果。  
  关键字段：`bpmnContent`, `svgContent`, `participants`, `events`, `status`。  
- **DMN**：保存决策模型内容与 SVG。  
  关键字段：`dmnContent`, `svgContent`。  
- **BpmnDmnBindingRecord**：BPMN 实例与 DMN 决策绑定。  
  关键字段：`bpmn_instance_id`, `business_rule_id`, `dmn_instance_id`。  

### 2.2 合约与部署层

- **ChainCode**：合约元数据表，承载链码名称、语言、版本与环境归属。  
  关键字段：`name`, `version`, `language`, `environment_id`。  
- **Channel**：Fabric 通道信息，承载组织与 orderer 列表。  
  关键字段：`name`, `fabric_resource_set`, `orderers`。  
- **File**：证书/配置等文件存储与关联。  
  关键字段：`type`, `file`。  

### 2.3 实例层与运行态

- **BPMNInstance**：流程实例，连接链上实例 ID 与 BPMN 模型。  
  关键字段：`instance_chaincode_id`, `bpmn_id`, `create_at`, `update_at`。  

> 业务逻辑上：BPMN 模型生成链码与 FFI（保存在 BPMN 记录中），ChainCode 记录部署状态；BPMNInstance 则记录链上实例号与运行过程，形成可追溯闭环。

## 3. Oracle（oracle-node 运行态存储）

Oracle 在后端只存一个轻量管理表，真正的运行态状态与日志在 `oracle-node` 内部 SQLite 数据库中维护。该数据库主要用于任务配置、事件监听与计算结果的记录。

### 3.1 后端 Oracle 管理表

- **Oracle**：Oracle 归属关系与环境绑定。  
  关键字段：`name`, `environment_id`, `membership_id`。  

> 用于平台侧“Oracle 实例归属”的管理入口，不承载运行态日志。

### 3.2 oracle-node SQLite 数据表

以下表均在 `src/oracle-node/oracle_node/backend/storage.py` 中定义：

- **data_sources**：数据源定义。  
  字段：`id`, `name`, `type`, `endpoint`, `metadata`。  
- **contracts**：链上合约接口信息。  
  字段：`id`, `name`, `chain_type`, `address`, `abi`。  
- **events**：事件监听配置，绑定合约与回调。  
  字段：`id`, `contract_interface_id`, `event_name`, `filter_args`, `rpc_url`, `callback_url`。  
- **event_logs**：事件触发日志。  
  字段：`id`, `event_id`, `payload`。  
- **identities**：链上身份与密钥配置。  
  字段：`id`, `chain_type`, `rpc_url`, `private_key`, `address`, `metadata`。  
- **compute_watchers**：计算任务监听器与周期调度配置。  
  字段：`id`, `contract_address`, `identity_id`, `poll_interval`, `enabled`。  
- **compute_logs**：计算任务执行日志与链上回写结果。  
  字段：`id`, `watcher_id`, `task_id`, `result`, `tx_hash`, `status`, `error`。  

> 运行链路为：contracts/events 定义监听 → event_logs 记录触发 → identities 提供链上执行身份 → compute_watchers 轮询并产生 compute_logs → 结果回写链上并与平台侧状态关联。

## 小结

平台的数据结构呈现明显的“身份 → 资源 → 运行”分层。  
环境构建依赖联盟/组织/成员关系建立资源集合，再通过 Agent/节点/端口落地执行；  
流程与合约数据通过 BPMN/DMN → ChainCode → BPMNInstance 形成模型到运行的闭环；  
Oracle 由后端管理入口与 oracle-node 运行态数据库共同组成，确保链外任务配置、执行与审计可追溯。
