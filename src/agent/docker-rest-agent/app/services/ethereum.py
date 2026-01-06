from typing import Tuple
import time
import re
import logging

from werkzeug.datastructures import ImmutableMultiDict

from ..template_lib.ethereum import EthereumNodeTemplate
from .base import ContainerSpec, NodeProvisioner, ProvisionContext


class EthereumNodeProvisioner(NodeProvisioner):
    type_name = "eth-node"

    def __init__(self):
        self.template = EthereumNodeTemplate()

    def build_spec(
        self, form_data: ImmutableMultiDict
    ) -> Tuple[ContainerSpec, ProvisionContext]:
        # Check if type is specified to determine which method to call
        # Support both 'type' (new) and 'node_type' (legacy) for backward compatibility
        node_type = form_data.get("type") or form_data.get("node_type", "default")

        if node_type == "system":
            return self.template.create_system_node(form_data)
        elif node_type == "organization":
            return self.template.create_org_node(form_data)
        else:
            # Default behavior for backward compatibility
            return self.template.render(form_data)

    def post_create(self, container, context: ProvisionContext):
        """Hook to run after container creation."""
        extra = {}

        # If this is a system node, get the enode
        # Check both 'type' and 'node_type' for backward compatibility
        node_type = context.metadata.get("type") or context.metadata.get("node_type")
        print('node type: ',node_type)
        if node_type == "system":
            try:
                # Wait for geth to start up (may take a few seconds)
                time.sleep(5)

                # Get enode from the running container
                enode = self._get_enode_from_container(container)
                if enode:
                    extra["enode"] = enode
                    logging.info(f"System node enode: {enode}")
                else:
                    logging.warning("Failed to get enode from system node")
            except Exception as e:
                logging.exception(f"Error getting enode from system node: {e}")

        return extra

    def _get_enode_from_container(self, container) -> str:
        """Get enode from a running geth container."""
        try:
            # Execute geth attach command to get enode
            exec_result = container.exec_run(
                'geth attach --exec "admin.nodeInfo.enode"',
                stdout=True,
                stderr=True
            )

            if exec_result.exit_code != 0:
                logging.error(f"Failed to get enode: {exec_result.output.decode()}")
                return None

            # Parse the output (remove quotes and newlines)
            enode_raw = exec_result.output.decode().strip().strip('"').strip("'")

            # Replace the IP address with container name
            # e.g., enode://pubkey@172.20.0.2:30303 -> enode://pubkey@sys_geth:30303
            container_name = container.name
            enode_fixed = re.sub(
                r'@172(\.[0-9]{1,3}){3}:',
                f'@{container_name}:',
                enode_raw
            )

            return enode_fixed
        except Exception as e:
            logging.exception(f"Exception getting enode: {e}")
            return None

    def describe(self, container):
        data = super().describe(container)
        mounts = container.attrs.get("Mounts", [])
        data["mounts"] = [
            {"source": mount.get("Source"), "destination": mount.get("Destination")}
            for mount in mounts
        ]
        return data
