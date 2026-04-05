"""Characterize node execution behavior without touching the network boundary."""

from __future__ import annotations

import base64
import io
import sys

import numpy as np
import pytest
import torch
from PIL import Image


class _FakeVideoInput:
    """Provide a deterministic Comfy ``VIDEO``-like input for node tests."""

    def __init__(self, payload: bytes) -> None:
        """Store the encoded video payload returned by ``get_stream_source``."""
        self._payload = payload

    def get_stream_source(self) -> io.BytesIO:
        """Return the in-memory payload as a streamable source."""
        return io.BytesIO(self._payload)


GRID_NODE_NAMES = [
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

TRANSLATE_WEIGHT_EXPECTATIONS = [
    ("MidjourneyCustomRequest", True),
    ("MidjourneyV4Request", True),
    ("MidjourneyV5Request", True),
    ("MidjourneyV6Request", True),
    ("MidjourneyV7Request", False),
    ("MidjourneyV8AlphaRequest", False),
    ("Niji4Request", True),
    ("Niji5Request", True),
    ("Niji6Request", True),
    ("Niji7Request", False),
]


def invoke_grid_node(node_name, node):
    """Call a grid-producing node with the minimum current required arguments."""
    kwargs = {
        "prompt": "(cat:1.4)",
        "negative_prompt": "(dog:0.5)",
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
    raise AssertionError(f"Unhandled grid node: {node_name}")


@pytest.mark.parametrize("node_name", GRID_NODE_NAMES)
def test_grid_nodes_return_split_batches(
    plugin_package, make_node, fake_runtime_service_factory, node_name
):
    """Keep all grid-producing request nodes on the canonical split batch output."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS[node_name]
    fake_runtime = fake_runtime_service_factory()
    node = make_node(node_class, _runtime_service=fake_runtime)

    (image,) = invoke_grid_node(node_name, node)

    assert tuple(image.shape) == (4, 2, 2, 3)


@pytest.mark.parametrize(
    ("node_name", "expect_translation"), TRANSLATE_WEIGHT_EXPECTATIONS
)
def test_translate_weights_behavior_matches_current_nodes(
    plugin_package,
    make_node,
    fake_runtime_service_factory,
    node_name,
    expect_translation,
):
    """Keep weight translation enabled only on nodes that still expose the control."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS[node_name]
    fake_runtime = fake_runtime_service_factory()
    node = make_node(node_class, _runtime_service=fake_runtime)

    invoke_grid_node(node_name, node)
    prompt = fake_runtime.imagine_calls[0]["prompt_text"]

    if expect_translation:
        assert "cat::1.4" in prompt
        assert "dog::0.5" in prompt
    else:
        assert "(cat:1.4)" in prompt
        assert "(dog:0.5)" in prompt


def test_midjourney_custom_request_places_version_after_prompt_text(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Keep the custom request prompt shape fixed after the Phase 2 refactor."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyCustomRequest"]
    fake_runtime = fake_runtime_service_factory()
    node = make_node(node_class, _runtime_service=fake_runtime)

    invoke_grid_node("MidjourneyCustomRequest", node)

    assert (
        fake_runtime.imagine_calls[0]["prompt_text"] == "cat::1.4 --v 7 --no dog::0.5"
    )


@pytest.mark.parametrize(
    ("batch_value", "expected_repeat_fragment"),
    [
        (5, None),
        (15, "--repeat 3"),
        (161, "--repeat 40"),
    ],
)
def test_request_nodes_normalize_batch_before_prompt_submission(
    plugin_package,
    make_node,
    fake_runtime_service_factory,
    batch_value,
    expected_repeat_fragment,
):
    """Normalize request batch counts before rendering backend repeat flags."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyV7Request"]
    fake_runtime = fake_runtime_service_factory()
    node = make_node(node_class, _runtime_service=fake_runtime)

    node.generate(prompt="cat", batch=batch_value)

    prompt_text = fake_runtime.imagine_calls[0]["prompt_text"]
    if expected_repeat_fragment is None:
        assert "--repeat" not in prompt_text
    else:
        assert expected_repeat_fragment in prompt_text


def test_nodes_resolve_runtime_service_per_execution(
    plugin_package, fake_runtime_service_factory, monkeypatch
):
    """Resolve the shared runtime on each execution instead of caching it on the node."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyV7Request"]
    common_module = sys.modules[f"{plugin_package.__name__}.nodes.common"]
    first_runtime = fake_runtime_service_factory(generated_job_id="job-1")
    second_runtime = fake_runtime_service_factory(generated_job_id="job-2")
    runtimes = [first_runtime, second_runtime]
    node = node_class()

    monkeypatch.setattr(common_module, "get_runtime_service", lambda: runtimes.pop(0))

    first_result = node.generate(prompt="cat")
    second_result = node.generate(prompt="dog")

    assert len(first_result) == 1
    assert len(second_result) == 1
    assert len(first_runtime.imagine_calls) == 1
    assert len(second_runtime.imagine_calls) == 1


def test_midjourney_v7_node_submits_prompt_images_through_runtime(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Encode wrapped prompt-image payloads into the structured runtime image payload."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyV7Request"]
    prompting_module = sys.modules[f"{plugin_package.__name__}.prompting"]
    fake_runtime = fake_runtime_service_factory()
    node = make_node(node_class, _runtime_service=fake_runtime)
    wrapped_images = prompting_module.MidjourneyPromptImagesPayload(
        images=torch.tensor(
            [[[[0.0, 0.5, 1.0], [1.0, 0.5, 0.0]]]],
            dtype=torch.float32,
        ),
        image_weight=2.0,
    )

    node.generate(
        prompt="cat",
        images=wrapped_images,
    )

    assert fake_runtime.imagine_calls[0]["prompt_text"] == "cat --iw 2 --v 7"
    image_inputs = fake_runtime.imagine_calls[0]["image_inputs"]
    assert image_inputs is not None
    assert len(image_inputs.prompt_images) == 1
    assert image_inputs.prompt_images[0].startswith("data:image/png;base64,")


def test_midjourney_v7_node_sends_seed_only_when_explicitly_enabled(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Submit ``--seed`` only when the explicit seed toggle is enabled."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyV7Request"]
    fake_runtime = fake_runtime_service_factory()
    node = make_node(node_class, _runtime_service=fake_runtime)

    node.generate(
        prompt="cat",
        seed=42,
        send_explicit_seed=True,
    )

    assert fake_runtime.imagine_calls[0]["prompt_text"] == "cat --seed 42 --v 7"


def test_niji6_node_submits_batched_images_through_runtime(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Encode batched request images into one runtime payload entry per image."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["Niji6Request"]
    fake_runtime = fake_runtime_service_factory()
    node = make_node(node_class, _runtime_service=fake_runtime)
    request_images = torch.tensor(
        [
            [[[0.0, 0.5, 1.0], [1.0, 0.5, 0.0]]],
            [[[0.25, 0.0, 0.5], [0.0, 1.0, 0.25]]],
        ],
        dtype=torch.float32,
    )

    node.generate(
        prompt="cat",
        aspect_ratio="2:1",
        translate_weights=True,
        images=request_images,
    )

    image_inputs = fake_runtime.imagine_calls[0]["image_inputs"]
    assert image_inputs is not None
    assert len(image_inputs.prompt_images) == 2
    assert all(
        data_url.startswith("data:image/png;base64,")
        for data_url in image_inputs.prompt_images
    )


def test_midjourney_v6_node_submits_image_based_style_and_character_references(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Forward style and character reference images through the shared runtime path."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyV6Request"]
    prompting_module = sys.modules[f"{plugin_package.__name__}.prompting"]
    fake_runtime = fake_runtime_service_factory()
    node = make_node(node_class, _runtime_service=fake_runtime)
    style_images = prompting_module.MidjourneyStyleReferencePayload(
        images=torch.zeros((2, 1, 1, 3), dtype=torch.float32),
        style_weight=300,
        image_multipliers=(2.0, 1.0),
    )
    character_images = prompting_module.MidjourneyCharacterReferencePayload(
        images=torch.zeros((1, 1, 3), dtype=torch.float32),
        character_weight=80,
    )

    node.generate(
        model="Midjourney v6.1",
        prompt="cat",
        aspect_ratio="1:1",
        quality="Default Quality",
        style_references=style_images,
        character_references=character_images,
    )

    image_inputs = fake_runtime.imagine_calls[0]["image_inputs"]
    assert image_inputs is not None
    assert len(image_inputs.style_reference_images) == 2
    assert image_inputs.style_reference_multipliers == (2.0, 1.0)
    assert len(image_inputs.character_reference_images) == 1


def test_midjourney_v7_node_submits_attached_omni_reference_images(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Forward one attached Omni Reference image through the shared runtime path."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyV7Request"]
    prompting_module = sys.modules[f"{plugin_package.__name__}.prompting"]
    fake_runtime = fake_runtime_service_factory()
    node = make_node(node_class, _runtime_service=fake_runtime)

    node.generate(
        prompt="cat",
        omni_reference=prompting_module.MidjourneyOmniReferencePayload(
            image=torch.zeros((1, 1, 3), dtype=torch.float32),
            omni_weight=180,
        ),
        quality="Default Quality",
    )

    image_inputs = fake_runtime.imagine_calls[0]["image_inputs"]
    assert image_inputs is not None
    assert image_inputs.omni_reference_image is not None
    assert image_inputs.omni_reference_image.startswith("data:image/png;base64,")


def test_custom_niji7_node_rejects_omni_reference_inputs(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Wrap the shared Niji 7 Omni rejection at the custom node boundary."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyCustomRequest"]
    common_module = sys.modules[f"{plugin_package.__name__}.nodes.common"]
    prompting_module = sys.modules[f"{plugin_package.__name__}.prompting"]
    fake_runtime = fake_runtime_service_factory()
    node = make_node(node_class, _runtime_service=fake_runtime)

    with pytest.raises(
        common_module.NodeExecutionError,
        match="This model does not support Midjourney Omni Reference\\.",
    ) as exc_info:
        node.generate(
            version="niji 7",
            prompt="cat",
            omni_reference=prompting_module.MidjourneyOmniReferencePayload(
                image=torch.zeros((1, 1, 3), dtype=torch.float32),
                omni_weight=100,
            ),
        )

    assert isinstance(exc_info.value.__cause__, ValueError)
    assert fake_runtime.imagine_calls == []


def test_midjourney_image_upscale_node_returns_single_image_batch(
    plugin_package, make_node, sample_single_image, fake_runtime_service_factory
):
    """Return one single-image batch from the image-driven upscale node."""
    runtime_module = sys.modules[f"{plugin_package.__name__}.runtime"]
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyUpscaleNode"]
    fake_runtime = fake_runtime_service_factory(generated_image=sample_single_image)
    node = make_node(node_class, _runtime_service=fake_runtime)
    mj_image = torch.from_numpy(sample_single_image.astype("float32") / 255.0)

    (image,) = node.upscale(mj_image, "Creative")

    assert tuple(image.shape) == (1, 2, 2, 3)
    assert len(fake_runtime.upscale_image_calls) == 1
    assert fake_runtime.upscale_image_calls[0]["node_name"] == "MidjourneyUpscaleNode"
    assert (
        fake_runtime.upscale_image_calls[0]["mode"]
        is runtime_module.MidjourneyUpscaleMode.CREATIVE
    )
    assert fake_runtime.upscale_image_calls[0]["progress_reporter"] is not None
    encoded_image = Image.open(
        io.BytesIO(fake_runtime.upscale_image_calls[0]["image_bytes"])
    ).convert("RGB")
    assert encoded_image.size == (2, 2)


def test_midjourney_image_upscale_node_reports_progress_through_comfy_preview(
    plugin_package, make_node, sample_single_image, fake_runtime_service_factory
):
    """Pass a progress reporter into the image-driven runtime path."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyUpscaleNode"]
    plugin_loader_module = sys.modules["support.plugin_loader"]
    fake_runtime = fake_runtime_service_factory(
        generated_image=sample_single_image,
        progress_updates=[("75%", sample_single_image)],
    )
    node = make_node(node_class, _runtime_service=fake_runtime)
    mj_image = torch.from_numpy(sample_single_image.astype("float32") / 255.0)

    node.upscale(mj_image, "Standard")

    progress_bar = plugin_loader_module.RecordingProgressBar.instances[-1]
    assert progress_bar.calls
    assert progress_bar.calls[-1][0] == 75
    assert progress_bar.calls[-1][2] is not None


def test_midjourney_pan_node_returns_split_image_batch(
    plugin_package, make_node, sample_single_image, fake_runtime_service_factory
):
    """Return one split four-image batch from the image-driven pan node."""
    runtime_module = sys.modules[f"{plugin_package.__name__}.runtime"]
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyPanNode"]
    fake_runtime = fake_runtime_service_factory(generated_image=sample_single_image)
    node = make_node(node_class, _runtime_service=fake_runtime)
    mj_image = torch.from_numpy(sample_single_image.astype("float32") / 255.0)

    (image,) = node.pan(mj_image, "Up")

    assert tuple(image.shape) == (4, 1, 1, 3)
    assert len(fake_runtime.pan_image_calls) == 1
    assert fake_runtime.pan_image_calls[0]["node_name"] == "MidjourneyPanNode"
    assert (
        fake_runtime.pan_image_calls[0]["direction"]
        is runtime_module.MidjourneyPanDirection.UP
    )
    assert fake_runtime.pan_image_calls[0]["progress_reporter"] is not None


def test_midjourney_pan_node_encodes_image_before_runtime_submission(
    plugin_package, make_node, sample_single_image, fake_runtime_service_factory
):
    """Encode the pan source image into PNG bytes before runtime submission."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyPanNode"]
    fake_runtime = fake_runtime_service_factory(generated_image=sample_single_image)
    node = make_node(node_class, _runtime_service=fake_runtime)
    mj_image = torch.from_numpy(sample_single_image.astype("float32") / 255.0)

    node.pan(mj_image, "Left")

    encoded_image = Image.open(
        io.BytesIO(fake_runtime.pan_image_calls[0]["image_bytes"])
    ).convert("RGB")
    assert encoded_image.size == (2, 2)


def test_midjourney_pan_node_reports_progress_through_comfy_preview(
    plugin_package, make_node, sample_single_image, fake_runtime_service_factory
):
    """Pass a progress reporter into the image-driven pan runtime path."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyPanNode"]
    plugin_loader_module = sys.modules["support.plugin_loader"]
    fake_runtime = fake_runtime_service_factory(
        generated_image=sample_single_image,
        progress_updates=[("55%", sample_single_image)],
    )
    node = make_node(node_class, _runtime_service=fake_runtime)
    mj_image = torch.from_numpy(sample_single_image.astype("float32") / 255.0)

    node.pan(mj_image, "Right")

    progress_bar = plugin_loader_module.RecordingProgressBar.instances[-1]
    assert progress_bar.calls
    assert progress_bar.calls[-1][0] == 55
    assert progress_bar.calls[-1][2] is not None


def test_midjourney_zoom_node_returns_single_image_batch(
    plugin_package, make_node, sample_single_image, fake_runtime_service_factory
):
    """Return one single-image batch from the image-driven zoom node."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyZoomNode"]
    fake_runtime = fake_runtime_service_factory(generated_image=sample_single_image)
    node = make_node(node_class, _runtime_service=fake_runtime)
    mj_image = torch.from_numpy(sample_single_image.astype("float32") / 255.0)

    (image,) = node.zoom(mj_image, 1.24, "tight crop")

    assert tuple(image.shape) == (1, 2, 2, 3)
    assert len(fake_runtime.zoom_image_calls) == 1
    assert fake_runtime.zoom_image_calls[0]["node_name"] == "MidjourneyZoomNode"
    assert fake_runtime.zoom_image_calls[0]["zoom_factor"] == 1.24
    assert fake_runtime.zoom_image_calls[0]["prompt_text"] == "tight crop"
    assert fake_runtime.zoom_image_calls[0]["progress_reporter"] is not None


