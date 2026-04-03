"""Persist plugin settings to a local JSON file."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .models import PluginSettings
from .paths import get_settings_file_path


class SettingsRepository:
    """Load and save non-secret plugin settings."""

    def __init__(self, settings_path: Path | None = None) -> None:
        """Store the JSON file location used by this repository."""
        self._settings_path = settings_path or get_settings_file_path()

    @property
    def settings_path(self) -> Path:
        """Return the JSON file path used by the repository."""
        return self._settings_path

    def load(self) -> PluginSettings:
        """Load settings from disk or return defaults when the file is absent."""
        if not self._settings_path.exists():
            return PluginSettings()

        try:
            with self._settings_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except json.JSONDecodeError as exc:
            raise RuntimeError("The Mutiny settings file is not valid JSON.") from exc
        except OSError as exc:
            raise RuntimeError("The Mutiny settings file could not be read.") from exc

        try:
            return PluginSettings.from_dict(payload)
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError("The Mutiny settings file is malformed.") from exc

    def save(self, settings: PluginSettings) -> PluginSettings:
        """Atomically persist a settings snapshot to disk."""
        self._settings_path.parent.mkdir(parents=True, exist_ok=True)
        payload = settings.as_dict()
        temp_path = self._settings_path.with_suffix(f"{self._settings_path.suffix}.tmp")

        try:
            with temp_path.open("w", encoding="utf-8", newline="\n") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
                handle.write("\n")
            os.replace(temp_path, self._settings_path)
        except OSError as exc:
            raise RuntimeError(
                "The Mutiny settings file could not be written."
            ) from exc
        finally:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)

        return settings


__all__ = ["SettingsRepository"]
