"""Test prompt-image encoding into Mutiny imagine submission payloads."""

from __future__ import annotations

import base64
import io
import sys

import numpy as np
import pytest
import torch
from PIL import Image


def test_comfy_image_to_png_bytes_accepts_hwc_rgb_tensor(plugin_package):
    """Encode one HWC Comfy image tensor into decodable PNG bytes."""
    services_module = sys.modules[f"{plugin_package.__name__}.services"]
    prompt_image = torch.tensor(
        [[[0.0, 0.5, 1.0], [1.0, 0.25, 0.0]]],
        dtype=torch.float32,
    )

    image_bytes = services_module.comfy_image_to_png_bytes(prompt_image)
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    assert image.size == (2, 1)
    assert np.array(image).tolist() == [[[0, 128, 255], [255, 64, 0]]]


def test_comfy_image_to_png_bytes_accepts_single_image_batch(plugin_package):
    """Accept one BHWC image batch when converting for Mutiny lookup."""
    services_module = sys.modules[f"{plugin_package.__name__}.services"]
    prompt_image = torch.tensor(
        [[[[0.0, 0.5, 1.0], [1.0, 0.25, 0.0]]]],
        dtype=torch.float32,
    )

    image_bytes = services_module.comfy_image_to_png_bytes(prompt_image)
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    assert image.size == (2, 1)


def test_comfy_image_to_png_bytes_rejects_multi_image_batches(plugin_package):
    """Reject batched prompt images when more than one image is present."""
    services_module = sys.modules[f"{plugin_package.__name__}.services"]

    with pytest.raises(ValueError, match="exactly one image"):
        services_module.comfy_image_to_png_bytes(
            torch.zeros((2, 1, 1, 3), dtype=torch.float32)
        )


def test_comfy_image_to_png_bytes_rejects_non_tensor_inputs(plugin_package):
    """Reject lookup image inputs that are not torch tensors."""
    services_module = sys.modules[f"{plugin_package.__name__}.services"]

    with pytest.raises(ValueError, match="torch.Tensor"):
        services_module.comfy_image_to_png_bytes("not-a-tensor")


def test_comfy_image_to_png_bytes_rejects_non_rgb_inputs(plugin_package):
    """Reject lookup image tensors that do not contain three color channels."""
    services_module = sys.modules[f"{plugin_package.__name__}.services"]

    with pytest.raises(ValueError, match="three RGB channels"):
        services_module.comfy_image_to_png_bytes(
            torch.zeros((1, 2, 1), dtype=torch.float32)
        )


def test_prompt_image_to_data_url_encodes_one_rgb_tensor(plugin_package):
    """Encode one ComfyUI IMAGE tensor into a PNG data URL."""
    services_module = sys.modules[f"{plugin_package.__name__}.services"]
    prompt_image = torch.tensor(
        [[[[0.0, 0.5, 1.0], [1.0, 0.25, 0.0]]]],
        dtype=torch.float32,
    )

    data_url = services_module.prompt_image_to_data_url(prompt_image)

    assert data_url.startswith("data:image/png;base64,")
    encoded_payload = data_url.split(",", maxsplit=1)[1]
    image = Image.open(io.BytesIO(base64.b64decode(encoded_payload))).convert("RGB")

    assert image.size == (2, 1)
    assert np.array(image).tolist() == [[[0, 128, 255], [255, 64, 0]]]


def test_count_comfy_images_reports_hwc_and_bhwc_sizes(plugin_package):
    """Count image payloads without encoding them into data URLs first."""
    services_module = sys.modules[f"{plugin_package.__name__}.services"]

    assert (
        services_module.count_comfy_images(
            torch.tensor([[[0.0, 0.5, 1.0]]], dtype=torch.float32)
        )
        == 1
    )
    assert (
        services_module.count_comfy_images(
            torch.zeros((2, 1, 1, 3), dtype=torch.float32)
        )
        == 2
    )


def test_comfy_images_to_data_urls_accepts_one_hwc_image(plugin_package):
    """Encode one HWC image tensor into a single data URL submission payload."""
    services_module = sys.modules[f"{plugin_package.__name__}.services"]
    prompt_image = torch.tensor(
        [[[0.0, 0.5, 1.0], [1.0, 0.25, 0.0]]],
        dtype=torch.float32,
    )

    data_urls = services_module.comfy_images_to_data_urls(prompt_image)

    assert len(data_urls) == 1
    assert data_urls[0].startswith("data:image/png;base64,")


def test_comfy_images_to_data_urls_accepts_batched_images(plugin_package):
    """Encode one BHWC image batch into one data URL per batch item."""
    services_module = sys.modules[f"{plugin_package.__name__}.services"]
    prompt_images = torch.tensor(
        [
            [[[0.0, 0.5, 1.0], [1.0, 0.25, 0.0]]],
            [[[0.25, 0.0, 0.5], [0.0, 1.0, 0.25]]],
        ],
        dtype=torch.float32,
    )

    data_urls = services_module.comfy_images_to_data_urls(prompt_images)

    assert len(data_urls) == 2
    assert all(data_url.startswith("data:image/png;base64,") for data_url in data_urls)


