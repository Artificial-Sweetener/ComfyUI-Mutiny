"""Test video result loading helpers used by the animate runtime path."""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest
from comfy_api.latest import InputImpl
from mutiny import Config
from requests import RequestException


class _FakeResponse:
    """Provide a minimal response object for the video loader tests."""

    def __init__(self, content: bytes, *, status_code: int = 200) -> None:
        """Store the canned payload returned by the fake session."""
        self.content = content
        self.status_code = status_code

    def raise_for_status(self) -> None:
        """Raise a simple error when the fake response is configured as failing."""
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _RecordingSession:
    """Record GET calls and return one scripted response or exception."""

    def __init__(self, response: _FakeResponse | Exception) -> None:
        """Store the fake response object or exception raised by ``get``."""
        self._response = response
        self.calls: list[tuple[str, tuple[float, float]]] = []

    def get(self, url: str, timeout: tuple[float, float]):
        """Record the request and return the scripted result."""
        self.calls.append((url, timeout))
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


def test_result_video_loader_wraps_downloaded_bytes_in_native_video(plugin_package):
    """Return a native file-backed Comfy video object from downloaded bytes."""
    services_module = sys.modules[f"{plugin_package.__name__}.services"]
    config = Config.create(
        token_provider=type("TokenProvider", (), {"get_token": lambda self: "x"})(),
        guild_id="guild-1",
        channel_id="channel-1",
    )
    session = _RecordingSession(_FakeResponse(b"fake-mp4"))
    loader = services_module.ResultVideoLoader(session=session)

    video_value = loader.fetch_video(
        "https://example.invalid/final.mp4",
        config=config,
    )

    assert isinstance(video_value, InputImpl.VideoFromFile)
    assert session.calls == [
        (
            "https://example.invalid/final.mp4",
            (config.cdn.connect_timeout, config.cdn.read_timeout),
        )
    ]
    source = video_value.get_stream_source()
    assert isinstance(source, io.BytesIO)
    assert source.getvalue() == b"fake-mp4"


def test_result_video_loader_raises_cleanly_for_download_failures(plugin_package):
    """Raise the stable video-download error when the CDN request fails."""
    services_module = sys.modules[f"{plugin_package.__name__}.services"]
    config = Config.create(
        token_provider=type("TokenProvider", (), {"get_token": lambda self: "x"})(),
        guild_id="guild-1",
        channel_id="channel-1",
    )
    loader = services_module.ResultVideoLoader(
        session=_RecordingSession(RequestException("network down"))
    )

    with pytest.raises(RuntimeError, match="Failed to download generated video\\."):
        loader.fetch_video("https://example.invalid/final.mp4", config=config)


def test_result_video_loader_prefers_local_file_paths(plugin_package, tmp_path):
    """Load local video artifacts directly instead of issuing another HTTP request."""

    services_module = sys.modules[f"{plugin_package.__name__}.services"]
    config = Config.create(
        token_provider=type("TokenProvider", (), {"get_token": lambda self: "x"})(),
        guild_id="guild-1",
        channel_id="channel-1",
    )
    local_path = Path(tmp_path) / "job-animate.mp4"
    local_path.write_bytes(b"local-video")
    session = _RecordingSession(_FakeResponse(b"remote-video"))
    loader = services_module.ResultVideoLoader(session=session)

    video_value = loader.fetch_video(str(local_path), config=config)

    assert isinstance(video_value, InputImpl.VideoFromFile)
    assert session.calls == []
    source = video_value.get_stream_source()
    assert isinstance(source, io.BytesIO)
    assert source.getvalue() == b"local-video"
