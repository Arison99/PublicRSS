"""
Human-in-the-Loop Curator Review Views.
Provides side-by-side inspection of Raw Feed Data vs. Gemma AI Proposal,
and supports Approve, Edit & Approve, and Reject actions.
"""
from datetime import datetime, timezone
from flask import render_template, request, redirect, url_for, flash, jsonify
from . import review_bp
from models.db import db
from models.feed import Feed, AIProposal, ProposalStatus
from ai.schemas import (
    AIProposalSchema,
    TargetAudience,
    ContentType,
    ContentTone,
)
from pydantic import ValidationError


@review_bp.route("/review", methods=["GET"])
def review_list():
    status_filter = request.args.get("status", ProposalStatus.PENDING_REVIEW)
    query = AIProposal.query
    if status_filter != "ALL":
        query = query.filter_by(status=status_filter)

    proposals = query.order_by(AIProposal.created_at.desc()).all()
    pending_count = AIProposal.query.filter_by(status=ProposalStatus.PENDING_REVIEW).count()
    approved_count = AIProposal.query.filter(AIProposal.status.in_([ProposalStatus.APPROVED, ProposalStatus.EDITED_APPROVED])).count()
    rejected_count = AIProposal.query.filter_by(status=ProposalStatus.REJECTED).count()

    return render_template(
        "review_list.html",
        proposals=proposals,
        status_filter=status_filter,
        pending_count=pending_count,
        approved_count=approved_count,
        rejected_count=rejected_count,
    )


@review_bp.route("/review/<int:proposal_id>", methods=["GET"])
def review_proposal(proposal_id: int):
    proposal = db.get_or_404(AIProposal, proposal_id)
    audiences = [a.value for a in TargetAudience]
    tones = [t.value for t in ContentTone]
    content_types = [c.value for c in ContentType]

    return render_template(
        "review_detail.html",
        proposal=proposal,
        audiences=audiences,
        tones=tones,
        content_types=content_types,
    )


@review_bp.route("/review/<int:proposal_id>/approve", methods=["POST"])
def approve_proposal(proposal_id: int):
    proposal = db.get_or_404(AIProposal, proposal_id)

    if proposal.status in (ProposalStatus.APPROVED, ProposalStatus.EDITED_APPROVED):
        flash("This proposal is already approved.", "info")
        return redirect(url_for("review.review_proposal", proposal_id=proposal.id))

    # Promote to authoritative feeds table
    existing_feed = Feed.query.filter_by(feed_url=proposal.feed_url).first()
    if existing_feed:
        feed = existing_feed
    else:
        feed = Feed(feed_url=proposal.feed_url)
        db.session.add(feed)

    feed.site_url = proposal.site_url
    feed.title = proposal.raw_title
    feed.description = proposal.raw_description
    feed.publisher = proposal.raw_publisher
    feed.primary_topic = proposal.primary_topic or "Technology"
    feed.sub_topics = proposal.sub_topics or []
    feed.target_audience = proposal.target_audience or TargetAudience.GENERAL.value
    feed.content_types = proposal.content_types or [ContentType.NEWS.value]
    feed.content_tone = proposal.content_tone or ContentTone.NEWSY.value
    feed.suggested_collection = proposal.suggested_collection or "General"
    feed.ai_description = proposal.description or proposal.raw_title
    feed.evidence = proposal.evidence or []
    feed.article_count = len(proposal.sample_articles) if proposal.sample_articles else 0
    feed.last_fetched_at = datetime.now(timezone.utc)

    # Update proposal state
    proposal.status = ProposalStatus.APPROVED
    proposal.reviewed_at = datetime.now(timezone.utc)

    db.session.commit()

    flash(f"Proposal approved! Feed '{feed.title}' is now live in the Public Directory.", "success")
    return redirect(url_for("review.review_proposal", proposal_id=proposal.id))


