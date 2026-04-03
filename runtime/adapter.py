"""Expose a sync-friendly Mutiny runtime service for ComfyUI nodes."""

from __future__ import annotations

import logging
import math
import time
from dataclasses import replace
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from mutiny import ImageOutput, JobSnapshot, JobStatus, TextOutput, VideoOutput

from ..prompting.validators import normalize_prompt_text
from ..services import ResultVideoLoader
from ..services.image_results import ResultImageLoader
from ..settings.service import get_settings_service
from .errors import (
    JobFailedError,
    RuntimeAdapterError,
    format_runtime_context,
    translate_runtime_exception,
)
from .manager import MutinyRuntimeManager
from .models import (
    JobTrackingSnapshot,
    MidjourneyAnimateMotion,
    MidjourneyPanDirection,
    MidjourneyUpscaleMode,
    MidjourneyVariationMode,
    RuntimeActionContext,
    RuntimeDescribeResult,
    RuntimeImagineImageInputs,
    RuntimeJobResult,
    RuntimeSubmission,
    RuntimeVideoResult,
)

logger = logging.getLogger(__name__)

_DEFAULT_RUNTIME_SERVICE: "MutinyRuntimeService | None" = None


class MutinyRuntimeService:
    """Submit jobs through Mutiny and wait for results without exposing async details."""

    def __init__(
        self,
        manager: MutinyRuntimeManager,
        *,
        image_loader: ResultImageLoader | None = None,
        video_loader: ResultVideoLoader | None = None,
    ) -> None:
        """Store the runtime manager and result loaders used for node execution."""
        self._manager = manager
        self._image_loader = image_loader or ResultImageLoader()
        self._video_loader = video_loader or ResultVideoLoader()

    def imagine_and_wait(
        self,
        prompt_text: str,
        *,
        node_name: str,
        model_name: str | None = None,
        image_inputs: RuntimeImagineImageInputs | None = None,
        progress_reporter=None,
    ) -> RuntimeJobResult:
        """Submit an imagine job and wait for its terminal image result."""
        context = RuntimeActionContext(
            node_name=node_name,
            action_name="imagine",
            model_name=model_name,
        )

        try:
            submission = self._manager.submit_imagine(
                prompt_text,
                image_inputs=image_inputs,
            )
            context = replace(context, job_id=submission.job_id)
            return self._wait_for_image_result(
                submission,
                context=context,
                expect_split_result=True,
                progress_reporter=progress_reporter,
            )
        except Exception as exc:
            self._raise_runtime_error(exc, context)

    def get_job(self, job_id: str) -> JobSnapshot:
        """Return one public job snapshot from the shared runtime."""
        context = RuntimeActionContext(
            node_name="runtime",
            action_name="get_job",
            job_id=job_id,
        )

        try:
            return self._manager.get_job(job_id)
        except Exception as exc:
            self._raise_runtime_error(exc, context)

    def upscale_image_and_wait(
        self,
        image_bytes: bytes,
        *,
        mode: MidjourneyUpscaleMode,
        node_name: str,
        progress_reporter=None,
    ) -> RuntimeJobResult:
        """Resolve one image context and submit the selected upscale-family action."""
        context = RuntimeActionContext(
            node_name=node_name,
            action_name="upscale",
        )

        try:
            resolved_context = self._resolve_recognized_source_context(
                image_bytes=image_bytes
            )
            submission = self._manager.submit_upscale(
                resolved_context.job_id,
                index=self._resolve_upscale_index(
                    resolved_index=resolved_context.index,
                    mode=mode,
                ),
                mode=mode,
            )
            context = replace(context, job_id=submission.job_id)
            return self._wait_for_image_result(
                submission,
                context=context,
                expect_split_result=False,
                progress_reporter=progress_reporter,
            )
        except Exception as exc:
            self._raise_runtime_error(exc, context)

    def vary_region_image_and_wait(
        self,
        source_image_data_url: str,
        mask_data_url: str,
        *,
        prompt_text: str,
        node_name: str,
        progress_reporter=None,
    ) -> RuntimeJobResult:
        """Submit one Vary Region request and wait for the final image result."""
        context = RuntimeActionContext(
            node_name=node_name,
            action_name="vary_region",
        )

        try:
            submission = self._manager.submit_vary_region(
                source_image_data_url=source_image_data_url,
                mask_data_url=mask_data_url,
                prompt_text=prompt_text,
            )
            context = replace(context, job_id=submission.job_id)
            return self._wait_for_image_result(
                submission,
                context=context,
                expect_split_result=True,
                progress_reporter=progress_reporter,
            )
        except Exception as exc:
            self._raise_runtime_error(exc, context)

    def variation_image_and_wait(
        self,
        image_bytes: bytes,
        *,
        mode: MidjourneyVariationMode,
        node_name: str,
        progress_reporter=None,
    ) -> RuntimeJobResult:
        """Resolve one grid tile and submit the selected variation-family action."""
        context = RuntimeActionContext(
            node_name=node_name,
            action_name="vary",
        )

        try:
            resolved_context = self._resolve_recognized_source_context(
                image_bytes=image_bytes
            )
            submission = self._manager.submit_variation(
                resolved_context.job_id,
                index=self._resolve_variation_index(
                    resolved_index=resolved_context.index,
                    mode=mode,
                ),
                mode=mode,
            )
            context = replace(context, job_id=submission.job_id)
            return self._wait_for_image_result(
                submission,
                context=context,
                expect_split_result=True,
                progress_reporter=progress_reporter,
            )
        except Exception as exc:
            self._raise_runtime_error(exc, context)

    def describe_image_and_wait(
        self,
        image_data_url: str,
        *,
        node_name: str,
        progress_reporter=None,
    ) -> RuntimeDescribeResult:
        """Submit one describe request and return the final prompt text."""
        context = RuntimeActionContext(
            node_name=node_name,
            action_name="describe",
        )

        try:
            submission = self._manager.submit_describe(image_data_url=image_data_url)
            context = replace(context, job_id=submission.job_id)
            snapshot = self._wait_for_terminal_snapshot(
                submission,
                context=context,
                progress_reporter=progress_reporter,
            )
            return RuntimeDescribeResult(
                job=snapshot,
                prompt_text=self._extract_describe_text(snapshot),
            )
        except Exception as exc:
            self._raise_runtime_error(exc, context)

    def animate_image_and_wait(
        self,
        start_frame_data_url: str,
        *,
        motion: MidjourneyAnimateMotion,
        end_frame_data_url: str | None = None,
        prompt_text: str = "",
        batch_size: int | None = None,
        node_name: str,
        progress_reporter=None,
    ) -> RuntimeVideoResult:
        """Submit one animate request and return the final native video result."""
        context = RuntimeActionContext(
            node_name=node_name,
            action_name="animate",
        )

        try:
            submission = self._manager.submit_animate(
                start_frame_data_url=start_frame_data_url,
                end_frame_data_url=end_frame_data_url,
                prompt_text=prompt_text,
                motion=motion,
                batch_size=batch_size,
            )
            context = replace(context, job_id=submission.job_id)
            snapshot = self._wait_for_terminal_snapshot(
                submission,
                context=context,
                progress_reporter=progress_reporter,
                progress_text_transformer=self._normalize_video_progress_text,
            )
            return self._build_video_result(snapshot, submission=submission)
        except Exception as exc:
            self._raise_runtime_error(exc, context)

    def extend_video_and_wait(
        self,
        video_bytes: bytes,
        *,
        motion: MidjourneyAnimateMotion,
        node_name: str,
        progress_reporter=None,
    ) -> RuntimeVideoResult:
        """Submit one animate-extend request and return the final native video result."""
        context = RuntimeActionContext(
            node_name=node_name,
            action_name="extend",
        )

        try:
            submission = self._manager.submit_extend(
                video_bytes=video_bytes,
                motion=motion,
            )
            context = replace(context, job_id=submission.job_id)
            snapshot = self._wait_for_terminal_snapshot(
                submission,
                context=context,
                progress_reporter=progress_reporter,
                progress_text_transformer=self._normalize_video_progress_text,
            )
            return self._build_video_result(snapshot, submission=submission)
        except Exception as exc:
            self._raise_runtime_error(exc, context)

    def pan_image_and_wait(
        self,
        image_bytes: bytes,
        *,
        direction: MidjourneyPanDirection,
        node_name: str,
        progress_reporter=None,
    ) -> RuntimeJobResult:
        """Resolve one recognized Midjourney source image and submit the pan action."""
        context = RuntimeActionContext(
            node_name=node_name,
            action_name="pan",
        )

        try:
            resolved_context = self._resolve_recognized_source_context(
                image_bytes=image_bytes
            )
            submission = self._manager.submit_pan(
                resolved_context.job_id,
                direction=direction,
                index=self._normalize_follow_up_submission_index(
                    resolved_context.index
                ),
            )
            context = replace(context, job_id=submission.job_id)
            return self._wait_for_image_result(
                submission,
                context=context,
                expect_split_result=True,
                progress_reporter=progress_reporter,
            )
        except Exception as exc:
            self._raise_runtime_error(exc, context)

    def zoom_image_and_wait(
        self,
        image_bytes: bytes,
        *,
        zoom_factor: float,
        prompt_text: str,
        node_name: str,
        progress_reporter=None,
    ) -> RuntimeJobResult:
        """Resolve one recognized Midjourney source image and submit the zoom action."""
        context = RuntimeActionContext(
            node_name=node_name,
            action_name="zoom",
        )

        try:
            resolved_context = self._resolve_recognized_source_context(
                image_bytes=image_bytes
            )
            normalized_factor = self._normalize_zoom_factor(zoom_factor)
            normalized_prompt = normalize_prompt_text(prompt_text) or None
            submission = self._manager.submit_zoom(
                resolved_context.job_id,
                factor=normalized_factor,
                prompt_text=normalized_prompt,
                index=self._normalize_follow_up_submission_index(
                    resolved_context.index
                ),
            )
            context = replace(context, job_id=submission.job_id)
            return self._wait_for_image_result(
                submission,
                context=context,
                expect_split_result=False,
                progress_reporter=progress_reporter,
            )
        except Exception as exc:
            self._raise_runtime_error(exc, context)

    def close(self) -> None:
        """Close the underlying shared runtime manager."""
        self._manager.close()

    def _wait_for_image_result(
        self,
        submission: RuntimeSubmission,
        *,
        context: RuntimeActionContext,
        expect_split_result: bool,
        progress_reporter,
    ) -> RuntimeJobResult:
        """Wait for one image-producing job and decode its final media payload."""
        snapshot = self._wait_for_terminal_snapshot(
            submission,
            context=context,
            progress_reporter=progress_reporter,
        )
        image_source = self._extract_image_source(snapshot)
        image_bytes = self._image_loader.fetch_bytes(
            image_source,
            config=submission.config,
        )
        tiles = ()
        if expect_split_result:
            tiles = self._manager.split_image_result(submission.job_id, image_bytes)
        return RuntimeJobResult(job=snapshot, image_bytes=image_bytes, tiles=tiles)

    def _wait_for_terminal_snapshot(
        self,
        submission: RuntimeSubmission,
        *,
        context: RuntimeActionContext,
        progress_reporter,
        progress_text_transformer=None,
    ) -> JobSnapshot:
        """Wait for tracked job updates until the job succeeds or fails."""
        timeout_seconds = max(
            1,
            submission.config.engine.execution.task_timeout_minutes * 60,
        )
        deadline = time.monotonic() + timeout_seconds
        last_version = -1
        last_progress_text: str | None = None
        last_preview_image_url: str | None = None

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Task timeout: Maximum wait time exceeded")

            snapshot = self._manager.wait_for_snapshot(
                submission.job_id,
                after_version=last_version,
                timeout_s=remaining,
            )

            if snapshot.version != last_version:
                if snapshot.status in {JobStatus.SUCCEEDED, JobStatus.FAILED}:
                    last_version = snapshot.version
                elif self._should_defer_preview_only_snapshot(
                    snapshot,
                    last_preview_image_url=last_preview_image_url,
                ):
                    last_version = snapshot.version
                else:
                    progress_text = snapshot.progress_text
                    if progress_text_transformer is not None:
                        progress_text = progress_text_transformer(progress_text)
                    (
                        last_progress_text,
                        last_preview_image_url,
                    ) = self._report_progress(
                        progress_text,
                        snapshot.preview_image_url,
                        last_progress_text=last_progress_text,
                        last_preview_image_url=last_preview_image_url,
                        progress_reporter=progress_reporter,
                        config=submission.config,
                        context=context,
                    )
                    last_version = snapshot.version

            if snapshot.status == JobStatus.SUCCEEDED:
                return self._manager.get_job(submission.job_id)

            if snapshot.status == JobStatus.FAILED:
                fail_reason = snapshot.fail_reason or "Unknown error"
                raise JobFailedError(f"Task failed: {fail_reason}")

    def _build_video_result(
        self,
        snapshot: JobSnapshot,
        *,
        submission: RuntimeSubmission,
    ) -> RuntimeVideoResult:
        """Build one native Comfy video result from a completed job snapshot."""
        output = snapshot.output
        if not isinstance(output, VideoOutput):
            raise RuntimeAdapterError(
                "Animate completed without returning a video artifact."
            )

        video_source = output.local_file_path or output.video_url or output.website_url
        if not video_source:
            raise RuntimeAdapterError(
                "Animate completed without returning a video artifact."
            )

        return RuntimeVideoResult(
            job=snapshot,
            video_url=output.video_url or output.website_url or video_source,
            video_value=self._video_loader.fetch_video(
                video_source,
                config=submission.config,
            ),
        )

    def _extract_describe_text(self, snapshot: JobSnapshot) -> str:
        """Return the final describe text from one completed public job snapshot."""
        if isinstance(snapshot.output, TextOutput) and snapshot.output.text:
            return snapshot.output.text
        if snapshot.prompt_text:
            return snapshot.prompt_text
        raise RuntimeAdapterError("Describe completed without returning prompt text.")

    def _extract_image_source(self, snapshot: JobSnapshot) -> str:
        """Return the local path or remote URL for one completed image result."""
        output = snapshot.output
        if not isinstance(output, ImageOutput):
            raise RuntimeAdapterError("Generated image output was missing.")
        image_source = output.local_file_path or output.image_url
        if not image_source:
            raise RuntimeAdapterError("Generated image output was missing.")
        return image_source

    def _resolve_upscale_index(
        self,
        *,
        resolved_index: int,
        mode: MidjourneyUpscaleMode,
    ) -> int:
        """Return the public submission index for one upscale mode."""
        if mode is MidjourneyUpscaleMode.STANDARD:
            if resolved_index not in {1, 2, 3, 4}:
                raise RuntimeAdapterError(
                    "Image was recognized, but Standard Upscale requires a Midjourney grid tile."
                )
            return resolved_index

        if resolved_index not in {0, 1, 2, 3, 4}:
            raise RuntimeAdapterError(
                "Image was recognized, but this Upscale mode requires one recognized Midjourney image."
            )
        return self._normalize_follow_up_submission_index(resolved_index)

    def _normalize_follow_up_submission_index(self, resolved_index: int) -> int:
        """Normalize one recognized image index into a concrete follow-up submission index."""
        if resolved_index == 0:
            return 1
        return resolved_index

    def _resolve_recognized_source_context(
        self,
        *,
        image_bytes: bytes,
    ):
        """Resolve one recognized Midjourney image into the stored Mutiny job context."""
        resolved_context = self._manager.resolve_image_context(image_bytes)
        if resolved_context is None:
            raise RuntimeAdapterError(
                "Image was not recognized as a cached Midjourney image by Mutiny."
            )
        return resolved_context

    def _resolve_variation_index(
        self,
        *,
        resolved_index: int,
        mode: MidjourneyVariationMode,
    ) -> int:
        """Return the required tile index for one variation mode."""
        del mode
        if resolved_index not in {1, 2, 3, 4}:
            raise RuntimeAdapterError(
                "Image was recognized, but Midjourney Variation requires a Midjourney grid tile."
            )
        return resolved_index

    def _normalize_zoom_factor(self, zoom_factor: float) -> float:
        """Normalize one user-entered zoom factor into the public submission range."""
        if not math.isfinite(zoom_factor):
            raise RuntimeAdapterError(
                "Midjourney Zoom factor must be between 1.00 and 2.00."
            )

        try:
            normalized = Decimal(str(zoom_factor)).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )
        except (InvalidOperation, ValueError) as exc:
            raise RuntimeAdapterError(
                "Midjourney Zoom factor must be between 1.00 and 2.00."
            ) from exc

        if normalized < Decimal("1.00") or normalized > Decimal("2.00"):
            raise RuntimeAdapterError(
                "Midjourney Zoom factor must be between 1.00 and 2.00."
            )
        return float(normalized)

    def _normalize_video_progress_text(self, progress_text: str | None) -> str | None:
        """Normalize animate progress text into one Comfy-friendly percentage when possible."""
        if not progress_text:
            return progress_text

        percent_index = progress_text.find("%")
        if percent_index == -1:
            return progress_text

        digits = []
        for character in reversed(progress_text[:percent_index]):
            if character.isdigit():
                digits.append(character)
                continue
            if digits:
                break
        if not digits:
            return progress_text
        return f"{''.join(reversed(digits))}%"

    def _should_defer_preview_only_snapshot(
        self,
        snapshot: JobTrackingSnapshot,
        *,
        last_preview_image_url: str | None,
    ) -> bool:
        """Return whether one non-terminal preview-only snapshot should wait for progress text."""
        return (
            snapshot.status == JobStatus.IN_PROGRESS
            and snapshot.progress_text is None
            and bool(snapshot.preview_image_url)
            and snapshot.preview_image_url != last_preview_image_url
        )

    def _report_progress(
        self,
        progress_text: str | None,
        preview_image_url: str | None,
        *,
        last_progress_text: str | None,
        last_preview_image_url: str | None,
        progress_reporter,
        config,
        context: RuntimeActionContext,
    ) -> tuple[str | None, str | None]:
        """Forward new progress updates to ComfyUI without breaking the main wait."""
        if progress_reporter is None:
            return progress_text, preview_image_url

        if (
            progress_text == last_progress_text
            and preview_image_url == last_preview_image_url
        ):
            return last_progress_text, last_preview_image_url

        preview_payload = None
        if preview_image_url and preview_image_url != last_preview_image_url:
            try:
                preview_payload = self._image_loader.fetch_bytes(
                    preview_image_url,
                    config=config,
                )
            except Exception:
                logger.warning(
                    "Failed to fetch progress preview %s preview_image_url=%s",
                    format_runtime_context(context),
                    preview_image_url,
                    exc_info=True,
                )

        try:
            progress_reporter(progress_text, preview_payload)
        except Exception:
            logger.warning(
                "Progress reporter failed %s progress=%s has_preview=%s",
                format_runtime_context(context),
                progress_text or "-",
                preview_payload is not None,
                exc_info=True,
            )

        return progress_text, preview_image_url

    def _raise_runtime_error(
        self,
        exc: Exception,
        context: RuntimeActionContext,
    ) -> None:
        """Log one runtime failure with context and raise the normalized error."""
        translated = translate_runtime_exception(exc)
        if isinstance(exc, RuntimeAdapterError):
            logger.error(
                "Mutiny runtime action failed %s error=%s",
                format_runtime_context(context),
                translated,
            )
        else:
            logger.exception(
                "Unexpected Mutiny runtime action failure %s",
                format_runtime_context(context),
            )
        raise translated from exc


