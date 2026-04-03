"""Implement wrapper nodes that attach Midjourney image metadata to IMAGE tensors."""

from __future__ import annotations

import torch

from ..prompting.wrapped_images import (
    MidjourneyCharacterReferencePayload,
    MidjourneyOmniReferencePayload,
    MidjourneyPromptImagesPayload,
    MidjourneyStyleReferencePayload,
)


def _parse_optional_multiplier_text(multiplier_text: str) -> tuple[float, ...]:
    """Parse optional comma-separated style-reference multipliers."""
    text = str(multiplier_text or "").strip()
    if not text:
        return ()

    multipliers: list[float] = []
    for part in text.split(","):
        stripped = part.strip()
        if not stripped:
            raise ValueError(
                "Style Reference multipliers must be a comma-separated list of numbers."
            )
        try:
            multipliers.append(float(stripped))
        except ValueError as exc:
            raise ValueError(
                "Style Reference multipliers must be a comma-separated list of numbers."
            ) from exc
    return tuple(multipliers)


def _count_images(image: torch.Tensor) -> int:
    """Return the number of images represented by one Comfy IMAGE tensor."""
    if image.ndim == 3:
        return 1
    if image.ndim == 4:
        return int(image.shape[0])
    raise ValueError("Expected a ComfyUI IMAGE tensor.")


class MidjourneyImagePromptNode:
    """Wrap one IMAGE tensor with an optional Midjourney image-weight override."""

    RETURN_TYPES = ("MJ_IMAGE_PROMPT",)
    RETURN_NAMES = ("image_prompt",)
    FUNCTION = "build"
    CATEGORY = "image"

    @classmethod
    def INPUT_TYPES(cls):
        """Return the ComfyUI input declaration for the image prompt wrapper."""
        return {
            "required": {
                "image": ("IMAGE",),
            },
            "optional": {
                "image_weight": (
                    "FLOAT",
                    {
                        "default": 1.0,
                        "min": 0.0,
                        "max": 3.0,
                        "step": 0.05,
                        "tooltip": "Optional Midjourney image weight override (0-3). Leave at 1.0 for no explicit --iw flag.",
                    },
                ),
            },
        }

    def build(
        self,
        image: torch.Tensor,
        image_weight: float = 1.0,
    ) -> tuple[MidjourneyPromptImagesPayload]:
        """Return one wrapped prompt-image payload."""
        if not 0 <= float(image_weight) <= 3:
            raise ValueError("Image weight must be between 0 and 3.")
        explicit_weight = None if float(image_weight) == 1.0 else float(image_weight)
        return (
            MidjourneyPromptImagesPayload(
                images=image,
                image_weight=explicit_weight,
            ),
        )


class MidjourneyStyleReferenceNode:
    """Wrap one IMAGE tensor with optional Midjourney style-reference metadata."""

    RETURN_TYPES = ("MJ_STYLE_REFERENCE",)
    RETURN_NAMES = ("style_reference",)
    FUNCTION = "build"
    CATEGORY = "image"

    @classmethod
    def INPUT_TYPES(cls):
        """Return the ComfyUI input declaration for the style-reference wrapper."""
        return {
            "required": {
                "image": ("IMAGE",),
            },
            "optional": {
                "style_weight": (
                    "INT",
                    {
                        "default": 100,
                        "min": 0,
                        "max": 1000,
                        "step": 1,
                        "tooltip": "Optional Midjourney style weight override (0-1000). Leave at 100 for no explicit --sw flag.",
                    },
                ),
                "style_version": (
                    ["Default", "1", "2", "3", "4", "5", "6"],
                    {
                        "default": "Default",
                        "tooltip": "Optional Midjourney style reference version override. Default leaves --sv unset.",
                    },
                ),
                "image_multipliers": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "Optional comma-separated per-image multipliers matching the incoming image batch order.",
                    },
                ),
            },
        }

    def build(
        self,
        image: torch.Tensor,
        style_weight: int = 100,
        style_version: str = "Default",
        image_multipliers: str = "",
    ) -> tuple[MidjourneyStyleReferencePayload]:
        """Return one wrapped style-reference payload."""
        if not 0 <= int(style_weight) <= 1000:
            raise ValueError("Style Reference weight must be between 0 and 1000.")

        multipliers = _parse_optional_multiplier_text(image_multipliers)
        image_count = _count_images(image)
        if multipliers and len(multipliers) != image_count:
            raise ValueError(
                "Style Reference multipliers must match the number of images."
            )

        explicit_version = None
        normalized_version = str(style_version or "Default").strip()
        if normalized_version != "Default":
            explicit_version = int(normalized_version)
            if not 1 <= explicit_version <= 6:
                raise ValueError("Style Reference version must be between 1 and 6.")

        explicit_weight = None if int(style_weight) == 100 else int(style_weight)
        return (
            MidjourneyStyleReferencePayload(
                images=image,
                style_weight=explicit_weight,
                style_version=explicit_version,
                image_multipliers=multipliers,
            ),
        )


