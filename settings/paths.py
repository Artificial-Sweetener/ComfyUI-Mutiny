"""Resolve filesystem paths used by the settings subsystem."""

from __future__ import annotations

import os
from pathlib import Path

_SETTINGS_PATH_ENV_VAR = "COMFYUI_MUTINY_SETTINGS_PATH"
_SETTINGS_FILE_NAME = "mutiny.settings.json"


def get_repo_root() -> Path:
    """Return the plugin repository root."""
    return Path(__file__).resolve().parents[1]


def get_settings_file_path() -> Path:
    """Return the JSON file path used for non-secret plugin settings."""
    override = os.environ.get(_SETTINGS_PATH_ENV_VAR)
    if override:
        return Path(override).expanduser()
    return get_repo_root() / _SETTINGS_FILE_NAME


__all__ = ["get_repo_root", "get_settings_file_path"]
