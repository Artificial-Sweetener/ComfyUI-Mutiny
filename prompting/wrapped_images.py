"""Define typed wrapped-image payloads and shared coercion helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

import torch

from ..services.image_inputs import count_comfy_images


@dataclass(frozen=True)
class MidjourneyPromptImagesPayload:
    """Carry prompt images plus an optional explicit image-weight override."""

    images: torch.Tensor
    image_weight: float | None = None


@dataclass(frozen=True)
class MidjourneyStyleReferencePayload:
    """Carry style-reference images plus optional explicit style metadata."""

    images: torch.Tensor
    style_weight: int | None = None
    style_version: int | None = None
    image_multipliers: tuple[float, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class MidjourneyCharacterReferencePayload:
    """Carry character-reference images plus an optional weight override."""

    images: torch.Tensor
    character_weight: int | None = None


@dataclass(frozen=True)
class MidjourneyOmniReferencePayload:
    """Carry one Omni Reference image plus an optional weight override."""

    image: torch.Tensor
    omni_weight: int | None = None


def unwrap_prompt_images(
    value: object,
) -> tuple[torch.Tensor | None, float | None]:
    """Return prompt images and any explicit image-weight override."""
    if value is None:
        return None, None
    if isinstance(value, MidjourneyPromptImagesPayload):
        return value.images, value.image_weight
    if _is_image_tensor(value):
        return value, None
    raise ValueError("Expected a Midjourney prompt image payload or IMAGE tensor.")


def unwrap_style_references(
    value: object,
) -> tuple[torch.Tensor | None, int | None, int | None, tuple[float, ...]]:
    """Return style images plus optional explicit style-reference metadata."""
    if value is None:
        return None, None, None, ()
    if isinstance(value, MidjourneyStyleReferencePayload):
        return (
            value.images,
            value.style_weight,
            value.style_version,
            value.image_multipliers,
        )
    if _is_image_tensor(value):
        return value, None, None, ()
    raise ValueError("Expected a Midjourney style reference payload or IMAGE tensor.")


def unwrap_character_references(
    value: object,
) -> tuple[torch.Tensor | None, int | None]:
    """Return character-reference images plus any explicit character weight."""
    if value is None:
        return None, None
    if isinstance(value, MidjourneyCharacterReferencePayload):
        return value.images, value.character_weight
    if _is_image_tensor(value):
        return value, None
    raise ValueError(
        "Expected a Midjourney character reference payload or IMAGE tensor."
    )


def unwrap_omni_reference(value: object) -> tuple[torch.Tensor | None, int | None]:
    """Return the Omni Reference image plus any explicit Omni weight override."""
    if value is None:
        return None, None
    if isinstance(value, MidjourneyOmniReferencePayload):
        return value.image, value.omni_weight
    if _is_image_tensor(value):
        return value, None
    raise ValueError("Expected a Midjourney Omni Reference payload or IMAGE tensor.")


def count_wrapped_images(value: object) -> int:
    """Return the number of images represented by one raw or wrapped value."""
    if value is None:
        return 0
    if isinstance(value, MidjourneyPromptImagesPayload):
        return count_comfy_images(value.images)
    if isinstance(value, MidjourneyStyleReferencePayload):
        return count_comfy_images(value.images)
    if isinstance(value, MidjourneyCharacterReferencePayload):
        return count_comfy_images(value.images)
    if isinstance(value, MidjourneyOmniReferencePayload):
        return count_comfy_images(value.image)
    if _is_image_tensor(value):
        return count_comfy_images(value)
    raise ValueError("Expected a Midjourney image payload or IMAGE tensor.")


def render_wrapped_image_flags(values: Mapping[str, Any]) -> str:
    """Render explicit prompt flags carried by wrapped-image payload metadata."""
    flag_parts: list[str] = []

    _prompt_images, image_weight = unwrap_prompt_images(values.get("images"))
    if image_weight is not None:
        flag_parts.append(f" --iw {_format_numeric_value(image_weight)}")

    _style_images, style_weight, style_version, _multipliers = unwrap_style_references(
        values.get("style_references")
    )
    if style_weight is not None:
        flag_parts.append(f" --sw {style_weight}")
    if style_version is not None:
        flag_parts.append(f" --sv {style_version}")

    _character_images, character_weight = unwrap_character_references(
        values.get("character_references")
    )
    if character_weight is not None:
        flag_parts.append(f" --cw {character_weight}")

    _omni_image, omni_weight = unwrap_omni_reference(values.get("omni_reference"))
    if omni_weight is not None:
        flag_parts.append(f" --ow {omni_weight}")

    return "".join(flag_parts)


def _format_numeric_value(value: float) -> str:
    """Format one numeric prompt flag compactly for Midjourney syntax."""
    if float(value).is_integer():
        return str(int(value))
    return f"{value:g}"


def _is_image_tensor(value: object) -> bool:
    """Return whether the provided value is a torch IMAGE tensor."""
    return isinstance(value, torch.Tensor)


__all__ = [
    "MidjourneyCharacterReferencePayload",
    "MidjourneyOmniReferencePayload",
    "MidjourneyPromptImagesPayload",
    "MidjourneyStyleReferencePayload",
    "count_wrapped_images",
    "render_wrapped_image_flags",
    "unwrap_character_references",
    "unwrap_omni_reference",
    "unwrap_prompt_images",
    "unwrap_style_references",
]
