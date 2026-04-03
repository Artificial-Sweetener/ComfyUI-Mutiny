"""Expose the ComfyUI node mappings for this plugin."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parent
_SYNTHETIC_PACKAGE_NAME = "_comfyui_mutiny_entrypoint"


def _ensure_synthetic_package() -> types.ModuleType:
    """Create the synthetic package used by isolated local imports."""
    synthetic_package = sys.modules.get(_SYNTHETIC_PACKAGE_NAME)
    if synthetic_package is None:
        synthetic_package = types.ModuleType(_SYNTHETIC_PACKAGE_NAME)
        synthetic_package.__path__ = [str(_PACKAGE_ROOT)]
        sys.modules[_SYNTHETIC_PACKAGE_NAME] = synthetic_package
    return synthetic_package


def _load_synthetic_module(
    module_name: str,
    module_path: Path,
    *,
    submodule_search_locations: list[str] | None = None,
):
    """Load one module into the synthetic package namespace."""
    _ensure_synthetic_package()
    qualified_name = f"{_SYNTHETIC_PACKAGE_NAME}.{module_name}"
    existing_module = sys.modules.get(qualified_name)
    if existing_module is not None:
        return existing_module

    spec = importlib.util.spec_from_file_location(
        qualified_name,
        module_path,
        submodule_search_locations=submodule_search_locations,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to create an import spec for {module_name}.")

    module = importlib.util.module_from_spec(spec)
    sys.modules[qualified_name] = module
    spec.loader.exec_module(module)
    return module


def _load_node_mappings():
    """Return the exported node mappings from the nodes package."""
    if __package__:
        from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

        return NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

    nodes_module = _load_synthetic_module(
        "nodes",
        _PACKAGE_ROOT / "nodes" / "__init__.py",
        submodule_search_locations=[str(_PACKAGE_ROOT / "nodes")],
    )
    return (
        nodes_module.NODE_CLASS_MAPPINGS,
        nodes_module.NODE_DISPLAY_NAME_MAPPINGS,
    )


def _register_routes():
    """Register PromptServer routes when the Comfy host is available."""
    if __package__:
        from .settings import register_prompt_server_routes

        register_prompt_server_routes()
        return
    settings_module = _load_synthetic_module(
        "settings",
        _PACKAGE_ROOT / "settings" / "__init__.py",
        submodule_search_locations=[str(_PACKAGE_ROOT / "settings")],
    )
    settings_module.register_prompt_server_routes()


NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS = _load_node_mappings()

WEB_DIRECTORY = "web"

_register_routes()
