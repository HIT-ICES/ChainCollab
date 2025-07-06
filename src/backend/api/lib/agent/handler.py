#
# SPDX-License-Identifier: Apache-2.0
#
import logging

from django.conf import settings

from api.lib.agent.docker import DockerAgent
from api.lib.agent.kubernetes import KubernetesAgent
from api.common.enums import HostType

LOG = logging.getLogger(__name__)
MEDIA_ROOT = getattr(settings, "MEDIA_ROOT")


class AgentHandler(object):
    def __init__(self, node=None):
        self._network_type = node.get("network_type")
        self._network_version = node.get("network_version")
        self._node_type = node.get("type")
        self._agent_type = node.get("agent_type")
        self._node = node
        if self._agent_type == HostType.Docker.name.lower():
            self._agent = DockerAgent(node)
        elif self._agent_type == HostType.Kubernetes.name.lower():
            self._agent = KubernetesAgent(node)

    @property
    def node(self):
        return self._node

    @node.setter
    def node(self, value):
        self._node = value

    @property
    def config(self):
        return self._agent.generate_config()

    def create(self, info):
        try:
            cid = self._agent.create(info)
            if cid:
                return cid
            else:
                return None
        except Exception as e:
            raise e

    def delete(self):
        self._agent.delete()

        return True

    def start(self):
        self._agent.start()

        return True

    def stop(self):
        self._agent.stop()

        return True

    def update_config(self, config_file, node_type):
        self._agent.update_config(config_file, node_type)

        return True

    def get(self):
        try:
            return self._agent.get()
        except Exception as e:
            LOG.error(e)
            return False

    # CA related
    def ca_create_custom(self, ca_name, port_map):
        try:
            data, file = self._agent.ca_create_custom(ca_name, port_map)
            return data, file
        except Exception as e:
            raise e

    def ca_start(self, ca_name):
        try:
            return self._agent.ca_start(ca_name)
        except Exception as e:
            LOG.error(e)
            return False

    # SSI related
    def ssi_create(self, agent_name, port_map):
        try:
            data = self._agent.ssi_create(agent_name, port_map)
            return data
        except Exception as e:
            raise e

    # get avaliable ports
    def available_ports_get(self, port_number):
        try:
            return self._agent.ports_gets(port_number)
        except Exception as e:
            LOG.error(e)
            return False
