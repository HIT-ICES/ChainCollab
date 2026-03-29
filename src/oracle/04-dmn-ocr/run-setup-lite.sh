#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORACLE_ROOT="${ORACLE_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
if [ "$(basename "$ORACLE_ROOT")" = "04-dmn-ocr" ]; then
  ORACLE_ROOT="$(cd "$ORACLE_ROOT/.." && pwd)"
fi
SRC_ROOT="${SRC_ROOT:-$(cd "$ORACLE_ROOT/.." && pwd)}"
CHAINLINK_ROOT="${CHAINLINK_ROOT:-$ORACLE_ROOT/CHAINLINK}"
CHAINLINK_DEPLOYMENT_DIR="$CHAINLINK_ROOT/deployment"
RUNTIME_ROOT="${RUNTIME_ROOT:-$SRC_ROOT/runtime}"
RUNTIME_DEPLOYMENT_DIR="${CHAINCOLLAB_RUNTIME_DEPLOYMENT_DIR:-$RUNTIME_ROOT/deployment}"
CHAINLINK_DEPLOYMENT_BACKUP_DIR="$RUNTIME_ROOT/.chainlink-deployment-backup"
FEATURES_04="$ORACLE_ROOT/04-dmn-ocr"
FEATURES_03="$ORACLE_ROOT/03-ocr-multinode"
if [ ! -d "$FEATURES_03" ]; then
  echo "❌ missing forked OCR cluster at: $FEATURES_03"
  exit 1
fi
if [ ! -d "$CHAINLINK_ROOT" ]; then
  echo "❌ missing forked CHAINLINK at: $CHAINLINK_ROOT"
  exit 1
fi

STARTED_OCR_NETWORK=0
STARTED_CDMN=0
export OCR_RPC_URL="${OCR_RPC_URL:-http://system-geth-node:8545}"
SYSTEM_GETH_CONTAINER="${SYSTEM_GETH_CONTAINER:-system-geth-node}"
export CHAINCOLLAB_RUNTIME_DEPLOYMENT_DIR="$RUNTIME_DEPLOYMENT_DIR"

DEPLOYMENT_FILES=(
  chainlink-deployment.json
  compiled.json
  deployment.json
  external-initiator.json
  node-info.json
  ocr-config-gen.json
  ocr-config.json
  ocr-deployment.json
  operator-abi.json
  operator-compiled.json
)

cleanup_on_failure() {
  local exit_code="$1"
  if [ "$exit_code" -eq 0 ]; then
    return
  fi

  echo "== [rollback] setup failed, tearing down containers =="
  set +e

  if [ "$STARTED_CDMN" -eq 1 ]; then
    echo " - stopping CDMN services"
    (cd "$FEATURES_04" && docker-compose -f docker-compose-cdmn.yml down) >/dev/null 2>&1 || true
  fi

  if [ "$STARTED_OCR_NETWORK" -eq 1 ]; then
    echo " - stopping OCR network"
    (cd "$FEATURES_03" && ./stop-ocr-network.sh) >/dev/null 2>&1 || true
  fi

  restore_chainlink_deployment_backup >/dev/null 2>&1 || true
}

MODE="full"
for arg in "$@"; do
  case "$arg" in
    --smoke) MODE="smoke" ;;
    --clean) MODE="clean" ;;
    -h|--help)
      echo "Usage: $0 [--smoke|--clean]"
      echo "  --smoke  only check running containers and basic health endpoints"
      echo "  --clean  stop lite containers and remove runtime/deployment artifacts"
      exit 0
      ;;
  esac
done

ensure_runtime_deployment_dir() {
  mkdir -p "$RUNTIME_DEPLOYMENT_DIR"
}

remove_runtime_deployment() {
  if [ -d "$RUNTIME_DEPLOYMENT_DIR" ]; then
    rm -rf "$RUNTIME_DEPLOYMENT_DIR"
  fi
}

