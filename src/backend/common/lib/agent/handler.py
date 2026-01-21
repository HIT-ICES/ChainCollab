#
# SPDX-License-Identifier: Apache-2.0
#
import logging

from apps.api.services.agent import AgentService, AgentServiceError

LOG = logging.getLogger(__name__)


class AgentHandler(object):
    """Backward-compatible facade built on top of AgentService."""

    def __init__(self, node=None):
        self._node = node or {}
        self._service = AgentService(self._node)

    @property
    def node(self):
        return self._node

    @node.setter
    def node(self, value):
        self._node = value or {}
        self._service = AgentService(self._node)

    @property
    def config(self):
        return self._service.generate_config()

    def create(self, info):
        cid = self._service.create(info)
        return cid if cid else None

    def delete(self):
        self._service.delete()
        return True

    def start(self):
        self._service.start()
        return True

    def stop(self):
        self._service.stop()
        return True

    def update_config(self, config_file, node_type):
        self._service.update_config(config_file, node_type)
        return True

    def get(self):
        try:
            return self._service.get()
        except AgentServiceError as exc:
            LOG.error(exc)
            return False

    # CA related
    def ca_create_custom(self, ca_name, port_map):
        return self._service.ca_create_custom(ca_name, port_map)

    def ca_start(self, ca_name):
        try:
            return self._service.ca_start(ca_name)
        except AgentServiceError as exc:
            LOG.error(exc)
            return False

    # get available ports
    def available_ports_get(self, port_number):
        try:
            return self._service.available_ports_get(port_number)
        except AgentServiceError as exc:
            LOG.error(exc)
            return False
