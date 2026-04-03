"""Provide fake backend objects for deterministic node and runtime tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from typing import Any

import numpy as np
from mutiny import (
    ImageOutput,
    ImageTile,
    JobSnapshot,
    JobStatus,
    TextOutput,
    VideoOutput,
)
from PIL import Image


@dataclass
class FakeRuntimeResult:
    """Store the image payload returned by the fake runtime service."""

    job: JobSnapshot
    image_bytes: bytes
    tiles: tuple[ImageTile, ...]


@dataclass
class FakeRuntimeDescribeResult:
    """Store the text payload returned by the fake runtime service."""

    job: JobSnapshot
    prompt_text: str


@dataclass
class FakeRuntimeVideoResult:
    """Store the video payload returned by the fake runtime service."""

    job: JobSnapshot
    video_url: str
    video_value: object


@dataclass
class FakeRuntimeService:
    """Simulate the runtime adapter boundary without starting Mutiny."""

    generated_image: np.ndarray
    generated_job_id: str = "job-123"
    upscale_image_job_id: str = "job-789"
    pan_job_id: str = "job-321"
    zoom_job_id: str = "job-6540"
    variation_job_id: str = "job-654"
    vary_region_job_id: str = "job-987"
    animate_job_id: str = "job-963"
    extend_job_id: str = "job-741"
    describe_job_id: str = "job-852"
    describe_text: str = "describe prompt text"
    animate_video_url: str = "https://example.invalid/final.mp4"
    animate_video_value: object = field(default_factory=lambda: object())
    imagine_exception: Exception | None = None
    upscale_image_exception: Exception | None = None
    pan_image_exception: Exception | None = None
    zoom_image_exception: Exception | None = None
    variation_exception: Exception | None = None
    vary_region_exception: Exception | None = None
    animate_exception: Exception | None = None
    extend_exception: Exception | None = None
    describe_exception: Exception | None = None
    progress_updates: list[tuple[str, np.ndarray | bytes | None]] = field(
        default_factory=list
    )
    imagine_calls: list[dict[str, Any]] = field(default_factory=list)
    upscale_image_calls: list[dict[str, Any]] = field(default_factory=list)
    pan_image_calls: list[dict[str, Any]] = field(default_factory=list)
    zoom_image_calls: list[dict[str, Any]] = field(default_factory=list)
    variation_image_calls: list[dict[str, Any]] = field(default_factory=list)
    vary_region_calls: list[dict[str, Any]] = field(default_factory=list)
    animate_calls: list[dict[str, Any]] = field(default_factory=list)
    extend_calls: list[dict[str, Any]] = field(default_factory=list)
    describe_calls: list[dict[str, Any]] = field(default_factory=list)

    def imagine_and_wait(
        self,
        prompt_text: str,
        *,
        node_name: str,
        model_name: str | None = None,
        image_inputs=None,
        progress_reporter=None,
    ) -> FakeRuntimeResult:
        """Record imagine calls and return a deterministic completed result."""
        self.imagine_calls.append(
            {
                "prompt_text": prompt_text,
                "node_name": node_name,
                "model_name": model_name,
                "image_inputs": image_inputs,
                "progress_reporter": progress_reporter,
            }
        )
        if self.imagine_exception is not None:
            raise self.imagine_exception

        self._emit_progress(progress_reporter)
        return _build_runtime_result(
            self.generated_image,
            job_id=self.generated_job_id,
            kind="imagine",
            include_tiles=True,
        )

    def upscale_image_and_wait(
        self,
        image_bytes: bytes,
        *,
        mode,
        node_name: str,
        progress_reporter=None,
    ) -> FakeRuntimeResult:
        """Record image-driven upscale calls and return a deterministic result."""
        self.upscale_image_calls.append(
            {
                "image_bytes": image_bytes,
                "mode": mode,
                "node_name": node_name,
                "progress_reporter": progress_reporter,
            }
        )
        if self.upscale_image_exception is not None:
            raise self.upscale_image_exception

        self._emit_progress(progress_reporter)
        return _build_runtime_result(
            self.generated_image,
            job_id=self.upscale_image_job_id,
            kind=f"upscale:{getattr(mode, 'value', mode)}",
            include_tiles=False,
        )

    def vary_region_image_and_wait(
        self,
        source_image_data_url: str,
        mask_data_url: str,
        *,
        prompt_text: str,
        node_name: str,
        progress_reporter=None,
    ) -> FakeRuntimeResult:
        """Record Vary Region calls and return a deterministic completed result."""
        self.vary_region_calls.append(
            {
                "source_image_data_url": source_image_data_url,
                "mask_data_url": mask_data_url,
                "prompt_text": prompt_text,
                "node_name": node_name,
                "progress_reporter": progress_reporter,
            }
        )
        if self.vary_region_exception is not None:
            raise self.vary_region_exception

        self._emit_progress(progress_reporter)
        return _build_runtime_result(
            self.generated_image,
            job_id=self.vary_region_job_id,
            kind="vary_region",
            include_tiles=True,
        )

    def pan_image_and_wait(
        self,
        image_bytes: bytes,
        *,
        direction,
        node_name: str,
        progress_reporter=None,
    ) -> FakeRuntimeResult:
        """Record pan calls and return a deterministic completed result."""
        self.pan_image_calls.append(
            {
                "image_bytes": image_bytes,
                "direction": direction,
                "node_name": node_name,
                "progress_reporter": progress_reporter,
            }
        )
        if self.pan_image_exception is not None:
            raise self.pan_image_exception

        self._emit_progress(progress_reporter)
        return _build_runtime_result(
            self.generated_image,
            job_id=self.pan_job_id,
            kind=f"pan:{getattr(direction, 'value', direction)}",
            include_tiles=True,
        )

    def zoom_image_and_wait(
        self,
        image_bytes: bytes,
        *,
        zoom_factor: float,
        prompt_text: str,
        node_name: str,
        progress_reporter=None,
    ) -> FakeRuntimeResult:
        """Record zoom calls and return a deterministic completed result."""
        self.zoom_image_calls.append(
            {
                "image_bytes": image_bytes,
                "zoom_factor": zoom_factor,
                "prompt_text": prompt_text,
                "node_name": node_name,
                "progress_reporter": progress_reporter,
            }
        )
        if self.zoom_image_exception is not None:
            raise self.zoom_image_exception

        self._emit_progress(progress_reporter)
        return _build_runtime_result(
            self.generated_image,
            job_id=self.zoom_job_id,
            kind="zoom",
            include_tiles=False,
        )

    def variation_image_and_wait(
        self,
        image_bytes: bytes,
        *,
        mode,
        node_name: str,
        progress_reporter=None,
    ) -> FakeRuntimeResult:
        """Record variation calls and return a deterministic completed result."""
        self.variation_image_calls.append(
            {
                "image_bytes": image_bytes,
                "mode": mode,
                "node_name": node_name,
                "progress_reporter": progress_reporter,
            }
        )
        if self.variation_exception is not None:
            raise self.variation_exception

        self._emit_progress(progress_reporter)
        return _build_runtime_result(
            self.generated_image,
            job_id=self.variation_job_id,
            kind=f"vary:{getattr(mode, 'value', mode)}",
            include_tiles=True,
        )

    def describe_image_and_wait(
        self,
        image_data_url: str,
        *,
        node_name: str,
        progress_reporter=None,
    ) -> FakeRuntimeDescribeResult:
        """Record describe calls and return a deterministic completed text result."""
        self.describe_calls.append(
            {
                "image_data_url": image_data_url,
                "node_name": node_name,
                "progress_reporter": progress_reporter,
            }
        )
        if self.describe_exception is not None:
            raise self.describe_exception

        self._emit_progress(progress_reporter)
        job = JobSnapshot(
            id=self.describe_job_id,
            kind="describe",
            status=JobStatus.SUCCEEDED,
            prompt_text=self.describe_text,
            output=TextOutput(text=self.describe_text),
        )
        return FakeRuntimeDescribeResult(job=job, prompt_text=self.describe_text)

    def animate_image_and_wait(
        self,
        start_frame_data_url: str,
        *,
        motion,
        end_frame_data_url: str | None = None,
        prompt_text: str = "",
        batch_size: int | None = None,
        node_name: str,
        progress_reporter=None,
    ) -> FakeRuntimeVideoResult:
        """Record animate calls and return a deterministic native-video result."""
        self.animate_calls.append(
            {
                "start_frame_data_url": start_frame_data_url,
                "end_frame_data_url": end_frame_data_url,
                "prompt_text": prompt_text,
                "motion": motion,
                "batch_size": batch_size,
                "node_name": node_name,
                "progress_reporter": progress_reporter,
            }
        )
        if self.animate_exception is not None:
            raise self.animate_exception

        self._emit_progress(progress_reporter)
        job = JobSnapshot(
            id=self.animate_job_id,
            kind="animate",
            status=JobStatus.SUCCEEDED,
            output=VideoOutput(video_url=self.animate_video_url),
        )
        return FakeRuntimeVideoResult(
            job=job,
            video_url=self.animate_video_url,
            video_value=self.animate_video_value,
        )

    def extend_video_and_wait(
        self,
        video_bytes: bytes,
        *,
        motion,
        node_name: str,
        progress_reporter=None,
    ) -> FakeRuntimeVideoResult:
        """Record extend calls and return a deterministic native-video result."""
        self.extend_calls.append(
            {
                "video_bytes": video_bytes,
                "motion": motion,
                "node_name": node_name,
                "progress_reporter": progress_reporter,
            }
        )
        if self.extend_exception is not None:
            raise self.extend_exception

        self._emit_progress(progress_reporter)
        job = JobSnapshot(
            id=self.extend_job_id,
            kind="extend",
            status=JobStatus.SUCCEEDED,
            output=VideoOutput(video_url=self.animate_video_url),
        )
        return FakeRuntimeVideoResult(
            job=job,
            video_url=self.animate_video_url,
            video_value=self.animate_video_value,
        )

    def _emit_progress(self, progress_reporter) -> None:
        """Dispatch fake progress updates through the provided reporter."""
        if progress_reporter is None:
            return

        for progress_text, payload in self.progress_updates:
            progress_reporter(progress_text, _normalize_progress_payload(payload))


@dataclass
class FakeTokenStore:
    """Simulate keyring-backed token storage without touching the host system."""

    token: str | None = None
    fail_on_save: Exception | None = None
    fail_on_load: Exception | None = None
    fail_on_clear: Exception | None = None

    def save_token(self, token: str) -> None:
        """Store one token value or raise a configured error."""
        if self.fail_on_save is not None:
            raise self.fail_on_save
        normalized = token.strip()
        if not normalized:
            raise ValueError("Discord token cannot be empty.")
        self.token = normalized

    def load_token(self) -> str | None:
        """Return the stored token or raise a configured error."""
        if self.fail_on_load is not None:
            raise self.fail_on_load
        return self.token

    def clear_token(self) -> None:
        """Remove the stored token or raise a configured error."""
        if self.fail_on_clear is not None:
            raise self.fail_on_clear
        self.token = None

    def token_exists(self) -> bool:
        """Return whether a token is currently stored."""
        return bool(self.load_token())


def _build_runtime_result(
    image: np.ndarray,
    *,
    job_id: str,
    kind: str,
    include_tiles: bool,
) -> FakeRuntimeResult:
    """Build a completed runtime result with deterministic image bytes and tiles."""
    image_bytes = _encode_image(image)
    job = JobSnapshot(
        id=job_id,
        kind=kind,
        status=JobStatus.SUCCEEDED,
        output=ImageOutput(image_url="https://example.invalid/final.png"),
    )

    tiles = ()
    if include_tiles:
        tiles = tuple(
            ImageTile(
                job_id=job_id,
                index=index,
                image_bytes=_encode_image(tile_image),
            )
            for index, tile_image in enumerate(_split_grid(image), start=1)
        )

    return FakeRuntimeResult(job=job, image_bytes=image_bytes, tiles=tiles)


def _normalize_progress_payload(
    payload: np.ndarray | bytes | None,
) -> bytes | None:
    """Normalize fake progress payloads into bytes like the real runtime uses."""
    if payload is None or isinstance(payload, bytes):
        return payload
    return _encode_image(payload)


def _encode_image(image: np.ndarray) -> bytes:
    """Encode one numpy RGB image into PNG bytes."""
    buffer = BytesIO()
    Image.fromarray(image.astype(np.uint8)).save(buffer, format="PNG")
    return buffer.getvalue()


def _split_grid(
    image: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Split a deterministic 2x2 grid image into its four quadrants."""
    height, width = image.shape[:2]
    half_height = height // 2
    half_width = width // 2
    return (
        image[:half_height, :half_width, :],
        image[:half_height, half_width:, :],
        image[half_height:, :half_width, :],
        image[half_height:, half_width:, :],
    )
