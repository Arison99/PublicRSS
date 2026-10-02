"""
Secure Feed Fetcher
Implements bounded HTTP retrieval with strict timeouts, size limits,
and SSRF protection.
"""
import socket
import ipaddress
import urllib.parse
import requests

MAX_FEED_SIZE_BYTES = 5 * 1024 * 1024  # 5 Megabytes max
CONNECT_TIMEOUT = 5.0
READ_TIMEOUT = 10.0
USER_AGENT = "PublicRSS-Bot/1.0 (+https://publicrss.org; FeedDiscovery)"


class FeedFetchError(Exception):
    """Raised when fetching an RSS feed fails due to network, size, or security constraints."""
    pass


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
    # Check if hostname itself is an IP literal or resolves to private/loopback
    try:
        # Resolve hostname to IPv4/IPv6
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
    Returns the decoded text string.
    """
    is_safe, error_msg = is_safe_url(url)
    if not is_safe:
        raise FeedFetchError(error_msg)

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
        "Accept-Encoding": "gzip, deflate",
    }

    try:
        with requests.get(
            url,
            headers=headers,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            stream=True,
            allow_redirects=True,
        ) as response:
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
                return raw_bytes.decode(encoding, errors="replace")
            except Exception:
                return raw_bytes.decode("utf-8", errors="replace")

    except requests.exceptions.Timeout:
        raise FeedFetchError(f"Connection timed out while fetching feed from {url}")
    except requests.exceptions.RequestException as exc:
        raise FeedFetchError(f"Network error while fetching feed: {str(exc)}")
