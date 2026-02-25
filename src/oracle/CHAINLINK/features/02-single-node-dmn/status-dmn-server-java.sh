#!/bin/bash

# DMN Decision Engine Server (Java/Spring Boot) 状态检查脚本

SERVER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/dmn-server-java"
PID_FILE="$SERVER_DIR/dmn-server.pid"
LOG_FILE="$SERVER_DIR/dmn-server.log"
JAR_FILE="$SERVER_DIR/target/dmn-server-1.0.0.jar"

echo "========================================="
echo "DMN Decision Engine Server (Java) 状态检查"
echo "========================================="
echo ""

# 检查服务器是否在运行
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null; then
        echo "✅ 服务器正在运行"
        echo "PID: $PID"
        echo "端口: 8080"

        # 检查内存使用情况（如果是 Linux 系统）
        if [ -f "/proc/$PID/status" ]; then
            MEM=$(cat /proc/$PID/status | grep VmRSS | awk '{print $2}')
            if [ -n "$MEM" ]; then
                echo "内存使用: ${MEM} kB"
            fi
        fi
    else
        echo "⚠️  PID 文件存在但进程不存在"
        rm -f "$PID_FILE"
    fi
else
    echo "❌ 服务器未在运行"
fi

# 检查 JAR 文件是否存在
if [ -f "$JAR_FILE" ]; then
    echo "✅ JAR 文件存在: $JAR_FILE"
else
    echo "⚠️  JAR 文件不存在，需要编译项目"
fi

# 检查服务器响应
echo ""
echo "📡 服务器响应检查:"
if curl -s http://localhost:8080/api/dmn/health > /dev/null; then
    echo "✅ 健康检查正常"
    # 获取服务器信息
    RESP=$(curl -s http://localhost:8080/api/dmn/health)
    VERSION=$(echo "$RESP" | grep -o '"version":"[^"]*' | cut -d'"' -f4)
    STATUS=$(echo "$RESP" | grep -o '"status":"[^"]*' | cut -d'"' -f4)
    TIMESTAMP=$(echo "$RESP" | grep -o '"timestamp":[0-9]*' | cut -d':' -f2)

    if [ -n "$VERSION" ]; then
        echo "版本: $VERSION"
    fi
    if [ -n "$TIMESTAMP" ]; then
        echo "响应时间: $(date -d @$(($TIMESTAMP/1000)))"
    fi
else
    echo "❌ 服务器无响应"
    if [ -f "$LOG_FILE" ]; then
        echo ""
        echo "📄 最近的日志信息:"
        tail -10 "$LOG_FILE"
    fi
fi

echo ""
echo "📊 服务器信息:"
echo "   - 服务器目录: $SERVER_DIR"
echo "   - 日志文件: $LOG_FILE"
echo "   - PID 文件: $PID_FILE"
echo "   - JAR 文件: $JAR_FILE"
echo "   - 启动脚本: start-dmn-server-java.sh"
echo "   - 停止脚本: stop-dmn-server-java.sh"
echo ""
echo "🔧 操作命令:"
echo "   启动: ./start-dmn-server-java.sh"
echo "   停止: ./stop-dmn-server-java.sh"
echo "   编译: cd $SERVER_DIR && mvn clean package"
