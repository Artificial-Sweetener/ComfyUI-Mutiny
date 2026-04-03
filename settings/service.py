"""Coordinate persisted settings, keyring tokens, and Mutiny config creation."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from mutiny import Config

from .migration import LegacySettingsMigrator
from .models import PluginSettings
from .repository import SettingsRepository
from .token_provider import KeyringTokenProvider
from .token_store import KeyringTokenStore

logger = logging.getLogger(__name__)

_DEFAULT_SETTINGS_SERVICE: "SettingsService | None" = None
_BYTES_PER_MEGABYTE = 1024 * 1024
_DEFAULT_DISK_CACHE_DIR = ".cache/mutiny"
_ARTIFACT_CACHE_NAMESPACE = "artifact_cache"


class SettingsValidationError(ValueError):
    """Raise when plugin settings are invalid for the requested operation."""


class SettingsService:
    """Own the plugin's non-secret settings and keyring-backed token access."""

    def __init__(
        self,
        repository: SettingsRepository,
        token_store: KeyringTokenStore,
        migrator: LegacySettingsMigrator | None = None,
        runtime_root: Path | None = None,
    ) -> None:
        """Store the collaborators used for settings access and migration."""
        self._repository = repository
        self._token_store = token_store
        self._migrator = migrator or LegacySettingsMigrator()
        self._runtime_root = runtime_root or Path(__file__).resolve().parents[1]

    def load_settings(self) -> PluginSettings:
        """Load settings and run one-time legacy migration when needed."""
        settings = self._repository.load()
        if settings.metadata.migration_completed:
            return settings

        migrated = self._migrator.migrate(settings, self._token_store)
        self._repository.save(migrated)
        return migrated

    def get_settings_status(self) -> dict[str, Any]:
        """Return the sanitized settings payload exposed to the UI."""
        settings = self.load_settings()
        return {
            "settings": settings.as_dict(),
            "token_configured": self._token_store.token_exists(),
        }

    def save_settings(self, payload: Mapping[str, Any]) -> PluginSettings:
        """Validate and persist non-secret settings from the UI."""
        if not isinstance(payload, Mapping):
            raise SettingsValidationError("Settings payload must be a JSON object.")

        if "token_configured" in payload:
            raise SettingsValidationError(
                "Token status is read-only and cannot be saved."
            )

        current = self.load_settings()
        normalized = self._normalize_update_payload(payload)
        updated = current.configure(**normalized)
        return self._repository.save(updated)

    def save_token(self, token: str) -> None:
        """Persist the Discord token in keyring."""
        self._token_store.save_token(token)

    def clear_token(self) -> None:
        """Remove the Discord token from keyring."""
        self._token_store.clear_token()

    def token_exists(self) -> bool:
        """Return whether a Discord token is configured."""
        return self._token_store.token_exists()

    def create_token_provider(self) -> KeyringTokenProvider:
        """Create the Mutiny-compatible token provider used by the runtime."""
        return KeyringTokenProvider(self._token_store)

    def build_mutiny_config(self) -> Config:
        """Build a Mutiny `Config` snapshot from plugin-owned settings."""
        settings = self.load_settings()
        self._validate_runtime_settings(settings)

        return Config.create(
            token_provider=self.create_token_provider(),
            guild_id=settings.discord.guild_id,
            channel_id=settings.discord.channel_id,
            user_agent=settings.discord.user_agent,
            api_endpoint=settings.discord.api_endpoint,
            cache=self._build_mutiny_cache_config(settings),
            execution={
                "task_timeout_minutes": settings.engine.execution.task_timeout_minutes,
            },
        )

    def get_cache_status(self) -> dict[str, int]:
        """Return logical disk-cache usage for artifact recognition data."""
        settings = self.load_settings()
        max_bytes = settings.cache.disk_cache_max_mb * _BYTES_PER_MEGABYTE
        used_bytes = 0
        db_path = self._resolve_disk_cache_db_path()
        if db_path.exists():
            try:
                used_bytes = self._read_artifact_cache_used_bytes(db_path)
            except sqlite3.DatabaseError:
                logger.exception(
                    "Failed to read Mutiny cache usage from %s.",
                    db_path,
                )
                raise RuntimeError(
                    "The Mutiny cache usage could not be read."
                ) from None
        percent_used = 0
        if max_bytes > 0:
            percent_used = min(100, round((used_bytes / max_bytes) * 100))
        return {
            "used_bytes": used_bytes,
            "max_bytes": max_bytes,
            "percent_used": percent_used,
        }

    def _build_mutiny_cache_config(self, settings: PluginSettings) -> dict[str, Any]:
        """Translate plugin cache settings into Mutiny's byte-based cache config."""
        return {
            "artifact_cache_ram_max_bytes": (
                settings.cache.artifact_cache_ram_max_mb * _BYTES_PER_MEGABYTE
            ),
            "disk_cache_enabled": True,
            "disk_cache_dir": str(self._resolve_disk_cache_root()),
            "disk_cache_max_bytes": (
                settings.cache.disk_cache_max_mb * _BYTES_PER_MEGABYTE
            ),
        }

    def _resolve_disk_cache_root(self) -> Path:
        """Return the stable cache directory used by this plugin installation."""

        cache_root = Path(_DEFAULT_DISK_CACHE_DIR)
        if cache_root.is_absolute():
            return cache_root
        return (self._runtime_root / cache_root).resolve()

    def _resolve_disk_cache_db_path(self) -> Path:
        """Return the SQLite file path used by Mutiny disk cache in this host."""
        return self._resolve_disk_cache_root() / "kv.sqlite"

    def _read_artifact_cache_used_bytes(self, db_path: Path) -> int:
        """Read the logical artifact-cache size from the SQLite store."""
        connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            cursor = connection.execute(
                "SELECT COALESCE(SUM(size_bytes), 0) FROM kv WHERE namespace = ?",
                (_ARTIFACT_CACHE_NAMESPACE,),
            )
            row = cursor.fetchone()
            return int(row[0] or 0) if row else 0
        finally:
            connection.close()

    def _normalize_update_payload(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Normalize nested JSON payloads into a settings update mapping."""
        normalized = {}
        for section_name, section_value in payload.items():
            if section_name == "settings":
                if not isinstance(section_value, Mapping):
                    raise SettingsValidationError(
                        "The settings payload must be an object."
                    )
                nested = self._normalize_update_payload(section_value)
                normalized.update(nested)
                continue

            if section_name == "metadata":
                raise SettingsValidationError(
                    "Settings metadata is managed internally."
                )

            normalized[section_name] = self._normalize_section(
                section_name, section_value
            )
        return normalized

    def _normalize_section(self, section_name: str, section_value: Any) -> Any:
        """Normalize one top-level settings section from a UI payload."""
        if section_name not in {"discord", "cache", "engine"}:
            raise SettingsValidationError(f"Unknown settings section: {section_name}")

        if not isinstance(section_value, Mapping):
            raise SettingsValidationError(
                f"The {section_name} section must be a JSON object."
            )

        if section_name == "discord":
            self._assert_known_keys(
                section_name,
                section_value,
                {"guild_id", "channel_id", "user_agent", "api_endpoint"},
            )
            normalized = {}
            if "guild_id" in section_value:
                normalized["guild_id"] = self._normalize_string(
                    section_value["guild_id"]
                )
            if "channel_id" in section_value:
                normalized["channel_id"] = self._normalize_string(
                    section_value["channel_id"]
                )
            if "user_agent" in section_value:
                normalized["user_agent"] = self._normalize_optional_string(
                    section_value["user_agent"],
                    default_value=PluginSettings().discord.user_agent,
                )
            if "api_endpoint" in section_value:
                normalized["api_endpoint"] = self._normalize_optional_string(
                    section_value["api_endpoint"],
                    default_value=PluginSettings().discord.api_endpoint,
                )
            return normalized

        if section_name == "cache":
            self._assert_known_keys(
                section_name,
                section_value,
                {"artifact_cache_ram_max_mb", "disk_cache_max_mb"},
            )
            normalized = {}
            if "artifact_cache_ram_max_mb" in section_value:
                normalized["artifact_cache_ram_max_mb"] = self._normalize_int(
                    section_value["artifact_cache_ram_max_mb"],
                    field_name="artifact_cache_ram_max_mb",
                    minimum=1,
                )
            if "disk_cache_max_mb" in section_value:
                normalized["disk_cache_max_mb"] = self._normalize_int(
                    section_value["disk_cache_max_mb"],
                    field_name="disk_cache_max_mb",
                    minimum=1,
                )
            return normalized

        self._assert_known_keys(section_name, section_value, {"execution"})
        if "execution" not in section_value:
            return {}
        execution_payload = section_value["execution"]
        if not isinstance(execution_payload, Mapping):
            raise SettingsValidationError(
                "The engine.execution section must be an object."
            )
        self._assert_known_keys(
            "engine.execution",
            execution_payload,
            {"task_timeout_minutes"},
        )
        execution = {}
        if "task_timeout_minutes" in execution_payload:
            execution["task_timeout_minutes"] = self._normalize_int(
                execution_payload["task_timeout_minutes"],
                field_name="task_timeout_minutes",
                minimum=1,
            )
        return {"execution": execution}

    def _assert_known_keys(
        self,
        label: str,
        payload: Mapping[str, Any],
        allowed_keys: set[str],
    ) -> None:
        """Raise when a payload contains unknown keys."""
        unknown_keys = set(payload) - allowed_keys
        if unknown_keys:
            joined = ", ".join(sorted(unknown_keys))
            raise SettingsValidationError(f"Unknown {label} keys: {joined}")

    def _normalize_string(self, value: Any) -> str:
        """Normalize a string field while preserving blank values."""
        if value is None:
            return ""
        if not isinstance(value, str):
            raise SettingsValidationError("Expected a string value.")
        return value.strip()

    def _normalize_optional_string(self, value: Any, *, default_value: str) -> str:
        """Normalize an optional string field and restore defaults when blank."""
        normalized = self._normalize_string(value)
        return normalized or default_value

    def _normalize_int(self, value: Any, *, field_name: str, minimum: int) -> int:
        """Normalize an integer field from a JSON payload."""
        if not isinstance(value, int):
            raise SettingsValidationError(f"{field_name} must be an integer.")
        if value < minimum:
            raise SettingsValidationError(
                f"{field_name} must be greater than or equal to {minimum}."
            )
        return value

    def _validate_runtime_settings(self, settings: PluginSettings) -> None:
        """Raise when required runtime settings are missing."""
        if not settings.discord.guild_id:
            raise SettingsValidationError(
                "Mutiny needs your Discord guild ID before it can run. "
                "Add it in ComfyUI Settings under Mutiny, and see the settings panel "
                "for instructions."
            )
        if not settings.discord.channel_id:
            raise SettingsValidationError(
                "Mutiny needs your Discord channel ID before it can run. "
                "Add it in ComfyUI Settings under Mutiny, and see the settings panel "
                "for instructions."
            )


def build_default_settings_service() -> SettingsService:
    """Construct the default settings service used by the plugin entrypoint."""
    return SettingsService(
        repository=SettingsRepository(),
        token_store=KeyringTokenStore(),
        migrator=LegacySettingsMigrator(),
    )


def get_settings_service() -> SettingsService:
    """Return the process-wide default settings service."""
    global _DEFAULT_SETTINGS_SERVICE
    if _DEFAULT_SETTINGS_SERVICE is None:
        _DEFAULT_SETTINGS_SERVICE = build_default_settings_service()
    return _DEFAULT_SETTINGS_SERVICE


def reset_settings_service() -> None:
    """Clear the process-wide default settings service."""
    global _DEFAULT_SETTINGS_SERVICE
    _DEFAULT_SETTINGS_SERVICE = None


__all__ = [
    "SettingsService",
    "SettingsValidationError",
    "build_default_settings_service",
    "get_settings_service",
    "reset_settings_service",
]
