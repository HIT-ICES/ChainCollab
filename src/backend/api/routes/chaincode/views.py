#
# SPDX-License-Identifier: Apache-2.0
#
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
import os
import zipfile

from drf_yasg.utils import swagger_auto_schema
from api.config import FABRIC_CHAINCODE_STORE
from api.config import CELLO_HOME
from api.models import (
    BPMN,
    BPMNInstance,
    Environment,
    Node,
    ChainCode,
    Port,
    ResourceSet,
    LoleidoOrganization,
)
from api.utils.common import make_uuid
from django.core.paginator import Paginator

from api.lib.peer.chaincode import ChainCode as PeerChainCode
from api.common.serializers import PageQuerySerializer
from api.utils.common import with_common_response
from api.exceptions import ResourceNotFound

from api.routes.chaincode.serializers import (
    ChainCodePackageBody,
    ChainCodeIDSerializer,
    ChainCodeCommitBody,
    ChainCodeApproveForMyOrgBody,
    ChaincodeListResponse,
)

from api.common import ok, err
import traceback


class ChainCodeViewSet(viewsets.ViewSet):
    """Class represents Channel related operations."""

    permission_classes = [
        IsAuthenticated,
    ]

    def retrieve(self, request, *args, **kwargs):
        try:
            chaincode_id = request.parser_context["kwargs"].get("pk")
            chaincode = ChainCode.objects.get(id=chaincode_id)
            chaincode = {
                "id": chaincode.id,
                "name": chaincode.name,
                "version": chaincode.version,
                "creator": chaincode.creator.name,
                "language": chaincode.language,
                "create_ts": chaincode.create_ts,
            }
            # response = ChainCodeIDSerializer(chaincode)
            return Response(data=chaincode, status=status.HTTP_200_OK)
        except Exception as e:
            traceback.print_exc()
            return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        query_serializer=PageQuerySerializer,
        responses=with_common_response(
            {status.HTTP_201_CREATED: ChaincodeListResponse}
        ),
    )
    def list(self, request, *args, **kwargs):
        """
        List Chaincodes
        :param request: org_id
        :return: chaincode list
        :rtype: list
        """
        try:
            env_id = request.parser_context["kwargs"].get("environment_id")
            chaincodes = ChainCode.objects.filter(environment_id=env_id)

            chanincodes_list = [
                {
                    "id": chaincode.id,
                    "name": chaincode.name,
                    "version": chaincode.version,
                    "creator": chaincode.creator.name,
                    "language": chaincode.language,
                    "create_ts": chaincode.create_ts,
                }
                for chaincode in chaincodes
            ]
            # response = ChaincodeListResponse(
            #     {"data": chanincodes_list, "total": chaincodes.count()}
            # )
            return Response(data=chanincodes_list, status=status.HTTP_200_OK)
        except Exception as e:
            traceback.print_exc()
            return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        method="post",
        query_serializer=PageQuerySerializer,
        responses=with_common_response(
            {status.HTTP_201_CREATED: ChainCodeIDSerializer}
        ),
    )
    @action(detail=False, methods=["post"])
    def package(self, request, *args, **kwargs):
        serializer = ChainCodePackageBody(data=request.data)
        if not serializer.is_valid(raise_exception=True):
            return Response(err(serializer.errors), status=status.HTTP_400_BAD_REQUEST)
        name = serializer.validated_data.get("name")
        version = serializer.validated_data.get("version")
        language = serializer.validated_data.get("language")
        file = serializer.validated_data.get("file")
        env_id = request.parser_context["kwargs"].get("environment_id")
        env = Environment.objects.get(id=env_id)
        env_resource_set = (
            env.resource_sets.all().filter(sub_resource_set__org_type=0).first()
        )
        org_id = serializer.validated_data.get("org_id")

        id = make_uuid()

        try:
            file_path = os.path.join(FABRIC_CHAINCODE_STORE, id)
            if not os.path.exists(file_path):
                os.makedirs(file_path)
            fileziped = os.path.join(file_path, file.name)
            with open(fileziped, "wb") as f:
                for chunk in file.chunks():
                    f.write(chunk)
                f.close()
            zipped_file = zipfile.ZipFile(fileziped)
            for filename in zipped_file.namelist():
                zipped_file.extract(filename, file_path)

            match language:
                case "golang":
                    # When there is go.mod in the chain code, execute the go mod vendor command to obtain dependencies.
                    chaincode_path = file_path
                    found = False
                    for _, dirs, _ in os.walk(file_path):
                        if found:
                            break
                        elif dirs:
                            for each in dirs:
                                chaincode_path += "/" + each
                                if os.path.exists(chaincode_path + "/go.mod"):
                                    cwd = os.getcwd()
                                    print("cwd:", cwd)
                                    os.chdir(chaincode_path)
                                    os.system("go mod vendor")
                                    found = True
                                    os.chdir(cwd)
                                    break
                    # if can not find go.mod, use the dir after extract zipped_file
                    if not found:
                        for _, dirs, _ in os.walk(file_path):
                            chaincode_path = file_path + "/" + dirs[0]
                            break
                case "java":
                    chaincode_path = file_path
                    found = False
                    for _, dirs, _ in os.walk(file_path):
                        if found:
                            break
                        elif dirs:
                            for each in dirs:
                                chaincode_path += "/" + each
                                if os.path.exists(chaincode_path + "/build.gradle"):
                                    cwd = os.getcwd()
                                    print("cwd:", cwd)
                                    os.chdir(chaincode_path)
                                    # os.system("gradle build")
                                    found = True
                                    os.chdir(cwd)
                                    break

            # find a resource_set.sub_resource_set in env
            # fabric_resource_set = request.user.organization
            fabric_resource_set = env_resource_set.sub_resource_set.get()
            qs = Node.objects.filter(
                type="peer", fabric_resource_set=fabric_resource_set
            )
            if not qs.exists():
                raise ResourceNotFound
            peer_node = qs.first()
            envs = init_env_vars(peer_node, fabric_resource_set)
            peer_channel_cli = PeerChainCode("v2.2.0", **envs)
            res = peer_channel_cli.lifecycle_package(
                name, version, chaincode_path, language
            )
            os.system("rm -rf {}/*".format(file_path))
            os.system("mv {}.tar.gz {}".format(name, file_path))
            if res != 0:
                return Response(
                    err("package chaincode failed."),
                    status=status.HTTP_400_BAD_REQUEST,
                )
            org = LoleidoOrganization.objects.get(id=org_id)
            chaincode = ChainCode(
                id=id,
                name=name,
                version=version,
                language=language,
                creator=org,
                environment=env,
                # md5=md5
            )
            chaincode.save()
        except Exception as e:
            traceback.print_exc()
            return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)
        return Response(ok({"id": id}), status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method="post",
        responses=with_common_response(
            {status.HTTP_201_CREATED: ChainCodeIDSerializer}
        ),
    )
    @action(detail=False, methods=["post"])
    def install(self, request, *args, **kwargs):
        chaincode_id = request.data.get("id")
        peer_node_list = request.data.get("peer_node_list")
        try:
            if isinstance(peer_node_list, str):
                peer_node_list = [peer_node_list]
            cc_targz = ""
            file_path = os.path.join(FABRIC_CHAINCODE_STORE, chaincode_id)
            for _, _, files in os.walk(file_path):
                cc_targz = os.path.join(file_path + "/" + files[0])
                break
            # fabric_resource_set = request.user.organization

            # qs = Node.objects.filter(type="peer", fabric_resource_set=fabric_resource_set)
            # if not qs.exists():
            #     raise ResourceNotFound
            # peer_node = qs.first()
            peer_nodes = Node.objects.filter(type="peer", id__in=peer_node_list)

            flag = False
            for peer_node in peer_nodes:
                envs = init_env_vars(peer_node, peer_node.fabric_resource_set)

                peer_channel_cli = PeerChainCode("v2.2.0", **envs)
                import time

                start_time = time.time()
                res = peer_channel_cli.lifecycle_install(cc_targz)
                print("install time:", time.time() - start_time)
                with open("install.log", "a") as f:
                    f.write(
                        "install chaincode {} time: {}\n".format(
                            chaincode_id, time.time() - start_time
                        )
                    )
                if res != 0:
                    flag = True
            if flag == True:
                return Response(
                    err("install chaincode failed."), status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            traceback.print_exc()
            return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)
        return Response(ok("success"), status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method="get",
        responses=with_common_response(
            {status.HTTP_201_CREATED: ChainCodeIDSerializer}
        ),
    )
    @action(detail=False, methods=["get"])
    def query_installed(self, request, *args, **kwargs):
        try:
            # fabric_resource_set = request.user.organization
            peer_id = request.query_params.get("peer_id")
            try:
                peer_node = Node.objects.get(id=peer_id)
            except Node.DoesNotExist:
                raise ResourceNotFound
            fabric_resource_set = peer_node.fabric_resource_set
            envs = init_env_vars(peer_node, fabric_resource_set)

            timeout = "5s"
            peer_channel_cli = PeerChainCode("v2.2.0", **envs)
            res, installed_chaincodes = peer_channel_cli.lifecycle_query_installed(
                timeout
            )
            print("installed_chaincodes", installed_chaincodes)
            installed_chaincodes = installed_chaincodes.get("installed_chaincodes", {})
            if res != 0:
                return Response(
                    err("query installed chaincode failed."),
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return_installed_chaincodes = []
            for chaincode in installed_chaincodes:
                # if chaincode["label"].split("_").__len__() != 3:
                chaincode_id = ChainCode.objects.get(
                    name=chaincode["label"].split("_", 1)[0],
                    version=chaincode["label"].split("_", 1)[1],
                ).id
                # else:
                #     print("chaincode", chaincode["label"])
                #     chaincode_id = ChainCode.objects.filter(
                #         name="_".join(chaincode["label"].split("_", 2)[0:2]),
                #         version=chaincode["label"].split("_", 2)[2],
                #     )[0].id
                return_installed_chaincodes.append(
                    {
                        "id": chaincode_id,
                        "label": chaincode["label"],
                        "package_id": chaincode["package_id"],
                    }
                )

        except Exception as e:
            traceback.print_exc()
            return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)
        return Response(ok(return_installed_chaincodes), status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method="get",
        responses=with_common_response(
            {status.HTTP_201_CREATED: ChainCodeIDSerializer}
        ),
    )
    @action(detail=False, methods=["get"])
    def get_installed_package(self, request, *args, **kwargs):
        # get back the package from peer
        try:
            # fabric_resource_set = request.user.organization
            resource_set_id = request.data.get("resource_set_id", None)
            resource_set = ResourceSet.objects.get(pk=resource_set_id)
            fabric_resource_set = resource_set.sub_resource_set.get()

            qs = Node.objects.filter(
                type="peer", fabric_resource_set=fabric_resource_set
            )
            if not qs.exists():
                raise ResourceNotFound
            peer_node = qs.first()
            envs = init_env_vars(peer_node, fabric_resource_set)

            timeout = "5s"
            peer_channel_cli = PeerChainCode("v2.2.0", **envs)
            res = peer_channel_cli.lifecycle_get_installed_package(timeout)
            if res != 0:
                return Response(
                    err("get installed package failed."),
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)
        return Response(ok("success"), status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method="post",
        responses=with_common_response(
            {status.HTTP_201_CREATED: ChainCodeIDSerializer}
        ),
    )
    @action(detail=False, methods=["post"])
    def approve_for_my_org(self, request, *args, **kwargs):
        serializer = ChainCodeApproveForMyOrgBody(data=request.data)
        if serializer.is_valid(raise_exception=True):
            try:
                channel_name = serializer.validated_data.get("channel_name")
                chaincode_name = serializer.validated_data.get("chaincode_name")
                chaincode_version = serializer.validated_data.get("chaincode_version")
                # policy = serializer.validated_data.get("policy")
                # Perhaps the orderer's port is best stored in the database
                # orderer_url = serializer.validated_data.get("orderer_url")
                sequence = serializer.validated_data.get("sequence")
                env_id = request.parser_context["kwargs"].get("environment_id")
                env = Environment.objects.get(pk=env_id)
                resource_set_id = request.data.get("resource_set_id", None)
                resource_set = ResourceSet.objects.get(pk=resource_set_id)
                env = resource_set.environment
                fabric_resource_set = resource_set.sub_resource_set.get()
                orderer_resource_set = (
                    env.resource_sets.all().filter(sub_resource_set__org_type=1).first()
                )  # 0: UserOrg 1: SystemOrg

                orderer_node = (
                    orderer_resource_set.sub_resource_set.get()
                    .node.all()
                    .filter(type="orderer")
                    .first()
                )
                # org = request.user.organization
                # qs = Node.objects.filter(type="orderer", organization=org)
                # if not qs.exists():
                #     raise ResourceNotFound
                # orderer_node = Node.objects.get(
                #     name=orderer_url.split(":")[0].split(".")[0]
                # )
                order_org = orderer_node.fabric_resource_set
                orderer_tls_dir = "{}/{}/crypto-config/ordererOrganizations/{}/orderers/{}/msp/tlscacerts".format(
                    CELLO_HOME,
                    order_org.name,
                    order_org.name.split(".", 1)[1],
                    orderer_node.name + "." + order_org.name.split(".", 1)[1],
                )
                orderer_tls_root_cert = ""
                for _, _, files in os.walk(orderer_tls_dir):
                    orderer_tls_root_cert = orderer_tls_dir + "/" + files[0]
                    break
                qs = Node.objects.filter(
                    type="peer", fabric_resource_set=fabric_resource_set
                )
                if not qs.exists():
                    raise ResourceNotFound
                peer_node = qs.first()
                envs = init_env_vars(peer_node, fabric_resource_set)

                peer_channel_cli = PeerChainCode("v2.2.0", **envs)
                orderer_url = orderer_node.urls  # plus port
                orderer_url_with_port = (
                    orderer_url
                    + ":"
                    + str(Port.objects.get(node=orderer_node, internal=7050).external)
                )
                code, content = peer_channel_cli.lifecycle_approve_for_my_org(
                    orderer_url_with_port,
                    orderer_tls_root_cert,
                    channel_name,
                    chaincode_name,
                    chaincode_version,
                    sequence,
                )
                if code != 0:
                    return Response(
                        err(" lifecycle_approve_for_my_org failed. err: " + content),
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except Exception as e:
                traceback.print_exc()
                return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)
            return Response(ok("success"), status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method="get",
        responses=with_common_response(
            {status.HTTP_201_CREATED: ChainCodeIDSerializer}
        ),
    )
    @action(detail=False, methods=["get"])
    def query_approved(self, request, *args, **kwargs):
        # Query organization's approved chaincode definitions from its peer.
        try:
            # environment_id = request.parser_context["kwargs"].get("environment_id")
            # env = Environment.objects.get(id=environment_id)

            resource_set_id = request.query_params.get("resource_set_id", None)

            try:
                resource_set = ResourceSet.objects.get(pk=resource_set_id)
            except ResourceSet.DoesNotExist:
                raise ResourceNotFound
            fabric_resource_set = resource_set.sub_resource_set.get()
            qs = Node.objects.filter(
                type="peer", fabric_resource_set=fabric_resource_set
            )
            if not qs.exists():
                # raise ResourceNotFound
                return Response(data={"approved": False}, status=status.HTTP_200_OK)
            peer_node = qs.first()
            envs = init_env_vars(peer_node, fabric_resource_set)

            channel_name = request.query_params.get("channel_name", None)
            cc_name = request.query_params.get("chaincode_name", None)

            peer_channel_cli = PeerChainCode("v2.2.0", **envs)
            code, content = peer_channel_cli.lifecycle_query_approved(
                channel_name, cc_name
            )
            if code != 0:
                return Response(ok({"approved": False}), status=status.HTTP_200_OK)
                # return Response(
                #     err("query_approved failed."), status=status.HTTP_400_BAD_REQUEST
                # )
            return_content = {"approved": True, "content": content}
        except Exception as e:
            traceback.print_exc()
            return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)
        return Response(ok(return_content), status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method="post",
        responses=with_common_response(
            {status.HTTP_201_CREATED: ChainCodeIDSerializer}
        ),
    )
    @action(detail=False, methods=["post"])
    def check_commit_readiness(self, request, *args, **kwargs):
        serializer = ChainCodeApproveForMyOrgBody(data=request.data)
        if serializer.is_valid(raise_exception=True):
            try:
                channel_name = serializer.validated_data.get("channel_name")
                chaincode_name = serializer.validated_data.get("chaincode_name")
                chaincode_version = serializer.validated_data.get("chaincode_version")
                # policy = serializer.validated_data.get("policy")
                # Perhaps the orderer's port is best stored in the database
                # orderer_url = serializer.validated_data.get("orderer_url")
                sequence = serializer.validated_data.get("sequence")
                # orderer_fabri_resource_set = request.user.organization
                env_id = request.parser_context["kwargs"].get("environment_id")

                env = Environment.objects.get(id=env_id)
                orderer_resource_set = (
                    env.resource_sets.all().filter(sub_resource_set__org_type=1).first()
                )  # 0: UserOrg 1: SystemOrg

                orderer_node = (
                    orderer_resource_set.sub_resource_set.get().node.all().first()
                )
                # qs = Node.objects.filter(type="orderer", organization=org)
                if not orderer_node:
                    raise ResourceNotFound
                # orderer_node = qs.first()
                # orderer_node = Node.objects.get(name=orderer_url.split(":")[0].split(".")[0])
                orderer_fabric_resource_set = orderer_node.fabric_resource_set

                orderer_tls_dir = "{}/{}/crypto-config/ordererOrganizations/{}/orderers/{}/msp/tlscacerts".format(
                    CELLO_HOME,
                    orderer_fabric_resource_set.name,
                    orderer_fabric_resource_set.name.split(".", 1)[1],
                    orderer_node.name
                    + "."
                    + orderer_fabric_resource_set.name.split(".", 1)[1],
                )

                orderer_tls_root_cert = ""
                for _, _, files in os.walk(orderer_tls_dir):
                    orderer_tls_root_cert = orderer_tls_dir + "/" + files[0]
                    break

                peer_resource_set = (
                    env.resource_sets.all().filter(sub_resource_set__org_type=0).first()
                )  # 0: UserOrg 1: SystemOrg
                peer_fabric_resource_set = peer_resource_set.sub_resource_set.get()
                qs = Node.objects.filter(
                    type="peer", organization=peer_fabric_resource_set
                )
                if not qs.exists():
                    raise ResourceNotFound
                peer_node = qs.first()
                envs = init_env_vars(peer_node, peer_fabric_resource_set)

                peer_channel_cli = PeerChainCode("v2.2.0", **envs)
                orderer_url = orderer_node.urls
                code, content = peer_channel_cli.lifecycle_check_commit_readiness(
                    orderer_url,
                    orderer_tls_root_cert,
                    channel_name,
                    chaincode_name,
                    chaincode_version,
                    sequence,
                )
                if code != 0:
                    return Response(
                        err("check_commit_readiness failed."),
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            except Exception as e:
                return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)
            return Response(ok(content), status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method="post",
        responses=with_common_response(
            {status.HTTP_201_CREATED: ChainCodeIDSerializer}
        ),
    )
    @action(detail=False, methods=["post"])
    def commit(self, request, *args, **kwargs):
        serializer = ChainCodeCommitBody(data=request.data)

        def flatten(xss):
            return [x for xs in xss for x in xs]

        if serializer.is_valid(raise_exception=True):
            try:
                channel_name = serializer.validated_data.get("channel_name")
                chaincode_name = serializer.validated_data.get("chaincode_name")
                chaincode_version = serializer.validated_data.get("chaincode_version")
                # policy = serializer.validated_data.get("policy")
                # Perhaps the orderer's port is best stored in the database
                # orderer_url = serializer.validated_data.get("orderer_url")
                sequence = serializer.validated_data.get("sequence")
                # peer_list = serializer.validated_data.get("peer_list")

                env_id = request.parser_context["kwargs"].get("environment_id")
                # who commit the chaincode
                commit_resource_set_id = request.data.get("resource_set_id", None)
                commit_resource_set = ResourceSet.objects.get(pk=commit_resource_set_id)

                env = Environment.objects.get(id=env_id)

                peer_resource_sets = env.resource_sets.all().filter(
                    sub_resource_set__org_type=0
                )  # 0: UserOrg 1: SystemOrg
                peer_ids = flatten(
                    [
                        [
                            node.id
                            for node in peer_resource_set.sub_resource_set.get().node.all()
                            if node.type != "ca"
                        ]
                        for peer_resource_set in peer_resource_sets
                    ]
                )
                orderer_resource_set = (
                    env.resource_sets.all().filter(sub_resource_set__org_type=1).first()
                )  # 0: UserOrg 1: SystemOrg

                orderer_node = (
                    orderer_resource_set.sub_resource_set.get()
                    .node.all()
                    .filter(type="orderer")
                    .first()
                )
                # org = request.user.organization
                # qs = Node.objects.filter(type="orderer", organization=org)
                # if not qs.exists():
                #     raise ResourceNotFound
                # orderer_node = qs.first()
                # orderer_node = Node.objects.get(
                #     name=orderer_url.split(":")[0].split(".")[0]
                # )
                order_org = orderer_node.fabric_resource_set
                orderer_tls_dir = "{}/{}/crypto-config/ordererOrganizations/{}/orderers/{}/msp/tlscacerts".format(
                    CELLO_HOME,
                    order_org.name,
                    order_org.name.split(".", 1)[1],
                    orderer_node.name + "." + order_org.name.split(".", 1)[1],
                )

                # orderer_tls_dir = "{}/{}/crypto-config/ordererOrganizations/{}/orderers/{}/msp/tlscacerts" \
                #     .format(CELLO_HOME, org.name, org.name.split(".", 1)[1], orderer_node.name + "." +
                #             org.name.split(".", 1)[1])
                orderer_tls_root_cert = ""
                for _, _, files in os.walk(orderer_tls_dir):
                    orderer_tls_root_cert = orderer_tls_dir + "/" + files[0]
                    break

                commit_fabric_resource_set = commit_resource_set.sub_resource_set.get()
                qs = Node.objects.filter(
                    type="peer", fabric_resource_set=commit_fabric_resource_set
                )
                if not qs.exists():
                    raise ResourceNotFound
                peer_node = qs.first()
                envs = init_env_vars(peer_node, peer_node.fabric_resource_set)

                peer_root_certs = []
                peer_address_list = []
                for each in peer_ids:
                    peer_node = Node.objects.get(id=each)
                    peer_org = peer_node.fabric_resource_set
                    peer_tls_cert = "{}/{}/crypto-config/peerOrganizations/{}/peers/{}/tls/ca.crt".format(
                        CELLO_HOME,
                        peer_org.name,
                        peer_org.name,
                        peer_node.name + "." + peer_org.name,
                    )
                    # port = peer_node.port.all()[0].internal
                    # port = ports[0].internal
                    port = Port.objects.get(node=peer_node, internal=7051)
                    peer_address = (
                        peer_node.name + "." + peer_org.name + ":" + str(port.external)
                    )
                    peer_address_list.append(peer_address)
                    peer_root_certs.append(peer_tls_cert)

                peer_channel_cli = PeerChainCode("v2.2.0", **envs)
                orderer_urls = orderer_node.urls
                orderer_with_port = (
                    orderer_urls
                    + ":"
                    + str(Port.objects.get(node=orderer_node, internal=7050).external)
                )
                code = peer_channel_cli.lifecycle_commit(
                    orderer_with_port,
                    orderer_tls_root_cert,
                    channel_name,
                    chaincode_name,
                    chaincode_version,
                    peer_address_list,
                    peer_root_certs,
                    sequence,
                )
                if code != 0:
                    return Response(
                        err("commit failed."), status=status.HTTP_400_BAD_REQUEST
                    )
                try:
                    chaincode = ChainCode.objects.get(
                        name=chaincode_name, version=chaincode_version
                    )
                    bpmn_object = BPMN.objects.get(chaincode_id=chaincode.id)
                    if bpmn_object:
                        bpmn_object.status = "Installed"
                        bpmn_object.save()
                except Exception as e:
                    pass
            except Exception as e:
                traceback.print_exc()
                return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)
            return Response(ok("commit success."), status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method="get",
        responses=with_common_response(
            {status.HTTP_201_CREATED: ChainCodeIDSerializer}
        ),
    )
    @action(detail=False, methods=["get"])
    def query_committed(self, request, *args, **kwargs):
        try:
            channel_name = request.query_params.get("channel_name")
            chaincode_name = request.query_params.get("chaincode_name")

            env_id = request.parser_context["kwargs"].get("environment_id")
            env = Environment.objects.get(id=env_id)

            # org = request.user.organization
            peer_resource_set = (
                env.resource_sets.all().filter(sub_resource_set__org_type=0).first()
            )  # 0: UserOrg 1: SystemOrg
            peer_fabric_resource_set = peer_resource_set.sub_resource_set.get()
            qs = Node.objects.filter(
                type="peer", fabric_resource_set=peer_fabric_resource_set
            )
            # qs = Node.objects.filter(type="peer", organization=org)
            if not qs.exists():
                raise ResourceNotFound
            peer_node = qs.first()
            envs = init_env_vars(peer_node, peer_fabric_resource_set)
            peer_channel_cli = PeerChainCode("v2.2.0", **envs)
            code, chaincodes_commited = peer_channel_cli.lifecycle_query_committed(
                channel_name, chaincode_name
            )
            return_message = {"committed": True, "content": chaincodes_commited}
            if code != 0:
                return Response(
                    ok(
                        {
                            "committed": False,
                            "content": chaincodes_commited,
                        }
                    ),
                    status=status.HTTP_200_OK,
                )
        except Exception as e:
            return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)
        return Response(ok(return_message), status=status.HTTP_200_OK)

    # @action(detail=False, methods=['post'])
    # def invoke(self, request):
    #     try:
    #         channel_name = request.data.get("channel_name")
    #         chaincode_name = request.data.get("chaincode_name")
    #         chaincode_version = request.data.get("chaincode_version")
    #         orderer_url = request.data.get("orderer_url")
    #         org = request.user.organization
    #         qs = Node.objects.filter(type="peer", organization=org)
    #         if not qs.exists():
    #             raise ResourceNotFound
    #         peer_node = qs.first()
    #         envs = init_env_vars(peer_node, org)
    #         peer_channel_cli = PeerChainCode("v2.2.0", **envs)
    #         # orderer_url, orderer_tls_rootcert, channel_name, cc_name, args
    #         code, content = peer_channel_cli.invoke(
    #             orderer_url,
    #         if code != 0:
    #             return Response(err("invoke failed."), status=status.HTTP_400_BAD_REQUEST)


