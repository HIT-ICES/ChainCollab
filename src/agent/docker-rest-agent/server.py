import socket
from flask import Flask, jsonify, request, send_file, make_response
import docker
import sys
import logging
import os
import ast
import yaml
import shutil
import glob
import traceback
import time

app = Flask(__name__)
PASS_CODE = "OK"
FAIL_CODE = "Fail"

# docker_url = os.getenv("DOCKER_URL")
docker_url = "unix://var/run/docker.sock"
# storage_path = os.getenv("STORAGE_PATH")
PWD = os.path.dirname(os.path.abspath(__file__))
storage_path = os.path.join(PWD, "storage")

# from env
client = docker.DockerClient(base_url=docker_url)
res = {"code": "", "data": {}, "msg": ""}


@app.route("/api/v1/networks", methods=["GET"])
def get_network():
    logging.info("get network with docker api")
    container_list = client.containers.list()
    containers = {}
    for container in container_list:
        containers[container.id] = {
            "id": container.id,
            "short_id": container.short_id,
            "name": container.name,
            "status": container.status,
            "image": str(container.image),
            "attrs": container.attrs,
        }
    res = {"code": PASS_CODE, "data": containers, "msg": ""}
    return jsonify({"res": res})


@app.route("/api/v1/nodes", methods=["POST"])
def create_node():
    logging.info("create node with docker api")
    node_name = request.form.get("name")
    env = {
        "HLF_NODE_MSP": request.form.get("msp"),
        "HLF_NODE_TLS": request.form.get("tls"),
        "HLF_NODE_BOOTSTRAP_BLOCK": request.form.get("bootstrap_block"),
        "HLF_NODE_PEER_CONFIG": request.form.get("peer_config_file"),
        "HLF_NODE_ORDERER_CONFIG": request.form.get("orderer_config_file"),
        "platform": "linux/amd64",
    }
    port_map = ast.literal_eval(request.form.get("port_map"))
    volumes = [
        "{}/fabric/{}:/etc/hyperledger/fabric".format(storage_path, node_name),
        "{}/production/{}:/var/hyperledger/production".format(storage_path, node_name),
        "/var/run/:/host/var/run/",
    ]
    if request.form.get("type") == "peer":
        peer_envs = {
            "CORE_VM_ENDPOINT": "unix:///host/var/run/docker.sock",
            "CORE_VM_DOCKER_HOSTCONFIG_NETWORKMODE": "cello-net",
            "FABRIC_LOGGING_SPEC": "INFO",
            "CORE_PEER_TLS_ENABLED": "true",
            "CORE_PEER_PROFILE_ENABLED": "true",
            "CORE_PEER_TLS_CERT_FILE": "/etc/hyperledger/fabric/tls/server.crt",
            "CORE_PEER_TLS_KEY_FILE": "/etc/hyperledger/fabric/tls/server.key",
            "CORE_PEER_TLS_ROOTCERT_FILE": "/etc/hyperledger/fabric/tls/ca.crt",
            "CORE_PEER_ID": node_name,
            "CORE_PEER_ADDRESS": node_name + ":7051",
            "CORE_PEER_LISTENADDRESS": "0.0.0.0:7051",
            "CORE_PEER_CHAINCODEADDRESS": node_name + ":7052",
            "CORE_PEER_CHAINCODELISTENADDRESS": "0.0.0.0:7052",
            "CORE_PEER_GOSSIP_BOOTSTRAP": node_name + ":7051",
            "CORE_PEER_GOSSIP_EXTERNALENDPOINT": node_name + ":7051",
            "CORE_OPERATIONS_LISTENADDRESS": "0.0.0.0:17051",
        }
        env.update(peer_envs)
    else:
        order_envs = {
            "FABRIC_LOGGING_SPEC": "DEBUG",
            "ORDERER_GENERAL_LISTENADDRESS": "0.0.0.0",
            "ORDERER_GENERAL_LISTENPORT": "7050",
            "ORDERER_GENERAL_GENESISMETHOD": "file",
            "ORDERER_GENERAL_LOCALMSPDIR": "/etc/hyperledger/fabric/msp",
            "ORDERER_GENERAL_GENESISFILE": "/etc/hyperledger/fabric/genesis.block",
            "ORDERER_GENERAL_TLS_ENABLED": "true",
            "ORDERER_GENERAL_TLS_PRIVATEKEY": "/etc/hyperledger/fabric/tls/server.key",
            "ORDERER_GENERAL_TLS_CERTIFICATE": "/etc/hyperledger/fabric/tls/server.crt",
            "ORDERER_GENERAL_TLS_ROOTCAS": "[/etc/hyperledger/fabric/tls/ca.crt]",
            "ORDERER_GENERAL_CLUSTER_CLIENTCERTIFICATE": "/etc/hyperledger/fabric/tls/server.crt",
            "ORDERER_GENERAL_CLUSTER_CLIENTPRIVATEKEY": "/etc/hyperledger/fabric/tls/server.key",
            "ORDERER_GENERAL_CLUSTER_ROOTCAS": "[/etc/hyperledger/fabric/tls/ca.crt]",
        }
        env.update(order_envs)
    try:
        # same as `docker run -dit yeasy/hyperledge-fabric:2.2.0 -e VARIABLES``
        container = client.containers.run(
            request.form.get("img"),
            request.form.get("cmd"),
            detach=True,
            tty=True,
            stdin_open=True,
            network="cello-net",
            name=request.form.get("name"),
            dns_search=["."],
            volumes=volumes,
            environment=env,
            ports=port_map,
        )
        print("create node container {} success".format(request.form.get("name")))
    except:
        res["code"] = FAIL_CODE
        res["data"] = sys.exc_info()[0]
        res["msg"] = "creation failed"
        logging.debug(res)
        raise

    res["code"] = PASS_CODE
    res["data"]["status"] = "created"
    res["data"]["id"] = container.id
    res["data"][
        "public-grpc"
    ] = "127.0.0.1:7050"  # TODO: read the info from config file
    res["data"]["public-raft"] = "127.0.0.1:7052"
    res["msg"] = "node created"
    return jsonify(res)


