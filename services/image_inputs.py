"""Encode ComfyUI image tensors into Mutiny-ready image payloads."""

from __future__ import annotations

import base64
from io import BytesIO

import numpy as np
import torch
from PIL import Image


class PromptImageEncodingError(ValueError):
    """Raise when a prompt-image input cannot be converted into one PNG data URL."""


class MaskImageEncodingError(ValueError):
    """Raise when a mask input cannot be converted into one grayscale PNG data URL."""


def count_comfy_images(prompt_image: torch.Tensor) -> int:
    """Return the number of images carried by one ComfyUI IMAGE payload."""
    return len(_extract_image_tensors(prompt_image))


def require_single_comfy_image(prompt_image: torch.Tensor) -> torch.Tensor:
    """Return exactly one HWC image tensor or raise when the payload is batched."""
    image_tensors = _extract_image_tensors(prompt_image)
    if len(image_tensors) != 1:
        raise PromptImageEncodingError(
            "Prompt image input must contain exactly one image."
        )
    return image_tensors[0]


def comfy_image_to_png_bytes(prompt_image: torch.Tensor) -> bytes:
    """Convert one ComfyUI IMAGE payload into PNG bytes.

    Args:
        prompt_image: A ComfyUI IMAGE tensor in ``HWC`` or ``BHWC`` form.

    Returns:
        PNG-encoded bytes suitable for image-context lookup.

    Raises:
        PromptImageEncodingError: If the payload is empty, batched with more than one
            image, or not a three-channel image tensor.
    """
    image_array = _extract_single_image_array(prompt_image)
    buffer = BytesIO()
    Image.fromarray(image_array).save(buffer, format="PNG")
    return buffer.getvalue()


def prompt_image_to_data_url(prompt_image: torch.Tensor) -> str:
    """Convert one ComfyUI IMAGE payload into a PNG data URL.

    Args:
        prompt_image: A ComfyUI IMAGE tensor in ``HWC`` or ``BHWC`` form.

    Returns:
        One ``data:image/png;base64,...`` string suitable for ``Mutiny.imagine``.

    Raises:
        PromptImageEncodingError: If the payload is empty, batched with more than one
            image, or not a three-channel image tensor.
    """
    encoded_bytes = base64.b64encode(comfy_image_to_png_bytes(prompt_image)).decode(
        "ascii"
    )
    return f"data:image/png;base64,{encoded_bytes}"


def comfy_images_to_data_urls(images: torch.Tensor) -> tuple[str, ...]:
    """Convert one or many ComfyUI IMAGE tensors into PNG data URLs.

    Args:
        images: A ComfyUI IMAGE tensor in ``HWC`` or ``BHWC`` form.

    Returns:
        One data URL per encoded image, preserving batch order.

    Raises:
        PromptImageEncodingError: If the payload is empty or not one or more RGB
            images in ``HWC`` or ``BHWC`` form.
    """
    encoded_images: list[str] = []
    for image_tensor in _extract_image_tensors(images):
        encoded_images.append(prompt_image_to_data_url(image_tensor))
    return tuple(encoded_images)


def comfy_mask_to_data_url(mask_image: torch.Tensor) -> str:
    """Convert one ComfyUI MASK payload into a grayscale PNG data URL.

    Args:
        mask_image: A ComfyUI MASK tensor in ``HW`` or ``BHW`` form.

    Returns:
        One ``data:image/png;base64,...`` string suitable for ``Mutiny.inpaint``.

    Raises:
        MaskImageEncodingError: If the payload is empty, batched with more than one
            mask, or not a mask tensor in ``HW`` or ``BHW`` form.
    """
    mask_array = _extract_single_mask_array(mask_image)
    buffer = BytesIO()
    Image.fromarray(mask_array).save(buffer, format="PNG")
    encoded_bytes = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded_bytes}"


