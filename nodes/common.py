"""Provide shared execution helpers for exported ComfyUI node modules."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Mapping, TypeVar

import torch

from ..prompting.wrapped_images import (
    unwrap_character_references,
    unwrap_omni_reference,
    unwrap_prompt_images,
    unwrap_style_references,
)
from ..runtime import MutinyRuntimeService, get_runtime_service
from ..runtime.errors import RuntimeAdapterError
from ..runtime.models import RuntimeImagineImageInputs
from ..services import (
    build_comfy_progress_reporter,
    build_split_image_output,
    comfy_images_to_data_urls,
)

logger = logging.getLogger(__name__)

_T = TypeVar("_T")


class NodeExecutionError(RuntimeError):
    """Raise when one exported node fails with a safe plugin-facing message."""


@dataclass(frozen=True)
class NodeBoundaryContext:
    """Capture the safe execution context logged for one node action."""

    node_name: str
    action_name: str
    model_name: str | None = None
    job_id: str | None = None


@dataclass(frozen=True)
class ImagineNodeIntent:
    """Describe one prompt-driven generation request submitted by a node."""

    prompt_text: str
    node_name: str
    model_name: str | None
    image_inputs: RuntimeImagineImageInputs | None = None


class RuntimeBackedNode:
    """Resolve the shared Mutiny runtime lazily for each node execution."""

    def __init__(self) -> None:
        """Initialize the optional test override for the runtime service."""
        self._runtime_service: MutinyRuntimeService | None = None

    def _get_runtime_service(self) -> MutinyRuntimeService:
        """Return the overridden runtime service or the shared process service."""
        if self._runtime_service is not None:
            return self._runtime_service
        return get_runtime_service()


class PromptDrivenNode(RuntimeBackedNode):
    """Expose ``INPUT_TYPES`` from one declarative prompting definition."""

    NODE_DEFINITION = None

    @classmethod
    def INPUT_TYPES(cls):
        """Return the ComfyUI input declaration for the node definition."""
        from ..prompting import build_input_types

        return build_input_types(cls.NODE_DEFINITION)


def execute_node_boundary(
    *,
    context: NodeBoundaryContext,
    operation: Callable[[], _T],
) -> _T:
    """Run one node action and translate unexpected failures once."""
    try:
        return operation()
    except NodeExecutionError:
        raise
    except (RuntimeAdapterError, ValueError) as exc:
        logger.error(
            "Node execution failed node=%s action=%s model=%s job_id=%s error=%s",
            context.node_name,
            context.action_name,
            context.model_name or "-",
            context.job_id or "-",
            _build_error_message(exc),
        )
        raise NodeExecutionError(_build_error_message(exc)) from exc
    except Exception as exc:
        logger.exception(
            "Unexpected node execution failure node=%s action=%s model=%s job_id=%s",
            context.node_name,
            context.action_name,
            context.model_name or "-",
            context.job_id or "-",
        )
        raise NodeExecutionError(_build_error_message(exc)) from exc


def run_imagine_intent(
    node: RuntimeBackedNode,
    *,
    intent: ImagineNodeIntent,
) -> tuple[torch.Tensor]:
    """Submit one imagine request through the shared runtime and return images."""
    progress_reporter, _preview_image = build_comfy_progress_reporter()
    result = node._get_runtime_service().imagine_and_wait(
        intent.prompt_text,
        node_name=intent.node_name,
        model_name=intent.model_name,
        image_inputs=intent.image_inputs,
        progress_reporter=progress_reporter,
    )
    return (build_split_image_output(result),)


def build_imagine_intent(
    *,
    build_result,
    prompt_text: str,
    node_name: str,
    model_name: str | None,
) -> ImagineNodeIntent:
    """Build one shared imagine intent from declarative prompt-build output."""
    return ImagineNodeIntent(
        prompt_text=prompt_text,
        node_name=node_name,
        model_name=model_name,
        image_inputs=build_runtime_image_inputs(
            build_result.submission_controls,
        ),
    )


def build_runtime_image_inputs(
    submission_controls: Mapping[str, Any],
) -> RuntimeImagineImageInputs | None:
    """Encode submission-control images into the structured runtime imagine payload."""
    prompt_images = _coerce_prompt_images(submission_controls.get("images"))
    (
        style_reference_images,
        style_reference_multipliers,
    ) = _coerce_style_references(submission_controls.get("style_references"))
    character_reference_images = _coerce_character_references(
        submission_controls.get("character_references")
    )
    omni_reference_image = _coerce_omni_reference(
        submission_controls.get("omni_reference")
    )

    image_inputs = RuntimeImagineImageInputs(
        prompt_images=prompt_images,
        style_reference_images=style_reference_images,
        style_reference_multipliers=style_reference_multipliers,
        character_reference_images=character_reference_images,
        omni_reference_image=omni_reference_image,
    )
    return None if image_inputs.is_empty else image_inputs


def _coerce_prompt_images(image_value: Any) -> tuple[str, ...]:
    """Encode raw or wrapped prompt-image inputs into runtime prompt images."""
    images, _image_weight = unwrap_prompt_images(image_value)
    return _encode_optional_images(images)


def _coerce_style_references(
    image_value: Any,
) -> tuple[tuple[str, ...], tuple[float, ...]]:
    """Encode raw or wrapped style-reference inputs into runtime style data."""
    images, _style_weight, _style_version, multipliers = unwrap_style_references(
        image_value
    )
    return _encode_optional_images(images), multipliers


def _coerce_character_references(image_value: Any) -> tuple[str, ...]:
    """Encode raw or wrapped character-reference inputs into runtime character images."""
    images, _character_weight = unwrap_character_references(image_value)
    return _encode_optional_images(images)


def _coerce_omni_reference(image_value: Any) -> str | None:
    """Encode raw or wrapped Omni inputs into one runtime Omni image."""
    image, _omni_weight = unwrap_omni_reference(image_value)
    return _encode_single_optional_image(image)


def _encode_optional_images(image_value: Any) -> tuple[str, ...]:
    """Encode an optional ComfyUI IMAGE value into one or more data URLs."""
    if image_value is None:
        return ()
    return comfy_images_to_data_urls(image_value)


def _encode_single_optional_image(image_value: Any) -> str | None:
    """Encode an optional single-image ComfyUI IMAGE value into one data URL."""
    if image_value is None:
        return None
    encoded_images = comfy_images_to_data_urls(image_value)
    if len(encoded_images) != 1:
        raise ValueError("Omni Reference accepts exactly one image.")
    return encoded_images[0]


def _build_error_message(exc: Exception) -> str:
    """Return the safe user-facing message for one node failure."""
    message = str(exc).strip()
    return message or "Unexpected node execution error."


__all__ = [
    "build_imagine_intent",
    "build_runtime_image_inputs",
    "ImagineNodeIntent",
    "NodeBoundaryContext",
    "NodeExecutionError",
    "PromptDrivenNode",
    "RuntimeBackedNode",
    "execute_node_boundary",
    "run_imagine_intent",
]
