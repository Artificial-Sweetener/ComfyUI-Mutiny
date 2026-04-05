"""Define reusable ComfyUI input specs and per-node prompt composition pieces."""

from __future__ import annotations

import random
from copy import deepcopy
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Callable, Mapping

from .validators import (
    coerce_int,
    normalize_prompt_text,
    validate_ratio_between_half_and_double,
)

FieldType = str | list[str]
NormalizedValues = Mapping[str, Any]
Renderer = Callable[[Any, NormalizedValues], str]
Normalizer = Callable[[Any, NormalizedValues], Any]
Validator = Callable[[Any, NormalizedValues], None]

RANDOM_SEED = random.randint(0, 4294967295)


class InputRole(StrEnum):
    """Describe how a piece participates in prompt building."""

    PROMPT_TEXT = "prompt_text"
    PROMPT_FLAG = "prompt_flag"
    BUILD_CONTROL = "build_control"
    SUBMISSION_CONTROL = "submission_control"
    LOCAL_ONLY = "local_only"


@dataclass(frozen=True)
class InputSpec:
    """Describe one reusable ComfyUI field and how it maps into prompting."""

    key: str
    field_name: str
    field_type: FieldType
    field_options: Mapping[str, Any] = field(default_factory=dict)
    role: InputRole = InputRole.PROMPT_FLAG
    renderer: Renderer | None = None
    normalizer: Normalizer | None = None
    validator: Validator | None = None

    def comfy_ui_entry(self) -> tuple[FieldType, dict[str, Any]]:
        """Return a defensive copy of the ComfyUI field declaration."""
        return self.field_type, deepcopy(dict(self.field_options))


@dataclass(frozen=True)
class NodeInputBinding:
    """Reference a reusable input spec inside a node definition."""

    spec_key: str
    required: bool = False


@dataclass(frozen=True)
class NodeDefinition:
    """Declare the ordered pieces that define one node's prompt surface."""

    bindings: tuple[NodeInputBinding, ...]
    image_capability_target: str | None = None


def bind(spec_key: str, *, required: bool = False) -> NodeInputBinding:
    """Bind a reusable input spec into a node definition."""
    return NodeInputBinding(spec_key=spec_key, required=required)


IMAGINE_SUBMISSION_BINDINGS: tuple[NodeInputBinding, ...] = (bind("images"),)
"""Share imagine-submission controls across all request-node definitions."""


def _render_prompt(value: Any, _: NormalizedValues) -> str:
    """Render the primary prompt text without adding argument prefixes."""
    return str(value or "")


def _render_negative_prompt(value: Any, _: NormalizedValues) -> str:
    """Render the Midjourney negative-prompt flag when content is present."""
    return f" --no {value}" if value else ""


def _render_flag(flag_name: str) -> Renderer:
    """Build a renderer for one value-bearing Midjourney flag."""

    def _renderer(value: Any, _: NormalizedValues) -> str:
        """Render the configured flag only when the field has a value."""
        return f" {flag_name} {value}" if value not in (None, "") else ""

    return _renderer


def _render_bare_flag(flag_name: str) -> Renderer:
    """Build a renderer that emits one flag whenever the field has a value."""

    def _renderer(value: Any, _: NormalizedValues) -> str:
        """Render the configured flag for any populated field value."""
        return f" {flag_name}" if value not in (None, "", False) else ""

    return _renderer


def _render_boolean_flag(flag_name: str) -> Renderer:
    """Build a renderer for one boolean Midjourney flag."""

    def _renderer(value: Any, _: NormalizedValues) -> str:
        """Render the configured flag only when the field is truthy."""
        return f" {flag_name}" if value else ""

    return _renderer


def _render_version(value: Any, _: NormalizedValues) -> str:
    """Render either a Midjourney version flag or a Niji variant flag."""
    version = str(value or "").strip()
    if not version:
        return ""
    if version.lower().startswith("niji"):
        return f" --{version}"
    return f" --v {version}"


def _render_stylize(value: Any, _: NormalizedValues) -> str:
    """Render the long-form stylize flag when a non-zero value is present."""
    coerced_value = coerce_int(value)
    if coerced_value in (None, 0, 100):
        return ""
    return f" --stylize {coerced_value}"


