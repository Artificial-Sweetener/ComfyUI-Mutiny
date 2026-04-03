"""Test the shared Mutiny runtime adapter and lifecycle manager."""

from __future__ import annotations

import asyncio
import io
import sys
from dataclasses import dataclass

import numpy as np
import pytest
from mutiny import (
    Config,
    ImageOutput,
    ImageResolution,
    ImageTile,
    JobHandle,
    JobSnapshot,
    JobStatus,
    ProgressUpdate,
    TextOutput,
    VideoOutput,
)
from PIL import Image


class StaticTokenProvider:
    """Provide a stable token for runtime tests without keyring access."""

    def get_token(self) -> str:
        """Return a deterministic Discord token for config construction."""
        return "discord-token"


class FakeSettingsService:
    """Return a prebuilt Mutiny config snapshot on demand."""

    def __init__(self, config: Config) -> None:
        """Store the config snapshot returned to the runtime manager."""
        self._config = config

    def build_mutiny_config(self) -> Config:
        """Return the runtime config snapshot."""
        return self._config


@dataclass(frozen=True)
class SubmissionScript:
    """Describe one fake public submission plus the events it should emit."""

    handle: JobHandle
    initial_snapshot: JobSnapshot
    events: tuple[tuple[float, ProgressUpdate | JobSnapshot], ...] = ()


