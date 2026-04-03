"""Characterize the exported ComfyUI node surface."""

from __future__ import annotations

EXPECTED_NODE_ORDER = [
    "MidjourneyImagePromptNode",
    "MidjourneyStyleReferenceNode",
    "MidjourneyCharacterReferenceNode",
    "MidjourneyOmniReferenceNode",
    "MidjourneyDescribeNode",
    "MidjourneyAnimateNode",
    "MidjourneyExtendNode",
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
    "MidjourneyUpscaleNode",
    "MidjourneyPanNode",
    "MidjourneyZoomNode",
    "MidjourneyVariationNode",
    "MidjourneyVaryRegionNode",
]

EXPECTED_DISPLAY_NAMES = {
    "MidjourneyImagePromptNode": "Midjourney Image Prompt",
    "MidjourneyStyleReferenceNode": "Midjourney Style Reference",
    "MidjourneyCharacterReferenceNode": "Midjourney Character Reference",
    "MidjourneyOmniReferenceNode": "Midjourney Omni Reference",
    "MidjourneyDescribeNode": "Midjourney Describe",
    "MidjourneyAnimateNode": "Midjourney Animate",
    "MidjourneyExtendNode": "Midjourney Extend",
    "MidjourneyCustomRequest": "Midjourney Custom Request",
    "MidjourneyV4Request": "Midjourney v4 Request",
    "MidjourneyV5Request": "Midjourney v5 Request",
    "MidjourneyV6Request": "Midjourney v6 Request",
    "MidjourneyV7Request": "Midjourney v7 Request",
    "MidjourneyV8AlphaRequest": "Midjourney v8 Alpha Request",
    "Niji4Request": "Niji 4 Request",
    "Niji5Request": "Niji 5 Request",
    "Niji6Request": "Niji 6 Request",
    "Niji7Request": "Niji 7 Request",
    "MidjourneyUpscaleNode": "Midjourney Upscale",
    "MidjourneyPanNode": "Midjourney Pan",
    "MidjourneyZoomNode": "Midjourney Zoom",
    "MidjourneyVariationNode": "Midjourney Variation",
    "MidjourneyVaryRegionNode": "Midjourney Vary Region",
}

EXPECTED_WEB_DIRECTORY = "web"