def test_midjourney_zoom_node_encodes_image_before_runtime_submission(
    plugin_package, make_node, sample_single_image, fake_runtime_service_factory
):
    """Encode the zoom source image into PNG bytes before runtime submission."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyZoomNode"]
    fake_runtime = fake_runtime_service_factory(generated_image=sample_single_image)
    node = make_node(node_class, _runtime_service=fake_runtime)
    mj_image = torch.from_numpy(sample_single_image.astype("float32") / 255.0)

    node.zoom(mj_image, 1.5)

    encoded_image = Image.open(
        io.BytesIO(fake_runtime.zoom_image_calls[0]["image_bytes"])
    ).convert("RGB")
    assert encoded_image.size == (2, 2)


def test_midjourney_zoom_node_reports_progress_through_comfy_preview(
    plugin_package, make_node, sample_single_image, fake_runtime_service_factory
):
    """Pass a progress reporter into the image-driven zoom runtime path."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyZoomNode"]
    plugin_loader_module = sys.modules["support.plugin_loader"]
    fake_runtime = fake_runtime_service_factory(
        generated_image=sample_single_image,
        progress_updates=[("65%", sample_single_image)],
    )
    node = make_node(node_class, _runtime_service=fake_runtime)
    mj_image = torch.from_numpy(sample_single_image.astype("float32") / 255.0)

    node.zoom(mj_image, 2.0)

    progress_bar = plugin_loader_module.RecordingProgressBar.instances[-1]
    assert progress_bar.calls
    assert progress_bar.calls[-1][0] == 65
    assert progress_bar.calls[-1][2] is not None


