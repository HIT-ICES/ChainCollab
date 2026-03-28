from __future__ import annotations

import logging

from common.lib.ethereum.identity_flow import IdentityContractFlow


class IdentityOrchestrator:
    def __init__(self, *, logger: logging.Logger):
        self._flow = IdentityContractFlow(logger=logger)

    @property
    def flow(self) -> IdentityContractFlow:
        return self._flow

    def deploy_identity_contract(self, env_id, **kwargs):
        return self._flow.deploy_identity_contract(env_id, **kwargs)

    def redeploy_and_sync(self, env_id):
        return self._flow.redeploy_and_sync(env_id)

    def get_firefly_core_url(self, env):
        return self._flow.get_firefly_core_url(env)

    def load_identity_abi(self):
        return self._flow.load_identity_abi()

    def get_identity_api_name(self, env):
        return self._flow.get_identity_api_name(env)
