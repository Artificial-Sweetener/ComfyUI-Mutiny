"""Test prompt assembly through the declarative prompting layer."""

from __future__ import annotations

import sys

import pytest
import torch


def test_custom_request_prompt_builder_fixes_version_spacing(plugin_package):
    """Build the custom request prompt with prompt text before version flags."""
    prompting_module = sys.modules[f"{plugin_package.__name__}.prompting"]
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyCustomRequest"]

    build_result = prompting_module.build_prompt(
        node_class.NODE_DEFINITION,
        {
            "version": "7",
            "prompt": "(cat:1.4)",
            "negative_prompt": "(dog:0.5)",
            "stylize": 100,
            "custom_args": "--raw",
            "chaos": 5,
            "aspect_ratio": "1:1",
            "batch": 8,
            "tile": True,
            "seed": 9,
            "translate_weights": True,
        },
    )

    assert build_result.prompt_text == (
        "cat::1.4 --v 7 --no dog::0.5 --raw --chaos 5 --repeat 2 --tile"
    )
    assert build_result.build_controls["translate_weights"] is True
    assert build_result.submission_controls == {
        "images": None,
        "style_references": None,
        "character_references": None,
        "omni_reference": None,
    }


def test_v7_prompt_builder_renders_wrapped_image_metadata(plugin_package):
    """Render explicit wrapped-image metadata while leaving uploaded URLs to Mutiny."""
    prompting_module = sys.modules[f"{plugin_package.__name__}.prompting"]
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyV7Request"]
    wrapped_prompt_images = prompting_module.MidjourneyPromptImagesPayload(
        images=torch.zeros((1, 1, 3), dtype=torch.float32),
        image_weight=1.5,
    )
    wrapped_style = prompting_module.MidjourneyStyleReferencePayload(
        images=torch.zeros((1, 1, 3), dtype=torch.float32),
        style_weight=0,
        style_version=5,
    )
    wrapped_omni = prompting_module.MidjourneyOmniReferencePayload(
        image=torch.zeros((1, 1, 3), dtype=torch.float32),
        omni_weight=321,
    )

    build_result = prompting_module.build_prompt(
        node_class.NODE_DEFINITION,
        {
            "prompt": "cat",
            "negative_prompt": "dog",
            "stylize": 250,
            "chaos": 7,
            "weird": 12,
            "style_references": wrapped_style,
            "use_personalization": False,
            "profile_code": "p123",
            "images": wrapped_prompt_images,
            "omni_reference": wrapped_omni,
            "aspect_ratio": "16:9",
            "quality": "High Quality",
            "exp": "5",
            "batch": 12,
            "tile": True,
            "seed": 42,
            "use_raw": True,
            "custom_args": "--stylize 900",
        },
    )

    assert build_result.prompt_text == (
        "cat --no dog --stylize 250 --chaos 7 --weird 12 --p p123 --ar 16:9"
        " --q 2 --exp 5 --repeat 3 --tile --raw --stylize 900"
        " --iw 1.5 --sw 0 --sv 5 --ow 321"
    )
    assert build_result.submission_controls["images"] is wrapped_prompt_images
    assert build_result.submission_controls["style_references"] is wrapped_style
    assert build_result.submission_controls["omni_reference"] is wrapped_omni
    assert "--sref" not in build_result.prompt_text
    assert "--oref" not in build_result.prompt_text


def test_v7_prompt_builder_renders_bare_personalization(plugin_package):
    """Render the bare default-personalization flag when explicitly enabled."""
    prompting_module = sys.modules[f"{plugin_package.__name__}.prompting"]
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyV7Request"]

    build_result = prompting_module.build_prompt(
        node_class.NODE_DEFINITION,
        {
            "prompt": "cat",
            "use_personalization": True,
            "profile_code": "",
            "quality": "Default Quality",
        },
    )

    assert build_result.prompt_text == "cat --p"


def test_v7_prompt_builder_sends_seed_only_when_explicitly_enabled(plugin_package):
    """Render ``--seed`` only when the explicit seed toggle is enabled."""
    prompting_module = sys.modules[f"{plugin_package.__name__}.prompting"]
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyV7Request"]

    build_result = prompting_module.build_prompt(
        node_class.NODE_DEFINITION,
        {
            "prompt": "cat",
            "seed": 42,
            "send_explicit_seed": True,
        },
    )

    assert build_result.prompt_text == "cat --seed 42"


def test_v7_prompt_builder_rejects_conflicting_personalization_controls(
    plugin_package,
):
    """Reject a simultaneous bare ``--p`` toggle and explicit profile code."""
    prompting_module = sys.modules[f"{plugin_package.__name__}.prompting"]
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyV7Request"]

    with pytest.raises(ValueError, match="cannot both be set"):
        prompting_module.build_prompt(
            node_class.NODE_DEFINITION,
            {
                "prompt": "cat",
                "use_personalization": True,
                "profile_code": "p123",
            },
        )


