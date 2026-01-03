#!/bin/bash

# 配置
API_BASE_URL="http://127.0.0.1:8000/api/v1"
EMAIL="org1@test.com"
USERNAME="Org1"
PASSWORD="123"
ORG_NAME="org"
CONSORTIUM_NAME="Consortium"
ENV_TYPE="ethereum"  # 可选: "fabric" 或 "ethereum"
ENV_NAME="EnvGeth"

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 打印带颜色的信息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查参数
MEMBERSHIP_COUNT=${1:-1}
CREATE_ENVIRONMENT=${2:-"yes"}  # 第二个参数控制是否创建环境，默认为yes

if ! [[ "$MEMBERSHIP_COUNT" =~ ^[0-9]+$ ]] || [ "$MEMBERSHIP_COUNT" -lt 1 ]; then
    print_error "Invalid membership count."
    echo "Usage: $0 <number_of_memberships> [create_environment]"
    echo "  number_of_memberships: Number of memberships to create (default: 1)"
    echo "  create_environment: 'yes' or 'no' (default: yes)"
    echo ""
    echo "Examples:"
    echo "  $0 3           # Creates 3 memberships and an environment"
    echo "  $0 3 yes       # Same as above"
    echo "  $0 3 no        # Creates 3 memberships but no environment"
    exit 1
fi

print_info "Will create $MEMBERSHIP_COUNT membership(s)"
if [ "$CREATE_ENVIRONMENT" == "yes" ]; then
    print_info "Will create $ENV_TYPE environment: $ENV_NAME"
else
    print_info "Will NOT create environment"
fi

