"""Test reusable prompt input spec behavior."""

from __future__ import annotations

import sys

import pytest


def test_build_input_types_preserves_required_and_optional_order(plugin_package):
    """Keep declarative input ordering stable for prompting definitions."""
    prompting_module = sys.modules[f"{plugin_package.__name__}.prompting"]
    input_types = prompting_module.build_input_types(
        prompting_module.NodeDefinition(
            bindings=(
                prompting_module.bind("prompt", required=True),
                prompting_module.bind("negative_prompt"),
                prompting_module.bind("stylize"),
            )
        )
    )

    assert list(input_types["required"]) == ["prompt"]
    assert list(input_types["optional"]) == ["negative_prompt", "stylize"]


def test_version_spec_normalizes_niji_prefix(plugin_package):
    """Render custom Niji versions without the broken legacy ``--v niji`` prefix."""
    specs_module = sys.modules[f"{plugin_package.__name__}.prompting.input_specs"]
    renderer = specs_module.INPUT_SPECS["version"].renderer

    assert renderer is not None
    assert renderer(" niji 5 ", {}) == " --niji 5"


def test_v7_quality_spec_maps_expected_flags(plugin_package):
    """Keep the v7 quality selector aligned with its prompt flags."""
    specs_module = sys.modules[f"{plugin_package.__name__}.prompting.input_specs"]
    renderer = specs_module.INPUT_SPECS["v7_quality"].renderer

    assert renderer is not None
    assert renderer("Draft Quality", {}) == " --draft"
    assert renderer("Default Quality", {}) == ""
    assert renderer("High Quality", {}) == " --q 2"
    assert renderer("Ultra Quality", {}) == " --q 4"


def test_shared_quality_spec_omits_default_flag(plugin_package):
    """Leave the shared default quality implicit while keeping explicit variants."""
    specs_module = sys.modules[f"{plugin_package.__name__}.prompting.input_specs"]
    renderer = specs_module.INPUT_SPECS["quality"].renderer

    assert renderer is not None
    assert renderer("Draft Quality", {}) == " --q 0.5"
    assert renderer("Default Quality", {}) == ""
    assert renderer("High Quality", {}) == " --q 2"


def test_legacy_quality_spec_omits_default_flag(plugin_package):
    """Leave the legacy default quality implicit while preserving old variants."""
    specs_module = sys.modules[f"{plugin_package.__name__}.prompting.input_specs"]
    renderer = specs_module.INPUT_SPECS["quality_legacy"].renderer

    assert renderer is not None
    assert renderer("Bad Quality", {}) == " --q 0.25"
    assert renderer("Draft Quality", {}) == " --q 0.5"
    assert renderer("Default Quality", {}) == ""


def test_aspect_ratio_specs_omit_default_ratio_flag(plugin_package):
    """Render only non-default aspect-ratio flags across shared selectors."""
    specs_module = sys.modules[f"{plugin_package.__name__}.prompting.input_specs"]
    shared_renderer = specs_module.INPUT_SPECS["aspect_ratio"].renderer
    niji_renderer = specs_module.INPUT_SPECS["niji_aspect_ratio"].renderer

    assert shared_renderer is not None
    assert niji_renderer is not None
    assert shared_renderer("1:1", {}) == ""
    assert shared_renderer("16:9", {}) == " --ar 16:9"
    assert niji_renderer("1:1", {}) == ""
    assert niji_renderer("2:1", {}) == " --ar 2:1"


def test_stylize_spec_omits_default_flag(plugin_package):
    """Render only non-default long-form stylize values."""
    specs_module = sys.modules[f"{plugin_package.__name__}.prompting.input_specs"]
    renderer = specs_module.INPUT_SPECS["stylize"].renderer

    assert renderer is not None
    assert renderer(0, {}) == ""
    assert renderer(100, {}) == ""
    assert renderer(250, {}) == " --stylize 250"


def test_use_raw_spec_renders_raw_mode_flag(plugin_package):
    """Render the shared Raw Mode toggle as ``--raw`` for all supported nodes."""
    specs_module = sys.modules[f"{plugin_package.__name__}.prompting.input_specs"]
    renderer = specs_module.INPUT_SPECS["use_raw"].renderer

    assert renderer is not None
    assert renderer(True, {}) == " --raw"
    assert renderer(False, {}) == ""


def test_batch_spec_declares_comfyui_batch_defaults(plugin_package):
    """Expose the shared request batch control with the approved UI contract."""
    specs_module = sys.modules[f"{plugin_package.__name__}.prompting.input_specs"]
    batch_spec = specs_module.INPUT_SPECS["batch"]

    assert batch_spec.field_name == "batch"
    assert batch_spec.field_type == "INT"
    assert batch_spec.field_options["default"] == 4
    assert batch_spec.field_options["min"] == 4
    assert batch_spec.field_options["step"] == 4
    assert batch_spec.field_options["max"] == 160


@pytest.mark.parametrize(
    ("raw_value", "normalized_value"),
    [
        (3, 4),
        (4, 4),
        (5, 4),
        (7, 4),
        (8, 8),
        (15, 12),
        (160, 160),
        (161, 160),
    ],
)
def test_batch_spec_normalizes_to_supported_midjourney_grid_counts(
    plugin_package, raw_value, normalized_value
):
    """Clamp batch values into 4..160 and floor them to a multiple of four."""
    specs_module = sys.modules[f"{plugin_package.__name__}.prompting.input_specs"]
    normalizer = specs_module.INPUT_SPECS["batch"].normalizer

    assert normalizer is not None
    assert normalizer(raw_value, {}) == normalized_value


def test_batch_spec_tooltip_explains_grid_and_repeat_mapping(plugin_package):
    """Document the batch normalization and backend repeat mapping in the tooltip."""
    specs_module = sys.modules[f"{plugin_package.__name__}.prompting.input_specs"]
    tooltip = specs_module.INPUT_SPECS["batch"].field_options["tooltip"]

    assert "Total images to request" in tooltip
    assert "4-image grids" in tooltip
    assert "clamped to 4-160" in tooltip
    assert "rounded down to a multiple of 4" in tooltip
    assert "Midjourney --repeat" in tooltip


def test_wrapped_image_specs_use_union_input_types(plugin_package):
    """Expose raw IMAGE and wrapped-image payload types on the shared ports."""
    specs_module = sys.modules[f"{plugin_package.__name__}.prompting.input_specs"]

    assert specs_module.INPUT_SPECS["images"].field_type == "IMAGE,MJ_IMAGE_PROMPT"
    assert (
        specs_module.INPUT_SPECS["style_references"].field_type
        == "IMAGE,MJ_STYLE_REFERENCE"
    )
    assert (
        specs_module.INPUT_SPECS["character_references"].field_type
        == "IMAGE,MJ_CHARACTER_REFERENCE"
    )
    assert (
        specs_module.INPUT_SPECS["omni_reference"].field_type
        == "IMAGE,MJ_OMNI_REFERENCE"
    )


def test_personalization_controls_reject_conflicting_values(plugin_package):
    """Reject simultaneous bare and explicit personalization settings."""
    specs_module = sys.modules[f"{plugin_package.__name__}.prompting.input_specs"]
    validator = specs_module.INPUT_SPECS["use_personalization"].validator

    assert validator is not None
    with pytest.raises(ValueError, match="cannot both be set"):
        validator(
            True,
            {
                "use_personalization": True,
                "profile_code": "p123",
            },
        )