def test_midjourney_variation_node_returns_split_images_by_default(
    plugin_package, make_node, sample_grid_image, fake_runtime_service_factory
):
    """Return a four-image batch from the variation node."""
    runtime_module = sys.modules[f"{plugin_package.__name__}.runtime"]
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyVariationNode"]
    fake_runtime = fake_runtime_service_factory()
    node = make_node(node_class, _runtime_service=fake_runtime)
    mj_image = torch.from_numpy(sample_grid_image.astype("float32") / 255.0)

    (image,) = node.vary(mj_image, "Strong")

    assert tuple(image.shape) == (4, 2, 2, 3)
    assert len(fake_runtime.variation_image_calls) == 1
    assert (
        fake_runtime.variation_image_calls[0]["node_name"] == "MidjourneyVariationNode"
    )
    assert (
        fake_runtime.variation_image_calls[0]["mode"]
        is runtime_module.MidjourneyVariationMode.STRONG
    )
    assert fake_runtime.variation_image_calls[0]["progress_reporter"] is not None


def test_midjourney_variation_node_encodes_image_before_runtime_submission(
    plugin_package, make_node, sample_grid_image, fake_runtime_service_factory
):
    """Encode the source image into PNG bytes before runtime submission."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyVariationNode"]
    fake_runtime = fake_runtime_service_factory(generated_image=sample_grid_image)
    node = make_node(node_class, _runtime_service=fake_runtime)
    mj_image = torch.from_numpy(sample_grid_image.astype("float32") / 255.0)

    node.vary(mj_image, "Subtle")

    encoded_image = Image.open(
        io.BytesIO(fake_runtime.variation_image_calls[0]["image_bytes"])
    ).convert("RGB")
    assert encoded_image.size == (4, 4)


def test_midjourney_variation_node_reports_progress_through_comfy_preview(
    plugin_package, make_node, sample_grid_image, fake_runtime_service_factory
):
    """Pass a progress reporter into the image-driven variation runtime path."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyVariationNode"]
    plugin_loader_module = sys.modules["support.plugin_loader"]
    fake_runtime = fake_runtime_service_factory(
        generated_image=sample_grid_image,
        progress_updates=[("40%", sample_grid_image)],
    )
    node = make_node(node_class, _runtime_service=fake_runtime)
    mj_image = torch.from_numpy(sample_grid_image.astype("float32") / 255.0)

    node.vary(mj_image, "Standard")

    progress_bar = plugin_loader_module.RecordingProgressBar.instances[-1]
    assert progress_bar.calls
    assert progress_bar.calls[-1][0] == 40
    assert progress_bar.calls[-1][2] is not None


