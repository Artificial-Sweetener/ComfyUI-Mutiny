"""Test shared image-prompting validation rules."""

from __future__ import annotations

import sys

import pytest
import torch


def _one_image() -> torch.Tensor:
    """Return one deterministic IMAGE tensor."""
    return torch.zeros((1, 1, 3), dtype=torch.float32)


def _two_images() -> torch.Tensor:
    """Return a deterministic two-image batch tensor."""
    return torch.zeros((2, 1, 1, 3), dtype=torch.float32)


def test_v7_rejects_single_image_without_text(plugin_package):
    """Require text when only one Image Prompt image is attached."""
    prompting_module = sys.modules[f"{plugin_package.__name__}.prompting"]
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyV7Request"]

    with pytest.raises(ValueError, match="must be paired with text"):
        prompting_module.build_prompt(
            node_class.NODE_DEFINITION,
            {
                "prompt": "",
                "images": _one_image(),
                "stylize": 0,
                "quality": "Default Quality",
            },
        )


def test_v7_allows_two_image_prompt_images_without_text(plugin_package):
    """Allow image-only prompts when two or more Image Prompt images are present."""
    prompting_module = sys.modules[f"{plugin_package.__name__}.prompting"]
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyV7Request"]

    build_result = prompting_module.build_prompt(
        node_class.NODE_DEFINITION,
        {
            "prompt": "",
            "images": _two_images(),
            "stylize": 0,
            "quality": "Default Quality",
        },
    )

    assert build_result.submission_controls["images"] is not None


def test_v7_rejects_image_only_prompt_with_stylize(plugin_package):
    """Reject stylize on image-only prompts per the image prompt spec."""
    prompting_module = sys.modules[f"{plugin_package.__name__}.prompting"]
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyV7Request"]

    with pytest.raises(ValueError, match="not compatible with stylize"):
        prompting_module.build_prompt(
            node_class.NODE_DEFINITION,
            {
                "prompt": "",
                "images": _two_images(),
                "stylize": 100,
                "quality": "Default Quality",
            },
        )


def test_v6_rejects_style_reference_version_above_model_limit(plugin_package):
    """Reject wrapped style versions above the v6 style-reference ceiling."""
    prompting_module = sys.modules[f"{plugin_package.__name__}.prompting"]
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyV6Request"]
    wrapped_style = prompting_module.MidjourneyStyleReferencePayload(
        images=_one_image(),
        style_version=5,
    )

    with pytest.raises(ValueError, match="between 1 and 4"):
        prompting_module.build_prompt(
            node_class.NODE_DEFINITION,
            {
                "model": "Midjourney v6.1",
                "prompt": "cat",
                "style_references": wrapped_style,
                "aspect_ratio": "1:1",
                "quality": "Default Quality",
            },
        )


def test_v7_renders_wrapped_omni_weight_when_image_is_present(plugin_package):
    """Allow wrapped Omni metadata to render ``--ow`` when the image is present."""
    prompting_module = sys.modules[f"{plugin_package.__name__}.prompting"]
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyV7Request"]
    wrapped_omni = prompting_module.MidjourneyOmniReferencePayload(
        image=_one_image(),
        omni_weight=180,
    )

    build_result = prompting_module.build_prompt(
        node_class.NODE_DEFINITION,
        {
            "prompt": "cat",
            "omni_reference": wrapped_omni,
            "quality": "Default Quality",
        },
    )

    assert "--ow 180" in build_result.prompt_text


def test_v7_rejects_multi_image_omni_reference_batches(plugin_package):
    """Require exactly one attached Omni Reference image."""
    prompting_module = sys.modules[f"{plugin_package.__name__}.prompting"]
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyV7Request"]

    with pytest.raises(ValueError, match="exactly one image"):
        prompting_module.build_prompt(
            node_class.NODE_DEFINITION,
            {
                "prompt": "cat",
                "omni_reference": _two_images(),
                "quality": "Default Quality",
            },
        )


def test_niji7_rejects_wrapped_image_weight(plugin_package):
    """Reject image weight on models the local spec says do not support it."""
    prompting_module = sys.modules[f"{plugin_package.__name__}.prompting"]
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyCustomRequest"]
    wrapped_prompt_images = prompting_module.MidjourneyPromptImagesPayload(
        images=_one_image(),
        image_weight=2.0,
    )

    with pytest.raises(ValueError, match="does not support Midjourney image weight"):
        prompting_module.build_prompt(
            node_class.NODE_DEFINITION,
            {
                "version": "niji 7",
                "prompt": "cat",
                "images": wrapped_prompt_images,
            },
        )


def test_custom_niji7_rejects_omni_reference_images(plugin_package):
    """Reject attached Omni Reference images when the custom node targets Niji 7."""
    prompting_module = sys.modules[f"{plugin_package.__name__}.prompting"]
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyCustomRequest"]

    with pytest.raises(
        ValueError,
        match="This model does not support Midjourney Omni Reference\\.",
    ):
        prompting_module.build_prompt(
            node_class.NODE_DEFINITION,
            {
                "version": "niji 7",
                "prompt": "cat",
                "omni_reference": _one_image(),
            },
        )


def test_custom_niji7_allows_plain_prompt_images_without_weight(plugin_package):
    """Treat plain prompt-image tensors as no explicit image-weight override."""
    prompting_module = sys.modules[f"{plugin_package.__name__}.prompting"]
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyCustomRequest"]

    build_result = prompting_module.build_prompt(
        node_class.NODE_DEFINITION,
        {
            "version": "niji 7",
            "prompt": "cat",
            "images": _one_image(),
        },
    )

    assert "--iw" not in build_result.prompt_text
