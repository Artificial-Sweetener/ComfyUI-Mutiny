"""Track Mutiny job and progress events for sync-friendly waiting."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from mutiny import JobSnapshot, ProgressUpdate

from .models import JobTrackingSnapshot


@dataclass
class _TrackedJobState:
    """Store the mutable event-tracking state for one submitted job."""

    version: int = 0
    status: object | None = None
    progress_text: str | None = None
    preview_image_url: str | None = None
    fail_reason: str | None = None


class JobEventTracker:
    """Store the latest job/progress state and wake waiters on change."""

    def __init__(self) -> None:
        """Initialize the tracker with an empty job map."""
        self._condition = threading.Condition()
        self._jobs: dict[str, _TrackedJobState] = {}
        self._stream_failure: Exception | None = None

    def reset(self) -> None:
        """Clear all tracked jobs and any remembered stream failure."""
        with self._condition:
            self._jobs = {}
            self._stream_failure = None
            self._condition.notify_all()

    def record_job_snapshot(self, snapshot: JobSnapshot) -> None:
        """Update the tracker from one public `JobSnapshot`."""
        with self._condition:
            state = self._jobs.setdefault(snapshot.id, _TrackedJobState())
            state.version += 1
            state.status = snapshot.status
            if snapshot.progress_text:
                state.progress_text = snapshot.progress_text
            if snapshot.preview_image_url:
                state.preview_image_url = snapshot.preview_image_url
            if snapshot.fail_reason:
                state.fail_reason = snapshot.fail_reason
            self._condition.notify_all()

    def record_progress_update(self, update: ProgressUpdate) -> None:
        """Update the tracker from one public `ProgressUpdate`."""
        with self._condition:
            state = self._jobs.setdefault(update.job_id, _TrackedJobState())
            state.version += 1
            if update.status_text:
                state.progress_text = update.status_text
            if update.preview_image_url:
                state.preview_image_url = update.preview_image_url
            self._condition.notify_all()

    def record_event(self, event: JobSnapshot | ProgressUpdate) -> None:
        """Record either public Mutiny event type."""
        if isinstance(event, JobSnapshot):
            self.record_job_snapshot(event)
            return

        self.record_progress_update(event)

    def fail_all(self, exc: Exception) -> None:
        """Wake all waiters with a shared stream failure."""
        with self._condition:
            self._stream_failure = exc
            self._condition.notify_all()

    def wait_for_update(
        self,
        job_id: str,
        *,
        after_version: int,
        timeout_s: float,
    ) -> JobTrackingSnapshot:
        """Block until the tracked job changes or the wait times out."""
        deadline = time.monotonic() + timeout_s

        with self._condition:
            while True:
                if self._stream_failure is not None:
                    raise self._stream_failure

                snapshot = self.snapshot(job_id)
                if snapshot.version > after_version or snapshot.is_terminal:
                    return snapshot

                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(f"Timed out waiting for job {job_id}.")
                self._condition.wait(timeout=remaining)

    def snapshot(self, job_id: str) -> JobTrackingSnapshot:
        """Return the latest known snapshot for one job id."""
        state = self._jobs.get(job_id)
        if state is None:
            return JobTrackingSnapshot(job_id=job_id)
        return JobTrackingSnapshot(
            job_id=job_id,
            version=state.version,
            status=state.status,
            progress_text=state.progress_text,
            preview_image_url=state.preview_image_url,
            fail_reason=state.fail_reason,
        )


__all__ = ["JobEventTracker"]