class FakeMutinyClient:
    """Provide the public Mutiny surface exercised by the runtime adapter."""

    _STOP = object()

    def __init__(
        self,
        config: Config,
        *,
        ready_result: bool = True,
        imagine_scripts: list[SubmissionScript] | None = None,
        upscale_scripts: list[SubmissionScript] | None = None,
        vary_scripts: list[SubmissionScript] | None = None,
        pan_scripts: list[SubmissionScript] | None = None,
        zoom_scripts: list[SubmissionScript] | None = None,
        vary_region_scripts: list[SubmissionScript] | None = None,
        animate_scripts: list[SubmissionScript] | None = None,
        extend_scripts: list[SubmissionScript] | None = None,
        describe_scripts: list[SubmissionScript] | None = None,
        image_resolution_by_bytes: dict[bytes, ImageResolution | None] | None = None,
        image_tiles_by_job_id: dict[str, tuple[ImageTile, ...]] | None = None,
    ) -> None:
        """Store the configured scripts and initialize runtime counters."""
        self.config = config
        self.ready_result = ready_result
        self.imagine_scripts = list(imagine_scripts or [])
        self.upscale_scripts = list(upscale_scripts or [])
        self.vary_scripts = list(vary_scripts or [])
        self.pan_scripts = list(pan_scripts or [])
        self.zoom_scripts = list(zoom_scripts or [])
        self.vary_region_scripts = list(vary_region_scripts or [])
        self.animate_scripts = list(animate_scripts or [])
        self.extend_scripts = list(extend_scripts or [])
        self.describe_scripts = list(describe_scripts or [])
        self.image_resolution_by_bytes = dict(image_resolution_by_bytes or {})
        self.image_tiles_by_job_id = dict(image_tiles_by_job_id or {})

        self.jobs: dict[str, JobSnapshot] = {}
        self.start_calls = 0
        self.close_calls = 0
        self.wait_ready_calls = 0
        self.imagine_calls: list[dict[str, object]] = []
        self.upscale_calls: list[dict[str, object]] = []
        self.vary_calls: list[dict[str, object]] = []
        self.pan_calls: list[dict[str, object]] = []
        self.zoom_calls: list[dict[str, object]] = []
        self.vary_region_calls: list[dict[str, object]] = []
        self.animate_calls: list[dict[str, object]] = []
        self.extend_calls: list[dict[str, object]] = []
        self.describe_calls: list[dict[str, object]] = []
        self.resolve_image_calls: list[bytes] = []
        self.split_image_result_calls: list[dict[str, object]] = []
        self._events: asyncio.Queue[object] = asyncio.Queue()

    async def start(self) -> None:
        """Record start calls without real network or gateway work."""
        self.start_calls += 1

    async def wait_ready(self, timeout_s: int | None = None) -> bool:
        """Return the configured ready-state result."""
        self.wait_ready_calls += 1
        return self.ready_result

    async def close(self) -> None:
        """Record shutdown and terminate the fake event stream."""
        self.close_calls += 1
        await self._events.put(self._STOP)

    async def events(self, job_id: str | None = None):
        """Yield scripted events until the runtime closes the client."""
        del job_id
        while True:
            item = await self._events.get()
            if item is self._STOP:
                return
            yield item

    async def imagine(
        self,
        prompt: str,
        *,
        prompt_images=(),
        style_references=(),
        character_references=(),
        omni_reference=None,
        state: str | None = None,
    ) -> JobHandle:
        """Record imagine submissions and schedule their scripted events."""
        self.imagine_calls.append(
            {
                "prompt": prompt,
                "prompt_images": prompt_images,
                "style_references": style_references,
                "character_references": character_references,
                "omni_reference": omni_reference,
                "state": state,
            }
        )
        return self._submit(self.imagine_scripts)

    async def upscale(
        self,
        job_id: str,
        *,
        index: int,
        mode: str = "standard",
        state: str | None = None,
    ) -> JobHandle:
        """Record public upscale submissions and schedule their scripted events."""
        self.upscale_calls.append(
            {
                "job_id": job_id,
                "index": index,
                "mode": mode,
                "state": state,
            }
        )
        return self._submit(self.upscale_scripts)

    async def vary(
        self,
        job_id: str,
        *,
        index: int,
        mode: str = "standard",
        state: str | None = None,
    ) -> JobHandle:
        """Record public vary submissions and schedule their scripted events."""
        self.vary_calls.append(
            {
                "job_id": job_id,
                "index": index,
                "mode": mode,
                "state": state,
            }
        )
        return self._submit(self.vary_scripts)

    async def pan(
        self,
        job_id: str,
        *,
        index: int | None = None,
        direction: str,
        state: str | None = None,
    ) -> JobHandle:
        """Record public pan submissions and schedule their scripted events."""
        self.pan_calls.append(
            {
                "job_id": job_id,
                "index": index,
                "direction": direction,
                "state": state,
            }
        )
        return self._submit(self.pan_scripts)

    async def zoom(
        self,
        job_id: str,
        *,
        index: int | None = None,
        factor: float,
        prompt: str | None = None,
        state: str | None = None,
    ) -> JobHandle:
        """Record public zoom submissions and schedule their scripted events."""
        self.zoom_calls.append(
            {
                "job_id": job_id,
                "index": index,
                "factor": factor,
                "prompt": prompt,
                "state": state,
            }
        )
        return self._submit(self.zoom_scripts)

    async def vary_region(
        self,
        image,
        mask,
        *,
        prompt: str | None = None,
        state: str | None = None,
    ) -> JobHandle:
        """Record public vary-region submissions and schedule their scripted events."""
        self.vary_region_calls.append(
            {
                "image": image,
                "mask": mask,
                "prompt": prompt,
                "state": state,
            }
        )
        return self._submit(self.vary_region_scripts)

    async def describe(self, image, *, state: str | None = None) -> JobHandle:
        """Record public describe submissions and schedule their scripted events."""
        self.describe_calls.append({"image": image, "state": state})
        return self._submit(self.describe_scripts)

    async def animate(
        self,
        start_frame,
        *,
        end_frame=None,
        prompt: str | None = None,
        motion: str = "low",
        batch_size: int | None = None,
        state: str | None = None,
    ) -> JobHandle:
        """Record public animate submissions and schedule their scripted events."""
        self.animate_calls.append(
            {
                "start_frame": start_frame,
                "end_frame": end_frame,
                "prompt": prompt,
                "motion": motion,
                "batch_size": batch_size,
                "state": state,
            }
        )
        return self._submit(self.animate_scripts)

    async def extend(
        self,
        *,
        job_id: str | None = None,
        video=None,
        motion: str = "low",
        state: str | None = None,
    ) -> JobHandle:
        """Record public extend submissions and schedule their scripted events."""
        self.extend_calls.append(
            {
                "job_id": job_id,
                "video": video,
                "motion": motion,
                "state": state,
            }
        )
        return self._submit(self.extend_scripts)

    async def get_job(self, job_id: str) -> JobSnapshot:
        """Return the latest stored public snapshot for one job id."""
        snapshot = self.jobs.get(job_id)
        if snapshot is None:
            raise RuntimeError("Job not found")
        return snapshot

    def resolve_image(self, image: bytes) -> ImageResolution | None:
        """Return the configured image-resolution result for one byte payload."""
        self.resolve_image_calls.append(image)
        return self.image_resolution_by_bytes.get(image)

    def split_image_result(self, job_id: str, image: bytes) -> tuple[ImageTile, ...]:
        """Return the configured split-tile payload for one completed image."""
        self.split_image_result_calls.append({"job_id": job_id, "image": image})
        return self.image_tiles_by_job_id.get(job_id, ())

    def _submit(self, scripts: list[SubmissionScript]) -> JobHandle:
        """Pop one scripted submission, seed the job store, and queue its events."""
        script = scripts.pop(0)
        self.jobs[script.handle.id] = script.initial_snapshot
        self._schedule_events(script.events)
        return script.handle

    def _schedule_events(
        self,
        events: tuple[tuple[float, ProgressUpdate | JobSnapshot], ...],
    ) -> None:
        """Queue the scripted progress and snapshot updates on the active event loop."""
        loop = asyncio.get_running_loop()
        for delay_s, event in events:
            loop.create_task(self._emit_event(delay_s, event))

    async def _emit_event(
        self,
        delay_s: float,
        event: ProgressUpdate | JobSnapshot,
    ) -> None:
        """Sleep for the configured delay, then publish one event."""
        await asyncio.sleep(delay_s)
        if isinstance(event, JobSnapshot):
            self.jobs[event.id] = event
        await self._events.put(event)


