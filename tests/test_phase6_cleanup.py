"""Assert that the repository no longer ships the removed Java proxy path."""

from __future__ import annotations

from support.plugin_loader import REPO_ROOT

LEGACY_REPO_PATHS = (
    "api_client.py",
    "application.yml",
    "discord_credentials.yml",
    "midjourney_generate_node.py",
    "proxy",
    "setting.yaml",
)


def test_repo_no_longer_ships_legacy_java_artifacts():
    """Keep removed Java-era files from silently re-entering the repository."""
    missing_paths = [
        relative_path
        for relative_path in LEGACY_REPO_PATHS
        if not (REPO_ROOT / relative_path).exists()
    ]

    assert missing_paths == list(LEGACY_REPO_PATHS)
