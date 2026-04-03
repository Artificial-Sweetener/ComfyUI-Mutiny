"""Expose a Mutiny-compatible token provider backed by keyring."""

from __future__ import annotations

from .token_store import KeyringTokenStore


class MissingDiscordTokenError(RuntimeError):
    """Raise when the plugin has no Discord token configured."""


class KeyringTokenProvider:
    """Load the Discord token from the plugin's keyring-backed store."""

    def __init__(self, token_store: KeyringTokenStore) -> None:
        """Store the keyring token store used by this provider."""
        self._token_store = token_store

    def get_token(self) -> str:
        """Return the configured Discord token or raise a clear error."""
        token = self._token_store.load_token()
        if not token:
            raise MissingDiscordTokenError(
                "Mutiny needs your Discord token before it can run. "
                "Save it in ComfyUI Settings under Mutiny. You'll need to figure "
                "out how to obtain that yourself; Mutiny does not provide help "
                "with token acquisition."
            )
        return token


__all__ = ["KeyringTokenProvider", "MissingDiscordTokenError"]
