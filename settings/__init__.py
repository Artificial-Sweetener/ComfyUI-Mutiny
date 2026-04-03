"""Expose the plugin settings subsystem."""

from .migration import LegacySettingsMigrator
from .models import PluginSettings
from .paths import get_settings_file_path
from .repository import SettingsRepository
from .routes import register_prompt_server_routes, register_settings_routes
from .service import (
    SettingsService,
    SettingsValidationError,
    build_default_settings_service,
    get_settings_service,
    reset_settings_service,
)
from .token_provider import KeyringTokenProvider, MissingDiscordTokenError
from .token_store import KeyringTokenStore

__all__ = [
    "KeyringTokenProvider",
    "KeyringTokenStore",
    "LegacySettingsMigrator",
    "MissingDiscordTokenError",
    "PluginSettings",
    "SettingsRepository",
    "SettingsService",
    "SettingsValidationError",
    "build_default_settings_service",
    "get_settings_file_path",
    "get_settings_service",
    "register_prompt_server_routes",
    "register_settings_routes",
    "reset_settings_service",
]
