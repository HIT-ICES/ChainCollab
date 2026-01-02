#!/bin/sh
set -e

DATADIR="${GETH_DATADIR:-/root/.ethereum}"
PW_FILE="${PW_FILE:-/root/password.txt}"

mkdir -p /out
ETHERBASE_FILE="/out/etherbase.txt"
ENV_FILE="/out/env"

# init
if [ ! -d "$DATADIR/geth/chaindata" ]; then
  echo "[prep] init datadir: $DATADIR"
  geth --datadir "$DATADIR" init /genesis.json
fi

# password 必须是文件
if [ -e "$PW_FILE" ] && [ -d "$PW_FILE" ]; then
  echo "[prep] ERROR: $PW_FILE is a directory (must be a file)"
  exit 1
fi

# password 不存在就创建默认（建议你实际挂载各 org 自己的 password.txt）
if [ ! -f "$PW_FILE" ]; then
  echo "[prep] password file not found, creating default at $PW_FILE"
  echo "org_default_password_change_me" > "$PW_FILE"
  chmod 600 "$PW_FILE" || true
fi

# 用 awk 抓取 0x+40hex（最稳）
extract_addr() {
  awk '
    match($0, /0x[0-9a-fA-F]{40}/) {
      print substr($0, RSTART, RLENGTH);
      exit
    }
  '
}

# 如果 keystore 为空就创建账户
if [ -z "$(ls -A "$DATADIR/keystore" 2>/dev/null)" ]; then
  echo "[prep] no account found, creating a new one..."
  OUT="$(geth account new --datadir "$DATADIR" --password "$PW_FILE" 2>&1 || true)"

  echo "[prep] raw output of geth account new:"
  echo "$OUT"

  NEWADDR="$(printf "%s\n" "$OUT" | extract_addr)"

  if [ -z "$NEWADDR" ]; then
    echo "[prep] failed to parse new account address"
    echo "[prep] debug: list keystore files:"
    ls -l "$DATADIR/keystore" 2>/dev/null || true
    exit 1
  fi

  echo "$NEWADDR" > "$ETHERBASE_FILE"
  echo "[prep] created account: $NEWADDR"
else
  OUT2="$(geth account list --datadir "$DATADIR" 2>&1 || true)"
  echo "[prep] raw output of geth account list:"
  echo "$OUT2"

  ADDR="$(printf "%s\n" "$OUT2" | extract_addr)"

  if [ -z "$ADDR" ]; then
    echo "[prep] failed to parse existing account"
    exit 1
  fi

  echo "$ADDR" > "$ETHERBASE_FILE"
  echo "[prep] existing account: $ADDR"
fi

ETHERBASE="$(cat "$ETHERBASE_FILE")"
echo "ETHERBASE=$ETHERBASE" > "$ENV_FILE"
echo "[prep] wrote $ENV_FILE: ETHERBASE=$ETHERBASE"
