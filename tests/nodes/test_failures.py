"""Characterize the unified exported node failure boundary."""

from __future__ import annotations

import sys
from io import BytesIO

import pytest
import torch


class _FakeVideoInput:
    """Provide a deterministic Comfy ``VIDEO``-like input for failure tests."""

    def __init__(self, payload: bytes) -> None:
        """Store the encoded video payload returned by ``get_stream_source``."""
        self._payload = payload

    def get_stream_source(self) -> BytesIO:
        """Return the in-memory payload as a streamable source."""
        return BytesIO(self._payload)


GENERATION_NODE_NAMES = [
    "MidjourneyCustomRequest",
    "MidjourneyV4Request",
    "MidjourneyV5Request",
    "MidjourneyV6Request",
    "MidjourneyV7Request",
    "MidjourneyV8AlphaRequest",
    "Niji4Request",
    "Niji5Request",
    "Niji6Request",
    "Niji7Request",
]


def invoke_generation_node(node_name, node):
    """Call a generation node with the minimum current required arguments."""
    kwargs = {
        "prompt": "cat",
        "negative_prompt": "dog",
    }

    if node_name == "MidjourneyCustomRequest":
        return node.generate(version="7", translate_weights=True, **kwargs)
    if node_name == "MidjourneyV4Request":
        return node.generate(
            model="Midjourney v4",
            aspect_ratio="1:1",
            translate_weights=True,
            **kwargs,
        )
    if node_name == "MidjourneyV5Request":
        return node.generate(model="Midjourney v5.2", translate_weights=True, **kwargs)
    if node_name == "MidjourneyV6Request":
        return node.generate(model="Midjourney v6.1", translate_weights=True, **kwargs)
    if node_name == "MidjourneyV7Request":
        return node.generate(**kwargs)
    if node_name == "MidjourneyV8AlphaRequest":
        return node.generate(**kwargs)
    if node_name == "Niji4Request":
        return node.generate(
            aspect_ratio="1:1",
            translate_weights=True,
            **kwargs,
        )
    if node_name == "Niji5Request":
        return node.generate(
            niji5_style="original",
            aspect_ratio="1:1",
            translate_weights=True,
            **kwargs,
        )
    if node_name == "Niji6Request":
        return node.generate(aspect_ratio="2:1", translate_weights=True, **kwargs)
    if node_name == "Niji7Request":
        return node.generate(aspect_ratio="2:1", **kwargs)
    raise AssertionError(f"Unhandled node: {node_name}")