class FakeClientFactory:
    """Create fake Mutiny clients and retain them for later assertions."""

    def __init__(self, **client_kwargs) -> None:
        """Store the fake client construction arguments."""
        self._client_kwargs = client_kwargs
        self.created_clients: list[FakeMutinyClient] = []

    def __call__(self, config: Config) -> FakeMutinyClient:
        """Build and record one fake Mutiny client."""
        client = FakeMutinyClient(config, **self._client_kwargs)
        self.created_clients.append(client)
        return client


class RecordingImageLoader:
    """Return deterministic bytes for image fetches while recording sources."""

    def __init__(self, payloads: dict[str, bytes]) -> None:
        """Store the payload returned for each requested image source."""
        self._payloads = dict(payloads)
        self.calls: list[str] = []

    def fetch_bytes(self, image_url: str, *, config: Config) -> bytes:
        """Return the configured bytes for one image URL or path."""
        del config
        self.calls.append(image_url)
        return self._payloads[image_url]


class RecordingVideoLoader:
    """Return deterministic video values while recording sources."""

    def __init__(self, values: dict[str, object]) -> None:
        """Store the video value returned for each requested source."""
        self._values = dict(values)
        self.calls: list[str] = []

    def fetch_video(self, video_url: str, *, config: Config) -> object:
        """Return the configured native video value for one source."""
        del config
        self.calls.append(video_url)
        return self._values[video_url]


def _config() -> Config:
    """Build a deterministic Mutiny config snapshot for runtime tests."""
    return Config.create(
        token_provider=StaticTokenProvider(),
        guild_id="guild-1",
        channel_id="channel-1",
    )


def _encode_png(image: np.ndarray) -> bytes:
    """Encode one numpy RGB image into PNG bytes."""
    buffer = io.BytesIO()
    Image.fromarray(image.astype(np.uint8)).save(buffer, format="PNG")
    return buffer.getvalue()


def _snapshot(
    job_id: str,
    *,
    kind: str,
    status: JobStatus,
    progress_text: str | None = None,
    preview_image_url: str | None = None,
    fail_reason: str | None = None,
    prompt_text: str | None = None,
    output=None,
) -> JobSnapshot:
    """Construct one public job snapshot with explicit fields."""
    return JobSnapshot(
        id=job_id,
        kind=kind,
        status=status,
        progress_text=progress_text,
        preview_image_url=preview_image_url,
        fail_reason=fail_reason,
        prompt_text=prompt_text,
        output=output,
    )


def _tile(job_id: str, index: int, image: np.ndarray) -> ImageTile:
    """Build one public image tile from deterministic image data."""
    return ImageTile(job_id=job_id, index=index, image_bytes=_encode_png(image))


def _runtime_module(plugin_package):
    """Return the loaded runtime module for the isolated plugin package."""
    return sys.modules[f"{plugin_package.__name__}.runtime"]


