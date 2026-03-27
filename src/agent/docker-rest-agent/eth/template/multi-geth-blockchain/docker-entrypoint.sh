#!/bin/sh
set -e

DATADIR="${GETH_DATADIR:-/root/.ethereum}"

# 首次启动自动 init（推荐）
if [ ! -d "$DATADIR/geth/chaindata" ]; then
  echo "[entrypoint] initializing geth datadir: $DATADIR"
  geth --datadir "$DATADIR" init /genesis.json
else
  echo "[entrypoint] datadir already initialized: $DATADIR"
fi

# 关键修复：如果参数以 -/-- 开头，说明 compose 只给了选项，没有给命令
if [ "${1#-}" != "$1" ]; then
  set -- geth "$@"
fi

# === 方案A关键：修复 ENR 广告成 loopback 的问题 ===
# 取容器在 Docker 网络里的 IP，用于 P2P advertise
IP="$(hostname -i | awk '{print $1}')"
echo "[entrypoint] container IP for nat extip: $IP"

# 如果用户没有显式传 --nat=...，则自动追加 --nat=extip:<IP>
# 这样 system-geth-node 的 ENR 里就不会出现 127.0.0.1
case " $* " in
  *" --nat="*)  # 已显式设置 nat，就不动
    ;;
  *)
    set -- "$@" --nat=extip:"$IP"
    ;;
esac

exec "$@"
