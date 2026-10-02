"""
Tests for Feed Ingestion, Robust Parsing, and Sanitization.
"""
import pytest
from feeds.parser import parse_raw_feed, FeedParseError
from feeds.sanitizer import sanitize_text, sanitize_feed_metadata, sanitize_article, TARGET_SAMPLE_ARTICLE_COUNT
from feeds.fetcher import is_safe_url
from feeds.service import FeedIngestionService
from tests.conftest import SAMPLE_VALID_RSS, SAMPLE_MALFORMED_XML


def test_parse_valid_rss():
    parsed = parse_raw_feed(SAMPLE_VALID_RSS)
    meta = parsed["metadata"]
    articles = parsed["articles"]

    assert meta["title"] == "Rust Programming Gazette"
    assert "systems programming" in meta["description"]
    assert len(articles) == 2
    assert articles[0]["title"] == "Async Closures in Rust 1.85"


def test_parse_malformed_xml():
    # Feeds with unclosed tags and unescaped ampersands must still parse or recover
    parsed = parse_raw_feed(SAMPLE_MALFORMED_XML)
    assert parsed is not None
    assert "articles" in parsed or "metadata" in parsed


def test_parse_empty_content_raises_error():
    with pytest.raises(FeedParseError):
        parse_raw_feed("")

    with pytest.raises(FeedParseError):
        parse_raw_feed("   \n\t  ")


def test_sanitizer_html_and_script_stripping():
    dirty_html = "<script>alert('xss')</script><b>Bold Title</b> with &amp; entity <iframe src='evil.com'></iframe>"
    cleaned = sanitize_text(dirty_html, max_length=100, strip_urls=True)
    assert "<script>" not in cleaned
    assert "alert" not in cleaned
    assert "<iframe>" not in cleaned
    assert "Bold Title with & entity" in cleaned


def test_sanitizer_url_stripping():
    text_with_urls = "Read our update at https://example.com/secret-post and follow www.twitter.com/test for news."
    cleaned = sanitize_text(text_with_urls, strip_urls=True)
    assert "https://" not in cleaned
    assert "www." not in cleaned
    assert "[link]" in cleaned


def test_sanitizer_bounds_enforcement():
    long_title = "A" * 500
    cleaned = sanitize_text(long_title, max_length=150)
    assert len(cleaned) == 150


def test_ssrf_safety_checks():
    # Loopback and private ranges must be blocked
    safe, msg = is_safe_url("http://127.0.0.1:8080/feed.xml")
    assert not safe
    assert "restricted/private" in msg.lower() or "localhost" in msg.lower()

    safe, msg = is_safe_url("http://192.168.1.1/feed.rss")
    assert not safe

    safe, msg = is_safe_url("ftp://example.com/feed.xml")
    assert not safe
    assert "scheme" in msg.lower()

    # Valid external HTTP/HTTPS host
    safe, msg = is_safe_url("https://news.ycombinator.com/rss")
    assert safe


def test_feed_service_produces_contract_payload():
    ingested = FeedIngestionService.ingest_content(SAMPLE_VALID_RSS, feed_url="https://rust-gazette.example.com/rss")

    assert ingested.raw_title == "Rust Programming Gazette"
    # Exactly 7 sample articles in AI contract payload
    assert len(ingested.sample_articles_for_ai) == TARGET_SAMPLE_ARTICLE_COUNT

    # Verify no URLs in sample articles for AI
    for art in ingested.sample_articles_for_ai:
        assert len(art["title"]) <= 150
        assert len(art["summary"]) <= 300
        assert "http://" not in art["summary"]
        assert "https://" not in art["summary"]
