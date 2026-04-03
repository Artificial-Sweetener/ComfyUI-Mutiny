"""Bridge runtime progress updates into ComfyUI previews."""

from __future__ import annotations

from io import BytesIO
from typing import Callable

import numpy as np
import torch
from comfy.utils import ProgressBar
from PIL import Image

ProgressPayload = bytes | np.ndarray | Image.Image | None


def build_comfy_progress_reporter() -> tuple[
    Callable[[str | None, ProgressPayload], None],
    list[torch.Tensor | None],
]:
    """Build a progress reporter that updates ComfyUI previews in-place."""
    progress_bar = ProgressBar(100)
    preview_image: list[torch.Tensor | None] = [None]

    def report(progress_text: str | None, preview_payload: ProgressPayload) -> None:
        """Apply one progress update without letting malformed input break previews."""
        percent = _parse_progress_percent(progress_text)
        preview = _normalize_preview_image(preview_payload)
        preview_tuple = None
        if preview is not None:
            preview_tuple = ("PNG", preview, 512)
            preview_image[0] = _image_to_preview_tensor(preview)

        progress_bar.update_absolute(percent, 100, preview_tuple)

    return report, preview_image


def _parse_progress_percent(progress_text: str | None) -> int:
    """Convert Mutiny progress text into a clamped integer percentage."""
    if not progress_text:
        return 0

    try:
        return max(0, min(100, int(str(progress_text).replace("%", "").strip())))
    except (TypeError, ValueError):
        return 0


def _normalize_preview_image(preview_payload: ProgressPayload) -> Image.Image | None:
    """Normalize preview payloads into an RGB Pillow image."""
    if preview_payload is None:
        return None

    if isinstance(preview_payload, Image.Image):
        return preview_payload.convert("RGB")

    if isinstance(preview_payload, bytes):
        with Image.open(BytesIO(preview_payload)) as image:
            return image.convert("RGB")

    image_array = preview_payload
    if image_array.ndim == 2:
        image_array = np.stack([image_array] * 3, axis=-1)
    if image_array.shape[-1] == 4:
        image_array = image_array[..., :3]
    return Image.fromarray(image_array.astype(np.uint8))


def _image_to_preview_tensor(image: Image.Image) -> torch.Tensor:
    """Convert a preview image into the tensor shape ComfyUI expects."""
    tensor = torch.from_numpy(np.array(image)).float() / 255.0
    return tensor.permute(2, 0, 1).unsqueeze(0)


__all__ = ["ProgressPayload", "build_comfy_progress_reporter"]