def test_midjourney_vary_region_node_returns_split_images_by_default(
    plugin_package, make_node, sample_single_image, fake_runtime_service_factory
):
    """Return a four-image batch from Vary Region."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyVaryRegionNode"]
    fake_runtime = fake_runtime_service_factory()
    node = make_node(node_class, _runtime_service=fake_runtime)
    mj_image = torch.from_numpy(sample_single_image.astype("float32") / 255.0)
    mask = torch.tensor([[0.0, 1.0], [0.5, 0.25]], dtype=torch.float32)

    (image,) = node.vary_region(
        mj_image,
        mask,
        "  add\n ivy  ",
        "  fog \n crowd ",
    )

    assert tuple(image.shape) == (4, 2, 2, 3)
    assert len(fake_runtime.vary_region_calls) == 1
    assert fake_runtime.vary_region_calls[0]["node_name"] == "MidjourneyVaryRegionNode"
    assert fake_runtime.vary_region_calls[0]["prompt_text"] == "add ivy --no fog crowd"
    assert fake_runtime.vary_region_calls[0]["progress_reporter"] is not None


def test_midjourney_vary_region_node_encodes_image_and_mask_inputs(
    plugin_package, make_node, sample_single_image, fake_runtime_service_factory
):
    """Encode the source image and mask into data URLs before runtime submission."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyVaryRegionNode"]
    fake_runtime = fake_runtime_service_factory(generated_image=sample_single_image)
    node = make_node(node_class, _runtime_service=fake_runtime)
    mj_image = torch.from_numpy(sample_single_image.astype("float32") / 255.0)
    mask = torch.tensor([[0.0, 1.0], [1.0, 0.0]], dtype=torch.float32)

    node.vary_region(mj_image, mask, "replace sky")

    call = fake_runtime.vary_region_calls[0]
    assert call["source_image_data_url"].startswith("data:image/png;base64,")
    assert call["mask_data_url"].startswith("data:image/png;base64,")

    encoded_source = call["source_image_data_url"].split(",", maxsplit=1)[1]
    source_image = Image.open(io.BytesIO(base64.b64decode(encoded_source))).convert(
        "RGB"
    )
    assert source_image.size == (2, 2)

    encoded_mask = call["mask_data_url"].split(",", maxsplit=1)[1]
    mask_image = Image.open(io.BytesIO(base64.b64decode(encoded_mask))).convert("L")
    assert mask_image.size == (2, 2)
    assert np.array(mask_image).tolist() == [[0, 255], [255, 0]]


