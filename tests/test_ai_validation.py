"""
Tests for Three-Layer AI Validation and Correction Retries.
"""
import pytest
from ai.schemas import (
    AIProposalSchema,
    TargetAudience,
    ContentType,
    ContentTone,
)
from ai.validator import validate_proposal, extract_json_substring
from ai.prompts import build_analysis_prompt, build_correction_prompt
from pydantic import ValidationError


VALID_AI_JSON = """
```json
{
  "primary_topic": "Systems Programming",
  "sub_topics": ["Rust", "Async Runtimes", "Memory Safety"],
  "target_audience": "advanced",
  "content_types": ["analysis", "tutorial"],
  "content_tone": "technical",
  "suggested_collection": "Systems & Infrastructure",
  "description": "Comprehensive engineering journal exploring async runtimes, compiler internals, and memory safety benchmarks in Rust.",
  "evidence": ["Deep dive into async closures", "Zero copy serialization benchmarks"]
}
```
"""


def test_extract_json_substring_from_markdown():
    extracted = extract_json_substring(VALID_AI_JSON)
    assert extracted.startswith("{")
    assert extracted.endswith("}")
    assert "primary_topic" in extracted


def test_layer_1_invalid_json():
    broken_json = '{"primary_topic": "Systems Programming", sub_topics: [broken}'
    is_valid, schema_obj, error = validate_proposal(broken_json)
    assert not is_valid
    assert schema_obj is None
    assert "Layer 1 Error" in error


def test_layer_2_extra_fields_forbidden():
    # extra="forbid" in AIProposalSchema must reject unapproved keys
    json_with_extra = """
    {
      "primary_topic": "Systems Programming",
      "sub_topics": ["Rust"],
      "target_audience": "advanced",
      "content_types": ["analysis"],
      "content_tone": "technical",
      "suggested_collection": "Systems & Infrastructure",
      "description": "Comprehensive engineering journal exploring async runtimes and memory safety.",
      "evidence": ["Deep dive into async closures"],
      "unapproved_hacker_key": "injected_data"
    }
    """
    is_valid, schema_obj, error = validate_proposal(json_with_extra)
    assert not is_valid
    assert schema_obj is None
    assert "Layer 2 Error" in error
    assert "unapproved_hacker_key" in error or "Extra inputs are not permitted" in error


def test_layer_2_invalid_enums():
    json_bad_enum = """
    {
      "primary_topic": "Systems Programming",
      "sub_topics": ["Rust"],
      "target_audience": "super_guru_expert",
      "content_types": ["analysis"],
      "content_tone": "technical",
      "suggested_collection": "Systems & Infrastructure",
      "description": "Comprehensive engineering journal exploring async runtimes and memory safety.",
      "evidence": ["Deep dive into async closures"]
    }
    """
    is_valid, schema_obj, error = validate_proposal(json_bad_enum)
    assert not is_valid
    assert "Layer 2 Error" in error
    assert "target_audience" in error


def test_layer_3_primary_topic_cannot_match_feed_title():
    # primary_topic must not be identical to feed_title
    json_matching_title = """
    {
      "primary_topic": "Rust Gazette",
      "sub_topics": ["Rust"],
      "target_audience": "advanced",
      "content_types": ["analysis"],
      "content_tone": "technical",
      "suggested_collection": "Systems",
      "description": "Comprehensive engineering journal exploring async runtimes and memory safety.",
      "evidence": ["Deep dive into async closures"]
    }
    """
    is_valid, schema_obj, error = validate_proposal(json_matching_title, feed_title="Rust Gazette")
    assert not is_valid
    assert "Layer 3 Semantic Error" in error
    assert "must not match the feed title" in error


def test_layer_3_topic_word_count():
    json_four_words = """
    {
      "primary_topic": "Software Engineering System Architecture",
      "sub_topics": ["Rust"],
      "target_audience": "advanced",
      "content_types": ["analysis"],
      "content_tone": "technical",
      "suggested_collection": "Systems",
      "description": "Comprehensive engineering journal exploring async runtimes and memory safety.",
      "evidence": ["Deep dive into async closures"]
    }
    """
    # Primary topic must be 1 to 3 words
    is_valid, schema_obj, error = validate_proposal(json_four_words)
    assert not is_valid
    assert "1 to 3 words" in error


def test_layer_3_description_length():
    json_short_desc = """
    {
      "primary_topic": "Rust",
      "sub_topics": ["Rust"],
      "target_audience": "advanced",
      "content_types": ["analysis"],
      "content_tone": "technical",
      "suggested_collection": "Systems",
      "description": "Too short.",
      "evidence": ["Deep dive into async closures"]
    }
    """
    is_valid, schema_obj, error = validate_proposal(json_short_desc)
    assert not is_valid
    assert "20 to 300 characters" in error or "String should have at least 20 characters" in error


def test_valid_proposal_passes_all_three_layers():
    is_valid, schema_obj, error = validate_proposal(VALID_AI_JSON, feed_title="Rust Programming Gazette")
    assert is_valid
    assert schema_obj is not None
    assert schema_obj.primary_topic == "Systems Programming"
    assert schema_obj.target_audience == TargetAudience.ADVANCED
    assert schema_obj.content_tone == ContentTone.TECHNICAL


def test_correction_prompt_contains_error_detail():
    payload = {
        "feed_metadata": {"title": "Rust Feed"},
        "sample_articles": [],
    }
    correction = build_correction_prompt(payload, "{'invalid': 'json'}", "Layer 1 Error: Invalid JSON syntax")
    assert "IMPORTANT CORRECTION REQUIRED" in correction
    assert "Layer 1 Error: Invalid JSON syntax" in correction
    assert "<UNTRUSTED_FEED_DATA>" in correction
