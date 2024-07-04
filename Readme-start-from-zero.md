# 部署详细教程

### 1. 安装wsl/Ubuntu

方法1：使用Microsoft官方教程的 `wsl --install`，需要代理；

方法2：下载appx网址：[Manual installation steps for older versions of WSL | Microsoft Learn](https://learn.microsoft.com/en-us/windows/wsl/install-manual#downloading-distributions)。

这里以下载Ubuntu 22.04 LTS为例，下载完成后，会得到Ubuntu2204-221101.AppxBundle文件，将文件放到你想安装Ubuntu的地方，可以在非系统盘选择一个文件夹，放到指定文件夹后，将后缀AppxBundle改成zip，解压，发现里面还有一个Ubuntu_2204.1.7.0_x64.zip，再解压，点进去里面有ubuntu.exe，以管理员模式运行，就可以了。

或者商店直接下载ubuntu即可。

*将ubuntu从C盘迁移到D盘

wsl --export Ubuntu20.04 D:/export.tar

wsl --unregister Ubuntu-20.04

wsl --import Ubuntu-20.04 D:\Ubuntu_20_04\ D:\export.tar --version 2



### 2. 安装docker

##### 使用官方脚本自动安装(或者安装docker desktop)

```
 curl -fsSL https://test.docker.com -o test-docker.sh
 sudo sh test-docker.sh
 sudo apt install docker-compose
```



### 3.其他必备前置安装

##### 安装 GCC 和相关工具

 `sudo apt-get install build-essential`

##### 安装python3.10+及相关

sudo apt update

(sudo apt install software-properties-common)

(sudo add-apt-repository ppa:deadsnakes/ppa)

sudo apt install python3.10

sudo apt-get install python3.10-venv

（sudo apt install libpython3.10-dev）

（pip install setuptools==68.0.0）（降低版本）

sudo apt-get install python3-dev

##### 安装libgraphviz

`apt-get update \`
`&& apt-get install -y gettext-base graphviz libgraphviz-dev \`
`&& apt-get autoclean \`
`&& apt-get clean \`
`&& apt-get autoremove && rm -rf /var/cache/apt/`

##### 安装Go及相关

###### 1.安装

wget https://golang.google.cn/dl/go1.21.12.linux-amd64.tar.gz

sudo tar -C /usr/local -zxvf go1.21.12.linux-amd64.tar.gz

###### 2.配置go环境变量

export GOROOT=/usr/local/go

export PATH=$PATH:$GOROOT/bin 

然后source

###### 3.go依赖

（先打开代理，配置文件中加入两行，下完之后注释掉，一定打开新终端才生效）

 export http_proxy=172.26.224.1:7890

 export https_proxy=172.26.224.1:7890

cd /IBC/src/backend/opt/chaincode-go-bpmn

go build

###### 4.go下载firefly

go install github.com/hyperledger/firefly-cli/ff@latest

配置firefly环境变量（目录到bin）



##### docker镜像

docker pull yeasy/hyperledger-fabric-peer:2.2.0

docker pull hyperledger/fabric-ca:latest （如果报错，删除，执行下面两步）

(docker pull hyperledger/fabric-ca:1.5.7)

(docker tag <id> hyperledger/fabric-ca:latest)



##### 其他

赋予权限：sudo chmod 777 /etc/hosts



##### cello相关

docker network create cello-net（仅定义网络）

（先打开代理，配置文件打开注释）

 export http_proxy=172.26.224.1:7890

 export https_proxy=172.26.224.1:7890

ff start cello_env --verbose (拉取cello相关镜像，并start)



##### 克隆IBC

git clone https://github.com/XinzheShen182/IBC

git switch NewCodeGenerate



### Backend配置

创建：`python -m venv venv_name`

激活：`source venv_name/bin/activate`

`pip install -r requirements.txt`



### front配置

sudo apt install npm

sudo apt install nodejs

npm install



### agent配置

`python -m venv venv_name`

`source venv_name/bin/activate`

`pip install -r requirements.txt`



### 运行

1.初始化

source startrc

分三个终端运行

（1）start_front

（2）start_agent

（3）start_backend

2.前端操作

添加org-->添加con-->邀请org/添加mem-->添加env-一步步来，手动添加chaincode-->...





### 可能的问题

1.安装docker后，可以测试一下`service docker start` `service docker status`，running表示正常，异常提示`Docker is not running`可参考[https://blog.csdn.net/ACkingdom/article/details/125747583；](https://blog.csdn.net/ACkingdom/article/details/125747583%EF%BC%9B)

2.启动服务容器时，若输出`TypeError: kwargs_from_env() got an unexpected keyword argument 'ssl_version'`说明docker-compose版本和Docker Engine版本不符，通过

`docker version --format '{{.Server.Version}}'`查Docker Engine的版本，`docker-compose --version`查看docker-compose版本，要对应。对应表:[撰写文件版本和升级_Docker中文网 (dockerdocs.cn)](https://dockerdocs.cn/compose/compose-file/compose-versioning/) 若输出 `Couldn't connect to Docker daemon`就在命令前加sudo,或考虑将当前用户加入docker用户组；

3.,安装requirements.txt时，若报错`[Errno 13] Permission denied`，执行`pip install --user -r requirements.txt`，此时若报错 `Can not perform a '--user'`，需要打开自己设置的venv文件夹的pyvenv.cfg文件，将`include-system-site-packages`属性设置为`true`，重新执行，若使用vscode修改pyvenv.cfg文件时提示无法更改，用chmod 777 你的目录... /venv/pyvenv.cfg改一下权限或者以管理员模式打开vscode就可以了；

4.启动agent时，若报权限错误，可以在命令前加sudo,或将当前用户加入docker用户组；

5.可能会出现莫名其妙的问题，update失败，考虑是不是换源了并且换的和Ubuntu版本不匹配。考虑python版本问题，可以改一下默认python版本 使用python3 --version测试；

6.创虚拟环境出错，可能是有多个python版本冲突，创建时可以指定python版本。