class MidjourneyCharacterReferenceNode:
    """Wrap one IMAGE tensor with an optional character-reference weight override."""

    RETURN_TYPES = ("MJ_CHARACTER_REFERENCE",)
    RETURN_NAMES = ("character_reference",)
    FUNCTION = "build"
    CATEGORY = "image"

    @classmethod
    def INPUT_TYPES(cls):
        """Return the ComfyUI input declaration for the character wrapper."""
        return {
            "required": {
                "image": ("IMAGE",),
            },
            "optional": {
                "character_weight": (
                    "INT",
                    {
                        "default": 100,
                        "min": 0,
                        "max": 100,
                        "step": 1,
                        "tooltip": "Optional Midjourney character weight override (0-100). Leave at 100 for no explicit --cw flag.",
                    },
                ),
            },
        }

    def build(
        self,
        image: torch.Tensor,
        character_weight: int = 100,
    ) -> tuple[MidjourneyCharacterReferencePayload]:
        """Return one wrapped character-reference payload."""
        if not 0 <= int(character_weight) <= 100:
            raise ValueError("Character Reference weight must be between 0 and 100.")
        explicit_weight = (
            None if int(character_weight) == 100 else int(character_weight)
        )
        return (
            MidjourneyCharacterReferencePayload(
                images=image,
                character_weight=explicit_weight,
            ),
        )


class MidjourneyOmniReferenceNode:
    """Wrap one single IMAGE tensor with an optional Omni weight override."""

    RETURN_TYPES = ("MJ_OMNI_REFERENCE",)
    RETURN_NAMES = ("omni_reference",)
    FUNCTION = "build"
    CATEGORY = "image"

    @classmethod
    def INPUT_TYPES(cls):
        """Return the ComfyUI input declaration for the Omni wrapper."""
        return {
            "required": {
                "image": ("IMAGE",),
            },
            "optional": {
                "omni_weight": (
                    "INT",
                    {
                        "default": 100,
                        "min": 1,
                        "max": 1000,
                        "step": 1,
                        "tooltip": "Optional Midjourney Omni weight override (1-1000). Leave at 100 for no explicit --ow flag.",
                    },
                ),
            },
        }

    def build(
        self,
        image: torch.Tensor,
        omni_weight: int = 100,
    ) -> tuple[MidjourneyOmniReferencePayload]:
        """Return one wrapped Omni Reference payload."""
        if not 1 <= int(omni_weight) <= 1000:
            raise ValueError("Omni Reference weight must be between 1 and 1000.")
        if _count_images(image) != 1:
            raise ValueError("Omni Reference accepts exactly one image.")
        explicit_weight = None if int(omni_weight) == 100 else int(omni_weight)
        return (
            MidjourneyOmniReferencePayload(
                image=image,
                omni_weight=explicit_weight,
            ),
        )


__all__ = [
    "MidjourneyCharacterReferenceNode",
    "MidjourneyImagePromptNode",
    "MidjourneyOmniReferenceNode",
    "MidjourneyStyleReferenceNode",
]
