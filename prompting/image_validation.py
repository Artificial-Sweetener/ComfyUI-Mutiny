"""Validate image-input combinations against the Midjourney image-prompt spec."""

from __future__ import annotations

from typing import Mapping

from .input_specs import NodeDefinition
from .model_capabilities import resolve_image_prompt_capabilities
from .validators import coerce_int
from .wrapped_images import (
    count_wrapped_images,
    unwrap_character_references,
    unwrap_omni_reference,
    unwrap_prompt_images,
    unwrap_style_references,
)


def validate_image_prompting(
    *,
    node_definition: NodeDefinition,
    values: Mapping[str, object],
) -> None:
    """Validate image-input rules for one prompt-driven node execution."""
    capabilities = resolve_image_prompt_capabilities(
        node_definition.image_capability_target,
        values,
    )
    if capabilities is None:
        return

    prompt_text = str(values.get("prompt") or "").strip()
    prompt_image_count = count_wrapped_images(values.get("images"))
    style_image_count = count_wrapped_images(values.get("style_references"))
    character_image_count = count_wrapped_images(values.get("character_references"))
    omni_image_count = count_wrapped_images(values.get("omni_reference"))
    _prompt_images, image_weight = unwrap_prompt_images(values.get("images"))
    (
        _style_images,
        style_weight,
        style_version,
        style_multipliers,
    ) = unwrap_style_references(values.get("style_references"))
    _character_images, character_weight = unwrap_character_references(
        values.get("character_references")
    )
    _omni_image, omni_weight = unwrap_omni_reference(values.get("omni_reference"))
    quality = values.get("quality")

    if prompt_image_count:
        if not capabilities.supports_image_prompt:
            raise ValueError("This model does not support Midjourney image prompts.")
        if prompt_image_count == 1 and not prompt_text:
            raise ValueError(
                "A single Midjourney image prompt must be paired with text."
            )
        if prompt_image_count >= 2 and not prompt_text:
            if coerce_int(values.get("stylize")):
                raise ValueError(
                    "Image-only Midjourney prompts are not compatible with stylize."
                )
            if coerce_int(values.get("weird")):
                raise ValueError(
                    "Image-only Midjourney prompts are not compatible with weird."
                )

    if (
        prompt_image_count
        and image_weight is not None
        and not capabilities.supports_image_weight
    ):
        raise ValueError("This model does not support Midjourney image weight.")

    has_style_reference = style_image_count > 0
    if style_image_count and not capabilities.supports_style_reference:
        raise ValueError("This model does not support Midjourney style references.")
    if has_style_reference and not prompt_text:
        raise ValueError("Midjourney style references require a text prompt.")
    if style_weight is not None and not has_style_reference:
        raise ValueError("Style Reference weight requires style_references to be set.")
    if style_version is not None:
        if not capabilities.supports_style_reference_version:
            raise ValueError(
                "This model does not support Midjourney Style Reference versions."
            )
        max_version = capabilities.style_reference_version_max
        coerced_style_version = coerce_int(style_version)
        if (
            max_version is not None
            and coerced_style_version is not None
            and coerced_style_version > max_version
        ):
            raise ValueError(
                f"Style Reference version must be between 1 and {max_version} for this model."
            )
        if not has_style_reference:
            raise ValueError(
                "Style Reference version requires style_references to be set."
            )
    if style_multipliers and not style_image_count:
        raise ValueError(
            "Style Reference image multipliers require style_references to be set."
        )
    if style_multipliers and len(style_multipliers) != style_image_count:
        raise ValueError(
            "Style Reference image multipliers must match the number of style reference images."
        )

    if character_image_count:
        if not capabilities.supports_character_reference:
            raise ValueError(
                "This model does not support Midjourney character references."
            )
        if not prompt_text:
            raise ValueError("Midjourney character references require a text prompt.")
    if character_weight is not None and not character_image_count:
        raise ValueError(
            "Character Reference weight requires character_references to be set."
        )

    has_omni_reference = omni_image_count > 0
    if has_omni_reference and not capabilities.supports_omni_reference:
        raise ValueError("This model does not support Midjourney Omni Reference.")
    if has_omni_reference and not prompt_text:
        raise ValueError("Midjourney Omni Reference requires a text prompt.")
    if omni_image_count > 1:
        raise ValueError("Omni Reference accepts exactly one image.")
    if omni_weight is not None and not has_omni_reference:
        raise ValueError("Omni Reference weight requires omni_reference to be set.")
    if has_omni_reference and quality == "Draft Quality":
        raise ValueError(
            "Omni Reference is not supported with Draft Quality in Midjourney v7."
        )
    if has_omni_reference and quality == "Ultra Quality":
        raise ValueError(
            "Omni Reference is not supported with Ultra Quality in Midjourney v7."
        )


__all__ = ["validate_image_prompting"]