@app.route("/api/v1/nodes/<id>", methods=["GET", "POST"])
def operate_node(id):
    logging.info("operate node with docker api")
    container = client.containers.get(id)
    if request.method == "POST":
        act = request.form.get("action")  # only with POST

        try:
            if act == "start":
                container.start()
                res["msg"] = "node started"
            elif act == "restart":
                container.restart()
                res["msg"] = "node restarted"
            elif act == "stop":
                container.stop()
                res["msg"] = "node stopped"
            elif act == "delete":
                container.remove()
                res["msg"] = "node deleted"
            elif act == "update":
                env = {}

                if "msp" in request.form:
                    env["HLF_NODE_MSP"] = request.form.get("msp")

                if "tls" in request.form:
                    env["HLF_NODE_TLS"] = request.form.get("tls")

                if "bootstrap_block" in request.form:
                    env["HLF_NODE_BOOTSTRAP_BLOCK"] = request.form.get(
                        "bootstrap_block"
                    )

                if "peer_config_file" in request.form:
                    env["HLF_NODE_PEER_CONFIG"] = request.form.get("peer_config_file")

                if "orderer_config_file" in request.form:
                    env["HLF_NODE_ORDERER_CONFIG"] = request.form.get(
                        "orderer_config_file"
                    )

                container.exec_run(
                    request.form.get("cmd"),
                    detach=True,
                    tty=True,
                    stdin=True,
                    environment=env,
                )
                container.restart()
                res["msg"] = "node updated"

            else:
                res["msg"] = "undefined action"
        except:
            res["code"] = FAIL_CODE
            res["data"] = sys.exc_info()[0]
            res["msg"] = act + "failed"
            logging.debug(res)
            raise
    else:
        # GET
        res["data"]["status"] = container.status

    res["code"] = PASS_CODE
    return jsonify(res)


# CA Related

STORAGE_PATH = os.path.join(PWD, "CA_related/storage")
TEMPLATE_PATH = os.path.join(PWD, "CA_related/template")
STORAGE_CA_SERVERS_PATH = os.path.join(PWD, "CA_related/storage/fabric-ca-servers")


