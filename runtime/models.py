"""Define the runtime-layer models shared across the plugin transport adapter."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from mutiny import Config, ImageTile, JobSnapshot, JobStatus


@dataclass(frozen=True)
class RuntimeActionContext:
    """Capture the user-safe execution context logged for one runtime action."""

    node_name: str
    action_name: str
    model_name: str | None = None
    job_id: str | None = None
    retry_state: str | None = None


@dataclass(frozen=True)
class RuntimeSubmission:
    """Capture the submitted job id plus the config snapshot used to submit it."""

    job_id: str
    config: Config


@dataclass(frozen=True)
class RuntimeImagineImageInputs:
    """Capture the structured image payload forwarded to Mutiny imagine calls."""

    prompt_images: tuple[str, ...] = ()
    style_reference_images: tuple[str, ...] = ()
    style_reference_multipliers: tuple[float, ...] = ()
    character_reference_images: tuple[str, ...] = ()
    omni_reference_image: str | None = None

    @property
    def is_empty(self) -> bool:
        """Return whether no attached image channels were populated."""
        return not (
            self.prompt_images
            or self.style_reference_images
            or self.character_reference_images
            or self.omni_reference_image
        )


@dataclass(frozen=True)
class ResolvedMidjourneyImageContext:
    """Capture the Mutiny job context resolved from one recognized image."""

    job_id: str
    index: int


class MidjourneyUpscaleMode(str, Enum):
    """Represent the supported upscale-family modes accepted by the node runtime."""

    STANDARD = "standard"
    SUBTLE = "subtle"
    CREATIVE = "creative"


class MidjourneyVariationMode(str, Enum):
    """Represent the supported variation-family modes accepted by the node runtime."""

    STANDARD = "standard"
    SUBTLE = "subtle"
    STRONG = "strong"


class MidjourneyPanDirection(str, Enum):
    """Represent the supported pan directions accepted by the node runtime."""

    LEFT = "left"
    RIGHT = "right"
    UP = "up"
    DOWN = "down"


class MidjourneyAnimateMotion(str, Enum):
    """Represent the supported animate motion levels accepted by the node runtime."""

    LOW = "low"
    HIGH = "high"


@dataclass(frozen=True)
class RuntimeJobResult:
    """Capture a completed job plus its decoded image payload information."""

    job: JobSnapshot
    image_bytes: bytes
    tiles: tuple[ImageTile, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RuntimeDescribeResult:
    """Capture one completed describe job plus its extracted prompt text."""

    job: JobSnapshot
    prompt_text: str


@dataclass(frozen=True)
class RuntimeVideoResult:
    """Capture one completed animate job plus its native Comfy video output."""

    job: JobSnapshot
    video_url: str
    video_value: object


@dataclass(frozen=True)
class JobTrackingSnapshot:
    """Store the latest public job/progress state seen by the runtime tracker."""

    job_id: str
    version: int = 0
    status: JobStatus | None = None
    progress_text: str | None = None
    preview_image_url: str | None = None
    fail_reason: str | None = None

    @property
    def is_terminal(self) -> bool:
        """Return whether the tracked job has reached a terminal state."""
        return self.status in {JobStatus.SUCCEEDED, JobStatus.FAILED}


__all__ = [
    "JobTrackingSnapshot",
    "MidjourneyAnimateMotion",
    "MidjourneyPanDirection",
    "MidjourneyUpscaleMode",
    "MidjourneyVariationMode",
    "ResolvedMidjourneyImageContext",
    "RuntimeImagineImageInputs",
    "RuntimeActionContext",
    "RuntimeDescribeResult",
    "RuntimeJobResult",
    "RuntimeVideoResult",
    "RuntimeSubmission",
]