def _extract_single_image_array(prompt_image: torch.Tensor) -> np.ndarray:
    """Normalize one ComfyUI IMAGE tensor into a uint8 RGB numpy image."""
    return _normalize_rgb_tensor(require_single_comfy_image(prompt_image))


def _extract_single_mask_array(mask_image: torch.Tensor) -> np.ndarray:
    """Normalize one ComfyUI MASK tensor into a uint8 grayscale numpy image."""
    return _normalize_mask_tensor(_extract_single_mask_tensor(mask_image))


def _extract_image_tensors(prompt_image: torch.Tensor) -> tuple[torch.Tensor, ...]:
    """Normalize one ComfyUI IMAGE payload into one or more HWC tensors."""
    if not isinstance(prompt_image, torch.Tensor):
        raise PromptImageEncodingError("Prompt image input must be a torch.Tensor.")

    image_tensor = prompt_image.detach().cpu()
    if image_tensor.ndim == 4:
        if image_tensor.shape[0] == 0:
            raise PromptImageEncodingError("Prompt image input cannot be empty.")
        return tuple(image_tensor[index] for index in range(image_tensor.shape[0]))
    elif image_tensor.ndim != 3:
        raise PromptImageEncodingError(
            "Prompt image input must use HWC or BHWC tensor shape."
        )
    return (image_tensor,)


def _extract_single_mask_tensor(mask_image: torch.Tensor) -> torch.Tensor:
    """Return exactly one HW mask tensor or raise when the payload is invalid."""
    if not isinstance(mask_image, torch.Tensor):
        raise MaskImageEncodingError("Mask input must be a torch.Tensor.")

    mask_tensor = mask_image.detach().cpu()
    if mask_tensor.ndim == 3:
        if mask_tensor.shape[0] == 0:
            raise MaskImageEncodingError("Mask input cannot be empty.")
        if mask_tensor.shape[0] != 1:
            raise MaskImageEncodingError("Mask input must contain exactly one mask.")
        mask_tensor = mask_tensor[0]
    elif mask_tensor.ndim != 2:
        raise MaskImageEncodingError("Mask input must use HW or BHW tensor shape.")

    height, width = mask_tensor.shape
    if height <= 0 or width <= 0:
        raise MaskImageEncodingError("Mask input cannot be empty.")
    return mask_tensor


def _normalize_rgb_tensor(image_tensor: torch.Tensor) -> np.ndarray:
    """Convert one HWC image tensor into a uint8 RGB numpy array."""
    height, width, channels = image_tensor.shape
    if height <= 0 or width <= 0:
        raise PromptImageEncodingError("Prompt image input cannot be empty.")
    if channels != 3:
        raise PromptImageEncodingError(
            "Prompt image input must contain exactly three RGB channels."
        )

    image_array = image_tensor.numpy()
    if np.issubdtype(image_array.dtype, np.floating):
        image_array = np.clip(image_array, 0.0, 1.0)
        image_array = np.rint(image_array * 255.0).astype(np.uint8)
    else:
        image_array = np.clip(image_array, 0, 255).astype(np.uint8)

    return image_array


def _normalize_mask_tensor(mask_tensor: torch.Tensor) -> np.ndarray:
    """Convert one HW mask tensor into a uint8 grayscale numpy array."""
    mask_array = mask_tensor.numpy()
    if np.issubdtype(mask_array.dtype, np.floating):
        mask_array = np.clip(mask_array, 0.0, 1.0)
        mask_array = np.rint(mask_array * 255.0).astype(np.uint8)
    else:
        mask_array = np.clip(mask_array, 0, 255).astype(np.uint8)
    return mask_array


__all__ = [
    "MaskImageEncodingError",
    "PromptImageEncodingError",
    "count_comfy_images",
    "comfy_mask_to_data_url",
    "comfy_image_to_png_bytes",
    "comfy_images_to_data_urls",
    "prompt_image_to_data_url",
    "require_single_comfy_image",
]
