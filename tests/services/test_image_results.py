"""Test image result conversion helpers used by the runtime adapter."""

from __future__ import annotations

import io
import sys

import numpy as np
import pytest
from PIL import Image

from tests.support.fakes import FakeRuntimeService


def test_image_to_tensor_batch_returns_single_image_batch(
    plugin_package, sample_single_image
):
    """Keep single-image batch conversion stable for grid-disabled flows."""
    services_module = sys.modules[f"{plugin_package.__name__}.services"]
    batch = services_module.image_to_tensor_batch(sample_single_image)

    assert tuple(batch.shape) == (1, 2, 2, 3)
    assert np.array_equal(
        (batch[0].numpy() * 255).astype(np.uint8), sample_single_image
    )


def test_build_split_image_output_returns_split_grid_batch(
    plugin_package, sample_grid_image
):
    """Use Mutiny-provided tiles when converting grid-producing results."""
    services_module = sys.modules[f"{plugin_package.__name__}.services"]
    runtime_result = FakeRuntimeService(sample_grid_image).imagine_and_wait(
        "cat",
        node_name="MidjourneyV7Request",
    )

    batch = services_module.build_split_image_output(runtime_result)

    assert tuple(batch.shape) == (4, 2, 2, 3)
    assert np.array_equal(
        (batch[0].numpy() * 255).astype(np.uint8), sample_grid_image[:2, :2, :]
    )


def test_build_split_image_output_requires_tiles_for_grid_results(
    plugin_package, sample_single_image
):
    """Fail clearly when grid conversion is requested without tile data."""
    services_module = sys.modules[f"{plugin_package.__name__}.services"]
    runtime_result = FakeRuntimeService(sample_single_image).upscale_image_and_wait(
        b"image-bytes",
        mode="standard",
        node_name="ChangeNodeTest",
    )

    with pytest.raises(RuntimeError, match="Split-grid output is unavailable"):
        services_module.build_split_image_output(runtime_result)


def test_build_single_image_output_returns_single_image_batch(
    plugin_package, sample_single_image
):
    """Return one single-image batch for single-image runtime results."""
    services_module = sys.modules[f"{plugin_package.__name__}.services"]
    runtime_result = FakeRuntimeService(sample_single_image).upscale_image_and_wait(
        b"image-bytes",
        mode="standard",
        node_name="ChangeNodeTest",
    )

    batch = services_module.build_single_image_output(runtime_result)

    assert tuple(batch.shape) == (1, 2, 2, 3)


def test_image_bytes_to_numpy_decodes_rgb_image(plugin_package, sample_single_image):
    """Decode runtime image bytes into the same RGB array shape the nodes expect."""
    services_module = sys.modules[f"{plugin_package.__name__}.services"]
    buffer = io.BytesIO()
    Image.fromarray(sample_single_image).save(buffer, format="PNG")

    image = services_module.image_bytes_to_numpy(buffer.getvalue())

    assert np.array_equal(image, sample_single_image)
