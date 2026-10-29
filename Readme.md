# ChainCollab

ChainCollab 是一个 BPMN choreography + DMN 协作系统：建模、组织与联盟管理、Fabric/Geth 环境管理、模型到 Go/Solidity 的代码生成，以及消息、决策和跨链调用的执行。

本分支 `release-MultiBlockchain` 保留运行系统所需的源码、模板、部署资源、示例，以及原 release 的实验目录。**所有命令均从仓库根目录执行**，除非代码块中明确写了 `cd`。旧版五终端 alias、旧翻译器和历史教程不再作为启动入口。

## 1. 分支和已有环境

清理前的完整版本已经保存到 `dev-MultiBlockchain` 和 `dev-MultiBlockChain-fork`。二者以清理前 release 的 `eaea6028` 为基础，并补入旧忽略规则漏掉的前端锁文件和既有数据库迁移，保存了相同的完整运行基线；历史提交没有被强制覆盖。论文证据归档、编辑器开发工程等保留在这两个 dev 分支；`Experiment/` 则在 release 中按清理前的布局和内容完整保留。

切换到 dev 前，先在当前 release 执行 `python3 scripts/chaincollab.py down`，再切分支并使用该分支原有的启动方式；数据库与原有依赖环境继续保留。

```bash
git switch release-MultiBlockchain
# 需要继续使用清理前的开发工程时：
# git switch dev-MultiBlockchain
# 或 git switch dev-MultiBlockChain-fork
```

这里的“保存环境”指保留代码版本，并且不删除本机现有 venv、node_modules、数据库、链数据或本地配置。Git 分支本身不包含运行中的容器、数据库内容或密码。此次本机配置和数据库备份保存在 `.git/release-preservation-20261029/`，不会被发布。

## 2. 软件条件

推荐 Ubuntu 22.04 / WSL2，Python **3.10**、Node.js **22**（至少 20.19）、Docker Engine 与 `docker compose`。本次本机验证使用 Node 22.21.0、Go 1.22.0 和 FireFly CLI 1.4.0。

WSL 用户先启动 Windows Docker Desktop，在 Settings → Resources → WSL Integration 中启用当前 Ubuntu。以下两个命令都必须成功：

```bash
docker info
docker compose version
```

如果系统默认 Node 仍是 12/16，先切换版本；已经安装 nvm 时：

```bash
source "$HOME/.nvm/nvm.sh"
nvm install 22
nvm use 22
```

首次安装 Python 依赖时需要编译工具和 Graphviz 开发文件：

```bash
sudo apt-get update
sudo apt-get install -y python3.10-venv python3.10-dev build-essential pkg-config libgraphviz-dev graphviz libpq-dev
```

运行 Web 系统不要求重新构建建模器。创建区块链/FireFly 环境还需要 Go、FireFly CLI 和对应镜像，并确保工具在 PATH 中，例如已安装到默认位置时：

```bash
export PATH="/usr/local/go/bin:$HOME/go/bin:$PATH"
go version
ff version
```

## 3. 初始化：新机器和已有环境使用同一入口

```bash
git clone --branch release-MultiBlockchain https://github.com/HIT-ICES/ChainCollab.git
cd ChainCollab
python3 scripts/chaincollab.py setup
python3 scripts/chaincollab.py doctor
```

已有工作目录直接执行后两条，不需要重新克隆。`setup` 会：

- 保留已经存在的 `.venv` / `venv` 和本地 `.env`，不覆盖或重装当前正常环境。
- 仅在缺少 Python 环境时创建 Python 3.10 venv，使用对应组件的 `requirements.release.txt` 安装已捕获的依赖版本。安装因网络中断时可重跑 setup，脚本会补齐不完整依赖，健康环境不重装。
- 注册 B2CDSL、Go、Solidity 三个 editable 包；已有注册可以继续使用。
- 首次安装前端时执行 `npm ci`。建模器通过 `src/front/vendor/bpmn-chor-app-0.1.2.tgz` 安装，不需要编辑器源码服务器。

配置文件：

| 文件 | 用途 |
| --- | --- |
| `src/backend/.env` | Django、PostgreSQL、Redis、媒体路径；从 `.env.example` 创建 |
| `src/front/.env.local` | 后端/翻译器地址；从 `.env.example` 创建 |
| `src/backend/docker-compose.yml` | PostgreSQL 与 Redis |

