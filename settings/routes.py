"""Register ComfyUI HTTP routes for secure settings management."""

from __future__ import annotations

import logging

from aiohttp import web

from .service import SettingsService, SettingsValidationError, get_settings_service

logger = logging.getLogger(__name__)

_ROUTES_REGISTERED = False


def _reset_shared_runtime() -> None:
    """Best-effort reset of the shared runtime after settings changes."""
    try:
        from ..runtime import reset_runtime_service
    except ImportError:
        logger.debug("Runtime service is unavailable during settings update.")
        return
    except Exception:
        logger.exception("Failed to import the shared Mutiny runtime reset hook.")
        return

    try:
        reset_runtime_service()
    except Exception:
        logger.exception("Failed to reset the shared Mutiny runtime.")


async def _load_json_payload(request: web.Request) -> dict:
    """Parse one JSON request body and reject malformed payloads as client errors."""
    try:
        payload = await request.json()
    except Exception as exc:
        raise SettingsValidationError("Request body must be valid JSON.") from exc

    if not isinstance(payload, dict):
        raise SettingsValidationError("Request body must be a JSON object.")
    return payload


def register_settings_routes(
    route_table: web.RouteTableDef,
    settings_service: SettingsService,
) -> None:
    """Register settings-management routes on a Comfy route table."""

    @route_table.get("/mutiny/settings")
    async def get_mutiny_settings(_request: web.Request) -> web.Response:
        """Return non-secret settings plus token presence state."""
        try:
            return web.json_response(settings_service.get_settings_status())
        except Exception:
            logger.exception(
                "Failed to load ComfyUI-Mutiny settings route=/mutiny/settings."
            )
            return web.json_response(
                {"error": "Failed to load ComfyUI-Mutiny settings."},
                status=500,
            )

    @route_table.post("/mutiny/settings")
    async def save_mutiny_settings(request: web.Request) -> web.Response:
        """Validate and persist non-secret settings from the frontend."""
        try:
            payload = await _load_json_payload(request)
            settings = settings_service.save_settings(payload)
            _reset_shared_runtime()
            return web.json_response(
                {
                    "settings": settings.as_dict(),
                    "token_configured": settings_service.token_exists(),
                }
            )
        except SettingsValidationError as exc:
            return web.json_response({"error": str(exc)}, status=400)
        except Exception:
            logger.exception(
                "Failed to save ComfyUI-Mutiny settings route=/mutiny/settings."
            )
            return web.json_response(
                {"error": "Failed to save ComfyUI-Mutiny settings."},
                status=500,
            )

    @route_table.get("/mutiny/cache/status")
    async def get_mutiny_cache_status(_request: web.Request) -> web.Response:
        """Return current logical usage for Mutiny's disk-backed artifact cache."""
        try:
            return web.json_response(settings_service.get_cache_status())
        except Exception:
            logger.exception(
                "Failed to load ComfyUI-Mutiny cache status route=/mutiny/cache/status."
            )
            return web.json_response(
                {"error": "Failed to load Mutiny cache status."},
                status=500,
            )

    @route_table.post("/mutiny/token")
    async def save_mutiny_token(request: web.Request) -> web.Response:
        """Persist the Discord token in keyring without exposing it back."""
        try:
            payload = await _load_json_payload(request)
            token = payload.get("token", "")
            settings_service.save_token(token)
            _reset_shared_runtime()
            return web.json_response({"token_configured": True})
        except (SettingsValidationError, ValueError) as exc:
            return web.json_response({"error": str(exc)}, status=400)
        except Exception:
            logger.exception(
                "Failed to save the ComfyUI-Mutiny Discord token route=/mutiny/token."
            )
            return web.json_response(
                {"error": "Failed to save the Discord token."},
                status=500,
            )

    @route_table.delete("/mutiny/token")
    async def clear_mutiny_token(_request: web.Request) -> web.Response:
        """Remove the stored Discord token from keyring."""
        try:
            settings_service.clear_token()
            _reset_shared_runtime()
            return web.json_response({"token_configured": False})
        except Exception:
            logger.exception(
                "Failed to clear the ComfyUI-Mutiny Discord token route=/mutiny/token."
            )
            return web.json_response(
                {"error": "Failed to clear the Discord token."},
                status=500,
            )


def register_prompt_server_routes(
    settings_service: SettingsService | None = None,
) -> bool:
    """Register settings routes on Comfy's PromptServer when available."""
    global _ROUTES_REGISTERED

    if _ROUTES_REGISTERED:
        return True

    try:
        from server import PromptServer
    except ImportError:
        logger.debug("PromptServer is unavailable; skipping route registration.")
        return False
    except Exception:
        logger.exception("Failed to import PromptServer during route registration.")
        return False

    prompt_server = getattr(PromptServer, "instance", None)
    if prompt_server is None or not hasattr(prompt_server, "routes"):
        logger.debug(
            "PromptServer instance is unavailable; skipping route registration."
        )
        return False

    register_settings_routes(
        prompt_server.routes, settings_service or get_settings_service()
    )
    _ROUTES_REGISTERED = True
    return True


__all__ = ["register_prompt_server_routes", "register_settings_routes"]
