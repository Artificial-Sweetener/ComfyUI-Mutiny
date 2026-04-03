"""Implement the Midjourney video extend node backed by Mutiny recognition."""

from __future__ import annotations

from ..runtime import MidjourneyAnimateMotion
from ..services import build_comfy_progress_reporter, comfy_video_to_bytes
from .common import NodeBoundaryContext, RuntimeBackedNode, execute_node_boundary


class MidjourneyExtendNode(RuntimeBackedNode):
    """Extend one recognized Midjourney video and return a native Comfy ``VIDEO``."""

    RETURN_TYPES = ("VIDEO",)
    RETURN_NAMES = ("video",)
    FUNCTION = "extend"
    CATEGORY = "image"

    _MOTION_BY_LABEL = {
        "Low Motion": MidjourneyAnimateMotion.LOW,
        "High Motion": MidjourneyAnimateMotion.HIGH,
    }

    @classmethod
    def INPUT_TYPES(cls):
        """Return the ComfyUI input declaration for the extend node."""
        return {
            "required": {
                "mj_video": (
                    "VIDEO",
                    {
                        "tooltip": (
                            "Recognized Midjourney video returned by this plugin. "
                            "Mutiny resolves the original animate context from the "
                            "video artifact before submitting Extend."
                        ),
                    },
                ),
                "motion": (
                    ["Low Motion", "High Motion"],
                    {
                        "default": "Low Motion",
                        "tooltip": "Choose the Midjourney Extend motion level.",
                    },
                ),
            }
        }

    def extend(self, mj_video, motion: str):
        """Submit Midjourney Extend for one recognized video artifact."""

        def submit():
            """Convert the input video into bytes and submit the extend request."""
            progress_reporter, _preview_image = build_comfy_progress_reporter()
            result = self._get_runtime_service().extend_video_and_wait(
                comfy_video_to_bytes(mj_video),
                motion=self._normalize_motion(motion),
                node_name=self.__class__.__name__,
                progress_reporter=progress_reporter,
            )
            return (result.video_value,)

        return execute_node_boundary(
            context=NodeBoundaryContext(
                node_name=self.__class__.__name__,
                action_name="extend",
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
                f"Unsupported Midjourney extend motion: {motion_label!r}."
            ) from exc


__all__ = ["MidjourneyExtendNode"]
