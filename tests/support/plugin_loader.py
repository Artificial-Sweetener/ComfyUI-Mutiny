"""Load the plugin package under test with lightweight ComfyUI stubs."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_INIT_PATH = REPO_ROOT / "__init__.py"


class RecordingProgressBar:
    """Capture progress updates emitted through the ComfyUI progress boundary."""

    instances: list["RecordingProgressBar"] = []

    def __init__(self, total: int):
        """Store the requested total and record this instance globally."""
        self.total = total
        self.calls: list[tuple[int, int, tuple[str, object, int] | None]] = []
        self.__class__.instances.append(self)

    def update_absolute(
        self,
        value: int,
        total: int,
        preview: tuple[str, object, int] | None = None,
    ) -> None:
        """Record each progress update for later assertions."""
        self.calls.append((value, total, preview))

    @classmethod
    def reset(cls) -> None:
        """Clear recorded instances between tests."""
        cls.instances = []


def install_comfy_stubs(
    progress_bar_class: type[RecordingProgressBar] | None = None,
) -> None:
    """Install minimal Comfy and Comfy API stubs needed by plugin imports."""
    progress_bar = progress_bar_class or RecordingProgressBar
    comfy_module = types.ModuleType("comfy")
    comfy_utils_module = types.ModuleType("comfy.utils")
    comfy_utils_module.ProgressBar = progress_bar
    comfy_module.utils = comfy_utils_module
    comfy_api_module = sys.modules.get("comfy_api") or types.ModuleType("comfy_api")
    comfy_api_latest_module = sys.modules.get("comfy_api.latest") or types.ModuleType(
        "comfy_api.latest"
    )

    existing_input_impl = getattr(comfy_api_latest_module, "InputImpl", None)
    if existing_input_impl is not None and hasattr(
        existing_input_impl, "VideoFromFile"
    ):
        video_from_file = existing_input_impl.VideoFromFile
    else:

        class VideoFromFile:
            """Store one file-backed video stream source for test-only Comfy stubs."""

            def __init__(self, file):
                """Store the provided stream source for later retrieval."""
                self._file = file

            def get_stream_source(self):
                """Return the stored stream source unchanged."""
                return self._file

        video_from_file = VideoFromFile

    comfy_api_latest_module.InputImpl = types.SimpleNamespace(
        VideoFromFile=video_from_file
    )

    sys.modules["comfy"] = comfy_module
    sys.modules["comfy.utils"] = comfy_utils_module
    sys.modules["comfy_api"] = comfy_api_module
    sys.modules["comfy_api.latest"] = comfy_api_latest_module


def unload_package(package_name: str) -> None:
    """Remove a previously loaded plugin package alias from `sys.modules`."""
    for module_name in list(sys.modules):
        if module_name == package_name or module_name.startswith(f"{package_name}."):
            del sys.modules[module_name]


def load_plugin_package(
    package_name: str = "comfyui_mutiny_under_test",
    progress_bar_class: type[RecordingProgressBar] | None = None,
) -> ModuleType:
    """Load the repo as a fresh package alias for isolated tests."""
    install_comfy_stubs(progress_bar_class=progress_bar_class)
    unload_package(package_name)

    spec = importlib.util.spec_from_file_location(
        package_name,
        PLUGIN_INIT_PATH,
        submodule_search_locations=[str(REPO_ROOT)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to create an import spec for the plugin package.")

    module = importlib.util.module_from_spec(spec)
    sys.modules[package_name] = module
    spec.loader.exec_module(module)
    return module