backup_chainlink_deployment() {
  rm -rf "$CHAINLINK_DEPLOYMENT_BACKUP_DIR"
  mkdir -p "$CHAINLINK_DEPLOYMENT_BACKUP_DIR"
  mkdir -p "$CHAINLINK_DEPLOYMENT_DIR"
  for name in "${DEPLOYMENT_FILES[@]}"; do
    if [ -f "$CHAINLINK_DEPLOYMENT_DIR/$name" ]; then
      cp "$CHAINLINK_DEPLOYMENT_DIR/$name" "$CHAINLINK_DEPLOYMENT_BACKUP_DIR/$name"
    fi
  done
}

restore_chainlink_deployment_backup() {
  if [ ! -d "$CHAINLINK_DEPLOYMENT_BACKUP_DIR" ]; then
    return
  fi
  mkdir -p "$CHAINLINK_DEPLOYMENT_DIR"
  for name in "${DEPLOYMENT_FILES[@]}"; do
    rm -f "$CHAINLINK_DEPLOYMENT_DIR/$name"
    if [ -f "$CHAINLINK_DEPLOYMENT_BACKUP_DIR/$name" ]; then
      cp "$CHAINLINK_DEPLOYMENT_BACKUP_DIR/$name" "$CHAINLINK_DEPLOYMENT_DIR/$name"
    fi
  done
  rm -rf "$CHAINLINK_DEPLOYMENT_BACKUP_DIR"
}

restore_chainlink_deployment_from_runtime() {
  mkdir -p "$CHAINLINK_DEPLOYMENT_DIR"
  for name in "${DEPLOYMENT_FILES[@]}"; do
    rm -f "$CHAINLINK_DEPLOYMENT_DIR/$name"
  done
  if [ ! -d "$RUNTIME_DEPLOYMENT_DIR" ]; then
    return
  fi
  for name in "${DEPLOYMENT_FILES[@]}"; do
    if [ -f "$RUNTIME_DEPLOYMENT_DIR/$name" ]; then
      cp "$RUNTIME_DEPLOYMENT_DIR/$name" "$CHAINLINK_DEPLOYMENT_DIR/$name"
    fi
  done
}

persist_chainlink_deployment_to_runtime() {
  ensure_runtime_deployment_dir
  for name in "${DEPLOYMENT_FILES[@]}"; do
    if [ -f "$CHAINLINK_DEPLOYMENT_DIR/$name" ]; then
      cp "$CHAINLINK_DEPLOYMENT_DIR/$name" "$RUNTIME_DEPLOYMENT_DIR/$name"
    fi
  done
}

smoke_check() {
  echo "== [smoke] basic checks =="
  if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running or not accessible"
    exit 1
  fi

  echo "== [smoke] chainlink cluster (fork) containers =="
  docker-compose -f "$FEATURES_03/docker-compose-multinode.yml" ps --status=running || true

  echo "== [smoke] cdmn containers =="
  docker-compose -f "$FEATURES_04/docker-compose-cdmn.yml" ps --status=running || true

  if command -v curl >/dev/null 2>&1; then
    for port in 8081 8082 8083 8084; do
      echo -n "cdmn-node on :${port} -> "
      if curl -sS --max-time 2 "http://localhost:${port}/api/dmn/health" >/dev/null; then
        echo "ok"
      else
        echo "not ready"
      fi
    done
  else
    echo "⚠️  curl not found; skip HTTP health checks"
  fi

  echo "== [smoke] done =="
}

clean_mode() {
  echo "== [clean] stop lite services =="
  (cd "$FEATURES_04" && docker-compose -f docker-compose-cdmn.yml down) >/dev/null 2>&1 || true
  (cd "$FEATURES_03" && ./stop-ocr-network.sh) >/dev/null 2>&1 || true
  restore_chainlink_deployment_backup >/dev/null 2>&1 || true
  echo "== [clean] remove runtime deployment =="
  remove_runtime_deployment
  echo "== [clean] done =="
}

resolve_host_rpc_url() {
  if [ -n "${RPC_URL:-}" ]; then
    printf '%s\n' "$RPC_URL"
    return 0
  fi

  local mapped
  mapped="$(docker port "$SYSTEM_GETH_CONTAINER" 8545/tcp 2>/dev/null | head -n 1 || true)"
  if [ -n "$mapped" ]; then
    printf 'http://127.0.0.1:%s\n' "${mapped##*:}"
    return 0
  fi

  printf 'http://localhost:8545\n'
}

