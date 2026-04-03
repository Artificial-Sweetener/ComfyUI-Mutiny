"""Implement the unified Midjourney animate node with native Comfy video output."""

from __future__ import annotations

from ..prompting.validators import normalize_prompt_text
from ..runtime import MidjourneyAnimateMotion
from ..services import build_comfy_progress_reporter, prompt_image_to_data_url
from .common import NodeBoundaryContext, RuntimeBackedNode, execute_node_boundary


class MidjourneyAnimateNode(RuntimeBackedNode):
    """Animate a start frame through Mutiny and return a native Comfy ``VIDEO``."""

    RETURN_TYPES = ("VIDEO",)
    RETURN_NAMES = ("video",)
    FUNCTION = "animate"
    CATEGORY = "image"

    _MOTION_BY_LABEL = {
        "Low Motion": MidjourneyAnimateMotion.LOW,
        "High Motion": MidjourneyAnimateMotion.HIGH,
    }

    @classmethod
    def INPUT_TYPES(cls):
        """Return the ComfyUI input declaration for the animate node."""
        return {
            "required": {
                "start_frame": (
                    "IMAGE",
                    {
                        "tooltip": (
                            "Required starting frame for Midjourney Animate. Mutiny "
                            "will prefer the existing MJ animate follow-up path when "
                            "the image is a recognized upscaled Midjourney image and "
                            "no prompt-video-only controls are used."
                        ),
                    },
                ),
                "motion": (
                    ["Low Motion", "High Motion"],
                    {
                        "default": "Low Motion",
                        "tooltip": "Choose the Midjourney animation motion level.",
                    },
                ),
            },
            "optional": {
                "end_frame": (
                    "IMAGE",
                    {
                        "tooltip": (
                            "Optional ending frame. Providing this forces prompt-based "
                            "Midjourney --video generation."
                        ),
                    },
                ),
                "prompt": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": (
                            "Optional prompt text used for prompt-based Midjourney "
                            "--video generation."
                        ),
                    },
                ),
                "negative_prompt": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": (
                            "Optional negative prompt appended as '--no ...' for "
                            "prompt-based Midjourney --video generation."
                        ),
                    },
                ),
                "batch_size": (
                    ["1", "2", "4"],
                    {
                        "default": "1",
                        "tooltip": (
                            "Optional Midjourney video batch size. Larger batches "
                            "increase cost."
                        ),
                    },
                ),
            },
        }

    def animate(
        self,
        start_frame,
        motion: str,
        end_frame=None,
        prompt: str = "",
        negative_prompt: str = "",
        batch_size: str = "1",
    ):
        """Encode the input frames, submit Animate through Mutiny, and return video."""

        def submit():
            """Build one animate submission from the node input frames."""
            start_frame_data_url = prompt_image_to_data_url(start_frame)
            end_frame_data_url = (
                None if end_frame is None else prompt_image_to_data_url(end_frame)
            )
            progress_reporter, _preview_image = build_comfy_progress_reporter()
            result = self._get_runtime_service().animate_image_and_wait(
                start_frame_data_url,
                end_frame_data_url=end_frame_data_url,
                prompt_text=_compile_animate_prompt(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                ),
                motion=self._normalize_motion(motion),
                batch_size=int(batch_size),
                node_name=self.__class__.__name__,
                progress_reporter=progress_reporter,
            )
            return (result.video_value,)

        return execute_node_boundary(
            context=NodeBoundaryContext(
                node_name=self.__class__.__name__,
                action_name="animate",
            ),
            operation=submit,
        )

    @classmethod
    def _normalize_motion(cls, motion_label: str) -> MidjourneyAnimateMotion:
        """Map one UI motion label to the internal runtime animate enum."""
        try:
            return cls._MOTION_BY_LABEL[motion_label]
        except KeyError as exc:
            raise ValueError(
                f"Unsupported Midjourney animate motion: {motion_label!r}."
            ) from exc


def _compile_animate_prompt(*, prompt: str, negative_prompt: str) -> str:
    """Normalize animate prompt fields and append ``--no`` when requested."""
    normalized_prompt = normalize_prompt_text(prompt)
    normalized_negative_prompt = normalize_prompt_text(negative_prompt)
    if not normalized_negative_prompt:
        return normalized_prompt
    if not normalized_prompt:
        return f"--no {normalized_negative_prompt}"
    return f"{normalized_prompt} --no {normalized_negative_prompt}"


__all__ = ["MidjourneyAnimateNode"]
