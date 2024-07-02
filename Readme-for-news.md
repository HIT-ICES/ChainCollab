# 后端部署

### 安装wsl/Ubuntu

方法1：使用Microsoft官方教程的 `wsl --install`，需要代理；

方法2：下载appx网址：[Manual installation steps for older versions of WSL | Microsoft Learn](https://learn.microsoft.com/en-us/windows/wsl/install-manual#downloading-distributions)。

这里以下载Ubuntu 22.04 LTS为例，下载完成后，会得到Ubuntu2204-221101.AppxBundle文件，将文件放到你想安装Ubuntu的地方，可以在非系统盘选择一个文件夹，放到指定文件夹后，将后缀AppxBundle改成zip，解压，发现里面还有一个Ubuntu_2204.1.7.0_x64.zip，再解压，点进去里面有ubuntu.exe，以管理员模式运行，就可以了。

------

### 安装docker

##### 使用官方脚本自动安装

```
 curl -fsSL https://test.docker.com -o test-docker.sh
 sudo sh test-docker.sh
```

------

### 前置安装

##### 安装 GCC 和相关工具

 `sudo apt-get install build-essential`

##### 安装Python Development Headers

`sudo apt-get install python3-dev`

##### 安装libgraphviz

`apt-get update \`
`&& apt-get install -y gettext-base graphviz libgraphviz-dev \`
`&& apt-get autoclean \`
`&& apt-get clean \`
`&& apt-get autoremove && rm -rf /var/cache/apt/`

------

### 启动服务容器

cd到/loleido/cello/src/api-engine，运行`docker-compose up -d`

应输出`cello-postgres is up-to-date` 

------

### api-engine目录相关配置

##### 配置requirements.txt

cd到/loleido/cello/src/api-engine，创建虚拟环境并激活

创建：`python -m venv venv_name`

激活：`source venv_name/bin/activate`

激活后配置requirements.txt 

`pip install -r requirements.txt`

##### 配置数据库

输入`python3 manage.py makemigrations` 和 `python3 manage.py migrate`

// 退出虚拟环境

------

### agent目录相关配置

##### 配置requirements.txt

cd到/loleido/cello/src/agent/docker-rest-agent，创建虚拟环境并激活

`python -m venv venv_name`

`source venv_name/bin/activate`

输入`pip install -r requirements.txt`

##### 启动agent

`gunicorn server:app -c ./gunicorn.conf.py`

------

### 运行test1

cd到/loleido/cello/src/api-engine，激活该目录的venv并执行`python3 manage.py runserver`命令，显示`Starting development server at http://127.0.0.1:8000/`但是在本地分支不能注册，需要切换到REDISIGN分支。

------

### 切换分支运行

`git checkout origin/REDESIGN`进到REDISIGN分支里，再激活api-engine目录里的venv，运行`python3 manage.py runserver`，可以进行注册。

------

### 问题

1.安装docker后，可以测试一下`service docker start` `service docker status`，running表示正常，异常提示`Docker is not running`可参考https://blog.csdn.net/ACkingdom/article/details/125747583；

2.启动服务容器时，若输出`TypeError: kwargs_from_env() got an unexpected keyword argument 'ssl_version'`说明docker-compose版本和Docker Engine版本不符，通过 

`docker version --format '{{.Server.Version}}'`查Docker Engine的版本，`docker-compose --version`查看docker-compose版本，要对应。对应表:[撰写文件版本和升级_Docker中文网 (dockerdocs.cn)](https://dockerdocs.cn/compose/compose-file/compose-versioning/)  若输出 `Couldn't connect to Docker daemon`就在命令前加sudo,或考虑将当前用户加入docker用户组；

3.,安装requirements.txt时，若报错`[Errno 13] Permission denied`，执行`pip install --user -r requirements.txt`，此时若报错 `Can not perform a '--user'`，需要打开自己设置的venv文件夹的pyvenv.cfg文件，将`include-system-site-packages`属性设置为`true`，重新执行，若使用vscode修改pyvenv.cfg文件时提示无法更改，用chmod 777  你的目录... /venv/pyvenv.cfg改一下权限或者以管理员模式打开vscode就可以了；

4.启动agent时，若报权限错误，可以在命令前加sudo,或将当前用户加入docker用户组；

5.可能会出现莫名其妙的问题，update失败，考虑是不是换源了并且换的和Ubuntu版本不匹配。考虑python版本问题，可以改一下默认python版本 使用python3 --version测试；

6.在REDESIGN分支里迁数据库可能会报error，虽然一般情况下不会这么办，但是推荐在注册之后回到本地分支；

7.创虚拟环境出错，可能是有多个python版本冲突，创建时可以指定python版本。

