"""Implement the image-driven Midjourney Vary Region node."""

from __future__ import annotations

from ..prompting.validators import normalize_prompt_text
from ..services import (
    build_comfy_progress_reporter,
    build_split_image_output,
    comfy_mask_to_data_url,
    prompt_image_to_data_url,
)
from .common import NodeBoundaryContext, RuntimeBackedNode, execute_node_boundary


class MidjourneyVaryRegionNode(RuntimeBackedNode):
    """Submit one recognized Midjourney image plus mask through Mutiny inpaint."""

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "vary_region"
    CATEGORY = "image"

    @classmethod
    def INPUT_TYPES(cls):
        """Return the ComfyUI input declaration for the Vary Region node."""
        return {
            "required": {
                "mj_image": ("IMAGE",),
                "mask": ("MASK",),
                "prompt": (
                    "STRING",
                    {
                        "tooltip": (
                            "Region edit prompt sent through Midjourney Vary Region."
                        ),
                    },
                ),
            },
            "optional": {
                "negative_prompt": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": (
                            "Optional negative prompt appended as '--no ...' before"
                            " submission."
                        ),
                    },
                )
            },
        }

    def vary_region(
        self,
        mj_image,
        mask,
        prompt: str,
        negative_prompt: str = "",
    ):
        """Encode one image and mask, then return the final Vary Region result."""

        def submit():
            """Build one runtime submission from the node inputs."""
            source_image_data_url = prompt_image_to_data_url(mj_image)
            mask_data_url = comfy_mask_to_data_url(mask)
            prompt_text = _compile_vary_region_prompt(
                prompt=prompt,
                negative_prompt=negative_prompt,
            )
            progress_reporter, _preview_image = build_comfy_progress_reporter()
            result = self._get_runtime_service().vary_region_image_and_wait(
                source_image_data_url,
                mask_data_url,
                prompt_text=prompt_text,
                node_name=self.__class__.__name__,
                progress_reporter=progress_reporter,
            )
            return (build_split_image_output(result),)

        return execute_node_boundary(
            context=NodeBoundaryContext(
                node_name=self.__class__.__name__,
                action_name="vary_region",
            ),
            operation=submit,
        )


def _compile_vary_region_prompt(*, prompt: str, negative_prompt: str) -> str:
    """Normalize prompt inputs and render the final Vary Region prompt text."""
    normalized_prompt = normalize_prompt_text(prompt)
    if not normalized_prompt:
        raise ValueError("Prompt cannot be empty.")

    normalized_negative_prompt = normalize_prompt_text(negative_prompt)
    if not normalized_negative_prompt:
        return normalized_prompt
    return f"{normalized_prompt} --no {normalized_negative_prompt}"


__all__ = ["MidjourneyVaryRegionNode"]
