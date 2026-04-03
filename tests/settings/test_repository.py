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
        "user_agent": original.discord.user_agent,
    }


def test_repository_raises_for_invalid_json(tmp_path):
    """Fail clearly when the persisted JSON file is malformed."""
    settings_path = tmp_path / "mutiny.settings.json"
    settings_path.write_text("{not-valid-json", encoding="utf-8")
    repository = SettingsRepository(settings_path)

    with pytest.raises(RuntimeError, match="not valid JSON"):
        repository.load()
