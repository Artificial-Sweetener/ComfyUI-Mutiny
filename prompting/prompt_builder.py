"""Build ComfyUI input metadata and prompt strings from declarative node definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .image_validation import validate_image_prompting
from .input_specs import INPUT_SPECS, InputRole, NodeDefinition
from .validators import translate_stable_diffusion_weights
from .wrapped_images import render_wrapped_image_flags


@dataclass(frozen=True)
class PromptBuildResult:
    """Capture the prompt text and non-prompt controls derived from node inputs."""

    prompt_text: str
    values: dict[str, Any]
    build_controls: dict[str, Any]
    submission_controls: dict[str, Any]


def build_input_types(
    node_definition: NodeDefinition,
) -> dict[str, dict[str, tuple[Any, dict[str, Any]]]]:
    """Build the ComfyUI ``INPUT_TYPES`` declaration for a node definition."""
    required: dict[str, tuple[Any, dict[str, Any]]] = {}
    optional: dict[str, tuple[Any, dict[str, Any]]] = {}

    for binding in node_definition.bindings:
        spec = INPUT_SPECS[binding.spec_key]
        target = required if binding.required else optional
        target[spec.field_name] = spec.comfy_ui_entry()

    return {"required": required, "optional": optional}


def build_prompt(
    node_definition: NodeDefinition,
    input_values: Mapping[str, Any],
) -> PromptBuildResult:
    """Normalize, validate, and render prompt data for one node execution."""
    normalized_values = _normalize_values(node_definition, input_values)
    build_controls = _collect_controls(
        node_definition, normalized_values, InputRole.BUILD_CONTROL
    )
    submission_controls = _collect_controls(
        node_definition, normalized_values, InputRole.SUBMISSION_CONTROL
    )

    if build_controls.get("translate_weights"):
        for field_name in ("prompt", "negative_prompt"):
            if normalized_values.get(field_name):
                normalized_values[field_name] = translate_stable_diffusion_weights(
                    normalized_values[field_name]
                )

    _validate_values(node_definition, normalized_values)
    validate_image_prompting(
        node_definition=node_definition,
        values=normalized_values,
    )
    prompt_text = _render_prompt_text(node_definition, normalized_values)
    prompt_text = _append_wrapped_image_flags(prompt_text, normalized_values)
    return PromptBuildResult(
        prompt_text=prompt_text,
        values=normalized_values,
        build_controls=build_controls,
        submission_controls=submission_controls,
    )


def _normalize_values(
    node_definition: NodeDefinition,
    input_values: Mapping[str, Any],
) -> dict[str, Any]:
    """Normalize raw node inputs in declaration order for prompt processing."""
    normalized_values: dict[str, Any] = {}

    for binding in node_definition.bindings:
        spec = INPUT_SPECS[binding.spec_key]
        current_value = input_values.get(spec.field_name)
        if spec.normalizer is not None:
            current_value = spec.normalizer(current_value, normalized_values)
        normalized_values[spec.field_name] = current_value

    return normalized_values


def _collect_controls(
    node_definition: NodeDefinition,
    normalized_values: Mapping[str, Any],
    role: InputRole,
) -> dict[str, Any]:
    """Collect non-prompt control fields for one declarative role."""
    controls: dict[str, Any] = {}
    for binding in node_definition.bindings:
        spec = INPUT_SPECS[binding.spec_key]
        if spec.role == role:
            controls[spec.field_name] = normalized_values.get(spec.field_name)
    return controls


def _validate_values(
    node_definition: NodeDefinition,
    normalized_values: Mapping[str, Any],
) -> None:
    """Run any spec-local validators against the normalized values."""
    for binding in node_definition.bindings:
        spec = INPUT_SPECS[binding.spec_key]
        if spec.validator is not None:
            spec.validator(normalized_values.get(spec.field_name), normalized_values)


def _render_prompt_text(
    node_definition: NodeDefinition,
    normalized_values: Mapping[str, Any],
) -> str:
    """Render prompt text first, then append prompt flags in declaration order."""
    prompt_parts: list[str] = []
    flag_parts: list[str] = []

    for binding in node_definition.bindings:
        spec = INPUT_SPECS[binding.spec_key]
        if spec.renderer is None:
            continue

        fragment = spec.renderer(
            normalized_values.get(spec.field_name),
            normalized_values,
        )
        if not fragment:
            continue

        if spec.role == InputRole.PROMPT_TEXT:
            prompt_parts.append(fragment.strip())
        elif spec.role == InputRole.PROMPT_FLAG:
            flag_parts.append(fragment)

    prompt_text = " ".join(part for part in prompt_parts if part)
    if not prompt_text:
        return "".join(flag_parts).lstrip()
    return f"{prompt_text}{''.join(flag_parts)}"


def _append_wrapped_image_flags(
    prompt_text: str,
    normalized_values: Mapping[str, Any],
) -> str:
    """Append explicit wrapped-image metadata flags after standard prompt rendering."""
    image_flag_text = render_wrapped_image_flags(normalized_values)
    if not image_flag_text:
        return prompt_text
    if not prompt_text:
        return image_flag_text.lstrip()
    return f"{prompt_text}{image_flag_text}"
