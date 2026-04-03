"""Implement the image-driven Midjourney variation-family node."""

from __future__ import annotations

from ..runtime import MidjourneyVariationMode
from ..services import (
    build_comfy_progress_reporter,
    build_split_image_output,
    comfy_image_to_png_bytes,
)
from .common import NodeBoundaryContext, RuntimeBackedNode, execute_node_boundary


class MidjourneyVariationNode(RuntimeBackedNode):
    """Resolve one recognized Midjourney tile and run the selected variation mode."""

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "vary"
    CATEGORY = "image"

    _MODE_BY_LABEL = {
        "Standard": MidjourneyVariationMode.STANDARD,
        "Subtle": MidjourneyVariationMode.SUBTLE,
        "Strong": MidjourneyVariationMode.STRONG,
    }

    @classmethod
    def INPUT_TYPES(cls):
        """Return the ComfyUI input declaration for the unified variation node."""
        return {
            "required": {
                "mj_image": ("IMAGE",),
                "mode": (
                    ["Standard", "Subtle", "Strong"],
                    {
                        "default": "Standard",
                        "tooltip": (
                            "All Midjourney Variation modes require a recognized "
                            "Midjourney grid tile."
                        ),
                    },
                ),
            },
        }

    def vary(self, mj_image, mode: str):
        """Resolve the input image through Mutiny and return the variation result."""

        def submit():
            """Encode the input image and delegate the selected action to runtime."""
            image_bytes = comfy_image_to_png_bytes(mj_image)
            runtime_mode = self._normalize_mode(mode)
            progress_reporter, _preview_image = build_comfy_progress_reporter()
            result = self._get_runtime_service().variation_image_and_wait(
                image_bytes,
                mode=runtime_mode,
                node_name=self.__class__.__name__,
                progress_reporter=progress_reporter,
            )
            return (build_split_image_output(result),)

        return execute_node_boundary(
            context=NodeBoundaryContext(
                node_name=self.__class__.__name__,
                action_name="vary",
            ),
            operation=submit,
        )

    @classmethod
    def _normalize_mode(cls, mode_label: str) -> MidjourneyVariationMode:
        """Map one UI label to the internal runtime variation enum."""
        try:
            return cls._MODE_BY_LABEL[mode_label]
        except KeyError as exc:
            raise ValueError(
                f"Unsupported Midjourney variation mode: {mode_label!r}."
            ) from exc


__all__ = ["MidjourneyVariationNode"]