def test_v7_prompt_builder_skips_image_weight_for_plain_images(plugin_package):
    """Avoid rendering ``--iw`` when the request receives a plain IMAGE tensor."""
    prompting_module = sys.modules[f"{plugin_package.__name__}.prompting"]
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyV7Request"]

    build_result = prompting_module.build_prompt(
        node_class.NODE_DEFINITION,
        {
            "prompt": "cat",
            "images": torch.zeros((1, 1, 3), dtype=torch.float32),
            "quality": "Default Quality",
        },
    )

    assert "--iw" not in build_result.prompt_text
    assert "--q" not in build_result.prompt_text
    assert build_result.submission_controls["images"] is not None


def test_v7_prompt_builder_allows_manual_reference_flags_in_custom_args(plugin_package):
    """Preserve free-form reference flags entered through custom args."""
    prompting_module = sys.modules[f"{plugin_package.__name__}.prompting"]
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyV7Request"]

    build_result = prompting_module.build_prompt(
        node_class.NODE_DEFINITION,
        {
            "prompt": "cat",
            "quality": "Default Quality",
            "custom_args": "--sref https://example.invalid/style.png --oref https://example.invalid/subject.png",
        },
    )

    assert "--sref https://example.invalid/style.png" in build_result.prompt_text
    assert "--oref https://example.invalid/subject.png" in build_result.prompt_text
    assert "--q" not in build_result.prompt_text


def test_v7_prompt_builder_rejects_omni_reference_with_draft_or_ultra_quality(
    plugin_package,
):
    """Reject unsupported quality combinations for Omni Reference."""
    prompting_module = sys.modules[f"{plugin_package.__name__}.prompting"]
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyV7Request"]
    wrapped_omni = prompting_module.MidjourneyOmniReferencePayload(
        image=torch.zeros((1, 1, 3), dtype=torch.float32),
        omni_weight=100,
    )

    with pytest.raises(ValueError, match="Draft Quality"):
        prompting_module.build_prompt(
            node_class.NODE_DEFINITION,
            {
                "prompt": "cat",
                "omni_reference": wrapped_omni,
                "quality": "Draft Quality",
            },
        )

    with pytest.raises(ValueError, match="Ultra Quality"):
        prompting_module.build_prompt(
            node_class.NODE_DEFINITION,
            {
                "prompt": "cat",
                "omni_reference": wrapped_omni,
                "quality": "Ultra Quality",
            },
        )


def test_niji7_prompt_builder_appends_niji7_supported_flags(plugin_package):
    """Build the Niji 7 prompt surface without unsupported legacy controls."""
    prompting_module = sys.modules[f"{plugin_package.__name__}.prompting"]
    node_class = plugin_package.NODE_CLASS_MAPPINGS["Niji7Request"]
    wrapped_style = prompting_module.MidjourneyStyleReferencePayload(
        images=torch.zeros((1, 1, 3), dtype=torch.float32),
        style_weight=0,
        style_version=4,
    )

    build_result = prompting_module.build_prompt(
        node_class.NODE_DEFINITION,
        {
            "prompt": "cat",
            "negative_prompt": "dog",
            "stylize": 100,
            "chaos": 5,
            "weird": 20,
            "style_references": wrapped_style,
            "aspect_ratio": "2:1",
            "batch": 8,
            "tile": True,
            "seed": 8,
            "use_raw": True,
            "custom_args": "--chaos 9",
        },
    )

    assert build_result.prompt_text == (
        "cat --no dog --chaos 5 --weird 20 --ar 2:1"
        " --repeat 2 --tile --raw --chaos 9 --sw 0 --sv 4"
    )


@pytest.mark.parametrize(
    ("batch_value", "expected_fragment"),
    [
        (4, ""),
        (5, ""),
        (8, " --repeat 2"),
        (15, " --repeat 3"),
        (161, " --repeat 40"),
    ],
)
def test_batch_prompt_builder_maps_total_images_to_repeat_flags(
    plugin_package, batch_value, expected_fragment
):
    """Render backend repeat counts from normalized request-node batch sizes."""
    prompting_module = sys.modules[f"{plugin_package.__name__}.prompting"]
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyV7Request"]

    build_result = prompting_module.build_prompt(
        node_class.NODE_DEFINITION,
        {
            "prompt": "cat",
            "quality": "Default Quality",
            "batch": batch_value,
        },
    )

    assert build_result.values["batch"] in {4, 8, 12, 160}
    assert "--q" not in build_result.prompt_text
    if expected_fragment:
        assert expected_fragment in build_result.prompt_text
    else:
        assert "--repeat" not in build_result.prompt_text
