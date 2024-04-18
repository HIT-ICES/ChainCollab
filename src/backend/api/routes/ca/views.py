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

from api.models import FabricCA as FabricCAModel, FabricResourceSet
from api.config import CELLO_HOME, FABRIC_CONFIG

# custom CA
from api.lib.ca.ca import FabricCA
from api.common.enums import FabricCAEnrollType, FabricCARegisterType, FabricCAOrgType
from api.utils.port_picker import set_ports_mapping, find_available_ports
from requests import get, post
import json
import traceback
from api.models import Node, Port, FabricCAServerType, Environment, ResourceSet
from api.common import ok, err
from api.utils.host import add_host

LOG = logging.getLogger(__name__)


class FabricCAViewSet(viewsets.ViewSet):
    # TODO 标准MSP生成方法，通过调用code/loleido/cello/src/api-engine/api/lib/ca/ca.py的方法，生成一套标准的MSP，例如Peer0的标准MSP目录，Order0的

    permission_classes = [
        IsAuthenticated,
    ]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _ca_create_agent(self, ca_name, port_map):
        try:
            data = {
                "ca_name": ca_name,
                "port_map": port_map,
            }
            response = post("{}/api/v1/ca".format("http://192.168.1.177:7001"), data=data)
            if response.status_code == 200:
                txt = json.loads(response.text)
                return txt["res"]
            else:
                txt = json.loads(response.text)
                print(txt)
                raise Exception(txt["res"])
        except Exception as e:
            raise Exception(e)

    def _ca_start(self, ca_name):
        try:
            data = {
                "action": "start",
            }
            response = post(
                "{}/api/v1/ca/{}/operation".format("http://192.168.1.177:7001", ca_name),
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

    def _create_folders_up_to_path(self, path):
        # 使用os.path.normpath来确保路径格式的一致性

        normalized_path = os.path.normpath(path)

        # 获取目标路径的各个部分
        folders = normalized_path.split(os.sep)

        # 逐个创建文件夹
        current_path = CELLO_HOME
        for folder in folders:
            current_path = os.path.join(current_path, folder)
            if not os.path.exists(current_path):
                os.makedirs(current_path)
                print(f"Created folder: {current_path}")

    def _create_start_CA_server(self, ca_name, port_map, org_name, type, infos=None):
        """
        # TODO 调用启动CA SERVER，把SERVER的TLS证书发回来，ca-cert.pem也发回来，放到CA_CLIENT_HOME/org_name/
        存到CA_CLIENT_HOME/org_name/ca_server/tls-cert.pem 对应的组织目录下 如果没有此目录，创建此目录

        input
            ca_name: ca.cello.org.com
            port_map: 映射 7054 和 17054
        """
        try:
            # 调用agent /api/v1/ca，存返回的证书
            # agent = org.agent.get()

            # 根据不同type生成 path
            if type is FabricCAOrgType.SYSTEMORG:
                # TODO 在启动CA的时候，mkdir,并且放置CA server tls证书
                org_path = "{}/{}/crypto-config/ordererOrganizations/{}/".format(
                    CELLO_HOME, org_name, org_name.split(".", 1)[1]
                )
                mkdir_path = "{}/crypto-config/ordererOrganizations/{}/".format(
                    org_name, org_name.split(".", 1)[1]
                )
                ca_file_name = "tlsca." + org_name.split(".", 1)[1] + "-cert.pem"
            elif type is FabricCAOrgType.USERORG:
                org_path = "{}/{}/crypto-config/peerOrganizations/{}/".format(
                    CELLO_HOME, org_name, org_name
                )
                mkdir_path = "{}/crypto-config/peerOrganizations/{}/".format(
                    org_name, org_name
                )
                ca_file_name = "ca.crt"
            else:
                raise "error org type"

            # 逐层创建文件夹
            self._create_folders_up_to_path(mkdir_path)
            # TODO 和agent接入逻辑
            # agent = AgentHandler(infos)
            # data, file = agent.ca_create_custom(ca_name, port_map)
            res = self._ca_create_agent(ca_name, port_map)
            # 启动CA
            # TODO 改用agent方式
            file = self._ca_start(ca_name)
            ca_server_file_path = org_path + "ca-server-cert.pem"
            # 将证书存到指定的路径
            with open(ca_server_file_path, "wb") as f:
                f.write(file)
            # print("copy ca server.pem")
            os.system(
                f"""mkdir -p {org_path}msp/tlscacerts ; mkdir -p {org_path}tlsca ; mkdir -p {org_path}ca"""
            )
            os.system(
                f"""cp {ca_server_file_path} {org_path}msp/tlscacerts/{ca_file_name} ;
                cp {ca_server_file_path} {org_path}tlsca/tlsca.{org_name}-cert.pem ;
                cp {ca_server_file_path} {org_path}ca/ca.{org_name}-cert.pem"""
            )
            # print("start ca done")
        except Exception as e:
            print(traceback.format_exc())
            err_msg = "ca server start failed {}!".format(e)
            print(err_msg)
            raise Exception(e)

    def _enroll_org_caAdmin(self, org_name, ca_server_address_port, type):
        """注册系统自带组织的CA admin  type为peer组织，或者orderer组织
        input
            org_name:   org.cello.com
            ca_server_address_port:   ca_org.cello.com:7054
            type: FabricCAOrgType
        """
        try:
            ca_name = "ca." + org_name
            # 根据不同type生成 path
            if type is FabricCAOrgType.SYSTEMORG:
                # TODO 在启动CA的时候，mkdir,并且放置CA server tls证书
                org_path = "{}/{}/crypto-config/ordererOrganizations/{}/".format(
                    CELLO_HOME, org_name, org_name.split(".", 1)[1]
                )
            elif type is FabricCAOrgType.USERORG:
                org_path = "{}/{}/crypto-config/peerOrganizations/{}/".format(
                    CELLO_HOME, org_name, org_name
                )
            else:
                raise "error org type"
            # enroll CA admin
            FabricCA(org_name).enroll(
                register_name="admin",
                ca_server_address_port=ca_server_address_port,
                ca_name=ca_name,
                generate_path=org_path,
                enroll_type=FabricCAEnrollType.CA_ADMIN,
                org_path=org_path,
            )
            # 生成msp下的config yaml
            file_names = os.listdir(org_path + "/msp/cacerts/")
            if not len(file_names) == 1:
                raise Exception("generate org ca admin msp file error")
            with open(f"{FABRIC_CONFIG}/msp_config_template.yaml", "r") as f:
                config = yaml.load(f.read(), Loader=yaml.FullLoader)
                config["NodeOUs"]["ClientOUIdentifier"][
                    "Certificate"
                ] = f"""cacerts/{file_names[0]}"""
                config["NodeOUs"]["PeerOUIdentifier"][
                    "Certificate"
                ] = f"""cacerts/{file_names[0]}"""
                config["NodeOUs"]["AdminOUIdentifier"][
                    "Certificate"
                ] = f"""cacerts/{file_names[0]}"""
                config["NodeOUs"]["OrdererOUIdentifier"][
                    "Certificate"
                ] = f"""cacerts/{file_names[0]}"""
            print("generate msp config file yaml success")
            with open(f"{org_path}/msp/config.yaml", "w") as f:
                yaml.dump(config, f)
            print("export msp config file yaml success")

        except Exception as e:
            traceback.print_exc(e)
            err_msg = "ca client enroll oderer org ca admin for {}!".format(e)
            raise Exception(e)

    def _registerAndEnroll_org_UserAdmin(self, org_name, ca_server_address_port, type):
        """register enroll组织的users(User Admin)
            orderer只需有Admin用户
            peer类型的组织 既有User 又有Admin
        input
            org_name:   org.cello.com
            ca_server_address_port:   ca_org.cello.com:7054
            type: FabricCAOrgType
        """
        try:
            ca_name = "ca." + org_name
            # 根据不同type生成 path
            if type is FabricCAOrgType.SYSTEMORG:
                org_path = "{}/{}/crypto-config/ordererOrganizations/{}/".format(
                    CELLO_HOME, org_name, org_name.split(".", 1)[1]
                )
                org_name_path = org_name.split(".", 1)[1]
                enroll_admin_path = org_path + f"""users/Admin@{org_name_path}/msp"""
            elif type is FabricCAOrgType.USERORG:
                org_path = "{}/{}/crypto-config/peerOrganizations/{}/".format(
                    CELLO_HOME, org_name, org_name
                )
                org_name_path = org_name
                enroll_admin_path = org_path + f"""users/Admin@{org_name_path}/msp"""
            else:
                raise "error org type"
            # register enroll admin
            admin_register_name = org_name.split(".")[0] + "admin"
            FabricCA(org_name).register(
                ca_name=ca_name,
                register_name=admin_register_name,
                register_type=FabricCARegisterType.ADMIN,
                org_path=org_path,
            )

            FabricCA(org_name).enroll(
                register_name=admin_register_name,
                ca_server_address_port=ca_server_address_port,
                ca_name=ca_name,
                generate_path=enroll_admin_path,
                enroll_type=FabricCAEnrollType.ADMIN_USER,
                org_path=org_path,
            )
            # cp org admin msp config.yaml to Admin
            print("cp org admin msp config.yaml to Admin")
            res = os.system(
                f"""cp {org_path}msp/config.yaml {org_path}/users/Admin@{org_name_path}/msp/config.yaml"""
            )
            print(res)

            if type is FabricCAOrgType.USERORG:
                # 注册client类型的user
                user_register_name = org_name.split(".")[0] + "user1"
                FabricCA(org_name).register(
                    ca_name=ca_name,
                    register_name=user_register_name,
                    register_type=FabricCARegisterType.CLIENT,
                    org_path=org_path,
                )

                FabricCA(org_name).enroll(
                    register_name=user_register_name,
                    ca_server_address_port=ca_server_address_port,
                    ca_name=ca_name,
                    generate_path=org_path + f"""users/User1@{org_name_path}/msp""",
                    enroll_type=FabricCAEnrollType.ADMIN_USER,
                    org_path=org_path,
                )
                print("cp org user msp config.yaml to User1")
                res = os.system(
                    f"""cp {org_path}msp/config.yaml {org_path}/users/User1@{org_name_path}/msp/config.yaml"""
                )
                print(res)

        except Exception as e:
            traceback.print_exc(e)
            err_msg = "ca client enroll org user admin for {}!".format(e)
            raise Exception(e)

    def _registerAndEnroll_node(
        self, org_name, ca_server_address_port, node_url, node_type
    ):
        """
        Peer组织只能创建peer节点 Order组织只能创建order节点
        input
            org_name:   org.cello.com
            ca_server_address_port:   ca_org.cello.com:7054
            node_url:   peer0.org.cello.com  order0.cello.com
            node_type:  FabricCAOrgType
            register enroll 一个node，可以是orderer/peer
        """
        try:
            ca_name = "ca." + org_name
            # 根据不同type生成 path
            if node_type is FabricCAOrgType.SYSTEMORG:
                register_type = FabricCARegisterType.ORDERER
                register_name = node_url.split(".")[0]
                org_path = "{}/{}/crypto-config/ordererOrganizations/{}/".format(
                    CELLO_HOME, org_name, org_name.split(".", 1)[1]
                )
                generate_path = org_path + "orderers/{}/".format(node_url)
                # org_name_path = org_name.split(".", 1)[1]
                # enroll_admin_path = (
                #     generate_path + f"""users/Admin@{org_name_path}/msp"""
                # )
            elif node_type is FabricCAOrgType.USERORG:
                register_type = FabricCARegisterType.PEER
                register_name = node_url.split(".")[0]
                org_path = "{}/{}/crypto-config/peerOrganizations/{}/".format(
                    CELLO_HOME, org_name, org_name
                )
                generate_path = org_path + "peers/{}/".format(node_url)
                # org_name_path = org_name
                # enroll_admin_path = (
                #     generate_path + f"""users/Admin@{org_name_path}/msp"""
                # )
            else:
                raise "error org type"

            FabricCA(org_name).register(
                ca_name=ca_name,
                register_name=register_name,
                register_type=register_type,
                org_path=org_path,
            )
            # enroll node
            FabricCA(org_name).enroll(
                register_name=register_name,
                ca_server_address_port=ca_server_address_port,
                ca_name=ca_name,
                generate_path=generate_path + "msp",
                enroll_type=FabricCAEnrollType.PEER_ORDERER,
                org_path=org_path,
                hosts=[node_url],
            )
            print("cp org msp config.yaml to node msp")
            res = os.system(
                f"""cp {org_path}msp/config.yaml {generate_path}msp/config.yaml"""
            )
            print(res)

            # enroll node tls
            FabricCA(org_name).enroll(
                register_name=register_name,
                ca_server_address_port=ca_server_address_port,
                ca_name=ca_name,
                generate_path=generate_path + "tls",
                enroll_type=FabricCAEnrollType.TLS,
                org_path=org_path,
                # TODO 官方加了localhost，咱们怎么加？？
                hosts=[node_url, "localhost"],
                # hosts=[node_url],
            )

            # Copy the tls CA cert, server cert, server keystore to well known file names in the peer/orderer's tls directory that are referenced by peer/orderer startup config
            print("copy tls related")
            os.system(
                f"""cp {generate_path}tls/tlscacerts/* {generate_path}tls/ca.crt"""
            )
            os.system(
                f"""cp {generate_path}tls/signcerts/* {generate_path}tls/server.crt"""
            )
            os.system(
                f"""cp {generate_path}tls/keystore/* {generate_path}tls/server.key"""
            )
            if node_type is FabricCAOrgType.SYSTEMORG:
                orderer_tls_path = generate_path + "msp/tlscacerts"
                os.mkdir(orderer_tls_path)
                ca_file_name = "tlsca." + org_name.split(".", 1)[1] + "-cert.pem"
                os.system(
                    f"""cp {generate_path}tls/tlscacerts/* {generate_path}msp/tlscacerts/{ca_file_name}"""
                )
        except Exception as e:
            traceback.print_exc(e)
            err_msg = "ca client enroll oderer orderer admin for {}!".format(e)
            raise Exception(e)

    def _set_port(self, node, agent):
        """
        get free port from agent,

        :param node: node obj
        :param agent: agent obj
        :return: none
        :rtype: none
        """
        ip = agent.urls.split(":")[1].strip("//")
        ports = find_available_ports(ip, node.id, agent.id, 1)
        set_ports_mapping(node.id, [{"internal": 7054, "external": ports[0]}], True)

    def _generate_ccp(
        self,
        ca_name,
        org_name,
        org_msp_id,
        ca_server_address_port,
        channel_name,
        orderer_org_name,
        orderer_url_port,
        peer_url_port,
    ):
        """
        此方法应该只是peer的组织来调用，因为ccp文件只需有用peer组织的
        """
        with open(f"{FABRIC_CONFIG}/ccp_template.yaml", "r") as f:
            config = yaml.load(f.read(), Loader=yaml.FullLoader)
            # 配置CA
            config["certificateAuthorities"] = {ca_name: {}}
            config["certificateAuthorities"][ca_name] = {
                "tlsCACerts": {
                    "path": f"""/etc/firefly/organizations/{org_name}/crypto-config/peerOrganizations/{org_name}/msp/tlscacerts/ca.crt"""
                },
                "url": f"""https://{ca_server_address_port.split(":")[0]}:7054""",
                "grpcOptions": {
                    "ssl-target-name-override": f"""{ca_server_address_port.split(":")[0]}"""
                },
                "registrar": {"enrollId": "admin", "enrollSecret": "adminpw"},
            }
            # 配置channel
            config["channels"] = {
                channel_name: {
                    "orderers": ["fabric_orderer"],
                    "peers": {
                        "fabric_peer": {
                            "chaincodeQuery": True,
                            "endorsingPeer": True,
                            "eventSource": True,
                            "ledgerQuery": True,
                        }
                    },
                }
            }
            # 配置client
            org_msp_path = f"""/etc/firefly/organizations/{org_name}/crypto-config/peerOrganizations/{org_name}/msp"""
            config["client"]["credentialStore"]["cryptoStore"]["path"] = org_msp_path
            config["client"]["credentialStore"]["path"] = org_msp_path
            config["client"]["cryptoconfig"]["path"] = org_msp_path
            config["client"]["organization"] = org_name
            org_admin_msp_path = f"""{CELLO_HOME}/{org_name}/crypto-config/peerOrganizations/{org_name}/users/Admin@{org_name}/msp/"""
            firefly_ccp_org_admin_msp_path = f"""/etc/firefly/organizations/{org_name}/crypto-config/peerOrganizations/{org_name}/users/Admin@{org_name}/msp/"""
            config["client"]["tlsCerts"]["client"]["cert"]["path"] = (
                firefly_ccp_org_admin_msp_path + "signcerts/cert.pem"
            )
            file_names = os.listdir(org_admin_msp_path + "keystore/")
            config["client"]["tlsCerts"]["client"]["key"]["path"] = (
                firefly_ccp_org_admin_msp_path + f"""keystore/{file_names[0]}"""
            )
            # 配置orderers
            orderer_org_name_postfix = orderer_url_port.split(":")[0].split(".", 1)[1]
            orderer_node_name = orderer_url_port.split(":")[0]
            orderer_tls_path = f"""{CELLO_HOME}/{orderer_org_name}/crypto-config/ordererOrganizations/{orderer_org_name_postfix}/orderers/{orderer_node_name}/tls/tlscacerts/"""
            firefly_ccp_orderer_tls_path = f"""/etc/firefly/organizations/{orderer_org_name}/crypto-config/ordererOrganizations/{orderer_url_port.split(":")[0].split(".", 1)[1]}/orderers/{orderer_node_name}/tls/tlscacerts/"""
            config["orderers"]["fabric_orderer"]["tlsCACerts"]["path"] = (
                firefly_ccp_orderer_tls_path + f"""{os.listdir(orderer_tls_path)[0]}"""
            )
            config["orderers"]["fabric_orderer"][
                "url"
            ] = f"""grpcs://{orderer_url_port.split(":")[0]}:7050"""
            # 配置organizations
            config["organizations"] = {
                org_name: {
                    "certificateAuthorities": [ca_name],
                    "cryptoPath": "/tmp/msp",
                    "mspid": org_msp_id,
                    "peers": ["fabric_peer"],
                }
            }
            # 配置peers
            peer_tls_path = f"""{CELLO_HOME}/{org_name}/crypto-config/peerOrganizations/{org_name}/peers/{peer_url_port.split(":")[0]}/tls/tlscacerts/"""
            firefly_ccp_peer_tls_path = f"""/etc/firefly/organizations/{org_name}/crypto-config/peerOrganizations/{org_name}/peers/{peer_url_port.split(":")[0]}/tls/tlscacerts/"""
            config["peers"]["fabric_peer"]["tlsCACerts"]["path"] = (
                firefly_ccp_peer_tls_path + f"""{os.listdir(peer_tls_path)[0]}"""
            )
            config["peers"]["fabric_peer"][
                "url"
            ] = f"""grpcs://{peer_url_port.split
                                                                 (":")[0]}:7051"""

        # 2. Write the config file to the ccp file
        with open(
            "{}/{}/crypto-config/peerOrganizations/{}/{}_ccp.yaml".format(
                CELLO_HOME, org_name, org_name, org_name
            ),
            "w",
        ) as f:
            yaml.dump(config, f)
        print(
            "generate ccp file to "
            + "{}/{}/crypto-config/peerOrganizations/{}/{}_ccp.yaml".format(
                CELLO_HOME, org_name, org_name, org_name
            )
            + " done"
        )

    # ----------CA related  apis-----------------
    # atomic
    @transaction.atomic
    @action(methods=["post"], detail=False, url_path="ca_create")
    def ca_create(self, request, pk=None, *args, **kwargs):
        print("begin ca crate post api")
        try:
            resource_set_id = request.parser_context["kwargs"].get("resource_set_id")
            resource_set = ResourceSet.objects.get(pk=resource_set_id)
            fabric_resource_set = resource_set.sub_resource_set.get()
            agent = resource_set.agent
            org_name = fabric_resource_set.name

            # create node and ca item

            node = Node(
                name="ca." + org_name,
                # JsonField
                urls="ca." + org_name,
                agent=agent,
                type="ca",
                fabric_resource_set=fabric_resource_set,
            )
            node.save()
            ca = FabricCAModel(
                # Json Field
                hosts=["ca." + org_name],
                type=FabricCAServerType.Both,
                node=node,
            )
            ca.save()
            # add ca to host
            add_host("ca."+org_name)

            # port_map = {"7054/tcp": 17054}.__repr__()

            self._set_port(node, resource_set.agent)

            port_map = {
                a["internal"]: a["external"]
                for a in Port.objects.filter(node=node)
                .values("internal", "external")
                .all()
            }.__repr__()
            self._create_start_CA_server(
                ca_name="ca." + org_name,
                port_map=port_map,
                org_name=org_name,
                type=FabricCAOrgType(int(fabric_resource_set.org_type)),
            )
            return Response(
                data=ok("ca create success"), status=status.HTTP_202_ACCEPTED
            )
        except Exception as e:
            print("________ERRORR_________")
            traceback.print_exc(e)
            return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["post"], detail=False, url_path="enroll_org_ca_admin")
    def enroll_org_ca_admin(self, request, pk=None, *args, **kwargs):
        print("begin enroll org ca and admin post api")
        try:
            resource_set_id = request.parser_context["kwargs"].get("resource_set_id")
            resource_set = ResourceSet.objects.get(pk=resource_set_id)
            fabric_resource_set = resource_set.sub_resource_set.get()
            org_name = fabric_resource_set.name

            ca = FabricCAModel.objects.get(node__fabric_resource_set=fabric_resource_set)
            port = Port.objects.get(node=ca.node, internal=7054)
            ca_server_address_port = ca.hosts[0] + ":" + str(port.external)
            print(ca_server_address_port)
            self._enroll_org_caAdmin(
                org_name=org_name,
                ca_server_address_port=ca_server_address_port,
                type=FabricCAOrgType(int(fabric_resource_set.org_type)),
            )
            return Response(data=ok("Enroll Success"), status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            traceback.print_exc(e)
            return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)

    # CA related
    @action(methods=["post"], detail=False, url_path="org_user_admin/register_enroll")
    def register_enroll_org_user_admin(self, request, pk=None, *args, **kwargs):
        print("begin register enroll org_user_admin post api")
        try:
            resource_set_id = request.parser_context["kwargs"].get("resource_set_id")
            resource_set = ResourceSet.objects.get(pk=resource_set_id)
            fabric_resource_set = resource_set.sub_resource_set.get()
            org_name = fabric_resource_set.name


            ca = FabricCAModel.objects.get(node__fabric_resource_set=fabric_resource_set)
            port = Port.objects.get(node=ca.node, internal=7054)
            ca_server_address_port = ca.hosts[0] + ":" + str(port.external)
            self._registerAndEnroll_org_UserAdmin(
                org_name=org_name,
                ca_server_address_port=ca_server_address_port,
                type=FabricCAOrgType(int(fabric_resource_set.org_type)),
            )
            return Response(data=ok("Enroll Success"), status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["post"], detail=False, url_path="register_enroll")
    def register_enroll_node(self, request, pk=None, *args, **kwargs):
        print("begin register enroll org_user_admin post api")
        try:
            node_url = request.data["node_url"]
            resource_set_id = request.parser_context["kwargs"].get("resource_set_id")
            resource_set = ResourceSet.objects.get(pk=resource_set_id)
            fabric_resource_set = resource_set.sub_resource_set.get()
            org_name = fabric_resource_set.name
            # port_map = [{"internal": 7054, "external": 17054}].__repr__()
            ca = FabricCAModel.objects.get(node__fabric_resource_set=fabric_resource_set)
            port = Port.objects.get(node=ca.node, internal=7054)
            ca_server_address_port = ca.hosts[0] + ":" + str(port.external)
            self._registerAndEnroll_node(
                org_name=org_name,
                ca_server_address_port=ca_server_address_port,
                node_url=node_url,
                node_type=FabricCAOrgType(int(fabric_resource_set.org_type)),
            )
            return Response(
                data=ok("Register and Enroll Success"), status=status.HTTP_202_ACCEPTED
            )
        except Exception as e:
            traceback.print_exc(e)
            return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)

    # TODO MOVE TO RESOURCE SET VIEW
    @action(methods=["post"], detail=False, url_path="ccp/generate")
    def ccp_generate(self, request, pk=None, *args, **kwargs):
        print("begin generate ccp")
        try:
            channel_name = request.data["channel_name"]
            # orderer_url_port = request.data["orderer_url_port"]
            peer_id = request.data["peer_id"]
            # resource_set_id = request.data['resource_set_id']
            resource_set_id = request.parser_context["kwargs"].get("resource_set_id")
            resource_set = ResourceSet.objects.get(pk=resource_set_id)
            fabric_resource_set = resource_set.sub_resource_set.get()

            # fabric_resource_set = request.user.organization
            org_name = fabric_resource_set.name
            ca = FabricCAModel.objects.get(node__fabric_resource_set=fabric_resource_set)
            port = Port.objects.get(node=ca.node, internal=7054)
            ca_server_address_port = ca.hosts[0] + ":" + str(port.external)

            env = resource_set.environment
            orderer_resource_set = ResourceSet.objects.get(
                sub_resource_set__org_type=1, environment=env
            )
            orderer_fabric_resource_set = orderer_resource_set.sub_resource_set.get()

            # orderer0.sys.edu.com
            orderer = Node.objects.get(fabric_resource_set=orderer_fabric_resource_set, type="orderer")
            port = Port.objects.get(node=orderer, internal=7050)
            print("_____________________")
            print(orderer.urls)
            # orderer_url_port = (
            #     orderer.urls.split(".", 1)[0]
            #     + "."
            #     + orderer.urls.split(".", 2)[2]
            #     + ":"
            #     + str(port.external)
            # )
            orderer_url_port = (
                orderer.urls
                + ":"
                + str(port.external)
            )

            peer = Node.objects.get(id=peer_id)
            port = Port.objects.get(node=peer, internal=7051)
            peer_url_port = peer.urls + ":" + str(port.external)

            mkdir_path = "{}/crypto-config/peerOrganizations/{}/".format(
                org_name, org_name
            )
            # 逐层创建文件夹
            self._create_folders_up_to_path(mkdir_path)
            self._generate_ccp(
                ca_name=ca.node.name,
                org_name=org_name,
                org_msp_id=org_name.capitalize() + "MSP",
                ca_server_address_port=ca_server_address_port,
                channel_name=channel_name,
                orderer_org_name=orderer_fabric_resource_set.name,
                orderer_url_port=orderer_url_port,
                peer_url_port=peer_url_port,
            )
            return Response(status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            traceback.print_exc()
            return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)


if __name__ == "__main__":
    org = FabricResourceSet.objects.get(id="")
    agent = org.agent.get()
