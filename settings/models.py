"""Define the plugin-owned non-secret settings model."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields, is_dataclass, replace
from typing import Any, Mapping, MutableMapping

_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) Gecko/20100101 Firefox/141.0"
)
_DEFAULT_API_ENDPOINT = "https://discord.com/api/v9"


@dataclass(frozen=True)
class SettingsMetadata:
    """Track schema and legacy-migration state for persisted settings."""

    schema_version: int = 1
    migration_completed: bool = False
    migrated_from_legacy: bool = False


@dataclass(frozen=True)
class DiscordSettings:
    """Store Discord identifiers and optional transport metadata."""

    guild_id: str = ""
    channel_id: str = ""
    user_agent: str = _DEFAULT_USER_AGENT
    api_endpoint: str = _DEFAULT_API_ENDPOINT


@dataclass(frozen=True)
class ExecutionSettings:
    """Store execution settings needed before the runtime layer lands."""

    task_timeout_minutes: int = 5


@dataclass(frozen=True)
class CacheSettings:
    """Store host-facing Mutiny artifact cache budgets in megabytes."""

    artifact_cache_ram_max_mb: int = 32
    disk_cache_max_mb: int = 256


@dataclass(frozen=True)
class EngineSettings:
    """Store engine execution settings forwarded into Mutiny."""

    execution: ExecutionSettings = field(default_factory=ExecutionSettings)


@dataclass(frozen=True)
class PluginSettings:
    """Store the plugin's non-secret settings snapshot."""

    metadata: SettingsMetadata = field(default_factory=SettingsMetadata)
    discord: DiscordSettings = field(default_factory=DiscordSettings)
    cache: CacheSettings = field(default_factory=CacheSettings)
    engine: EngineSettings = field(default_factory=EngineSettings)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> "PluginSettings":
        """Build a validated settings snapshot from persisted JSON data."""
        payload = data or {}
        return cls(
            metadata=_coerce_section(
                SettingsMetadata, payload.get("metadata"), "metadata"
            ),
            discord=_coerce_section(DiscordSettings, payload.get("discord"), "discord"),
            cache=_coerce_section(CacheSettings, payload.get("cache"), "cache"),
            engine=_coerce_section(EngineSettings, payload.get("engine"), "engine"),
        )

    def as_dict(self) -> dict[str, Any]:
        """Return a stable nested dict for JSON serialization."""
        return asdict(self)

    def configure(self, **updates: Any) -> "PluginSettings":
        """Return a new snapshot with validated updates applied."""
        if not updates:
            return self
        applied = {}
        for key, value in updates.items():
            if not hasattr(self, key):
                raise KeyError(f"Unknown settings section: {key}")
            current = getattr(self, key)
            applied[key] = _merge_dataclass(current, value, key)
        return replace(self, **applied)


def _coerce_section(section_cls, value: Any, label: str):
    """Coerce a persisted section into its dataclass representation."""
    if value is None:
        return section_cls()
    if isinstance(value, section_cls):
        return value
    if isinstance(value, MutableMapping):
        return _merge_dataclass(section_cls(), value, label)
    if isinstance(value, Mapping):
        return _merge_dataclass(section_cls(), dict(value), label)
    raise TypeError(f"{label} must be a mapping or {section_cls.__name__}")


def _merge_dataclass(current: Any, value: Any, label: str):
    """Merge a mapping onto a dataclass instance with unknown-key checks."""
    if isinstance(value, Mapping):
        valid_field_names = {field_def.name for field_def in fields(current)}
        unknown = set(value) - valid_field_names
        if unknown:
            unknown_keys = ", ".join(sorted(unknown))
            raise KeyError(f"Unknown {label} keys: {unknown_keys}")

        updates = {}
        for key, item in value.items():
            field_value = getattr(current, key)
            if is_dataclass(field_value) and isinstance(item, Mapping):
                updates[key] = _merge_dataclass(field_value, item, f"{label}.{key}")
            else:
                updates[key] = item
        return replace(current, **updates)

    if isinstance(value, current.__class__):
        return value

    raise TypeError(f"{label} must be a mapping or {current.__class__.__name__}")


__all__ = [
    "CacheSettings",
    "DiscordSettings",
    "EngineSettings",
    "ExecutionSettings",
    "PluginSettings",
    "SettingsMetadata",
]