def test_midjourney_vary_region_node_reports_progress_through_comfy_preview(
    plugin_package, make_node, sample_single_image, fake_runtime_service_factory
):
    """Pass a progress reporter into the Vary Region runtime path."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyVaryRegionNode"]
    plugin_loader_module = sys.modules["support.plugin_loader"]
    fake_runtime = fake_runtime_service_factory(
        generated_image=sample_single_image,
        progress_updates=[("80%", sample_single_image)],
    )
    node = make_node(node_class, _runtime_service=fake_runtime)
    mj_image = torch.from_numpy(sample_single_image.astype("float32") / 255.0)
    mask = torch.ones((2, 2), dtype=torch.float32)

    node.vary_region(mj_image, mask, "add lanterns")

    progress_bar = plugin_loader_module.RecordingProgressBar.instances[-1]
    assert progress_bar.calls
    assert progress_bar.calls[-1][0] == 80
    assert progress_bar.calls[-1][2] is not None


def test_midjourney_describe_node_returns_prompt_text(
    plugin_package, make_node, sample_single_image, fake_runtime_service_factory
):
    """Return the described prompt text unchanged from the runtime result."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyDescribeNode"]
    fake_runtime = fake_runtime_service_factory(
        generated_image=sample_single_image,
        describe_text="described castle prompt",
    )
    node = make_node(node_class, _runtime_service=fake_runtime)
    image = torch.from_numpy(sample_single_image.astype("float32") / 255.0)

    (prompt_text,) = node.describe(image)

    assert prompt_text == "described castle prompt"
    assert len(fake_runtime.describe_calls) == 1
    assert fake_runtime.describe_calls[0]["node_name"] == "MidjourneyDescribeNode"
    assert fake_runtime.describe_calls[0]["progress_reporter"] is not None


