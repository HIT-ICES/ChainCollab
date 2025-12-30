#
# SPDX-License-Identifier: Apache-2.0
#
import logging
from requests import get, post
import json

from api.lib.agent.base import AgentBase

LOG = logging.getLogger(__name__)


class DockerAgent(AgentBase):
    """Class represents docker agent."""

    def __init__(self, node=None):
        """init DockerAgent
        param:
        node:Information needed to create, start, and delete nodes, such as organizations, nodes, and so on
        return:null
        """
        if node is None:
            node = {}
        self._id = node.get("id")
        self._name = node.get("name")
        self._urls = node.get("urls")
        self._cname = node.get("container_name")

    def create(self, info):
        """
        Create node
        :param node: Information needed to create nodes
        :return: container ID
        :rtype: string
        """
        try:
            port_map = {
                str(port.internal): str(port.external) for port in info.get("ports")
            }
            port_map_json = json.dumps(port_map)

            data = {
                "msp": info.get("msp")[2:-1],
                "tls": info.get("tls")[2:-1],
                "bootstrap_block": info.get("bootstrap_block")[2:-1],
                "peer_config_file": info.get("config_file")[2:-1],
                "orderer_config_file": info.get("config_file")[2:-1],
                "img": "yeasy/hyperledger-fabric:2.2.0",
                "cmd": (
                    'bash /tmp/init.sh "peer node start"'
                    if info.get("type") == "peer"
                    else 'bash /tmp/init.sh "orderer"'
                ),
                "name": info.get("name"),
                "type": info.get("type"),
                "port_map": port_map_json,
                "action": "create",
            }

            LOG.info("Agent node create -> %s payload=%s", f"{self._urls}/api/v1/nodes", data)
            response = post("{}/api/v1/nodes".format(self._urls), data=data)

            try:
                txt = response.json()
            except Exception:
                LOG.error("Agent node create invalid JSON: %s", response.text)
                return None

            res_block = {}
            if isinstance(txt, dict):
                if "data" in txt:
                    res_block = txt
                elif "res" in txt:
                    res_block = txt.get("res") or {}
            node_id = (
                res_block.get("data", {}).get("id")
                if isinstance(res_block, dict)
                else None
            )

            if 200 <= response.status_code < 300 and node_id:
                return node_id

            LOG.error(
                "Agent node create failed status=%s body=%s", response.status_code, txt
            )
            return None
        except Exception as e:
            LOG.error("Agent node create exception: %s", e)
            raise e

    def delete(self, *args, **kwargs):
        try:
            response = post(
                "{}/api/v1/nodes/{}".format(self._urls, self._cname),
                data={"action": "delete"},
            )
            if response.status_code == 200:
                return True
            else:
                raise response.reason
        except Exception as e:
            raise e

    def start(self, *args, **kwargs):
        try:
            response = post(
                "{}/api/v1/nodes/{}".format(self._urls, self._cname),
                data={"action": "start"},
            )
            if response.status_code == 200:
                return True
            else:
                raise response.reason
        except Exception as e:
            raise e

    def restart(self, *args, **kwargs):
        try:
            response = post(
                "{}/api/v1/nodes/{}".format(self._urls, self._cname),
                data={"action": "restart"},
            )
            if response.status_code == 200:
                return True
            else:
                raise response.reason
        except Exception as e:
            raise e

    def stop(self, *args, **kwargs):
        try:
            response = post(
                "{}/api/v1/nodes/{}".format(self._urls, self._cname),
                data={"action": "stop"},
            )
            if response.status_code == 200:
                return True
            else:
                raise response.reason
        except Exception as e:
            raise e

    def get(self, *args, **kwargs):
        try:
            response = get("{}/api/v1/nodes/{}".format(self._urls, self._cname))
            if response.status_code == 200:
                return True
            else:
                raise response.reason
        except Exception as e:
            raise e

    def update_config(self, config_file, node_type):
        try:
            cmd = 'bash /tmp/update.sh "{} node start"'.format(node_type)
            data = {
                "peer_config_file": config_file,
                "orderer_config_file": config_file,
                "action": "update",
                "cmd": cmd,
            }
            response = post(
                "{}/api/v1/nodes/{}".format(self._urls, self._cname), data=data
            )
            if response.status_code == 200:
                return True
            else:
                raise response.reason
        except Exception as e:
            raise e

    # CA Related ----------------------------------------------------------- TODO

    def ca_create(self, info):
        try:
            port_map = {
                str(port.internal): str(port.external) for port in info.get("ports")
            }
            port_map_json = json.dumps(port_map)
            data = {
                "msp": info.get("msp")[2:-1],
                "tls": info.get("tls")[2:-1],
                "bootstrap_block": info.get("bootstrap_block")[2:-1],
                "img": "yeasy/hyperledger-fabric-ca:1.4.7",
                "cmd": 'bash /tmp/init.sh "fabric-ca-server start"',
                "name": info.get("name"),
                "type": info.get("type"),
                "port_map": port_map_json,
                "action": "create",
            }

            response = post("{}/api/v1/nodes".format(self._urls), data=data)

            if response.status_code == 200:
                txt = json.loads(response.text)
                return txt["data"]["id"]
            else:
                return None
        except Exception as e:
            raise e

    def ca_create_custom(self, ca_name, port_map):
        try:
            data = {
                "ca_name": ca_name,
                "port_map": port_map,
            }
            response = post("{}/api/v1/ca".format(self._urls), data=data)

            if response.status_code == 200:
                file = response.content
                txt = json.loads(response.text)
                return txt["data"], file
            else:
                return None
        except Exception as e:
            raise e

    def ca_delete(self, *args, **kwargs):
        try:
            response = post(
                "{}/api/v1/nodes/{}".format(self._urls, self._cname),
                data={"action": "delete"},
            )
            if response.status_code == 200:
                return True
            else:
                raise response.reason
        except Exception as e:
            raise e

    def ca_start(self, ca_name):
        try:
            response = post(
                "{}/api/v1/ca/{}/operation".format(self._urls, ca_name),
                data={"action": "start"},
            )
            if response.status_code == 200:
                return True
            else:
                raise response.reason
        except Exception as e:
            raise e

    def ca_stop(self, *args, **kwargs):
        try:
            response = post(
                "{}/api/v1/nodes/{}".format(self._urls, self._cname),
                data={"action": "stop"},
            )
            if response.status_code == 200:
                return True
            else:
                raise response.reason
        except Exception as e:
            raise e

    def ca_list(self, *args, **kwargs):
        try:
            response = get("{}/api/v1/nodes".format(self._urls))
            if response.status_code == 200:
                return True
            else:
                raise response.reason
        except Exception as e:
            raise e

    def ca_register(self, *args, **kwargs):
        try:
            response = get("{}/api/v1/nodes".format(self._urls))
            if response.status_code == 200:
                return True
            else:
                raise response.reason
        except Exception as e:
            raise e

    def ca_enroll(self, *args, **kwargs):
        try:
            response = get("{}/api/v1/nodes".format(self._urls))
            if response.status_code == 200:
                return True
            else:
                raise response.reason
        except Exception as e:
            raise e

    # Port related
    def ports_gets(self, port_number, *args, **kwargs):
        try:
            params = {"port_number": port_number}
            response = get("{}/api/v1/ports".format(self._urls), params=params)
            if response.status_code == 200:
                txt = json.loads(response.text)
                avaliable_ports = txt["data"]
                print(avaliable_ports)
                return avaliable_ports
            else:
                raise response.reason
        except Exception as e:
            raise e
