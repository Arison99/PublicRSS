"""
Gemma AI Provider with Two-Attempt Validation Retry Logic.
Connects to Google AI Studio API, executes inference, and enforces
strict retry policies with targeted correction prompts.
"""
import os
import json
import logging
from typing import Dict, Any, Optional, Tuple
from google import genai
from google.genai import errors as genai_errors

from .schemas import AIProposalSchema, TargetAudience, ContentType, ContentTone
from .prompts import build_analysis_prompt, build_correction_prompt
from .validator import validate_proposal

logger = logging.getLogger(__name__)

# Preferred model sequence
PREFERRED_MODELS = [
    os.environ.get("GEMMA_MODEL_NAME", "gemma-4-26b-a4b-it"),
    "gemini-3.1-flash-lite-preview",
    "gemini-flash-latest",
]


class GemmaProvider:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

    def _call_model(self, prompt: str) -> str:
        """
        Executes generation using the preferred model list, falling back if a model
        encounters transient or version errors.
        """
        if not self.client:
            raise RuntimeError("GEMINI_API_KEY is not configured.")

        last_error = None
        for model_name in PREFERRED_MODELS:
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                if response and response.text:
                    return response.text
            except Exception as exc:
                last_error = exc
                logger.warning(f"Model {model_name} invocation failed: {exc}. Trying next model...")
                continue

        raise RuntimeError(f"All AI model invocations failed. Last error: {last_error}")

    def generate_and_validate(
        self,
        payload: Dict[str, Any],
    ) -> Tuple[Optional[AIProposalSchema], str, int, Optional[str]]:
        """
        Executes the two-attempt inference loop:
        1. Attempt 1: Standard structured prompt.
        2. Validate Layer 1 (JSON), Layer 2 (Pydantic), Layer 3 (Semantic).
        3. If invalid, Attempt 2 with focused correction prompt.
        Returns: (validated_schema, raw_text, total_attempts, final_error)
        """
        feed_title = payload.get("feed_metadata", {}).get("title", "")

        # --- ATTEMPT 1 ---
        attempt_1_prompt = build_analysis_prompt(payload)
        try:
            attempt_1_raw = self._call_model(attempt_1_prompt)
        except Exception as exc:
            # If API call itself failed
            return None, "", 1, f"API Execution Error on Attempt 1: {str(exc)}"

        is_valid, schema_obj, error_msg = validate_proposal(attempt_1_raw, feed_title=feed_title)
        if is_valid and schema_obj:
            return schema_obj, attempt_1_raw, 1, None

        logger.info(f"Attempt 1 failed validation: {error_msg}. Initiating Attempt 2 with correction instruction...")

        # --- ATTEMPT 2 (With Correction Instruction) ---
        attempt_2_prompt = build_correction_prompt(payload, attempt_1_raw, error_msg)
        try:
            attempt_2_raw = self._call_model(attempt_2_prompt)
        except Exception as exc:
            return None, attempt_1_raw, 2, f"Attempt 1 failed ({error_msg}); Attempt 2 API error: {str(exc)}"

        is_valid_2, schema_obj_2, error_msg_2 = validate_proposal(attempt_2_raw, feed_title=feed_title)
        if is_valid_2 and schema_obj_2:
            return schema_obj_2, attempt_2_raw, 2, None

        logger.warning(f"Attempt 2 also failed validation: {error_msg_2}")
        return None, attempt_2_raw, 2, f"Validation failed after 2 attempts. Final error: {error_msg_2}"


def generate_fallback_mock_proposal(payload: Dict[str, Any]) -> AIProposalSchema:
    """
    Offline/deterministic mock generator for unit testing or fallback scenarios.
    """
    meta = payload.get("feed_metadata", {})
    articles = payload.get("sample_articles", [])
    title = meta.get("title", "Technology Feed")
    desc = meta.get("description", "")

    # Pick primary topic distinct from title
    primary_topic = "Tech & Software"
    if "python" in title.lower() or "code" in title.lower():
        primary_topic = "Python Programming"
    elif "news" in title.lower() or "world" in title.lower():
        primary_topic = "Current Affairs"
    elif "science" in title.lower() or "research" in title.lower():
        primary_topic = "Scientific Research"

    # Evidence
    evidence = []
    if articles:
        evidence.append(f"Recent article: {articles[0].get('title', '')[:40]}")
    if len(articles) > 1:
        evidence.append(f"Followup: {articles[1].get('title', '')[:40]}")
    if not evidence:
        evidence.append("Feed metadata analysis")

    return AIProposalSchema(
        primary_topic=primary_topic,
        sub_topics=["Software Engineering", "Open Source", "Developer Tools"],
        target_audience=TargetAudience.INTERMEDIATE,
        content_types=[ContentType.NEWS, ContentType.ANALYSIS],
        content_tone=ContentTone.TECHNICAL,
        suggested_collection="Engineering & Code",
        description=f"Curated feed covering {primary_topic.lower()} with in-depth analysis and timely development updates.",
        evidence=evidence[:3],
    )
