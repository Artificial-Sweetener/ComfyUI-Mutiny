"""Implement the Midjourney version-family request nodes."""

from __future__ import annotations

from ..prompting import (
    IMAGINE_SUBMISSION_BINDINGS,
    NodeDefinition,
    bind,
    build_prompt,
)
from ..prompting.validators import validate_v4_model_aspect_ratio
from .common import (
    NodeBoundaryContext,
    PromptDrivenNode,
    build_imagine_intent,
    execute_node_boundary,
    run_imagine_intent,
)

_V4_MODEL_SUFFIXES = {
    "Midjourney v4": " --v 4",
    "Midjourney v4a": " --v 4a",
    "Midjourney v4b": " --v 4b",
    "Midjourney v4c": " --v 4c",
}

_V5_MODEL_SUFFIXES = {
    "Midjourney v5.2": " --v 5.2",
    "Midjourney v5.1": " --v 5.1",
    "Midjourney v5": " --v 5",
}

_V6_MODEL_SUFFIXES = {
    "Midjourney v6.1": " --v 6.1",
    "Midjourney v6": " --v 6",
}


class MidjourneyV4Request(PromptDrivenNode):
    """Submit a Midjourney v4 family job."""

    NODE_DEFINITION = NodeDefinition(
        bindings=(
            bind("v4_model", required=True),
            bind("prompt", required=True),
            bind("negative_prompt"),
            bind("stylize"),
            bind("chaos"),
            bind("aspect_ratio"),
            bind("quality_legacy"),
            bind("batch"),
            bind("tile"),
            bind("seed"),
            *IMAGINE_SUBMISSION_BINDINGS,
            bind("translate_weights"),
            bind("custom_args"),
        ),
        image_capability_target="midjourney_v4",
    )

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "generate"
    CATEGORY = "image"

    def generate(self, model="Midjourney v4", **kwargs):
        """Build the prompt, validate the ratio, and return grid outputs."""

        def submit():
            """Build and validate one Midjourney v4-family prompt submission."""
            build_result = build_prompt(
                self.NODE_DEFINITION, {"model": model, **kwargs}
            )
            aspect_ratio = build_result.values.get("aspect_ratio")
            if not aspect_ratio:
                raise ValueError("Aspect ratio is required for Midjourney v4 requests.")
            validate_v4_model_aspect_ratio(model, aspect_ratio)
            return run_imagine_intent(
                self,
                intent=build_imagine_intent(
                    build_result=build_result,
                    prompt_text=f"{build_result.prompt_text}{_V4_MODEL_SUFFIXES[model]}",
                    node_name=self.__class__.__name__,
                    model_name=model,
                ),
            )

        return execute_node_boundary(
            context=NodeBoundaryContext(
                node_name=self.__class__.__name__,
                action_name="imagine",
                model_name=model,
            ),
            operation=submit,
        )


class MidjourneyV5Request(PromptDrivenNode):
    """Submit a Midjourney v5 family job."""

    NODE_DEFINITION = NodeDefinition(
        bindings=(
            bind("v5_model", required=True),
            bind("prompt", required=True),
            bind("negative_prompt"),
            bind("stylize"),
            bind("chaos"),
            bind("weird"),
            bind("aspect_ratio"),
            bind("quality_legacy"),
            bind("batch"),
            bind("tile"),
            bind("seed"),
            bind("use_raw"),
            *IMAGINE_SUBMISSION_BINDINGS,
            bind("translate_weights"),
            bind("custom_args"),
        ),
        image_capability_target="midjourney_v5",
    )

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "generate"
    CATEGORY = "image"

    def generate(self, model="Midjourney v5.2", **kwargs):
        """Build the prompt, execute the job, and return grid outputs."""

        def submit():
            """Build and execute one Midjourney v5-family prompt submission."""
            build_result = build_prompt(
                self.NODE_DEFINITION, {"model": model, **kwargs}
            )
            return run_imagine_intent(
                self,
                intent=build_imagine_intent(
                    build_result=build_result,
                    prompt_text=f"{build_result.prompt_text}{_V5_MODEL_SUFFIXES[model]}",
                    node_name=self.__class__.__name__,
                    model_name=model,
                ),
            )

        return execute_node_boundary(
            context=NodeBoundaryContext(
                node_name=self.__class__.__name__,
                action_name="imagine",
                model_name=model,
            ),
            operation=submit,
        )