def test_runtime_service_imagine_forwards_public_image_inputs_and_split_tiles(
    plugin_package,
    sample_grid_image,
):
    """Route imagine submissions through public keyword channels and tile helpers."""
    runtime_module = _runtime_module(plugin_package)
    final_job_id = "job-imagine"
    preview_url = "https://example.invalid/preview.png"
    final_url = "https://example.invalid/final.png"
    preview_bytes = _encode_png(sample_grid_image[:2, :2, :])
    final_bytes = _encode_png(sample_grid_image)
    factory = FakeClientFactory(
        imagine_scripts=[
            SubmissionScript(
                handle=JobHandle(id=final_job_id),
                initial_snapshot=_snapshot(
                    final_job_id,
                    kind="imagine",
                    status=JobStatus.SUBMITTED,
                ),
                events=(
                    (
                        0.0,
                        ProgressUpdate(
                            job_id=final_job_id,
                            status_text="Rendering",
                            preview_image_url=preview_url,
                        ),
                    ),
                    (
                        0.1,
                        _snapshot(
                            final_job_id,
                            kind="imagine",
                            status=JobStatus.SUCCEEDED,
                            output=ImageOutput(image_url=final_url),
                        ),
                    ),
                ),
            )
        ],
        image_tiles_by_job_id={
            final_job_id: (
                _tile(final_job_id, 1, sample_grid_image[:2, :2, :]),
                _tile(final_job_id, 2, sample_grid_image[:2, 2:, :]),
            )
        },
    )
    service = runtime_module.MutinyRuntimeService(
        runtime_module.MutinyRuntimeManager(
            FakeSettingsService(_config()),
            client_factory=factory,
        ),
        image_loader=RecordingImageLoader(
            {
                preview_url: preview_bytes,
                final_url: final_bytes,
            }
        ),
    )
    progress_updates: list[tuple[str | None, bytes | None]] = []

    result = service.imagine_and_wait(
        "castle prompt",
        node_name="MidjourneyV7Request",
        image_inputs=runtime_module.RuntimeImagineImageInputs(
            prompt_images=("prompt-a",),
            style_reference_images=("style-a",),
            character_reference_images=("character-a",),
            omni_reference_image="omni-a",
        ),
        progress_reporter=lambda text, preview: progress_updates.append(
            (text, preview)
        ),
    )

    client = factory.created_clients[0]
    assert client.imagine_calls == [
        {
            "prompt": "castle prompt",
            "prompt_images": ("prompt-a",),
            "style_references": ("style-a",),
            "character_references": ("character-a",),
            "omni_reference": "omni-a",
            "state": None,
        }
    ]
    assert result.job.id == final_job_id
    assert result.image_bytes == final_bytes
    assert tuple(tile.index for tile in result.tiles) == (1, 2)
    assert progress_updates == [("Rendering", preview_bytes)]
    assert client.split_image_result_calls == [
        {"job_id": final_job_id, "image": final_bytes}
    ]


def test_runtime_service_upscale_normalizes_single_image_resolution_for_subtle_mode(
    plugin_package,
    sample_single_image,
):
    """Route subtle upscale through the public `upscale` verb with normalized index."""
    runtime_module = _runtime_module(plugin_package)
    image_bytes = _encode_png(sample_single_image)
    final_url = "https://example.invalid/upscale.png"
    factory = FakeClientFactory(
        upscale_scripts=[
            SubmissionScript(
                handle=JobHandle(id="job-upscale"),
                initial_snapshot=_snapshot(
                    "job-upscale",
                    kind="upscale",
                    status=JobStatus.SUBMITTED,
                ),
                events=(
                    (
                        0.0,
                        _snapshot(
                            "job-upscale",
                            kind="upscale",
                            status=JobStatus.SUCCEEDED,
                            output=ImageOutput(image_url=final_url),
                        ),
                    ),
                ),
            )
        ],
        image_resolution_by_bytes={
            image_bytes: ImageResolution(job_id="job-source", index=0)
        },
    )
    service = runtime_module.MutinyRuntimeService(
        runtime_module.MutinyRuntimeManager(
            FakeSettingsService(_config()),
            client_factory=factory,
        ),
        image_loader=RecordingImageLoader({final_url: image_bytes}),
    )

    result = service.upscale_image_and_wait(
        image_bytes,
        mode=runtime_module.MidjourneyUpscaleMode.SUBTLE,
        node_name="MidjourneyUpscaleNode",
    )

    client = factory.created_clients[0]
    assert client.resolve_image_calls == [image_bytes]
    assert client.upscale_calls == [
        {"job_id": "job-source", "index": 1, "mode": "subtle", "state": None}
    ]
    assert result.job.id == "job-upscale"
    assert result.image_bytes == image_bytes
    assert client.split_image_result_calls == []


def test_runtime_service_variation_requires_a_grid_tile(
    plugin_package,
    sample_single_image,
):
    """Reject variation requests resolved from solo-image surfaces."""
    runtime_module = _runtime_module(plugin_package)
    image_bytes = _encode_png(sample_single_image)
    factory = FakeClientFactory(
        image_resolution_by_bytes={
            image_bytes: ImageResolution(job_id="job-source", index=0)
        }
    )
    service = runtime_module.MutinyRuntimeService(
        runtime_module.MutinyRuntimeManager(
            FakeSettingsService(_config()),
            client_factory=factory,
        )
    )

    with pytest.raises(
        runtime_module.RuntimeAdapterError,
        match="Midjourney Variation requires a Midjourney grid tile",
    ):
        service.variation_image_and_wait(
            image_bytes,
            mode=runtime_module.MidjourneyVariationMode.STANDARD,
            node_name="MidjourneyVariationNode",
        )


