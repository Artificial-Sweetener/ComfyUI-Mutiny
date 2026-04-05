"""Implement the custom-version Midjourney request node."""

from __future__ import annotations

from ..prompting import IMAGINE_SUBMISSION_BINDINGS, NodeDefinition, bind, build_prompt
from .common import (
    NodeBoundaryContext,
    PromptDrivenNode,
    build_imagine_intent,
    execute_node_boundary,
    run_imagine_intent,
)


class MidjourneyCustomRequest(PromptDrivenNode):
    """Submit a custom-version Midjourney job through declarative prompt pieces."""

    NODE_DEFINITION = NodeDefinition(
        bindings=(
            bind("version", required=True),
            bind("prompt", required=True),
            bind("negative_prompt"),
            bind("stylize"),
            bind("custom_args"),
            bind("chaos"),
            bind("aspect_ratio"),
            bind("batch"),
            bind("tile"),
            bind("seed"),
            bind("send_explicit_seed"),
            *IMAGINE_SUBMISSION_BINDINGS,
            bind("style_references"),
            bind("character_references"),
            bind("omni_reference"),
            bind("translate_weights"),
        ),
        image_capability_target="midjourney_custom",
    )

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "generate"
    CATEGORY = "image"

    def generate(self, **kwargs):
        """Build the prompt, execute the job, and return split grid images."""

        def submit():
            """Build the custom-version prompt text and execute the request."""
            build_result = build_prompt(self.NODE_DEFINITION, kwargs)
            return run_imagine_intent(
                self,
                intent=build_imagine_intent(
                    build_result=build_result,
                    prompt_text=build_result.prompt_text,
                    node_name=self.__class__.__name__,
                    model_name=kwargs.get("version"),
                ),
            )

        return execute_node_boundary(
            context=NodeBoundaryContext(
                node_name=self.__class__.__name__,
                action_name="imagine",
                model_name=kwargs.get("version"),
            ),
            operation=submit,
        )


__all__ = ["MidjourneyCustomRequest"]
