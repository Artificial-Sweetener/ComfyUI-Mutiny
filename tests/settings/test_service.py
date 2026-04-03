"""Test the settings service that bridges storage and Mutiny config creation."""

from __future__ import annotations

import sqlite3

import pytest

from support.plugin_loader import load_plugin_package

load_plugin_package()

from comfyui_mutiny_under_test.settings.migration import LegacySettingsMigrator
from comfyui_mutiny_under_test.settings.repository import SettingsRepository
from comfyui_mutiny_under_test.settings.service import (
    SettingsService,
    SettingsValidationError,
)
from tests.support.fakes import FakeTokenStore


def build_service(tmp_path, *, token=None, repo_root=None):
    """Construct a settings service with isolated storage and token state."""
    repository = SettingsRepository(tmp_path / "mutiny.settings.json")
    token_store = FakeTokenStore(token=token)
    migrator = LegacySettingsMigrator(repo_root=repo_root or tmp_path)
    return (
        SettingsService(
            repository,
            token_store,
            migrator,
            runtime_root=repo_root or tmp_path,
        ),
        token_store,
    )


def test_service_saves_partial_non_secret_updates(tmp_path):
    """Persist partial updates without requiring every section every time."""
    service, _token_store = build_service(tmp_path)

    saved = service.save_settings(
        {
            "discord": {"guild_id": "guild-1", "channel_id": "channel-1"},
            "engine": {"execution": {"task_timeout_minutes": 11}},
        }
    )

    reloaded = service.load_settings()

    assert saved.discord.guild_id == "guild-1"
    assert saved.discord.channel_id == "channel-1"
    assert reloaded.engine.execution.task_timeout_minutes == 11


def test_service_preserves_existing_values_during_single_field_partial_save(tmp_path):
    """Preserve unrelated settings when the UI saves only one row's payload."""
    service, _token_store = build_service(tmp_path)
    service.save_settings(
        {
            "discord": {"guild_id": "guild-1", "channel_id": "channel-1"},
            "engine": {"execution": {"task_timeout_minutes": 9}},
        }
    )

    updated = service.save_settings({"discord": {"guild_id": "guild-2"}})
    reloaded = service.load_settings()

    assert updated.discord.guild_id == "guild-2"
    assert reloaded.discord.channel_id == "channel-1"
    assert reloaded.engine.execution.task_timeout_minutes == 9


def test_service_builds_mutiny_config_from_secure_settings(tmp_path):
    """Create a Mutiny config snapshot with plugin-owned runtime settings."""
    service, token_store = build_service(tmp_path, token="discord-token")
    service.save_settings(
        {
            "discord": {"guild_id": "guild-1", "channel_id": "channel-1"},
            "cache": {
                "artifact_cache_ram_max_mb": 64,
                "disk_cache_max_mb": 256,
            },
            "engine": {"execution": {"task_timeout_minutes": 7}},
        }
    )

    config = service.build_mutiny_config()

    assert config.discord.guild_id == "guild-1"
    assert config.discord.channel_id == "channel-1"
    assert not hasattr(config, "features")
    assert config.websocket.capture_enabled is False
    assert config.cache.artifact_cache_ram_max_bytes == 64 * 1024 * 1024
    assert config.cache.disk_cache_enabled is True
    assert config.cache.disk_cache_max_bytes == 256 * 1024 * 1024
    assert config.engine.execution.task_timeout_minutes == 7
    assert config.token_provider.get_token() == token_store.token


def test_service_uses_default_cache_budgets_when_ui_never_saved_cache_settings(
    tmp_path,
):
    """Preserve Mutiny's current cache defaults when plugin cache settings are absent."""
    service, _token_store = build_service(tmp_path, token="discord-token")
    service.save_settings(
        {"discord": {"guild_id": "guild-1", "channel_id": "channel-1"}}
    )

    config = service.build_mutiny_config()

    assert config.cache.artifact_cache_ram_max_bytes == 32 * 1024 * 1024
    assert config.cache.disk_cache_max_bytes == 256 * 1024 * 1024


