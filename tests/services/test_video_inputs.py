"""Test video input encoding helpers used by the extend node path."""

from __future__ import annotations

from io import BytesIO

import pytest


class _VideoFromBytes:
    """Provide a deterministic Comfy ``VIDEO``-like input backed by memory."""

    def __init__(self, payload: bytes) -> None:
        """Store the encoded payload returned by ``get_stream_source``."""
        self._payload = payload

    def get_stream_source(self) -> BytesIO:
        """Return the payload as a new streamable in-memory source."""
        return BytesIO(self._payload)


def test_comfy_video_to_bytes_reads_bytesio_sources(plugin_package):
    """Return the exact bytes from an in-memory Comfy ``VIDEO`` input."""
    services_module = __import__(
        f"{plugin_package.__name__}.services",
        fromlist=["comfy_video_to_bytes"],
    )

    payload = services_module.comfy_video_to_bytes(_VideoFromBytes(b"midjourney-video"))

    assert payload == b"midjourney-video"


def test_comfy_video_to_bytes_raises_cleanly_for_invalid_inputs(plugin_package):
    """Raise the stable encoding error when the input is not a Comfy ``VIDEO``."""
    services_module = __import__(
        f"{plugin_package.__name__}.services",
        fromlist=["comfy_video_to_bytes"],
    )

    with pytest.raises(
        RuntimeError,
        match="Video input did not expose a streamable ComfyUI source\\.",
    ):
        services_module.comfy_video_to_bytes(object())


__all__ = []