def test_runtime_service_pan_normalizes_single_image_resolution(
    plugin_package,
    sample_single_image,
):
    """Route pan through the public `pan` verb and split the completed grid result."""
    runtime_module = _runtime_module(plugin_package)
    image_bytes = _encode_png(sample_single_image)
    final_url = "https://example.invalid/pan.png"
    final_tiles = (
        _tile("job-pan", 1, sample_single_image[:1, :1, :]),
        _tile("job-pan", 2, sample_single_image[:1, 1:, :]),
    )
    factory = FakeClientFactory(
        pan_scripts=[
            SubmissionScript(
                handle=JobHandle(id="job-pan"),
                initial_snapshot=_snapshot(
                    "job-pan",
                    kind="pan",
                    status=JobStatus.SUBMITTED,
                ),
                events=(
                    (
                        0.0,
                        _snapshot(
                            "job-pan",
                            kind="pan",
                            status=JobStatus.SUCCEEDED,
                            output=ImageOutput(image_url=final_url),
                        ),
                    ),
                ),
            )
        ],
        image_resolution_by_bytes={
            image_bytes: ImageResolution(job_id="job-source", index=0)
        },
        image_tiles_by_job_id={"job-pan": final_tiles},
    )
    service = runtime_module.MutinyRuntimeService(
        runtime_module.MutinyRuntimeManager(
            FakeSettingsService(_config()),
            client_factory=factory,
        ),
        image_loader=RecordingImageLoader({final_url: image_bytes}),
    )

    result = service.pan_image_and_wait(
        image_bytes,
        direction=runtime_module.MidjourneyPanDirection.LEFT,
        node_name="MidjourneyPanNode",
    )

    client = factory.created_clients[0]
    assert client.pan_calls == [
        {
            "job_id": "job-source",
            "index": 1,
            "direction": "left",
            "state": None,
        }
    ]
    assert tuple(tile.index for tile in result.tiles) == (1, 2)
    assert client.split_image_result_calls == [
        {"job_id": "job-pan", "image": image_bytes}
    ]


def test_runtime_service_variation_splits_completed_grid_results(
    plugin_package,
    sample_grid_image,
):
    """Split variation results through Mutiny's public tile projection."""
    runtime_module = _runtime_module(plugin_package)
    image_bytes = _encode_png(sample_grid_image)
    final_url = "https://example.invalid/vary.png"
    final_bytes = _encode_png(sample_grid_image)
    factory = FakeClientFactory(
        vary_scripts=[
            SubmissionScript(
                handle=JobHandle(id="job-vary"),
                initial_snapshot=_snapshot(
                    "job-vary",
                    kind="vary",
                    status=JobStatus.SUBMITTED,
                ),
                events=(
                    (
                        0.0,
                        _snapshot(
                            "job-vary",
                            kind="vary",
                            status=JobStatus.SUCCEEDED,
                            output=ImageOutput(image_url=final_url),
                        ),
                    ),
                ),
            )
        ],
        image_resolution_by_bytes={
            image_bytes: ImageResolution(job_id="job-source", index=2)
        },
        image_tiles_by_job_id={
            "job-vary": (
                _tile("job-vary", 1, sample_grid_image[:2, :2, :]),
                _tile("job-vary", 2, sample_grid_image[:2, 2:, :]),
            )
        },
    )
    service = runtime_module.MutinyRuntimeService(
        runtime_module.MutinyRuntimeManager(
            FakeSettingsService(_config()),
            client_factory=factory,
        ),
        image_loader=RecordingImageLoader({final_url: final_bytes}),
    )

    result = service.variation_image_and_wait(
        image_bytes,
        mode=runtime_module.MidjourneyVariationMode.STRONG,
        node_name="MidjourneyVariationNode",
    )

    client = factory.created_clients[0]
    assert client.vary_calls == [
        {"job_id": "job-source", "index": 2, "mode": "strong", "state": None}
    ]
    assert tuple(tile.index for tile in result.tiles) == (1, 2)
    assert client.split_image_result_calls == [
        {"job_id": "job-vary", "image": final_bytes}
    ]


