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
ACAPY_IMAGE_NAME = "acapy-1.3.0"
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
    port_map = ast.literal_eval(request.form.get("port_map"))
    env = {
        "RUST_LOG": "aries-askar::log::target=error",
        "AGENT_NAME": agent_name,
    }
    command = [
            "poetry", "run", "aca-py",
            "start", "--label", agent_name,
            "--inbound-transport", "http","0.0.0.0", str(port_map["inbound"]),
            "--outbound-transport","http",
            "--endpoint",f"http://{agent_name}:{port_map['inbound']}",
            "--admin", "0.0.0.0", str(port_map["admin"]),
            "--admin-insecure-mode",
            "--tails-server-base-url",f"http://{agent_name}-tails:6543",
            "--genesis-url","http://test.bcovrin.vonx.io/genesis",
            "--wallet-type","askar",
            "--wallet-name", agent_name,
            "--wallet-key", "insecure",
            "--auto-provision",
            "--log-level",
            "debug",
            "--debug-webhooks"
            ]
    
    # 在运行容器前调用
    _ensure_image_built_from_git(
        image_tag="acapy-1.3.0",
        git_url="https://github.com/hyperledger/aries-cloudagent-python.git",
        tag="1.3.0",
        dockerfile_path="docker/Dockerfile.run"
    )
    try:
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
            ports=port_map,
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
    res["data"]["status"] = "created"
    res["data"]["id"] = container.id    
    return jsonify({"res": res}), 200


# Other Method


import os
import tempfile
import subprocess
import docker
from docker.errors import ImageNotFound, BuildError, APIError

def _ensure_image_built_from_git(image_tag: str, git_url: str, tag: str, dockerfile_path: str):
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

    print(f"🔍 Image '{image_tag}' not found. Cloning and building from {git_url}@{tag} ...")

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Clone repo
        subprocess.run(["git", "clone", git_url, tmp_dir], check=True)
        # Checkout tag
        subprocess.run(["git", "checkout", f"tags/{tag}"], cwd=tmp_dir, check=True)

        try:
            image, logs = client.images.build(
                path=tmp_dir,
                dockerfile=dockerfile_path,
                tag=image_tag,
                rm=True
            )
            for chunk in logs:
                if 'stream' in chunk:
                    print(chunk['stream'].strip())
            print(f"✅ Successfully built image: '{image_tag}'")
            return image
        except (BuildError, APIError) as e:
            print(f"❌ Failed to build image '{image_tag}': {e}")
            raise


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
