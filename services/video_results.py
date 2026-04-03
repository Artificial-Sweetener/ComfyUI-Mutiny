"""Load generated videos and convert them into native ComfyUI video values."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import requests
from comfy_api.latest import InputImpl
from mutiny import Config
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class VideoFetchError(RuntimeError):
    """Raise when a generated video could not be downloaded."""


class ResultVideoLoader:
    """Download generated video bytes using explicit timeouts and retries."""

    def __init__(self, session: Session | None = None) -> None:
        """Store the HTTP session used for generated-video fetches."""
        self._session = session or _build_session()

    def fetch_video(self, video_url: str, *, config: Config) -> InputImpl.VideoFromFile:
        """Load one generated video from either a local file path or a remote URL."""
        if "://" not in video_url:
            local_path = Path(video_url)
            try:
                return InputImpl.VideoFromFile(BytesIO(local_path.read_bytes()))
            except OSError as exc:
                raise VideoFetchError(
                    "Failed to load generated video artifact."
                ) from exc

        timeout = (config.cdn.connect_timeout, config.cdn.read_timeout)

        try:
            response = self._session.get(video_url, timeout=timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise VideoFetchError("Failed to download generated video.") from exc

        return InputImpl.VideoFromFile(BytesIO(response.content))


def _build_session() -> Session:
    """Create a requests session with retry behavior for CDN video fetches."""
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=(500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


__all__ = ["ResultVideoLoader", "VideoFetchError"]
