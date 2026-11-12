# Eclipse OCL Runner（Tycho / p2）

你遇到的 “Maven Central / 国内镜像找不到 `org.eclipse.ocl.*` / `org.eclipse.emf.*`” 是常见情况：Eclipse OCL（Pivot/Complete OCL）主要作为 **Eclipse bundles（p2）** 发布，并不保证在 Maven Central 提供完整的可用 artifacts。

本目录使用 **Tycho** 直接从 Eclipse release train 的 **p2 仓库**解析依赖，从而实现命令行/CI 的 OCL 校验。

## Java 版本要求

- 本方案要求 **Java 17**（Eclipse 2024+ / OCL 依赖普遍要求 Java 17）。
- 若你机器上同时装了多个 JDK，确保运行 Maven 时使用 Java 17，例如：

```bash
export JAVA_HOME=/path/to/jdk-17
export PATH="$JAVA_HOME/bin:$PATH"
java -version
mvn -version
```

## 运行（仅校验）

在 `code/ChainCollab/src/newTranslator` 下：

```bash
mvn -f MDAcheck/ocl-runner-tycho/pom.xml \
  -Decore=MDAcheck/b2c.ecore -Docl=MDAcheck/check.ocl -Dxmi=MDAcheck/chaincode.xmi \
  integration-test
```

这条命令做了三件事（一次完成）：

1. **解析/下载依赖**：Tycho 从 `pom.xml` 配置的 Eclipse p2 仓库解析 EMF/OCL/Xtext bundles，并缓存到本地 Maven 仓库。
2. **构建插件**：编译 `runner`（Eclipse bundle jar）和 `runner.tests`（测试 bundle）。
3. **执行校验**：通过 `tycho-surefire-plugin` 启动 OSGi 测试运行时，读取 `-Decore/-Docl/-Dxmi` 指定的文件并执行 Complete OCL 校验。

其中：

- `-U`（可选）会强制 Maven 重新检查远端更新；日常运行建议不加，避免每次都刷新。
- `-Dtycho.disableP2Mirrors=true` 用于避免某些网络环境下 p2 镜像导致解析异常。

## 卡住不动时怎么排查

Tycho 第一次解析/下载 p2 依赖可能比较慢（体积大 + p2 解析步骤多），看起来像“卡住”。如果长时间没有任何输出：

1) 确认 Maven 正在用 Java 17：

```bash
mvn -version
```

2) 去掉 `-q` 观察下载与解析进度（或者用 `-X` 看更详细的卡点）：

```bash
mvn -f MDAcheck/ocl-runner-tycho/pom.xml -U -Dtycho.disableP2Mirrors=true \
  -Decore=MDAcheck/b2c.ecore -Docl=MDAcheck/check.ocl -Dxmi=MDAcheck/chaincode.xmi \
  integration-test
```

3) 测试 p2 仓库是否可访问（网络/代理问题时会一直等）：

```bash
curl -I https://download.eclipse.org/releases/2025-12/
```

4) 如果 `download.eclipse.org` 访问不稳，切换到你能访问的镜像。p2 仓库 URL 可通过 Maven 属性覆盖：

```bash
mvn -q -f MDAcheck/ocl-runner-tycho/pom.xml \
  -Declipse.p2.repo=https://download.eclipse.org/releases/2025-12/ \
  -Dtycho.disableP2Mirrors=true \
  -Decore=MDAcheck/b2c.ecore -Docl=MDAcheck/check.ocl -Dxmi=MDAcheck/chaincode.xmi \
  integration-test
```

## 一键（生成 + 转换 + 校验）

```bash
bash MDAcheck/run_ocl_validate.sh
```

## 批量（对目录下所有 XMI 生成报告）

对一个目录下的所有 `*.xmi` 批量跑 Complete OCL 校验，并输出 JSON 报告（默认会为每个模型也输出一个 JSON）：

```bash
bash MDAcheck/run_ocl_validate_batch.sh \
  MDAcheck/emf-random/b2c \
  MDAcheck/b2c.ecore \
  MDAcheck/check.ocl \
  MDAcheck/ocl-report
```

输出：

- 汇总：`MDAcheck/ocl-report/report.json`
- 单模型：`MDAcheck/ocl-report/models/*.json`
- 每条 violation 会包含：
  - `code`：约束“枚举值”（通常是 `Context::InvariantName`）
  - `meaningZh`：从 `check.ocl` 对应 `inv` 上方的 `-- 注释` 自动提取的中文含义
  - `message`：原始诊断信息（保留完整细节）

## 先 build，再运行（避免重复下载/便于离线）

Tycho 跑校验时本质仍然会“先 build 再 run”。你可以分两步把依赖先缓存好：

1) **预下载/预构建**（只做构建，不跑校验）：

```bash
mvn -f MDAcheck/ocl-runner-tycho/pom.xml -DskipTests package
```

2) **离线运行校验**（依赖已缓存后可用 `-o`）：

```bash
mvn -o -f MDAcheck/ocl-runner-tycho/pom.xml \
  -Decore=MDAcheck/b2c.ecore -Docl=MDAcheck/check.ocl -Dxmi=MDAcheck/chaincode.xmi \
  integration-test
```

> 说明：Tycho 构建产物里会有 `runner/target/*.jar`，但它是 **OSGi bundle**，不是“带齐依赖即可 `java -jar` 直接运行”的单体 jar。若你想要真正的可执行分发（带 Equinox/依赖的 product），需要再做一层 Tycho product/materialize（可以继续扩展实现）。

## 参数

Tycho 测试通过系统属性接收输入文件路径（都可传绝对或相对路径）：

- `-Decore=...`
- `-Docl=...`
- `-Dxmi=...`

## 备注

- `-Dtycho.disableP2Mirrors=true` 用于避免某些网络环境下的 p2 镜像导致解析异常。
- p2 仓库默认是 `https://download.eclipse.org/releases/2025-12/`（需要 Java 17）。
  - 可用 `-Declipse.p2.repo=...` 覆盖（见上文）。