def _create_folders_up_to_path(current_path, path):
    # 使用os.path.normpath来确保路径格式的一致性

    normalized_path = os.path.normpath(path)

    # 获取目标路径的各个部分
    folders = normalized_path.split(os.sep)

    # 逐个创建文件夹
    for folder in folders:
        current_path = os.path.join(current_path, folder)
        if not os.path.exists(current_path):
            os.makedirs(current_path)
            print(f"Created folder: {current_path}")


@app.route("/api/v1/ca", methods=["POST"])
def create_ca():
    """
    input
        ca_name: ca.cello.org.com
        port_map: 映射 7054 和 17054
        org_name: cello.org.com
    """
    try:
        ca_name = request.form.get("ca_name")
        port_map = ast.literal_eval(request.form.get("port_map"))

        _create_folders_up_to_path(
            STORAGE_CA_SERVERS_PATH,
            STORAGE_CA_SERVERS_PATH + "storage/fabric-ca-servers/",
        )
        ca_server_home = f"{STORAGE_CA_SERVERS_PATH}/{ca_name}"

        org_name = ca_name.split(".", 1)[1]

        if os.path.exists(ca_server_home):
            res = {"code": FAIL_CODE, "data": {}, "msg": "name repeat"}
            return jsonify({"res": res}), 400
        os.mkdir(ca_server_home)

        # Start a Fabric CA container with default fabric-ca-server config

        # 1. Prepare the fabric-ca-server config file
        with open(f"{TEMPLATE_PATH}/fabric-ca-server-config.yaml", "r") as f:
            config = yaml.load(f.read(), Loader=yaml.FullLoader)
            # # TODO 一定需要配置吗？官方sample没有配置
            # config["affiliations"][ca_name] = {
            #     "name": ca_name,
            #     "department": ca_name,
            #     "displayName": ca_name,
            #     "caname": ca_name,
            # }
            # TLS 为什么是false
            # ca name字段缺少
            config["ca"]["name"] = ca_name + "_CA"
            # TODO csr names为什么不配置  samples 配置了csr names，O字段配置name        #
            config["csr"]["names"][0]["O"] = org_name
            config["csr"]["cn"] = ca_name
            # TODO 模板中有localhost 字段，为什么还需要配置一次
            config["csr"]["hosts"] = [ca_name, "localhost"]
            # 应该是1  0意味着是中间CA
            config["csr"]["ca"]["pathlength"] = 1
            # TODO name pass应该从参数中传，默认是这两个
            config["registry"]["identities"][0]["name"] = "admin"
            config["registry"]["identities"][0]["pass"] = "adminpw"
            config["version"] = "1.5.7"

        # 2. Write the config file to the ca_server_home
        with open(f"{ca_server_home}/fabric-ca-server-config.yaml", "w") as f:
            yaml.dump(config, f)
    except Exception as e:
        ca_name = request.form.get("ca_name")
        ca_server_home = f"{STORAGE_CA_SERVERS_PATH}/{ca_name}"
        traceback.print_exc()
        logging.debug(e)
        # delete the ca_server_home
        # judge if exists
        if os.path.exists(ca_server_home):
            shutil.rmtree(ca_server_home)
        res = {
            "code": FAIL_CODE,
            "data": {e.__repr__},
            "msg": "create ca config failed",
        }
        return jsonify({"res": res}), 500

    # 2. Start the fabric-ca-server container
    try:
        container = client.containers.create(
            image="hyperledger/fabric-ca",
            command="fabric-ca-server start -b admin:adminpw -d",
            name=ca_name,
            ports=port_map,
            network="cello-net",
            environment={
                "FABRIC_CA_HOME": "/etc/hyperledger/fabric-ca-server",
                "FABRIC_CA_SERVER_TLS_ENABLED": "true",
                "FABRIC_CA_SERVER_CA_NAME": ca_name,
                "FABRIC_CA_SERVER_PORT": 7054,
                "FABRIC_CA_SERVER_OPERATIONS_LISTENADDRESS": "0.0.0.0:17054",
            },
            volumes={
                os.path.abspath(ca_server_home): {
                    "bind": "/etc/hyperledger/fabric-ca-server",
                    "mode": "rw",
                }
            },
        )
        res = {"code": PASS_CODE, "data": {}, "msg": "create ca success"}
        return jsonify({"res": res}), 200
    except Exception as e:
        traceback.print_exc(e)
        res = {"code": FAIL_CODE, "data": {e.__repr__}, "msg": "create ca failed"}
        # delete the ca_server_home
        shutil.rmtree(ca_server_home)
        # TODO 删除docker container
        container.stop()
        container.remove()
        return jsonify({"res": res}), 500


