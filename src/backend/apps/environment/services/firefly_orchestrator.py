from __future__ import annotations

import logging

from common.lib.ethereum.firefly_manager import FireflyContractManager


class FireflyOrchestrator:
    def __init__(self, *, logger: logging.Logger):
        self._manager = FireflyContractManager(logger=logger)

    def generate_ffi(self, *args, **kwargs):
        return self._manager.generate_ffi(*args, **kwargs)

    def register_interface(self, *args, **kwargs):
        return self._manager.register_interface(*args, **kwargs)

    def register_api(self, *args, **kwargs):
        return self._manager.register_api(*args, **kwargs)

    def register_listener(self, *args, **kwargs):
        return self._manager.register_listener(*args, **kwargs)

    def invoke_api(self, *args, **kwargs):
        return self._manager.invoke_api(*args, **kwargs)
