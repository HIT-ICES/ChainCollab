from typing import Tuple

from werkzeug.datastructures import ImmutableMultiDict
import yaml

from ..config import (
    CA_SERVERS_PATH,
    CA_TEMPLATE_PATH,
    CONFIG,
    FABRIC_PRODUCTION_PATH,
    FABRIC_STORAGE_PATH,
)
from ..infrastructure.storage import storage_manager
from ..services.base import ContainerSpec, ProvisionContext
from ..utils import parse_port_map, require_param


class FabricPeerTemplate:
    role = "peer"

    def render(self, form_data: ImmutableMultiDict) -> Tuple[ContainerSpec, ProvisionContext]:
        node_name = require_param(form_data, "name")
        image = require_param(form_data, "img")
        cmd = require_param(form_data, "cmd")
        env = self._common_env(form_data)
        env.update(
            {
                "CORE_VM_ENDPOINT": "unix:///host/var/run/docker.sock",
                "CORE_VM_DOCKER_HOSTCONFIG_NETWORKMODE": CONFIG.fabric_network,
                "FABRIC_LOGGING_SPEC": "INFO",
                "CORE_PEER_TLS_ENABLED": "true",
                "CORE_PEER_PROFILE_ENABLED": "true",
                "CORE_PEER_TLS_CERT_FILE": "/etc/hyperledger/fabric/tls/server.crt",
                "CORE_PEER_TLS_KEY_FILE": "/etc/hyperledger/fabric/tls/server.key",
                "CORE_PEER_TLS_ROOTCERT_FILE": "/etc/hyperledger/fabric/tls/ca.crt",
                "CORE_PEER_ID": node_name,
                "CORE_PEER_ADDRESS": f"{node_name}:7051",
                "CORE_PEER_LISTENADDRESS": "0.0.0.0:7051",
                "CORE_PEER_CHAINCODEADDRESS": f"{node_name}:7052",
                "CORE_PEER_CHAINCODELISTENADDRESS": "0.0.0.0:7052",
                "CORE_PEER_GOSSIP_BOOTSTRAP": f"{node_name}:7051",
                "CORE_PEER_GOSSIP_EXTERNALENDPOINT": f"{node_name}:7051",
                "CORE_OPERATIONS_LISTENADDRESS": "0.0.0.0:17051",
            }
        )
        return self._build_spec(node_name, image, cmd, env, form_data)

    def _common_env(self, form_data):
        return {
            "HLF_NODE_MSP": form_data.get("msp"),
            "HLF_NODE_TLS": form_data.get("tls"),
            "HLF_NODE_BOOTSTRAP_BLOCK": form_data.get("bootstrap_block"),
            "HLF_NODE_PEER_CONFIG": form_data.get("peer_config_file"),
            "HLF_NODE_ORDERER_CONFIG": form_data.get("orderer_config_file"),
            "platform": "linux/amd64",
        }

    def _build_spec(self, node_name, image, cmd, env, form_data):
        port_map = parse_port_map(form_data.get("port_map"))
        fabric_dir = storage_manager.ensure_dir(FABRIC_STORAGE_PATH / node_name)
        production_dir = storage_manager.ensure_dir(FABRIC_PRODUCTION_PATH / node_name)
        volumes = [
            f"{fabric_dir}:/etc/hyperledger/fabric",
            f"{production_dir}:/var/hyperledger/production",
            "/var/run/:/host/var/run/",
        ]
        spec = ContainerSpec(
            image=image,
            command=cmd,
            name=node_name,
            environment=env,
            volumes=volumes,
            ports=port_map,
            network=CONFIG.fabric_network,
            dns_search=["."],
        )
        context = ProvisionContext(
            cleanup_paths=[str(fabric_dir), str(production_dir)],
            metadata={
                "role": self.role,
                "storage": str(fabric_dir),
                "production": str(production_dir),
            },
        )
        return spec, context


class FabricOrdererTemplate(FabricPeerTemplate):
    role = "orderer"

    def render(self, form_data: ImmutableMultiDict) -> Tuple[ContainerSpec, ProvisionContext]:
        node_name = require_param(form_data, "name")
        image = require_param(form_data, "img")
        cmd = require_param(form_data, "cmd")
        env = self._common_env(form_data)
        env.update(
            {
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
        )
        return self._build_spec(node_name, image, cmd, env, form_data)


class FabricCATemplate:
    def render(self, form_data: ImmutableMultiDict) -> Tuple[ContainerSpec, ProvisionContext]:
        ca_name = require_param(form_data, "ca_name")
        port_map = parse_port_map(form_data.get("port_map"))
        if not port_map:
            raise ValueError("port_map is required for CA")

        ca_server_home = CA_SERVERS_PATH / ca_name
        if ca_server_home.exists():
            raise ValueError("ca_name already exists")
        storage_manager.ensure_dir(ca_server_home)

        org_name = ca_name.split(".", 1)[1]
        with open(CA_TEMPLATE_PATH / "fabric-ca-server-config.yaml", "r") as f:
            config = yaml.load(f.read(), Loader=yaml.FullLoader)
            config["ca"]["name"] = ca_name + "_CA"
            config["csr"]["names"][0]["O"] = org_name
            config["csr"]["cn"] = ca_name
            config["csr"]["hosts"] = [ca_name, "localhost"]
            config["csr"]["ca"]["pathlength"] = 1
            config["registry"]["identities"][0]["name"] = "admin"
            config["registry"]["identities"][0]["pass"] = "adminpw"
            config["version"] = "1.5.7"
        with open(ca_server_home / "fabric-ca-server-config.yaml", "w") as f:
            yaml.dump(config, f)

        spec = ContainerSpec(
            image="hyperledger/fabric-ca",
            command="fabric-ca-server start -b admin:adminpw -d",
            name=ca_name,
            environment={
                "FABRIC_CA_HOME": "/etc/hyperledger/fabric-ca-server",
                "FABRIC_CA_SERVER_TLS_ENABLED": "true",
                "FABRIC_CA_SERVER_CA_NAME": ca_name,
                "FABRIC_CA_SERVER_PORT": 7054,
                "FABRIC_CA_SERVER_OPERATIONS_LISTENADDRESS": "0.0.0.0:17054",
            },
            volumes={
                str(ca_server_home.resolve()): {
                    "bind": "/etc/hyperledger/fabric-ca-server",
                    "mode": "rw",
                }
            },
            ports=port_map,
            network=CONFIG.fabric_network,
            dns_search=["."],
        )
        context = ProvisionContext(
            cleanup_paths=[str(ca_server_home)],
            metadata={"home": str(ca_server_home)},
        )
        return spec, context
