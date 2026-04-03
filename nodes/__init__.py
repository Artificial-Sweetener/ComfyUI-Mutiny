"""Expose the exported ComfyUI node classes and display mappings."""

from .actions import MidjourneyUpscaleNode
from .animate import MidjourneyAnimateNode
from .custom import MidjourneyCustomRequest
from .describe import MidjourneyDescribeNode
from .extend import MidjourneyExtendNode
from .midjourney_versions import (
    MidjourneyV4Request,
    MidjourneyV5Request,
    MidjourneyV6Request,
    MidjourneyV7Request,
    MidjourneyV8AlphaRequest,
)
from .niji import Niji4Request, Niji5Request, Niji6Request, Niji7Request
from .pan import MidjourneyPanNode
from .variation import MidjourneyVariationNode
from .vary_region import MidjourneyVaryRegionNode
from .wrapped_images import (
    MidjourneyCharacterReferenceNode,
    MidjourneyImagePromptNode,
    MidjourneyOmniReferenceNode,
    MidjourneyStyleReferenceNode,
)
from .zoom import MidjourneyZoomNode

NODE_CLASS_MAPPINGS = {
    "MidjourneyImagePromptNode": MidjourneyImagePromptNode,
    "MidjourneyStyleReferenceNode": MidjourneyStyleReferenceNode,
    "MidjourneyCharacterReferenceNode": MidjourneyCharacterReferenceNode,
    "MidjourneyOmniReferenceNode": MidjourneyOmniReferenceNode,
    "MidjourneyDescribeNode": MidjourneyDescribeNode,
    "MidjourneyAnimateNode": MidjourneyAnimateNode,
    "MidjourneyExtendNode": MidjourneyExtendNode,
    "MidjourneyCustomRequest": MidjourneyCustomRequest,
    "MidjourneyV4Request": MidjourneyV4Request,
    "MidjourneyV5Request": MidjourneyV5Request,
    "MidjourneyV6Request": MidjourneyV6Request,
    "MidjourneyV7Request": MidjourneyV7Request,
    "MidjourneyV8AlphaRequest": MidjourneyV8AlphaRequest,
    "Niji4Request": Niji4Request,
    "Niji5Request": Niji5Request,
    "Niji6Request": Niji6Request,
    "Niji7Request": Niji7Request,
    "MidjourneyUpscaleNode": MidjourneyUpscaleNode,
    "MidjourneyPanNode": MidjourneyPanNode,
    "MidjourneyZoomNode": MidjourneyZoomNode,
    "MidjourneyVariationNode": MidjourneyVariationNode,
    "MidjourneyVaryRegionNode": MidjourneyVaryRegionNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MidjourneyImagePromptNode": "Midjourney Image Prompt",
    "MidjourneyStyleReferenceNode": "Midjourney Style Reference",
    "MidjourneyCharacterReferenceNode": "Midjourney Character Reference",
    "MidjourneyOmniReferenceNode": "Midjourney Omni Reference",
    "MidjourneyDescribeNode": "Midjourney Describe",
    "MidjourneyAnimateNode": "Midjourney Animate",
    "MidjourneyExtendNode": "Midjourney Extend",
    "MidjourneyCustomRequest": "Midjourney Custom Request",
    "MidjourneyV4Request": "Midjourney v4 Request",
    "MidjourneyV5Request": "Midjourney v5 Request",
    "MidjourneyV6Request": "Midjourney v6 Request",
    "MidjourneyV7Request": "Midjourney v7 Request",
    "MidjourneyV8AlphaRequest": "Midjourney v8 Alpha Request",
    "Niji4Request": "Niji 4 Request",
    "Niji5Request": "Niji 5 Request",
    "Niji6Request": "Niji 6 Request",
    "Niji7Request": "Niji 7 Request",
    "MidjourneyUpscaleNode": "Midjourney Upscale",
    "MidjourneyPanNode": "Midjourney Pan",
    "MidjourneyZoomNode": "Midjourney Zoom",
    "MidjourneyVariationNode": "Midjourney Variation",
    "MidjourneyVaryRegionNode": "Midjourney Vary Region",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
