"""Implement the Niji request nodes."""

from __future__ import annotations

from ..prompting import IMAGINE_SUBMISSION_BINDINGS, NodeDefinition, bind, build_prompt
from .common import (
    NodeBoundaryContext,
    PromptDrivenNode,
    build_imagine_intent,
    execute_node_boundary,
    run_imagine_intent,
)


class Niji5Request(PromptDrivenNode):
    """Submit a Niji 5 job."""

    NODE_DEFINITION = NodeDefinition(
        bindings=(
            bind("prompt", required=True),
            bind("negative_prompt"),
            bind("stylize"),
            bind("chaos"),
            bind("weird"),
            bind("niji5_style"),
            bind("niji_aspect_ratio"),
            bind("quality"),
            bind("batch"),
            bind("tile"),
            bind("seed"),
            bind("send_explicit_seed"),
            bind("use_raw"),
            *IMAGINE_SUBMISSION_BINDINGS,
            bind("translate_weights"),
            bind("custom_args"),
        ),
        image_capability_target="niji5",
    )

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "generate"
    CATEGORY = "image"

    def generate(self, niji5_style="original", **kwargs):
        """Build the prompt, execute the job, and return grid outputs."""

        def submit():
            """Build and execute one Niji 5 prompt submission."""
            build_result = build_prompt(
                self.NODE_DEFINITION,
                {"niji5_style": niji5_style, **kwargs},
            )
            prompt_text = f"{build_result.prompt_text} --niji 5"
            if niji5_style != "original":
                prompt_text += f" --style {niji5_style}"
            return run_imagine_intent(
                self,
                intent=build_imagine_intent(
                    build_result=build_result,
                    prompt_text=prompt_text,
                    node_name=self.__class__.__name__,
                    model_name="Niji 5",
                ),
            )

        return execute_node_boundary(
            context=NodeBoundaryContext(
                node_name=self.__class__.__name__,
                action_name="imagine",
                model_name="Niji 5",
            ),
            operation=submit,
        )


class Niji4Request(PromptDrivenNode):
    """Submit a Niji 4 job."""

    NODE_DEFINITION = NodeDefinition(
        bindings=(
            bind("prompt", required=True),
            bind("negative_prompt"),
            bind("stylize"),
            bind("chaos"),
            bind("weird"),
            bind("niji_aspect_ratio"),
            bind("quality_legacy"),
            bind("batch"),
            bind("tile"),
            bind("seed"),
            bind("send_explicit_seed"),
            *IMAGINE_SUBMISSION_BINDINGS,
            bind("translate_weights"),
            bind("custom_args"),
        ),
        image_capability_target="niji4",
    )

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "generate"
    CATEGORY = "image"

    def generate(self, **kwargs):
        """Build the prompt, execute the job, and return grid outputs."""

        def submit():
            """Build and execute one Niji 4 prompt submission."""
            build_result = build_prompt(self.NODE_DEFINITION, kwargs)
            return run_imagine_intent(
                self,
                intent=build_imagine_intent(
                    build_result=build_result,
                    prompt_text=f"{build_result.prompt_text} --niji 4",
                    node_name=self.__class__.__name__,
                    model_name="Niji 4",
                ),
            )

        return execute_node_boundary(
            context=NodeBoundaryContext(
                node_name=self.__class__.__name__,
                action_name="imagine",
                model_name="Niji 4",
            ),
            operation=submit,
        )


class Niji6Request(PromptDrivenNode):
    """Submit a Niji 6 job."""

    NODE_DEFINITION = NodeDefinition(
        bindings=(
            bind("prompt", required=True),
            bind("negative_prompt"),
            bind("stylize"),
            bind("chaos"),
            bind("weird"),
            bind("style_references"),
            bind("character_references"),
            bind("profile_code"),
            bind("niji_aspect_ratio"),
            bind("quality"),
            bind("batch"),
            bind("tile"),
            bind("seed"),
            bind("send_explicit_seed"),
            bind("use_raw"),
            *IMAGINE_SUBMISSION_BINDINGS,
            bind("translate_weights"),
            bind("custom_args"),
        ),
        image_capability_target="niji6",
    )

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "generate"
    CATEGORY = "image"

    def generate(self, **kwargs):
        """Build the prompt, execute the job, and return grid outputs."""

        def submit():
            """Build and execute one Niji 6 prompt submission."""
            build_result = build_prompt(self.NODE_DEFINITION, kwargs)
            return run_imagine_intent(
                self,
                intent=build_imagine_intent(
                    build_result=build_result,
                    prompt_text=f"{build_result.prompt_text} --niji 6",
                    node_name=self.__class__.__name__,
                    model_name="Niji 6",
                ),
            )

        return execute_node_boundary(
            context=NodeBoundaryContext(
                node_name=self.__class__.__name__,
                action_name="imagine",
                model_name="Niji 6",
            ),
            operation=submit,
        )


class Niji7Request(PromptDrivenNode):
    """Submit a Niji 7 job."""

    NODE_DEFINITION = NodeDefinition(
        bindings=(
            bind("prompt", required=True),
            bind("negative_prompt"),
            bind("stylize"),
            bind("chaos"),
            bind("weird"),
            bind("style_references"),
            bind("niji_aspect_ratio"),
            bind("batch"),
            bind("tile"),
            bind("seed"),
            bind("send_explicit_seed"),
            bind("use_raw"),
            *IMAGINE_SUBMISSION_BINDINGS,
            bind("custom_args"),
        ),
        image_capability_target="niji7",
    )

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "generate"
    CATEGORY = "image"

    def generate(self, **kwargs):
        """Build the prompt, execute the job, and return grid outputs."""

        def submit():
            """Build and execute one Niji 7 prompt submission."""
            build_result = build_prompt(self.NODE_DEFINITION, kwargs)
            return run_imagine_intent(
                self,
                intent=build_imagine_intent(
                    build_result=build_result,
                    prompt_text=f"{build_result.prompt_text} --niji 7",
                    node_name=self.__class__.__name__,
                    model_name="Niji 7",
                ),
            )

        return execute_node_boundary(
            context=NodeBoundaryContext(
                node_name=self.__class__.__name__,
                action_name="imagine",
                model_name="Niji 7",
            ),
            operation=submit,
        )


__all__ = ["Niji4Request", "Niji5Request", "Niji6Request", "Niji7Request"]
