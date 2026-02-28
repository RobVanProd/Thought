"""Public package namespace for ThoughtWrapper."""

from __future__ import annotations

from importlib import import_module, metadata
import sys

from thought_wrapper import *  # noqa: F401,F403
from thought_wrapper import __all__ as _legacy_all

__all__ = list(_legacy_all)

try:
    __version__ = metadata.version("thoughtwrapper")
except metadata.PackageNotFoundError:  # pragma: no cover - local editable source
    __version__ = "1.0.0"

for _module in ("core", "samples", "tms", "sdk", "agent"):
    sys.modules[f"{__name__}.{_module}"] = import_module(f"thought_wrapper.{_module}")

del _legacy_all
del _module
