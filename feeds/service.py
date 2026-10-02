"""
Feed Ingestion Service
Coordinates fetching, parsing, sanitization, and assembly of the
Intelligence Contract payload.
"""
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

from .fetcher import fetch_feed_content, FeedFetchError
from .parser import parse_raw_feed, FeedParseError
from .sanitizer import (
    sanitize_feed_metadata,
    sanitize_article,
    TARGET_SAMPLE_ARTICLE_COUNT,
)


@dataclass
class IngestedFeedData:
    feed_url: str
    site_url: str
    raw_title: str
    raw_description: str
    raw_publisher: str
    total_articles_found: int
    # Intelligence Contract payload (strictly bounded, sanitized, no URLs):
    feed_metadata_for_ai: Dict[str, str]
    sample_articles_for_ai: List[Dict[str, str]]
    # Raw sample articles for Curator Review UI (includes link & date):
    curator_articles: List[Dict[str, Any]]

    def to_ai_payload(self) -> Dict[str, Any]:
        """Returns the bounded payload for the Gemma intelligence contract."""
        return {
            "feed_metadata": self.feed_metadata_for_ai,
            "sample_articles": self.sample_articles_for_ai,
        }


class FeedIngestionService:
    @staticmethod
    def ingest_url(feed_url: str) -> IngestedFeedData:
        """
        Fetches, parses, and sanitizes an RSS feed from a remote URL.
        """
        raw_xml = fetch_feed_content(feed_url)
        return FeedIngestionService.ingest_content(raw_xml, feed_url=feed_url)

    @staticmethod
    def ingest_content(raw_xml: str, feed_url: str = "") -> IngestedFeedData:
        """
        Parses and sanitizes raw XML content directly (useful for testing and offline analysis).
        """
        parsed_data = parse_raw_feed(raw_xml)
        meta = parsed_data.get("metadata", {})
        articles = parsed_data.get("articles", [])

        # 1. Sanitize metadata according to contract limits
        sanitized_meta = sanitize_feed_metadata(
            raw_title=meta.get("title"),
            raw_description=meta.get("description"),
            raw_publisher=meta.get("publisher"),
        )

        # 2. Select up to 7 articles for the AI contract
        # The contract specifies: Exactly 7 articles. If fewer than 7 exist,
        # we take all available and provide descriptive placeholder markers
        # if needed, or send the available set bounded.
        selected_raw_articles = articles[:TARGET_SAMPLE_ARTICLE_COUNT]

        sample_articles_for_ai: List[Dict[str, str]] = []
        curator_articles: List[Dict[str, Any]] = []

        for item in selected_raw_articles:
            sanitized = sanitize_article(
                raw_title=item.get("title"),
                raw_summary=item.get("summary"),
            )
            # Crucial: No URLs sent to model per spec
            sample_articles_for_ai.append({
                "title": sanitized["title"],
                "summary": sanitized["summary"],
            })

            # For the human review panel, keep the link and published date
            curator_articles.append({
                "title": sanitized["title"],
                "summary": sanitized["summary"],
                "link": item.get("link", ""),
                "published": item.get("published", ""),
            })

        # If a feed has fewer than 7 articles, pad with a distinct placeholder note
        # so the contract is deterministic with exactly 7 articles as requested:
        # "sample_articles: Exactly 7 articles. Each: title (150), summary (300)."
        original_article_count = len(sample_articles_for_ai)
        while len(sample_articles_for_ai) < TARGET_SAMPLE_ARTICLE_COUNT:
            pad_idx = len(sample_articles_for_ai) + 1
            if original_article_count == 0:
                summary_text = "No published articles found in this feed stream yet."
            else:
                summary_text = f"Only {original_article_count} active items available in current feed XML archive."
            sample_articles_for_ai.append({
                "title": f"[Archive Slot {pad_idx}: No additional article]",
                "summary": summary_text,
            })

        return IngestedFeedData(
            feed_url=feed_url,
            site_url=meta.get("site_url", ""),
            raw_title=meta.get("title", ""),
            raw_description=meta.get("description", ""),
            raw_publisher=meta.get("publisher", ""),
            total_articles_found=len(articles),
            feed_metadata_for_ai=sanitized_meta,
            sample_articles_for_ai=sample_articles_for_ai,
            curator_articles=curator_articles,
        )
