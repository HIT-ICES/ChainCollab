# 环境设置脚本使用指南

本脚本用于自动化设置ChainCollab的组织、联盟、成员和环境(Fabric/Ethereum)。

## 脚本: `setup_org_consortium_mem.sh`

一体化脚本,可自动创建:
- 用户注册和登录
- 组织 (Organization)
- 联盟 (Consortium)
- 成员 (Memberships)
- 环境 (Environment - Fabric或Ethereum)

### 使用方法

```bash
./setup_org_consortium_mem.sh <membership_count> [create_environment]
```

### 参数

- `membership_count`: 要创建的成员数量(默认: 1)
- `create_environment`: 是否创建环境 "yes" 或 "no" (默认: yes)

### 配置项

在脚本顶部修改以下配置:

```bash
API_BASE_URL="http://127.0.0.1:8000/api/v1"
EMAIL="org1@test.com"       # 用户邮箱
USERNAME="Org1"              # 用户名
PASSWORD="123"               # 密码
ORG_NAME="org"              # 组织名称
CONSORTIUM_NAME="Consortium" # 联盟名称
ENV_TYPE="ethereum"          # 环境类型: "fabric" 或 "ethereum"
ENV_NAME="EnvGeth"           # 环境名称
```

### 使用示例

#### 示例 1: 创建3个成员和以太坊环境(默认)
```bash
./setup_org_consortium_mem.sh 3
```

#### 示例 2: 创建5个成员但不创建环境
```bash
./setup_org_consortium_mem.sh 5 no
```

#### 示例 3: 创建1个成员和Fabric环境
```bash
# 先修改脚本配置: ENV_TYPE="fabric"
./setup_org_consortium_mem.sh 1
```

#### 示例 4: 只创建组织和联盟,不创建成员和环境
```bash
./setup_org_consortium_mem.sh 0 no
```

### 输出示例

运行 `./setup_org_consortium_mem.sh 3` 会产生如下输出:

```
[INFO] Will create 3 membership(s)
[INFO] Will create ethereum environment: EnvGeth
[INFO] Registering user...
[SUCCESS] User registered
{
  "status": "success",
  "data": {...}
}
[INFO] Logging in...
[SUCCESS] Logged in successfully
[INFO] Token: eyJhbGciOiJIUzI1NiI...

[INFO] Creating organization...
[SUCCESS] Organization created with ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890

[INFO] Creating consortium...
[SUCCESS] Consortium created with ID: b2c3d4e5-f6a7-8901-bcde-f12345678901

[INFO] Creating 3 membership(s)...
[INFO] Creating membership 1/3: mem1
[SUCCESS] Membership created: mem1 (ID: c3d4e5f6-a7b8-9012-cdef-123456789012)
[INFO] Creating membership 2/3: mem2
[SUCCESS] Membership created: mem2 (ID: d4e5f6a7-b8c9-0123-def1-234567890123)
[INFO] Creating membership 3/3: mem3
[SUCCESS] Membership created: mem3 (ID: e5f6a7b8-c9d0-1234-ef12-345678901234)

[INFO] =========================================
[INFO] Creating ethereum environment: EnvGeth
[INFO] =========================================
[SUCCESS] Ethereum environment created with ID: f6a7b8c9-d0e1-2345-f123-456789012345
[SUCCESS] Environment name: EnvGeth

[INFO] Next steps - API endpoints:
[INFO]   Init:     POST http://127.0.0.1:8000/api/v1/eth-environments/f6a7.../init
[INFO]   Join:     POST http://127.0.0.1:8000/api/v1/eth-environments/f6a7.../join
[INFO]   Start:    POST http://127.0.0.1:8000/api/v1/eth-environments/f6a7.../start
[INFO]   Activate: POST http://127.0.0.1:8000/api/v1/eth-environments/f6a7.../activate
[INFO]
[INFO] Firefly endpoints:
[INFO]   Init:     POST http://127.0.0.1:8000/api/v1/eth-environments/f6a7.../fireflys/init_eth
[INFO]   Start:    POST http://127.0.0.1:8000/api/v1/eth-environments/f6a7.../fireflys/start_eth

[SUCCESS] All done! Created 3 membership(s)

=========================================
Summary:
  Organization ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
  Consortium ID: b2c3d4e5-f6a7-8901-bcde-f12345678901
  Environment ID: f6a7b8c9-d0e1-2345-f123-456789012345
  Environment Type: Ethereum
  Environment Name: EnvGeth
  Access Token: eyJhbGciOiJIUzI1NiI...
=========================================

You can now use these IDs in your application or scripts.
```