def test_prompt_image_to_data_url_rejects_invalid_tensor_shape(plugin_package):
    """Reject prompt-image tensors that are not one RGB image."""
    services_module = sys.modules[f"{plugin_package.__name__}.services"]

    with pytest.raises(ValueError, match="HWC or BHWC"):
        services_module.prompt_image_to_data_url(
            torch.zeros((1, 2), dtype=torch.float32)
        )

    with pytest.raises(ValueError, match="exactly one image"):
        services_module.prompt_image_to_data_url(
            torch.zeros((2, 1, 1, 3), dtype=torch.float32)
        )

    with pytest.raises(ValueError, match="torch.Tensor"):
        services_module.prompt_image_to_data_url("not-a-tensor")

    with pytest.raises(ValueError, match="three RGB channels"):
        services_module.prompt_image_to_data_url(
            torch.zeros((1, 2, 1), dtype=torch.float32)
        )


def test_comfy_images_to_data_urls_rejects_invalid_tensor_shape(plugin_package):
    """Reject image-condition tensors that are not one or more RGB images."""
    services_module = sys.modules[f"{plugin_package.__name__}.services"]

    with pytest.raises(ValueError, match="HWC or BHWC"):
        services_module.comfy_images_to_data_urls(
            torch.zeros((1, 2), dtype=torch.float32)
        )

    with pytest.raises(ValueError, match="cannot be empty"):
        services_module.comfy_images_to_data_urls(
            torch.zeros((0, 1, 1, 3), dtype=torch.float32)
        )

    with pytest.raises(ValueError, match="torch.Tensor"):
        services_module.comfy_images_to_data_urls("not-a-tensor")

    with pytest.raises(ValueError, match="three RGB channels"):
        services_module.comfy_images_to_data_urls(
            torch.zeros((2, 1, 1, 1), dtype=torch.float32)
        )


def test_comfy_mask_to_data_url_encodes_one_hw_mask(plugin_package):
    """Encode one HW mask tensor into a grayscale PNG data URL."""
    services_module = sys.modules[f"{plugin_package.__name__}.services"]
    mask = torch.tensor([[0.0, 1.0], [0.5, 0.25]], dtype=torch.float32)

    data_url = services_module.comfy_mask_to_data_url(mask)

    assert data_url.startswith("data:image/png;base64,")
    encoded_payload = data_url.split(",", maxsplit=1)[1]
    image = Image.open(io.BytesIO(base64.b64decode(encoded_payload))).convert("L")

    assert image.size == (2, 2)
    assert np.array(image).tolist() == [[0, 255], [128, 64]]


def test_comfy_mask_to_data_url_accepts_single_mask_batch(plugin_package):
    """Accept one BHW mask batch when converting for Mutiny inpaint."""
    services_module = sys.modules[f"{plugin_package.__name__}.services"]
    mask = torch.tensor([[[0.0, 1.0], [1.0, 0.0]]], dtype=torch.float32)

    data_url = services_module.comfy_mask_to_data_url(mask)

    assert data_url.startswith("data:image/png;base64,")


def test_comfy_mask_to_data_url_rejects_multi_mask_batches(plugin_package):
    """Reject batched mask inputs when more than one mask is present."""
    services_module = sys.modules[f"{plugin_package.__name__}.services"]

    with pytest.raises(ValueError, match="exactly one mask"):
        services_module.comfy_mask_to_data_url(
            torch.zeros((2, 2, 2), dtype=torch.float32)
        )


def test_comfy_mask_to_data_url_rejects_non_tensor_inputs(plugin_package):
    """Reject mask inputs that are not torch tensors."""
    services_module = sys.modules[f"{plugin_package.__name__}.services"]

    with pytest.raises(ValueError, match="torch.Tensor"):
        services_module.comfy_mask_to_data_url("not-a-tensor")


def test_comfy_mask_to_data_url_rejects_empty_masks(plugin_package):
    """Reject empty mask tensors before attempting PNG encoding."""
    services_module = sys.modules[f"{plugin_package.__name__}.services"]

    with pytest.raises(ValueError, match="cannot be empty"):
        services_module.comfy_mask_to_data_url(torch.zeros((0, 2), dtype=torch.float32))


def test_comfy_mask_to_data_url_preserves_black_and_white_polarity(plugin_package):
    """Preserve mask polarity so white remains selected and black remains preserved."""
    services_module = sys.modules[f"{plugin_package.__name__}.services"]
    mask = torch.tensor([[0.0, 1.0]], dtype=torch.float32)

    data_url = services_module.comfy_mask_to_data_url(mask)

    encoded_payload = data_url.split(",", maxsplit=1)[1]
    image = Image.open(io.BytesIO(base64.b64decode(encoded_payload))).convert("L")
    assert np.array(image).tolist() == [[0, 255]]
