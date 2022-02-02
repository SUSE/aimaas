from importlib import import_module
from pathlib import Path
from typing import List

from ...config import settings
from .abstract import AbstractBackend


def get() -> List[AbstractBackend]:
    backends = []
    base_import_path = ".".join(Path(__file__).parts[-4:-1])

    for backend in settings.backends:
        module = import_module(f"{base_import_path}.{backend}")
        be = getattr(module, "Backend", None)
        if not be:
            raise ValueError(f"No such authentication backend: {backend}.Backend")
        backends.append(be)

    return backends