def test_midjourney_describe_node_encodes_image_before_runtime_submission(
    plugin_package, make_node, sample_single_image, fake_runtime_service_factory
):
    """Encode the describe source image into a PNG data URL before runtime submission."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyDescribeNode"]
    fake_runtime = fake_runtime_service_factory(generated_image=sample_single_image)
    node = make_node(node_class, _runtime_service=fake_runtime)
    image = torch.from_numpy(sample_single_image.astype("float32") / 255.0)

    node.describe(image)

    encoded_image = fake_runtime.describe_calls[0]["image_data_url"]
    assert encoded_image.startswith("data:image/png;base64,")
    image_bytes = base64.b64decode(encoded_image.split(",", maxsplit=1)[1])
    decoded_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    assert decoded_image.size == (2, 2)


def test_midjourney_describe_node_reports_progress_through_comfy_preview(
    plugin_package, make_node, sample_single_image, fake_runtime_service_factory
):
    """Pass a progress reporter into the describe runtime path."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyDescribeNode"]
    plugin_loader_module = sys.modules["support.plugin_loader"]
    fake_runtime = fake_runtime_service_factory(
        generated_image=sample_single_image,
        progress_updates=[("33%", sample_single_image)],
    )
    node = make_node(node_class, _runtime_service=fake_runtime)
    image = torch.from_numpy(sample_single_image.astype("float32") / 255.0)

    node.describe(image)

    progress_bar = plugin_loader_module.RecordingProgressBar.instances[-1]
    assert progress_bar.calls
    assert progress_bar.calls[-1][0] == 33
    assert progress_bar.calls[-1][2] is not None


