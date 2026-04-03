"""Implement the standalone Midjourney Describe node."""

from __future__ import annotations

from ..services import build_comfy_progress_reporter, prompt_image_to_data_url
from .common import NodeBoundaryContext, RuntimeBackedNode, execute_node_boundary


class MidjourneyDescribeNode(RuntimeBackedNode):
    """Submit one arbitrary image to Midjourney Describe and return the prompt text."""

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)
    FUNCTION = "describe"
    CATEGORY = "image"

    @classmethod
    def INPUT_TYPES(cls):
        """Return the ComfyUI input declaration for the describe node."""
        return {
            "required": {
                "image": (
                    "IMAGE",
                    {
                        "tooltip": (
                            "Send any image to Midjourney Describe and return the "
                            "resulting prompt text."
                        ),
                    },
                ),
            }
        }

    def describe(self, image):
        """Encode the input image, submit Describe through Mutiny, and return text."""

        def submit():
            """Build one describe submission from the node input image."""
            image_data_url = prompt_image_to_data_url(image)
            progress_reporter, _preview_image = build_comfy_progress_reporter()
            result = self._get_runtime_service().describe_image_and_wait(
                image_data_url,
                node_name=self.__class__.__name__,
                progress_reporter=progress_reporter,
            )
            return (result.prompt_text,)

        return execute_node_boundary(
            context=NodeBoundaryContext(
                node_name=self.__class__.__name__,
                action_name="describe",
            ),
            operation=submit,
        )


__all__ = ["MidjourneyDescribeNode"]
