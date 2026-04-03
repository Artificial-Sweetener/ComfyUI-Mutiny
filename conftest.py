"""Prepare minimal host stubs before pytest imports package-scoped modules."""

from __future__ import annotations

import sys
import types


class _BootstrapProgressBar:
    """Provide a no-op ComfyUI progress bar during pytest collection."""

    def __init__(self, total: int):
        """Store the total so the stub matches the host constructor."""
        self.total = total

    def update_absolute(self, value: int, total: int, preview=None) -> None:
        """Accept progress updates without performing any host work."""


comfy_module = types.ModuleType("comfy")
comfy_utils_module = types.ModuleType("comfy.utils")
comfy_utils_module.ProgressBar = _BootstrapProgressBar
comfy_module.utils = comfy_utils_module
sys.modules.setdefault("comfy", comfy_module)
sys.modules.setdefault("comfy.utils", comfy_utils_module)

collect_ignore = ["__init__.py"]
