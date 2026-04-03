"""Test reusable prompting validators."""

from __future__ import annotations

import sys

import pytest


def test_normalize_prompt_text_collapses_whitespace(plugin_package):
    """Keep prompt normalization stable for multiline input."""
    validators = sys.modules[f"{plugin_package.__name__}.prompting.validators"]
    assert validators.normalize_prompt_text("a\n\n b   c") == "a b c"


def test_translate_stable_diffusion_weights_translates_current_syntax(plugin_package):
    """Keep Stable Diffusion weight translation stable across the prompting layer."""
    validators = sys.modules[f"{plugin_package.__name__}.prompting.validators"]
    assert (
        validators.translate_stable_diffusion_weights("a (cat:1.4), b")
        == "a::1 cat::1.4, b::1"
    )


def test_translate_stable_diffusion_weights_skips_blank_groups(plugin_package):
    """Avoid rewriting malformed groups that the helper intentionally skips."""
    validators = sys.modules[f"{plugin_package.__name__}.prompting.validators"]
    assert validators.translate_stable_diffusion_weights("(:1.2)") == "(:1.2)"


def test_validate_v4_model_aspect_ratio_normalizes_valid_values(plugin_package):
    """Keep v4-compatible aspect ratios normalized to ``W:H`` output."""
    validators = sys.modules[f"{plugin_package.__name__}.prompting.validators"]
    assert (
        validators.validate_v4_model_aspect_ratio("Midjourney v4c", " 2 : 1 ") == "2:1"
    )


@pytest.mark.parametrize("value", ["bad", "0:1", "3:1"])
def test_validate_ratio_between_half_and_double_rejects_invalid_values(
    plugin_package,
    value,
):
    """Reject invalid ratios for Niji and other bounded-ratio surfaces."""
    validators = sys.modules[f"{plugin_package.__name__}.prompting.validators"]

    with pytest.raises(ValueError):
        validators.validate_ratio_between_half_and_double(value)
