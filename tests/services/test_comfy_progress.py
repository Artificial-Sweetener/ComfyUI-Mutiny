"""Test ComfyUI progress reporting helpers."""

from __future__ import annotations

import sys

from PIL import Image
from support.plugin_loader import RecordingProgressBar


def test_build_comfy_progress_reporter_records_preview_updates(
    plugin_package, sample_grid_image
):
    """Keep preview progress updates wired through the Comfy progress boundary."""
    services_module = sys.modules[f"{plugin_package.__name__}.services"]
    report_progress, preview_image = services_module.build_comfy_progress_reporter()
    report_progress("25%", sample_grid_image)

    progress_bar = RecordingProgressBar.instances[0]
    recorded_value, recorded_total, preview = progress_bar.calls[0]

    assert recorded_value == 25
    assert recorded_total == 100
    assert preview[0] == "PNG"
    assert isinstance(preview[1], Image.Image)
    assert preview[2] == 512
    assert tuple(preview_image[0].shape) == (1, 3, 4, 4)


def test_build_comfy_progress_reporter_falls_back_to_zero_for_invalid_percent(
    plugin_package, sample_grid_image
):
    """Keep malformed progress strings from breaking preview updates."""
    services_module = sys.modules[f"{plugin_package.__name__}.services"]
    report_progress, _preview_image = services_module.build_comfy_progress_reporter()
    report_progress("unknown", sample_grid_image)

    progress_bar = RecordingProgressBar.instances[0]
    recorded_value, _recorded_total, _preview = progress_bar.calls[0]
    assert recorded_value == 0


def test_build_comfy_progress_reporter_handles_missing_preview_payload(plugin_package):
    """Allow progress updates without preview images."""
    services_module = sys.modules[f"{plugin_package.__name__}.services"]
    report_progress, preview_image = services_module.build_comfy_progress_reporter()
    report_progress("40%", None)

    progress_bar = RecordingProgressBar.instances[0]
    recorded_value, recorded_total, preview = progress_bar.calls[0]

    assert recorded_value == 40
    assert recorded_total == 100
    assert preview is None
    assert preview_image[0] is None