@app.route("/api/v1/ca/<ca_name>/operation", methods=["POST"])
def ca_operation(ca_name):
    command = request.form.get("action")

    if command == "start":
        try:
            container = client.containers.get(ca_name)
            container.start()
            time.sleep(2)
            # 等待容器启动成功，最多等待一定时间（例如，30秒）
            max_attempts = 30
            for _ in range(max_attempts):
                container.reload()  # 刷新容器状态信息
                if container.status == "running":
                    # 容器已经启动成功
                    # 把CA server公钥返回
                    ca_server_home = f"{STORAGE_CA_SERVERS_PATH}/{ca_name}"
                    file_path = (
                        ca_server_home + "/ca-cert.pem"
                    )  # 替换成您的本地文件路径

                    if os.path.isfile(file_path):
                        # 返回文件和自定义的状态码和信息
                        res = {"code": PASS_CODE, "data": {}, "msg": "start ca success"}
                        json_response = jsonify(res)
                        file_response = send_file(file_path, as_attachment=True)
                        file_response.status_code = 200
                        return file_response
                    else:
                        print(f"The file '{file_path}' does not exist.")
                        return (
                            jsonify(
                                {
                                    "res": {
                                        "code": FAIL_CODE,
                                        "data": {},
                                        "msg": "create ca fail, ca_cert doesn`t exist",
                                    }
                                }
                            ),
                            500,
                        )
                time.sleep(1)  # 等待1秒后继续检查

        except Exception as e:
            traceback.print_exc(e)
            res = {"code": FAIL_CODE, "data": {}, "msg": "start ca failed"}
            return jsonify({"res": res}), 500

    elif command == "stop":
        try:
            container = client.containers.get(ca_name)
            container.stop()
        except Exception as e:
            traceback.print_exc(e)
            res = {"code": FAIL_CODE, "data": {}, "msg": "stop ca failed"}
            return jsonify({"res": res}), 500

        res = {"code": PASS_CODE, "data": {}, "msg": "stop ca success"}
        return jsonify({"res": res}), 200


@app.route("/api/v1/ssi_agents", methods=["POST"])
def create_ssi_agent():
    """
    Create a new SSI agent.
    """
    """

    alice:
        # image: acapy-test
        build:
            context: https://github.com/hyperledger/aries-cloudagent-python.git#tags/1.3.0
            dockerfile: docker/Dockerfile.run
        ports:
        - "3001:3001"
        environment:
        RUST_LOG: 'aries-askar::log::target=error'
        command: >
        start
            --label Alice
            --inbound-transport http 0.0.0.0 3000
            --outbound-transport http
            --endpoint http://alice:3000
            --admin 0.0.0.0 3001
            --admin-insecure-mode
            --tails-server-base-url http://tails:6543
            --genesis-url http://test.bcovrin.vonx.io/genesis
            --wallet-type askar
            --wallet-name alice
            --wallet-key insecure
            --auto-provision
            --log-level debug
            --debug-webhooks
        healthcheck:
            test: curl -s -o /dev/null -w '%{http_code}' "http://localhost:3001/status/live" | grep "200" > /dev/null
            start_period: 30s
            interval: 7s
            timeout: 5s
            retries: 5
        depends_on:
        tails:
            condition: service_started
    """
    logging.info("create ssi agent with docker api")
    agent_name = request.form.get("name")
    port_str = request.form.get("port")  # 获取传入的端口字符串
    env = {
        "RUST_LOG": "aries-askar::log::target=error",
        "AGENT_NAME": agent_name,
    }
    command = [
        # "poetry", "run", "aca-py",
        "start",
        "--label",
        agent_name,
        "--inbound-transport",
        "http",
        "0.0.0.0",
        "3000",
        "--outbound-transport",
        "http",
        "--endpoint",
        f"http://{agent_name}:3000",
        "--admin",
        "0.0.0.0",
        "3001",
        "--admin-insecure-mode",
        # "--tails-server-base-url",f"http://{agent_name}-tails:6543",
        "--genesis-url",
        "http://test.bcovrin.vonx.io/genesis",
        "--wallet-type",
        "askar",
        "--wallet-name",
        agent_name,
        "--wallet-key",
        "insecure",
        "--auto-provision",
        "--log-level",
        "debug",
        "--debug-webhooks",
    ]

    # 在运行容器前调用
    _ensure_image_built_from_git(
        image_tag="acapy-1.3.0",
        git_url="https://github.com/hyperledger/aries-cloudagent-python.git",
        tag="1.3.0",
        dockerfile_path="docker/Dockerfile.run",
    )
    try:
        docker_ports = {
            f"{3001}/tcp": port_str  # 宿主机端口映射来自请求体
        }
        container = client.containers.run(
            "acapy-1.3.0",
            command,
            detach=True,
            tty=True,
            stdin_open=True,
            name=agent_name,
            network="cello-net",
            dns_search=["."],
            environment=env,
            ports=docker_ports,
        )
    except Exception as e:
        res["code"] = FAIL_CODE
        res["data"] = sys.exc_info()[0]
        res["msg"] = "creation failed: {}".format(str(e))
        logging.debug(res)
        traceback.print_exc()
        return jsonify({"res": res}), 500
    print("create ssi agent container {} success".format(agent_name))
    res["code"] = PASS_CODE
    res["data"] = {"status": "created", "id": container.id}
    return jsonify({"res": res}), 200


