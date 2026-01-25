#!/bin/bash

# DMN Decision Engine Server (Java/Spring Boot) 停止脚本

SERVER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/dmn-server-java"
PID_FILE="$SERVER_DIR/dmn-server.pid"

echo "========================================="
echo "DMN Decision Engine Server (Java) 停止脚本"
echo "========================================="
echo ""

if [ ! -f "$PID_FILE" ]; then
    echo "⚠️  服务器未在运行"
    exit 0
fi

PID=$(cat "$PID_FILE")

if ! ps -p $PID > /dev/null; then
    echo "⚠️  PID 文件存在但进程不存在，删除 PID 文件"
    rm -f "$PID_FILE"
    exit 0
fi

echo "⏹️  正在停止 DMN 服务器 (PID: $PID)..."

kill "$PID"

# 等待进程终止
for i in {1..5}; do
    if ! ps -p "$PID" > /dev/null; then
        echo "✅ DMN 服务器已停止"
        rm -f "$PID_FILE"
        exit 0
    fi
    echo "⏳ 等待服务器停止..."
    sleep 1
done

# 强制终止进程
echo "⚠️  强制停止服务器..."
kill -9 "$PID"

if ! ps -p "$PID" > /dev/null; then
    echo "✅ DMN 服务器已强制停止"
    rm -f "$PID_FILE"
else
    echo "❌ 无法停止 DMN 服务器"
    exit 1
fi
