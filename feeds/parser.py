"""
Robust RSS/Atom Feed Parser
Handles RSS 0.9x, 2.0, RDF, and Atom formats, including malformed or irregular XML.
"""
import re
import feedparser
from xml.etree import ElementTree as ET


class FeedParseError(Exception):
    """Raised when feed content cannot be parsed as RSS or Atom."""
    pass


def parse_raw_feed(raw_xml: str) -> dict:
    """
    Parses raw XML string into structured channel metadata and entry list.
    Handles malformed XML gracefully.
    """
    if not raw_xml or not raw_xml.strip():
        raise FeedParseError("Feed content is empty.")

    # Parse with feedparser
    parsed = feedparser.parse(raw_xml)

    # feedparser sets bozo=1 for malformed XML, but often extracts useful data anyway.
    entries = getattr(parsed, "entries", [])
    feed_meta = getattr(parsed, "feed", {})

    # If feedparser found no entries and no feed metadata, try fallback XML parsing
    if not entries and not feed_meta.get("title"):
        parsed = _attempt_fallback_parse(raw_xml)
        entries = parsed.get("entries", [])
        feed_meta = parsed.get("feed", {})

    if not entries and not feed_meta.get("title"):
        # Bozo exception inspection
        bozo_exc = getattr(parsed, "bozo_exception", None)
        msg = f"Unable to parse document as RSS or Atom: {bozo_exc}" if bozo_exc else "No RSS or Atom feed structure detected."
        raise FeedParseError(msg)

    # Extract channel metadata
    title = feed_meta.get("title") or feed_meta.get("subtitle") or "Untitled Feed"
    description = (
        feed_meta.get("description")
        or feed_meta.get("summary")
        or feed_meta.get("subtitle")
        or ""
    )
    site_url = feed_meta.get("link") or feed_meta.get("id") or ""
    publisher = (
        feed_meta.get("publisher")
        or feed_meta.get("author")
        or (feed_meta.get("author_detail", {}).get("name") if hasattr(feed_meta, "author_detail") else None)
        or ""
    )

    # Extract articles
    parsed_articles = []
    for item in entries:
        item_title = getattr(item, "title", None) or "Untitled Article"

        # Summary resolution order: summary, description, content value
        item_summary = getattr(item, "summary", None)
        if not item_summary and hasattr(item, "content") and item.content:
            try:
                item_summary = item.content[0].get("value", "")
            except Exception:
                item_summary = ""
        if not item_summary:
            item_summary = getattr(item, "description", "")

        published = (
            getattr(item, "published", None)
            or getattr(item, "updated", None)
            or getattr(item, "created", None)
            or ""
        )
        link = getattr(item, "link", None) or ""

        parsed_articles.append({
            "title": str(item_title),
            "summary": str(item_summary or ""),
            "published": str(published or ""),
            "link": str(link or ""),
        })

    return {
        "metadata": {
            "title": str(title),
            "description": str(description),
            "site_url": str(site_url),
            "publisher": str(publisher),
        },
        "articles": parsed_articles,
    }


def _attempt_fallback_parse(raw_xml: str) -> dict:
    """
    Fallback parser using regex / standard ElementTree for feeds where feedparser fails
    due to XML namespace or encoding quirks.
    """
    entries = []
    feed_title = ""
    feed_desc = ""
    feed_link = ""

    try:
        # Attempt to clean XML declaration or malformed prefix
        cleaned = re.sub(r'^[^{\w<]+', '', raw_xml.strip())
        root = ET.fromstring(cleaned)

        # Detect RSS vs Atom
        # RSS: <rss><channel><item>
        channel = root.find("channel")
        if channel is not None:
            t = channel.find("title")
            d = channel.find("description")
            l = channel.find("link")
            if t is not None and t.text:
                feed_title = t.text
            if d is not None and d.text:
                feed_desc = d.text
            if l is not None and l.text:
                feed_link = l.text

            for item in channel.findall("item"):
                it = item.find("title")
                ids = item.find("description")
                il = item.find("link")
                ip = item.find("pubDate")
                entries.append({
                    "title": it.text if (it is not None and it.text) else "Untitled",
                    "summary": ids.text if (ids is not None and ids.text) else "",
                    "link": il.text if (il is not None and il.text) else "",
                    "published": ip.text if (ip is not None and ip.text) else "",
                })
        else:
            # Atom fallback: <feed><entry>
            # Remove namespace prefixes for easier parsing
            cleaned_no_ns = re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', cleaned, count=0)
            root_no_ns = ET.fromstring(cleaned_no_ns)
            t = root_no_ns.find("title")
            sub = root_no_ns.find("subtitle")
            if t is not None and t.text:
                feed_title = t.text
            if sub is not None and sub.text:
                feed_desc = sub.text

            for entry in root_no_ns.findall("entry"):
                et = entry.find("title")
                es = entry.find("summary") or entry.find("content")
                ep = entry.find("published") or entry.find("updated")
                el = entry.find("link")
                link_href = el.attrib.get("href", "") if (el is not None) else ""
                entries.append({
                    "title": et.text if (et is not None and et.text) else "Untitled",
                    "summary": es.text if (es is not None and es.text) else "",
                    "link": link_href,
                    "published": ep.text if (ep is not None and ep.text) else "",
                })
    except Exception:
        pass

    return {
        "feed": {
            "title": feed_title,
            "description": feed_desc,
            "link": feed_link,
            "publisher": "",
        },
        "entries": entries,
    }
