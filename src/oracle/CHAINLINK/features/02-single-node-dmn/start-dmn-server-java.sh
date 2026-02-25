#!/bin/bash

# DMN Decision Engine Server (Java/Spring Boot) 启动脚本

SERVER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/dmn-server-java"
JAR_FILE="$SERVER_DIR/target/dmn-server-1.0.0.jar"
PID_FILE="$SERVER_DIR/dmn-server.pid"
LOG_FILE="$SERVER_DIR/dmn-server.log"

echo "========================================="
echo "DMN Decision Engine Server (Java) 启动脚本"
echo "========================================="
echo ""

# 检查 Java 是否安装
if ! command -v java &> /dev/null; then
    echo "❌ Java 未安装，请先安装 Java 17 或更高版本"
    exit 1
fi

# 检查 Maven 是否安装
if ! command -v mvn &> /dev/null; then
    echo "❌ Maven 未安装，请先安装 Maven"
    exit 1
fi

# 检查服务器目录是否存在
if [ ! -d "$SERVER_DIR" ]; then
    echo "❌ DMN 服务器目录不存在: $SERVER_DIR"
    exit 1
fi

cd "$SERVER_DIR"

# 检查 JAR 文件是否存在，不存在则编译
if [ ! -f "$JAR_FILE" ]; then
    echo "📦 编译项目..."
    mvn clean package -DskipTests
    if [ $? -ne 0 ]; then
        echo "❌ 编译失败"
        exit 1
    fi
    echo "✅ 编译完成"
fi

# 检查是否已经在运行
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null; then
        echo "⚠️  DMN 服务器已经在运行 (PID: $PID)"
        exit 0
    else
        echo "⚠️  PID 文件存在但进程不存在，删除 PID 文件"
        rm -f "$PID_FILE"
    fi
fi

echo "🚀 启动 DMN 决策引擎服务器..."

# 启动服务器（后台运行）
nohup java -jar "$JAR_FILE" > "$LOG_FILE" 2>&1 < /dev/null &
SERVER_PID=$!

# 写入 PID 文件
echo "$SERVER_PID" > "$PID_FILE"

# 等待服务器启动
echo "⏳ 等待服务器启动..."
sleep 5

# 检查服务器是否成功启动
if ps -p $SERVER_PID > /dev/null; then
    echo "✅ DMN 服务器启动成功"
    echo "PID: $SERVER_PID"
    echo "端口: 8080"
    echo "PID 文件: $PID_FILE"
    echo "日志文件: $LOG_FILE"
    echo ""
    echo "📋 服务信息:"
    echo "   - 健康检查: curl http://localhost:8080/api/dmn/health"
    echo "   - 决策执行: POST http://localhost:8080/api/dmn/evaluate"
    echo "   - 决策信息: POST http://localhost:8080/api/dmn/input-info"
else
    echo "❌ DMN 服务器启动失败"
    if [ -f "$LOG_FILE" ]; then
        echo "🔍 错误日志:"
        tail -20 "$LOG_FILE"
    fi
    rm -f "$PID_FILE"
    exit 1
fi

# 测试服务器是否响应
echo ""
echo "🔍 测试服务器响应..."
if curl -s http://localhost:8080/api/dmn/health > /dev/null; then
    echo "✅ 服务器响应正常"
else
    echo "⚠️  服务器无响应"
fi
