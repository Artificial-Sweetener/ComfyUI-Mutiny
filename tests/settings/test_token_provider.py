"""Test keyring-backed token storage and provider behavior."""

from __future__ import annotations

import keyring
import pytest
from keyring.errors import KeyringError

from support.plugin_loader import load_plugin_package

load_plugin_package()

from comfyui_mutiny_under_test.settings.token_provider import (
    KeyringTokenProvider,
    MissingDiscordTokenError,
)
from comfyui_mutiny_under_test.settings.token_store import KeyringTokenStore


def install_fake_keyring(monkeypatch):
    """Install an in-memory keyring backend for deterministic tests."""
    storage = {}

    def get_password(service_name, username):
        """Return one stored token value from the in-memory keyring."""
        return storage.get((service_name, username))

    def set_password(service_name, username, password):
        """Persist one token value into the in-memory keyring."""
        storage[(service_name, username)] = password

    def delete_password(service_name, username):
        """Remove one token value from the in-memory keyring when present."""
        storage.pop((service_name, username), None)

    monkeypatch.setattr(keyring, "get_password", get_password)
    monkeypatch.setattr(keyring, "set_password", set_password)
    monkeypatch.setattr(keyring, "delete_password", delete_password)
    return storage


def test_token_store_round_trips_tokens(monkeypatch):
    """Save, load, clear, and probe token presence through keyring."""
    install_fake_keyring(monkeypatch)
    token_store = KeyringTokenStore()

    token_store.save_token("  discord-token  ")

    assert token_store.load_token() == "discord-token"
    assert token_store.token_exists() is True

    token_store.clear_token()

    assert token_store.load_token() is None
    assert token_store.token_exists() is False


def test_token_store_rejects_empty_tokens(monkeypatch):
    """Reject blank token writes before they reach keyring."""
    install_fake_keyring(monkeypatch)
    token_store = KeyringTokenStore()

    with pytest.raises(ValueError, match="cannot be empty"):
        token_store.save_token("   ")


def test_token_provider_raises_when_token_is_missing(monkeypatch):
    """Expose a clear runtime error when no token has been configured."""
    install_fake_keyring(monkeypatch)
    provider = KeyringTokenProvider(KeyringTokenStore())

    with pytest.raises(MissingDiscordTokenError, match="Discord token"):
        provider.get_token()


def test_token_store_wraps_keyring_errors(monkeypatch):
    """Translate backend keyring failures into plugin-safe runtime errors."""

    def raise_keyring_error(_service_name, _username):
        """Raise a deterministic backend failure for the in-memory keyring."""
        raise KeyringError("backend failure")

    monkeypatch.setattr(keyring, "get_password", raise_keyring_error)
    token_store = KeyringTokenStore()

    with pytest.raises(RuntimeError, match="could not be read"):
        token_store.load_token()
