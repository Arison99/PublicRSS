"""
SQLAlchemy Models for PublicRSS:
1. Feed: Authoritative / Approved directory entries.
2. AIProposal: Staging / Unapproved AI outputs pending human curator review.
"""
from datetime import datetime, timezone
import json
from models.db import db


class ProposalStatus:
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    EDITED_APPROVED = "EDITED_APPROVED"
    REJECTED = "REJECTED"


class Feed(db.Model):
    """
    Authoritative public directory feed model.
    Only approved feeds are stored or displayed here.
    """
    __tablename__ = "feeds"

    id = db.Column(db.Integer, primary_key=True)
    feed_url = db.Column(db.String(512), unique=True, nullable=False, index=True)
    site_url = db.Column(db.String(512), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    publisher = db.Column(db.String(100), nullable=True)

    # Gemma curated metadata
    primary_topic = db.Column(db.String(50), nullable=False, index=True)
    sub_topics = db.Column(db.JSON, nullable=False, default=list)
    target_audience = db.Column(db.String(20), nullable=False, index=True)
    content_types = db.Column(db.JSON, nullable=False, default=list)
    content_tone = db.Column(db.String(20), nullable=False, index=True)
    suggested_collection = db.Column(db.String(50), nullable=False, index=True)
    ai_description = db.Column(db.String(300), nullable=False)
    evidence = db.Column(db.JSON, nullable=False, default=list)

    article_count = db.Column(db.Integer, default=0)
    last_fetched_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "feed_url": self.feed_url,
            "site_url": self.site_url,
            "title": self.title,
            "description": self.description,
            "publisher": self.publisher,
            "primary_topic": self.primary_topic,
            "sub_topics": self.sub_topics if isinstance(self.sub_topics, list) else [],
            "target_audience": self.target_audience,
            "content_types": self.content_types if isinstance(self.content_types, list) else [],
            "content_tone": self.content_tone,
            "suggested_collection": self.suggested_collection,
            "ai_description": self.ai_description,
            "evidence": self.evidence if isinstance(self.evidence, list) else [],
            "article_count": self.article_count,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M UTC") if self.created_at else "",
        }


class AIProposal(db.Model):
    """
    Staging table for unverified or unapproved AI proposals.
    Human curators review, approve, edit, or reject records here.
    """
    __tablename__ = "ai_proposals"

    id = db.Column(db.Integer, primary_key=True)
    feed_url = db.Column(db.String(512), nullable=False)
    site_url = db.Column(db.String(512), nullable=True)
    raw_title = db.Column(db.String(200), nullable=False)
    raw_description = db.Column(db.Text, nullable=True)
    raw_publisher = db.Column(db.String(100), nullable=True)
    sample_articles = db.Column(db.JSON, nullable=False, default=list)

    # Workflow status
    status = db.Column(
        db.String(30),
        nullable=False,
        default=ProposalStatus.PENDING_REVIEW,
        index=True,
    )

    # Proposed schema fields
    primary_topic = db.Column(db.String(50), nullable=True)
    sub_topics = db.Column(db.JSON, nullable=True, default=list)
    target_audience = db.Column(db.String(20), nullable=True)
    content_types = db.Column(db.JSON, nullable=True, default=list)
    content_tone = db.Column(db.String(20), nullable=True)
    suggested_collection = db.Column(db.String(50), nullable=True)
    description = db.Column(db.String(300), nullable=True)
    evidence = db.Column(db.JSON, nullable=True, default=list)

    # Ingestion & Validation metrics
    raw_ai_response = db.Column(db.Text, nullable=True)
    validation_attempts = db.Column(db.Integer, default=1)
    validation_error = db.Column(db.Text, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    reviewed_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "feed_url": self.feed_url,
            "site_url": self.site_url,
            "raw_title": self.raw_title,
            "raw_description": self.raw_description,
            "raw_publisher": self.raw_publisher,
            "sample_articles": self.sample_articles if isinstance(self.sample_articles, list) else [],
            "status": self.status,
            "primary_topic": self.primary_topic,
            "sub_topics": self.sub_topics if isinstance(self.sub_topics, list) else [],
            "target_audience": self.target_audience,
            "content_types": self.content_types if isinstance(self.content_types, list) else [],
            "content_tone": self.content_tone,
            "suggested_collection": self.suggested_collection,
            "description": self.description,
            "evidence": self.evidence if isinstance(self.evidence, list) else [],
            "validation_attempts": self.validation_attempts,
            "validation_error": self.validation_error,
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M UTC") if self.created_at else "",
            "reviewed_at": self.reviewed_at.strftime("%Y-%m-%d %H:%M UTC") if self.reviewed_at else None,
        }