## 完整工作流程示例

### 从零开始设置以太坊环境

```bash
# 1. 运行完整设置脚本
./setup_org_consortium_mem.sh 3

# 脚本会自动创建:
# - 1个用户 (org1@test.com)
# - 1个组织 (org)
# - 1个联盟 (Consortium)
# - 3个成员 (mem1, mem2, mem3)
# - 1个以太坊环境 (EnvGeth)

# 2. 记录输出中的环境ID和Token

# 3. 使用前端或API继续操作环境:
#    - 初始化环境
#    - 加入成员
#    - 启动环境
#    - 激活环境
#    - 初始化Firefly
#    - 启动Firefly
```

### 创建Fabric环境

```bash
# 1. 修改脚本配置
#    编辑 setup_org_consortium_mem.sh
#    将 ENV_TYPE="ethereum" 改为 ENV_TYPE="fabric"
#    将 ENV_NAME="EnvGeth" 改为 ENV_NAME="MyFabricNetwork"

# 2. 运行脚本
./setup_org_consortium_mem.sh 3

# 现在会创建Fabric环境而不是Ethereum环境
```

## 环境类型对比

### Fabric环境
- **创建端点**: `POST /consortium/{id}/environments`
- **环境端点前缀**: `/environments/{id}`
- **Firefly初始化**: `POST /environments/{id}/fireflys/init`
- **Firefly启动**: `POST /environments/{id}/fireflys/start_firefly`

### Ethereum环境
- **创建端点**: `POST /consortium/{id}/eth-environments`
- **环境端点前缀**: `/eth-environments/{id}`
- **Firefly初始化**: `POST /eth-environments/{id}/fireflys/init_eth`
- **Firefly启动**: `POST /eth-environments/{id}/fireflys/start_eth`

## 环境设置后续步骤

创建环境后,通常的操作流程:

```bash
# 1. 初始化环境
curl -X POST "http://127.0.0.1:8000/api/v1/eth-environments/{env_id}/init" \
  -H "Authorization: JWT {token}"

# 2. 加入成员
curl -X POST "http://127.0.0.1:8000/api/v1/eth-environments/{env_id}/join" \
  -H "Authorization: JWT {token}" \
  -H "Content-Type: application/json" \
  -d '{"membership_id": "{membership_id}"}'

# 3. 启动环境
curl -X POST "http://127.0.0.1:8000/api/v1/eth-environments/{env_id}/start" \
  -H "Authorization: JWT {token}"

# 4. 激活环境
curl -X POST "http://127.0.0.1:8000/api/v1/eth-environments/{env_id}/activate" \
  -H "Authorization: JWT {token}"

# 5. 初始化Firefly
curl -X POST "http://127.0.0.1:8000/api/v1/eth-environments/{env_id}/fireflys/init_eth" \
  -H "Authorization: JWT {token}"

# 6. 启动Firefly
curl -X POST "http://127.0.0.1:8000/api/v1/eth-environments/{env_id}/fireflys/start_eth" \
  -H "Authorization: JWT {token}"
```

## 故障排除

### 错误: "Failed to create organization"
- 检查API服务是否运行: `curl http://127.0.0.1:8000/api/v1/`
- 检查用户是否已存在,尝试使用不同的邮箱

### 错误: "Invalid environment type"
- 确保 `ENV_TYPE` 设置为 "fabric" 或 "ethereum"
- 检查 `create_environment.sh` 的参数拼写

### 错误: "Failed to get access token"
- 检查用户名和密码是否正确
- 确认注册步骤成功完成

### 需要重新运行脚本
如果需要重新运行脚本,请:
1. 清理数据库中的旧数据
2. 或者修改脚本中的 `EMAIL`, `ORG_NAME`, `CONSORTIUM_NAME` 等配置使用新的值

## 注意事项

1. **JWT Token有效期**: Token可能会过期,如果遇到认证错误,重新运行登录步骤获取新Token
2. **环境类型**: 创建后无法更改环境类型,请在创建前确认
3. **网络配置**: 确保脚本中的API地址 `http://127.0.0.1:8000` 与你的实际部署匹配
4. **并发限制**: 避免同时运行多个脚本实例,可能导致数据冲突

## 相关文档

- [Firefly测试命令](../FIREFLY_TEST_COMMANDS.md)
- [测试脚本](../test_firefly_endpoints.sh)