if [ "$MODE" = "smoke" ]; then
  smoke_check
  exit 0
fi

if [ "$MODE" = "clean" ]; then
  clean_mode
  exit 0
fi

export RPC_URL="${RPC_URL:-$(resolve_host_rpc_url)}"
echo "== [rpc] host RPC: ${RPC_URL} =="
echo "== [deployment] runtime dir: ${RUNTIME_DEPLOYMENT_DIR} =="
ensure_runtime_deployment_dir

trap 'exit_code=$?; trap - EXIT; cleanup_on_failure "$exit_code"; exit "$exit_code"' EXIT

ensure_chainlink_deps() {
  local oz_vendor="$CHAINLINK_ROOT/contracts/vendor/openzeppelin/contracts/token/ERC20/ERC20.sol"
  local oz_nm="$CHAINLINK_ROOT/node_modules/@openzeppelin/contracts/token/ERC20/ERC20.sol"
  local cl_nm="$CHAINLINK_ROOT/node_modules/@chainlink/contracts/src/v0.8/operatorforwarder/ChainlinkClient.sol"
  local axios_nm="$CHAINLINK_ROOT/node_modules/axios/package.json"
  local dotenv_nm="$CHAINLINK_ROOT/node_modules/dotenv/package.json"
  local web3abi_nm="$CHAINLINK_ROOT/node_modules/web3-eth-abi/package.json"

  local oz_ok=0
  if [ -f "$oz_vendor" ] || [ -f "$oz_nm" ]; then
    oz_ok=1
  fi

  local cl_ok=0
  if [ -f "$cl_nm" ]; then
    cl_ok=1
  fi

  local js_ok=0
  if [ -f "$axios_nm" ] && [ -f "$dotenv_nm" ] && [ -f "$web3abi_nm" ]; then
    js_ok=1
  fi

  if [ "$oz_ok" -eq 1 ] && [ "$cl_ok" -eq 1 ] && [ "$js_ok" -eq 1 ]; then
    return 0
  fi

  if ! command -v npm >/dev/null 2>&1; then
    echo "== [deps] 缺少 npm，无法自动安装依赖 =="
    echo "请先安装 Node.js / npm 后重试。"
    exit 1
  fi

  echo "== [deps] 检测到依赖缺失，正在自动执行 npm install =="
  if [ "$oz_ok" -ne 1 ]; then
    echo " - OpenZeppelin 未就绪:"
    echo "   * vendor:      $oz_vendor"
    echo "   * node_modules $oz_nm"
  fi
  if [ "$cl_ok" -ne 1 ]; then
    echo " - Chainlink contracts 未就绪:"
    echo "   * node_modules $cl_nm"
  fi
  if [ "$js_ok" -ne 1 ]; then
    echo " - Node.js 运行依赖未就绪:"
    echo "   * axios:       $axios_nm"
    echo "   * dotenv:      $dotenv_nm"
    echo "   * web3-eth-abi $web3abi_nm"
  fi
  echo " - 在 $CHAINLINK_ROOT 执行 npm install --no-fund --no-audit"
  npm install --no-fund --no-audit

  if [ ! -f "$oz_vendor" ] && [ ! -f "$oz_nm" ]; then
    echo "❌ OpenZeppelin 依赖仍未就绪: $oz_vendor / $oz_nm"
    exit 1
  fi
  if [ ! -f "$cl_nm" ]; then
    echo "❌ Chainlink contracts 依赖仍未就绪: $cl_nm"
    exit 1
  fi
  if [ ! -f "$axios_nm" ] || [ ! -f "$dotenv_nm" ] || [ ! -f "$web3abi_nm" ]; then
    echo "❌ Node.js 运行依赖仍未就绪"
    exit 1
  fi
}

read_deployment_contract() {
  local deployment_json="$CHAINLINK_DEPLOYMENT_DIR/deployment.json"
  if [ ! -f "$deployment_json" ]; then
    return 0
  fi
  node -e "const fs=require('fs');const p=process.argv[1];const j=JSON.parse(fs.readFileSync(p,'utf8'));process.stdout.write(j.contractAddress||'');" "$deployment_json"
}

