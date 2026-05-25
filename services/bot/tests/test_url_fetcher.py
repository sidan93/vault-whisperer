from unittest.mock import patch, MagicMock
import httpx
from url_fetcher import extract_urls, fetch_titles, SKIP_DOMAINS


def test_extract_urls_finds_https_url():
    assert extract_urls("Check this: https://example.com") == ["https://example.com"]


def test_extract_urls_finds_multiple_urls():
    text = "See https://example.com and https://github.com/repo"
    assert extract_urls(text) == ["https://example.com", "https://github.com/repo"]


def test_extract_urls_returns_empty_for_plain_text():
    assert extract_urls("no links here") == []


def test_extract_urls_finds_url_only_message():
    url = "https://x.com/_guillecasaus/status/123"
    assert extract_urls(url) == [url]


def test_fetch_titles_skips_twitter():
    result = fetch_titles(["https://twitter.com/user/status/123"])
    assert result == {"https://twitter.com/user/status/123": None}


def test_fetch_titles_skips_x_com():
    result = fetch_titles(["https://x.com/user/status/123"])
    assert result == {"https://x.com/user/status/123": None}


def test_fetch_titles_skips_instagram():
    result = fetch_titles(["https://instagram.com/p/abc"])
    assert result == {"https://instagram.com/p/abc": None}


def test_fetch_titles_returns_none_on_timeout():
    with patch("url_fetcher.httpx.get", side_effect=httpx.TimeoutException("timeout")):
        result = fetch_titles(["https://example.com"])
    assert result == {"https://example.com": None}


def test_fetch_titles_returns_page_title():
    mock_response = MagicMock()
    mock_response.text = "<html><head><title>Hello World</title></head></html>"
    with patch("url_fetcher.httpx.get", return_value=mock_response):
        result = fetch_titles(["https://example.com"])
    assert result == {"https://example.com": "Hello World"}


def test_fetch_titles_returns_none_when_no_title_tag():
    mock_response = MagicMock()
    mock_response.text = "<html><body>No title here</body></html>"
    with patch("url_fetcher.httpx.get", return_value=mock_response):
        result = fetch_titles(["https://example.com"])
    assert result == {"https://example.com": None}


def test_fetch_titles_handles_empty_list():
    assert fetch_titles([]) == {}


def test_extract_urls_strips_trailing_punctuation():
    assert extract_urls("See https://example.com.") == ["https://example.com"]
    assert extract_urls("(https://example.com)") == ["https://example.com"]
    assert extract_urls("Check https://example.com, https://github.com;") == [
        "https://example.com",
        "https://github.com",
    ]
    assert extract_urls("https://example.com!") == ["https://example.com"]


def test_fetch_titles_does_not_skip_similar_domain():
    # "text.me" contains "t.me" as substring but should NOT be skipped
    mock_response = MagicMock()
    mock_response.text = "<html><head><title>Not Skipped</title></head></html>"
    with patch("url_fetcher.httpx.get", return_value=mock_response):
        result = fetch_titles(["https://text.me/document"])
    assert result == {"https://text.me/document": "Not Skipped"}
