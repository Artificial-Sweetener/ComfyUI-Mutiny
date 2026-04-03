"""Own the shared Mutiny lifecycle and background event consumption."""

from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Awaitable, Callable
from typing import TypeVar

from mutiny import Config, JobSnapshot, Mutiny

from ..settings.service import SettingsService
from .errors import RuntimeNotReadyError
from .models import (
    MidjourneyAnimateMotion,
    MidjourneyPanDirection,
    MidjourneyUpscaleMode,
    MidjourneyVariationMode,
    ResolvedMidjourneyImageContext,
    RuntimeImagineImageInputs,
    RuntimeSubmission,
)
from .tracker import JobEventTracker

logger = logging.getLogger(__name__)

_READY_TIMEOUT_SECONDS = 60
_T = TypeVar("_T")


class MutinyRuntimeManager:
    """Manage one shared Mutiny client on a dedicated background event loop."""

    def __init__(
        self,
        settings_service: SettingsService,
        *,
        client_factory: Callable[[Config], Mutiny] = Mutiny,
        ready_timeout_seconds: int = _READY_TIMEOUT_SECONDS,
    ) -> None:
        """Store the collaborators used to build and run the shared Mutiny client."""
        self._settings_service = settings_service
        self._client_factory = client_factory
        self._ready_timeout_seconds = ready_timeout_seconds
        self._tracker = JobEventTracker()

        self._thread_lock = threading.RLock()
        self._loop_ready = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_thread: threading.Thread | None = None
        self._client: Mutiny | None = None
        self._config_signature: dict[str, object] | None = None
        self._event_task: asyncio.Task[None] | None = None

    def submit_imagine(
        self,
        prompt_text: str,
        *,
        image_inputs: RuntimeImagineImageInputs | None = None,
    ) -> RuntimeSubmission:
        """Submit one imagine request and return plugin runtime metadata."""
        return self._run_on_loop(
            self._submit_imagine_async(prompt_text, image_inputs=image_inputs)
        )

    def submit_upscale(
        self,
        job_id: str,
        *,
        index: int,
        mode: MidjourneyUpscaleMode,
    ) -> RuntimeSubmission:
        """Submit one upscale-family follow-up request."""
        return self._run_on_loop(
            self._submit_upscale_async(job_id, index=index, mode=mode)
        )

    def submit_variation(
        self,
        job_id: str,
        *,
        index: int,
        mode: MidjourneyVariationMode,
    ) -> RuntimeSubmission:
        """Submit one variation-family follow-up request."""
        return self._run_on_loop(
            self._submit_variation_async(job_id, index=index, mode=mode)
        )

    def submit_pan(
        self,
        job_id: str,
        *,
        direction: MidjourneyPanDirection,
        index: int | None = None,
    ) -> RuntimeSubmission:
        """Submit one pan follow-up request."""
        return self._run_on_loop(
            self._submit_pan_async(job_id, direction=direction, index=index)
        )

    def submit_zoom(
        self,
        job_id: str,
        *,
        factor: float,
        prompt_text: str | None = None,
        index: int | None = None,
    ) -> RuntimeSubmission:
        """Submit one zoom follow-up request."""
        return self._run_on_loop(
            self._submit_zoom_async(
                job_id,
                factor=factor,
                prompt_text=prompt_text,
                index=index,
            )
        )

    def submit_vary_region(
        self,
        *,
        source_image_data_url: str,
        mask_data_url: str,
        prompt_text: str,
    ) -> RuntimeSubmission:
        """Submit one vary-region request."""
        return self._run_on_loop(
            self._submit_vary_region_async(
                source_image_data_url=source_image_data_url,
                mask_data_url=mask_data_url,
                prompt_text=prompt_text,
            )
        )

    def submit_animate(
        self,
        *,
        start_frame_data_url: str,
        motion: MidjourneyAnimateMotion,
        end_frame_data_url: str | None = None,
        prompt_text: str = "",
        batch_size: int | None = None,
    ) -> RuntimeSubmission:
        """Submit one animate request."""
        return self._run_on_loop(
            self._submit_animate_async(
                start_frame_data_url=start_frame_data_url,
                motion=motion,
                end_frame_data_url=end_frame_data_url,
                prompt_text=prompt_text,
                batch_size=batch_size,
            )
        )

    def submit_extend(
        self,
        *,
        video_bytes: bytes,
        motion: MidjourneyAnimateMotion,
    ) -> RuntimeSubmission:
        """Submit one animate-extend request."""
        return self._run_on_loop(
            self._submit_extend_async(video_bytes=video_bytes, motion=motion)
        )

    def submit_describe(self, *, image_data_url: str) -> RuntimeSubmission:
        """Submit one describe request."""
        return self._run_on_loop(
            self._submit_describe_async(image_data_url=image_data_url)
        )

    def get_job(self, job_id: str) -> JobSnapshot:
        """Look up the latest public job snapshot by id."""
        return self._run_on_loop(self._get_job_async(job_id))

    def resolve_image_context(
        self, image_bytes: bytes
    ) -> ResolvedMidjourneyImageContext | None:
        """Resolve one recognized image back to its Midjourney job context."""
        return self._run_on_loop(self._resolve_image_context_async(image_bytes))

    def split_image_result(self, job_id: str, image_bytes: bytes):
        """Split one image result into the public tile projection."""
        return self._run_on_loop(self._split_image_result_async(job_id, image_bytes))

    def wait_for_snapshot(
        self,
        job_id: str,
        *,
        after_version: int,
        timeout_s: float,
    ):
        """Wait synchronously for the next tracked change to one job."""
        return self._tracker.wait_for_update(
            job_id,
            after_version=after_version,
            timeout_s=timeout_s,
        )

    def close(self) -> None:
        """Shut down the shared Mutiny client and its event loop thread."""
        loop = self._loop
        if loop is not None and loop.is_running():
            self._run_on_loop(self._close_client_async())
            loop.call_soon_threadsafe(loop.stop)

        thread = self._loop_thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=5)

        with self._thread_lock:
            self._client = None
            self._config_signature = None
            self._event_task = None
            self._loop = None
            self._loop_thread = None
            self._loop_ready.clear()
            self._tracker.reset()

    async def _submit_imagine_async(
        self,
        prompt_text: str,
        *,
        image_inputs: RuntimeImagineImageInputs | None = None,
    ) -> RuntimeSubmission:
        """Submit one imagine request after ensuring the shared client is ready."""
        client, config = await self._ensure_client_started()
        kwargs = _build_imagine_kwargs(image_inputs)
        handle = await client.imagine(prompt_text, **kwargs)
        await self._seed_tracker_async(handle.id)
        return RuntimeSubmission(job_id=handle.id, config=config)

    async def _submit_upscale_async(
        self,
        job_id: str,
        *,
        index: int,
        mode: MidjourneyUpscaleMode,
    ) -> RuntimeSubmission:
        """Submit one public upscale request."""
        client, config = await self._ensure_client_started()
        handle = await client.upscale(
            job_id, index=index, mode=_to_upscale_mode_value(mode)
        )
        await self._seed_tracker_async(handle.id)
        return RuntimeSubmission(job_id=handle.id, config=config)

    async def _submit_variation_async(
        self,
        job_id: str,
        *,
        index: int,
        mode: MidjourneyVariationMode,
    ) -> RuntimeSubmission:
        """Submit one public variation request."""
        client, config = await self._ensure_client_started()
        handle = await client.vary(
            job_id, index=index, mode=_to_variation_mode_value(mode)
        )
        await self._seed_tracker_async(handle.id)
        return RuntimeSubmission(job_id=handle.id, config=config)

    async def _submit_pan_async(
        self,
        job_id: str,
        *,
        direction: MidjourneyPanDirection,
        index: int | None = None,
    ) -> RuntimeSubmission:
        """Submit one public pan request."""
        client, config = await self._ensure_client_started()
        handle = await client.pan(
            job_id,
            direction=_to_pan_direction_value(direction),
            index=index,
        )
        await self._seed_tracker_async(handle.id)
        return RuntimeSubmission(job_id=handle.id, config=config)

    async def _submit_zoom_async(
        self,
        job_id: str,
        *,
        factor: float,
        prompt_text: str | None = None,
        index: int | None = None,
    ) -> RuntimeSubmission:
        """Submit one public zoom request."""
        client, config = await self._ensure_client_started()
        handle = await client.zoom(
            job_id,
            factor=factor,
            prompt=prompt_text,
            index=index,
        )
        await self._seed_tracker_async(handle.id)
        return RuntimeSubmission(job_id=handle.id, config=config)

    async def _submit_vary_region_async(
        self,
        *,
        source_image_data_url: str,
        mask_data_url: str,
        prompt_text: str,
    ) -> RuntimeSubmission:
        """Submit one public vary-region request."""
        client, config = await self._ensure_client_started()
        handle = await client.vary_region(
            source_image_data_url,
            mask_data_url,
            prompt=prompt_text,
        )
        await self._seed_tracker_async(handle.id)
        return RuntimeSubmission(job_id=handle.id, config=config)

    async def _submit_describe_async(self, *, image_data_url: str) -> RuntimeSubmission:
        """Submit one public describe request."""
        client, config = await self._ensure_client_started()
        handle = await client.describe(image_data_url)
        await self._seed_tracker_async(handle.id)
        return RuntimeSubmission(job_id=handle.id, config=config)

    async def _submit_animate_async(
        self,
        *,
        start_frame_data_url: str,
        motion: MidjourneyAnimateMotion,
        end_frame_data_url: str | None = None,
        prompt_text: str = "",
        batch_size: int | None = None,
    ) -> RuntimeSubmission:
        """Submit one public animate request."""
        client, config = await self._ensure_client_started()
        handle = await client.animate(
            start_frame_data_url,
            end_frame=end_frame_data_url,
            prompt=prompt_text,
            motion=_to_motion_level(motion),
            batch_size=batch_size,
        )
        await self._seed_tracker_async(handle.id)
        return RuntimeSubmission(job_id=handle.id, config=config)

    async def _submit_extend_async(
        self,
        *,
        video_bytes: bytes,
        motion: MidjourneyAnimateMotion,
    ) -> RuntimeSubmission:
        """Submit one public animate-extend request."""
        client, config = await self._ensure_client_started()
        handle = await client.extend(video=video_bytes, motion=_to_motion_level(motion))
        await self._seed_tracker_async(handle.id)
        return RuntimeSubmission(job_id=handle.id, config=config)

    async def _get_job_async(self, job_id: str) -> JobSnapshot:
        """Fetch the latest public job snapshot and refresh the local tracker."""
        client, _config = await self._ensure_client_started()
        snapshot = await client.get_job(job_id)
        self._tracker.record_job_snapshot(snapshot)
        return snapshot

    async def _resolve_image_context_async(
        self, image_bytes: bytes
    ) -> ResolvedMidjourneyImageContext | None:
        """Resolve one image to the Mutiny job id and source index it belongs to."""
        client, _config = await self._ensure_client_started()
        resolution = client.resolve_image(image_bytes)
        if resolution is None:
            return None
        return ResolvedMidjourneyImageContext(
            job_id=resolution.job_id,
            index=resolution.index,
        )

    async def _split_image_result_async(self, job_id: str, image_bytes: bytes):
        """Split one completed image into public tile projections."""
        client, _config = await self._ensure_client_started()
        return tuple(client.split_image_result(job_id, image_bytes))

    async def _seed_tracker_async(self, job_id: str) -> None:
        """Prime the event tracker with the current public job snapshot."""
        if self._client is None:
            return

        try:
            snapshot = await self._client.get_job(job_id)
        except RuntimeError:
            logger.debug("Skipping tracker seed for unknown job_id=%s", job_id)
            return

        self._tracker.record_job_snapshot(snapshot)

    async def _ensure_client_started(self) -> tuple[Mutiny, Config]:
        """Create or reuse the shared Mutiny client for the current settings snapshot."""
        config = self._settings_service.build_mutiny_config()
        signature = config.as_dict()

        recreate_client = (
            self._client is None
            or self._config_signature != signature
            or self._event_task is None
            or self._event_task.done()
        )

        if recreate_client:
            await self._close_client_async()
            self._tracker.reset()
            self._client = self._client_factory(config)
            self._config_signature = signature
            await self._client.start()
            ready = await self._client.wait_ready(timeout_s=self._ready_timeout_seconds)
            if not ready:
                await self._client.close()
                self._client = None
                self._config_signature = None
                raise RuntimeNotReadyError(
                    "Mutiny did not become ready before the timeout expired."
                )
            self._event_task = asyncio.create_task(self._consume_events())
            return self._client, config

        await self._client.start()
        ready = await self._client.wait_ready(timeout_s=self._ready_timeout_seconds)
        if not ready:
            raise RuntimeNotReadyError(
                "Mutiny did not become ready before the timeout expired."
            )
        return self._client, config

    async def _consume_events(self) -> None:
        """Drain Mutiny's public event firehose into the tracker's thread-safe store."""
        if self._client is None:
            return

        try:
            async for event in self._client.events():
                self._tracker.record_event(event)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Mutiny event consumption failed.")
            self._tracker.fail_all(exc)
            raise

    async def _close_client_async(self) -> None:
        """Stop event consumption and close the current Mutiny client if present."""
        event_task = self._event_task
        self._event_task = None

        if event_task is not None:
            event_task.cancel()
            try:
                await event_task
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.exception("Mutiny event task shutdown failed.")

        client = self._client
        self._client = None
        self._config_signature = None

        if client is not None:
            await client.close()

    def _run_on_loop(self, coroutine: Awaitable[_T]) -> _T:
        """Run one coroutine on the background loop and return its result."""
        self._ensure_loop_thread()
        if self._loop is None:
            raise RuntimeError("Mutiny runtime loop was not initialized.")
        future = asyncio.run_coroutine_threadsafe(coroutine, self._loop)
        return future.result()

    def _ensure_loop_thread(self) -> None:
        """Start the background event loop thread if it is not already running."""
        with self._thread_lock:
            if self._loop_thread is not None and self._loop_thread.is_alive():
                return

            self._loop_ready.clear()

            def run_loop() -> None:
                """Run the dedicated asyncio loop that owns the shared client."""
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                self._loop = loop
                self._loop_ready.set()

                try:
                    loop.run_forever()
                finally:
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()
                    if pending:
                        loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )
                    loop.close()

            self._loop_thread = threading.Thread(
                target=run_loop,
                name="ComfyUI-MutinyRuntime",
                daemon=True,
            )
            self._loop_thread.start()
            self._loop_ready.wait(timeout=5)

            if self._loop is None:
                raise RuntimeError("Failed to start the Mutiny runtime loop.")


def _build_imagine_kwargs(
    image_inputs: RuntimeImagineImageInputs | None,
) -> dict[str, object]:
    """Translate plugin imagine inputs into Mutiny's public keyword arguments."""
    if image_inputs is None:
        return {}

    return {
        "prompt_images": image_inputs.prompt_images,
        "style_references": image_inputs.style_reference_images,
        "character_references": image_inputs.character_reference_images,
        "omni_reference": image_inputs.omni_reference_image,
    }


def _to_upscale_mode_value(mode: MidjourneyUpscaleMode) -> str:
    """Translate the plugin runtime upscale enum into Mutiny's public mode string."""
    return mode.value


def _to_variation_mode_value(mode: MidjourneyVariationMode) -> str:
    """Translate the plugin runtime variation enum into Mutiny's public mode string."""
    return mode.value


def _to_pan_direction_value(direction: MidjourneyPanDirection) -> str:
    """Translate the plugin runtime pan enum into Mutiny's public direction string."""
    return direction.value


def _to_motion_level(motion: MidjourneyAnimateMotion) -> str:
    """Translate the plugin runtime animate enum into Mutiny's public motion level."""
    return motion.value


__all__ = ["MutinyRuntimeManager"]