@pytest.mark.parametrize("node_name", GENERATION_NODE_NAMES)
def test_generation_nodes_raise_node_execution_error_on_runtime_failures(
    plugin_package, make_node, fake_runtime_service_factory, node_name
):
    """Raise one shared node-boundary exception type for runtime failures."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS[node_name]
    common_module = sys.modules[f"{plugin_package.__name__}.nodes.common"]
    fake_runtime = fake_runtime_service_factory(imagine_exception=RuntimeError("boom"))
    node = make_node(node_class, _runtime_service=fake_runtime)

    with pytest.raises(common_module.NodeExecutionError, match="boom") as exc_info:
        invoke_generation_node(node_name, node)

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_validation_failures_are_wrapped_at_the_node_boundary(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Wrap prompt validation errors in the same node-boundary exception type."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["Niji6Request"]
    common_module = sys.modules[f"{plugin_package.__name__}.nodes.common"]
    fake_runtime = fake_runtime_service_factory()
    node = make_node(node_class, _runtime_service=fake_runtime)

    with pytest.raises(
        common_module.NodeExecutionError, match="between 1:2 and 2:1"
    ) as exc_info:
        node.generate(
            prompt="cat",
            negative_prompt="dog",
            aspect_ratio="3:1",
            translate_weights=True,
        )

    assert isinstance(exc_info.value.__cause__, ValueError)


def test_midjourney_image_upscale_node_wraps_unrecognized_image_failures(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Wrap the exact image-recognition failure at the shared node boundary."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyUpscaleNode"]
    common_module = sys.modules[f"{plugin_package.__name__}.nodes.common"]
    fake_runtime = fake_runtime_service_factory(
        upscale_image_exception=RuntimeError(
            "Image was not recognized as a cached Midjourney image by Mutiny."
        )
    )
    node = make_node(node_class, _runtime_service=fake_runtime)

    with pytest.raises(
        common_module.NodeExecutionError,
        match="Image was not recognized as a cached Midjourney image by Mutiny\\.",
    ) as exc_info:
        node.upscale(torch.zeros((1, 1, 3), dtype=torch.float32), "Standard")

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_midjourney_image_upscale_node_wraps_invalid_standard_image_failures(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Wrap the exact standard-mode compatibility error at the node boundary."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyUpscaleNode"]
    common_module = sys.modules[f"{plugin_package.__name__}.nodes.common"]
    fake_runtime = fake_runtime_service_factory(
        upscale_image_exception=RuntimeError(
            "Image was recognized, but Standard Upscale requires a Midjourney grid tile."
        )
    )
    node = make_node(node_class, _runtime_service=fake_runtime)

    with pytest.raises(
        common_module.NodeExecutionError,
        match="Image was recognized, but Standard Upscale requires a Midjourney grid tile\\.",
    ) as exc_info:
        node.upscale(torch.zeros((1, 1, 3), dtype=torch.float32), "Standard")

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_midjourney_image_upscale_node_wraps_invalid_subtle_image_failures(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Wrap the exact subtle-mode compatibility error at the node boundary."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyUpscaleNode"]
    common_module = sys.modules[f"{plugin_package.__name__}.nodes.common"]
    fake_runtime = fake_runtime_service_factory(
        upscale_image_exception=RuntimeError(
            "Image was recognized, but Subtle Upscale requires a recognized already-upscaled Midjourney image."
        )
    )
    node = make_node(node_class, _runtime_service=fake_runtime)

    with pytest.raises(
        common_module.NodeExecutionError,
        match=(
            "Image was recognized, but Subtle Upscale requires a recognized "
            "already-upscaled Midjourney image\\."
        ),
    ) as exc_info:
        node.upscale(torch.zeros((1, 1, 3), dtype=torch.float32), "Subtle")

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_midjourney_image_upscale_node_wraps_invalid_creative_image_failures(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Wrap the exact creative-mode compatibility error at the node boundary."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyUpscaleNode"]
    common_module = sys.modules[f"{plugin_package.__name__}.nodes.common"]
    fake_runtime = fake_runtime_service_factory(
        upscale_image_exception=RuntimeError(
            "Image was recognized, but Creative Upscale requires a recognized already-upscaled Midjourney image."
        )
    )
    node = make_node(node_class, _runtime_service=fake_runtime)

    with pytest.raises(
        common_module.NodeExecutionError,
        match=(
            "Image was recognized, but Creative Upscale requires a recognized "
            "already-upscaled Midjourney image\\."
        ),
    ) as exc_info:
        node.upscale(torch.zeros((1, 1, 3), dtype=torch.float32), "Creative")

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_midjourney_pan_node_wraps_unrecognized_image_failures(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Wrap the exact pan image-recognition failure at the shared node boundary."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyPanNode"]
    common_module = sys.modules[f"{plugin_package.__name__}.nodes.common"]
    fake_runtime = fake_runtime_service_factory(
        pan_image_exception=RuntimeError(
            "Image was not recognized as a cached Midjourney image by Mutiny."
        )
    )
    node = make_node(node_class, _runtime_service=fake_runtime)

    with pytest.raises(
        common_module.NodeExecutionError,
        match="Image was not recognized as a cached Midjourney image by Mutiny\\.",
    ) as exc_info:
        node.pan(torch.zeros((1, 1, 3), dtype=torch.float32), "Left")

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_midjourney_pan_node_wraps_non_upscaled_image_failures(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Wrap the exact pan compatibility error at the node boundary."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyPanNode"]
    common_module = sys.modules[f"{plugin_package.__name__}.nodes.common"]
    fake_runtime = fake_runtime_service_factory(
        pan_image_exception=RuntimeError(
            "Image was recognized, but Midjourney Pan requires a recognized already-upscaled Midjourney image."
        )
    )
    node = make_node(node_class, _runtime_service=fake_runtime)

    with pytest.raises(
        common_module.NodeExecutionError,
        match=(
            "Image was recognized, but Midjourney Pan requires a recognized "
            "already-upscaled Midjourney image\\."
        ),
    ) as exc_info:
        node.pan(torch.zeros((1, 1, 3), dtype=torch.float32), "Right")

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_midjourney_pan_node_wraps_runtime_submission_failures(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Wrap runtime submission failures at the pan node boundary."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyPanNode"]
    common_module = sys.modules[f"{plugin_package.__name__}.nodes.common"]
    fake_runtime = fake_runtime_service_factory(
        pan_image_exception=RuntimeError("Task failed: Queue full")
    )
    node = make_node(node_class, _runtime_service=fake_runtime)

    with pytest.raises(
        common_module.NodeExecutionError,
        match="Task failed: Queue full",
    ) as exc_info:
        node.pan(torch.zeros((1, 1, 3), dtype=torch.float32), "Down")

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_midjourney_pan_node_rejects_unsupported_direction_labels(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Wrap unsupported direct direction labels as one safe node-boundary failure."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyPanNode"]
    common_module = sys.modules[f"{plugin_package.__name__}.nodes.common"]
    fake_runtime = fake_runtime_service_factory()
    node = make_node(node_class, _runtime_service=fake_runtime)

    with pytest.raises(
        common_module.NodeExecutionError,
        match="Unsupported Midjourney pan direction: 'Diagonal'\\.",
    ) as exc_info:
        node.pan(torch.zeros((1, 1, 3), dtype=torch.float32), "Diagonal")

    assert isinstance(exc_info.value.__cause__, ValueError)
    assert fake_runtime.pan_image_calls == []


def test_midjourney_zoom_node_wraps_unrecognized_image_failures(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Wrap the exact zoom image-recognition failure at the shared node boundary."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyZoomNode"]
    common_module = sys.modules[f"{plugin_package.__name__}.nodes.common"]
    fake_runtime = fake_runtime_service_factory(
        zoom_image_exception=RuntimeError(
            "Image was not recognized as a cached Midjourney image by Mutiny."
        )
    )
    node = make_node(node_class, _runtime_service=fake_runtime)

    with pytest.raises(
        common_module.NodeExecutionError,
        match="Image was not recognized as a cached Midjourney image by Mutiny\\.",
    ) as exc_info:
        node.zoom(torch.zeros((1, 1, 3), dtype=torch.float32), 1.5)

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_midjourney_zoom_node_wraps_non_upscaled_image_failures(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Wrap the exact zoom compatibility error at the node boundary."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyZoomNode"]
    common_module = sys.modules[f"{plugin_package.__name__}.nodes.common"]
    fake_runtime = fake_runtime_service_factory(
        zoom_image_exception=RuntimeError(
            "Image was recognized, but Midjourney Zoom requires a recognized already-upscaled Midjourney image."
        )
    )
    node = make_node(node_class, _runtime_service=fake_runtime)

    with pytest.raises(
        common_module.NodeExecutionError,
        match=(
            "Image was recognized, but Midjourney Zoom requires a recognized "
            "already-upscaled Midjourney image\\."
        ),
    ) as exc_info:
        node.zoom(torch.zeros((1, 1, 3), dtype=torch.float32), 1.5)

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_midjourney_zoom_node_wraps_invalid_factor_failures(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Wrap zoom-factor validation failures at the node boundary."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyZoomNode"]
    common_module = sys.modules[f"{plugin_package.__name__}.nodes.common"]
    fake_runtime = fake_runtime_service_factory(
        zoom_image_exception=RuntimeError(
            "Midjourney Zoom factor must be between 1.00 and 2.00."
        )
    )
    node = make_node(node_class, _runtime_service=fake_runtime)

    with pytest.raises(
        common_module.NodeExecutionError,
        match="Midjourney Zoom factor must be between 1.00 and 2.00\\.",
    ) as exc_info:
        node.zoom(torch.zeros((1, 1, 3), dtype=torch.float32), 2.5)

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_midjourney_zoom_node_wraps_runtime_submission_failures(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Wrap runtime submission failures at the zoom node boundary."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyZoomNode"]
    common_module = sys.modules[f"{plugin_package.__name__}.nodes.common"]
    fake_runtime = fake_runtime_service_factory(
        zoom_image_exception=RuntimeError("Task failed: Queue full")
    )
    node = make_node(node_class, _runtime_service=fake_runtime)

    with pytest.raises(
        common_module.NodeExecutionError,
        match="Task failed: Queue full",
    ) as exc_info:
        node.zoom(torch.zeros((1, 1, 3), dtype=torch.float32), 1.24, "tight crop")

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_midjourney_variation_node_wraps_unrecognized_image_failures(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Wrap the exact image-recognition failure at the shared node boundary."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyVariationNode"]
    common_module = sys.modules[f"{plugin_package.__name__}.nodes.common"]
    fake_runtime = fake_runtime_service_factory(
        variation_exception=RuntimeError(
            "Image was not recognized as a cached Midjourney image by Mutiny."
        )
    )
    node = make_node(node_class, _runtime_service=fake_runtime)

    with pytest.raises(
        common_module.NodeExecutionError,
        match="Image was not recognized as a cached Midjourney image by Mutiny\\.",
    ) as exc_info:
        node.vary(torch.zeros((1, 1, 3), dtype=torch.float32), "Standard")

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_midjourney_variation_node_wraps_non_tile_image_failures(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Wrap the exact tile-required compatibility error at the node boundary."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyVariationNode"]
    common_module = sys.modules[f"{plugin_package.__name__}.nodes.common"]
    fake_runtime = fake_runtime_service_factory(
        variation_exception=RuntimeError(
            "Image was recognized, but Midjourney Variation requires a Midjourney grid tile."
        )
    )
    node = make_node(node_class, _runtime_service=fake_runtime)

    with pytest.raises(
        common_module.NodeExecutionError,
        match=(
            "Image was recognized, but Midjourney Variation requires a "
            "Midjourney grid tile\\."
        ),
    ) as exc_info:
        node.vary(torch.zeros((1, 1, 3), dtype=torch.float32), "Subtle")

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_midjourney_variation_node_wraps_runtime_submission_failures(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Wrap runtime submission failures at the variation node boundary."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyVariationNode"]
    common_module = sys.modules[f"{plugin_package.__name__}.nodes.common"]
    fake_runtime = fake_runtime_service_factory(
        variation_exception=RuntimeError("Task failed: Queue full")
    )
    node = make_node(node_class, _runtime_service=fake_runtime)

    with pytest.raises(
        common_module.NodeExecutionError,
        match="Task failed: Queue full",
    ) as exc_info:
        node.vary(torch.zeros((1, 1, 3), dtype=torch.float32), "Strong")

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_midjourney_variation_node_rejects_unsupported_mode_labels(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Wrap unsupported direct mode labels as one safe node-boundary failure."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyVariationNode"]
    common_module = sys.modules[f"{plugin_package.__name__}.nodes.common"]
    fake_runtime = fake_runtime_service_factory()
    node = make_node(node_class, _runtime_service=fake_runtime)

    with pytest.raises(
        common_module.NodeExecutionError,
        match="Unsupported Midjourney variation mode: 'Chaos'\\.",
    ) as exc_info:
        node.vary(torch.zeros((1, 1, 3), dtype=torch.float32), "Chaos")

    assert isinstance(exc_info.value.__cause__, ValueError)
    assert fake_runtime.variation_image_calls == []


def test_midjourney_vary_region_node_wraps_unrecognized_image_failures(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Wrap the exact image-recognition failure at the shared node boundary."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyVaryRegionNode"]
    common_module = sys.modules[f"{plugin_package.__name__}.nodes.common"]
    fake_runtime = fake_runtime_service_factory(
        vary_region_exception=RuntimeError(
            "Source image was not recognized as a cached Midjourney upscale."
        )
    )
    node = make_node(node_class, _runtime_service=fake_runtime)

    with pytest.raises(
        common_module.NodeExecutionError,
        match="Source image was not recognized as a cached Midjourney upscale\\.",
    ) as exc_info:
        node.vary_region(
            torch.zeros((1, 1, 3), dtype=torch.float32),
            torch.ones((1, 1), dtype=torch.float32),
            "add ivy",
        )

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_midjourney_vary_region_node_wraps_invalid_mask_failures(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Wrap invalid local mask encoding failures at the shared node boundary."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyVaryRegionNode"]
    common_module = sys.modules[f"{plugin_package.__name__}.nodes.common"]
    fake_runtime = fake_runtime_service_factory()
    node = make_node(node_class, _runtime_service=fake_runtime)

    with pytest.raises(
        common_module.NodeExecutionError,
        match="Mask input must contain exactly one mask\\.",
    ) as exc_info:
        node.vary_region(
            torch.zeros((1, 1, 3), dtype=torch.float32),
            torch.ones((2, 1, 1), dtype=torch.float32),
            "add ivy",
        )

    assert isinstance(exc_info.value.__cause__, ValueError)
    assert fake_runtime.vary_region_calls == []


def test_midjourney_vary_region_node_wraps_runtime_submission_failures(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Wrap runtime submission failures at the node boundary."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyVaryRegionNode"]
    common_module = sys.modules[f"{plugin_package.__name__}.nodes.common"]
    fake_runtime = fake_runtime_service_factory(
        vary_region_exception=RuntimeError("Task failed: Queue full")
    )
    node = make_node(node_class, _runtime_service=fake_runtime)

    with pytest.raises(
        common_module.NodeExecutionError,
        match="Task failed: Queue full",
    ) as exc_info:
        node.vary_region(
            torch.zeros((1, 1, 3), dtype=torch.float32),
            torch.ones((1, 1), dtype=torch.float32),
            "add ivy",
        )

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_midjourney_describe_node_wraps_runtime_submission_failures(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Wrap describe runtime submission failures at the shared node boundary."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyDescribeNode"]
    common_module = sys.modules[f"{plugin_package.__name__}.nodes.common"]
    fake_runtime = fake_runtime_service_factory(
        describe_exception=RuntimeError("Describe submit failed")
    )
    node = make_node(node_class, _runtime_service=fake_runtime)

    with pytest.raises(
        common_module.NodeExecutionError,
        match="Describe submit failed",
    ) as exc_info:
        node.describe(torch.zeros((1, 1, 3), dtype=torch.float32))

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_midjourney_describe_node_wraps_terminal_job_failures(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Wrap describe terminal job failures at the shared node boundary."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyDescribeNode"]
    common_module = sys.modules[f"{plugin_package.__name__}.nodes.common"]
    fake_runtime = fake_runtime_service_factory(
        describe_exception=RuntimeError("Task failed: Blocked by moderation")
    )
    node = make_node(node_class, _runtime_service=fake_runtime)

    with pytest.raises(
        common_module.NodeExecutionError,
        match="Task failed: Blocked by moderation",
    ) as exc_info:
        node.describe(torch.zeros((1, 1, 3), dtype=torch.float32))

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_midjourney_describe_node_wraps_missing_text_failures(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Wrap the exact missing-text runtime error at the shared node boundary."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyDescribeNode"]
    common_module = sys.modules[f"{plugin_package.__name__}.nodes.common"]
    fake_runtime = fake_runtime_service_factory(
        describe_exception=RuntimeError(
            "Describe completed without returning prompt text."
        )
    )
    node = make_node(node_class, _runtime_service=fake_runtime)

    with pytest.raises(
        common_module.NodeExecutionError,
        match="Describe completed without returning prompt text\\.",
    ) as exc_info:
        node.describe(torch.zeros((1, 1, 3), dtype=torch.float32))

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_midjourney_animate_node_wraps_runtime_submission_failures(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Wrap animate runtime submission failures at the shared node boundary."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyAnimateNode"]
    common_module = sys.modules[f"{plugin_package.__name__}.nodes.common"]
    fake_runtime = fake_runtime_service_factory(
        animate_exception=RuntimeError("Animate submit failed")
    )
    node = make_node(node_class, _runtime_service=fake_runtime)

    with pytest.raises(
        common_module.NodeExecutionError,
        match="Animate submit failed",
    ) as exc_info:
        node.animate(torch.zeros((1, 1, 3), dtype=torch.float32), "Low Motion")

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_midjourney_animate_node_wraps_terminal_job_failures(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Wrap animate terminal job failures at the shared node boundary."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyAnimateNode"]
    common_module = sys.modules[f"{plugin_package.__name__}.nodes.common"]
    fake_runtime = fake_runtime_service_factory(
        animate_exception=RuntimeError("Task failed: Blocked by moderation")
    )
    node = make_node(node_class, _runtime_service=fake_runtime)

    with pytest.raises(
        common_module.NodeExecutionError,
        match="Task failed: Blocked by moderation",
    ) as exc_info:
        node.animate(torch.zeros((1, 1, 3), dtype=torch.float32), "High Motion")

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_midjourney_animate_node_wraps_missing_video_failures(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Wrap the exact missing-video runtime error at the shared node boundary."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyAnimateNode"]
    common_module = sys.modules[f"{plugin_package.__name__}.nodes.common"]
    fake_runtime = fake_runtime_service_factory(
        animate_exception=RuntimeError(
            "Animate completed without returning a video URL."
        )
    )
    node = make_node(node_class, _runtime_service=fake_runtime)

    with pytest.raises(
        common_module.NodeExecutionError,
        match="Animate completed without returning a video URL\\.",
    ) as exc_info:
        node.animate(torch.zeros((1, 1, 3), dtype=torch.float32), "Low Motion")

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_midjourney_extend_node_wraps_runtime_submission_failures(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Wrap extend runtime submission failures at the shared node boundary."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyExtendNode"]
    common_module = sys.modules[f"{plugin_package.__name__}.nodes.common"]
    fake_runtime = fake_runtime_service_factory(
        extend_exception=RuntimeError(
            "Video was not recognized as a cached Midjourney video by Mutiny."
        )
    )
    node = make_node(node_class, _runtime_service=fake_runtime)

    with pytest.raises(
        common_module.NodeExecutionError,
        match="Video was not recognized as a cached Midjourney video by Mutiny\\.",
    ) as exc_info:
        node.extend(_FakeVideoInput(b"midjourney-video"), "Low Motion")

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_midjourney_extend_node_wraps_unsupported_motion_labels(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Wrap unsupported extend motion labels as one safe node-boundary failure."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyExtendNode"]
    common_module = sys.modules[f"{plugin_package.__name__}.nodes.common"]
    fake_runtime = fake_runtime_service_factory()
    node = make_node(node_class, _runtime_service=fake_runtime)

    with pytest.raises(
        common_module.NodeExecutionError,
        match="Unsupported Midjourney extend motion: 'Turbo'\\.",
    ) as exc_info:
        node.extend(_FakeVideoInput(b"midjourney-video"), "Turbo")

    assert isinstance(exc_info.value.__cause__, ValueError)
    assert fake_runtime.extend_calls == []