def _render_short_stylize(value: Any, _: NormalizedValues) -> str:
    """Render the legacy short-form stylize flag when a value is present."""
    return f" --s {value}" if value is not None else ""


def _render_chaos(value: Any, _: NormalizedValues) -> str:
    """Render the long-form chaos flag when a non-zero value is present."""
    return f" --chaos {value}" if coerce_int(value) else ""


def _render_short_chaos(value: Any, _: NormalizedValues) -> str:
    """Render the legacy short-form chaos flag when a non-zero value is present."""
    return f" --c {value}" if coerce_int(value) else ""


def _render_weird(value: Any, _: NormalizedValues) -> str:
    """Render the weird flag when a non-zero value is present."""
    return f" --weird {value}" if coerce_int(value) else ""


def _render_quality(value: Any, _: NormalizedValues) -> str:
    """Render the current shared quality selector into Midjourney flags."""
    if value in (None, "", "Default Quality"):
        return ""
    if value == "Draft Quality":
        return " --q 0.5"
    if value == "High Quality":
        return " --q 2"
    return ""


def _render_legacy_quality(value: Any, _: NormalizedValues) -> str:
    """Render the legacy quality selector used by older model families."""
    if value in (None, "", "Default Quality"):
        return ""
    if value == "Bad Quality":
        return " --q 0.25"
    if value == "Draft Quality":
        return " --q 0.5"
    return ""


def _render_v7_quality(value: Any, _: NormalizedValues) -> str:
    """Render the Midjourney v7 quality selector into prompt flags."""
    if value in (None, "", "Default Quality"):
        return ""
    if value == "Draft Quality":
        return " --draft"
    if value == "High Quality":
        return " --q 2"
    if value == "Ultra Quality":
        return " --q 4"
    return ""


def _render_aspect_ratio(value: Any, _: NormalizedValues) -> str:
    """Render a non-default aspect ratio while leaving the default implicit."""
    normalized_value = str(value or "").strip()
    if not normalized_value or normalized_value == "1:1":
        return ""
    return f" --ar {normalized_value}"


def _normalize_batch_count(value: Any, _: NormalizedValues) -> int:
    """Clamp batch count into 4..160 and floor it to a 4-image Midjourney grid."""
    coerced_value = coerce_int(value, 4)
    clamped_value = min(max(coerced_value, 4), 160)
    return clamped_value - (clamped_value % 4)


def _render_batch_repeat(value: Any, _: NormalizedValues) -> str:
    """Render Midjourney ``--repeat`` from a normalized total image batch count."""
    repeat_count = coerce_int(value, 4) // 4
    return f" --repeat {repeat_count}" if repeat_count > 1 else ""


def _render_seed(value: Any, _: NormalizedValues) -> str:
    """Render the seed flag when the seed is a non-negative integer."""
    coerced_value = coerce_int(value)
    return (
        f" --seed {value}" if coerced_value is not None and coerced_value >= 0 else ""
    )


def _render_custom_args(value: Any, _: NormalizedValues) -> str:
    """Append raw custom arguments without further transformation."""
    custom_args = str(value or "").strip()
    return f" {custom_args}" if custom_args else ""


def _normalize_prompt_field(value: Any, _: NormalizedValues) -> str:
    """Normalize a prompt-like field by collapsing internal whitespace."""
    return normalize_prompt_text(str(value or ""))


def _normalize_string_field(value: Any, _: NormalizedValues) -> str:
    """Normalize a simple string field by trimming outer whitespace."""
    return str(value or "").strip()


def _normalize_ratio_field(value: Any, _: NormalizedValues) -> str:
    """Normalize an aspect-ratio field by stripping surrounding whitespace."""
    return str(value or "").strip()


def _validate_v4c_ratio(value: Any, _: NormalizedValues) -> None:
    """Validate the narrow aspect-ratio band used by Niji and Midjourney v4c."""
    if str(value or "").strip():
        validate_ratio_between_half_and_double(str(value))


