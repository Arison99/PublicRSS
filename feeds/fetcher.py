"""
Secure Feed Fetcher
Implements bounded HTTP retrieval with strict timeouts, size limits,
SSRF protection, intelligent URL normalization, and detailed HTTP 429 rate limit diagnostics.
"""
import time
import socket
import ipaddress
import urllib.parse
import re
import requests

MAX_FEED_SIZE_BYTES = 5 * 1024 * 1024  # 5 Megabytes max
CONNECT_TIMEOUT = 5.0
READ_TIMEOUT = 10.0

# Modern browser-compatible User-Agent that avoids bot bans on Reddit/Substack
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 (compatible; PublicRSS/1.0; +https://publicrss.org)"


class FeedFetchError(Exception):
    """Raised when fetching an RSS feed fails due to network, size, or security constraints."""
    pass


def normalize_feed_url(url: str) -> str:
    """
    Intelligently fixes common user input patterns for RSS feeds:
    - Adds https:// if missing
    - Substack: automatically adds /feed if missing
    - Reddit: ensures /r/<sub_name>/.rss format
    - Strips tracking query parameters
    """
    clean_url = url.strip()
    if not clean_url:
        return ""

    if not clean_url.startswith(("http://", "https://")):
        clean_url = "https://" + clean_url

    parsed = urllib.parse.urlparse(clean_url)
    hostname = (parsed.hostname or "").lower()
    path = parsed.path or ""

    # Normalization for Substack
    if "substack.com" in hostname or "newsletter." in hostname:
        if not path or path == "/" or not (path.endswith("/feed") or path.endswith(".xml") or path.endswith(".rss")):
            clean_path = path.rstrip("/") + "/feed"
            clean_url = urllib.parse.urlunparse((
                parsed.scheme,
                parsed.netloc,
                clean_path,
                parsed.params,
                "",  # remove tracking params
                ""
            ))
            return clean_url

    # Normalization for Reddit
    if "reddit.com" in hostname:
        # Match /r/<subreddit>
        reddit_match = re.match(r"^/r/([a-zA-Z0-9_]+)/?(.*)$", path)
        if reddit_match:
            sub = reddit_match.group(1)
            suffix = reddit_match.group(2)
            # If user didn't specify .rss or .xml, append /.rss
            if not (suffix.endswith(".rss") or suffix.endswith(".xml")):
                clean_path = f"/r/{sub}/.rss"
                clean_url = urllib.parse.urlunparse((
                    parsed.scheme,
                    parsed.netloc,
                    clean_path,
                    "",
                    "",
                    ""
                ))
                return clean_url

    return clean_url


def is_safe_url(url: str) -> tuple[bool, str]:
    """
    Validates that a URL is safe to fetch (HTTP/HTTPS only, non-private, non-loopback IP).
    """
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return False, "Invalid URL structure."

    if parsed.scheme not in ("http", "https"):
        return False, f"Unsupported URL scheme: {parsed.scheme}. Only HTTP/HTTPS are permitted."

    hostname = parsed.hostname
    if not hostname:
        return False, "URL does not contain a valid hostname."

    # Prevent loopback or private ranges (SSRF mitigation)
    try:
        ip_addresses = socket.getaddrinfo(hostname, None)
        for entry in ip_addresses:
            ip_str = entry[4][0]
            ip_obj = ipaddress.ip_address(ip_str)
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved or ip_obj.is_link_local:
                return False, f"Target host resolves to a restricted/private IP address: {ip_str}"
    except socket.gaierror:
        return False, f"Could not resolve hostname: {hostname}"
    except Exception as err:
        return False, f"Host resolution failed: {err}"

    return True, ""


def fetch_feed_content(url: str) -> str:
    """
    Safely fetches the RSS/Atom XML content from the specified URL.
    Handles redirects, size limits, and detailed HTTP 429 rate limit errors.
    """
    normalized_url = normalize_feed_url(url)

    is_safe, error_msg = is_safe_url(normalized_url)
    if not is_safe:
        raise FeedFetchError(error_msg)

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9, text/html;q=0.8, */*;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
    }

    def _execute_request(target_url: str):
        return requests.get(
            target_url,
            headers=headers,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            stream=True,
            allow_redirects=True,
        )

    try:
        response = _execute_request(normalized_url)

        # Handle HTTP 429 Too Many Requests
        if response.status_code == 429:
            reset_sec = (
                response.headers.get("x-ratelimit-reset")
                or response.headers.get("Retry-After")
            )
            hostname = urllib.parse.urlparse(normalized_url).netloc

            # If reset time is small (<= 3s), attempt a quick single retry
            if reset_sec and reset_sec.isdigit() and int(reset_sec) <= 3:
                time.sleep(int(reset_sec) + 0.5)
                response = _execute_request(normalized_url)

            # If still 429, give the user a clear, helpful diagnosis
            if response.status_code == 429:
                reset_info = f" (Resets in ~{reset_sec} seconds)" if reset_sec else ""
                if "reddit.com" in hostname:
                    msg = (
                        f"Rate Limit Exceeded (HTTP 429) from Reddit{reset_info}. "
                        "Reddit aggressively restricts unauthenticated cloud datacenter IP addresses "
                        "to 1 request per 30-60 second window. Please wait a moment and try again."
                    )
                else:
                    msg = (
                        f"Rate Limit Exceeded (HTTP 429) from {hostname}{reset_info}. "
                        "The remote server is temporarily rate-limiting requests. Please wait a moment and retry."
                    )
                raise FeedFetchError(msg)

        if response.status_code != 200:
            raise FeedFetchError(f"HTTP request failed with status code {response.status_code}")

        # Verify content-length header if provided
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > MAX_FEED_SIZE_BYTES:
            raise FeedFetchError(f"Feed payload too large: {content_length} bytes exceeds 5MB limit.")

        # Read chunks safely to prevent memory exhaustion
        chunks = []
        total_bytes = 0
        for chunk in response.iter_content(chunk_size=16384):
            if chunk:
                total_bytes += len(chunk)
                if total_bytes > MAX_FEED_SIZE_BYTES:
                    raise FeedFetchError(f"Feed download exceeded maximum allowable size ({MAX_FEED_SIZE_BYTES} bytes).")
                chunks.append(chunk)

        raw_bytes = b"".join(chunks)

        # Determine encoding
        encoding = response.encoding or response.apparent_encoding or "utf-8"
        try:
            content = raw_bytes.decode(encoding, errors="replace")
        except Exception:
            content = raw_bytes.decode("utf-8", errors="replace")

        # Check if the response is an HTML block page instead of XML (common with Reddit lor2 login wall)
        if ("<html" in content[:400].lower() or "<!doctype html" in content[:400].lower()) and not ("<rss" in content[:1000].lower() or "<feed" in content[:1000].lower()):
            if "reddit.com" in normalized_url and ("welcome to reddit" in content.lower() or "login" in content.lower()):
                raise FeedFetchError(
                    "Reddit redirected the feed to a login page (Rate limit / Logged-out restriction). "
                    "Reddit limits unauthenticated cloud IPs. Please wait a minute and retry, or use a curated feed."
                )
            elif "cloudflare" in content.lower() and "challenge" in content.lower():
                raise FeedFetchError(
                    f"The feed provider ({urllib.parse.urlparse(normalized_url).netloc}) presented a Cloudflare anti-bot verification challenge."
                )

        return content

    except requests.exceptions.Timeout:
        raise FeedFetchError(f"Connection timed out while fetching feed from {normalized_url}")
    except requests.exceptions.RequestException as exc:
        raise FeedFetchError(f"Network error while fetching feed: {str(exc)}")
