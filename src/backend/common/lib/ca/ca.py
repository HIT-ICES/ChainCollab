import os
from subprocess import call
import traceback
from apps.api.config import CELLO_HOME, FABRIC_TOOL
from common.enums import FabricCARegisterType, FabricCAEnrollType

# CELLO HOME对应的组织存的CA server的TLS  client与其交互的时候需要拿，考虑把它与fabric-ca-client.yaml路径一样


class FabricCA:
    def __init__(self, name, filepath=CELLO_HOME, fabric_tool_path=FABRIC_TOOL):
        self.ca_client = fabric_tool_path + "/fabric-ca-client"
        self.ca_server = fabric_tool_path + "/fabric-ca-server"
        self.filepath = filepath
        self.name = name

    # TODO register不指定CA的URL 端口 如何与server交互呢？
    def register(
        self, ca_name, register_name, register_type, org_path, register_pw=None
    ):
        """register use client
        eg:   fabric-ca-client register --caname ca-org1 --id.name peer0 --id.secret peer0pw --id.type peer --tls.certfiles ${PWD}/organizations/fabric-ca/org1/tls-cert.pem
        param:
            ca_name: ca_server docker config name
            register_name:
            register_pw:  如果register_pw为空，则使用默认值，这里默认值为register_name + "pw"
            type: FabricCA.RegisterType  peer,client,admin,user
            org_name:组织名字，文件夹名字  org.cello.com
        output:
            TODO
        """
        try:
            if register_type.value not in FabricCARegisterType._value2member_map_:
                raise ValueError("Invalid register type")
            if not register_pw:
                # 如果register_pw为空，则使用默认值，这里默认值为register_name + "pw"
                register_pw = register_name + "pw"

            command1 = f"""export FABRIC_CA_CLIENT_HOME={org_path}"""
            print(command1)
            # TODO  ca_server admin username password  目前默认
            command2 = [
                self.ca_client,
                "register",
                f"""--caname {ca_name} --id.name {register_name}  --id.secret {register_pw} --id.type {register_type.value}""",
                f"""--tls.certfiles {org_path}/ca-server-cert.pem""",
            ]
            command2 = " ".join(command2)
            print(command2)

            output = call(command1 + ";" + command2, shell=True)
            print("Command Output:")
            print(output)
        except Exception as e:
            traceback.print_exc(e)
            err_msg = "ca client register generate fail for {}!".format(e)
            raise Exception(err_msg)

    def enroll(
        self,
        register_name,
        ca_server_address_port,
        ca_name,
        generate_path,
        enroll_type,
        org_path,
        register_pw=None,
        hosts=None,
    ):
        """register use client
        eg:
                CA_ADMIN
                fabric-ca-client enroll -u https://admin:adminpw@localhost:7054 --caname ca-org1 --tls.certfiles ${PWD}/organizations/fabric-ca/org1/tls-cert.pem
                PEER_ORDER
                fabric-ca-client enroll -u https://peer0:peer0pw@localhost:7054 --caname ca-org1 -M ${PWD}/organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/msp --csr.hosts peer0.org1.example.com --tls.certfiles ${PWD}/organizations/fabric-ca/org1/tls-cert.pem
                TLS:
                fabric-ca-client enroll -u https://peer0:peer0pw@localhost:7054 --caname ca-org1 -M ${PWD}/organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls --enrollment.profile tls --csr.hosts peer0.org1.example.com --csr.hosts localhost --tls.certfiles ${PWD}/organizations/fabric-ca/org1/tls-cert.pem
                fabric-ca-client enroll -u https://orderer:ordererpw@localhost:9054 --caname ca-orderer -M ${PWD}/organizations/ordererOrganizations/example.com/orderers/orderer.example.com/tls --enrollment.profile tls --csr.hosts orderer.example.com --csr.hosts localhost --tls.certfiles ${PWD}/organizations/fabric-ca/ordererOrg/tls-cert.pem
                USER_ADMIN
                fabric-ca-client enroll -u https://user1:user1pw@localhost:7054 --caname ca-org1 -M ${PWD}/organizations/peerOrganizations/org1.example.com/users/User1@org1.example.com/msp --tls.certfiles ${PWD}/organizations/fabric-ca/org1/tls-cert.pem

        param:
            ca_name: ca_server docker config name
            register_name:
            register_pw:  如果register_pw为空，则使用默认值，这里默认值为register_name + "pw"
            type: FabricCA.RegisterType  peer,client,admin,user
            org_name:存放TLS证书的组织名字，文件夹名字
        output:
            TODO
        """
        try:
            if enroll_type.value not in FabricCAEnrollType._value2member_map_:
                raise ValueError("Invalid register type")
            if register_pw is None:
                # 如果register_pw为空，则使用默认值，这里默认值为register_name + "pw"
                register_pw = register_name + "pw"

            # TODO  ca_server admin username password  目前默认
            # eg ${PWD}/organizations/peerOrganizations/org1.example.com/
            command1 = f"""export FABRIC_CA_CLIENT_HOME={org_path}"""
            print(command1)
            # output = call(command, shell=True)
            # print("Command Output:")
            # print(output)

            command2 = [
                self.ca_client,
                "enroll",
                "-u",
                f"""https://{register_name}:{register_pw}@{ca_server_address_port}""",
                "--caname",
                f"""{ca_name}""",
                "--tls.certfiles",
                f"""{org_path}/ca-server-cert.pem""",
            ]
            # if entroll_type is FabricCA.EntrollType.CA_ADMIN:
            if enroll_type is FabricCAEnrollType.ADMIN_USER:
                command2.append(f"""-M {generate_path}""")
            elif (enroll_type is FabricCAEnrollType.PEER_ORDERER) or (
                enroll_type is FabricCAEnrollType.TLS
            ):
                command2.append(f"""-M {generate_path}""")
                for host in hosts:
                    command2.append(f"""--csr.hosts {host}""")
                if enroll_type is FabricCAEnrollType.TLS:
                    command2.append("--enrollment.profile tls")
            command2 = " ".join(command2)
            print(command2)

            output = call(command1 + ";" + command2, shell=True)
            print("Command Output:")
            print(output)
        except Exception as e:
            traceback.print_exc(e)
            err_msg = "ca client entroll generate fail for {}!".format(e)
            raise Exception(err_msg)

    def revoke(
        self,
    ):
        # TODO
        print(1)

    def list(
        self,
    ):
        # TODO
        print(1)
