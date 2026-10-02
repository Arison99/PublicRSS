"""
PublicRSS AI Subsystem.
"""
from .schemas import AIProposalSchema, TargetAudience, ContentType, ContentTone
from .prompts import build_analysis_prompt, build_correction_prompt
from .validator import validate_proposal, extract_json_substring
from .provider import GemmaProvider, generate_fallback_mock_proposal

__all__ = [
    "AIProposalSchema",
    "TargetAudience",
    "ContentType",
    "ContentTone",
    "build_analysis_prompt",
    "build_correction_prompt",
    "validate_proposal",
    "extract_json_substring",
    "GemmaProvider",
    "generate_fallback_mock_proposal",
]
