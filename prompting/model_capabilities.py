"""Resolve image-prompting capability rules for each request-node surface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ImagePromptCapabilities:
    """Describe which image-input channels one model family supports."""

    supports_image_prompt: bool
    supports_image_weight: bool
    supports_style_reference: bool
    supports_style_reference_version: bool
    style_reference_version_max: int | None
    supports_character_reference: bool
    supports_omni_reference: bool


_CAPABILITIES_BY_TARGET: dict[str, ImagePromptCapabilities] = {
    "midjourney_v4": ImagePromptCapabilities(
        supports_image_prompt=True,
        supports_image_weight=True,
        supports_style_reference=False,
        supports_style_reference_version=False,
        style_reference_version_max=None,
        supports_character_reference=False,
        supports_omni_reference=False,
    ),
    "midjourney_v5": ImagePromptCapabilities(
        supports_image_prompt=True,
        supports_image_weight=True,
        supports_style_reference=False,
        supports_style_reference_version=False,
        style_reference_version_max=None,
        supports_character_reference=False,
        supports_omni_reference=False,
    ),
    "midjourney_v6": ImagePromptCapabilities(
        supports_image_prompt=True,
        supports_image_weight=True,
        supports_style_reference=True,
        supports_style_reference_version=True,
        style_reference_version_max=4,
        supports_character_reference=True,
        supports_omni_reference=False,
    ),
    "midjourney_v7": ImagePromptCapabilities(
        supports_image_prompt=True,
        supports_image_weight=True,
        supports_style_reference=True,
        supports_style_reference_version=True,
        style_reference_version_max=6,
        supports_character_reference=False,
        supports_omni_reference=True,
    ),
    "midjourney_v8_alpha": ImagePromptCapabilities(
        supports_image_prompt=False,
        supports_image_weight=False,
        supports_style_reference=True,
        supports_style_reference_version=False,
        style_reference_version_max=None,
        supports_character_reference=False,
        supports_omni_reference=False,
    ),
    "niji4": ImagePromptCapabilities(
        supports_image_prompt=True,
        supports_image_weight=True,
        supports_style_reference=False,
        supports_style_reference_version=False,
        style_reference_version_max=None,
        supports_character_reference=False,
        supports_omni_reference=False,
    ),
    "niji5": ImagePromptCapabilities(
        supports_image_prompt=True,
        supports_image_weight=False,
        supports_style_reference=False,
        supports_style_reference_version=False,
        style_reference_version_max=None,
        supports_character_reference=False,
        supports_omni_reference=False,
    ),
    "niji6": ImagePromptCapabilities(
        supports_image_prompt=True,
        supports_image_weight=True,
        supports_style_reference=True,
        supports_style_reference_version=True,
        style_reference_version_max=6,
        supports_character_reference=True,
        supports_omni_reference=False,
    ),
    "niji7": ImagePromptCapabilities(
        supports_image_prompt=True,
        supports_image_weight=False,
        supports_style_reference=True,
        supports_style_reference_version=True,
        style_reference_version_max=6,
        supports_character_reference=False,
        supports_omni_reference=False,
    ),
}


def resolve_image_prompt_capabilities(
    target: str | None,
    values: Mapping[str, object],
) -> ImagePromptCapabilities | None:
    """Return the image-prompting capabilities for one prompt-driven node."""
    if target is None:
        return None
    if target == "midjourney_custom":
        return _resolve_custom_midjourney_capabilities(values)
    return _CAPABILITIES_BY_TARGET[target]


def _resolve_custom_midjourney_capabilities(
    values: Mapping[str, object],
) -> ImagePromptCapabilities:
    """Resolve the advanced custom node from its entered version string."""
    version_text = str(values.get("version") or "").strip().lower()
    normalized = version_text.replace("midjourney", "").replace("mj", "").strip()
    normalized = " ".join(normalized.split())

    if normalized.startswith("niji"):
        if "7" in normalized:
            return _CAPABILITIES_BY_TARGET["niji7"]
        if "6" in normalized:
            return _CAPABILITIES_BY_TARGET["niji6"]
        if "5" in normalized:
            return _CAPABILITIES_BY_TARGET["niji5"]
        if "4" in normalized:
            return _CAPABILITIES_BY_TARGET["niji4"]
    elif normalized.startswith("8"):
        return _CAPABILITIES_BY_TARGET["midjourney_v8_alpha"]
    elif normalized.startswith("7"):
        return _CAPABILITIES_BY_TARGET["midjourney_v7"]
    elif normalized.startswith("6"):
        return _CAPABILITIES_BY_TARGET["midjourney_v6"]
    elif normalized.startswith("5"):
        return _CAPABILITIES_BY_TARGET["midjourney_v5"]
    elif normalized.startswith("4"):
        return _CAPABILITIES_BY_TARGET["midjourney_v4"]

    raise ValueError(
        "Unsupported custom Midjourney version for image prompting. "
        "Use MJ v4-v8 Alpha or Niji 4-7."
    )


__all__ = ["ImagePromptCapabilities", "resolve_image_prompt_capabilities"]