class MidjourneyV6Request(PromptDrivenNode):
    """Submit a Midjourney v6 family job."""

    NODE_DEFINITION = NodeDefinition(
        bindings=(
            bind("v6_model", required=True),
            bind("prompt", required=True),
            bind("negative_prompt"),
            bind("stylize"),
            bind("chaos"),
            bind("weird"),
            bind("style_references"),
            bind("character_references"),
            bind("profile_code"),
            bind("aspect_ratio"),
            bind("quality"),
            bind("batch"),
            bind("tile"),
            bind("seed"),
            bind("use_raw"),
            *IMAGINE_SUBMISSION_BINDINGS,
            bind("translate_weights"),
            bind("custom_args"),
        ),
        image_capability_target="midjourney_v6",
    )

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "generate"
    CATEGORY = "image"

    def generate(self, model="Midjourney v6.1", **kwargs):
        """Build the prompt, execute the job, and return grid outputs."""

        def submit():
            """Build and execute one Midjourney v6-family prompt submission."""
            build_result = build_prompt(
                self.NODE_DEFINITION, {"model": model, **kwargs}
            )
            return run_imagine_intent(
                self,
                intent=build_imagine_intent(
                    build_result=build_result,
                    prompt_text=f"{build_result.prompt_text}{_V6_MODEL_SUFFIXES[model]}",
                    node_name=self.__class__.__name__,
                    model_name=model,
                ),
            )

        return execute_node_boundary(
            context=NodeBoundaryContext(
                node_name=self.__class__.__name__,
                action_name="imagine",
                model_name=model,
            ),
            operation=submit,
        )


class MidjourneyV7Request(PromptDrivenNode):
    """Submit a Midjourney v7 job."""

    NODE_DEFINITION = NodeDefinition(
        bindings=(
            bind("prompt", required=True),
            bind("negative_prompt"),
            bind("stylize"),
            bind("chaos"),
            bind("weird"),
            bind("style_references"),
            bind("use_personalization"),
            bind("profile_code"),
            *IMAGINE_SUBMISSION_BINDINGS,
            bind("omni_reference"),
            bind("aspect_ratio"),
            bind("v7_quality"),
            bind("exp"),
            bind("batch"),
            bind("tile"),
            bind("seed"),
            bind("use_raw"),
            bind("custom_args"),
        ),
        image_capability_target="midjourney_v7",
    )

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "generate"
    CATEGORY = "image"

    def generate(self, **kwargs):
        """Build the prompt, execute the job, and return grid outputs."""

        def submit():
            """Build and execute one Midjourney v7 prompt submission."""
            build_result = build_prompt(self.NODE_DEFINITION, kwargs)
            return run_imagine_intent(
                self,
                intent=build_imagine_intent(
                    build_result=build_result,
                    prompt_text=f"{build_result.prompt_text} --v 7",
                    node_name=self.__class__.__name__,
                    model_name="Midjourney v7",
                ),
            )

        return execute_node_boundary(
            context=NodeBoundaryContext(
                node_name=self.__class__.__name__,
                action_name="imagine",
                model_name="Midjourney v7",
            ),
            operation=submit,
        )


class MidjourneyV8AlphaRequest(PromptDrivenNode):
    """Submit a conservative Midjourney v8 Alpha job with style-reference support."""

    NODE_DEFINITION = NodeDefinition(
        bindings=(
            bind("prompt", required=True),
            bind("negative_prompt"),
            bind("style_references"),
            bind("aspect_ratio"),
            bind("batch"),
            bind("seed"),
            bind("custom_args"),
        ),
        image_capability_target="midjourney_v8_alpha",
    )

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "generate"
    CATEGORY = "image"

    def generate(self, **kwargs):
        """Build the prompt, execute the job, and return v8 Alpha outputs."""

        def submit():
            """Build and execute one Midjourney v8 Alpha prompt submission."""
            build_result = build_prompt(self.NODE_DEFINITION, kwargs)
            return run_imagine_intent(
                self,
                intent=build_imagine_intent(
                    build_result=build_result,
                    prompt_text=f"{build_result.prompt_text} --v 8",
                    node_name=self.__class__.__name__,
                    model_name="Midjourney v8 Alpha",
                ),
            )

        return execute_node_boundary(
            context=NodeBoundaryContext(
                node_name=self.__class__.__name__,
                action_name="imagine",
                model_name="Midjourney v8 Alpha",
            ),
            operation=submit,
        )


__all__ = [
    "MidjourneyV4Request",
    "MidjourneyV5Request",
    "MidjourneyV6Request",
    "MidjourneyV7Request",
    "MidjourneyV8AlphaRequest",
]
