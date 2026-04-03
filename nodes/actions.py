"""Implement image-driven Midjourney upscale-family nodes."""

from __future__ import annotations

from ..runtime import MidjourneyUpscaleMode
from ..services import (
    build_comfy_progress_reporter,
    build_single_image_output,
    comfy_image_to_png_bytes,
)
from .common import NodeBoundaryContext, RuntimeBackedNode, execute_node_boundary


class MidjourneyUpscaleNode(RuntimeBackedNode):
    """Resolve one cached Midjourney image and run the selected upscale action."""

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "upscale"
    CATEGORY = "image"

    _MODE_BY_LABEL = {
        "Standard": MidjourneyUpscaleMode.STANDARD,
        "Subtle": MidjourneyUpscaleMode.SUBTLE,
        "Creative": MidjourneyUpscaleMode.CREATIVE,
    }

    @classmethod
    def INPUT_TYPES(cls):
        """Return the ComfyUI input declaration for the unified upscale node."""
        return {
            "required": {
                "mj_image": ("IMAGE",),
                "mode": (
                    ["Standard", "Subtle", "Creative"],
                    {
                        "default": "Standard",
                        "tooltip": (
                            "Standard requires a recognized Midjourney grid tile. "
                            "Subtle and Creative require a recognized already-upscaled Midjourney image."
                        ),
                    },
                ),
            }
        }

    def upscale(self, mj_image, mode):
        """Resolve the input image through Mutiny and return the final upscale."""

        def submit():
            """Encode the input image and delegate the selected action to runtime."""
            image_bytes = comfy_image_to_png_bytes(mj_image)
            runtime_mode = self._normalize_mode(mode)
            progress_reporter, _preview_image = build_comfy_progress_reporter()
            result = self._get_runtime_service().upscale_image_and_wait(
                image_bytes,
                mode=runtime_mode,
                node_name=self.__class__.__name__,
                progress_reporter=progress_reporter,
            )
            return (build_single_image_output(result),)

        return execute_node_boundary(
            context=NodeBoundaryContext(
                node_name=self.__class__.__name__,
                action_name="upscale",
            ),
            operation=submit,
        )

    @classmethod
    def _normalize_mode(cls, mode_label: str) -> MidjourneyUpscaleMode:
        """Map one UI label to the internal runtime mode enum."""
        try:
            return cls._MODE_BY_LABEL[mode_label]
        except KeyError as exc:
            raise ValueError(
                f"Unsupported Midjourney upscale mode: {mode_label!r}."
            ) from exc


__all__ = ["MidjourneyUpscaleNode"]
