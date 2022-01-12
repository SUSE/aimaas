from importlib import import_module
from typing import List

from ...config import settings
from .abstract import AbstractBackend


def get() -> List[AbstractBackend]:
    backends = []

    for backend in settings.backends:
        # TODO: Clean-up the import path
        module = import_module(f"backend.auth.backends.{backend}")
        be = getattr(module, "Backend", None)
        if not be:
            raise ValueError(f"No such authentication backend: {backend}.Backend")
        backends.append(be)

    return backends
