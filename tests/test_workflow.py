"""
End-to-End Workflow Tests:
Onboarding -> Staging Proposal -> Approve / Edit / Reject -> Public Directory.
"""
from models.db import db
from models.feed import Feed, AIProposal, ProposalStatus
from tests.conftest import SAMPLE_VALID_RSS
from feeds.service import FeedIngestionService


def test_public_directory_seeded_and_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "PublicRSS" in html
    assert "Hacker News: Front Page" in html or "Simon Willison" in html


def test_directory_live_search_htmx(client):
    # Live search query
    response = client.get("/?q=Simon", headers={"HX-Request": "true"})
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Simon Willison" in html


def test_proposal_lifecycle_approve(client, app):
    with app.app_context():
        # Create staging proposal
        proposal = AIProposal(
            feed_url="https://test-feed.example.com/rss",
            site_url="https://test-feed.example.com",
            raw_title="Test Software Gazette",
            raw_description="A test engineering journal.",
            sample_articles=[{"title": "Intro to SQLite", "summary": "Fast lightweight DB"}],
            status=ProposalStatus.PENDING_REVIEW,
            primary_topic="Database Engineering",
            sub_topics=["SQLite", "Embedded DB"],
            target_audience="intermediate",
            content_types=["tutorial"],
            content_tone="educational",
            suggested_collection="Databases",
            description="Engineering journal dedicated to embedded database internals and testing.",
            evidence=["Intro article on SQLite"],
        )
        db.session.add(proposal)
        db.session.commit()
        prop_id = proposal.id

    # 1. Curator visits review detail
    res = client.get(f"/review/{prop_id}")
    assert res.status_code == 200
    assert "Test Software Gazette" in res.data.decode("utf-8")

    # 2. Curator approves
    approve_res = client.post(f"/review/{prop_id}/approve", follow_redirects=True)
    assert approve_res.status_code == 200

    with app.app_context():
        # Proposal is marked APPROVED
        updated_prop = db.session.get(AIProposal, prop_id)
        assert updated_prop.status == ProposalStatus.APPROVED

        # Feed is now in authoritative feeds table
        feed = Feed.query.filter_by(feed_url="https://test-feed.example.com/rss").first()
        assert feed is not None
        assert feed.title == "Test Software Gazette"
        assert feed.primary_topic == "Database Engineering"


def test_proposal_lifecycle_edit_and_approve(client, app):
    with app.app_context():
        proposal = AIProposal(
            feed_url="https://editable-feed.example.com/rss",
            site_url="https://editable-feed.example.com",
            raw_title="Original Raw Title",
            status=ProposalStatus.PENDING_REVIEW,
            primary_topic="Draft Topic",
            sub_topics=["Draft"],
            target_audience="general",
            content_types=["news"],
            content_tone="newsy",
            suggested_collection="Drafts",
            description="Initial drafted feed description placeholder for test.",
            evidence=["First observation"],
        )
        db.session.add(proposal)
        db.session.commit()
        prop_id = proposal.id

    # Post curator edits
    edit_payload = {
        "primary_topic": "Curated Computer Science",
        "sub_topics": "Algorithms, Distributed Systems",
        "target_audience": "advanced",
        "content_tone": "technical",
        "suggested_collection": "Computer Science",
        "description": "Refined and vetted technical feed covering distributed systems and modern algorithm design.",
        "evidence": "Vetted article on consensus, In-depth analysis of Paxos",
        "content_types": ["analysis", "research"],
    }
    edit_res = client.post(f"/review/{prop_id}/edit", data=edit_payload, follow_redirects=True)
    assert edit_res.status_code == 200

    with app.app_context():
        updated_prop = db.session.get(AIProposal, prop_id)
        assert updated_prop.status == ProposalStatus.EDITED_APPROVED
        assert updated_prop.primary_topic == "Curated Computer Science"

        feed = Feed.query.filter_by(feed_url="https://editable-feed.example.com/rss").first()
        assert feed is not None
        assert feed.primary_topic == "Curated Computer Science"
        assert feed.target_audience == "advanced"


def test_proposal_lifecycle_reject(client, app):
    with app.app_context():
        proposal = AIProposal(
            feed_url="https://spammy-feed.example.com/rss",
            raw_title="Low Quality Spam Feed",
            status=ProposalStatus.PENDING_REVIEW,
            primary_topic="Spam Topic",
            sub_topics=["Spam"],
            target_audience="general",
            content_types=["opinion"],
            content_tone="opinionated",
            suggested_collection="Junk",
            description="A spammy feed that fails editorial quality standards.",
            evidence=["Spam articles"],
        )
        db.session.add(proposal)
        db.session.commit()
        prop_id = proposal.id

    # Reject
    reject_res = client.post(
        f"/review/{prop_id}/reject",
        data={"rejection_reason": "Low editorial quality."},
        follow_redirects=True,
    )
    assert reject_res.status_code == 200

    with app.app_context():
        updated_prop = db.session.get(AIProposal, prop_id)
        assert updated_prop.status == ProposalStatus.REJECTED
        assert updated_prop.rejection_reason == "Low editorial quality."

        # MUST NOT appear in authoritative feeds table
        feed = Feed.query.filter_by(feed_url="https://spammy-feed.example.com/rss").first()
        assert feed is None
