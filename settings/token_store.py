"""Persist the Discord token in the system credential store via keyring."""

from __future__ import annotations

import keyring
from keyring.errors import KeyringError, PasswordDeleteError

_SERVICE_NAME = "ComfyUI-Mutiny"
_TOKEN_USERNAME = "discord-user-token"


class KeyringTokenStore:
    """Read and write the Discord token through keyring."""

    def __init__(
        self,
        *,
        service_name: str = _SERVICE_NAME,
        token_username: str = _TOKEN_USERNAME,
    ) -> None:
        """Store the keyring identity used for token access."""
        self._service_name = service_name
        self._token_username = token_username

    def save_token(self, token: str) -> None:
        """Persist a non-empty Discord token into keyring."""
        normalized_token = token.strip()
        if not normalized_token:
            raise ValueError("Discord token cannot be empty.")

        try:
            keyring.set_password(
                self._service_name,
                self._token_username,
                normalized_token,
            )
        except KeyringError as exc:
            raise RuntimeError("The Discord token could not be saved.") from exc

    def load_token(self) -> str | None:
        """Return the stored Discord token or `None` when absent."""
        try:
            return keyring.get_password(self._service_name, self._token_username)
        except KeyringError as exc:
            raise RuntimeError("The Discord token could not be read.") from exc

    def clear_token(self) -> None:
        """Remove the stored Discord token when present."""
        try:
            keyring.delete_password(self._service_name, self._token_username)
        except PasswordDeleteError:
            return
        except KeyringError as exc:
            raise RuntimeError("The Discord token could not be cleared.") from exc

    def token_exists(self) -> bool:
        """Return whether a Discord token is currently stored."""
        return bool(self.load_token())


__all__ = ["KeyringTokenStore"]