def test_runtime_service_zoom_uses_public_zoom_method_for_custom_requests(
    plugin_package,
    sample_single_image,
):
    """Route custom zoom through the facade's unified `zoom` method."""
    runtime_module = _runtime_module(plugin_package)
    image_bytes = _encode_png(sample_single_image)
    final_url = "https://example.invalid/zoom.png"
    factory = FakeClientFactory(
        zoom_scripts=[
            SubmissionScript(
                handle=JobHandle(id="job-zoom"),
                initial_snapshot=_snapshot(
                    "job-zoom",
                    kind="zoom",
                    status=JobStatus.SUBMITTED,
                ),
                events=(
                    (
                        0.0,
                        _snapshot(
                            "job-zoom",
                            kind="zoom",
                            status=JobStatus.SUCCEEDED,
                            output=ImageOutput(image_url=final_url),
                        ),
                    ),
                ),
            )
        ],
        image_resolution_by_bytes={
            image_bytes: ImageResolution(job_id="job-source", index=0)
        },
    )
    service = runtime_module.MutinyRuntimeService(
        runtime_module.MutinyRuntimeManager(
            FakeSettingsService(_config()),
            client_factory=factory,
        ),
        image_loader=RecordingImageLoader({final_url: image_bytes}),
    )

    service.zoom_image_and_wait(
        image_bytes,
        zoom_factor=1.75,
        prompt_text="tight crop",
        node_name="MidjourneyZoomNode",
    )

    client = factory.created_clients[0]
    assert client.zoom_calls == [
        {
            "job_id": "job-source",
            "index": 1,
            "factor": 1.75,
            "prompt": "tight crop",
            "state": None,
        }
    ]
    assert client.split_image_result_calls == []


def test_runtime_service_zoom_leaves_fixed_routes_promptless(
    plugin_package,
    sample_single_image,
):
    """Keep fixed-factor zoom submissions on the promptless public route."""
    runtime_module = _runtime_module(plugin_package)
    image_bytes = _encode_png(sample_single_image)
    final_url = "https://example.invalid/zoom-fixed.png"
    factory = FakeClientFactory(
        zoom_scripts=[
            SubmissionScript(
                handle=JobHandle(id="job-zoom-fixed"),
                initial_snapshot=_snapshot(
                    "job-zoom-fixed",
                    kind="zoom",
                    status=JobStatus.SUBMITTED,
                ),
                events=(
                    (
                        0.0,
                        _snapshot(
                            "job-zoom-fixed",
                            kind="zoom",
                            status=JobStatus.SUCCEEDED,
                            output=ImageOutput(image_url=final_url),
                        ),
                    ),
                ),
            )
        ],
        image_resolution_by_bytes={
            image_bytes: ImageResolution(job_id="job-source", index=0)
        },
    )
    service = runtime_module.MutinyRuntimeService(
        runtime_module.MutinyRuntimeManager(
            FakeSettingsService(_config()),
            client_factory=factory,
        ),
        image_loader=RecordingImageLoader({final_url: image_bytes}),
    )

    service.zoom_image_and_wait(
        image_bytes,
        zoom_factor=1.5,
        prompt_text="   ",
        node_name="MidjourneyZoomNode",
    )

    assert factory.created_clients[0].zoom_calls == [
        {
            "job_id": "job-source",
            "index": 1,
            "factor": 1.5,
            "prompt": None,
            "state": None,
        }
    ]
    assert factory.created_clients[0].split_image_result_calls == []


def test_runtime_service_vary_region_uses_public_method_and_split_tiles(
    plugin_package,
    sample_grid_image,
):
    """Submit vary-region through the public facade and split the completed grid result."""
    runtime_module = _runtime_module(plugin_package)
    final_job_id = "job-vary-region"
    final_url = "https://example.invalid/vary-region.png"
    final_bytes = _encode_png(sample_grid_image)
    factory = FakeClientFactory(
        vary_region_scripts=[
            SubmissionScript(
                handle=JobHandle(id=final_job_id),
                initial_snapshot=_snapshot(
                    final_job_id,
                    kind="vary_region",
                    status=JobStatus.SUBMITTED,
                ),
                events=(
                    (
                        0.0,
                        _snapshot(
                            final_job_id,
                            kind="vary_region",
                            status=JobStatus.SUCCEEDED,
                            output=ImageOutput(image_url=final_url),
                        ),
                    ),
                ),
            )
        ],
        image_tiles_by_job_id={
            final_job_id: (
                _tile(final_job_id, 1, sample_grid_image[:2, :2, :]),
                _tile(final_job_id, 2, sample_grid_image[:2, 2:, :]),
            )
        },
    )
    service = runtime_module.MutinyRuntimeService(
        runtime_module.MutinyRuntimeManager(
            FakeSettingsService(_config()),
            client_factory=factory,
        ),
        image_loader=RecordingImageLoader({final_url: final_bytes}),
    )

    result = service.vary_region_image_and_wait(
        "data:image/png;base64,source",
        "data:image/png;base64,mask",
        prompt_text="add ivy",
        node_name="MidjourneyVaryRegionNode",
    )

    client = factory.created_clients[0]
    assert client.vary_region_calls == [
        {
            "image": "data:image/png;base64,source",
            "mask": "data:image/png;base64,mask",
            "prompt": "add ivy",
            "state": None,
        }
    ]
    assert len(result.tiles) == 2
    assert client.split_image_result_calls == [
        {"job_id": final_job_id, "image": final_bytes}
    ]