@review_bp.route("/review/<int:proposal_id>/edit", methods=["POST"])
def edit_and_approve_proposal(proposal_id: int):
    proposal = db.get_or_404(AIProposal, proposal_id)

    primary_topic = request.form.get("primary_topic", "").strip()
    sub_topics_raw = request.form.get("sub_topics", "").strip()
    target_audience = request.form.get("target_audience", "").strip()
    content_tone = request.form.get("content_tone", "").strip()
    suggested_collection = request.form.get("suggested_collection", "").strip()
    description = request.form.get("description", "").strip()
    evidence_raw = request.form.get("evidence", "").strip()
    selected_content_types = request.form.getlist("content_types")

    # Parse sub_topics (comma-separated)
    sub_topics = [s.strip() for s in sub_topics_raw.split(",") if s.strip()]
    if not sub_topics:
        sub_topics = [primary_topic]

    # Parse evidence (lines or comma separated)
    evidence = [e.strip() for e in evidence_raw.replace("\n", ",").split(",") if e.strip()]

    # Validate curator edits against Pydantic schema
    try:
        validated = AIProposalSchema(
            primary_topic=primary_topic,
            sub_topics=sub_topics,
            target_audience=target_audience,
            content_types=selected_content_types or [ContentType.NEWS.value],
            content_tone=content_tone,
            suggested_collection=suggested_collection,
            description=description,
            evidence=evidence[:3],
        )
    except ValidationError as err:
        flash(f"Validation error in your edits: {err.errors()[0]['msg']}", "error")
        return redirect(url_for("review.review_proposal", proposal_id=proposal.id))

    # Update proposal record
    proposal.primary_topic = validated.primary_topic
    proposal.sub_topics = validated.sub_topics
    proposal.target_audience = validated.target_audience.value
    proposal.content_types = [c.value for c in validated.content_types]
    proposal.content_tone = validated.content_tone.value
    proposal.suggested_collection = validated.suggested_collection
    proposal.description = validated.description
    proposal.evidence = validated.evidence
    proposal.status = ProposalStatus.EDITED_APPROVED
    proposal.reviewed_at = datetime.now(timezone.utc)

    # Promote to authoritative feeds table
    feed = Feed.query.filter_by(feed_url=proposal.feed_url).first()
    if not feed:
        feed = Feed(feed_url=proposal.feed_url)
        db.session.add(feed)

    feed.site_url = proposal.site_url
    feed.title = proposal.raw_title
    feed.description = proposal.raw_description
    feed.publisher = proposal.raw_publisher
    feed.primary_topic = validated.primary_topic
    feed.sub_topics = validated.sub_topics
    feed.target_audience = validated.target_audience.value
    feed.content_types = [c.value for c in validated.content_types]
    feed.content_tone = validated.content_tone.value
    feed.suggested_collection = validated.suggested_collection
    feed.ai_description = validated.description
    feed.evidence = validated.evidence
    feed.article_count = len(proposal.sample_articles) if proposal.sample_articles else 0
    feed.last_fetched_at = datetime.now(timezone.utc)

    db.session.commit()

    flash(f"Edits saved and approved! Feed '{feed.title}' is published.", "success")
    return redirect(url_for("review.review_proposal", proposal_id=proposal.id))


@review_bp.route("/review/<int:proposal_id>/reject", methods=["POST"])
def reject_proposal(proposal_id: int):
    proposal = db.get_or_404(AIProposal, proposal_id)
    rejection_reason = request.form.get("rejection_reason", "Curator rejected feed quality/content.")

    proposal.status = ProposalStatus.REJECTED
    proposal.rejection_reason = rejection_reason
    proposal.reviewed_at = datetime.now(timezone.utc)

    db.session.commit()

    flash(f"Proposal for '{proposal.raw_title}' has been rejected.", "info")
    return redirect(url_for("review.review_list", status=ProposalStatus.PENDING_REVIEW))
