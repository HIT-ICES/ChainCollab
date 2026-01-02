#!/usr/bin/env bash
set -e

# 1) 从 system 节点直接获取 enode
ENODE_RAW=$(docker exec -i sys_geth geth attach --exec "admin.nodeInfo.enode" \
  | tr -d '\r' \
  | tr -d '"')

# 2) 把 enode 里的 docker bridge IP（172.x.x.x）替换成 docker 网络内可解析的 sys_geth
#    例：@172.20.0.2:30303 -> @sys_geth:30303
ENODE_FIXED=$(echo "$ENODE_RAW" \
  | sed -E 's/@172(\.[0-9]{1,3}){3}:/@sys_geth:/')

# 3) 写入 .env（供 org compose 使用）
cat > .env <<EOF
SYS_ENODE=${ENODE_FIXED}
ORG1_ETHERBASE=0xORG1_ADDRESS
ORG2_ETHERBASE=0xORG2_ADDRESS
ORG3_ETHERBASE=0xORG3_ADDRESS
EOF

# 4) 打印确认
echo "[OK] SYS_ENODE exported:"
echo "SYS_ENODE=${ENODE_FIXED}"
