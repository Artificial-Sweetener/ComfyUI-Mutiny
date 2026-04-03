"""Provide reusable prompt normalization and validation helpers."""

from __future__ import annotations

import re

_WEIGHT_PATTERN = re.compile(r"\(([^:()]+):([^)]+)\)")
_ASPECT_RATIO_PATTERN = re.compile(r"^\s*(\d+)\s*:\s*(\d+)\s*$")

V4_MODEL_RATIO_MAP = {
    "Midjourney v4a": {"1:1", "2:3", "3:2"},
    "Midjourney v4b": {"1:1", "2:3", "3:2"},
    "Midjourney v4c": {"1:1", "2:3", "3:2", "16:9", "4:5", "5:4", "2:1", "1:2"},
    "Midjourney v4": {"1:1", "2:3", "3:2", "16:9", "4:5", "5:4", "2:1", "1:2"},
}


def normalize_prompt_text(text: str) -> str:
    """Collapse line breaks and repeated whitespace in prompt text."""
    text = re.sub(r"[\r\n]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def coerce_int(value: object, default: int | None = None) -> int | None:
    """Coerce a value to ``int`` and fall back to the provided default."""
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def translate_stable_diffusion_weights(prompt: str) -> str:
    """Translate Stable Diffusion weight groups into Midjourney syntax."""
    matches = list(_WEIGHT_PATTERN.finditer(prompt))
    if not matches:
        return prompt

    if any(match.group(1).strip() == "" for match in matches):
        return prompt

    result: list[str] = []
    last_index = 0

    for match in matches:
        prefix = " ".join(prompt[last_index : match.start()].strip().split())
        if prefix:
            prefix = re.sub(r"\s+([,.;!?])", r"\1", prefix)
            result.append(f"{prefix}::1")

        text = re.sub(r"\s+([,.;!?])", r"\1", match.group(1).strip())
        weight = match.group(2).strip()
        result.append(f"{text}::{weight}")
        last_index = match.end()

    suffix = " ".join(prompt[last_index:].strip().split())
    if suffix:
        suffix = re.sub(r"\s+([,.;!?])", r"\1", suffix)
        result.append(f"{suffix}::1")

    return re.sub(r"\s+([,.;!?])", r"\1", " ".join(result))


def normalize_ratio_text(value: str) -> str:
    """Normalize an aspect ratio string to ``W:H`` form."""
    match = _ASPECT_RATIO_PATTERN.match(str(value))
    if not match:
        raise ValueError("Aspect ratio must be in 'W:H' format (e.g. 1:2, 3:2)")

    width, height = map(int, match.groups())
    if width <= 0 or height <= 0:
        raise ValueError("Aspect ratio components must be positive integers.")

    return f"{width}:{height}"


def validate_ratio_between_half_and_double(aspect_ratio: str) -> str:
    """Validate that an aspect ratio stays within the 1:2 to 2:1 range."""
    normalized_ratio = normalize_ratio_text(aspect_ratio)
    width_str, height_str = normalized_ratio.split(":")
    width = int(width_str)
    height = int(height_str)
    ratio = width / height
    if ratio < 0.5 or ratio > 2.0:
        raise ValueError("Aspect ratio must be between 1:2 and 2:1 (0.5 ≤ W:H ≤ 2.0).")
    return normalized_ratio


def validate_v4_model_aspect_ratio(model: str, aspect_ratio: str) -> str:
    """Validate a v4 aspect ratio against the selected model variant."""
    allowed = V4_MODEL_RATIO_MAP.get(model)
    if not allowed:
        raise ValueError(f"Unknown v4 model variant: {model}")

    normalized_ratio = normalize_ratio_text(aspect_ratio)
    if normalized_ratio not in allowed:
        raise ValueError(
            f"Aspect ratio '{normalized_ratio}' is not supported for model '{model}'. "
            f"Allowed ratios: {', '.join(sorted(allowed))}"
        )
    return normalized_ratio
