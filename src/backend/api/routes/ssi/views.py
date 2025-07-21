#
# SPDX-License-Identifier: Apache-2.0
#
import logging
import os
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.http import HttpResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
import yaml

from api.models import FabricCA as FabricCAModel, FabricResourceSet, SSIAgentNode
from api.config import CELLO_HOME, FABRIC_CONFIG
from api.utils.port_picker import set_ports_mapping, find_available_ports
from requests import get, post
import json
import traceback
from api.models import Port, Environment, ResourceSet, Membership, LoleidoOrganization
from api.common import ok, err
from api.common.enums import NodeStatus
from api.utils.host import add_host
from api.config import CURRENT_IP

LOG = logging.getLogger(__name__)


class SSIViewSet(viewsets.ViewSet):

    def _ssiAgent_create_agent(self, ssi_agent_name, port_str):
        try:
            data = {
                "name": ssi_agent_name,
                "port": port_str,
            }
            response = post(f"""http://{CURRENT_IP}:7001/api/v1/ca""", data=data)
            if response.status_code == 200:
                txt = json.loads(response.text)
                return txt["res"]
            else:
                txt = json.loads(response.text)
                print(txt)
                raise Exception(txt["res"])
        except Exception as e:
            # raise Exception(e)
            return Response(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _ssiAgent_start(self, ca_name):
        try:
            data = {
                "action": "start",
            }
            response = post(
                f"""http://{CURRENT_IP}:7001/api/v1/ca/{ca_name}/operation""",
                data=data,
            )

            if response.status_code == 200:
                file = response.content
                # txt = json.loads(response.text)
                return file
            else:
                txt = json.loads(response.text)
                print(txt)
                raise Exception(txt["res"])
        except Exception as e:
            raise e

    # atomic
    @transaction.atomic
    @action(methods=["post"], detail=False, url_path="ssi_agent_create")
    def ssi_agent_create(self, request, pk=None, *args, **kwargs):
        """
        Create a new SSI agent.
        """
        try:
            resource_set_id = self.kwargs.get("resource_set_id")
            membership_id = request.data.get("membership_id", None)
            resource_set = ResourceSet.objects.get(pk=resource_set_id)
            membership = Membership.objects.get(pk=membership_id)
            agent = resource_set.agent
            if not agent:
                return err("Agent not found", status.HTTP_404_NOT_FOUND)
            ssi_agent_name = f"ssi_agent_{resource_set.name}"
            # construct port map
            ip = agent.urls.split(":")[1].strip("//")
            ports = find_available_ports(ip, agent.id, 1)
            # create SSI agent
            ssi_agent_node=SSIAgentNode(
                name=ssi_agent_name,
                agent=agent,
                membership=membership,
                url= f"http://{CURRENT_IP}:{ports[0]}",
            )
            self._ssiAgent_create_agent(ssi_agent_name, ports[0])
            ssi_agent_node.status = NodeStatus.Running.name.lower()
            ssi_agent_node.save()
            Port.objects.create(
                external=ports[0],
                internal=3001,
                ssi_agent_node=ssi_agent_node,
            )
            return Response(
                {
                    "ssi_agent_id": ssi_agent_node.id,
                    "ssi_agent_name": ssi_agent_node.name,
                    "ssi_agent_url": ssi_agent_node.url,
                },
                status.HTTP_201_CREATED,
            )
        except Exception as e:
            LOG.error(f"Error creating SSI agent: {e}")
            return Response(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)
