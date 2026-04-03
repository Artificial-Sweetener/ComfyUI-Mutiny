"""Implement the image-driven Midjourney pan node."""

from __future__ import annotations

from ..runtime import MidjourneyPanDirection
from ..services import (
    build_comfy_progress_reporter,
    build_split_image_output,
    comfy_image_to_png_bytes,
)
from .common import NodeBoundaryContext, RuntimeBackedNode, execute_node_boundary


class MidjourneyPanNode(RuntimeBackedNode):
    """Resolve one recognized upscaled Midjourney image and return split pan tiles."""

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "pan"
    CATEGORY = "image"

    _DIRECTION_BY_LABEL = {
        "Left": MidjourneyPanDirection.LEFT,
        "Right": MidjourneyPanDirection.RIGHT,
        "Up": MidjourneyPanDirection.UP,
        "Down": MidjourneyPanDirection.DOWN,
    }

    @classmethod
    def INPUT_TYPES(cls):
        """Return the ComfyUI input declaration for the pan node."""
        return {
            "required": {
                "mj_image": ("IMAGE",),
                "direction": (
                    ["Left", "Right", "Up", "Down"],
                    {
                        "default": "Left",
                        "tooltip": (
                            "Midjourney Pan requires a recognized already-upscaled "
                            "Midjourney image."
                        ),
                    },
                ),
            }
        }

    def pan(self, mj_image, direction: str):
        """Resolve the input image through Mutiny and return split pan images."""

        def submit():
            """Encode the input image and delegate the selected pan action to runtime."""
            image_bytes = comfy_image_to_png_bytes(mj_image)
            runtime_direction = self._normalize_direction(direction)
            progress_reporter, _preview_image = build_comfy_progress_reporter()
            result = self._get_runtime_service().pan_image_and_wait(
                image_bytes,
                direction=runtime_direction,
                node_name=self.__class__.__name__,
                progress_reporter=progress_reporter,
            )
            return (build_split_image_output(result),)

        return execute_node_boundary(
            context=NodeBoundaryContext(
                node_name=self.__class__.__name__,
                action_name="pan",
            ),
            operation=submit,
        )

    @classmethod
    def _normalize_direction(cls, direction_label: str) -> MidjourneyPanDirection:
        """Map one UI direction label to the internal runtime direction enum."""
        try:
            return cls._DIRECTION_BY_LABEL[direction_label]
        except KeyError as exc:
            raise ValueError(
                f"Unsupported Midjourney pan direction: {direction_label!r}."
            ) from exc


__all__ = ["MidjourneyPanNode"]
