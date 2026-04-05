"""Test JSON-backed settings persistence."""

from __future__ import annotations

import json

import pytest

from support.plugin_loader import load_plugin_package

load_plugin_package()

from comfyui_mutiny_under_test.settings.models import PluginSettings
from comfyui_mutiny_under_test.settings.repository import SettingsRepository


def test_repository_returns_defaults_when_file_is_missing(tmp_path):
    """Load defaults when the non-secret settings file does not exist yet."""
    repository = SettingsRepository(tmp_path / "mutiny.settings.json")

    settings = repository.load()

    assert settings == PluginSettings()


def test_repository_round_trips_settings_snapshot(tmp_path):
    """Persist one settings snapshot and load it back unchanged."""
    settings_path = tmp_path / "mutiny.settings.json"
    repository = SettingsRepository(settings_path)
    original = PluginSettings().configure(
        discord={"guild_id": "guild-123", "channel_id": "channel-456"},
        engine={"execution": {"task_timeout_minutes": 9}},
    )

    repository.save(original)

    reloaded = repository.load()

    assert reloaded == original
    assert json.loads(settings_path.read_text(encoding="utf-8"))["discord"] == {
        "api_endpoint": original.discord.api_endpoint,
        "channel_id": "channel-456",
        "guild_id": "guild-123",
    }


def test_repository_raises_for_invalid_json(tmp_path):
    """Fail clearly when the persisted JSON file is malformed."""
    settings_path = tmp_path / "mutiny.settings.json"
    settings_path.write_text("{not-valid-json", encoding="utf-8")
    repository = SettingsRepository(settings_path)

    with pytest.raises(RuntimeError, match="not valid JSON"):
        repository.load()


def test_repository_ignores_removed_user_agent_from_existing_settings_file(tmp_path):
    """Load older settings files without preserving the removed user-agent override."""
    settings_path = tmp_path / "mutiny.settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "metadata": {
                    "schema_version": 1,
                    "migration_completed": True,
                    "migrated_from_legacy": False,
                },
                "discord": {
                    "guild_id": "guild-123",
                    "channel_id": "channel-456",
                    "user_agent": "legacy-agent",
                    "api_endpoint": "https://discord.com/api/v9",
                },
                "cache": {
                    "artifact_cache_ram_max_mb": 32,
                    "disk_cache_max_mb": 256,
                },
                "engine": {"execution": {"task_timeout_minutes": 5}},
            }
        ),
        encoding="utf-8",
    )
    repository = SettingsRepository(settings_path)

    loaded = repository.load()

    assert loaded.discord.guild_id == "guild-123"
    assert loaded.discord.channel_id == "channel-456"
    assert loaded.discord.api_endpoint == "https://discord.com/api/v9"
    assert not hasattr(loaded.discord, "user_agent")
