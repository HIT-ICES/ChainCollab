#
# SPDX-License-Identifier: Apache-2.0
#

import os

mode = os.environ.get("MODE", "local")

PWD = os.path.dirname(os.path.abspath(__file__))
BASE_PATH = os.path.dirname(PWD)

CELLO_HOME = os.path.join(BASE_PATH, "opt", "cello")
FABRIC_TOOL = os.path.join(BASE_PATH, "opt", "bin")
FABRIC_CONFIG = os.path.join(BASE_PATH, "opt", "config")
ORACLE_CONTRACT_PATH = os.path.join(BASE_PATH, "opt")
DMN_CONTRACT_PATH = os.path.join(BASE_PATH, "opt")
FABRIC_CFG = os.path.join(BASE_PATH, "opt", "node")
FABRIC_NODE = os.path.join(BASE_PATH, "opt", "hyperledger", "fabric")
PRODUCTION_NODE = os.path.join(BASE_PATH, "opt", "hyperledger", "production")

FABRIC_PEER_CFG = os.path.join(BASE_PATH, "opt", "node", "peer.yaml.bak")
FABRIC_ORDERER_CFG = os.path.join(BASE_PATH, "opt", "node", "orderer.yaml.bak")
FABRIC_CA_CFG = os.path.join(BASE_PATH, "opt", "node", "ca.yaml.bak")

FABRIC_CHAINCODE_STORE = os.path.join(BASE_PATH, "opt", "chaincode")
BPMN_CHAINCODE_STORE = os.path.join(BASE_PATH, "opt", "chaincode-go-bpmn")
CURRENT_IP = "192.168.1.177" if mode == "server" else "127.0.0.1"
AGENT_PORT = 7001
DEFAULT_AGENT = default_agent = {
    "name": "default_agent",
    "urls": f"http://{CURRENT_IP}:{AGENT_PORT}",
    "type": "docker",
    "status": "active",
}

DEFAULT_CHANNEL_NAME = "default"
