# DMN Decision Engine Server (Java/Spring Boot)

这是一个基于 Java Spring Boot 和 Camunda DMN 引擎的决策引擎服务器，专门为 Chainlink Oracle 节点设计。

## 功能特性

- **DMN 决策执行**: 接受 DMN 模型和输入数据，执行决策并返回结果
- **决策信息提取**: 解析 DMN 模型，返回决策的输入输出变量信息
- **RESTful API**: 简单易用的 HTTP 接口
- **健康检查**: 提供服务健康状态检查
- **高性能**: 基于 Spring Boot 3.2.2 和 Camunda DMN 引擎 7.21.0
- **CORS 支持**: 支持跨域请求

## 技术栈

- Java 17+
- Spring Boot 3.2.2
- Camunda DMN Engine 7.21.0
- fastjson 2.0.32 (JSON 解析)
- dom4j 2.1.4 (XML 解析)

## 安装和运行

### 1. 环境要求

- **Java 17+**: 必须安装 Java 17 或更高版本
- **Maven 3.8+**: 用于编译和构建项目

### 2. 安装 Java 和 Maven（Ubuntu/Debian）

```bash
# 安装 Java 17
sudo apt update
sudo apt install openjdk-17-jdk -y

# 验证 Java 安装
java -version
javac -version

# 安装 Maven
sudo apt install maven -y

# 验证 Maven 安装
mvn -version
```

### 3. 编译项目

```bash
cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK/scripts/dmn-server-java
mvn clean package -DskipTests
```

### 4. 启动服务器

```bash
# 使用启动脚本
cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK/scripts
./start-dmn-server-java.sh
```

或者直接使用 Java 命令：

```bash
cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK/scripts/dmn-server-java
java -jar target/dmn-server-1.0.0.jar
```

默认端口为 8080，可通过 `application.properties` 文件修改。

### 5. 验证服务

服务器启动后，可以通过以下方式验证服务：

```bash
# 健康检查
curl http://localhost:8080/api/dmn/health

# 或者使用状态检查脚本
cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK/scripts
./status-dmn-server-java.sh
```

## API 文档

### 1. 健康检查

**接口**: `GET /api/dmn/health`

**响应示例**:
```json
{
  "status": "ok",
  "timestamp": 1705296340123,
  "service": "DMN Decision Engine",
  "version": "1.0.0"
}
```

### 2. 执行决策

**接口**: `POST /api/dmn/evaluate`

**请求体**:
```json
{
  "dmnContent": "<DMN XML 内容>",
  "decisionId": "决策ID",
  "inputData": {
    "变量名": 值
  }
}
```

**响应示例**:
```json
{
  "success": true,
  "result": [{"Dish": "Pasta"}],
  "decisionId": "dish",
  "timestamp": 1705296340123
}
```

### 3. 获取决策信息

**接口**: `POST /api/dmn/input-info`

**请求体**:
```json
{
  "dmnContent": "<DMN XML 内容>"
}
```

**响应示例**:
```json
{
  "success": true,
  "inputs": [
    {
      "key": "input1",
      "label": "Temperature",
      "type": "integer",
      "name": "temperature"
    },
    {
      "key": "input2",
      "label": "Day Type",
      "type": "string",
      "name": "dayType"
    }
  ],
  "timestamp": 1705296340123
}
```

## Chainlink 集成

要在 Chainlink Oracle 节点中使用此服务，需要配置对应的 Job Spec。请参考 `job-spec-dmn-java.toml` 文件。

## 管理命令

### 启动服务器
```bash
./start-dmn-server-java.sh
```

### 停止服务器
```bash
./stop-dmn-server-java.sh
```

### 检查服务器状态
```bash
./status-dmn-server-java.sh
```

### 重新编译项目
```bash
cd dmn-server-java
mvn clean package -DskipTests
```

## 项目结构

```
dmn-server-java/
├── src/
│   ├── main/
│   │   ├── java/com/chaincollab/dmn/server/
│   │   │   ├── DmnServerApplication.java    # 主应用类
│   │   │   ├── controller/
│   │   │   │   └── DmnController.java       # REST 控制器
│   │   │   └── service/
│   │   │       └── DmnEngineService.java    # DMN 引擎服务
│   │   └── resources/
│   │       ├── application.properties       # 配置文件
│   │       └── banner.txt                   # Spring Banner
│   └── test/                                # 测试代码
├── target/                                  # 编译输出目录
├── pom.xml                                  # Maven 项目配置
└── README.md                                # 项目说明
```

## 配置

服务器配置文件位于 `src/main/resources/application.properties` 中。

主要配置项：
```properties
server.port=8080                    # 服务端口
spring.servlet.multipart.max-file-size=10MB  # 最大文件大小
```

## 与 Fabric 链码的关系

这个 DMN 服务器是从原来的 Fabric 链码（SampleDMNContract.java）中提取出来的，使用完全相同的 Camunda DMN 引擎和决策逻辑。主要的改进包括：

1. 从链码改为独立的 RESTful 服务
2. 支持通过 HTTP 请求调用
3. 可以通过 Chainlink Oracle 节点访问
4. 使用 Spring Boot 框架提供更好的服务管理功能

## 开发说明

- 使用 Camunda DMN Engine 7.21.0 执行 DMN 决策
- 支持 DMN 1.3 版本
- 使用 fastjson 进行 JSON 解析
- 使用 dom4j 解析 DMN XML 文件
- 接口支持跨域请求（CORS）
- 使用 SAX 解析器解析 XML
