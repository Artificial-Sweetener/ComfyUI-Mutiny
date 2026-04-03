"""Import stale pre-Mutiny YAML settings into the secure settings stores once."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import yaml

from .models import PluginSettings, SettingsMetadata
from .paths import get_repo_root
from .token_store import KeyringTokenStore

logger = logging.getLogger(__name__)

_LEGACY_ACCOUNT_FILES = (
    "proxy/application.yml",
    "application.yml",
    "discord_credentials.yml",
)
_LEGACY_PROXY_URL_FILE_NAME = "setting.yaml"


@dataclass(frozen=True)
class LegacyAccountSnapshot:
    """Store one legacy account snapshot extracted from YAML."""

    guild_id: str = ""
    channel_id: str = ""
    token: str = ""


class LegacySettingsMigrator:
    """Read stale upgrade-era YAML files only long enough to populate new stores."""

    def __init__(self, repo_root: Path | None = None) -> None:
        """Store the repository root used to resolve legacy YAML paths."""
        self._repo_root = repo_root or get_repo_root()

    def migrate(
        self,
        settings: PluginSettings,
        token_store: KeyringTokenStore,
    ) -> PluginSettings:
        """Return a migrated settings snapshot and persist any legacy token once."""
        if settings.metadata.migration_completed:
            return settings

        legacy_snapshot = self._load_first_legacy_account()
        migrated = settings
        migrated_from_legacy = False

        if (
            legacy_snapshot
            and legacy_snapshot.guild_id
            and not settings.discord.guild_id
        ):
            migrated = migrated.configure(
                discord={"guild_id": legacy_snapshot.guild_id},
            )
            migrated_from_legacy = True

        if (
            legacy_snapshot
            and legacy_snapshot.channel_id
            and not settings.discord.channel_id
        ):
            migrated = migrated.configure(
                discord={"channel_id": legacy_snapshot.channel_id},
            )
            migrated_from_legacy = True

        if legacy_snapshot and legacy_snapshot.token and not token_store.token_exists():
            token_store.save_token(legacy_snapshot.token)
            migrated_from_legacy = True

        metadata = SettingsMetadata(
            schema_version=migrated.metadata.schema_version,
            migration_completed=True,
            migrated_from_legacy=migrated_from_legacy,
        )
        return migrated.configure(metadata=metadata)

    def _load_first_legacy_account(self) -> LegacyAccountSnapshot | None:
        """Return the first legacy account record found in precedence order."""
        for relative_path in _LEGACY_ACCOUNT_FILES:
            path = self._repo_root / relative_path
            snapshot = self._load_account_snapshot(path)
            if snapshot is not None:
                return snapshot

        proxy_url_path = self._repo_root / _LEGACY_PROXY_URL_FILE_NAME
        if proxy_url_path.exists():
            logger.info(
                "Ignoring legacy proxy URL upgrade file during settings migration: %s",
                proxy_url_path.name,
            )

        return None

    def _load_account_snapshot(self, path: Path) -> LegacyAccountSnapshot | None:
        """Return the first account snapshot from one legacy YAML file."""
        if not path.exists():
            return None

        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = yaml.safe_load(handle) or {}
        except (OSError, yaml.YAMLError):
            logger.warning("Skipping unreadable legacy settings file: %s", path.name)
            return None

        account_payloads = (
            payload.get("mj", {}).get("accounts", [])
            if isinstance(payload, dict)
            else []
        )
        if not account_payloads:
            return None

        account = account_payloads[0] or {}
        return LegacyAccountSnapshot(
            guild_id=str(account.get("guildId", "")).strip(),
            channel_id=str(account.get("channelId", "")).strip(),
            token=str(account.get("userToken", "")).strip(),
        )


__all__ = ["LegacyAccountSnapshot", "LegacySettingsMigrator"]
