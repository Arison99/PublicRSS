"""
Three-Layer Validation Pipeline for Gemma Intelligence Contract.
Layer 1: JSON Syntax
Layer 2: Pydantic Structural & Enum Constraints
Layer 3: Semantic Sanity & Anti-Injection Guards
"""
import re
import json
from typing import Tuple, Optional, Dict, Any
from pydantic import ValidationError

from .schemas import AIProposalSchema


class ValidationPipelineError(Exception):
    """Base exception for proposal validation errors."""
    def __init__(self, layer: int, message: str, raw_output: str = ""):
        super().__init__(f"Layer {layer} Error: {message}")
        self.layer = layer
        self.message = message
        self.raw_output = raw_output


# Banned instruction phrases that should never appear in a legitimate catalog proposal
BANNED_SEMANTIC_PHRASES = [
    "ignore all previous instructions",
    "ignore previous instructions",
    "disregard previous instructions",
    "system prompt",
    "developer instruction",
    "you are a large language model",
    "as an ai",
    "<untrusted_feed_data>",
    "</untrusted_feed_data>",
    "jailbreak",
]


def extract_json_substring(text: str) -> str:
    """
    Cleans markdown code fences or finds the outer JSON object brackets.
    """
    cleaned = text.strip()

    # Remove markdown code fences ```json ... ```
    if "```" in cleaned:
        # Match ```json ... ``` or ``` ... ```
        pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
        matches = re.findall(pattern, cleaned, re.IGNORECASE)
        if matches:
            cleaned = matches[0].strip()

    # If still not starting with {, search for first { and matching last }
    if not cleaned.startswith("{"):
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            cleaned = cleaned[start_idx : end_idx + 1]

    return cleaned


def validate_proposal(
    raw_text: str,
    feed_title: str = "",
) -> Tuple[bool, Optional[AIProposalSchema], str]:
    """
    Executes the three-layer validation pipeline.
    Returns: (is_valid, parsed_schema_instance, error_message)
    """
    # ----------------------------------------------------
    # LAYER 1: JSON Syntax Check
    # ----------------------------------------------------
    clean_json_str = extract_json_substring(raw_text)
    if not clean_json_str:
        return False, None, "Layer 1 Error: Model response does not contain JSON structure."

    try:
        data = json.loads(clean_json_str)
    except json.JSONDecodeError as err:
        return False, None, f"Layer 1 Error: Invalid JSON syntax - {err.msg} at line {err.lineno} col {err.colno}"

    if not isinstance(data, dict):
        return False, None, "Layer 1 Error: Model response is a JSON array or scalar, expected a JSON object."

    # ----------------------------------------------------
    # LAYER 2: Pydantic Validation (Types, Enums, Bounds, extra='forbid')
    # ----------------------------------------------------
    try:
        validated_schema = AIProposalSchema.model_validate(data)
    except ValidationError as val_err:
        errors = val_err.errors()
        error_details = []
        for e in errors:
            field_name = ".".join(str(p) for p in e.get("loc", []))
            msg = e.get("msg", "invalid")
            error_details.append(f"Field '{field_name}': {msg}")
        return False, None, f"Layer 2 Error (Schema): {'; '.join(error_details)}"
    except Exception as exc:
        return False, None, f"Layer 2 Error: {str(exc)}"

    # ----------------------------------------------------
    # LAYER 3: Semantic Sanity Checks
    # ----------------------------------------------------
    # 3.1 Primary topic must NOT be identical to the feed title
    if feed_title:
        norm_title = feed_title.strip().lower()
        norm_topic = validated_schema.primary_topic.strip().lower()
        if norm_topic == norm_title or (len(norm_title) > 3 and norm_topic in norm_title and len(norm_topic) == len(norm_title)):
            return False, None, f"Layer 3 Semantic Error: primary_topic ('{validated_schema.primary_topic}') must not match the feed title ('{feed_title}')."

    # 3.2 Primary topic word count check
    topic_words = validated_schema.primary_topic.split()
    if not (1 <= len(topic_words) <= 3):
        return False, None, f"Layer 3 Semantic Error: primary_topic must be 1 to 3 words, found {len(topic_words)}: '{validated_schema.primary_topic}'."

    # 3.3 Description length check (20 - 300 chars)
    desc_len = len(validated_schema.description.strip())
    if not (20 <= desc_len <= 300):
        return False, None, f"Layer 3 Semantic Error: description length must be 20 to 300 characters, got {desc_len}."

    # 3.4 Evidence items check (max 3 items, each max 50 chars, non-empty)
    if len(validated_schema.evidence) > 3:
        return False, None, f"Layer 3 Semantic Error: evidence can have at most 3 items, got {len(validated_schema.evidence)}."
    for ev in validated_schema.evidence:
        if not ev.strip():
            return False, None, "Layer 3 Semantic Error: evidence items cannot be blank strings."
        if len(ev.strip()) > 50:
            return False, None, f"Layer 3 Semantic Error: evidence item exceeds 50 chars ('{ev}')."

    # 3.5 Check for adversarial prompt leaking or instructions in fields
    combined_content = (
        f"{validated_schema.primary_topic} {' '.join(validated_schema.sub_topics)} "
        f"{validated_schema.description} {' '.join(validated_schema.evidence)} "
        f"{validated_schema.suggested_collection}"
    ).lower()

    for phrase in BANNED_SEMANTIC_PHRASES:
        if phrase in combined_content:
            return False, None, f"Layer 3 Security Error: Output contains disallowed instruction/prompt-leak phrase: '{phrase}'."

    return True, validated_schema, ""