def test_midjourney_animate_node_returns_native_video_value(
    plugin_package, make_node, sample_single_image, fake_runtime_service_factory
):
    """Return the native video object unchanged from the runtime result."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyAnimateNode"]
    expected_video = object()
    fake_runtime = fake_runtime_service_factory(
        generated_image=sample_single_image,
        animate_video_value=expected_video,
    )
    node = make_node(node_class, _runtime_service=fake_runtime)
    image = torch.from_numpy(sample_single_image.astype("float32") / 255.0)

    (video_value,) = node.animate(image, "High Motion")

    assert video_value is expected_video
    assert len(fake_runtime.animate_calls) == 1
    assert fake_runtime.animate_calls[0]["node_name"] == "MidjourneyAnimateNode"
    assert fake_runtime.animate_calls[0]["progress_reporter"] is not None


def test_midjourney_animate_node_encodes_start_and_end_frames(
    plugin_package, make_node, sample_single_image, fake_runtime_service_factory
):
    """Encode animate frame inputs into PNG data URLs before runtime submission."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyAnimateNode"]
    fake_runtime = fake_runtime_service_factory(generated_image=sample_single_image)
    node = make_node(node_class, _runtime_service=fake_runtime)
    start_frame = torch.from_numpy(sample_single_image.astype("float32") / 255.0)
    end_frame = torch.from_numpy(sample_single_image.astype("float32") / 255.0)

    node.animate(
        start_frame,
        "Low Motion",
        end_frame=end_frame,
        prompt="camera push through fog",
        negative_prompt="traffic cones",
        batch_size="2",
    )

    call = fake_runtime.animate_calls[0]
    assert call["start_frame_data_url"].startswith("data:image/png;base64,")
    assert call["end_frame_data_url"].startswith("data:image/png;base64,")
    assert call["prompt_text"] == "camera push through fog --no traffic cones"
    assert getattr(call["motion"], "value", None) == "low"
    assert call["batch_size"] == 2


