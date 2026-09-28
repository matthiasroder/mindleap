"""Bounded HTTP downloads shared by feeds and article retrieval."""

from dataclasses import dataclass
from http.client import HTTPException
from ipaddress import ip_address
import socket
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .llm import ResearchError


REQUEST_TIMEOUT = 20
MAX_RESPONSE_BYTES = 5_000_000


@dataclass(frozen=True)
class Download:
    content: bytes
    url: str
    content_type: str


def _validate_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ResearchError(f"Only HTTP(S) URLs are supported: {url}")
    if parsed.username or parsed.password:
        raise ResearchError("Feed and article URLs must not contain credentials")
    # Article links come from external feeds, not from a trusted local operator.
    addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
    if not addresses or any(not ip_address(address[4][0]).is_global for address in addresses):
        raise ResearchError(f"Feed and article URLs must resolve to public addresses: {parsed.hostname}")


class _PublicRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(url: str) -> Download:
    try:
        _validate_url(url)
        request = Request(url, headers={"User-Agent": "Mindleap/1.0 (+https://github.com/matthiasroder/mindleap)"})
        with build_opener(_PublicRedirects()).open(request, timeout=REQUEST_TIMEOUT) as response:
            content = response.read(MAX_RESPONSE_BYTES + 1)
            if len(content) > MAX_RESPONSE_BYTES:
                raise ResearchError(f"Response exceeds {MAX_RESPONSE_BYTES} bytes: {url}")
            return Download(content, response.geturl(), response.headers.get_content_type())
    except (OSError, ValueError, HTTPException) as exc:
        raise ResearchError(f"Could not download {url}: {exc}") from exc
