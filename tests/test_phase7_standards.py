"""Guard the repository-wide standards finalized in roadmap Phase 7."""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
_SKIPPED_PARTS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", "node_modules"}
_LOGGING_SEVERITY_CALLS = {
    "basicConfig",
    "critical",
    "debug",
    "error",
    "exception",
    "info",
    "warning",
}


def iter_python_files() -> list[Path]:
    """Return the repository Python files that Phase 7 standards cover."""
    return sorted(
        path
        for path in REPO_ROOT.rglob("*.py")
        if not any(part in _SKIPPED_PARTS for part in path.parts)
    )


def parse_module(path: Path) -> ast.Module:
    """Parse one repository Python file into an AST for structural checks."""
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def collect_missing_docstrings(tree: ast.AST) -> list[str]:
    """Return a stable list of module, class, and function docstring violations."""
    missing = []
    if ast.get_docstring(tree) is None:
        missing.append("module")

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if ast.get_docstring(node) is None:
                missing.append(f"{type(node).__name__}:{node.name}:{node.lineno}")

    return sorted(missing)


def collect_disallowed_logging_calls(tree: ast.AST) -> list[str]:
    """Return direct root-logging calls that bypass the module logger pattern."""
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if not isinstance(node.func.value, ast.Name):
            continue
        if node.func.value.id != "logging":
            continue
        if node.func.attr in _LOGGING_SEVERITY_CALLS:
            violations.append(f"logging.{node.func.attr}:{node.lineno}")
    return sorted(violations)


def collect_bare_except_handlers(tree: ast.AST) -> list[str]:
    """Return any bare ``except:`` handlers, which are forbidden by AGENTS.md."""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            violations.append(f"except:{node.lineno}")
    return sorted(violations)


def test_python_files_define_required_docstrings():
    """Require module, class, and function docstrings across repository Python files."""
    violations = {}
    for path in iter_python_files():
        missing = collect_missing_docstrings(parse_module(path))
        if missing:
            violations[path.relative_to(REPO_ROOT).as_posix()] = missing

    assert violations == {}


def test_python_files_avoid_root_logging_calls():
    """Require module-level logger usage instead of direct root logging calls."""
    violations = {}
    for path in iter_python_files():
        calls = collect_disallowed_logging_calls(parse_module(path))
        if calls:
            violations[path.relative_to(REPO_ROOT).as_posix()] = calls

    assert violations == {}


def test_python_files_do_not_use_bare_except():
    """Require explicit exception types for every repository ``except`` handler."""
    violations = {}
    for path in iter_python_files():
        handlers = collect_bare_except_handlers(parse_module(path))
        if handlers:
            violations[path.relative_to(REPO_ROOT).as_posix()] = handlers

    assert violations == {}
