"""Test the Comfy route handlers used by the settings frontend."""

from __future__ import annotations

import asyncio
import json
import sqlite3

from aiohttp import web

from support.plugin_loader import load_plugin_package

load_plugin_package()

from comfyui_mutiny_under_test.settings.migration import LegacySettingsMigrator
from comfyui_mutiny_under_test.settings.repository import SettingsRepository
from comfyui_mutiny_under_test.settings.routes import register_settings_routes
from comfyui_mutiny_under_test.settings.service import SettingsService
from tests.support.fakes import FakeTokenStore


class FakeRequest:
    """Provide the minimal request surface needed by the route handlers."""

    def __init__(self, payload=None, *, json_exc: Exception | None = None):
        """Store the JSON payload or parsing failure returned by `json()`."""
        self._payload = payload
        self._json_exc = json_exc

    async def json(self):
        """Return the configured JSON payload."""
        if self._json_exc is not None:
            raise self._json_exc
        return self._payload


def build_service_and_handlers(tmp_path, *, token=None):
    """Construct isolated settings routes and return them by method/path."""
    service = SettingsService(
        SettingsRepository(tmp_path / "mutiny.settings.json"),
        FakeTokenStore(token=token),
        LegacySettingsMigrator(repo_root=tmp_path),
        runtime_root=tmp_path,
    )
    routes = web.RouteTableDef()
    register_settings_routes(routes, service)
    handlers = {(route.method, route.path): route.handler for route in routes}
    return service, handlers


def decode_json_response(response):
    """Decode one JSON response body for assertions."""
    return json.loads(response.text)


def test_get_settings_route_returns_status_payload(tmp_path):
    """Return sanitized settings plus token presence state."""
    _service, handlers = build_service_and_handlers(tmp_path)

    response = asyncio.run(handlers[("GET", "/mutiny/settings")](FakeRequest()))
    payload = decode_json_response(response)

    assert response.status == 200
    assert payload["token_configured"] is False
    assert payload["settings"]["metadata"]["migration_completed"] is True


def test_get_cache_status_route_returns_logical_artifact_cache_usage(tmp_path):
    """Report the logical usage of the artifact cache namespace."""
    _service, handlers = build_service_and_handlers(tmp_path)
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
        connection.execute(
            """
            INSERT INTO kv(namespace, key, value, created_ts, last_access_ts, size_bytes)
            VALUES (?, ?, ?, 0, 0, ?)
            """,
            ("artifact_cache", "digest-1", "{}", 4096),
        )
        connection.execute(
            """
            INSERT INTO kv(namespace, key, value, created_ts, last_access_ts, size_bytes)
            VALUES (?, ?, ?, 0, 0, ?)
            """,
            ("image_cache", "legacy-1", "{}", 8192),
        )
        connection.commit()
    finally:
        connection.close()

    response = asyncio.run(handlers[("GET", "/mutiny/cache/status")](FakeRequest()))
    payload = decode_json_response(response)

    assert response.status == 200
    assert payload["used_bytes"] == 4096
    assert payload["max_bytes"] == 256 * 1024 * 1024
    assert payload["percent_used"] == 0


def test_save_settings_route_persists_non_secret_values(tmp_path):
    """Save non-secret settings through the HTTP boundary."""
    service, handlers = build_service_and_handlers(tmp_path)

    response = asyncio.run(
        handlers[("POST", "/mutiny/settings")](
            FakeRequest(
                {
                    "discord": {"guild_id": "guild-1", "channel_id": "channel-1"},
                    "cache": {
                        "artifact_cache_ram_max_mb": 48,
                        "disk_cache_max_mb": 128,
                    },
                    "engine": {"execution": {"task_timeout_minutes": 7}},
                }
            )
        )
    )
    payload = decode_json_response(response)

    assert response.status == 200
    assert payload["settings"]["discord"]["guild_id"] == "guild-1"
    assert payload["settings"]["cache"]["artifact_cache_ram_max_mb"] == 48
    assert payload["settings"]["cache"]["disk_cache_max_mb"] == 128
    assert "api" not in payload["settings"]
    assert "images" not in payload["settings"]
    assert "features" not in payload["settings"]
    assert service.load_settings().engine.execution.task_timeout_minutes == 7


def test_token_routes_save_and_clear_secure_tokens(tmp_path):
    """Store and remove the token without ever returning the token value."""
    _service, handlers = build_service_and_handlers(tmp_path)

    save_response = asyncio.run(
        handlers[("POST", "/mutiny/token")](FakeRequest({"token": "discord-token"}))
    )
    clear_response = asyncio.run(handlers[("DELETE", "/mutiny/token")](FakeRequest()))

    assert decode_json_response(save_response) == {"token_configured": True}
    assert decode_json_response(clear_response) == {"token_configured": False}


def test_save_settings_route_rejects_malformed_json(tmp_path):
    """Return a safe 400 when the settings payload is not valid JSON."""
    _service, handlers = build_service_and_handlers(tmp_path)

    response = asyncio.run(
        handlers[("POST", "/mutiny/settings")](
            FakeRequest(json_exc=ValueError("invalid json"))
        )
    )
    payload = decode_json_response(response)

    assert response.status == 400
    assert payload["error"] == "Request body must be valid JSON."


def test_settings_routes_do_not_register_test_configuration_action(tmp_path):
    """Do not expose the removed test-configuration route in the settings API."""
    _service, handlers = build_service_and_handlers(tmp_path)

    assert ("POST", "/mutiny/settings/test") not in handlers


def test_save_settings_route_rejects_feature_payloads(tmp_path):
    """Return a safe 400 when the client tries to save removed feature flags."""
    _service, handlers = build_service_and_handlers(tmp_path)

    response = asyncio.run(
        handlers[("POST", "/mutiny/settings")](
            FakeRequest({"features": {"custom_zoom": False}})
        )
    )
    payload = decode_json_response(response)

    assert response.status == 400
    assert "Unknown settings section" in payload["error"]


def test_save_settings_route_rejects_removed_api_and_image_payloads(tmp_path):
    """Return a safe 400 when the client tries to save removed runtime internals."""
    _service, handlers = build_service_and_handlers(tmp_path)

    api_response = asyncio.run(
        handlers[("POST", "/mutiny/settings")](
            FakeRequest({"api": {"secret": "ignored"}})
        )
    )
    image_response = asyncio.run(
        handlers[("POST", "/mutiny/settings")](
            FakeRequest({"images": {"backend": "opencv"}})
        )
    )

    assert api_response.status == 400
    assert image_response.status == 400
    assert "Unknown settings section" in decode_json_response(api_response)["error"]
    assert "Unknown settings section" in decode_json_response(image_response)["error"]