# 1. 注册用户
print_info "Registering user..."
REGISTER_RESPONSE=$(curl -s -X POST "$API_BASE_URL/register" \
  -H "Accept: application/json, text/plain, */*" \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3000" \
  --data-raw "{\"email\":\"$EMAIL\",\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}")

if [ $? -eq 0 ]; then
    print_success "User registered"
    echo "$REGISTER_RESPONSE" | jq '.' 2>/dev/null || echo "$REGISTER_RESPONSE"
else
    print_error "Failed to register user"
    exit 1
fi

# 2. 登录获取Token
print_info "Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST "$API_BASE_URL/login" \
  -H "Accept: application/json, text/plain, */*" \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3000" \
  --data-raw "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.data.token // .token // .access' 2>/dev/null)

if [ -z "$TOKEN" ] || [ "$TOKEN" == "null" ]; then
    print_error "Failed to get access token"
    echo "$LOGIN_RESPONSE"
    exit 1
fi

print_success "Logged in successfully"
print_info "Token: ${TOKEN:0:20}..."

# 3. 创建组织
print_info "Creating organization..."
ORG_RESPONSE=$(curl -s -X POST "$API_BASE_URL/organizations" \
  -H "Accept: application/json, text/plain, */*" \
  -H "Authorization: JWT $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3000" \
  --data-raw "{\"name\":\"$ORG_NAME\"}")

# 尝试从 .data.id 或直接从 .id 获取
ORG_ID=$(echo "$ORG_RESPONSE" | jq -r '.data.id // .id' 2>/dev/null)

if [ -z "$ORG_ID" ] || [ "$ORG_ID" == "null" ]; then
    print_error "Failed to create organization"
    echo "$ORG_RESPONSE"
    exit 1
fi

print_success "Organization created with ID: $ORG_ID"

# 4. 创建联盟
print_info "Creating consortium..."
CONSORTIUM_RESPONSE=$(curl -s -X POST "$API_BASE_URL/consortiums" \
  -H "Accept: application/json, text/plain, */*" \
  -H "Authorization: JWT $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3000" \
  --data-raw "{\"name\":\"$CONSORTIUM_NAME\",\"baseOrgId\":\"$ORG_ID\"}")

CONSORTIUM_ID=$(echo "$CONSORTIUM_RESPONSE" | jq -r '.data.id // .id' 2>/dev/null)

if [ -z "$CONSORTIUM_ID" ] || [ "$CONSORTIUM_ID" == "null" ]; then
    print_error "Failed to create consortium"
    echo "$CONSORTIUM_RESPONSE"
    exit 1
fi

print_success "Consortium created with ID: $CONSORTIUM_ID"

# 5. 创建多个Memberships
print_info "Creating $MEMBERSHIP_COUNT membership(s)..."

for i in $(seq 1 $MEMBERSHIP_COUNT); do
    MEMBERSHIP_NAME="mem$i"
    print_info "Creating membership $i/$MEMBERSHIP_COUNT: $MEMBERSHIP_NAME"

    MEMBERSHIP_RESPONSE=$(curl -s -X POST "$API_BASE_URL/consortium/$CONSORTIUM_ID/memberships" \
      -H "Accept: application/json, text/plain, */*" \
      -H "Authorization: JWT $TOKEN" \
      -H "Content-Type: application/json" \
      -H "Origin: http://localhost:3000" \
      --data-raw "{\"org_uuid\":\"$ORG_ID\",\"name\":\"$MEMBERSHIP_NAME\"}")

    MEMBERSHIP_ID=$(echo "$MEMBERSHIP_RESPONSE" | jq -r '.data.id // .id' 2>/dev/null)

    if [ -z "$MEMBERSHIP_ID" ] || [ "$MEMBERSHIP_ID" == "null" ]; then
        print_error "Failed to create membership: $MEMBERSHIP_NAME"
        echo "$MEMBERSHIP_RESPONSE"
    else
        print_success "Membership created: $MEMBERSHIP_NAME (ID: $MEMBERSHIP_ID)"
    fi
done

# 6. 创建环境(如果需要)
if [ "$CREATE_ENVIRONMENT" == "yes" ]; then
    echo ""
    print_info "========================================="
    print_info "Creating $ENV_TYPE environment: $ENV_NAME"
    print_info "========================================="

    if [ "$ENV_TYPE" == "ethereum" ] || [ "$ENV_TYPE" == "eth" ]; then
        # 创建以太坊环境
        ENV_RESPONSE=$(curl -s -X POST "$API_BASE_URL/consortium/$CONSORTIUM_ID/eth-environments" \
          -H "Accept: application/json, text/plain, */*" \
          -H "Authorization: JWT $TOKEN" \
          -H "Content-Type: application/json" \
          -H "Origin: http://localhost:3000" \
          --data-raw "{\"name\":\"$ENV_NAME\"}")

        ENV_TYPE_DISPLAY="Ethereum"
        ENV_ENDPOINT="eth-environments"
    else
        # 创建Fabric环境
        ENV_RESPONSE=$(curl -s -X POST "$API_BASE_URL/consortium/$CONSORTIUM_ID/environments" \
          -H "Accept: application/json, text/plain, */*" \
          -H "Authorization: JWT $TOKEN" \
          -H "Content-Type: application/json" \
          -H "Origin: http://localhost:3000" \
          --data-raw "{\"name\":\"$ENV_NAME\"}")

        ENV_TYPE_DISPLAY="Fabric"
        ENV_ENDPOINT="environments"
    fi

    ENV_ID=$(echo "$ENV_RESPONSE" | jq -r '.data.id // .id' 2>/dev/null)

    if [ -z "$ENV_ID" ] || [ "$ENV_ID" == "null" ]; then
        print_error "Failed to create $ENV_TYPE_DISPLAY environment"
        echo "$ENV_RESPONSE"
    else
        print_success "$ENV_TYPE_DISPLAY environment created with ID: $ENV_ID"
        print_success "Environment name: $ENV_NAME"
        echo ""
        print_info "Next steps - API endpoints:"
        print_info "  Init:     POST $API_BASE_URL/$ENV_ENDPOINT/$ENV_ID/init"
        print_info "  Join:     POST $API_BASE_URL/$ENV_ENDPOINT/$ENV_ID/join"
        if [ "$ENV_TYPE_DISPLAY" == "Ethereum" ]; then
            print_info "  Start:    POST $API_BASE_URL/$ENV_ENDPOINT/$ENV_ID/start"
            print_info "  Activate: POST $API_BASE_URL/$ENV_ENDPOINT/$ENV_ID/activate"
            print_info ""
            print_info "Firefly endpoints:"
            print_info "  Init:     POST $API_BASE_URL/$ENV_ENDPOINT/$ENV_ID/fireflys/init_eth"
            print_info "  Start:    POST $API_BASE_URL/$ENV_ENDPOINT/$ENV_ID/fireflys/start_eth"
        else
            print_info "  Start:    POST $API_BASE_URL/$ENV_ENDPOINT/$ENV_ID/start"
            print_info "  Activate: POST $API_BASE_URL/$ENV_ENDPOINT/$ENV_ID/activate"
            print_info ""
            print_info "Firefly endpoints:"
            print_info "  Init:     POST $API_BASE_URL/$ENV_ENDPOINT/$ENV_ID/fireflys/init"
            print_info "  Start:    POST $API_BASE_URL/$ENV_ENDPOINT/$ENV_ID/fireflys/start_firefly"
        fi
    fi
fi

print_success "All done! Created $MEMBERSHIP_COUNT membership(s)"
echo ""
echo "========================================="
echo "Summary:"
echo "  Organization ID: $ORG_ID"
echo "  Consortium ID: $CONSORTIUM_ID"
if [ "$CREATE_ENVIRONMENT" == "yes" ] && [ ! -z "$ENV_ID" ] && [ "$ENV_ID" != "null" ]; then
    echo "  Environment ID: $ENV_ID"
    echo "  Environment Type: $ENV_TYPE_DISPLAY"
    echo "  Environment Name: $ENV_NAME"
fi
echo "  Access Token: ${TOKEN:0:20}..."
echo "========================================="
echo ""
echo "You can now use these IDs in your application or scripts."