def init_env_vars(node, org):
    """
    Initialize environment variables for peer channel CLI.
    :param node: Node object
    :param org: Organization object.
    :return env: dict
    """
    org_name = org.name
    org_domain = org_name.split(".", 1)[1]
    dir_certificate = "{}/{}/crypto-config/ordererOrganizations/{}".format(
        CELLO_HOME, org_name, org_domain
    )
    dir_node = "{}/{}/crypto-config/peerOrganizations".format(CELLO_HOME, org_name)
    port = Port.objects.get(node=node, internal=7051)
    envs = {
        "CORE_PEER_TLS_ENABLED": "true",
        # "Org1.cello.comMSP"
        "CORE_PEER_LOCALMSPID": "{}MSP".format(org_name.capitalize()),
        "CORE_PEER_TLS_ROOTCERT_FILE": "{}/{}/peers/{}/tls/ca.crt".format(
            dir_node, org_name, node.name + "." + org_name
        ),
        "CORE_PEER_ADDRESS": "{}:{}".format(
            node.name + "." + org_name, str(port.external)
        ),
        # "CORE_PEER_ADDRESS":f"127.0.0.1:{port.external}",
        "CORE_PEER_MSPCONFIGPATH": "{}/{}/users/Admin@{}/msp".format(
            dir_node, org_name, org_name
        ),
        "FABRIC_CFG_PATH": "{}/{}/peers/{}/".format(
            dir_node, org_name, node.name + "." + org_name
        ),
        "ORDERER_CA": "{}/msp/tlscacerts/tlsca.{}-cert.pem".format(
            dir_certificate, org_domain
        ),
    }
    print(envs)
    return envs