def test_runtime_service_describe_prefers_text_output(plugin_package):
    """Extract describe text from the public `TextOutput` when present."""
    runtime_module = _runtime_module(plugin_package)
    factory = FakeClientFactory(
        describe_scripts=[
            SubmissionScript(
                handle=JobHandle(id="job-describe"),
                initial_snapshot=_snapshot(
                    "job-describe",
                    kind="describe",
                    status=JobStatus.SUBMITTED,
                ),
                events=(
                    (
                        0.0,
                        _snapshot(
                            "job-describe",
                            kind="describe",
                            status=JobStatus.SUCCEEDED,
                            prompt_text="fallback text",
                            output=TextOutput(text="described prompt"),
                        ),
                    ),
                ),
            )
        ]
    )
    service = runtime_module.MutinyRuntimeService(
        runtime_module.MutinyRuntimeManager(
            FakeSettingsService(_config()),
            client_factory=factory,
        )
    )

    result = service.describe_image_and_wait(
        "data:image/png;base64,input",
        node_name="MidjourneyDescribeNode",
    )

    assert result.prompt_text == "described prompt"
    assert factory.created_clients[0].describe_calls == [
        {"image": "data:image/png;base64,input", "state": None}
    ]


def test_runtime_service_describe_falls_back_to_prompt_text(plugin_package):
    """Extract describe text from `prompt_text` when no text output is present."""
    runtime_module = _runtime_module(plugin_package)
    factory = FakeClientFactory(
        describe_scripts=[
            SubmissionScript(
                handle=JobHandle(id="job-describe"),
                initial_snapshot=_snapshot(
                    "job-describe",
                    kind="describe",
                    status=JobStatus.SUBMITTED,
                ),
                events=(
                    (
                        0.0,
                        _snapshot(
                            "job-describe",
                            kind="describe",
                            status=JobStatus.SUCCEEDED,
                            prompt_text="fallback prompt",
                            output=None,
                        ),
                    ),
                ),
            )
        ]
    )
    service = runtime_module.MutinyRuntimeService(
        runtime_module.MutinyRuntimeManager(
            FakeSettingsService(_config()),
            client_factory=factory,
        )
    )

    result = service.describe_image_and_wait(
        "data:image/png;base64,input",
        node_name="MidjourneyDescribeNode",
    )

    assert result.prompt_text == "fallback prompt"


def test_runtime_service_animate_reads_video_output_and_normalizes_progress(
    plugin_package,
):
    """Return native video values from `VideoOutput` and keep percent progress concise."""
    runtime_module = _runtime_module(plugin_package)
    preview_url = "https://example.invalid/animate-preview.png"
    local_video_path = "E:\\videos\\animate.mp4"
    factory = FakeClientFactory(
        animate_scripts=[
            SubmissionScript(
                handle=JobHandle(id="job-animate"),
                initial_snapshot=_snapshot(
                    "job-animate",
                    kind="animate",
                    status=JobStatus.SUBMITTED,
                ),
                events=(
                    (
                        0.0,
                        ProgressUpdate(
                            job_id="job-animate",
                            status_text="Animating 42%",
                            preview_image_url=preview_url,
                        ),
                    ),
                    (
                        0.1,
                        _snapshot(
                            "job-animate",
                            kind="animate",
                            status=JobStatus.SUCCEEDED,
                            output=VideoOutput(local_file_path=local_video_path),
                        ),
                    ),
                ),
            )
        ]
    )
    service = runtime_module.MutinyRuntimeService(
        runtime_module.MutinyRuntimeManager(
            FakeSettingsService(_config()),
            client_factory=factory,
        ),
        image_loader=RecordingImageLoader({preview_url: b"preview-bytes"}),
        video_loader=RecordingVideoLoader({local_video_path: "video-value"}),
    )
    progress_updates: list[tuple[str | None, bytes | None]] = []

    result = service.animate_image_and_wait(
        "data:image/png;base64,start",
        motion=runtime_module.MidjourneyAnimateMotion.HIGH,
        node_name="MidjourneyAnimateNode",
        progress_reporter=lambda text, preview: progress_updates.append(
            (text, preview)
        ),
    )

    client = factory.created_clients[0]
    assert client.animate_calls == [
        {
            "start_frame": "data:image/png;base64,start",
            "end_frame": None,
            "prompt": "",
            "motion": "high",
            "batch_size": None,
            "state": None,
        }
    ]
    assert result.video_url == local_video_path
    assert result.video_value == "video-value"
    assert progress_updates == [("42%", b"preview-bytes")]


