"""Test one-time migration from legacy YAML files."""

from __future__ import annotations

from pathlib import Path

from support.plugin_loader import load_plugin_package

load_plugin_package()

from comfyui_mutiny_under_test.settings.migration import LegacySettingsMigrator
from comfyui_mutiny_under_test.settings.models import PluginSettings
from tests.support.fakes import FakeTokenStore


def write_legacy_config(
    path: Path, *, guild_id: str, channel_id: str, token: str
) -> None:
    """Write one legacy YAML file without exposing any real credentials."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "mj:",
                "  accounts:",
                f'    - userToken: "{token}"',
                f'      guildId: "{guild_id}"',
                f'      channelId: "{channel_id}"',
            ]
        ),
        encoding="utf-8",
    )


def test_migration_prefers_proxy_application_yaml(tmp_path):
    """Prefer the most recent upgrade-era application YAML when both exist."""
    write_legacy_config(
        tmp_path / "application.yml",
        guild_id="root-guild",
        channel_id="root-channel",
        token="root-token",
    )
    write_legacy_config(
        tmp_path / "proxy" / "application.yml",
        guild_id="proxy-guild",
        channel_id="proxy-channel",
        token="proxy-token",
    )

    migrator = LegacySettingsMigrator(repo_root=tmp_path)
    token_store = FakeTokenStore()

    migrated = migrator.migrate(PluginSettings(), token_store)

    assert migrated.discord.guild_id == "proxy-guild"
    assert migrated.discord.channel_id == "proxy-channel"
    assert token_store.token == "proxy-token"
    assert migrated.metadata.migration_completed is True
    assert migrated.metadata.migrated_from_legacy is True


def test_migration_preserves_existing_settings_and_token(tmp_path):
    """Do not overwrite values that the secure settings system already owns."""
    write_legacy_config(
        tmp_path / "proxy" / "application.yml",
        guild_id="legacy-guild",
        channel_id="legacy-channel",
        token="legacy-token",
    )

    current = PluginSettings().configure(
        discord={"guild_id": "current-guild", "channel_id": "current-channel"}
    )
    token_store = FakeTokenStore(token="current-token")
    migrator = LegacySettingsMigrator(repo_root=tmp_path)

    migrated = migrator.migrate(current, token_store)

    assert migrated.discord.guild_id == "current-guild"
    assert migrated.discord.channel_id == "current-channel"
    assert token_store.token == "current-token"
    assert migrated.metadata.migration_completed is True


def test_migration_ignores_legacy_proxy_url_only_file(tmp_path):
    """Ignore `setting.yaml` because it belonged to the removed proxy transport."""
    (tmp_path / "setting.yaml").write_text(
        "\n".join(
            [
                "API_URL:",
                '  api_url: "http://127.0.0.1:8080"',
            ]
        ),
        encoding="utf-8",
    )

    migrator = LegacySettingsMigrator(repo_root=tmp_path)
    token_store = FakeTokenStore()

    migrated = migrator.migrate(PluginSettings(), token_store)

    assert migrated.discord.guild_id == ""
    assert migrated.discord.channel_id == ""
    assert token_store.token is None
    assert migrated.metadata.migration_completed is True
    assert migrated.metadata.migrated_from_legacy is False
