"""Provide isolated fixtures for repo-local plugin tests."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

TESTS_ROOT = Path(__file__).resolve().parent
if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))

from support.fakes import FakeRuntimeService
from support.plugin_loader import (
    RecordingProgressBar,
    install_comfy_stubs,
    load_plugin_package,
)

install_comfy_stubs(progress_bar_class=RecordingProgressBar)


@pytest.fixture()
def plugin_package():
    """Load a fresh plugin package with ComfyUI stubs installed."""
    RecordingProgressBar.reset()
    package = load_plugin_package(progress_bar_class=RecordingProgressBar)
    yield package

    runtime_module = sys.modules.get(f"{package.__name__}.runtime")
    if runtime_module is not None:
        runtime_module.reset_runtime_service()


@pytest.fixture()
def sample_grid_image() -> np.ndarray:
    """Return a deterministic 4x4 RGB image suitable for grid-splitting tests."""
    return np.arange(4 * 4 * 3, dtype=np.uint8).reshape(4, 4, 3)


@pytest.fixture()
def sample_single_image() -> np.ndarray:
    """Return a deterministic 2x2 RGB image for single-image node tests."""
    return np.arange(2 * 2 * 3, dtype=np.uint8).reshape(2, 2, 3)


@pytest.fixture()
def make_node():
    """Instantiate a node and override selected attributes for tests."""

    def _make(node_class, **attrs):
        """Create one node instance with targeted test-only attribute overrides."""
        node = node_class()
        for name, value in attrs.items():
            setattr(node, name, value)
        return node

    return _make


@pytest.fixture()
def fake_runtime_service_factory(sample_grid_image):
    """Build fake runtime services with deterministic default responses."""

    def _make(**overrides):
        """Create one fake runtime service with deterministic default payloads."""
        defaults = {
            "generated_image": sample_grid_image,
            "generated_job_id": "job-123",
        }
        defaults.update(overrides)
        return FakeRuntimeService(**defaults)

    return _make