def test_runtime_service_extend_uses_public_video_argument(plugin_package):
    """Submit extend requests through the public `extend(video=...)` contract."""
    runtime_module = _runtime_module(plugin_package)
    remote_video_url = "https://example.invalid/extended.mp4"
    factory = FakeClientFactory(
        extend_scripts=[
            SubmissionScript(
                handle=JobHandle(id="job-extend"),
                initial_snapshot=_snapshot(
                    "job-extend",
                    kind="extend",
                    status=JobStatus.SUBMITTED,
                ),
                events=(
                    (
                        0.0,
                        _snapshot(
                            "job-extend",
                            kind="extend",
                            status=JobStatus.SUCCEEDED,
                            output=VideoOutput(video_url=remote_video_url),
                        ),
                    ),
                ),
            )
        ]
    )
    service = runtime_module.MutinyRuntimeService(
        runtime_module.MutinyRuntimeManager(
            FakeSettingsService(_config()),
            client_factory=factory,
        ),
        video_loader=RecordingVideoLoader({remote_video_url: "extend-video"}),
    )

    result = service.extend_video_and_wait(
        b"midjourney-video",
        motion=runtime_module.MidjourneyAnimateMotion.LOW,
        node_name="MidjourneyExtendNode",
    )

    assert factory.created_clients[0].extend_calls == [
        {
            "job_id": None,
            "video": b"midjourney-video",
            "motion": "low",
            "state": None,
        }
    ]
    assert result.video_url == remote_video_url
    assert result.video_value == "extend-video"


def test_runtime_manager_reuses_client_for_same_config_and_recreates_on_change(
    plugin_package,
):
    """Reuse one shared Mutiny client per config snapshot and recreate on changes."""
    runtime_module = _runtime_module(plugin_package)
    settings_service = FakeSettingsService(_config())
    factory = FakeClientFactory(
        describe_scripts=[
            SubmissionScript(
                handle=JobHandle(id="job-describe-1"),
                initial_snapshot=_snapshot(
                    "job-describe-1",
                    kind="describe",
                    status=JobStatus.SUBMITTED,
                ),
                events=(
                    (
                        0.0,
                        _snapshot(
                            "job-describe-1",
                            kind="describe",
                            status=JobStatus.SUCCEEDED,
                            output=TextOutput(text="first"),
                        ),
                    ),
                ),
            ),
            SubmissionScript(
                handle=JobHandle(id="job-describe-2"),
                initial_snapshot=_snapshot(
                    "job-describe-2",
                    kind="describe",
                    status=JobStatus.SUBMITTED,
                ),
                events=(
                    (
                        0.0,
                        _snapshot(
                            "job-describe-2",
                            kind="describe",
                            status=JobStatus.SUCCEEDED,
                            output=TextOutput(text="second"),
                        ),
                    ),
                ),
            ),
            SubmissionScript(
                handle=JobHandle(id="job-describe-3"),
                initial_snapshot=_snapshot(
                    "job-describe-3",
                    kind="describe",
                    status=JobStatus.SUBMITTED,
                ),
                events=(
                    (
                        0.0,
                        _snapshot(
                            "job-describe-3",
                            kind="describe",
                            status=JobStatus.SUCCEEDED,
                            output=TextOutput(text="third"),
                        ),
                    ),
                ),
            ),
        ]
    )
    service = runtime_module.MutinyRuntimeService(
        runtime_module.MutinyRuntimeManager(
            settings_service,
            client_factory=factory,
        )
    )

    assert (
        service.describe_image_and_wait("image-a", node_name="DescribeNode").prompt_text
        == "first"
    )
    assert (
        service.describe_image_and_wait("image-b", node_name="DescribeNode").prompt_text
        == "second"
    )
    assert len(factory.created_clients) == 1

    settings_service._config = Config.create(
        token_provider=StaticTokenProvider(),
        guild_id="guild-2",
        channel_id="channel-1",
    )

    assert (
        service.describe_image_and_wait("image-c", node_name="DescribeNode").prompt_text
        == "first"
    )
    assert len(factory.created_clients) == 2
    assert factory.created_clients[0].close_calls == 1


def test_runtime_manager_raises_cleanly_when_mutiny_never_becomes_ready(
    plugin_package,
):
    """Raise the plugin's readiness error when the facade stays unready."""
    runtime_module = _runtime_module(plugin_package)
    factory = FakeClientFactory(ready_result=False)
    manager = runtime_module.MutinyRuntimeManager(
        FakeSettingsService(_config()),
        client_factory=factory,
        ready_timeout_seconds=1,
    )

    with pytest.raises(
        runtime_module.RuntimeNotReadyError,
        match="Mutiny did not become ready before the timeout expired",
    ):
        manager.get_job("job-missing")
