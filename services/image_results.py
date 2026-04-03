"""Load generated images and convert them into ComfyUI tensors."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Sequence

import numpy as np
import requests
import torch
from mutiny import Config, ImageTile
from PIL import Image, UnidentifiedImageError
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

if TYPE_CHECKING:
    from ..runtime.models import RuntimeJobResult


class ImageFetchError(RuntimeError):
    """Raise when a generated image could not be downloaded."""


class ImageDecodeError(RuntimeError):
    """Raise when generated image bytes could not be decoded."""


class ResultImageLoader:
    """Download generated image bytes using explicit timeouts and retries."""

    def __init__(self, session: Session | None = None) -> None:
        """Store the HTTP session used for generated-image fetches."""
        self._session = session or _build_session()

    def fetch_bytes(self, image_url: str, *, config: Config) -> bytes:
        """Load generated image bytes from either a local path or a remote URL."""
        if "://" not in image_url:
            local_path = Path(image_url)
            try:
                return local_path.read_bytes()
            except OSError as exc:
                raise ImageFetchError(
                    "Failed to load generated image artifact."
                ) from exc

        timeout = (config.cdn.connect_timeout, config.cdn.read_timeout)

        try:
            response = self._session.get(image_url, timeout=timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ImageFetchError("Failed to download generated image.") from exc

        return response.content


def build_single_image_output(result: RuntimeJobResult) -> torch.Tensor:
    """Convert one completed single-image runtime result into a ComfyUI batch."""
    return image_to_tensor_batch(image_bytes_to_numpy(result.image_bytes))


def build_split_image_output(result: RuntimeJobResult) -> torch.Tensor:
    """Convert one completed grid-producing runtime result into a split batch."""
    if not result.tiles:
        raise ImageDecodeError("Split-grid output is unavailable for this result.")
    return job_tiles_to_tensor_batch(result.tiles)


def image_bytes_to_numpy(image_bytes: bytes) -> np.ndarray:
    """Decode raw image bytes into an RGB numpy array."""
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            return np.array(image.convert("RGB"))
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ImageDecodeError("Failed to decode generated image.") from exc


def image_to_tensor_batch(image: np.ndarray) -> torch.Tensor:
    """Convert one RGB image into a single-image ComfyUI batch tensor."""
    tensor = torch.from_numpy(image).float() / 255.0
    return tensor.unsqueeze(0)


def job_tiles_to_tensor_batch(tiles: Sequence[ImageTile]) -> torch.Tensor:
    """Convert public Mutiny tile bytes into a multi-image ComfyUI batch tensor."""
    tensors = [
        image_to_tensor_batch(image_bytes_to_numpy(tile.image_bytes)) for tile in tiles
    ]
    return torch.cat(tensors, dim=0)


def _build_session() -> Session:
    """Create a requests session with retry behavior for CDN fetches."""
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


__all__ = [
    "ImageDecodeError",
    "ImageFetchError",
    "ResultImageLoader",
    "build_single_image_output",
    "build_split_image_output",
    "image_bytes_to_numpy",
    "image_to_tensor_batch",
    "job_tiles_to_tensor_batch",
]