read_deployment_field() {
  local deployment_json="$1"
  local field="$2"
  if [ ! -f "$deployment_json" ]; then
    return 0
  fi
  node -e "const fs=require('fs');const p=process.argv[1];const field=process.argv[2];const j=JSON.parse(fs.readFileSync(p,'utf8'));process.stdout.write(j[field]||'');" "$deployment_json" "$field"
}

get_contract_code() {
  local rpc_url="$1"
  local contract_addr="$2"
  node - "$rpc_url" "$contract_addr" <<'NODE'
const http = require('http');
const { URL } = require('url');
const rpcUrl = process.argv[2];
const contractAddress = process.argv[3];
if (!rpcUrl || !contractAddress) {
  process.exit(2);
}
const payload = JSON.stringify({
  jsonrpc: '2.0',
  method: 'eth_getCode',
  params: [contractAddress, 'latest'],
  id: 1
});
const rpc = new URL(rpcUrl);
const req = http.request({
  hostname: rpc.hostname,
  port: rpc.port || (rpc.protocol === 'https:' ? 443 : 80),
  path: rpc.pathname || '/',
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Content-Length': Buffer.byteLength(payload),
  },
}, (res) => {
  let data = '';
  res.on('data', (chunk) => (data += chunk));
  res.on('end', () => {
    try {
      const out = JSON.parse(data);
      if (out.error) {
        console.error(out.error.message || JSON.stringify(out.error));
        process.exit(1);
      }
      process.stdout.write(out.result || '');
    } catch (e) {
      console.error(e.message);
      process.exit(1);
    }
  });
});
req.on('error', (err) => {
  console.error(err.message);
  process.exit(1);
});
req.write(payload);
req.end();
NODE
}

ensure_dmn_contract_deployed() {
  local rpc_url="${RPC_URL:-http://localhost:8545}"
  local deployment_json="$CHAINLINK_DEPLOYMENT_DIR/deployment.json"
  local chainlink_json="$CHAINLINK_DEPLOYMENT_DIR/chainlink-deployment.json"
  local contract_addr=""
  local contract_code=""
  local current_link_token=""
  local current_oracle=""
  local deployed_link_token=""
  local deployed_oracle=""
  local need_redeploy=0

  current_link_token="$(read_deployment_field "$chainlink_json" linkToken)"
  current_oracle="$(read_deployment_field "$chainlink_json" operator)"

  if [ ! -f "$deployment_json" ]; then
    echo "ℹ️  deployment.json 不存在，准备部署 DMN 合约"
    need_redeploy=1
  else
    contract_addr="$(read_deployment_contract)"
    deployed_link_token="$(read_deployment_field "$deployment_json" linkToken)"
    deployed_oracle="$(read_deployment_field "$deployment_json" oracle)"
    if [ -z "$contract_addr" ]; then
      echo "⚠️  deployment.json 缺少 contractAddress，准备重新部署"
      need_redeploy=1
    elif [ -n "$current_link_token" ] && [ "$deployed_link_token" != "$current_link_token" ]; then
      echo "⚠️  deployment.json 的 LINK Token 已过期: $deployed_link_token"
      echo "   当前 Chainlink 基础设施使用: $current_link_token"
      need_redeploy=1
    elif [ -n "$current_oracle" ] && [ "$deployed_oracle" != "$current_oracle" ]; then
      echo "⚠️  deployment.json 的 Oracle 地址已过期: $deployed_oracle"
      echo "   当前 Chainlink 基础设施使用: $current_oracle"
      need_redeploy=1
    else
      if ! contract_code="$(get_contract_code "$rpc_url" "$contract_addr")"; then
        echo "⚠️  无法在 RPC($rpc_url) 校验合约地址 $contract_addr，准备重新部署"
        need_redeploy=1
      elif [ -z "$contract_code" ] || [ "$contract_code" = "0x" ]; then
        echo "⚠️  合约地址 $contract_addr 在当前 RPC($rpc_url) 无代码，准备重新部署"
        need_redeploy=1
      else
        echo "✅ 已发现有效 DMN 合约地址: $contract_addr"
      fi
    fi
  fi

  if [ "$need_redeploy" -eq 1 ]; then
    echo "🔁 重新部署 DMN 请求合约..."
    FORCE_DMN_CONTRACT=1 DMN_MODE=lite RPC_URL="$rpc_url" node scripts/deploy-contract.js
    contract_addr="$(read_deployment_contract)"
    if [ -z "$contract_addr" ]; then
      echo "❌ 重新部署后仍未写入 contractAddress"
      exit 1
    fi
    contract_code="$(get_contract_code "$rpc_url" "$contract_addr" || true)"
    if [ -z "$contract_code" ] || [ "$contract_code" = "0x" ]; then
      echo "❌ 重新部署后合约地址仍无代码: $contract_addr (RPC=$rpc_url)"
      exit 1
    fi
    echo "✅ DMN 合约部署并校验成功: $contract_addr"
  fi
}