def test_service_reports_zero_cache_usage_when_disk_cache_file_is_absent(tmp_path):
    """Treat an empty host cache directory as zero logical usage."""
    service, _token_store = build_service(tmp_path)

    status = service.get_cache_status()

    assert status["used_bytes"] == 0
    assert status["max_bytes"] == 256 * 1024 * 1024
    assert status["percent_used"] == 0


def test_service_reads_logical_artifact_cache_usage_from_sqlite(tmp_path):
    """Read artifact-cache usage from the unified Mutiny SQLite store."""
    service, _token_store = build_service(tmp_path)
    cache_root = tmp_path / ".cache" / "mutiny"
    cache_root.mkdir(parents=True)
    connection = sqlite3.connect(cache_root / "kv.sqlite")
    try:
        connection.execute(
            """
            CREATE TABLE kv (
                namespace TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                created_ts REAL NOT NULL,
                last_access_ts REAL NOT NULL,
                size_bytes INTEGER NOT NULL,
                PRIMARY KEY(namespace, key)
            )
            """
        )
        connection.executemany(
            """
            INSERT INTO kv(namespace, key, value, created_ts, last_access_ts, size_bytes)
            VALUES (?, ?, ?, 0, 0, ?)
            """,
            [
                ("artifact_cache", "digest-1", "{}", 1024),
                ("artifact_cache", "digest-2", "{}", 2048),
                ("job_index", "legacy-1", "{}", 4096),
            ],
        )
        connection.commit()
    finally:
        connection.close()

    status = service.get_cache_status()

    assert status["used_bytes"] == 3072
    assert status["max_bytes"] == 256 * 1024 * 1024
    assert status["percent_used"] == 0


def test_service_requires_runtime_identifiers_before_config_build(tmp_path):
    """Reject runtime config creation when required Discord IDs are missing."""
    service, _token_store = build_service(tmp_path, token="discord-token")

    with pytest.raises(SettingsValidationError, match="Discord guild ID"):
        service.build_mutiny_config()


def test_service_rejects_feature_section_updates(tmp_path):
    """Reject feature payloads because those capabilities are always enabled."""
    service, _token_store = build_service(tmp_path)

    with pytest.raises(SettingsValidationError, match="Unknown settings section"):
        service.save_settings({"features": {"custom_zoom": False}})


def test_service_rejects_removed_api_and_image_sections(tmp_path):
    """Reject removed UI sections that are now fixed integration behavior."""
    service, _token_store = build_service(tmp_path)

    with pytest.raises(SettingsValidationError, match="Unknown settings section"):
        service.save_settings({"api": {"secret": "ignored"}})

    with pytest.raises(SettingsValidationError, match="Unknown settings section"):
        service.save_settings({"images": {"backend": "opencv"}})


def test_service_rejects_invalid_cache_payloads(tmp_path):
    """Fail clearly when cache settings are malformed or non-positive."""
    service, _token_store = build_service(tmp_path)

    with pytest.raises(SettingsValidationError, match="must be an integer"):
        service.save_settings({"cache": {"artifact_cache_ram_max_mb": "32"}})

    with pytest.raises(
        SettingsValidationError,
        match="disk_cache_max_mb must be greater than or equal to 1",
    ):
        service.save_settings({"cache": {"disk_cache_max_mb": 0}})


def test_service_reports_unknown_settings_sections(tmp_path):
    """Fail clearly when the UI payload contains unknown sections."""
    service, _token_store = build_service(tmp_path)

    with pytest.raises(SettingsValidationError, match="Unknown settings section"):
        service.save_settings({"unknown": {}})


def test_service_persists_migration_completion_when_no_legacy_files_exist(tmp_path):
    """Mark migration complete even when there is nothing to import."""
    service, _token_store = build_service(tmp_path)

    loaded = service.load_settings()

    assert loaded.metadata.migration_completed is True
    assert service.load_settings() == loaded
