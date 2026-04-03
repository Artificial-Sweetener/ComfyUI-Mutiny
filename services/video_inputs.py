"""Encode ComfyUI ``VIDEO`` inputs into raw bytes for Mutiny submissions."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Protocol


class VideoEncodingError(RuntimeError):
    """Raise when a ComfyUI ``VIDEO`` input cannot be converted into bytes."""


class _StreamableVideoInput(Protocol):
    """Describe the ``VIDEO`` input capability the plugin relies on."""

    def get_stream_source(self) -> str | BytesIO:
        """Return the path or in-memory stream backing the video input."""


def comfy_video_to_bytes(video_value: _StreamableVideoInput) -> bytes:
    """Return the exact bytes backing one ComfyUI ``VIDEO`` input."""
    try:
        source = video_value.get_stream_source()
    except AttributeError as exc:
        raise VideoEncodingError(
            "Video input did not expose a streamable ComfyUI source."
        ) from exc

    if isinstance(source, str):
        try:
            return Path(source).read_bytes()
        except OSError as exc:
            raise VideoEncodingError("Failed to read video input from disk.") from exc

    if isinstance(source, BytesIO):
        position = source.tell()
        try:
            source.seek(0)
            return source.read()
        finally:
            source.seek(position)

    if hasattr(source, "read"):
        try:
            position = source.tell()
        except (AttributeError, OSError):
            position = None

        try:
            if position is not None:
                source.seek(0)
            return source.read()
        except OSError as exc:
            raise VideoEncodingError("Failed to read video input stream.") from exc
        finally:
            if position is not None:
                source.seek(position)

    raise VideoEncodingError("Video input exposed an unsupported stream source.")


__all__ = ["VideoEncodingError", "comfy_video_to_bytes"]