后端配置实际读取 `src/backend/.env`，API 前缀为 `WEBROOT=/api/v1`。如果旧配置仍为 `/api`，改为 `/api/v1`，使其与主前端一致。数据库连接的库名、用户名和密码必须与 compose 的 `POSTGRES_*` 配置一致。前端使用 `VITE_BACKEND_URL`、`VITE_TRANSLATOR_URL` 和 `VITE_HOST_BASE_URL`；这些值会进入浏览器，不能填写容器内部主机名。

**已有数据库不要换主版本直接启动。** 本次确认本机 `pgdata/PG_VERSION` 为 11，因此发布默认镜像锁定为 `postgres:11.1`，本机 `.env` 也使用相同的 `POSTGRES_IMAGE`。这次整理没有夹带数据库主版本升级，没有重建数据目录。其他已有环境应使用匹配原数据目录的镜像；升级数据库应另行迁移与验证。

`POSTGRES_IMAGE` / `REDIS_IMAGE` 支持镜像源覆盖。本次本机 Redis 已从 `public.ecr.aws/docker/library/redis:7` 拉取，并在本机 `.env` 中设置了该 `REDIS_IMAGE`；这项机器网络配置不写入发布默认值。若 `docker pull` 返回网络 EOF，先恢复 registry 网络或配置可用镜像源，再启动；不要删除数据库或重装 Python 来处理镜像下载问题。

## 4. 启动、停止和日志

```bash
python3 scripts/chaincollab.py up
python3 scripts/chaincollab.py status
```

`up` 顺序：启动 PostgreSQL/Redis → 等待数据库 → 执行**已提交**的迁移 → 翻译器 → Docker agent → Celery worker → Django → 前端。正常启动不会运行 `makemigrations`，也不会清空数据库。

| 服务 | 默认地址 | 日志 |
| --- | --- | --- |
| 主前端 | http://127.0.0.1:3000 | `.runtime/front.log` |
| Django API | http://127.0.0.1:8000 | `.runtime/backend.log` |
| 翻译器与 API 文档 | http://127.0.0.1:9999/docs | `.runtime/translator.log` |
| Docker agent | http://127.0.0.1:7001 | `.runtime/agent.log` |
| Celery worker | 后台队列，使用 Redis | `.runtime/worker.log` |

```bash
# 查看日志
tail -f .runtime/backend.log
# 停止由本脚本启动的应用；数据库继续保留和运行
python3 scripts/chaincollab.py down
# 如需停止数据库容器（不删除数据卷）
python3 scripts/chaincollab.py db-stop
```

脚本只管理自己记录的 PID，并检查进程身份，不接管/终止占用相同端口的其他进程。端口已被占用时会报错；先确认对应服务，再选择复用外部部署或停止原服务。

可以在前台单独启动组件以诊断，例如：

```bash
python3 scripts/chaincollab.py run translator
python3 scripts/chaincollab.py run backend
```

外部数据库已经配置、服务也已就绪时，可以 `up --no-db`。`--no-migrate` 仅用于确认数据库已迁移的情况。只测试独立前端/翻译器而不启动数据库时：

```bash
python3 scripts/chaincollab.py up --services translator agent front --no-db --no-migrate
```

这一命令只验证所选组件，不能据此声称已经复现了完整区块链工作流。

## 5. 使用系统

首次部署可以创建管理员账户；已有数据库不要重复初始化测试数据：

```bash
python3 scripts/chaincollab.py manage createsuperuser
```

打开前端，注册/登录用户，创建组织与联盟、邀请参与组织/成员，选择 Fabric 或 Geth 创建环境，再按界面完成节点/网络/FireFly 初始化。部署前确认相应镜像可以拉取、Docker 网络存在、Go/ff 可执行文件可用。

随后导入 `examples/bpmn-dmn/SupplyChainPaper.bpmn` 和对应 `supplyChainPaper.dmn`，分配参与方，生成并部署代码，创建实例，然后执行消息、网关与决策节点。