echo "== [1] 启动 OCR 多节点网络（仅用于 Chainlink 节点与 Operator 监听） =="
STARTED_OCR_NETWORK=1
cd "$FEATURES_03"
./start-ocr-network.sh

echo "== [2] 启动 CDMN Python 服务（缓存 API + DMN 计算） =="
STARTED_CDMN=1
cd "$FEATURES_04"
export COMPOSE_DOCKER_CLI_BUILD=1
export DOCKER_BUILDKIT=1
export COMPOSE_BUILD_PULL_POLICY=never
echo "   OCR_RPC_URL=${OCR_RPC_URL}"
docker-compose -f docker-compose-cdmn.yml up -d --build --pull=never

echo "== [3] Chainlink 基础部署（LinkToken/Operator） =="
cd "$CHAINLINK_ROOT"
ensure_chainlink_deps
backup_chainlink_deployment
restore_chainlink_deployment_from_runtime
# 允许 04-dmn-ocr 脚本从 CHAINLINK_ROOT/node_modules 解析依赖。
export NODE_PATH="$CHAINLINK_ROOT/node_modules${NODE_PATH:+:$NODE_PATH}"
./compile.sh
./unlock-account.sh
node scripts/deploy-chainlink.js
node scripts/fund-chainlink-node.js --all --min 1 --amount 10
persist_chainlink_deployment_to_runtime

echo "== [4] 确保 DMN 请求合约已部署 =="
cd "$CHAINLINK_ROOT"
restore_chainlink_deployment_from_runtime
ensure_dmn_contract_deployed
persist_chainlink_deployment_to_runtime

echo "== [5] 创建 directrequest 缓存 Job（监听 OracleRequest） =="
cd "$CHAINLINK_ROOT"
EXTERNAL_JOB_ID=$(node -e "const fs=require('fs');const path=require('path');const p=path.join(process.env.CHAINCOLLAB_RUNTIME_DEPLOYMENT_DIR||path.join(process.cwd(),'deployment'),'chainlink-deployment.json');const data=JSON.parse(fs.readFileSync(p,'utf8'));console.log(data.dmnJobId||'');") \
  node "$FEATURES_04/create-dmn-directrequest-job.js"

echo "== [6] 将 DMN Job ID 写回合约 setJobId =="
cd "$CHAINLINK_ROOT"
DMN_MODE=lite node "$FEATURES_04/set-dmn-job-id.js"

echo "== [7] 设置 baseline writers =="
cd "$CHAINLINK_ROOT"
DMN_MODE=lite node "$FEATURES_04/set-ocr-and-writer.js"

echo "== [8] 为 DMN 合约充值 LINK =="
cd "$CHAINLINK_ROOT"
restore_chainlink_deployment_from_runtime
node scripts/fund-contract.js
persist_chainlink_deployment_to_runtime

echo "== [9] 测试 directrequest 缓存链路 =="
DMN_MODE=lite DMN_RANDOM=1 node "$FEATURES_04/test-dmn-ocr.js"

restore_chainlink_deployment_backup

echo "== 完成：已启用 Operator 监听 + DMN 直写链路（无 OCR 聚合） =="
