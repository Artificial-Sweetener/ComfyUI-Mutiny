"""Test the Midjourney wrapped-image helper nodes."""

from __future__ import annotations

import sys

import pytest
import torch


def test_image_prompt_wrapper_returns_prompt_payload(plugin_package, make_node):
    """Return a wrapped prompt-image payload with an explicit image weight."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyImagePromptNode"]
    prompting_module = sys.modules[f"{plugin_package.__name__}.prompting"]
    node = make_node(node_class)

    (payload,) = node.build(torch.zeros((1, 1, 3), dtype=torch.float32), 2.0)

    assert isinstance(payload, prompting_module.MidjourneyPromptImagesPayload)
    assert payload.image_weight == 2.0


def test_style_reference_wrapper_returns_style_payload(plugin_package, make_node):
    """Return a wrapped style payload with explicit multipliers and version."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyStyleReferenceNode"]
    prompting_module = sys.modules[f"{plugin_package.__name__}.prompting"]
    node = make_node(node_class)

    (payload,) = node.build(
        torch.zeros((2, 1, 1, 3), dtype=torch.float32),
        style_weight=300,
        style_version="5",
        image_multipliers="2,1",
    )

    assert isinstance(payload, prompting_module.MidjourneyStyleReferencePayload)
    assert payload.style_weight == 300
    assert payload.style_version == 5
    assert payload.image_multipliers == (2.0, 1.0)


def test_character_reference_wrapper_returns_character_payload(
    plugin_package, make_node
):
    """Return a wrapped character payload with an explicit character weight."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyCharacterReferenceNode"]
    prompting_module = sys.modules[f"{plugin_package.__name__}.prompting"]
    node = make_node(node_class)

    (payload,) = node.build(torch.zeros((1, 1, 3), dtype=torch.float32), 80)

    assert isinstance(payload, prompting_module.MidjourneyCharacterReferencePayload)
    assert payload.character_weight == 80


def test_omni_reference_wrapper_returns_omni_payload(plugin_package, make_node):
    """Return a wrapped Omni payload for one single image."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyOmniReferenceNode"]
    prompting_module = sys.modules[f"{plugin_package.__name__}.prompting"]
    node = make_node(node_class)

    (payload,) = node.build(torch.zeros((1, 1, 3), dtype=torch.float32), 180)

    assert isinstance(payload, prompting_module.MidjourneyOmniReferencePayload)
    assert payload.omni_weight == 180


def test_omni_reference_wrapper_rejects_batches(plugin_package, make_node):
    """Reject multi-image batches for the Omni Reference wrapper."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyOmniReferenceNode"]
    node = make_node(node_class)

    with pytest.raises(ValueError, match="exactly one image"):
        node.build(torch.zeros((2, 1, 1, 3), dtype=torch.float32), 100)


def test_style_reference_wrapper_rejects_mismatched_multiplier_count(
    plugin_package, make_node
):
    """Reject multiplier lists that do not match the style-image batch size."""
    node_class = plugin_package.NODE_CLASS_MAPPINGS["MidjourneyStyleReferenceNode"]
    node = make_node(node_class)

    with pytest.raises(ValueError, match="must match the number of images"):
        node.build(
            torch.zeros((2, 1, 1, 3), dtype=torch.float32),
            image_multipliers="2",
        )


def test_wrapper_nodes_reject_invalid_ranges(plugin_package, make_node):
    """Reject invalid explicit weight and version values inside wrapper nodes."""
    image_prompt_node = make_node(
        plugin_package.NODE_CLASS_MAPPINGS["MidjourneyImagePromptNode"]
    )
    style_node = make_node(
        plugin_package.NODE_CLASS_MAPPINGS["MidjourneyStyleReferenceNode"]
    )
    character_node = make_node(
        plugin_package.NODE_CLASS_MAPPINGS["MidjourneyCharacterReferenceNode"]
    )
    omni_node = make_node(
        plugin_package.NODE_CLASS_MAPPINGS["MidjourneyOmniReferenceNode"]
    )

    with pytest.raises(ValueError, match="between 0 and 3"):
        image_prompt_node.build(torch.zeros((1, 1, 3), dtype=torch.float32), 4.0)
    with pytest.raises(ValueError, match="between 1 and 6"):
        style_node.build(
            torch.zeros((1, 1, 3), dtype=torch.float32),
            style_version="8",
        )
    with pytest.raises(ValueError, match="between 0 and 100"):
        character_node.build(torch.zeros((1, 1, 3), dtype=torch.float32), 200)
    with pytest.raises(ValueError, match="between 1 and 1000"):
        omni_node.build(torch.zeros((1, 1, 3), dtype=torch.float32), 0)