生成代码不等于完成 DMN 服务绑定：请根据实际 DMN 文件的 decision ID 配置运行时绑定。消息采用 Send → 等待接收确认 → Complete → 完成；BusinessRule 使用 Request → 等待结果 → Continue → 写回与完成。说明见 [消息确认协议](docs/Solidity_Message_Confirmation.md)。

Oracle、DMN/OCR 和 Relayer 是执行决策/跨链时需要的独立组件，启动命令、外部条件及实际路径见 [Oracle / Relayer 操作指南](docs/ORACLE_RELAYER_SETUP.md)。它们不能在没有区块链环境时由一个 Web 启动命令凭空建立。

## 6. 独立复现 BPMN → PIM → Go / Solidity

不需要运行数据库、前端或链节点：

```bash
mkdir -p .runtime/generated/go .runtime/generated/solidity
src/newTranslator/.venv/bin/python src/newTranslator/generator/bpmn_to_dsl.py \
  examples/bpmn-dmn/SupplyChainPaper.bpmn \
  -o .runtime/generated/SupplyChainPaper.b2c -n SupplyChainPaper
src/newTranslator/.venv/bin/textx generate .runtime/generated/SupplyChainPaper.b2c \
  --target go --output-path .runtime/generated/go --overwrite
src/newTranslator/.venv/bin/textx generate .runtime/generated/SupplyChainPaper.b2c \
  --target solidity --output-path .runtime/generated/solidity --overwrite
```

这是实际解析器、textX grammar 和 Jinja 模板的生成结果。没有独立导出的 PSM 文件；DMN companion 文件在此步骤不被求值。

```bash
python3 scripts/chaincollab.py check
# 前端生产构建
(cd src/front && npm run build)
```

## 7. 发布目录

```text
Experiment/                     原 release 的实验模型、脚本和结果，保持原有布局
examples/bpmn-dmn/               可复现的结构化 BPMN / DMN 示例
scripts/chaincollab.py           唯一 setup / doctor / up / down / check 入口
src/backend/                    Django、数据库迁移、区块链部署资源
src/agent/docker-rest-agent/     Docker 资源连接器
src/front/                      主前端及 vendor 建模器分发包
src/newTranslator/              解析器、DSL、Jinja 生成器、API 与测试
src/oracle/                     被后台实际调用的 Oracle / OCR / DMN 栈
src/relayer-node/                跨链监听转发服务及其可选 UI
src/geth_identity_contract/      Geth 多实例参与方身份合约
docs/                           发布边界、操作说明和验证记录
```

`Experiment/` 包含 `BPMNwithDMNcase/`、`NoiseExperiment/`、`PerformanceTest/` 和 `new/`，完整保留清理前 release 的 3,631 个文件。结构化 SupplyChainPaper 模型位于 `Experiment/BPMNwithDMNcase/new/SupplyChainPaper.bpmn`。`examples/bpmn-dmn/` 用于上面的快速生成示例；原始实验布局和既有数据仍以 `Experiment/` 为准。本次整理没有重跑实验或改写实验结果。

[目录保留/删除依据](docs/RELEASE_LAYOUT.md) 说明哪些开发资料转留 dev 分支。`.gitignore` 隐藏本机保留的旧开发目录、venv、node_modules、配置和数据；它们可能仍在原工作目录中，但不会进入新克隆的发布源码。

## 8. 排错

- `doctor` 的 Node 版本错误：切换 nvm 版本后重新运行，不必重建 Python 环境。
- Docker API 不可用：先启动 Docker Desktop/Engine，检查当前 WSL 集成与 `docker context show`。
- 镜像拉取 EOF/超时：镜像仓库网络问题；可设置 `POSTGRES_IMAGE` / `REDIS_IMAGE` 为可用来源。
- PostgreSQL 提示 data directory version incompatible：使用与 `PG_VERSION` 匹配的主版本；不要用删除 pgdata 的方式解决。
- 翻译器缺少 b2cdsl 包：用翻译器自己的 Python 执行三个本地包的 `pip install -e`，不要安装进后端 venv。
- 创建链环境失败：检查 `.runtime/backend.log`、agent 日志、镜像/Go/ff，以及目标环境的 hosts/Docker 网络配置；主前端能打开不代表链网络已经部署。
- Oracle/Relayer 离线：按可选组件指南启动，校对节点 URL、运行时身份与 job/contract 配置。