EXPECTED_NODE_METADATA = {
    "MidjourneyImagePromptNode": {
        "required_order": ["image"],
        "optional_order": ["image_weight"],
        "return_types": ("MJ_IMAGE_PROMPT",),
        "return_names": ("image_prompt",),
        "function": "build",
        "category": "image",
    },
    "MidjourneyStyleReferenceNode": {
        "required_order": ["image"],
        "optional_order": ["style_weight", "style_version", "image_multipliers"],
        "return_types": ("MJ_STYLE_REFERENCE",),
        "return_names": ("style_reference",),
        "function": "build",
        "category": "image",
    },
    "MidjourneyCharacterReferenceNode": {
        "required_order": ["image"],
        "optional_order": ["character_weight"],
        "return_types": ("MJ_CHARACTER_REFERENCE",),
        "return_names": ("character_reference",),
        "function": "build",
        "category": "image",
    },
    "MidjourneyOmniReferenceNode": {
        "required_order": ["image"],
        "optional_order": ["omni_weight"],
        "return_types": ("MJ_OMNI_REFERENCE",),
        "return_names": ("omni_reference",),
        "function": "build",
        "category": "image",
    },
    "MidjourneyDescribeNode": {
        "required_order": ["image"],
        "optional_order": [],
        "return_types": ("STRING",),
        "return_names": ("prompt",),
        "function": "describe",
        "category": "image",
    },
    "MidjourneyAnimateNode": {
        "required_order": ["start_frame", "motion"],
        "optional_order": ["end_frame", "prompt", "negative_prompt", "batch_size"],
        "return_types": ("VIDEO",),
        "return_names": ("video",),
        "function": "animate",
        "category": "image",
    },
    "MidjourneyExtendNode": {
        "required_order": ["mj_video", "motion"],
        "optional_order": [],
        "return_types": ("VIDEO",),
        "return_names": ("video",),
        "function": "extend",
        "category": "image",
    },
    "MidjourneyCustomRequest": {
        "required_order": ["version", "prompt"],
        "optional_order": [
            "negative_prompt",
            "stylize",
            "custom_args",
            "chaos",
            "aspect_ratio",
            "batch",
            "tile",
            "seed",
            "images",
            "style_references",
            "character_references",
            "omni_reference",
            "translate_weights",
        ],
        "return_types": ("IMAGE",),
        "return_names": ("images",),
        "function": "generate",
        "category": "image",
    },
    "MidjourneyV4Request": {
        "required_order": ["model", "prompt"],
        "optional_order": [
            "negative_prompt",
            "stylize",
            "chaos",
            "aspect_ratio",
            "quality",
            "batch",
            "tile",
            "seed",
            "images",
            "translate_weights",
            "custom_args",
        ],
        "return_types": ("IMAGE",),
        "return_names": ("images",),
        "function": "generate",
        "category": "image",
    },
    "MidjourneyV5Request": {
        "required_order": ["model", "prompt"],
        "optional_order": [
            "negative_prompt",
            "stylize",
            "chaos",
            "weird",
            "aspect_ratio",
            "quality",
            "batch",
            "tile",
            "seed",
            "use_raw",
            "images",
            "translate_weights",
            "custom_args",
        ],
        "return_types": ("IMAGE",),
        "return_names": ("images",),
        "function": "generate",
        "category": "image",
    },
    "MidjourneyV6Request": {
        "required_order": ["model", "prompt"],
        "optional_order": [
            "negative_prompt",
            "stylize",
            "chaos",
            "weird",
            "style_references",
            "character_references",
            "profile_code",
            "aspect_ratio",
            "quality",
            "batch",
            "tile",
            "seed",
            "use_raw",
            "images",
            "translate_weights",
            "custom_args",
        ],
        "return_types": ("IMAGE",),
        "return_names": ("images",),
        "function": "generate",
        "category": "image",
    },
    "MidjourneyV7Request": {
        "required_order": ["prompt"],
        "optional_order": [
            "negative_prompt",
            "stylize",
            "chaos",
            "weird",
            "style_references",
            "use_personalization",
            "profile_code",
            "images",
            "omni_reference",
            "aspect_ratio",
            "quality",
            "exp",
            "batch",
            "tile",
            "seed",
            "use_raw",
            "custom_args",
        ],
        "return_types": ("IMAGE",),
        "return_names": ("images",),
        "function": "generate",
        "category": "image",
    },
    "MidjourneyV8AlphaRequest": {
        "required_order": ["prompt"],
        "optional_order": [
            "negative_prompt",
            "style_references",
            "aspect_ratio",
            "batch",
            "seed",
            "custom_args",
        ],
        "return_types": ("IMAGE",),
        "return_names": ("images",),
        "function": "generate",
        "category": "image",
    },
    "Niji4Request": {
        "required_order": ["prompt"],
        "optional_order": [
            "negative_prompt",
            "stylize",
            "chaos",
            "weird",
            "aspect_ratio",
            "quality",
            "batch",
            "tile",
            "seed",
            "images",
            "translate_weights",
            "custom_args",
        ],
        "return_types": ("IMAGE",),
        "return_names": ("images",),
        "function": "generate",
        "category": "image",
    },
    "Niji5Request": {
        "required_order": ["prompt"],
        "optional_order": [
            "negative_prompt",
            "stylize",
            "chaos",
            "weird",
            "niji5_style",
            "aspect_ratio",
            "quality",
            "batch",
            "tile",
            "seed",
            "use_raw",
            "images",
            "translate_weights",
            "custom_args",
        ],
        "return_types": ("IMAGE",),
        "return_names": ("images",),
        "function": "generate",
        "category": "image",
    },
    "Niji6Request": {
        "required_order": ["prompt"],
        "optional_order": [
            "negative_prompt",
            "stylize",
            "chaos",
            "weird",
            "style_references",
            "character_references",
            "profile_code",
            "aspect_ratio",
            "quality",
            "batch",
            "tile",
            "seed",
            "use_raw",
            "images",
            "translate_weights",
            "custom_args",
        ],
        "return_types": ("IMAGE",),
        "return_names": ("images",),
        "function": "generate",
        "category": "image",
    },
    "Niji7Request": {
        "required_order": ["prompt"],
        "optional_order": [
            "negative_prompt",
            "stylize",
            "chaos",
            "weird",
            "style_references",
            "aspect_ratio",
            "batch",
            "tile",
            "seed",
            "use_raw",
            "images",
            "custom_args",
        ],
        "return_types": ("IMAGE",),
        "return_names": ("images",),
        "function": "generate",
        "category": "image",
    },
    "MidjourneyUpscaleNode": {
        "required_order": ["mj_image", "mode"],
        "optional_order": [],
        "return_types": ("IMAGE",),
        "return_names": ("image",),
        "function": "upscale",
        "category": "image",
    },
    "MidjourneyPanNode": {
        "required_order": ["mj_image", "direction"],
        "optional_order": [],
        "return_types": ("IMAGE",),
        "return_names": ("images",),
        "function": "pan",
        "category": "image",
    },
    "MidjourneyZoomNode": {
        "required_order": ["mj_image", "zoom_factor"],
        "optional_order": ["prompt"],
        "return_types": ("IMAGE",),
        "return_names": ("image",),
        "function": "zoom",
        "category": "image",
    },
    "MidjourneyVariationNode": {
        "required_order": ["mj_image", "mode"],
        "optional_order": [],
        "return_types": ("IMAGE",),
        "return_names": ("images",),
        "function": "vary",
        "category": "image",
    },
    "MidjourneyVaryRegionNode": {
        "required_order": ["mj_image", "mask", "prompt"],
        "optional_order": ["negative_prompt"],
        "return_types": ("IMAGE",),
        "return_names": ("images",),
        "function": "vary_region",
        "category": "image",
    },
}