def build_default_runtime_service() -> MutinyRuntimeService:
    """Construct the process-wide default runtime service."""
    return MutinyRuntimeService(MutinyRuntimeManager(get_settings_service()))


def get_runtime_service() -> MutinyRuntimeService:
    """Return the process-wide runtime service used by exported nodes."""
    global _DEFAULT_RUNTIME_SERVICE
    if _DEFAULT_RUNTIME_SERVICE is None:
        _DEFAULT_RUNTIME_SERVICE = build_default_runtime_service()
    return _DEFAULT_RUNTIME_SERVICE


def close_runtime_service() -> None:
    """Close the process-wide runtime service when it exists."""
    if _DEFAULT_RUNTIME_SERVICE is not None:
        _DEFAULT_RUNTIME_SERVICE.close()


def reset_runtime_service() -> None:
    """Discard the process-wide runtime service after closing it."""
    global _DEFAULT_RUNTIME_SERVICE
    if _DEFAULT_RUNTIME_SERVICE is not None:
        _DEFAULT_RUNTIME_SERVICE.close()
        _DEFAULT_RUNTIME_SERVICE = None


__all__ = [
    "MutinyRuntimeService",
    "build_default_runtime_service",
    "close_runtime_service",
    "get_runtime_service",
    "reset_runtime_service",
]
