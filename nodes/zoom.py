"""Implement the image-driven Midjourney zoom node."""

from __future__ import annotations

from ..services import (
    build_comfy_progress_reporter,
    build_single_image_output,
    comfy_image_to_png_bytes,
)
from .common import NodeBoundaryContext, RuntimeBackedNode, execute_node_boundary


class MidjourneyZoomNode(RuntimeBackedNode):
    """Resolve one recognized upscaled Midjourney image and submit a zoom action."""

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "zoom"
    CATEGORY = "image"

    @classmethod
    def INPUT_TYPES(cls):
        """Return the ComfyUI input declaration for the zoom node."""
        return {
            "required": {
                "mj_image": ("IMAGE",),
                "zoom_factor": (
                    "FLOAT",
                    {
                        "default": 1.5,
                        "min": 1.0,
                        "max": 2.0,
                        "step": 0.01,
                        "tooltip": (
                            "Midjourney Zoom requires a recognized already-upscaled "
                            "Midjourney image. Empty prompt values use the dedicated "
                            "1.5x and 2x buttons when applicable."
                        ),
                    },
                ),
            },
            "optional": {
                "prompt": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": (
                            "Optional prompt text used only for custom zoom requests."
                        ),
                    },
                )
            },
        }

    def zoom(
        self,
        mj_image,
        zoom_factor: float,
        prompt: str = "",
    ):
        """Resolve the input image through Mutiny and return the zoom result."""

        def submit():
            """Encode the input image and delegate the zoom request to runtime."""
            image_bytes = comfy_image_to_png_bytes(mj_image)
            progress_reporter, _preview_image = build_comfy_progress_reporter()
            result = self._get_runtime_service().zoom_image_and_wait(
                image_bytes,
                zoom_factor=zoom_factor,
                prompt_text=prompt,
                node_name=self.__class__.__name__,
                progress_reporter=progress_reporter,
            )
            return (build_single_image_output(result),)

        return execute_node_boundary(
            context=NodeBoundaryContext(
                node_name=self.__class__.__name__,
                action_name="zoom",
            ),
            operation=submit,
        )


__all__ = ["MidjourneyZoomNode"]
