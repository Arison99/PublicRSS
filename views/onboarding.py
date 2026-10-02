"""
Feed Onboarding Views.
Handles URL submission, ingestion pipeline execution, and proposal creation.
"""
from flask import render_template, request, redirect, url_for, flash, jsonify
from . import onboarding_bp
from models.db import db
from models.feed import AIProposal, ProposalStatus
from feeds.service import FeedIngestionService, FeedFetchError, FeedParseError
from ai.provider import GemmaProvider, generate_fallback_mock_proposal


POPULAR_FEEDS = [
    {
        "name": "Hacker News: Front Page",
        "url": "https://news.ycombinator.com/rss",
        "badge": "Tech News",
    },
    {
        "name": "Simon Willison's Weblog",
        "url": "https://simonwillison.net/atom/everything/",
        "badge": "AI & Software",
    },
    {
        "name": "Ars Technica",
        "url": "https://feeds.arstechnica.com/arstechnica/index",
        "badge": "Science & Tech",
    },
    {
        "name": "Python Insider",
        "url": "https://blog.python.org/feeds/posts/default",
        "badge": "Programming",
    },
]


@onboarding_bp.route("/onboarding", methods=["GET"])
def onboarding_page():
    recent_proposals = AIProposal.query.order_by(AIProposal.created_at.desc()).limit(5).all()
    return render_template(
        "onboarding.html",
        popular_feeds=POPULAR_FEEDS,
        recent_proposals=recent_proposals,
    )


@onboarding_bp.route("/onboarding/submit", methods=["POST"])
def submit_feed():
    feed_url = request.form.get("feed_url", "").strip()

    if not feed_url:
        flash("Please provide a valid RSS or Atom feed URL.", "error")
        return redirect(url_for("onboarding.onboarding_page"))

    # Step 1: Ingest (Fetch -> Parse -> Sanitize)
    try:
        ingested = FeedIngestionService.ingest_url(feed_url)
    except (FeedFetchError, FeedParseError) as err:
        flash(f"Feed Ingestion Failed: {str(err)}", "error")
        return redirect(url_for("onboarding.onboarding_page"))
    except Exception as exc:
        flash(f"Unexpected error during feed fetch: {str(exc)}", "error")
        return redirect(url_for("onboarding.onboarding_page"))

    # Step 2: AI Inference & Validation
    provider = GemmaProvider()
    payload = ingested.to_ai_payload()

    validated_schema, raw_ai_text, attempts, validation_error = provider.generate_and_validate(payload)

    # If AI API failed or returned error, try fallback heuristic so curator can still review and edit
    if not validated_schema:
        fallback_schema = generate_fallback_mock_proposal(payload)
        status_note = f"AI validation issue: {validation_error or 'Attempted 2 validation passes'}. Auto-generated initial proposal template."
    else:
        fallback_schema = validated_schema
        status_note = None

    # Step 3: Save to ai_proposals staging table
    proposal = AIProposal(
        feed_url=ingested.feed_url,
        site_url=ingested.site_url,
        raw_title=ingested.raw_title,
        raw_description=ingested.raw_description,
        raw_publisher=ingested.raw_publisher,
        sample_articles=ingested.curator_articles,
        status=ProposalStatus.PENDING_REVIEW,
        primary_topic=fallback_schema.primary_topic,
        sub_topics=fallback_schema.sub_topics,
        target_audience=fallback_schema.target_audience.value,
        content_types=[ct.value for ct in fallback_schema.content_types],
        content_tone=fallback_schema.content_tone.value,
        suggested_collection=fallback_schema.suggested_collection,
        description=fallback_schema.description,
        evidence=fallback_schema.evidence,
        raw_ai_response=raw_ai_text,
        validation_attempts=attempts,
        validation_error=validation_error,
    )

    db.session.add(proposal)
    db.session.commit()

    if status_note:
        flash(status_note, "warning")
    else:
        flash(f"Feed '{ingested.raw_title}' ingested and analyzed by Gemma! Review proposal below.", "success")

    return redirect(url_for("review.review_proposal", proposal_id=proposal.id))