def _validate_personalization_conflict(value: Any, values: NormalizedValues) -> None:
    """Reject simultaneous bare and explicit personalization controls."""
    del value
    if (
        values.get("use_personalization")
        and str(values.get("profile_code") or "").strip()
    ):
        raise ValueError(
            "Default personalization and explicit profile-code personalization cannot both be set."
        )


INPUT_SPECS: dict[str, InputSpec] = {
    "version": InputSpec(
        key="version",
        field_name="version",
        field_type="STRING",
        field_options={
            "default": "7",
            "tooltip": "Midjourney version string, e.g. '5', '5.2', 'niji 5'. (--v).",
        },
        role=InputRole.PROMPT_FLAG,
        renderer=_render_version,
    ),
    "prompt": InputSpec(
        key="prompt",
        field_name="prompt",
        field_type="STRING",
        field_options={
            "tooltip": "Main image prompt. Mutiny will remove line breaks before sending to MJ. (--prompt)"
        },
        role=InputRole.PROMPT_TEXT,
        renderer=_render_prompt,
        normalizer=_normalize_prompt_field,
    ),
    "negative_prompt": InputSpec(
        key="negative_prompt",
        field_name="negative_prompt",
        field_type="STRING",
        field_options={
            "tooltip": "Negative prompt, what to avoid. Line breaks will be removed here, too! (--no)"
        },
        role=InputRole.PROMPT_FLAG,
        renderer=_render_negative_prompt,
        normalizer=_normalize_prompt_field,
    ),
    "stylize": InputSpec(
        key="stylize",
        field_name="stylize",
        field_type="INT",
        field_options={
            "default": 100,
            "min": 0,
            "max": 1000,
            "step": 1,
            "tooltip": (
                "Controls the strength of Midjourney’s learned aesthetic priors - "
                "higher adds more artistic, less literal details. Default 100 is "
                "implicit; non-default values render --stylize."
            ),
        },
        role=InputRole.PROMPT_FLAG,
        renderer=_render_stylize,
    ),
    "chaos": InputSpec(
        key="chaos",
        field_name="chaos",
        field_type="INT",
        field_options={
            "default": 0,
            "min": 0,
            "max": 100,
            "step": 1,
            "tooltip": "Adjusts the diversity of outputs by widening the latent noise spread - higher means more unpredictable options. (--chaos)",
        },
        role=InputRole.PROMPT_FLAG,
        renderer=_render_chaos,
    ),
    "weird": InputSpec(
        key="weird",
        field_name="weird",
        field_type="INT",
        field_options={
            "default": 0,
            "min": 0,
            "max": 3000,
            "step": 1,
            "tooltip": "Biases generation toward low-likelihood, unconventional latent paths - higher produces quirkier, surreal outputs. (--weird)",
        },
        role=InputRole.PROMPT_FLAG,
        renderer=_render_weird,
    ),
    "aspect_ratio": InputSpec(
        key="aspect_ratio",
        field_name="aspect_ratio",
        field_type="STRING",
        field_options={
            "default": "1:1",
            "tooltip": (
                "Aspect ratio (W:H), e.g., 16:9 or 4:3. Default 1:1 is implicit; "
                "non-default ratios render --ar."
            ),
        },
        role=InputRole.PROMPT_FLAG,
        renderer=_render_aspect_ratio,
        normalizer=_normalize_ratio_field,
    ),
    "niji_aspect_ratio": InputSpec(
        key="niji_aspect_ratio",
        field_name="aspect_ratio",
        field_type="STRING",
        field_options={
            "default": "1:1",
            "tooltip": (
                "Aspect ratio (W:H) between 1:2 and 2:1, e.g., 2:3, 3:2, 1:1. "
                "Default 1:1 is implicit; non-default ratios render --ar."
            ),
        },
        role=InputRole.PROMPT_FLAG,
        renderer=_render_aspect_ratio,
        normalizer=_normalize_ratio_field,
        validator=_validate_v4c_ratio,
    ),
    "quality": InputSpec(
        key="quality",
        field_name="quality",
        field_type=["Draft Quality", "Default Quality", "High Quality"],
        field_options={
            "default": "Default Quality",
            "tooltip": (
                "Draft renders --q 0.5, Default is implicit, High renders --q 2. "
                "Not all models support every value."
            ),
        },
        role=InputRole.PROMPT_FLAG,
        renderer=_render_quality,
    ),
    "quality_legacy": InputSpec(
        key="quality_legacy",
        field_name="quality",
        field_type=["Bad Quality", "Draft Quality", "Default Quality"],
        field_options={
            "default": "Default Quality",
            "tooltip": (
                "Controls generation speed and detail for legacy MJ models (v1–v5, Niji 5, etc). "
                "Bad Quality (--q 0.25): Fastest/lowest detail. "
                "Draft Quality (--q 0.5): Lower quality, faster/cheaper. "
                "Default Quality: Normal implicit quality. "
                "Higher values are NOT supported."
            ),
        },
        role=InputRole.PROMPT_FLAG,
        renderer=_render_legacy_quality,
    ),
    "v7_quality": InputSpec(
        key="v7_quality",
        field_name="quality",
        field_type=[
            "Draft Quality",
            "Default Quality",
            "High Quality",
            "Ultra Quality",
        ],
        field_options={
            "default": "Default Quality",
            "tooltip": (
                "Draft Quality renders --draft, Default Quality is implicit, "
                "High renders --q 2, Ultra renders --q 4 (v7 only)."
            ),
        },
        role=InputRole.PROMPT_FLAG,
        renderer=_render_v7_quality,
    ),
    "batch": InputSpec(
        key="batch",
        field_name="batch",
        field_type="INT",
        field_options={
            "default": 4,
            "min": 4,
            "max": 160,
            "step": 4,
            "tooltip": (
                "Total images to request. Midjourney returns 4-image grids, so "
                "batch is clamped to 4-160 and rounded down to a multiple of 4. "
                "Internally this maps to Midjourney --repeat (batch 4 = default "
                "grid, batch 8 = --repeat 2, batch 12 = --repeat 3)."
            ),
        },
        role=InputRole.PROMPT_FLAG,
        renderer=_render_batch_repeat,
        normalizer=_normalize_batch_count,
    ),
    "tile": InputSpec(
        key="tile",
        field_name="tile",
        field_type="BOOLEAN",
        field_options={"default": False, "tooltip": "Seamless tiling (--tile)"},
        role=InputRole.PROMPT_FLAG,
        renderer=_render_boolean_flag("--tile"),
    ),
    "seed": InputSpec(
        key="seed",
        field_name="seed",
        field_type="INT",
        field_options={
            "default": RANDOM_SEED,
            "min": 0,
            "max": 4294967295,
            "step": 1,
            "tooltip": "Random seed for reproducibility (--seed)",
        },
        role=InputRole.PROMPT_FLAG,
        renderer=_render_seed,
    ),
    "use_raw": InputSpec(
        key="use_raw",
        field_name="use_raw",
        field_type="BOOLEAN",
        field_options={
            "default": False,
            "label_on": "--raw enabled",
            "label_off": "--raw disabled",
            "tooltip": "Enable Raw Mode (--raw)",
        },
        role=InputRole.PROMPT_FLAG,
        renderer=_render_boolean_flag("--raw"),
    ),
    "translate_weights": InputSpec(
        key="translate_weights",
        field_name="translate_weights",
        field_type="BOOLEAN",
        field_options={
            "default": True,
            "label_on": "Translate SD Weights",
            "label_off": "Don't Translate Weights",
            "tooltip": "Convert SD weights to MJ. Example: (cat:1.4) → cat::1.4",
        },
        role=InputRole.BUILD_CONTROL,
    ),
    "profile_code": InputSpec(
        key="profile_code",
        field_name="profile_code",
        field_type="STRING",
        field_options={
            "default": "",
            "tooltip": "Personalization code (--p). Leave blank for no personalization.",
        },
        role=InputRole.PROMPT_FLAG,
        renderer=_render_flag("--p"),
        normalizer=_normalize_string_field,
        validator=_validate_personalization_conflict,
    ),
    "use_personalization": InputSpec(
        key="use_personalization",
        field_name="use_personalization",
        field_type="BOOLEAN",
        field_options={
            "default": False,
            "label_on": "Personalization enabled",
            "label_off": "Personalization disabled",
            "tooltip": "Enable the default personalization profile (--p).",
        },
        role=InputRole.PROMPT_FLAG,
        renderer=_render_bare_flag("--p"),
        validator=_validate_personalization_conflict,
    ),
    "exp": InputSpec(
        key="exp",
        field_name="exp",
        field_type="STRING",
        field_options={
            "default": "",
            "tooltip": "Experimental aesthetics value (--exp). Passed through as provided.",
        },
        role=InputRole.PROMPT_FLAG,
        renderer=_render_flag("--exp"),
        normalizer=_normalize_string_field,
    ),
    "images": InputSpec(
        key="images",
        field_name="images",
        field_type="IMAGE,MJ_IMAGE_PROMPT",
        field_options={
            "tooltip": "Optional Midjourney Image Prompt images. Accepts a raw IMAGE or a wrapped Midjourney Image Prompt payload.",
        },
        role=InputRole.SUBMISSION_CONTROL,
    ),
    "style_references": InputSpec(
        key="style_references",
        field_name="style_references",
        field_type="IMAGE,MJ_STYLE_REFERENCE",
        field_options={
            "tooltip": "Optional Midjourney Style Reference images. Accepts a raw IMAGE or a wrapped Midjourney Style Reference payload.",
        },
        role=InputRole.SUBMISSION_CONTROL,
    ),
    "character_references": InputSpec(
        key="character_references",
        field_name="character_references",
        field_type="IMAGE,MJ_CHARACTER_REFERENCE",
        field_options={
            "tooltip": "Optional Midjourney Character Reference images. Accepts a raw IMAGE or a wrapped Midjourney Character Reference payload.",
        },
        role=InputRole.SUBMISSION_CONTROL,
    ),
    "omni_reference": InputSpec(
        key="omni_reference",
        field_name="omni_reference",
        field_type="IMAGE,MJ_OMNI_REFERENCE",
        field_options={
            "tooltip": "Optional Midjourney Omni Reference image. Accepts a raw IMAGE or a wrapped Midjourney Omni Reference payload.",
        },
        role=InputRole.SUBMISSION_CONTROL,
    ),
    "custom_args": InputSpec(
        key="custom_args",
        field_name="custom_args",
        field_type="STRING",
        field_options={
            "default": "",
            "tooltip": "Advanced: Append custom MJ arguments. Use valid MJ parameter codes or you will break things. Leave blank for none.",
        },
        role=InputRole.PROMPT_FLAG,
        renderer=_render_custom_args,
    ),
    "v4_model": InputSpec(
        key="v4_model",
        field_name="model",
        field_type=[
            "Midjourney v4",
            "Midjourney v4a",
            "Midjourney v4b",
            "Midjourney v4c",
        ],
        field_options={
            "default": "Midjourney v4",
            "tooltip": "Select the Midjourney v4 model (--v 4, --v 4a, --v 4b, --v 4c)",
        },
        role=InputRole.LOCAL_ONLY,
    ),
    "v5_model": InputSpec(
        key="v5_model",
        field_name="model",
        field_type=["Midjourney v5.2", "Midjourney v5.1", "Midjourney v5"],
        field_options={
            "default": "Midjourney v5.2",
            "tooltip": "Select the Midjourney v5 model (--v 5, --v 5.1, or --v 5.2)",
        },
        role=InputRole.LOCAL_ONLY,
    ),
    "v6_model": InputSpec(
        key="v6_model",
        field_name="model",
        field_type=["Midjourney v6.1", "Midjourney v6"],
        field_options={
            "default": "Midjourney v6.1",
            "tooltip": "Select the Midjourney v6 model (--v 6 or --v 6.1)",
        },
        role=InputRole.LOCAL_ONLY,
    ),
    "niji5_style": InputSpec(
        key="niji5_style",
        field_name="niji5_style",
        field_type=["original", "cute", "expressive", "scenic"],
        field_options={
            "default": "original",
            "tooltip": "Niji 5 style preset (--style)",
        },
        role=InputRole.LOCAL_ONLY,
    ),
}