def test_exported_node_mappings_remain_stable(plugin_package):
    """Keep the public node mapping order and keys stable."""
    assert list(plugin_package.NODE_CLASS_MAPPINGS) == EXPECTED_NODE_ORDER
    assert plugin_package.NODE_DISPLAY_NAME_MAPPINGS == EXPECTED_DISPLAY_NAMES
    assert plugin_package.WEB_DIRECTORY == EXPECTED_WEB_DIRECTORY


def test_exported_node_metadata_matches_current_surface(plugin_package):
    """Keep per-node metadata and `INPUT_TYPES` ordering stable."""
    for node_name, expected in EXPECTED_NODE_METADATA.items():
        node_class = plugin_package.NODE_CLASS_MAPPINGS[node_name]
        input_types = node_class.INPUT_TYPES()
        optional_fields = list(input_types.get("optional", {}))

        assert list(input_types.get("required", {})) == expected["required_order"]
        assert _is_subsequence(expected["optional_order"], optional_fields)
        assert node_class.RETURN_TYPES == expected["return_types"]
        assert (
            tuple(getattr(node_class, "RETURN_NAMES", ())) == expected["return_names"]
        )
        assert node_class.FUNCTION == expected["function"]
        assert node_class.CATEGORY == expected["category"]


def test_exported_string_inputs_stay_single_line(plugin_package):
    """Keep all shipped text inputs on the single-line ComfyUI control."""
    for node_class in plugin_package.NODE_CLASS_MAPPINGS.values():
        input_types = node_class.INPUT_TYPES()
        for section_name in ("required", "optional"):
            for field in input_types.get(section_name, {}).values():
                if not isinstance(field, tuple) or len(field) < 2:
                    continue
                field_type, field_options = field[0], field[1]
                if field_type != "STRING" or not isinstance(field_options, dict):
                    continue
                assert field_options.get("multiline") is not True


def _is_subsequence(expected: list[str], actual: list[str]) -> bool:
    """Return whether the expected fields appear in order within the actual list."""
    actual_iter = iter(actual)
    return all(field in actual_iter for field in expected)
