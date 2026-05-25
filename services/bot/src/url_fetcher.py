import re
import httpx
from urllib.parse import urlparse

_URL_RE = re.compile(r"https?://[^\s<>\"']+")
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)

SKIP_DOMAINS: frozenset[str] = frozenset({
    "twitter.com",
    "x.com",
    "instagram.com",
    "t.me",
    "facebook.com",
})


def extract_urls(text: str) -> list[str]:
    urls = _URL_RE.findall(text)
    return [url.rstrip(".,;:!?)'\"") for url in urls]


def _should_skip(url: str) -> bool:
    try:
        hostname = urlparse(url).hostname or ""
        return any(hostname == domain or hostname.endswith("." + domain) for domain in SKIP_DOMAINS)
    except Exception:
        return False


def fetch_titles(urls: list[str]) -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    for url in urls:
        if _should_skip(url):
            result[url] = None
            continue
        try:
            response = httpx.get(
                url,
                timeout=5.0,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (compatible; VaultWhisperer/1.0)"},
            )
            match = _TITLE_RE.search(response.text)
            result[url] = match.group(1).strip() if match else None
        except Exception:
            result[url] = None
    return result