def test_midjourney_animate_node_reports_progress_through_comfy_preview(
    plugin_package, make_node, sample_single_image, fake_runtime_service_factory
):
    """Pass a progress reporter into the animate runtime path."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyAnimateNode"]
    plugin_loader_module = sys.modules["support.plugin_loader"]
    fake_runtime = fake_runtime_service_factory(
        generated_image=sample_single_image,
        progress_updates=[("45%", sample_single_image)],
    )
    node = make_node(node_class, _runtime_service=fake_runtime)
    image = torch.from_numpy(sample_single_image.astype("float32") / 255.0)

    node.animate(image, "Low Motion")

    progress_bar = plugin_loader_module.RecordingProgressBar.instances[-1]
    assert progress_bar.calls
    assert progress_bar.calls[-1][0] == 45
    assert progress_bar.calls[-1][2] is not None


def test_midjourney_extend_node_returns_native_video_value(
    plugin_package, make_node, fake_runtime_service_factory
):
    """Return the native video object unchanged from the runtime result."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyExtendNode"]
    expected_video = object()
    fake_runtime = fake_runtime_service_factory(animate_video_value=expected_video)
    node = make_node(node_class, _runtime_service=fake_runtime)

    (video_value,) = node.extend(_FakeVideoInput(b"midjourney-video"), "High Motion")

    assert video_value is expected_video
    assert len(fake_runtime.extend_calls) == 1
    assert fake_runtime.extend_calls[0]["video_bytes"] == b"midjourney-video"
    assert fake_runtime.extend_calls[0]["node_name"] == "MidjourneyExtendNode"
    assert getattr(fake_runtime.extend_calls[0]["motion"], "value", None) == "high"
    assert fake_runtime.extend_calls[0]["progress_reporter"] is not None


def test_midjourney_extend_node_reports_progress_through_comfy_preview(
    plugin_package, make_node, sample_single_image, fake_runtime_service_factory
):
    """Pass a progress reporter into the extend runtime path."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyExtendNode"]
    plugin_loader_module = sys.modules["support.plugin_loader"]
    fake_runtime = fake_runtime_service_factory(
        generated_image=sample_single_image,
        progress_updates=[("72%", sample_single_image)],
    )
    node = make_node(node_class, _runtime_service=fake_runtime)

    node.extend(_FakeVideoInput(b"midjourney-video"), "Low Motion")

    progress_bar = plugin_loader_module.RecordingProgressBar.instances[-1]
    assert progress_bar.calls
    assert progress_bar.calls[-1][0] == 72
    assert progress_bar.calls[-1][2] is not None