# Other Method


## 端口探查
# 定义一个函数来检查端口是否可用
def _is_port_available(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


# 获取指定数量的可用端口
def _get_available_ports(port_number):
    available_ports = []
    port = 1024  # 从端口1024开始检查
    while len(available_ports) < port_number and port < 65535:
        if _is_port_available(port):
            available_ports.append(port)
        port += 1

    return available_ports


from contextlib import closing


def _find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


import os
import tempfile
import subprocess
import docker
from docker.errors import ImageNotFound, BuildError, APIError


def _ensure_image_built_from_git(
    image_tag: str, git_url: str, tag: str, dockerfile_path: str
):
    """
    确保基于 Git 仓库 + Dockerfile 构建的镜像存在，不存在则自动构建。

    参数:
    - image_tag: 构建后的镜像名称（如 acapy-test）
    - git_url: 远程 Git 仓库地址（不含 tag 参数）
    - tag: Git 标签名（如 1.3.0）
    - dockerfile_path: 仓库中的 Dockerfile 路径（如 docker/Dockerfile.run）

    返回:
    - Docker image 对象
    """
    client = docker.from_env()

    # 如果镜像已经存在，就不再构建
    try:
        image = client.images.get(image_tag)
        print(f"✅ Image '{image_tag}' already exists.")
        return image
    except ImageNotFound:
        pass

    print(
        f"🔍 Image '{image_tag}' not found. Cloning and building from {git_url}@{tag} ..."
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Clone repo
        subprocess.run(["git", "clone", git_url, tmp_dir], check=True)
        # Checkout tag
        subprocess.run(["git", "checkout", f"tags/{tag}"], cwd=tmp_dir, check=True)

        try:
            image, logs = client.images.build(
                path=tmp_dir, dockerfile=dockerfile_path, tag=image_tag, rm=True
            )
            for chunk in logs:
                if "stream" in chunk:
                    print(chunk["stream"].strip())
            print(f"✅ Successfully built image: '{image_tag}'")
            return image
        except (BuildError, APIError) as e:
            print(f"❌ Failed to build image '{image_tag}': {e}")
            raise


@app.route("/api/v1/ports", methods=["GET"])
def port_probe():
    """
    given some ports which are available
    """
    port_number = request.args.get("port_number")
    if port_number is None:
        res = {"code": FAIL_CODE, "data": {}, "msg": "port is required"}
        return jsonify({"res": res}), 400
    try:
        port_number = int(port_number)
        avaliable_ports = _get_available_ports(port_number)
        res = {"code": PASS_CODE, "data": avaliable_ports, "msg": "success"}
        return jsonify({"res": res}, 200)
    except ValueError:
        res = {"code": FAIL_CODE, "data": {}, "msg": "port should be a number"}
        return jsonify({"res": res}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
