"""
Pydantic Schemas for the Gemma <-> PublicRSS Intelligence Contract.
Enforces strict types, enums, character bounds, and forbids extra keys.
"""
from enum import Enum
from typing import List
from pydantic import BaseModel, Field, ConfigDict, field_validator


class TargetAudience(str, Enum):
    GENERAL = "general"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class ContentType(str, Enum):
    NEWS = "news"
    ANALYSIS = "analysis"
    TUTORIAL = "tutorial"
    RESEARCH = "research"
    OPINION = "opinion"
    DOCUMENTATION = "documentation"
    ANNOUNCEMENTS = "announcements"
    REVIEWS = "reviews"
    MIXED = "mixed"


class ContentTone(str, Enum):
    NEWSY = "newsy"
    TECHNICAL = "technical"
    EDUCATIONAL = "educational"
    ACADEMIC = "academic"
    OPINIONATED = "opinionated"
    MIXED = "mixed"


class AIProposalSchema(BaseModel):
    """
    Authoritative Pydantic model for AI categorization output.
    extra='forbid' strictly disallows unapproved keys.
    """
    model_config = ConfigDict(extra="forbid")

    primary_topic: str = Field(
        ...,
        description="Core subject matter, strictly 1 to 3 words.",
        min_length=2,
        max_length=50,
    )
    sub_topics: List[str] = Field(
        ...,
        description="Relevant sub-topics, tags, or domain specializations.",
        min_length=1,
        max_length=10,
    )
    target_audience: TargetAudience = Field(
        ...,
        description="Audience expertise level required.",
    )
    content_types: List[ContentType] = Field(
        ...,
        description="Primary content formats found in the articles.",
        min_length=1,
    )
    content_tone: ContentTone = Field(
        ...,
        description="Overall editorial tone and presentation style.",
    )
    suggested_collection: str = Field(
        ...,
        description="Suggested thematic folder or shelf name, max 50 chars.",
        min_length=2,
        max_length=50,
    )
    description: str = Field(
        ...,
        description="Synthesized description of the feed, between 20 and 300 characters.",
        min_length=20,
        max_length=300,
    )
    evidence: List[str] = Field(
        ...,
        description="Up to 3 brief factual observation phrases, max 50 chars each.",
        max_length=3,
    )

    @field_validator("primary_topic")
    @classmethod
    def validate_word_count(cls, v: str) -> str:
        words = v.strip().split()
        if not (1 <= len(words) <= 3):
            raise ValueError(f"primary_topic must be 1 to 3 words, got {len(words)} words: '{v}'")
        return v.strip()

    @field_validator("sub_topics")
    @classmethod
    def validate_sub_topics(cls, v: List[str]) -> List[str]:
        cleaned = [t.strip() for t in v if t and t.strip()]
        if not cleaned:
            raise ValueError("sub_topics cannot be empty or contain only blank items.")
        return cleaned[:8]

    @field_validator("evidence")
    @classmethod
    def validate_evidence_items(cls, v: List[str]) -> List[str]:
        cleaned = []
        for item in v:
            clean_item = item.strip()
            if not clean_item:
                continue
            if len(clean_item) > 50:
                clean_item = clean_item[:50].rstrip()
            cleaned.append(clean_item)
        if len(cleaned) > 3:
            cleaned = cleaned[:3]
        return cleaned
